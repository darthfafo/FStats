"""
Regresor de viralidad — aprende de los reels REALES del warehouse.

Toma las features deterministas (video + audio) de cada reel analizado y su
etiqueta real (ganador / perdedor, de raw_analyzer_outcomes) y entrena un
clasificador scikit-learn que predice la probabilidad de ser ganador → score 0-100.

Liviano: corre sobrado en CPU sin GPU, gratis. Es la alternativa al LLM de visión
para máquinas chicas, y mejora a medida que se ingestan más reels (Parte 3).

El modelo entrenado se guarda en data/analyzer/model.joblib (gitignoreado).
"""
import os
import json

from warehouse.db import get_connection

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "analyzer", "model.joblib")

# Features numéricas que alimentan al modelo. Soporta claves anidadas con punto
# (p.ej. "first_frame.brightness"). Los booleanos se mapean a 0/1; los faltantes
# quedan NaN y los completa el imputer del pipeline.
FEATURE_KEYS = [
    # dinámica / ritmo
    "duration_sec", "aspect_ratio", "is_vertical", "fps",
    "cuts_total", "cuts_per_sec", "cuts_in_hook", "motion_mean", "motion_hook",
    "first_frame.brightness", "first_frame.contrast", "first_frame.saturation",
    # visuales del contenido (lo que más correlaciona con el enganche)
    "faces_max", "faces_mean", "face_frames_ratio", "face_in_hook",
    "edge_density_mean", "colorfulness_mean", "saturation_mean",
    "text_region_score", "color_variety",
    # audio
    "lufs_integrated", "has_audio",
    "audio_rms_db", "audio_tempo_bpm", "audio_onset_rate",
    "audio_spectral_centroid_hz", "audio_zcr", "audio_voiced_ratio", "has_voice",
]

_MIN_PER_CLASS = 5   # mínimo de ganadores y de perdedores para entrenar


def _get(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def featurize(features):
    """dict de features -> lista de floats en el orden de FEATURE_KEYS (NaN si falta)."""
    import numpy as np
    out = []
    for k in FEATURE_KEYS:
        v = _get(features or {}, k)
        if isinstance(v, bool):
            v = 1.0 if v else 0.0
        out.append(float(v) if isinstance(v, (int, float)) else np.nan)
    return out


def load_training_data():
    """Devuelve (X, y) desde la base: features de cada run + label is_winner."""
    import numpy as np
    con = get_connection()
    try:
        rows = con.execute(
            """SELECT r.features, o.is_winner
               FROM analyzer_runs r
               JOIN analyzer_outcomes o ON r.run_id = o.run_id
               WHERE o.is_winner IS NOT NULL AND r.features IS NOT NULL""").fetchall()
    finally:
        con.close()
    X, y = [], []
    for feats_json, is_winner in rows:
        try:
            X.append(featurize(json.loads(feats_json)))
            y.append(1 if is_winner else 0)
        except Exception:
            continue
    return np.array(X, dtype=float), np.array(y, dtype=int)


def train():
    """
    Entrena y guarda el modelo. Devuelve {ok, n, n_pos, n_neg, cv_auc, message}.
    No entrena si faltan datos de alguna de las dos clases.
    """
    import numpy as np
    X, y = load_training_data()
    n_pos, n_neg = int((y == 1).sum()), int((y == 0).sum())
    if n_pos < _MIN_PER_CLASS or n_neg < _MIN_PER_CLASS:
        return {"ok": False, "n": len(y), "n_pos": n_pos, "n_neg": n_neg,
                "cv_auc": None,
                "message": f"Faltan datos: hay {n_pos} ganadores y {n_neg} perdedores; "
                           f"se necesitan ≥{_MIN_PER_CLASS} de cada uno. Ingestá más "
                           f"bloques desde la Realimentación (top y bottom percentil)."}

    from sklearn.pipeline import Pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.model_selection import cross_val_score
    import joblib

    pipe = Pipeline([
        # keep_empty_features: si una feature está toda vacía en el set, la rellena
        # con 0 en vez de descartarla (mantiene la dimensión estable train↔predict).
        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(random_state=0)),
    ])

    cv_auc = None
    try:
        folds = min(5, n_pos, n_neg)
        if folds >= 2:
            cv_auc = float(np.mean(
                cross_val_score(pipe, X, y, cv=folds, scoring="roc_auc")))
    except Exception:
        cv_auc = None

    import datetime
    pipe.fit(X, y)
    obj = {"pipe": pipe, "keys": FEATURE_KEYS, "n": len(y),
           "n_pos": n_pos, "n_neg": n_neg, "cv_auc": cv_auc,
           "trained_at": datetime.datetime.now()}

    saved_db = _save_to_db(obj)                 # respaldo persistente (BLOB)
    try:                                        # caché local rápido (best-effort)
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(obj, MODEL_PATH)
    except Exception:
        pass
    _CACHE.clear()

    respaldo = ("respaldado en la base" if saved_db
                else "guardado solo local (no se pudo respaldar en la base)")
    return {"ok": True, "n": len(y), "n_pos": n_pos, "n_neg": n_neg,
            "cv_auc": cv_auc, "saved_db": saved_db,
            "message": f"Modelo entrenado con {len(y)} reels "
                       f"({n_pos} ganadores / {n_neg} perdedores)"
                       + (f", AUC {cv_auc:.2f}" if cv_auc else "")
                       + f". {respaldo.capitalize()}."}


