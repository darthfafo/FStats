"""
Features deterministas de un video, sin modelos pesados: solo OpenCV + ffmpeg.

Dos clases de señales:
  - dinámica/ritmo: cortes de escena, movimiento, duración (pasada liviana 64x64).
  - visuales del contenido: caras/personas, texto en pantalla, colorido, densidad
    de bordes, saturación (sobre frames muestreados de buena calidad).
El audio se agrega aparte (analyzer/audio.py). La transcripción NO alimenta estas
features: lo que importa es el contenido visual de los fotogramas.
"""
import os
import re
import base64
import subprocess

import numpy as np
import cv2

HOOK_SECS = 3.0          # ventana del "gancho" inicial
CUT_THRESHOLD = 25.0     # diff medio (0-255) entre frames para contar un corte

_CASCADE = None


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


def _grab_frames(video_path, times):
    """Devuelve [(t, frame_bgr)] en los timestamps pedidos (frames de calidad)."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    out = []
    for t in times:
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(int(t * fps), 0))
        ok, frame = cap.read()
        if ok and frame is not None:
            out.append((t, frame))
    cap.release()
    return out


# ── Features visuales del contenido (lo que importa para el enganche) ──────────
def _face_cascade():
    """Detector de caras Haar (viene incluido en opencv). None si no carga."""
    global _CASCADE
    if _CASCADE is None:
        try:
            path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            c = cv2.CascadeClassifier(path)
            _CASCADE = c if not c.empty() else False
        except Exception:
            _CASCADE = False
    return _CASCADE or None


def _colorfulness(frame):
    """Métrica de colorido de Hasler-Süsstrunk (qué tan vívido/llamativo es el frame)."""
    b, g, r = cv2.split(frame.astype("float"))
    rg = np.abs(r - g)
    yb = np.abs(0.5 * (r + g) - b)
    std = np.sqrt(rg.std() ** 2 + yb.std() ** 2)
    mean = np.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
    return float(std + 0.3 * mean)


def _text_region_score(gray):
    """
    Proxy de 'texto en pantalla' sin OCR: resalta regiones horizontales tipo texto
    con morfología y devuelve la proporción de área que ocupan. Correlaciona con
    overlays de texto/subtítulos quemados, muy comunes en reels que enganchan.
    """
    h, w = gray.shape
    grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT,
                            cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    _, bw = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    conn = cv2.morphologyEx(bw, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_RECT, (9, 1)))
    cnts, _ = cv2.findContours(conn, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    area = 0
    for c in cnts:
        x, y, cw, ch = cv2.boundingRect(c)
        ar = cw / float(ch + 1)
        if 2 < ar < 25 and ch > 8 and cw > 20 and cw * ch < 0.3 * h * w:
            area += cw * ch
    return area / float(h * w)


def _visual_features(grabbed, hook_secs):
    """Agrega señales visuales sobre los frames muestreados."""
    if not grabbed:
        return {}
    casc = _face_cascade()
    faces, edges, colorf, sats, texts = [], [], [], [], []
    face_in_hook = False
    for t, frame in grabbed:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        nf = 0
        if casc is not None:
            det = casc.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5,
                                        minSize=(40, 40))
            nf = len(det)
        faces.append(nf)
        if t <= hook_secs and nf > 0:
            face_in_hook = True
        ed = cv2.Canny(gray, 100, 200)
        edges.append(float(np.count_nonzero(ed)) / ed.size)
        colorf.append(_colorfulness(frame))
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        sats.append(float(np.mean(hsv[:, :, 1])) / 255)
        texts.append(_text_region_score(gray))
    n = len(grabbed)
    return {
        "faces_max": int(max(faces)),
        "faces_mean": round(float(np.mean(faces)), 2),
        "face_frames_ratio": round(sum(1 for c in faces if c > 0) / n, 3),
        "face_in_hook": bool(face_in_hook),
        "edge_density_mean": round(float(np.mean(edges)), 4),
        "colorfulness_mean": round(float(np.mean(colorf)), 2),
        "saturation_mean": round(float(np.mean(sats)), 3),
        "text_region_score": round(float(np.mean(texts)), 4),
        "color_variety": round(float(np.std(colorf)), 2),
    }


def extract_features(video_path, sample_frames=6):
    """
    Devuelve (features: dict, frames_b64: list[str]).

    features: duración, aspect ratio, cortes (totales/seg/gancho), movimiento,
    stats del primer frame, loudness, y señales visuales (caras, texto en pantalla,
    colorido, densidad de bordes, variedad).
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

    # Features de audio open source (librosa). Import perezoso.
    try:
        from analyzer import audio as _audio
        features.update(_audio.extract_audio_features(video_path))
    except Exception:
        pass

    # Frames de calidad (gancho denso + uniformes): para Claude/Ollama y para las
    # features visuales del contenido.
    hook_t = [0.0, min(1.0, duration), min(2.0, duration)]
    uniform_t = list(np.linspace(0, duration, sample_frames)) if duration > 0 else [0.0]
    times = sorted({round(float(x), 2) for x in hook_t + uniform_t})
    grabbed = _grab_frames(video_path, times)
    features.update(_visual_features(grabbed, HOOK_SECS))
    frames_b64 = [b for b in (_frame_to_b64(f) for _, f in grabbed) if b]

    return features, frames_b64
