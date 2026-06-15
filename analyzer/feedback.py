"""
Parte 3 — Realimentación desde el warehouse de FStats.

El "éxito" de un reel NO es solo alcance bruto: es una COMBINACIÓN ponderada de
cómo interactuó la gente. Para cada reel se calcula, normalizado por portal:
  success = w_eng·pct(engagement_rate) + w_plays·pct(plays) + w_reach·pct(reach)
donde engagement_rate = (likes + comentarios) / reach. Los pesos se ajustan por
entorno (SUCCESS_W_ENG / SUCCESS_W_PLAYS / SUCCESS_W_REACH).

Para entrenar el regresor se traen dos clases por `success`:
  - ganadores  = top percentil    (is_winner=True)
  - perdedores = bottom percentil  (is_winner=False)
La ingesta va por bloques y es idempotente (saltea post_ids ya analizados).
"""
import os
import tempfile

import requests

from warehouse.db import get_connection, portal_id as _portal_id
from analyzer import store

_COLS = ["post_id", "caption", "permalink", "reach", "plays",
         "like_count", "comments_count", "success"]


def _weights():
    w = (float(os.getenv("SUCCESS_W_ENG", "0.5")),
         float(os.getenv("SUCCESS_W_PLAYS", "0.3")),
         float(os.getenv("SUCCESS_W_REACH", "0.2")))
    s = sum(w) or 1.0
    return tuple(x / s for x in w)


def _select(portal_nombre, where, order, percentile, limit):
    pid = _portal_id(portal_nombre)
    we, wp, wr = _weights()
    limit_sql = f"LIMIT {int(limit)}" if limit else ""
    con = get_connection(read_only=True)
    try:
        rows = con.execute(
            f"""
            WITH reels AS (
                SELECT post_id, caption, permalink, reach, plays,
                       like_count, comments_count,
                       -- "audiencia" del reel: reach si lo hay, si no las reproducciones
                       -- (los reels se miden por plays, y muchas veces reach viene 0).
                       CASE WHEN greatest(COALESCE(reach,0), COALESCE(plays,0)) > 0
                            THEN (COALESCE(like_count,0)+COALESCE(comments_count,0))::DOUBLE
                                 / greatest(COALESCE(reach,0), COALESCE(plays,0))
                            ELSE 0 END AS eng_rate
                FROM ig_posts
                WHERE portal_id = ? AND is_reel = TRUE
                  AND (COALESCE(reach,0) > 0 OR COALESCE(plays,0) > 0)
            ),
            ranked AS (
                SELECT *,
                       percent_rank() OVER (ORDER BY eng_rate) AS pr_eng,
                       percent_rank() OVER (ORDER BY plays)    AS pr_plays,
                       percent_rank() OVER (ORDER BY reach)    AS pr_reach
                FROM reels
            ),
            scored AS (
                SELECT *, (? * pr_eng + ? * pr_plays + ? * pr_reach) AS success
                FROM ranked
            )
            SELECT post_id, caption, permalink, reach, plays,
                   like_count, comments_count, success
            FROM scored WHERE success {where} ?
            ORDER BY success {order}
            {limit_sql}
            """,
            [pid, we, wp, wr, percentile]).fetchall()
    finally:
        con.close()
    return [dict(zip(_COLS, r)) for r in rows]


def select_winners(portal_nombre, percentile=0.8, limit=None):
    """Reels con success en el top (≥ percentile), normalizado por portal."""
    return _select(portal_nombre, ">=", "DESC", percentile, limit)


def select_losers(portal_nombre, percentile=0.2, limit=None):
    """Reels con success en el bottom (≤ percentile)."""
    return _select(portal_nombre, "<=", "ASC", percentile, limit)


