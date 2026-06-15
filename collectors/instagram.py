import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class InstagramCollector:
    def __init__(self, ig_id=None, access_token=None):
        self.ig_id        = ig_id        or os.getenv("META_INSTAGRAM_ID")
        self.access_token = access_token or os.getenv("META_PAGE_ACCESS_TOKEN")
        self.base_url     = "https://graph.facebook.com/v25.0"

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

    def get_account_info(self):
        return self._get(self.ig_id, {
            "fields": "id,name,username,biography,followers_count,follows_count,media_count"
        })

    def get_recent_media(self, limit=30):
        # El campo correcto es media_product_type = "REELS" para Reels (media_type
        # siempre devuelve "VIDEO"). Lo normalizamos a product_type para el resto.
        data = self._get(f"{self.ig_id}/media", {
            "fields": "id,caption,media_type,media_product_type,timestamp,like_count,comments_count,permalink",
            "limit":  limit
        })
        for m in data.get("data", []):
            m["product_type"] = m.get("media_product_type") or m.get("product_type") or ""
        return data

    def get_all_media(self, max_posts=500):
        """Pagina por todos los posts para encontrar el top histórico por likes."""
        all_posts = []
        params = {
            "fields": "id,caption,media_type,media_product_type,timestamp,like_count,comments_count,permalink",
            "limit": 100,
            "access_token": self.access_token,
        }
        url = f"{self.base_url}/{self.ig_id}/media"
        while url and len(all_posts) < max_posts:
            r = requests.get(url, params=params)
            if not r.ok:
                break
            data = r.json()
            all_posts.extend(data.get("data", []))
            next_url = data.get("paging", {}).get("next")
            url = next_url
            params = {}  # la URL "next" ya trae todos los params
        for m in all_posts:
            m["product_type"] = m.get("media_product_type") or m.get("product_type") or ""
        print(f"[IG] get_all_media: {len(all_posts)} posts obtenidos")
        return {"data": all_posts[:max_posts]}

    def get_media_url(self, post_id):
        """
        URL del archivo de media de un post propio (Graph API).

        Para Reels/videos devuelve el mp4 servido por el CDN de Meta. La URL es
        firmada y EXPIRA, así que hay que descargar el archivo en el momento.
        Devuelve dict con {media_url, thumbnail_url, media_type, product_type}.
        """
        data = self._get(post_id, {
            "fields": "media_url,thumbnail_url,media_type,product_type"
        })
        return {
            "media_url":     data.get("media_url", ""),
            "thumbnail_url": data.get("thumbnail_url", ""),
            "media_type":    data.get("media_type", ""),
            "product_type":  data.get("product_type", ""),
        }

    def get_account_insights(self):
        """
        Métricas a nivel de cuenta Instagram (v25.0).
        Dos tipos de métricas según la API:
          - time_series: usan period=day + since/until → devuelven values[] con valores diarios
          - total_value: necesitan metric_type=total_value → devuelven total_value.value
        """
        since = int((datetime.now() - timedelta(days=30)).timestamp())
        until = int(datetime.now().timestamp())

        result = {
            "views":         0,   # visualizaciones totales (Reels plays + videos + fotos)
            "alcance":       0,   # reach — personas únicas
            "engaged":       0,   # accounts_engaged
            "vistas_perfil": 0,   # profile_views
            "total_inter":   0,   # total_interactions
            "daily_views":   {},
            "daily_alcance": {},
        }

        result["daily_followers"] = {}

        # ── 1. Métricas time-series (period=day) ───────────────────
        for metric in ["reach", "follower_count"]:
            try:
                resp = self._get(f"{self.ig_id}/insights", {
                    "metric": metric,
                    "period": "day",
                    "since":  since,
                    "until":  until,
                })
                for m in resp.get("data", []):
                    vals  = m.get("values", [])
                    total = sum(v.get("value", 0) for v in vals)
                    daily = {v["end_time"][:10]: v.get("value", 0)
                             for v in vals if v.get("value", 0) > 0}
                    name  = m["name"]
                    if name == "reach":
                        result["alcance"]       = total
                        result["daily_alcance"] = daily
                    elif name == "follower_count":
                        result["daily_followers"] = daily
                    elif name == "total_interactions":
                        result["total_inter"]   = total
                print(f"[IG] ✓ account insights (time_series): {metric} = {total:,}")
            except Exception as e:
                print(f"[IG] ✗ account insights {metric}: {e}")

        # ── 2. Métricas total_value (metric_type=total_value) ───────
        # views = "Visualizaciones" del panel profesional IG (plays de Reels + videos + fotos)
        for metric in ["views", "total_interactions", "accounts_engaged", "profile_views"]:
            try:
                resp = self._get(f"{self.ig_id}/insights", {
                    "metric":      metric,
                    "metric_type": "total_value",
                    "period":      "day",
                    "since":       since,
                    "until":       until,
                })
                for m in resp.get("data", []):
                    name = m["name"]
                    # Formato total_value: {"total_value": {"value": N}}
                    # También puede venir en "values" normales según versión
                    if "total_value" in m:
                        tv    = m["total_value"]
                        total = tv.get("value", 0) if isinstance(tv, dict) else int(tv)
                    else:
                        vals  = m.get("values", [])
                        total = sum(
                            (v["value"].get("value", 0) if isinstance(v.get("value"), dict)
                             else v.get("value", 0))
                            for v in vals
                        )
                    if name == "views":
                        result["views"] = total
                    elif name == "total_interactions":
                        result["total_inter"] = total
                    elif name == "accounts_engaged":
                        result["engaged"] = total
                    elif name == "profile_views":
                        result["vistas_perfil"] = total
                print(f"[IG] ✓ account insights (total_value): {metric} = {total:,}")
            except Exception as e:
                print(f"[IG] ✗ account insights {metric}: {e}")

        return result

    def _get_media_metric(self, post_id, media_type, product_type=""):
        """
        Intenta obtener métricas de un post individual.
        Detecta Reels por media_product_type="REELS" (media_type siempre es "VIDEO").
        Devuelve (imp, reach) o (0, 0). imp = views (reproducciones) en Reels.
        """
        es_reel = (str(media_type).upper() in ("REEL", "REELS")) or \
                  (str(product_type).upper() in ("CLIPS", "REELS"))

        if es_reel:
            # 'plays' fue deprecado en Reels (abr 2025) → la métrica es 'views'.
            intentos = [
                "views,reach",
                "ig_reels_aggregated_all_plays_count,reach",
                "plays,reach",
                "reach,total_interactions",
                "reach",
            ]
            imp_keys = {"views", "ig_reels_aggregated_all_plays_count", "plays"}
            tipo_label = "REEL"
        elif str(media_type).upper() == "VIDEO":
            intentos = [
                "views,reach",
                "reach,total_interactions",
                "reach",
            ]
            imp_keys = {"views", "total_interactions"}
            tipo_label = "VIDEO"
        else:
            # IMAGE, CAROUSEL_ALBUM
            intentos = [
                "reach,saved",
                "reach,total_interactions",
                "reach",
            ]
            imp_keys = {"saved", "total_interactions"}
            tipo_label = media_type

        for metrics in intentos:
            try:
                resp = self._get(f"{post_id}/insights", {"metric": metrics})
                imp = reach = 0
                for m in resp.get("data", []):
                    vals = m.get("values", [])
                    if vals:
                        val = vals[0].get("value", 0)
                    elif isinstance(m.get("total_value"), dict):
                        val = m["total_value"].get("value", 0)   # forma total_value (p.ej. views)
                    else:
                        val = m.get("value", 0)
                    name = m["name"]
                    if name in imp_keys:
                        imp = val
                    elif name == "reach":
                        reach = val
                print(f"[IG] ✓ {tipo_label} OK con {metrics} → imp={imp}, reach={reach}")
                return imp, reach
            except Exception as e:
                print(f"[IG] ✗ {tipo_label} / {metrics}: {e}")

        return 0, 0

    def get_media_impressions(self, limit=25, days=30):
        """
        Estrategia:
        - Totales (hero): siempre usa account-level insights (reach de cuenta = métrica real 30d).
        - Gráfico diario: usa reach por post (media-level), más granular.
        - Reels: usa ig_reels_aggregated_all_plays_count para el gráfico diario.
        - posts_data: lista por post con plays/reach/likes para gráficos de top contenidos.
        - days: ventana de dias a considerar (default 30, extender para cubrir posts mas antiguos).
        """
        media      = self.get_recent_media(limit=limit)
        daily      = {}
        posts_data = []
        limite     = datetime.now() - timedelta(days=days)

        # ── Gráfico diario + datos por post ─────────────────────────
        for post in media.get("data", []):
            ts           = post.get("timestamp", "")[:10]
            media_type   = post.get("media_type", "IMAGE")
            product_type = post.get("product_type", "")
            is_reel      = (product_type == "clips" or media_type == "REEL")
            try:
                fecha = datetime.strptime(ts, "%Y-%m-%d")
                if fecha < limite:
                    continue
                imp, reach = self._get_media_metric(post["id"], media_type, product_type)
                val = imp if is_reel else reach
                if val > 0:
                    daily[ts] = daily.get(ts, 0) + val
                posts_data.append({
                    "id":        post.get("id", ""),   # ID exacto para matching
                    "ts":        ts,
                    "tipo":      "reel" if is_reel else media_type.lower(),
                    "plays":     imp,
                    "reach":     reach,
                    "likes":     post.get("like_count", 0),
                    "comments":  post.get("comments_count", 0),
                    "permalink": post.get("permalink", ""),
                    "caption":   (post.get("caption") or "")[:60],
                })
            except Exception as e:
                print(f"[IG] post {post.get('id')}: {e}")

        # ── Totales: account-level (siempre más preciso) ─────────────
        acc = self.get_account_insights()
        total_imp   = acc.get("views", 0) or acc.get("alcance", 0)
        total_reach = acc.get("alcance", 0)

        # daily_alcance de account insights cubre los 30 días completos (un valor por día).
        # El 'daily' de posts es esparso (solo días con publicaciones nuevas).
        # Siempre preferimos el account-level para el gráfico de tendencia.
        daily_account = acc.get("daily_alcance", {})
        if daily_account:
            daily = daily_account   # cobertura completa: 30 datos diarios
        elif not daily:
            daily = {}              # sin datos en ninguna fuente

        return {
            "total_imp":       total_imp,
            "total_reach":     total_reach,
            "daily":           daily,          # ahora = account-level reach diario
            "daily_posts":     posts_data,     # datos por post para otros usos
            "engaged":         acc.get("total_inter", 0),
            "posts_data":      posts_data,
            "daily_followers": acc.get("daily_followers", {}),
        }
