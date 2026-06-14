from datetime import datetime
from collectors.instagram import InstagramCollector
from warehouse.db import get_connection

PORTAL_ID_MAP = {
    "Chubut Noticias": "chubut_noticias",
    "Atento Chubut":   "atento_chubut",
    "La Calle Online": "la_calle_online",
    "El Americano":    "el_americano",
    "VISTE ESTO?":     "viste_esto",
    "Boca en Linea":   "boca_en_linea",
}


def _portal_id(nombre):
    return PORTAL_ID_MAP.get(nombre, nombre.lower().replace(" ", "_"))


def ingest_instagram(portal):
    nombre = portal["nombre"]
    pid = _portal_id(nombre)
    ig_id = portal.get("instagram_id")
    token = portal.get("access_token")

    if not ig_id or not token:
        print(f"[IG/{nombre}] Skipped — missing ig_id or token")
        return

    ig = InstagramCollector(ig_id=ig_id, access_token=token)
    con = get_connection()

    try:
        _ingest_account_insights(con, ig, pid, ig_id)
    except Exception as e:
        print(f"[IG/{nombre}] account_insights error: {e}")

    try:
        _ingest_account_info(con, ig, pid, ig_id)
    except Exception as e:
        print(f"[IG/{nombre}] account_info error: {e}")

    try:
        _ingest_posts(con, ig, pid)
    except Exception as e:
        print(f"[IG/{nombre}] posts error: {e}")

    con.commit()
    con.close()


def _ingest_account_insights(con, ig, portal_id, ig_id):
    insights = ig.get_account_insights()

    metric_map = {
        "reach":             "alcance",
        "follower_count":    "follower_count",
        "views":             "views",
        "total_interactions": "total_interactions",
        "accounts_engaged":  "accounts_engaged",
        "profile_views":     "profile_views",
    }

    daily_map = {
        "reach":     ("daily_alcance", "reach"),
        "follower_count": ("daily_followers", "follower_count"),
    }

    for daily_key, (dict_key, metric_name) in daily_map.items():
        daily = insights.get(dict_key, {})
        for date_str, value in daily.items():
            if value and value > 0:
                con.execute(
                    """INSERT INTO raw_ig_account_insights
                       (portal_id, ig_id, metric_name, metric_date, metric_value, ingested_at)
                       VALUES (?, ?, ?, ?, ?, now())""",
                    [portal_id, ig_id, metric_name, date_str, int(value)]
                )

    today_str = datetime.now().strftime("%Y-%m-%d")
    total_metrics = {
        "views":              insights.get("views", 0),
        "total_interactions": insights.get("total_inter", 0),
        "accounts_engaged":   insights.get("engaged", 0),
        "profile_views":      insights.get("vistas_perfil", 0),
    }
    for metric_name, total in total_metrics.items():
        if total and total > 0:
            con.execute(
                """INSERT INTO raw_ig_account_insights
                   (portal_id, ig_id, metric_name, metric_date, metric_value, ingested_at)
                   VALUES (?, ?, ?, ?, ?, now())""",
                [portal_id, ig_id, metric_name, today_str, int(total)]
            )

    print(f"[IG/{portal_id}] account_insights ingested")


def _ingest_account_info(con, ig, portal_id, ig_id):
    info = ig.get_account_info()

    con.execute(
        """INSERT INTO raw_ig_account_info
           (portal_id, ig_id, followers_count, follows_count, media_count, ingested_at)
           VALUES (?, ?, ?, ?, ?, now())""",
        [
            portal_id,
            ig_id,
            info.get("followers_count", 0),
            info.get("follows_count", 0),
            info.get("media_count", 0),
        ]
    )
    print(f"[IG/{portal_id}] account_info: followers={info.get('followers_count')}")


def _ingest_posts(con, ig, portal_id):
    media = ig.get_recent_media(limit=100)
    posts = media.get("data", [])
    if not posts:
        print(f"[IG/{portal_id}] posts: no posts returned")
        return

    inserted = 0
    for p in posts:
        try:
            product_type = p.get("product_type", "")
            media_type = p.get("media_type", "IMAGE")
            is_reel = (product_type == "clips" or media_type == "REEL")

            content_type = "reel" if is_reel else media_type.lower()

            con.execute(
                """INSERT INTO raw_ig_posts
                   (portal_id, post_id, caption, media_type, product_type,
                    published_date, like_count, comments_count, permalink,
                    content_type, is_reel, ingested_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now())""",
                [
                    portal_id,
                    p.get("id", ""),
                    (p.get("caption") or "")[:500],
                    media_type,
                    product_type,
                    p.get("timestamp", "")[:10],
                    p.get("like_count", 0),
                    p.get("comments_count", 0),
                    p.get("permalink", ""),
                    content_type,
                    is_reel,
                ]
            )
            inserted += 1
        except Exception as e:
            print(f"[IG/{portal_id}] post {p.get('id')}: {e}")

    print(f"[IG/{portal_id}] posts: {inserted}/{len(posts)} inserted")
