from datetime import datetime
from collectors.facebook import FacebookCollector
from warehouse.db import get_connection, portal_id as _portal_id


def ingest_facebook(portal):
    nombre = portal["nombre"]
    pid = _portal_id(nombre)
    page_id = portal.get("facebook_page_id")
    token = portal.get("access_token")

    if not page_id or not token:
        print(f"[FB/{nombre}] Skipped — missing page_id or token")
        return

    fb = FacebookCollector(page_id=page_id, access_token=token)
    con = get_connection()

    try:
        _ingest_page_insights(con, fb, pid, page_id)
    except Exception as e:
        print(f"[FB/{nombre}] page_insights error: {e}")

    try:
        _ingest_page_info(con, fb, pid, page_id)
    except Exception as e:
        print(f"[FB/{nombre}] page_info error: {e}")

    try:
        _ingest_posts(con, fb, pid)
    except Exception as e:
        print(f"[FB/{nombre}] posts error: {e}")

    try:
        _ingest_fan_growth(con, fb, pid)
    except Exception as e:
        print(f"[FB/{nombre}] fan_growth error: {e}")

    con.commit()
    con.close()


def _ingest_fan_growth(con, fb, portal_id):
    """Nuevos seguidores por día (page_daily_follows / fan_adds)."""
    raw = fb.get_fan_growth()
    por_dia = {}
    for m in raw.get("data", []):
        name = m.get("name", "")
        if "follow" in name or "fan_adds" in name:
            for v in m.get("values", []):
                fecha = v.get("end_time", "")[:10]
                if fecha:
                    por_dia[fecha] = por_dia.get(fecha, 0) + v.get("value", 0)

    inserted = 0
    for fecha, valor in por_dia.items():
        con.execute(
            """INSERT INTO raw_fb_fan_growth
               (portal_id, metric_date, new_follows, ingested_at)
               VALUES (?, ?, ?, now())""",
            [portal_id, fecha, int(valor)]
        )
        inserted += 1
    print(f"[FB/{portal_id}] fan_growth: {inserted} días")


def _ingest_page_insights(con, fb, portal_id, page_id):
    insights = fb.get_page_insights()

    # El collector solo expone detalle diario para alcance y engagement
    # (page_views_total llega solo como total, se guarda más abajo).
    daily_metric_names = {
        "alcance":    "page_impressions_unique",
        "engagement": "page_post_engagements",
    }

    for key, metric_name in daily_metric_names.items():
        daily = insights.get(f"daily_{key}", {})
        for date_str, value in daily.items():
            if value and value > 0:
                con.execute(
                    """INSERT INTO raw_fb_page_insights
                       (portal_id, page_id, metric_name, metric_date, metric_value, ingested_at)
                       VALUES (?, ?, ?, ?, ?, now())""",
                    [portal_id, page_id, metric_name, date_str, int(value)]
                )

    # Solo guardamos como total las métricas SIN serie diaria (vistas). Los
    # totales de alcance/engagement NO se guardan: se calculan sumando el diario
    # en la lectura (igual que la API), evitando colisionar con la serie diaria.
    today_str = datetime.now().strftime("%Y-%m-%d")
    vistas = insights.get("vistas", 0)
    if vistas and vistas > 0:
        con.execute(
            """INSERT INTO raw_fb_page_insights
               (portal_id, page_id, metric_name, metric_date, metric_value, ingested_at)
               VALUES (?, ?, ?, ?, ?, now())""",
            [portal_id, page_id, "page_views_total", today_str, int(vistas)]
        )

    print(f"[FB/{portal_id}] page_insights: daily rows inserted")


def _ingest_page_info(con, fb, portal_id, page_id):
    info = fb.get_page_info()

    con.execute(
        """INSERT INTO raw_fb_page_info
           (portal_id, page_id, followers_count, fan_count, ingested_at)
           VALUES (?, ?, ?, ?, now())""",
        [
            portal_id,
            page_id,
            info.get("followers_count", 0),
            info.get("fan_count", 0),
        ]
    )
    print(f"[FB/{portal_id}] page_info: followers={info.get('followers_count')}")


def _ingest_posts(con, fb, portal_id):
    raw = fb.get_recent_posts(limit=100)
    posts = raw.get("data", [])
    if not posts:
        print(f"[FB/{portal_id}] posts: no posts returned")
        return

    inserted = 0
    for p in posts:
        try:
            created = p.get("created_time", "")[:10]
            reac = p.get("reactions") or p.get("likes") or {}
            likes = 0
            if isinstance(reac, dict):
                if "summary" in reac:
                    likes = reac["summary"].get("total_count", 0)
                else:
                    likes = reac.get("total_count", 0)

            comments = 0
            comments_data = p.get("comments", {})
            if isinstance(comments_data, dict):
                comments = comments_data.get("summary", {}).get("total_count", 0)

            shares = 0
            shares_data = p.get("shares", {})
            if isinstance(shares_data, dict):
                shares = shares_data.get("count", 0)

            con.execute(
                """INSERT INTO raw_fb_posts
                   (portal_id, post_id, created_date, message,
                    reactions_count, comments_count, shares_count, ingested_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, now())""",
                [
                    portal_id,
                    p.get("id", ""),
                    created,
                    (p.get("message") or "")[:500],
                    likes,
                    comments,
                    shares,
                ]
            )
            inserted += 1
        except Exception as e:
            print(f"[FB/{portal_id}] post {p.get('id')}: {e}")

    print(f"[FB/{portal_id}] posts: {inserted}/{len(posts)} inserted")