def diagnose(portal_nombre):
    """
    Conteos del warehouse para entender por qué la selección puede dar 0:
    cuántos posts/reels hay para el portal, cuántos con reach/plays, y qué
    portal_ids existen realmente en ig_posts (para detectar un id que no matchea).
    """
    pid = _portal_id(portal_nombre)
    con = get_connection(read_only=True)
    try:
        row = con.execute(
            """SELECT count(*),
                      count(*) FILTER (WHERE is_reel),
                      count(*) FILTER (WHERE is_reel AND COALESCE(reach,0) > 0),
                      count(*) FILTER (WHERE is_reel AND COALESCE(plays,0) > 0)
               FROM ig_posts WHERE portal_id = ?""", [pid]).fetchone()
        portales = con.execute(
            """SELECT portal_id, count(*) AS posts,
                      count(*) FILTER (WHERE is_reel) AS reels
               FROM ig_posts GROUP BY portal_id ORDER BY posts DESC""").fetchall()
        # Qué media_type/product_type hay realmente en los datos de este portal
        # (revela si Meta devolvió 'REELS' y si plays/reach vienen poblados).
        tipos = con.execute(
            """SELECT COALESCE(media_type,'?'), COALESCE(product_type,'?'),
                      count(*),
                      count(*) FILTER (WHERE COALESCE(plays,0) > 0),
                      count(*) FILTER (WHERE COALESCE(reach,0) > 0)
               FROM ig_posts WHERE portal_id = ?
               GROUP BY 1, 2 ORDER BY 3 DESC""", [pid]).fetchall()
    finally:
        con.close()
    return {
        "portal_id_buscado": pid,
        "posts": row[0], "reels": row[1],
        "reels_con_reach": row[2], "reels_con_plays": row[3],
        "portales_en_warehouse": [
            {"portal_id": p[0], "posts": p[1], "reels": p[2]} for p in portales],
        "tipos": [
            {"media_type": t[0], "product_type": t[1], "n": t[2],
             "con_plays": t[3], "con_reach": t[4]} for t in tipos],
    }


def _download(url, dest):
    r = requests.get(url, stream=True, timeout=180)
    r.raise_for_status()
    with open(dest, "wb") as fh:
        for chunk in r.iter_content(1 << 16):
            if chunk:
                fh.write(chunk)


def _analyze_and_store(ig, item, pid, is_winner):
    """Baja, analiza y guarda un reel con su etiqueta real. None si OK, o (post_id, error)."""
    from analyzer import features as feats_mod, score as score_mod

    media = ig.get_media_url(item["post_id"])
    url = media.get("media_url")
    if not url:
        return (item["post_id"], "sin media_url (¿no es video?)")

    fd, tmp = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    try:
        _download(url, tmp)
        sha, dest = store.save_video(tmp, move=True)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    features, frames = feats_mod.extract_features(dest)
    # Sin transcripción acá: no alimenta el score y Whisper es el paso más caro de
    # la ingesta en lote. La forma del video + el audio (librosa) ya están.
    result = score_mod.score_video(features, caption=item.get("caption", ""),
                                   frames_b64=frames)
    run_id = store.insert_run(
        source="warehouse", features=features, score_result=result,
        video_sha256=sha, video_path=dest,
        filename=f"{item['post_id']}.mp4", portal_id=pid, post_id=item["post_id"])
    engagement = int(item.get("like_count", 0) or 0) + int(item.get("comments_count", 0) or 0)
    store.insert_outcome(
        run_id=run_id, is_winner=is_winner,
        real_reach=item.get("reach", 0), real_plays=item.get("plays", 0),
        real_engagement=engagement, portal_id=pid, post_id=item["post_id"],
        label_source="warehouse_success_combo")
    return None


def ingest_training_block(portal, top_pct=0.8, bottom_pct=0.2, block_size=10,
                          progress_cb=None):
    """
    Ingesta un bloque balanceado de ganadores (top success) y perdedores (bottom)
    de un portal, idempotente. Devuelve {winners, losers, processed, skipped, errors}.
    """
    from collectors.instagram import InstagramCollector
    nombre = portal["nombre"]
    pid = _portal_id(nombre)
    done = store.ingested_post_ids(pid)

    winners = [w for w in select_winners(nombre, top_pct)
               if w["post_id"] not in done][:block_size]
    losers = [l for l in select_losers(nombre, bottom_pct)
              if l["post_id"] not in done][:block_size]
    items = [(w, True) for w in winners] + [(l, False) for l in losers]

    ig = InstagramCollector(ig_id=portal.get("instagram_id"),
                            access_token=portal.get("access_token"))
    summary = {"winners": len(winners), "losers": len(losers),
               "processed": 0, "skipped": 0, "errors": []}

    for i, (item, is_winner) in enumerate(items):
        if progress_cb:
            progress_cb(i, len(items), item)
        try:
            err = _analyze_and_store(ig, item, pid, is_winner)
            if err:
                summary["errors"].append(err)
            else:
                summary["processed"] += 1
        except Exception as e:
            summary["errors"].append((item["post_id"], str(e)))

    if progress_cb:
        progress_cb(len(items), len(items), None)
    return summary
