import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


def _es_error_permiso(e):
    """¿El error de la API es por permisos/scopes faltantes del token? (code 10
    o code 190 / 'permission'). Si lo es, no sirve reintentar otros endpoints.

    OJO: anclamos con ':' ("code 10:") porque el mensaje tiene formato
    "code {n}: ..."; sin el ':' la subcadena "code 10" matchea "code 100"
    (parámetro inválido / métrica deprecada), que NO es un problema de token y
    no debe abortar la recolección de insights."""
    msg = str(e).lower()
    return ("code 190:" in msg or "code 10:" in msg or "permission" in msg
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

        La Batch API admite hasta 50 sub-requests por llamada, así que recorremos
        TODOS los posts en lotes de 50 (antes solo se enriquecían los primeros 50).
        """
        import json as _json
        for start in range(0, len(posts), 50):
            chunk = posts[start:start + 50]   # slicing comparte las mismas dicts
            try:
                batch = [
                    {"method": "GET",
                     "relative_url": f"{p['id']}?fields=reactions.summary(true),comments.summary(true),shares"}
                    for p in chunk
                ]
                r = requests.post(
                    self.base_url,
                    params={"access_token": self.access_token},
                    json={"batch": batch}
                )
                if not r.ok:
                    continue
                for i, resp in enumerate(r.json() or []):
                    if i >= len(chunk):
                        break
                    if resp and resp.get("code") == 200:
                        try:
                            data = _json.loads(resp.get("body", "{}"))
                            if data.get("reactions"):
                                chunk[i]["reactions"] = data["reactions"]
                            if data.get("comments"):
                                chunk[i]["comments"] = data["comments"]
                            if data.get("shares"):
                                chunk[i]["shares"] = data["shares"]
                        except Exception:
                            pass
            except Exception as e:
                print(f"[FB] ✗ Batch reactions error (lote {start}): {e}")
        enriched = sum(1 for p in posts if p.get("reactions") or p.get("comments"))
        print(f"[FB] ✓ Batch reactions enriched {enriched}/{len(posts)} posts")

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
        Métricas de página (API v25.0). Meta está deprecando varias métricas de
        página (page_impressions_unique entre ellas, jun 2026). Para el ALCANCE
        probamos una lista de candidatos y usamos el primero que devuelva datos;
        si ninguno responde, caemos a page_views_total como proxy de actividad
        para no mostrar 0.
        """
        since = int((datetime.now() - timedelta(days=30)).timestamp())
        until = int(datetime.now().timestamp())

        result = {
            "alcance":            0,   # personas únicas alcanzadas (reach)
            "engagement":         0,   # page_post_engagements
            "vistas":             0,   # page_views_total (vistas de PERFIL, chico)
            "video_views":        0,   # page_video_views (reproducciones de contenido)
            "daily_alcance":      {},
            "daily_engagement":   {},
            "daily_vistas":       {},
            "daily_video_views":  {},
        }

        def _serie(metric):
            """Devuelve (total, {fecha: valor}) o (None, {}) si la métrica falla."""
            resp  = self._get(f"{self.page_id}/insights", {
                "metric": metric, "period": "day", "since": since, "until": until})
            datos = resp.get("data", [])
            vals  = datos[0].get("values", []) if datos else []
            total = sum(v.get("value", 0) for v in vals)
            daily = {v["end_time"][:10]: v.get("value", 0)
                     for v in vals if v.get("value", 0) > 0}
            return total, daily

        # ── Alcance: page_impressions_unique fue deprecada por Meta (jun 2026).
        # La intentamos UNA vez; si responde, la usamos; si no, más abajo caemos a
        # page_views_total como proxy. Sus variantes organic/viral también están
        # deprecadas: no las probamos para no llenar el log de "errores" que no lo son.
        token_muerto = False
        try:
            total, daily = _serie("page_impressions_unique")
            if daily:
                result["alcance"], result["daily_alcance"] = total, daily
                print("[FB] ✓ alcance vía page_impressions_unique")
        except Exception as e:
            if _es_error_permiso(e):
                print("[FB] token inválido/expirado: corto page insights.")
                token_muerto = True
            else:
                print("[FB] alcance: page_impressions_unique deprecada por Meta; "
                      "uso page_views_total como proxy.")

        # ── Engagement, vistas de perfil y REPRODUCCIONES de video (vigentes) ──
        # page_video_views = reproducciones de reels/videos: es la métrica de
        # consumo de contenido grande (la app de Meta la muestra como parte de
        # "Visualizaciones"), a diferencia de page_views_total (vistas de PERFIL).
        for metric, total_key, daily_key in (
                ("page_post_engagements", "engagement",  "daily_engagement"),
                ("page_views_total",      "vistas",      "daily_vistas"),
                ("page_video_views",      "video_views", "daily_video_views")):
            if token_muerto:
                break
            try:
                total, daily = _serie(metric)
                result[total_key] = total
                result[daily_key] = daily
                print(f"[FB] ✓ page insights: {metric} OK")
            except Exception as e:
                print(f"[FB] ✗ page insights {metric}: {e}")
                if _es_error_permiso(e):
                    print("[FB] token inválido/expirado: corto page insights.")
                    break

        # ── Fallback: si el alcance quedó en 0 (métrica deprecada) pero hay
        # vistas, las usamos como proxy para que el panel no muestre 0. ──
        if not result["alcance"] and result["vistas"]:
            result["alcance"]       = result["vistas"]
            result["daily_alcance"] = result["daily_vistas"]
            print("[FB] alcance no disponible; uso page_views_total como proxy.")

        return result

    def get_posts_impressions(self, limit=25):
        """
        Devuelve alcance e impresiones usando page-level insights (v25.0).
        post_impressions fue deprecada; page_impressions_unique es la métrica disponible.
        """
        insights = self.get_page_insights()
        return {
            "total_imp":         insights["alcance"],
            "total_reach":       insights["alcance"],
            "daily":             insights["daily_alcance"],
            "engagement":        insights["engagement"],
            "vistas":            insights["vistas"],
            "video_views":       insights["video_views"],
            "daily_video_views": insights["daily_video_views"],
            "posts_error":       "",
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
