"""
Collectors "espejo" que leen del warehouse (MotherDuck) replicando la MISMA
interfaz que collectors.facebook / collectors.instagram.

Permiten servir el panel desde la base (instantáneo) sin pegar a la API. Los
métodos devuelven exactamente los mismos shapes que consumen las páginas, así
el cambio en cada consumidor es solo elegir la fuente (ver config.fb_source /
config.ig_source).

No necesitan token de Meta; sí el de MotherDuck (en el entorno o secrets).
"""
from warehouse.db import get_connection, portal_id as _portal_id

# Conexión de solo-lectura compartida (se abre una vez por sesión/proceso).
_con = None


def _ro():
    global _con
    if _con is None:
        _con = get_connection(read_only=True)
    return _con


def _q(sql, params=None):
    """Ejecuta una consulta; si la conexión se cayó, la reabre y reintenta una vez."""
    global _con
    try:
        return _ro().execute(sql, params or []).fetchall()
    except Exception:
        _con = None
        return _ro().execute(sql, params or []).fetchall()


def _d(date_val):
    """date/datetime de DuckDB -> 'YYYY-MM-DD' (como devuelve la API)."""
    return date_val.strftime("%Y-%m-%d") if date_val is not None else ""


# ════════════════════════════════ FACEBOOK ════════════════════════════════
class WarehouseFacebookCollector:
    def __init__(self, nombre=None, page_id=None, access_token=None):
        self.nombre = nombre
        self.portal_id = _portal_id(nombre) if nombre else None
        self.page_id = page_id

    def get_page_info(self):
        # Tomamos el último snapshot con followers > 0: la ingesta hace DELETE→INSERT
        # y, si el cache del app cae en esa ventana, un 0 transitorio quedaría pegado.
        rows = _q(
            """SELECT followers_count, fan_count FROM fb_page_info_daily
               WHERE portal_id = ? AND COALESCE(followers_count, 0) > 0
               ORDER BY snapshot_date DESC LIMIT 1""",
            [self.portal_id])
        if rows:
            f, fan = rows[0]
            return {"followers_count": int(f or 0), "fan_count": int(fan or 0)}
        return {"followers_count": 0, "fan_count": 0}

    def get_posts_impressions(self, limit=25):
        daily_rows = _q(
            """SELECT metric_date, metric_value FROM fb_page_insights
               WHERE portal_id = ? AND metric_name = 'page_impressions_unique'
               ORDER BY metric_date""", [self.portal_id])
        daily = {_d(r[0]): int(r[1]) for r in daily_rows}
        alcance = sum(daily.values())   # total = suma del diario (igual que la API)

        eng = _q(
            """SELECT sum(metric_value) FROM fb_page_insights
               WHERE portal_id = ? AND metric_name = 'page_post_engagements'""",
            [self.portal_id])
        engagement = int(eng[0][0] or 0) if eng and eng[0][0] is not None else 0

        vis = _q(
            """SELECT metric_value FROM fb_page_insights
               WHERE portal_id = ? AND metric_name = 'page_views_total'
               ORDER BY metric_date DESC LIMIT 1""", [self.portal_id])
        vistas = int(vis[0][0]) if vis else 0

        # Reproducciones de video (reels/videos): suma del diario, igual que la API.
        vv_rows = _q(
            """SELECT metric_date, metric_value FROM fb_page_insights
               WHERE portal_id = ? AND metric_name = 'page_video_views'
               ORDER BY metric_date""", [self.portal_id])
        daily_video = {_d(r[0]): int(r[1]) for r in vv_rows}
        video_views = sum(daily_video.values())

        return {"total_imp": alcance, "total_reach": alcance, "daily": daily,
                "engagement": engagement, "vistas": vistas,
                "video_views": video_views, "daily_video_views": daily_video,
                "posts_error": ""}

    def get_recent_posts(self, limit=30):
        rows = _q(
            """SELECT post_id, created_date, message, reactions_count,
                      comments_count, shares_count FROM fb_posts
               WHERE portal_id = ? ORDER BY created_date DESC LIMIT ?""",
            [self.portal_id, limit])
        data = []
        for pid, created, msg, reac, com, sh in rows:
            data.append({
                "id":           pid,
                "created_time": _d(created),
                "message":      msg or "",
                "reactions":    {"summary": {"total_count": int(reac or 0)}},
                "comments":     {"summary": {"total_count": int(com or 0)}},
                "shares":       {"count": int(sh or 0)},
            })
        return {"data": data}

    def get_fan_growth(self):
        rows = _q(
            """SELECT metric_date, new_follows FROM fb_fan_growth
               WHERE portal_id = ? ORDER BY metric_date""", [self.portal_id])
        values = [{"end_time": _d(r[0]), "value": int(r[1] or 0)} for r in rows]
        return {"data": [{"name": "page_daily_follows", "values": values}]}


