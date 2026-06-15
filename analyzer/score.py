"""
Score de potencial de viralidad — 100% open source, sin APIs pagas.

Motor por defecto: **heurístico** por reglas sobre las features (instantáneo, estable,
sin dependencias). Para usar un LLM de visión local (Ollama) hay que pedirlo
explícitamente con ANALYZER_BACKEND=ollama — requiere RAM/GPU suficiente (un VLM 7B
como llava necesita >8 GB de RAM; en máquinas chicas crashea o tarda minutos).

Config por entorno:
  ANALYZER_BACKEND = "heuristic" (default) | "ollama"
  OLLAMA_HOST      = "http://localhost:11434"   (puede apuntar a un host remoto)
  OLLAMA_MODEL     = "llava"   (alternativas: "qwen2.5vl", "llama3.2-vision")
  OLLAMA_MAX_IMAGES / OLLAMA_NUM_CTX / OLLAMA_TIMEOUT  (ajuste fino)
"""
import os
import json

import requests

DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llava")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
# Modelos de visión chicos tienen contexto limitado: mandamos pocas imágenes
# (las del gancho) y ampliamos num_ctx. Todo configurable por entorno.
OLLAMA_MAX_IMAGES = int(os.getenv("OLLAMA_MAX_IMAGES", "2"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "4096"))
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))

_RUBRIC = """Sos un analista experto en contenido de video corto (Reels/TikTok) para
medios de noticias. Evaluás el POTENCIAL DE VIRALIDAD de un video a partir de
features objetivas, su transcripción y algunos frames.

Criterios (cada subscore 0-100):
- gancho: ¿los primeros 3 segundos capturan la atención? (corte/movimiento inicial,
  primer frame llamativo, promesa clara). Penalizá arranques lentos o planos.
- ritmo: ¿sostiene la atención? (cortes por segundo, movimiento, duración 7-40s).
  Penalizá monotonía o duración excesiva.
- audio: ¿hay audio presente y con energía? (loudness, presencia de voz/música).
- claridad: ¿el mensaje/tema se entiende rápido? (transcripción, texto en pantalla).

score = potencial global 0-100 (NO es el promedio simple: ponderá gancho y ritmo más alto).

Devolvé SOLO un JSON válido, sin texto extra, con esta forma exacta:
{"score": int, "subscores": {"gancho": int, "ritmo": int, "audio": int, "claridad": int},
 "explanation": "2-4 frases en español explicando el puntaje y 1 sugerencia concreta de mejora"}
"""


def score_video(features, transcript="", caption="", frames_b64=None, model=None):
    """
    Devuelve {score, subscores, explanation, model}.

    Usa Ollama por defecto; si falla o ANALYZER_BACKEND='heuristic', usa la heurística.
    """
    backend = os.getenv("ANALYZER_BACKEND", "heuristic").lower()
    if backend == "model":
        return _model_score(features, transcript, caption)
    if backend == "ollama":
        try:
            return _ollama_score(features, transcript, caption, frames_b64,
                                 model or DEFAULT_MODEL)
        except Exception as e:
            out = _heuristic(features, transcript, caption)
            out["explanation"] += f" (fallback: Ollama no disponible — {e})"
            return out
    return _heuristic(features, transcript, caption)


def _model_score(features, transcript, caption):
    """Score del regresor entrenado + desglose heurístico interpretable."""
    from analyzer import trainer
    base = _heuristic(features, transcript, caption)   # subscores + desglose
    s = trainer.predict_score(features)
    if s is None:
        base["explanation"] = ("Modelo aún no entrenado — usando heurístico. Entrená "
                               "el regresor desde Realimentación cuando tengas ganadores "
                               "y perdedores ingestados. ") + base["explanation"]
        return base
    info = trainer.model_info() or {}
    auc = info.get("cv_auc")
    base["score"] = s
    base["model"] = "regresor"
    base["explanation"] = (
        f"Score {s}/100 del modelo entrenado con {info.get('n', '?')} reels reales "
        f"({info.get('n_pos', '?')} ganadores / {info.get('n_neg', '?')} perdedores"
        + (f", AUC {auc:.2f}" if auc else "") + "). Los subscores son el desglose "
        "heurístico orientativo.")
    return base


def _ollama_score(features, transcript, caption, frames_b64, model):
    prompt = (
        _RUBRIC +
        "\n\nFEATURES (JSON):\n" + json.dumps(features, ensure_ascii=False) +
        f"\n\nCAPTION: {(caption or '')[:500]}" +
        f"\n\nTRANSCRIPCIÓN: {(transcript or '')[:2000]}"
    )
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": prompt,
            # base64 JPEG (sin prefijo data:). Pocas imágenes para no exceder el
            # contexto de modelos chicos; las primeras son las del gancho.
            "images": (frames_b64 or [])[:OLLAMA_MAX_IMAGES],
        }],
        "stream": False,
        "format": "json",                        # fuerza salida JSON válida
        "options": {"temperature": 0.2, "num_ctx": OLLAMA_NUM_CTX},
    }
    r = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT)
    r.raise_for_status()
    content = r.json().get("message", {}).get("content", "")
    data = _parse_json(content)
    data["model"] = f"ollama:{model}"
    data["score"] = int(round(float(data.get("score", 0))))
    data.setdefault("subscores", {})
    data.setdefault("explanation", "")
    return data


