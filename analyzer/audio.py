"""
Features deterministas de AUDIO con motores open source (librosa + ffmpeg).

El equivalente sonoro de features.py: extrae señales objetivas del audio del video
—energía, tempo, ritmo de onsets, brillo espectral, proporción de voz/silencio—
para alimentar el scorer (Ollama o heurístico). Todo local, sin APIs.

Degradación elegante: si falta ffmpeg o librosa, devuelve {"audio_available": False}
y el resto del pipeline sigue (igual que la transcripción y el loudness).
"""
import os
import math
import tempfile
import subprocess


def _extract_wav(video_path, sr=22050):
    """Saca un wav mono del video con ffmpeg. None si no hay ffmpeg/audio."""
    fd, wav = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", video_path, "-ac", "1", "-ar", str(sr), wav],
            check=True, timeout=180,
        )
        # ffmpeg crea el archivo aunque el video no tenga pista de audio (silencio):
        # eso lo detecta librosa luego como energía ~0.
        return wav if os.path.getsize(wav) > 0 else None
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        if os.path.exists(wav):
            os.remove(wav)
        return None


def _tempo_bpm(y, sr):
    """BPM estimado, tolerante a la versión de librosa (la API del tempo cambió)."""
    import numpy as np
    import librosa
    try:
        from librosa.feature.rhythm import tempo as _tempo   # librosa >= 0.10
        t = _tempo(y=y, sr=sr)
    except Exception:
        t = librosa.beat.tempo(y=y, sr=sr)                   # versiones previas
    return round(float(np.atleast_1d(t)[0]), 1)


def extract_audio_features(video_path):
    """
    Devuelve un dict con prefijo `audio_`. Claves:
      audio_available, audio_duration_sec, audio_rms_db, audio_tempo_bpm,
      audio_onset_rate (onsets/seg), audio_spectral_centroid_hz, audio_zcr,
      audio_voiced_ratio, audio_silence_ratio, has_voice (proxy).
    """
    try:
        import numpy as np
        import librosa
    except Exception:
        return {"audio_available": False}

    wav = _extract_wav(video_path)
    if not wav:
        return {"audio_available": False}

    try:
        y, sr = librosa.load(wav, sr=22050, mono=True)
        if y.size == 0:
            return {"audio_available": False}

        duration = float(librosa.get_duration(y=y, sr=sr))
        rms = float(np.mean(librosa.feature.rms(y=y)[0]))
        rms_db = round(20 * math.log10(rms), 1) if rms > 1e-6 else -120.0

        # Pista esencialmente en silencio (video sin audio): marcamos voz/energía nulas.
        if rms_db <= -60:
            return {
                "audio_available": True, "audio_duration_sec": round(duration, 2),
                "audio_rms_db": rms_db, "audio_silence_ratio": 1.0,
                "audio_voiced_ratio": 0.0, "has_voice": False,
            }

        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
        onset_rate = round(len(onsets) / duration, 2) if duration else 0.0
        centroid = round(float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0])), 1)
        zcr = round(float(np.mean(librosa.feature.zero_crossing_rate(y)[0])), 4)

        # Proporción de audio "con sonido" vs silencio (proxy de densidad sonora).
        intervals = librosa.effects.split(y, top_db=30)
        voiced = int(sum(e - s for s, e in intervals))
        voiced_ratio = round(voiced / len(y), 3) if len(y) else 0.0

        return {
            "audio_available": True,
            "audio_duration_sec": round(duration, 2),
            "audio_rms_db": rms_db,
            "audio_tempo_bpm": _tempo_bpm(y, sr),
            "audio_onset_rate": onset_rate,
            "audio_spectral_centroid_hz": centroid,
            "audio_zcr": zcr,
            "audio_voiced_ratio": voiced_ratio,
            "audio_silence_ratio": round(1 - voiced_ratio, 3),
            # Proxy de voz: hay sonido sostenido y el centroide cae en rango de habla.
            "has_voice": bool(voiced_ratio > 0.3 and 200 <= centroid <= 4000),
        }
    except Exception:
        return {"audio_available": False}
    finally:
        if os.path.exists(wav):
            os.remove(wav)
