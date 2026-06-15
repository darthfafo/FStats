"""
Parte 3 — Realimentación desde el warehouse de FStats.

Selecciona reels reales de un portal, baja el mp4 vía Graph API (media_url, con los
tokens de cada portal), corre el pipeline del analizador y guarda el resultado real
etiquetado. Para entrenar el regresor se traen DOS clases:
  - ganadores  = top percentil de reach/plays por portal   (is_winner=True)
  - perdedores = bottom percentil                            (is_winner=False)

La ingesta va por bloques y es idempotente (saltea post_ids ya analizados).
"""
import os
import tempfile

import requests

from warehouse.db import get_connection, portal_id as _portal_id
from analyzer import store

_COLS = ["post_id", "caption", "permalink", "reach", "plays",
         "like_count", "comments_count", "percent_rank"]


def _select(portal_nombre, metric, where_pr, order, percentile, limit):
    metric = "plays" if metric == "plays" else "reach"
    pid = _portal_id(portal_nombre)
    limit_sql = f"LIMIT {int(limit)}" if limit else ""
    con = get_connection(read_only=True)
    try:
        rows = con.execute(
            f"""
            WITH reels AS (
                SELECT post_id, caption, permalink, reach, plays,
                       like_count, comments_count,
                       percent_rank() OVER (ORDER BY {metric}) AS pr
                FROM ig_posts
                WHERE portal_id = ? AND is_reel = TRUE AND {metric} > 0
            )
            SELECT post_id, caption, permalink, reach, plays,
                   like_count, comments_count, pr
            FROM reels WHERE pr {where_pr} ?
            ORDER BY {metric} {order}
            {limit_sql}
            """,
            [pid, percentile]).fetchall()
    finally:
        con.close()
    return [dict(zip(_COLS, r)) for r in rows]


def select_winners(portal_nombre, metric="reach", percentile=0.8, limit=None):
    """Top (1 - percentile) por métrica, normalizado por portal. Orden desc."""
    return _select(portal_nombre, metric, ">=", "DESC", percentile, limit)


def select_losers(portal_nombre, metric="reach", percentile=0.2, limit=None):
    """Bottom percentile por métrica (peores reels). Orden asc."""
    return _select(portal_nombre, metric, "<=", "ASC", percentile, limit)


def _download(url, dest):
    r = requests.get(url, stream=True, timeout=180)
    r.raise_for_status()
    with open(dest, "wb") as fh:
        for chunk in r.iter_content(1 << 16):
            if chunk:
                fh.write(chunk)


def _analyze_and_store(ig, item, pid, is_winner):
    """Baja, analiza y guarda un reel con su etiqueta real. Devuelve None o (post_id, error)."""
    from analyzer import features as feats_mod, transcribe as tr_mod, score as score_mod

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
    transcript = tr_mod.transcribe(dest).get("text", "")
    result = score_mod.score_video(features, transcript=transcript,
                                   caption=item.get("caption", ""), frames_b64=frames)
    run_id = store.insert_run(
        source="warehouse", features=features, score_result=result,
        video_sha256=sha, video_path=dest,
        filename=f"{item['post_id']}.mp4", portal_id=pid, post_id=item["post_id"])
    engagement = int(item.get("like_count", 0) or 0) + int(item.get("comments_count", 0) or 0)
    store.insert_outcome(
        run_id=run_id, is_winner=is_winner,
        real_reach=item.get("reach", 0), real_plays=item.get("plays", 0),
        real_engagement=engagement, portal_id=pid, post_id=item["post_id"],
        label_source="warehouse_percentile")
    return None


def ingest_training_block(portal, metric="reach", top_pct=0.8, bottom_pct=0.2,
                          block_size=10, progress_cb=None):
    """
    Ingesta un bloque balanceado de ganadores (top) y perdedores (bottom) de un
    portal, idempotente. Devuelve {winners, losers, processed, skipped, errors}.
    """
    from collectors.instagram import InstagramCollector
    nombre = portal["nombre"]
    pid = _portal_id(nombre)
    done = store.ingested_post_ids(pid)

    winners = [w for w in select_winners(nombre, metric, top_pct)
               if w["post_id"] not in done][:block_size]
    losers = [l for l in select_losers(nombre, metric, bottom_pct)
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
