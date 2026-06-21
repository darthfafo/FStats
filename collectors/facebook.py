import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


def _es_error_permiso(e):
    """¿El error de la API es por permisos/scopes faltantes del token? (code 10
    o code 190 / 'permission'). Si lo es, no sirve reintentar otros endpoints."""
    msg = str(e).lower()
    return ("code 190" in msg or "code 10" in msg or "permission" in msg
            or "must be granted" in msg)


class FacebookCollector:
    def __init__(self, page_id=None, access_token=None):
        self.page_id           = page_id      or os.getenv("META_PAGE_ID")
        self.system_user_token = access_token or os.getenv("META_PAGE_ACCESS_TOKEN")
        self.access_token      = self.system_user_token
        self.base_url          = "https://graph.facebook.com/v25.0"
        # Intercambiar System User Token por Page Access Token
        self._upgrade_to_page_token()

    def _upgrade_to_page_token(self):
        """
        El System User Token no puede leer posts/feed directamente.
        Obtener el Page Access Token usando el System User Token.
        """
        try:
            r = requests.get(
                f"{self.base_url}/{self.page_id}",
                params={"fields": "access_token", "access_token": self.system_user_token}
            )
            if r.ok and "access_token" in r.json():
                self.access_token = r.json()["access_token"]
                print("[FB] ✓ Page Access Token obtenido")
            else:
                err = r.json().get("error", {})
                print(f"[FB] ⚠️  No se pudo obtener Page Token: {err.get('message')} — usando System User Token")
        except Exception as e:
            print(f"[FB] ⚠️  Error al obtener Page Token: {e}")

    def _get(self, endpoint, params=None):
        if params is None:
            params = {}
        params["access_token"] = self.access_token
        r = requests.get(f"{self.base_url}/{endpoint}", params=params)
        if not r.ok:
            try:
                err = r.json().get("error", {})
                raise requests.HTTPError(
                    f"[{r.status_code}] code {err.get('code')}: {err.get('message')}",
                    response=r
                )
            except (ValueError, KeyError):
                r.raise_for_status()
        return r.json()

    def get_page_info(self):
        r = requests.get(
            f"{self.base_url}/{self.page_id}",
            params={
                "fields":       "id,name,fan_count,followers_count,category",
                "access_token": self.system_user_token
            }
        )
        r.raise_for_status()
        return r.json()

    def _enrich_with_reactions(self, posts):
        """
        Para páginas NPE donde /posts?fields=reactions falla, usa la Batch API
        para obtener reactions de cada post individualmente.
        """
        import json as _json
        try:
            batch = [
                {"method": "GET",
                 "relative_url": f"{p['id']}?fields=reactions.summary(true),comments.summary(true),shares"}
                for p in posts[:50]
            ]
            r = requests.post(
                self.base_url,
                params={"access_token": self.access_token},
                json={"batch": batch}
            )
            if not r.ok:
                return
            responses = r.json()
            for i, resp in enumerate(responses or []):
                if i >= len(posts):
                    break
                if resp and resp.get("code") == 200:
                    try:
                        data = _json.loads(resp.get("body", "{}"))
                        if data.get("reactions"):
                            posts[i]["reactions"] = data["reactions"]
                        if data.get("comments"):
                            posts[i]["comments"] = data["comments"]
                        if data.get("shares"):
                            posts[i]["shares"] = data["shares"]
                    except Exception:
                        pass
            enriched = sum(1 for p in posts if p.get("reactions") or p.get("comments"))
            print(f"[FB] ✓ Batch reactions enriched {enriched}/{len(posts)} posts")
        except Exception as e:
            print(f"[FB] ✗ Batch reactions error: {e}")

    def get_recent_posts(self, limit=30):
        """
        Obtiene posts recientes con reactions.
        Para páginas NPE donde el endpoint bulk falla, usa Batch API
        para obtener reactions post por post.
        """
        # Intentar primero con reactions incluidas en el mismo request
        intentos_con_reac = [
            (f"{self.page_id}/posts",
             "id,message,created_time,reactions.summary(true),comments.summary(true),shares"),
            (f"{self.page_id}/posts",
             "id,message,created_time,likes.summary(true),comments.summary(true),shares"),
            (f"{self.page_id}/feed",
             "id,message,created_time,reactions.summary(true),comments.summary(true),shares"),
        ]
        for endpoint, fields in intentos_con_reac:
            try:
                result = self._get(endpoint, {"fields": fields, "limit": limit})
                if result.get("data"):
                    has_reac = any(p.get("reactions") or p.get("likes") for p in result["data"])
                    if has_reac:
                        print(f"[FB] ✓ Posts con reactions OK — {len(result['data'])} posts")
                        return result
            except Exception as e:
                print(f"[FB] ✗ {endpoint} con reactions: {e}")
                if _es_error_permiso(e):
                    print("[FB] El token no tiene permisos para leer los posts de la "
                          "página (pages_read_engagement / pages_read_user_content). "
                          "Se omiten los posts.")
                    return {"data": [], "error": str(e)}

        # Si falla, obtener posts sin reactions y luego enriquecer con Batch API
        intentos_basicos = [
            (f"{self.page_id}/posts", "id,message,created_time,comments.summary(true),shares"),
            (f"{self.page_id}/posts", "id,message,created_time"),
            (f"{self.page_id}/feed",  "id,message,created_time"),
        ]
        last_error = ""
        for endpoint, fields in intentos_basicos:
            try:
                result = self._get(endpoint, {"fields": fields, "limit": limit})
                if result.get("data") is not None:
                    print(f"[FB] ✓ Posts sin reactions — {len(result['data'])} posts, intentando batch enrichment")
                    self._enrich_with_reactions(result["data"])
                    return result
            except Exception as e:
                last_error = str(e)
                print(f"[FB] ✗ {endpoint}: {e}")
        return {"data": [], "error": last_error}

    def get_page_insights(self):
        """
        Métricas de página disponibles en API v25.0.
        Nota: page_impressions fue deprecada; usamos page_impressions_unique (alcance único).
        """
        since = int((datetime.now() - timedelta(days=30)).timestamp())
        until = int(datetime.now().timestamp())

        result = {
            "alcance":          0,   # page_impressions_unique
            "engagement":       0,   # page_post_engagements
            "vistas":           0,   # page_views_total
            "daily_alcance":    {},
            "daily_engagement": {},
        }

        metricas = [
            "page_impressions_unique",
            "page_post_engagements",
            "page_views_total",
        ]

        for metric in metricas:
            try:
                resp = self._get(f"{self.page_id}/insights", {
                    "metric": metric,
                    "period": "day",
                    "since":  since,
                    "until":  until,
                })
                for m in resp.get("data", []):
                    vals  = m.get("values", [])
                    total = sum(v.get("value", 0) for v in vals)
                    daily = {
                        v["end_time"][:10]: v.get("value", 0)
                        for v in vals if v.get("value", 0) > 0
                    }
                    name = m["name"]
                    if name == "page_impressions_unique":
                        result["alcance"]       = total
                        result["daily_alcance"] = daily
                    elif name == "page_post_engagements":
                        result["engagement"]       = total
                        result["daily_engagement"] = daily
                    elif name == "page_views_total":
                        result["vistas"] = total
                print(f"[FB] ✓ page insights: {metric} OK")
            except Exception as e:
                print(f"[FB] ✗ page insights {metric}: {e}")

        return result

    def get_posts_impressions(self, limit=25):
        """
        Devuelve alcance e impresiones usando page-level insights (v25.0).
        post_impressions fue deprecada; page_impressions_unique es la métrica disponible.
        """
        insights = self.get_page_insights()
        return {
            "total_imp":   insights["alcance"],
            "total_reach": insights["alcance"],
            "daily":       insights["daily_alcance"],
            "engagement":  insights["engagement"],
            "vistas":      insights["vistas"],
            "posts_error": "",
        }

    def get_fan_growth(self):
        """Intenta obtener crecimiento de seguidores (métricas disponibles en v25.0)."""
        since = int((datetime.now() - timedelta(days=30)).timestamp())
        until = int((datetime.now() - timedelta(days=1)).timestamp())
        # Probar métricas alternativas para fan growth
        for metric in ["page_daily_follows,page_daily_unfollows",
                        "page_follows",
                        "page_fan_adds_unique"]:
            try:
                result = self._get(f"{self.page_id}/insights", {
                    "metric": metric,
                    "period": "day",
                    "since":  since,
                    "until":  until,
                })
                if result.get("data"):
                    print(f"[FB] ✓ fan growth OK con {metric}")
                    return result
            except Exception as e:
                print(f"[FB] ✗ fan growth {metric}: {e}")
        return {"data": []}