# ════════════════════════════════ INSTAGRAM ═══════════════════════════════
class WarehouseInstagramCollector:
    def __init__(self, nombre=None, ig_id=None, access_token=None):
        self.nombre = nombre
        self.portal_id = _portal_id(nombre) if nombre else None
        self.ig_id = ig_id

    def get_account_info(self):
        # Último snapshot con followers > 0 (ver nota en FB.get_page_info): evita que
        # un 0 transitorio de la ventana de ingesta quede cacheado como en La Calle.
        rows = _q(
            """SELECT followers_count, follows_count, media_count
               FROM ig_account_info_daily
               WHERE portal_id = ? AND COALESCE(followers_count, 0) > 0
               ORDER BY snapshot_date DESC LIMIT 1""", [self.portal_id])
        if rows:
            f, fo, mc = rows[0]
            return {"followers_count": int(f or 0), "follows_count": int(fo or 0),
                    "media_count": int(mc or 0)}
        return {"followers_count": 0, "follows_count": 0, "media_count": 0}

    def _daily(self, metric_name):
        rows = _q(
            """SELECT metric_date, metric_value FROM ig_account_insights
               WHERE portal_id = ? AND metric_name = ? ORDER BY metric_date""",
            [self.portal_id, metric_name])
        return {_d(r[0]): int(r[1]) for r in rows}

    def _latest(self, metric_name):
        rows = _q(
            """SELECT metric_value FROM ig_account_insights
               WHERE portal_id = ? AND metric_name = ?
               ORDER BY metric_date DESC LIMIT 1""", [self.portal_id, metric_name])
        return int(rows[0][0]) if rows else 0

    def _posts_data(self):
        rows = _q(
            """SELECT post_id, published_date, content_type, media_type,
                      plays, reach, like_count, comments_count, permalink, caption
               FROM ig_posts WHERE portal_id = ?""", [self.portal_id])
        out = []
        for pid, pub, ctype, mtype, plays, reach, likes, com, perm, cap in rows:
            out.append({
                "id":        pid,
                "ts":        _d(pub),
                "tipo":      ctype or (mtype or "").lower(),
                "plays":     int(plays or 0),
                "reach":     int(reach or 0),
                "likes":     int(likes or 0),
                "comments":  int(com or 0),
                "permalink": perm or "",
                "caption":   (cap or "")[:60],
            })
        return out

    def get_media_impressions(self, limit=25, days=30):
        daily_alcance  = self._daily("reach")
        total_reach    = sum(daily_alcance.values())   # = 'alcance' de la API
        views          = self._latest("views")
        posts_data     = self._posts_data()
        return {
            "total_imp":       views or total_reach,
            "total_reach":     total_reach,
            "daily":           daily_alcance,
            "daily_posts":     posts_data,
            "engaged":         self._latest("total_interactions"),
            "posts_data":      posts_data,
            "daily_followers": self._daily("follower_count"),
        }

    def get_all_media(self, max_posts=500):
        # Ordenamos por visualizaciones (plays o reach) DESC antes del LIMIT: si un
        # portal tiene más de max_posts publicaciones, sin ORDER BY el LIMIT dejaba
        # afuera posts arbitrarios —incluido el reel más visto (p.ej. el del
        # terremoto de La Calle)— y así no entraba al Top 10.
        rows = _q(
            """SELECT post_id, caption, media_type, product_type,
                      published_date, like_count, comments_count, permalink
               FROM ig_posts WHERE portal_id = ?
               ORDER BY GREATEST(COALESCE(plays, 0), COALESCE(reach, 0)) DESC
               LIMIT ?""",
            [self.portal_id, max_posts])
        data = []
        for pid, cap, mtype, ptype, pub, likes, com, perm in rows:
            data.append({
                "id":             pid,
                "caption":        cap or "",
                "media_type":     mtype or "IMAGE",
                "product_type":   ptype or "",
                "timestamp":      _d(pub),
                "like_count":     int(likes or 0),
                "comments_count": int(com or 0),
                "permalink":      perm or "",
            })
        return {"data": data}
