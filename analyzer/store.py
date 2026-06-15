"""
Persistencia del analizador.

Las filas (features, score, explicación, outcome real) van a MotherDuck reusando
warehouse.db. Los mp4 NO van a la base: se guardan en data/analyzer/<sha>.mp4
(carpeta ya ignorada por git) y la base referencia el hash/ruta.
"""
import os
import json
import uuid
import shutil
import hashlib
from datetime import datetime

from warehouse.db import get_connection

VIDEO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "analyzer")


def _ensure_dir():
    os.makedirs(VIDEO_DIR, exist_ok=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def save_video(src_path, move=False):
    """Copia (o mueve) el mp4 a data/analyzer/<sha>.mp4. Devuelve (sha, dest)."""
    _ensure_dir()
    sha = sha256_file(src_path)
    dest = os.path.join(VIDEO_DIR, f"{sha}.mp4")
    if os.path.abspath(src_path) == os.path.abspath(dest):
        return sha, dest
    if not os.path.exists(dest):
        (shutil.move if move else shutil.copy2)(src_path, dest)
    elif move and os.path.exists(src_path):
        os.remove(src_path)
    return sha, dest


def insert_run(*, source, features, score_result, video_sha256=None,
               video_path=None, filename=None, portal_id=None, post_id=None):
    run_id = str(uuid.uuid4())
    con = get_connection()
    try:
        con.execute(
            """INSERT INTO raw_analyzer_runs
               (run_id, source, portal_id, post_id, video_sha256, video_path,
                filename, model, score, subscores, explanation, features,
                duration_sec, created_at, ingested_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?, now())""",
            [run_id, source, portal_id, post_id, video_sha256, video_path, filename,
             score_result.get("model"), float(score_result.get("score", 0) or 0),
             json.dumps(score_result.get("subscores", {}), ensure_ascii=False),
             score_result.get("explanation", ""),
             json.dumps(features or {}, ensure_ascii=False),
             float((features or {}).get("duration_sec", 0) or 0),
             datetime.now()],
        )
        con.commit()
    finally:
        con.close()
    return run_id


def insert_outcome(*, run_id, is_winner, real_reach=0, real_plays=0,
                   real_engagement=0, portal_id=None, post_id=None,
                   label_source="warehouse_percentile"):
    con = get_connection()
    try:
        con.execute(
            """INSERT INTO raw_analyzer_outcomes
               (run_id, portal_id, post_id, real_reach, real_plays,
                real_engagement, is_winner, label_source, ingested_at)
               VALUES (?,?,?,?,?,?,?,?, now())""",
            [run_id, portal_id, post_id, int(real_reach or 0), int(real_plays or 0),
             int(real_engagement or 0), bool(is_winner), label_source],
        )
        con.commit()
    finally:
        con.close()


def list_runs(limit=50):
    """Análisis recientes (DataFrame). Usa conexión completa para garantizar el esquema."""
    con = get_connection()
    try:
        return con.execute(
            """SELECT created_at, source, portal_id, post_id, filename, score,
                      subscores, explanation, model
               FROM analyzer_runs ORDER BY created_at DESC LIMIT ?""",
            [limit]).fetchdf()
    finally:
        con.close()


def ingested_post_ids(portal_id=None):
    """post_ids ya analizados desde el warehouse (para ingestar bloques sin repetir)."""
    con = get_connection()
    try:
        if portal_id:
            rows = con.execute(
                """SELECT DISTINCT post_id FROM analyzer_runs
                   WHERE source='warehouse' AND portal_id = ? AND post_id IS NOT NULL""",
                [portal_id]).fetchall()
        else:
            rows = con.execute(
                """SELECT DISTINCT post_id FROM analyzer_runs
                   WHERE source='warehouse' AND post_id IS NOT NULL""").fetchall()
        return {r[0] for r in rows}
    finally:
        con.close()