_CACHE = {}


def _save_to_db(obj):
    """Serializa el modelo (joblib) y lo guarda como BLOB en la base. True si OK."""
    import io
    import json
    import joblib
    try:
        buf = io.BytesIO()
        joblib.dump(obj, buf)
        con = get_connection()
        try:
            con.execute(
                """INSERT INTO raw_analyzer_model
                   (model_blob, feature_keys, n, n_pos, n_neg, cv_auc,
                    trained_at, ingested_at)
                   VALUES (?,?,?,?,?,?,?, now())""",
                [buf.getvalue(), json.dumps(obj.get("keys")), obj.get("n"),
                 obj.get("n_pos"), obj.get("n_neg"), obj.get("cv_auc"),
                 obj.get("trained_at")])
            con.commit()
        finally:
            con.close()
        return True
    except Exception:
        return False


def _load_from_db():
    """Modelo vigente desde la base, cacheado por trained_at. None si no hay/falla."""
    try:
        con = get_connection(read_only=True)
        try:
            row = con.execute("SELECT trained_at FROM analyzer_model").fetchone()
            if not row:
                return None
            stamp = row[0]
            if _CACHE.get("stamp") == stamp and _CACHE.get("obj") is not None:
                return _CACHE["obj"]
            blob = con.execute("SELECT model_blob FROM analyzer_model").fetchone()[0]
        finally:
            con.close()
    except Exception:
        return None
    try:
        import io
        import joblib
        obj = joblib.load(io.BytesIO(bytes(blob)))
        _CACHE["stamp"], _CACHE["obj"] = stamp, obj
        return obj
    except Exception:
        return None


def load_model():
    """Modelo vigente. Fuente de verdad: la base; fallback: caché local en disco."""
    obj = _load_from_db()
    if obj is not None:
        return obj
    if os.path.exists(MODEL_PATH):
        try:
            import joblib
            return joblib.load(MODEL_PATH)
        except Exception:
            return None
    return None


def model_info():
    """Resumen del modelo entrenado, o None si no hay."""
    m = load_model()
    if not m:
        return None
    return {"n": m.get("n"), "n_pos": m.get("n_pos"),
            "n_neg": m.get("n_neg"), "cv_auc": m.get("cv_auc")}


def predict_score(features):
    """Score 0-100 (prob. de ganador ×100). None si no hay modelo entrenado."""
    m = load_model()
    if not m:
        return None
    try:
        v = featurize(features)
        prob = float(m["pipe"].predict_proba([v])[0][1])
        return int(round(prob * 100))
    except Exception:
        return None