def _parse_json(text):
    text = (text or "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


def describe(features):
    """
    Traduce las features a una explicación corta por cada subscore, para que el
    puntaje no quede aislado. Devuelve dict {gancho, ritmo, audio, claridad}.
    """
    f = features or {}
    ff = f.get("first_frame") or {}

    # Gancho: qué pasa en los primeros segundos.
    g = []
    n = f.get("cuts_in_hook", 0)
    g.append(f"{n} corte(s) en los primeros 3s" if n else "arranque sin cortes (puede ser lento)")
    g.append("cara al inicio ✅" if f.get("face_in_hook") else "sin cara al inicio")
    g.append("vertical ✅" if f.get("is_vertical") else "no es vertical ⚠️")
    if f.get("colorfulness_mean", 0) >= 30:
        g.append("colores llamativos")

    # Ritmo: dinamismo y duración.
    r = []
    r.append(f"{f.get('cuts_per_sec', 0):.1f} cortes/seg")
    dur = f.get("duration_sec", 0) or 0
    if dur:
        r.append(f"dura {dur:.0f}s " + ("(ideal 7-40s) ✅" if 7 <= dur <= 40
                                        else "(fuera del rango ideal 7-40s) ⚠️"))
    if f.get("audio_available") and f.get("audio_onset_rate"):
        r.append(f"ritmo sonoro {f.get('audio_onset_rate', 0):.1f}/s")

    # Audio.
    a = []
    if f.get("audio_available"):
        a.append(f"{int(f.get('audio_voiced_ratio', 0) * 100)}% con sonido")
        a.append("con voz ✅" if f.get("has_voice") else "sin voz clara")
    elif f.get("has_audio"):
        a.append("tiene audio")
    elif f.get("has_audio") is False:
        a.append("sin audio o casi en silencio ⚠️")
    else:
        a.append("audio no analizado (falta ffmpeg)")

    # Claridad visual: ¿se entiende sin sonido?
    c = []
    c.append("texto en pantalla ✅" if f.get("text_region_score", 0) > 0.02
             else "sin texto en pantalla")
    fr = f.get("face_frames_ratio", 0)
    c.append(f"caras en {int(fr * 100)}% de los frames" if fr else "sin caras")
    if (ff.get("contrast") or 0) >= 0.2:
        c.append("buen contraste")

    return {"gancho": " · ".join(g), "ritmo": " · ".join(r),
            "audio": " · ".join(a), "claridad": " · ".join(c)}


def _heuristic(features, transcript="", caption=""):
    """
    Score sin LLM, basado en el CONTENIDO VISUAL de los fotogramas + ritmo + audio.
    La transcripción NO influye en el puntaje (señal secundaria). Es un arranque;
    el score calibrado lo da el regresor entrenado con interacción real.
    """
    f = features or {}
    ff = f.get("first_frame") or {}
    clamp = lambda x: int(max(0, min(100, x)))

    # Gancho visual: arranque con cortes/movimiento, vertical, cara y color llamativo.
    gancho = (45 + 8 * f.get("cuts_in_hook", 0) + min(f.get("motion_hook", 0), 30)
              + (10 if f.get("is_vertical") else -10)
              + (12 if f.get("face_in_hook") else 0)
              + min(f.get("colorfulness_mean", 0) / 4, 12))

    # Ritmo: cortes por segundo + ritmo sonoro + penalización por duración mala.
    ritmo = 55 + 20 * min(f.get("cuts_per_sec", 0), 2)
    if f.get("audio_available"):
        ritmo += 5 * min(f.get("audio_onset_rate", 0), 4)
    dur = f.get("duration_sec", 0) or 0
    if dur and (dur < 5 or dur > 45):
        ritmo -= 20

    # Audio: features de librosa si están; si no, el flag de loudness de ffmpeg.
    if f.get("audio_available"):
        audio = 40 + int(50 * f.get("audio_voiced_ratio", 0)) + \
            (10 if f.get("has_voice") else 0)
    elif f.get("has_audio"):
        audio = 70
    elif f.get("has_audio") is False:
        audio = 35
    else:
        audio = 50

    # Claridad VISUAL: ¿se entiende sin audio? texto en pantalla, caras, contraste.
    claridad = (40 + 250 * f.get("text_region_score", 0)
                + 25 * f.get("face_frames_ratio", 0)
                + 40 * (ff.get("contrast") or 0))

    sub = {"gancho": clamp(gancho), "ritmo": clamp(ritmo),
           "audio": clamp(audio), "claridad": clamp(claridad)}
    # El visual (gancho + claridad) pesa más que el audio.
    score = clamp(0.35 * sub["gancho"] + 0.30 * sub["ritmo"] +
                  0.20 * sub["claridad"] + 0.15 * sub["audio"])
    # El título también cuenta (la gente lo lee): mezclamos con el gancho del copy.
    cs = f.get("copy_score")
    if cs is not None and f.get("copy_has"):
        score = clamp(0.85 * score + 0.15 * cs)
    return {"score": score, "subscores": sub, "model": "heuristic",
            "explanation": "Score heurístico (sin LLM): gancho visual (cortes, "
                           "movimiento, caras, colorido), ritmo, claridad visual "
                           "(texto en pantalla, caras, contraste) y audio. La "
                           "transcripción no influye. Entrená el regresor para un "
                           "score calibrado con la interacción real de la gente."}
