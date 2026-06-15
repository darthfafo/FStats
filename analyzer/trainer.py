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
    "duration_sec", "aspect_ratio", "is_vertical", "fps",
    "cuts_total", "cuts_per_sec", "cuts_in_hook", "motion_mean", "motion_hook",
    "first_frame.brightness", "first_frame.contrast", "first_frame.saturation",
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

    pipe.fit(X, y)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"pipe": pipe, "keys": FEATURE_KEYS, "n": len(y),
                 "n_pos": n_pos, "n_neg": n_neg, "cv_auc": cv_auc}, MODEL_PATH)
    return {"ok": True, "n": len(y), "n_pos": n_pos, "n_neg": n_neg,
            "cv_auc": cv_auc,
            "message": f"Modelo entrenado con {len(y)} reels "
                       f"({n_pos} ganadores / {n_neg} perdedores)."
                       + (f" AUC validación: {cv_auc:.2f}" if cv_auc else "")}


_CACHE = {}


def load_model():
    """Carga el modelo entrenado (cacheado por mtime). None si no existe."""
    if not os.path.exists(MODEL_PATH):
        return None
    mtime = os.path.getmtime(MODEL_PATH)
    if _CACHE.get("mtime") != mtime:
        import joblib
        _CACHE["model"] = joblib.load(MODEL_PATH)
        _CACHE["mtime"] = mtime
    return _CACHE.get("model")


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
