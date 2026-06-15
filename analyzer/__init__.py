"""
Analizador de potencial de viralidad.

Pipeline: features deterministas (ffmpeg/opencv) → transcripción → score híbrido
con Claude → persistencia en el warehouse (MotherDuck). Los módulos pesados se
importan de forma perezosa para no romper el arranque del panel si falta alguna
dependencia (opencv / anthropic / faster-whisper).
"""
import os


def analyze_video(video_path, *, caption="", source="upload", portal_id=None,
                  post_id=None, persist=True, transcribe_audio=False):
    """
    Corre el pipeline completo sobre un archivo de video.

    Devuelve dict: {features, transcript, score_result, run_id}.
    score_result = {score, subscores, explanation, model}.
    Si persist=True, guarda el mp4 en data/analyzer/ y una fila en raw_analyzer_runs.
    """
    from analyzer import features as feats_mod, score as score_mod, store

    features, frames = feats_mod.extract_features(video_path)

    transcript = ""
    if transcribe_audio:
        from analyzer import transcribe as tr_mod
        transcript = tr_mod.transcribe(video_path).get("text", "")

    result = score_mod.score_video(
        features, transcript=transcript, caption=caption, frames_b64=frames)

    run_id, persist_error = None, None
    if persist:
        # El guardado es best-effort: si la base no está disponible (falta token,
        # etc.) el análisis se devuelve igual, solo sin persistir.
        try:
            sha, dest = store.save_video(video_path)
            run_id = store.insert_run(
                source=source, features=features, score_result=result,
                video_sha256=sha, video_path=dest,
                filename=os.path.basename(video_path),
                portal_id=portal_id, post_id=post_id)
        except Exception as e:
            persist_error = str(e)

    return {"features": features, "transcript": transcript,
            "score_result": result, "run_id": run_id, "persist_error": persist_error}
