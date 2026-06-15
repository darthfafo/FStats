"""
Transcripción del audio del video.

Usa faster-whisper en CPU si está instalado. Si falta faster-whisper o ffmpeg,
devuelve texto vacío con available=False y el resto del pipeline sigue andando
(el score se calcula igual, solo pierde la señal de "claridad" del habla).
"""
import os
import tempfile
import subprocess

_MODEL_CACHE = {}


def _extract_audio(video_path):
    fd, wav = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", video_path, "-ac", "1", "-ar", "16000", wav],
            check=True, timeout=180,
        )
        return wav
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        if os.path.exists(wav):
            os.remove(wav)
        return None


def _load_model(model_size):
    if model_size not in _MODEL_CACHE:
        from faster_whisper import WhisperModel
        _MODEL_CACHE[model_size] = WhisperModel(
            model_size, device="cpu", compute_type="int8")
    return _MODEL_CACHE[model_size]


def transcribe(video_path, language="es", model_size="small"):
    """Devuelve {text, language, available}."""
    try:
        import faster_whisper  # noqa: F401
    except Exception:
        return {"text": "", "language": language, "available": False}

    wav = _extract_audio(video_path)
    if not wav:
        return {"text": "", "language": language, "available": False}
    try:
        model = _load_model(model_size)
        segments, info = model.transcribe(wav, language=language, vad_filter=True)
        text = " ".join(s.text.strip() for s in segments).strip()
        return {"text": text,
                "language": getattr(info, "language", language),
                "available": True}
    except Exception:
        return {"text": "", "language": language, "available": False}
    finally:
        if os.path.exists(wav):
            os.remove(wav)
