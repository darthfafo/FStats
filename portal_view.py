"""
Vista unificada de un portal (la misma para las 5 páginas de portal).

Estructura: hero con el total de visualizaciones, luego Instagram COMPLETO
(KPIs + gráficos + contenido) y, abajo, Facebook COMPACTO (KPIs + crecimiento de
seguidores). Instagram va primero porque concentra casi toda la data; Facebook
quedó acotado porque Meta le sacó el alcance de página.

Las 5 páginas pages/1..5 solo llaman a mostrar_portal("<nombre>").
"""
import html

import streamlit as st
import pandas as pd
import plotly.express as px

from config import PORTALES, fb_source, ig_source
import warehouse.reader as _wr

_PEND = ("PENDIENTE", "", None)


def _portal(nombre):
    return next((p for p in PORTALES if p["nombre"] == nombre), None)


@st.cache_data(ttl=3600, show_spinner=False)
def _cargar_ig(nombre, ig_id, token, live):
    ig = ig_source(nombre, ig_id, token, live)
    return {
        "info":        ig.get_account_info(),
        "impresiones": ig.get_media_impressions(limit=25),
        "media":       ig.get_all_media(max_posts=500),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def _cargar_fb(nombre, page_id, token, live):
    fb = fb_source(nombre, page_id, token, live)
    return {
        "info":        fb.get_page_info(),
        "impresiones": fb.get_posts_impressions(),
        "fan_growth":  fb.get_fan_growth(),
        "posts":       fb.get_recent_posts(limit=100),
    }


def _kpis(items):
    """items: lista de (label, valor_str, sub). Renderiza tarjetas KPI azules."""
    cards = "".join(
        f'<div class="kpi-card"><div class="k-label">{l}</div>'
        f'<div class="k-value">{v}</div><div class="k-sub">{s}</div></div>'
        for l, v, s in items)
    st.markdown(f'<div class="kpi-grid">{cards}</div>', unsafe_allow_html=True)


# ── Tarjeta de ranking (Top 10): rank + meta + título + KPIs + copy expandible.
# Compartida entre las páginas de portal y Estadísticas Globales. ──────────────
# La tarjeta tiene FONDO OSCURO PROPIO (isla oscura), igual que los banners/KPI:
# así el texto claro se lee bien tanto en tema claro como oscuro de Streamlit.
TOP_CSS = """
<style>
.tp-card { background:linear-gradient(135deg,#0f172a,#1e1b4b);
           border:1px solid rgba(148,163,184,0.18); border-radius:14px;
           padding:13px 18px; margin-bottom:10px; }
.tp-row { display:flex; flex-wrap:wrap; align-items:center; gap:8px 16px; }
.tp-rank { font-size:1.7rem; font-weight:900; color:#c084fc; min-width:42px; line-height:1; }
.tp-main { flex:1 1 220px; min-width:170px; }
.tp-meta { color:#cbd5e1; font-size:0.82rem; margin-bottom:3px; }
.tp-meta a { color:#c084fc; text-decoration:none; font-weight:600; }
.tp-title { color:#f1f5f9; font-size:0.98rem; font-weight:600; line-height:1.3; }
.tp-stat { text-align:center; min-width:62px; }
.tp-stat b { display:block; color:#fff; font-size:1.15rem; font-weight:800; line-height:1.1; white-space:nowrap; }
.tp-stat span { color:#cbd5e1; font-size:0.66rem; }
</style>
"""


def tarjeta_ranking(rank, meta_html, titulo, stats, copy_full=None):
    """Una tarjeta de ranking. stats: lista de (emoji, valor_str, etiqueta).
    meta_html ya viene como HTML (puede traer un <a> con el link)."""
    LIM = 110
    titulo = titulo or ""
    corto  = html.escape(titulo[:LIM].rstrip()) + ("…" if len(titulo) > LIM else "")
    stats_html = "".join(
        f'<div class="tp-stat">{e}<b>{v}</b><span>{l}</span></div>' for e, v, l in stats)
    st.markdown(
        f'<div class="tp-card"><div class="tp-row"><div class="tp-rank">#{rank}</div>'
        f'<div class="tp-main"><div class="tp-meta">{meta_html}</div>'
        f'<div class="tp-title">{corto}</div></div>{stats_html}</div></div>',
        unsafe_allow_html=True)
    if copy_full and len(copy_full) > LIM:
        with st.expander("📖 Leer descripción completa"):
            st.write(copy_full)


def mostrar_portal(nombre):
    portal = _portal(nombre)
    icono  = portal["icono"] if portal else "📊"
    st.title(f"{icono} {nombre}")
    st.markdown("---")

    if portal is None or portal.get("access_token") in _PEND or portal.get("instagram_id") in _PEND:
        st.info(f"**{nombre}** — pendiente de configuración (falta el token o el ID de Instagram).")
        st.stop()

    live = st.session_state.get("fstats_live", False)
    es_ig_only = portal.get("ig_only", False) or portal.get("facebook_page_id") in _PEND

    with st.spinner("Cargando estadísticas..."):
        try:
            datos_ig = _cargar_ig(nombre, portal["instagram_id"], portal["access_token"], live)
            err_ig = None
        except Exception as e:
            datos_ig = {"info": {}, "impresiones": {"total_imp": 0, "total_reach": 0,
                        "daily": {}, "daily_followers": {}, "posts_data": []}, "media": {"data": []}}
            err_ig = str(e)
        datos_fb, err_fb = None, None
        if not es_ig_only:
            try:
                datos_fb = _cargar_fb(nombre, portal["facebook_page_id"], portal["access_token"], live)
            except Exception as e:
                datos_fb = {"info": {}, "impresiones": {"total_imp": 0, "daily": {}, "vistas": 0,
                            "engagement": 0}, "fan_growth": {"data": []}, "posts": {"data": []}}
                err_fb = str(e)

    imp_ig       = datos_ig["impresiones"]
    imp_ig_total = imp_ig.get("total_imp", 0)
    imp_fb_total = datos_fb["impresiones"].get("total_imp", 0) if datos_fb else 0
    gran_total   = imp_ig_total + imp_fb_total
    fuentes      = "Instagram + Facebook" if not es_ig_only else "Instagram"

    seg_ig    = datos_ig["info"].get("followers_count", 0)
    seg_fb    = datos_fb["info"].get("followers_count", 0) if datos_fb else 0
    seg_total = seg_ig + seg_fb

    # ── HERO: total de visualizaciones ──────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0f172a,#3b0764);border-radius:16px;
                padding:24px 28px;margin-bottom:18px;text-align:center">
        <div style="color:#cbd5e1;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase">
            📊 Total visualizaciones — último mes</div>
        <div style="color:#fff;font-size:clamp(28px,7vw,58px);font-weight:900;line-height:1;margin:8px 0 4px">
            {gran_total:,}</div>
        <div style="color:#cbd5e1;font-size:13px">{fuentes}</div>
        <div style="color:#e9d5ff;font-size:15px;font-weight:700;margin-top:10px">
            👥 {seg_total:,} <span style="color:#cbd5e1;font-weight:500;font-size:13px">seguidores totales</span></div>
    </div>
    """, unsafe_allow_html=True)

    # ════════════════════════ INSTAGRAM (completo) ══════════════════════
    st.markdown('<div class="grupo-titulo">📸 Instagram</div>', unsafe_allow_html=True)
    if err_ig:
        st.error(f"⚠️ Error al cargar Instagram: {err_ig}")
    info_ig = datos_ig["info"]
    _kpis([
        ("👥 Seguidores",     f"{info_ig.get('followers_count', 0):,}", "Audiencia de Instagram"),
        ("▶️ Visualizaciones", f"{imp_ig_total:,}",                     "Reels + videos + fotos · 30d"),
        ("🎯 Alcance",        f"{imp_ig.get('total_reach', 0):,}",      "Personas únicas alcanzadas · 30d"),
        ("💬 Interacciones",  f"{imp_ig.get('engaged', 0):,}",          "Likes, comentarios y guardados · 30d"),
    ])

    col_izq, col_der = st.columns(2)
    with col_izq:
        st.subheader("📈 Alcance diario")
        if imp_ig.get("daily"):
            df = pd.DataFrame([{"Fecha": k, "Personas alcanzadas": v}
                               for k, v in sorted(imp_ig["daily"].items())])
            fig = px.line(df, x="Fecha", y="Personas alcanzadas",
                          color_discrete_sequence=["#c026d3"])
            fig.update_traces(fill="tozeroy", fillcolor="rgba(192,38,211,0.12)", line_width=2)
            fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Sin datos de alcance diario.")
    with col_der:
        st.subheader("👥 Nuevos seguidores por día")
        daily_seg = imp_ig.get("daily_followers", {})
        df_seg = pd.DataFrame([{"Fecha": k, "Nuevos seguidores": v}
                               for k, v in sorted(daily_seg.items()) if v > 0]) if daily_seg else pd.DataFrame()
        if not df_seg.empty:
            fig = px.bar(df_seg, x="Fecha", y="Nuevos seguidores",
                         color_discrete_sequence=["#c026d3"])
            fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Sin datos de seguidores por día.")

    # Evolución de visualizaciones por día (de las publicaciones de cada día).
    st.markdown("---")
    st.subheader("📈 Evolución de visualizaciones por día")
    try:
        _pv = _wr.posts(nombre, "ig")
    except Exception:
        _pv = None
    if _pv is not None and not _pv.empty and "published_date" in _pv.columns:
        _pv = _pv.assign(_d=pd.to_datetime(_pv["published_date"], errors="coerce"))
        _pv["_views"] = _pv["plays"].where(_pv["plays"] > 0, _pv["reach"])
        serie = (_pv.dropna(subset=["_d"]).groupby(_pv["_d"].dt.date)["_views"].sum()
                    .sort_index())
        serie = serie[serie > 0]
        # Recortar la cola antigua y dispersa: arrancar DESPUÉS del último hueco
        # grande (>30 días), así el eje queda encuadrado en el período con datos
        # continuos y no se ve la rampa larga de posts viejos sueltos.
        fechas = list(serie.index)
        if len(fechas) > 2:
            inicio = fechas[0]
            for j in range(1, len(fechas)):
                if (pd.Timestamp(fechas[j]) - pd.Timestamp(fechas[j - 1])).days > 30:
                    inicio = fechas[j]
            serie = serie[[d >= inicio for d in serie.index]]
        if len(serie) >= 2:
            dfv = pd.DataFrame({"Fecha": pd.to_datetime(list(serie.index)),
                                "Visualizaciones": list(serie.values)})
            fig = px.line(dfv, x="Fecha", y="Visualizaciones", markers=True,
                          color_discrete_sequence=["#a855f7"])
            fig.update_traces(line_width=2, marker=dict(size=5))
            # Sin rangos fijos: dejamos AUTORANGO (= lo que hace el botón "autoscale"),
            # así carga ya encuadrado. La cola vieja ya se recortó arriba, por eso el
            # autorango del eje X arranca en el período con datos continuos.
            lay = dict(showlegend=False, margin=dict(l=0, r=0, t=10, b=0),
                       xaxis=dict(title="", autorange=True))
            vmin, vmax = serie.min(), serie.max()
            if vmin > 0 and vmax / vmin > 30:        # mucha varianza → escala log
                lay["yaxis"] = dict(type="log", title="visualizaciones",
                                    tickformat=".2s", autorange=True)
            else:
                lay["yaxis"] = dict(title="visualizaciones", tickformat=".2s", autorange=True)
            fig.update_layout(**lay)
            st.plotly_chart(fig, width='stretch')
            st.caption("Visualizaciones que acumulan las publicaciones según el día en que "
                       "se publicaron (plays de reels + reproducciones).")
        else:
            st.info("Todavía no hay suficientes días con visualizaciones para graficar la evolución.")
    else:
        st.info("Sin datos de publicaciones para la evolución de visualizaciones.")

    # Rendimiento por tipo de contenido — resumen compacto (los reels rinden más).
    st.markdown("---")
    st.subheader("📊 Rendimiento por tipo de contenido")
    all_media = datos_ig.get("media", {}).get("data", [])
    if all_media:
        tipos_map = {}
        for post in all_media:
            mt = post.get("media_type", "IMAGE")
            pt = post.get("product_type", "")
            if pt == "clips":            t = "🎬 Reel"
            elif mt == "VIDEO":          t = "▶️ Video"
            elif mt == "CAROUSEL_ALBUM": t = "🖼️ Carrusel"
            else:                        t = "📷 Imagen"
            tipos_map.setdefault(t, {"count": 0, "likes": 0})
            tipos_map[t]["count"] += 1
            tipos_map[t]["likes"] += post.get("like_count", 0)
        orden = sorted(tipos_map.items(),
                       key=lambda kv: (kv[1]["likes"] / kv[1]["count"]) if kv[1]["count"] else 0,
                       reverse=True)
        st.markdown("\n".join(
            f"- **{t}** — {d['count']:,} publicaciones · "
            f"**{round(d['likes'] / d['count']):,}** likes promedio · {d['likes']:,} likes totales"
            for t, d in orden))
        if orden:
            st.caption(f"El formato que más rinde por publicación es **{orden[0][0]}**.")
    else:
        st.info("Sin datos de contenido para resumir.")

    # Top 10 publicaciones de Instagram — tarjetas tipo ranking (hero + KPI), responsive.
    st.markdown("---")
    st.subheader("🏆 Top 10 publicaciones de Instagram")
    st.caption("Ordenadas por **visualizaciones** (difusión real), no por likes.")
    media_data = datos_ig.get("media", {})
    if media_data.get("data"):
        # Visualizaciones por post: del warehouse (cubre todos los posts ingestados),
        # con fallback a las métricas en vivo de los más recientes.
        try:
            _wp = _wr.posts(nombre, "ig")
            views_lookup = {str(r["post_id"]): int((r["plays"] or 0) or (r["reach"] or 0))
                            for _, r in _wp.iterrows()} if _wp is not None and not _wp.empty else {}
        except Exception:
            views_lookup = {}
        plays_lookup = {(p.get("id", "") or p.get("ts", "")): (p.get("plays", 0) or p.get("reach", 0))
                        for p in imp_ig.get("posts_data", [])}

        lista_ig = []
        for post in media_data["data"]:
            cap = post.get("caption", "") or "(Sin descripción)"
            mt  = post.get("media_type", "")
            pt  = post.get("product_type", "")
            if pt == "clips":            tl = "🎬 Reel"
            elif mt == "VIDEO":          tl = "▶️ Video"
            elif mt == "CAROUSEL_ALBUM": tl = "🖼️ Carrusel"
            else:                        tl = "📷 Imagen"
            pid   = post.get("id", "")
            views = (views_lookup.get(str(pid)) or plays_lookup.get(pid, 0)
                     or plays_lookup.get(post.get("timestamp", "")[:10], 0))
            lista_ig.append({
                "ts": post.get("timestamp", "")[:10], "tipo": tl, "cap": cap,
                "likes": post.get("like_count", 0),
                "com":   post.get("comments_count", 0),
                "views": int(views or 0),
                "link":  post.get("permalink", ""),
            })
        # Ordenamos por visualizaciones (difusión real) y, a igualdad, por likes:
        # así los reels más virales (p.ej. el del terremoto de La Calle) sí entran
        # al top, en vez de quedar afuera por tener menos likes que posts chicos.
        lista_ig.sort(key=lambda x: (x["views"], x["likes"]), reverse=True)

        st.markdown(TOP_CSS, unsafe_allow_html=True)
        for i, p in enumerate(lista_ig[:10], 1):
            tipo   = (f'<a href="{p["link"]}" target="_blank">{p["tipo"]}</a>'
                      if p["link"] else p["tipo"])
            vistas = f'{p["views"]:,}' if p["views"] else "—"
            tarjeta_ranking(i, f'📅 {p["ts"]} · {tipo}', p["cap"], [
                ("❤️", f'{p["likes"]:,}', "likes"),
                ("💬", f'{p["com"]:,}', "comentarios"),
                ("▶️", vistas, "visualizaciones"),
            ], copy_full=p["cap"])

        with st.expander("📋 Ver todas las publicaciones de Instagram"):
            df_all = pd.DataFrame([
                {"Fecha": p["ts"], "Tipo": p["tipo"], "❤️ Likes": p["likes"],
                 "💬 Coment.": p["com"], "▶️ Visualiz.": p["views"],
                 "Publicación": p["cap"][:120]}
                for p in lista_ig])
            st.dataframe(df_all, width='stretch', hide_index=True)
    else:
        st.warning("No se pudieron cargar las publicaciones de Instagram.")

    # ════════════════════════ FACEBOOK (compacto) ═══════════════════════
    if es_ig_only:
        return

    st.markdown("---")
    st.markdown('<div class="grupo-titulo">📘 Facebook</div>', unsafe_allow_html=True)
    st.caption("Facebook ya no expone alcance de página (Meta lo deprecó), por eso "
               "esta sección es más acotada: engagement, vistas y el crecimiento de seguidores.")
    if err_fb:
        st.error(f"⚠️ Error al cargar Facebook: {err_fb}")
    info_fb = datos_fb["info"]
    imp_fb  = datos_fb["impresiones"]
    _kpis([
        ("💬 Engagement",       f"{imp_fb.get('engagement', 0):,}",     "Interacciones del mes (reacciones, comentarios, compartidos)"),
        ("👥 Seguidores",       f"{info_fb.get('followers_count', 0):,}", "Audiencia de Facebook"),
        ("🖥️ Vistas de página", f"{imp_fb.get('vistas', 0):,}",          "Veces que se vio la página · 30d"),
    ])

    # Dos gráficos: actividad diaria de FB (engagement) + crecimiento de seguidores.
    col_eng, col_dia = st.columns(2)
    with col_eng:
        st.subheader("📈 Engagement diario")
        try:
            de = _wr.daily_metric(nombre, "fb", "page_post_engagements")
        except Exception:
            de = None
        if de is not None and not de.empty:
            fig = px.bar(de, x="metric_date", y="metric_value",
                         color_discrete_sequence=["#2563eb"])
            fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0),
                              xaxis_title="", yaxis_title="interacciones")
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Sin engagement diario en la base todavía.")
    with col_dia:
        st.subheader("👥 Nuevos seguidores por día")
        fan_data = {}
        for m in datos_fb["fan_growth"].get("data", []):
            if "follow" in m.get("name", "") or "fan" in m.get("name", ""):
                for v in m.get("values", []):
                    dt = v.get("end_time", "")[:10]
                    if dt:
                        fan_data[dt] = fan_data.get(dt, 0) + v.get("value", 0)
        if fan_data:
            df = pd.DataFrame([{"Fecha": k, "Nuevos": v} for k, v in sorted(fan_data.items())])
            fig = px.bar(df, x="Fecha", y="Nuevos", color_discrete_sequence=["#16a34a"])
            fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Sin datos de seguidores por día.")

    # Top 10 publicaciones de Facebook — mismas tarjetas de ranking que Instagram.
    st.markdown("---")
    st.subheader("🏆 Top 10 publicaciones de Facebook")
    posts_fb = datos_fb.get("posts", {}).get("data", [])
    if posts_fb:
        lista_fb = []
        for post in posts_fb:
            reac   = post.get("reactions") or post.get("likes") or {}
            likes  = reac.get("summary", {}).get("total_count", 0)
            com    = post.get("comments", {}).get("summary", {}).get("total_count", 0)
            shares = post.get("shares", {}).get("count", 0)
            lista_fb.append({
                "ts": post.get("created_time", "")[:10],
                "msg": post.get("message", "") or "(Sin texto)",
                "likes": likes, "com": com, "shares": shares,
            })
        lista_fb.sort(key=lambda x: x["likes"], reverse=True)
        st.markdown(TOP_CSS, unsafe_allow_html=True)
        for i, p in enumerate(lista_fb[:10], 1):
            tarjeta_ranking(i, f'📅 {p["ts"]}', p["msg"], [
                ("❤️", f'{p["likes"]:,}', "reacciones"),
                ("💬", f'{p["com"]:,}', "comentarios"),
                ("🔁", f'{p["shares"]:,}', "compartidos"),
            ], copy_full=p["msg"])
    else:
        st.info("Sin datos de publicaciones de Facebook.")
