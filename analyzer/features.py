"""
Features deterministas de un video, sin modelos pesados: solo OpenCV + ffmpeg.

Se hace una pasada liviana (frames reducidos a 64x64) para medir cortes de
escena, movimiento y duración, y una segunda pasada puntual que extrae unos
pocos frames de buena calidad (gancho + uniformes) para mandarle a Claude.
Nunca se acumulan frames a resolución completa en memoria.
"""
import os
import re
import base64
import subprocess

import numpy as np
import cv2

HOOK_SECS = 3.0          # ventana del "gancho" inicial
CUT_THRESHOLD = 25.0     # diff medio (0-255) entre frames para contar un corte


def _ffmpeg_loudness(video_path):
    """Loudness integrada (LUFS) vía ffmpeg ebur128. None si no hay ffmpeg/audio."""
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-i", video_path,
             "-af", "ebur128", "-f", "null", "-"],
            capture_output=True, text=True, timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"lufs_integrated": None, "has_audio": None}
    matches = re.findall(r"I:\s*(-?\d+\.?\d*)\s*LUFS", proc.stderr or "")
    lufs = float(matches[-1]) if matches else None
    # -inf / muy bajo ≈ silencio o sin pista de audio
    has_audio = (lufs is not None) and (lufs > -70)
    return {"lufs_integrated": lufs, "has_audio": has_audio}


def _frame_to_b64(frame, max_side=512, quality=80):
    h, w = frame.shape[:2]
    scale = max_side / max(h, w)
    if scale < 1:
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf.tobytes()).decode("ascii") if ok else None


def _frame_stats(frame):
    if frame is None:
        return {"brightness": None, "contrast": None, "saturation": None}
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    return {
        "brightness": round(float(np.mean(gray)) / 255, 3),
        "contrast":   round(float(np.std(gray)) / 255, 3),
        "saturation": round(float(np.mean(hsv[:, :, 1])) / 255, 3),
    }


def _frames_at_times(video_path, times, max_side=512):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    out = []
    for t in times:
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(int(t * fps), 0))
        ok, frame = cap.read()
        if ok and frame is not None:
            b = _frame_to_b64(frame, max_side)
            if b:
                out.append(b)
    cap.release()
    return out


def extract_features(video_path, sample_frames=6):
    """
    Devuelve (features: dict, frames_b64: list[str]).

    features: duración, aspect ratio, cortes de escena (totales / por seg / en el
    gancho), movimiento (global y en el gancho), stats del primer frame y loudness.
    frames_b64: frames muestreados (gancho + uniformes) en JPEG base64.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = total / fps if fps else 0.0
    step = max(1, int(round(fps / 6)))   # ~6 muestras por segundo

    prev_small = None
    diffs, diff_times, cut_times = [], [], []
    first_stats = {"brightness": None, "contrast": None, "saturation": None}
    idx = 0
    while True:
        if not cap.grab():
            break
        if idx % step == 0:
            ok, frame = cap.retrieve()
            if ok and frame is not None:
                t = idx / fps
                if idx == 0:
                    first_stats = _frame_stats(frame)
                small = cv2.cvtColor(cv2.resize(frame, (64, 64)), cv2.COLOR_BGR2GRAY)
                if prev_small is not None:
                    d = float(np.mean(np.abs(small.astype(np.int16) -
                                             prev_small.astype(np.int16))))
                    diffs.append(d)
                    diff_times.append(t)
                    if d > CUT_THRESHOLD:
                        cut_times.append(t)
                prev_small = small
        idx += 1
    cap.release()

    cuts_total = len(cut_times)
    cuts_hook = sum(1 for t in cut_times if t <= HOOK_SECS)
    motion = round(float(np.mean(diffs)), 2) if diffs else 0.0
    hook_diffs = [d for d, t in zip(diffs, diff_times) if t <= HOOK_SECS]
    motion_hook = round(float(np.mean(hook_diffs)), 2) if hook_diffs else 0.0
    aspect = round(height / width, 3) if width else None

    features = {
        "duration_sec": round(duration, 2),
        "width": width,
        "height": height,
        "aspect_ratio": aspect,
        "is_vertical": bool(aspect and aspect > 1.1),
        "fps": round(fps, 2),
        "cuts_total": cuts_total,
        "cuts_per_sec": round(cuts_total / duration, 3) if duration else 0.0,
        "cuts_in_hook": cuts_hook,
        "motion_mean": motion,
        "motion_hook": motion_hook,
        "first_frame": first_stats,
    }
    features.update(_ffmpeg_loudness(video_path))

    # Features de audio open source (librosa). Import perezoso: si librosa no está
    # instalado, no agrega nada y el resto sigue igual.
    try:
        from analyzer import audio as _audio
        features.update(_audio.extract_audio_features(video_path))
    except Exception:
        pass

    # Tiempos de muestreo: gancho denso + uniformes en todo el video.
    hook_t = [0.0, min(1.0, duration), min(2.0, duration)]
    uniform_t = list(np.linspace(0, duration, sample_frames)) if duration > 0 else [0.0]
    times = sorted({round(float(x), 2) for x in hook_t + uniform_t})
    frames_b64 = _frames_at_times(video_path, times)

    return features, frames_b64
