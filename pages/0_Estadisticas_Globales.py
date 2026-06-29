import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from config import PORTALES, RESPONSIVE_CSS, sidebar_nav, fb_source, ig_source
from audience import contribucion_audiencia
from portal_view import tarjeta_ranking, TOP_CSS, mostrar_top, TABLA_CSS

st.set_page_config(page_title="Estadísticas Globales", page_icon="📊", layout="wide")

st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)
st.markdown(TABLA_CSS, unsafe_allow_html=True)   # estilo isla-oscura de las tablas
sidebar_nav(current="")

st.markdown("## 📊 Estadísticas Globales")
st.caption(
    "El desempeño del último mes de toda la red, para comparar portales y ver su evolución."
)
st.markdown("---")

# ── Carga de datos ──────────────────────────────────────────────────
def pendiente(v):
    return v in ("PENDIENTE", "", None)

@st.cache_data(ttl=3600)
def cargar_portal(nombre, page_id, ig_id, token, ig_only=False, live=False):
    r = {"nombre": nombre, "fb_seg":0,"fb_imp":0,"fb_eng":0,"fb_vistas":0,
         "ig_seg":0,"ig_imp":0,"ig_reach":0,"ig_engaged":0,
         "fb_daily":{},"fb_video_daily":{},"ig_daily":{},"posts_ig":[],"posts_fb":[],"all_media_ig":[]}
    if not ig_only and not pendiente(page_id) and not pendiente(token):
        try:
            fb = fb_source(nombre, page_id, token, live)
            info = fb.get_page_info()
            r["fb_seg"] = info.get("followers_count", 0)
            imp = fb.get_posts_impressions()
            # Visualizaciones de FB = reproducciones de video (no vistas de perfil).
            r["fb_imp"]   = imp.get("video_views", 0)
            r["fb_eng"]   = imp.get("engagement", 0)
            r["fb_vistas"]= imp.get("vistas", 0)
            r["fb_daily"] = imp.get("daily", {})
            r["fb_video_daily"] = imp.get("daily_video_views", {})
            posts = fb.get_recent_posts(limit=30)
            r["posts_fb"] = posts.get("data", [])
        except Exception as e:
            print(f"[{nombre}] FB: {e}")
    if not pendiente(ig_id) and not pendiente(token):
        try:
            ig = ig_source(nombre, ig_id, token, live)
            info_ig = ig.get_account_info()
            r["ig_seg"] = info_ig.get("followers_count", 0)
            imp_ig = ig.get_media_impressions(limit=25)
            r["ig_imp"]     = imp_ig.get("total_imp", 0)
            r["ig_reach"]   = imp_ig.get("total_reach", 0)
            r["ig_engaged"] = imp_ig.get("engaged", 0)
            r["ig_daily"]   = imp_ig.get("daily", {})
            r["posts_ig"]   = imp_ig.get("posts_data", [])
            # Historial completo para ranking por likes
            all_m = ig.get_all_media(max_posts=500)
            r["all_media_ig"] = [
                {
                    "ts":        p.get("timestamp","")[:10],
                    "tipo":      "reel" if p.get("product_type")=="clips"
                                 else p.get("media_type","IMAGE").lower(),
                    "plays":     0,
                    "reach":     0,
                    "likes":     p.get("like_count", 0),
                    "comments":  p.get("comments_count", 0),
                    "permalink": p.get("permalink",""),
                    "caption":   (p.get("caption") or "")[:60],
                }
                for p in all_m.get("data", [])
            ]
        except Exception as e:
            print(f"[{nombre}] IG: {e}")
    r["total_imp"] = r["fb_imp"] + r["ig_imp"]
    r["total_seg"] = r["fb_seg"] + r["ig_seg"]
    r["tasa_eng"]  = round(r["fb_eng"] / r["fb_seg"] * 100, 2) if r["fb_seg"] else 0
    return r

live = st.session_state.get("fstats_live", False)
with st.spinner("Cargando datos de todos los portales..."):
    datos_portales = []
    for p in PORTALES:
        if p.get("oculto"):          # portal oculto hasta configurar su acceso
            continue
        token = p.get("access_token","")
        if pendiente(token):
            datos_portales.append({"nombre": p["nombre"], "pendiente": True,
                                   "fb_seg":0,"fb_imp":0,"fb_eng":0,"fb_vistas":0,
                                   "ig_seg":0,"ig_imp":0,"ig_reach":0,"ig_engaged":0,
                                   "fb_daily":{},"fb_video_daily":{},"ig_daily":{},"posts_ig":[],"posts_fb":[],"all_media_ig":[],
                                   "total_imp":0,"total_seg":0,"tasa_eng":0})
        else:
            d = cargar_portal(p["nombre"], p.get("facebook_page_id"),
                              p.get("instagram_id"), token, p.get("ig_only", False), live)
            datos_portales.append(d)

activos = [d for d in datos_portales if not d.get("pendiente") and d["total_imp"] > 0]

# ── Helpers de warehouse y colores (usados en varias secciones) ──────
import warehouse.reader as _wr

_COLORES_PORTAL = {
    "Chubut Noticias": "#E2E8F0", "Atento Chubut": "#0EA5E9",
    "La Calle Online": "#EA580C", "El Americano": "#22C55E",
    "Viste esto?": "#a855f7", "Boca en Linea": "#fbbf24",
}
_PALETA = ["#a855f7", "#fbbf24", "#14b8a6", "#f472b6", "#38bdf8"]

def _color_portal(nombre, i):
    return _COLORES_PORTAL.get(nombre) or _PALETA[i % len(_PALETA)]

def _df_seguro(fn, *args):
    """Lee del warehouse devolviendo DataFrame vacío si la vista aún no existe
    (las tablas nuevas recién se crean en la primera ingesta)."""
    try:
        df = fn(*args)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def _alcance_por_tipo(portales):
    """Alcance diario PROMEDIO a seguidores y no-seguidores por portal, desde el
    warehouse (desglose follow_type de IG). Usa el promedio diario (no la suma)
    para que sea comparable con la base de seguidores y no se infle al acumular
    días. Devuelve {} si la tabla aún no existe."""
    out = {}
    for d in portales:
        rt = _df_seguro(_wr.reach_by_follow_type, d["nombre"])
        if rt.empty:
            continue
        ndias = max(1, rt["metric_date"].nunique())
        fr = rt.loc[rt["follow_type"] == "follower", "reach_value"].sum() / ndias
        nf = rt.loc[rt["follow_type"] == "non_follower", "reach_value"].sum() / ndias
        out[d["nombre"]] = {"follower": float(fr), "non_follower": float(nf)}
    return out

def _delta_periodo(plataforma, metric_name, dias=30):
    """Variación de PERÍODO: total de los últimos `dias` vs el período anterior
    equivalente, sumando POR PORTAL. Comparar períodos (no días sueltos) evita el
    ruido de un día viral aislado y es coherente con que los KPIs son del mes. Si
    un portal no tiene historia para dos ventanas completas, usa la mayor ventana
    pareja disponible. None si ningún portal tiene datos suficientes."""
    total, hubo = 0, False
    for d in activos:
        df = _df_seguro(_wr.daily_metric, d["nombre"], plataforma, metric_name)
        if df.empty:
            continue
        vals = (df.dropna(subset=["metric_value"]).sort_values("metric_date")
                  ["metric_value"].astype(int).tolist())
        w = min(dias, len(vals) // 2)
        if w < 3:                      # muy pocos días para comparar dos períodos
            continue
        total += sum(vals[-w:]) - sum(vals[-2 * w:-w])
        hubo = True
    return total if hubo else None

def _delta_periodo_seguidores(dias=30):
    """Crecimiento neto de seguidores en los últimos `dias` (foto de hoy vs la de
    hace ~`dias`), sumando POR PORTAL (FB + IG). None si no hay historia."""
    total, hubo = 0, False
    for d in activos:
        for plat in ("fb", "ig"):
            h = _df_seguro(_wr.followers_history, d["nombre"], plat)
            if h.empty:
                continue
            vals = (h.dropna(subset=["followers_count"]).sort_values("snapshot_date")
                     ["followers_count"].astype(int).tolist())
            if len(vals) < 2:
                continue
            w = min(dias, len(vals) - 1)
            total += vals[-1] - vals[-1 - w]
            hubo = True
    return total if hubo else None


# ── KPIs globales ───────────────────────────────────────────────────
total_viz   = sum(d["total_imp"] for d in datos_portales)
total_seg   = sum(d["total_seg"] for d in datos_portales)
total_eng   = sum(d["fb_eng"]    for d in datos_portales)
total_fb_vv = sum(d["fb_imp"]    for d in datos_portales)   # reproducciones de video FB
total_reach = sum(d["ig_reach"]  for d in datos_portales)

# Interacciones de la red (reacciones / comentarios / envíos), sumando IG + FB de
# las publicaciones del último mes. Se calcula acá (antes de los KPIs) y se reusa
# en la sección de detalle más abajo.
from datetime import timedelta as _td_int
_lim_int = (datetime.now() - _td_int(days=30)).strftime("%Y-%m-%d")
_filas_int, _tot_reac, _tot_com, _tot_env = [], 0, 0, 0
for d in datos_portales:
    if d.get("pendiente"):
        continue
    reac = com = env = 0
    for p in d.get("posts_ig", []):
        if p.get("ts", "") >= _lim_int:
            reac += p.get("likes", 0) or 0
            com  += p.get("comments", 0) or 0
            env  += p.get("shares", 0) or 0
    for post in d.get("posts_fb", []):
        if post.get("created_time", "")[:10] >= _lim_int:
            _r = post.get("reactions") or post.get("likes") or {}
            reac += _r.get("summary", {}).get("total_count", 0)
            com  += post.get("comments", {}).get("summary", {}).get("total_count", 0)
            env  += post.get("shares", {}).get("count", 0)
    if reac or com or env:
        _filas_int.append((d["nombre"], reac, com, env))
        _tot_reac += reac; _tot_com += com; _tot_env += env
total_interacciones = _tot_reac + _tot_com + _tot_env
# Interacciones por portal (para la columna de tasa de engagement de la tabla:
# interacciones ÷ visualizaciones, un % comparable entre portales).
_interacc_map = {n: r + c + e for n, r, c, e in _filas_int}
portales_activos = len(activos)

# Variación de PERÍODO (verde/roja): últimos 30 días vs los 30 anteriores,
# calculada por portal. Comparar períodos (no días sueltos) evita el ruido de un
# día viral y es coherente con que los KPIs son del mes. Visualizaciones y tasa
# no llevan flecha (no son un flujo diario acumulable comparable).
d_seg = _delta_periodo_seguidores()
d_vv  = _delta_periodo("fb", "page_video_views")
d_rch = _delta_periodo("ig", "reach")

def _kpi_delta(d, fallback=""):
    """Línea inferior de la tarjeta: delta de período (verde/rojo) o un subtítulo."""
    if d is None:
        return f'<div class="k-sub">{fallback}</div>' if fallback else ""
    cls = "up" if d >= 0 else "down"
    fl  = "▲" if d >= 0 else "▼"
    return f'<div class="k-delta {cls}">{fl} {d:+,} · 30d</div>'

st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card"><div class="k-label">🎯 Visualizaciones</div>
    <div class="k-value">{total_viz:,}</div><div class="k-sub">Acumulado · 30 días</div></div>
  <div class="kpi-card"><div class="k-label">👥 Seguidores</div>
    <div class="k-value">{total_seg:,}</div>{_kpi_delta(d_seg, "Audiencia propia (hoy)")}</div>
  <div class="kpi-card"><div class="k-label">▶️ Reproducciones FB</div>
    <div class="k-value">{total_fb_vv:,}</div>{_kpi_delta(d_vv, "Reproducciones de video · 30d")}</div>
  <div class="kpi-card"><div class="k-label">🎯 Alcance IG</div>
    <div class="k-value">{total_reach:,}</div>{_kpi_delta(d_rch, "Personas únicas · 30d")}</div>
  <div class="kpi-card"><div class="k-label">💬 Interacciones</div>
    <div class="k-value">{total_interacciones:,}</div><div class="k-sub">Reacciones + comentarios + envíos · IG + FB · 30d</div></div>
</div>
""", unsafe_allow_html=True)

st.caption(
    "Acumulado del último mes. La flecha marca la variación contra el mes anterior: "
    "🟢 subió · 🔴 bajó."
)

with st.expander("📖 Qué mide cada indicador"):
    st.markdown(
        "- **🎯 Visualizaciones (mes):** cuánto se *vio* tu contenido en toda la red "
        "(reproducciones de IG + reproducciones de video de FB). Es el termómetro de "
        "difusión total.\n"
        "- **👥 Seguidores totales:** el tamaño de tu audiencia propia (FB + IG). La "
        "flecha muestra si la red ganó o perdió seguidores en el último día.\n"
        "- **▶️ Reproducciones FB:** cuántas veces se reprodujeron los reels y videos de "
        "Facebook en el mes. Es el consumo de contenido real de FB (Meta dejó de exponer "
        "el alcance de página).\n"
        "- **🎯 Alcance IG:** a cuántas **personas únicas** llegaste en Instagram. A "
        "diferencia de las visualizaciones, cuenta personas, no reproducciones.\n"
        "- **💬 Interacciones:** total de reacciones + comentarios + envíos del mes, "
        "sumando Instagram y Facebook. Mide qué tan involucrada está la audiencia.\n\n"
        "Más abajo, la sección **💬 Interacciones de la red** desglosa las reacciones, "
        "comentarios y envíos sumando ambas plataformas. Esta vista reúne todo para "
        "**comparar portales**, **ver la evolución** y **detectar a tiempo** qué crece y qué cae."
    )

st.markdown("---")

# ── Tendencia de alcance diario — selector en vivo / histórico ─────
# Es el gráfico que mejor refleja la actividad, por eso va arriba de todo.
# Misma métrica sobre los mismos ejes (escala log); un selector elige la fuente:
# API en vivo (máx 30 días) o base de datos histórica (crece sola).
st.markdown('<div class="grupo-titulo">📡 Alcance de la red</div>', unsafe_allow_html=True)
st.subheader("📈 Tendencia de alcance diario — todos los portales")

if activos:
    PORTAL_COLOR = {
        "Chubut Noticias": "#E2E8F0",  # blanco/gris claro (tema oscuro)
        "Atento Chubut":   "#0EA5E9",  # celeste
        "La Calle Online": "#EA580C",  # naranja
        "El Americano":    "#22C55E",  # verde
    }
    FALLBACK = ["#a855f7", "#fbbf24", "#14b8a6"]
    # Color estable por portal: el mismo en ambas fuentes.
    _colores_trend, _fi = {}, 0
    for d in activos:
        c = PORTAL_COLOR.get(d["nombre"])
        if not c:
            c = FALLBACK[_fi % len(FALLBACK)]
            _fi += 1
        _colores_trend[d["nombre"]] = c

    _MODO_VIVO = "🟢 En vivo (últimos 30 días)"
    _MODO_HIST = "🗄️ Histórico acumulado (base de datos)"
    modo_trend = st.radio(
        "Fuente de datos", [_MODO_VIVO, _MODO_HIST],
        horizontal=True, key="trend_src",
        help="Misma métrica y mismos ejes. En vivo: API de Meta, máximo 30 días. "
             "Histórico: base de datos, se acumula indefinidamente día a día.")

    fig_trend = go.Figure()
    hay_datos = False
    nota_extra = []
    ymax = 0   # mayor valor graficado, para recortar el vacío de abajo en el eje log

    if modo_trend == _MODO_VIVO:
        from datetime import datetime as _dt, timedelta as _td
        # "En vivo" = SOLO los últimos 30 días (el histórico completo está en la
        # otra opción). Filtramos las series por este corte.
        corte_30 = (_dt.now() - _td(days=30)).strftime("%Y-%m-%d")
        fecha_inicio_global = (_dt.now() - _td(days=29)).strftime("%Y-%m-%d")
        notas_inicio = []
        for d in activos:
            color = _colores_trend[d["nombre"]]
            # IG = línea continua (últimos 30 días)
            items_ig = [(k, v) for k, v in sorted(d["ig_daily"].items()) if k >= corte_30]
            if items_ig:
                fechas_ig = [k for k, v in items_ig]
                vals_ig   = [v for k, v in items_ig]
                ymax = max(ymax, max(vals_ig) if vals_ig else 0)
                nombre_ig = d["nombre"] + " (IG)"
                if fechas_ig[0] > fecha_inicio_global:
                    nombre_ig += f" · desde {fechas_ig[0][8:10]}/{fechas_ig[0][5:7]}"
                    notas_inicio.append(f"**{d['nombre']} IG**: datos desde {fechas_ig[0][8:10]}/{fechas_ig[0][5:7]}")
                fig_trend.add_trace(go.Scatter(
                    x=fechas_ig, y=vals_ig, mode="lines+markers", name=nombre_ig,
                    connectgaps=False, line=dict(color=color, width=2),
                    marker=dict(size=4, color=color, opacity=0.7), opacity=0.95))
                hay_datos = True
        if any(len(d.get("ig_daily", {})) < 25 for d in activos if d.get("ig_daily")):
            nota_extra.append("Los puntos (•) marcan días con dato; una brecha indica día sin datos.")
        if notas_inicio:
            nota_extra.append("⚠️ Inicio tardío: " + " | ".join(notas_inicio) +
                              " — Meta solo provee histórico desde la conexión al panel.")
        nota_extra.append("ℹ️ Los datos del día actual pueden tardar horas en estar disponibles.")
    else:
        try:
            import warehouse.reader as wreader
            sin_hist = []   # portales activos sin ninguna serie histórica en la base
            for d in activos:
                color = _colores_trend[d["nombre"]]
                con_traza = False
                df_ig = wreader.daily_metric(d["nombre"], "ig", "reach")
                if not df_ig.empty:
                    hay_datos = True
                    con_traza = True
                    ymax = max(ymax, int(df_ig["metric_value"].max()))
                    fig_trend.add_trace(go.Scatter(
                        x=df_ig["metric_date"], y=df_ig["metric_value"],
                        mode="lines+markers", name=d["nombre"] + " (IG)",
                        connectgaps=False, line=dict(color=color, width=2),
                        marker=dict(size=4, color=color, opacity=0.7)))
                if not con_traza:
                    sin_hist.append(d["nombre"])
            nota_extra.append(
                "🗄️ Se nutre de la base de datos histórica: se actualiza cada día y "
                "**sigue creciendo indefinidamente**, a diferencia del modo en vivo (máx 30 días).")
            if sin_hist:
                nota_extra.append(
                    "⚠️ Sin alcance histórico en la base todavía: **" + ", ".join(sin_hist) +
                    "** — van a aparecer cuando su ingesta cargue alcance diario (revisá que "
                    "su token esté ingestando bien).")
        except Exception:
            st.info(
                "📦 La base de datos histórica todavía no está conectada. Agregá "
                "`MOTHERDUCK_TOKEN` en los *secrets* de Streamlit (Settings → Secrets) "
                "para ver el histórico acumulado que se va guardando cada día.")
            hay_datos = None  # aviso ya mostrado

    if hay_datos:
        import math
        # Recortamos el vacío de abajo: mostramos ~4,5 décadas desde el máximo, así
        # Viste (que arranca cerca de 1) no deja media escala vacía.
        techo   = math.log10(ymax) + 0.15 if ymax > 0 else 7.5
        rango_y = [max(0, techo - 4.5), techo]
        fig_trend.update_layout(
            showlegend=True,
            legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left",
                        x=0, font=dict(size=10.5), bgcolor="rgba(0,0,0,0)", title=None),
            margin=dict(l=0, r=0, t=10, b=130),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="rgba(255,255,255,0.08)", showgrid=True),
            yaxis=dict(type="log", title="Alcance (escala log.)", range=rango_y,
                       gridcolor="rgba(255,255,255,0.08)", tickformat=".2s"),
            hovermode="x unified")
        st.plotly_chart(fig_trend, width='stretch')
        partes = [
            "📐 **Escala logarítmica**: cada división = 10× el valor anterior, "
            "permite comparar portales con audiencias muy distintas.",
            "Cada línea = **alcance diario** (personas únicas) de Instagram por portal.",
        ]
        partes.extend(nota_extra)
        st.caption("  \n".join(partes))
    elif hay_datos is False:
        st.info("No hay datos de alcance para mostrar en esta fuente todavía.")
else:
    st.info("Todavía no hay portales activos con datos de alcance para graficar.")

# ── Reproducciones de video de Facebook — todos los portales ──────────
# Gemelo del gráfico de alcance, pero para el CONSUMO de contenido en FB
# (page_video_views): es la métrica grande que Meta dejó viva y que antes no
# contabilizábamos. Usa el mismo selector vivo/histórico de arriba (modo_trend).
if activos:
    st.markdown("---")
    st.markdown('<div class="grupo-titulo">📘 Reproducciones de video — Facebook</div>',
                unsafe_allow_html=True)
    st.subheader("▶️ Reproducciones de video de Facebook por día — todos los portales")

    fig_fb = go.Figure()
    hay_fb = False
    ymax_fb = 0
    if modo_trend == _MODO_VIVO:
        from datetime import datetime as _dt2, timedelta as _td2
        corte_30_fb = (_dt2.now() - _td2(days=30)).strftime("%Y-%m-%d")
        for d in activos:
            items = [(k, v) for k, v in sorted(d.get("fb_video_daily", {}).items())
                     if k >= corte_30_fb and v > 0]
            if items:
                fechas = [k for k, v in items]; vals = [v for k, v in items]
                ymax_fb = max(ymax_fb, max(vals))
                fig_fb.add_trace(go.Scatter(
                    x=fechas, y=vals, mode="lines+markers", name=d["nombre"] + " (FB)",
                    connectgaps=False, line=dict(color=_colores_trend[d["nombre"]], width=2),
                    marker=dict(size=4, color=_colores_trend[d["nombre"]], opacity=0.7)))
                hay_fb = True
    else:
        try:
            import warehouse.reader as wreader_fb
            for d in activos:
                df = wreader_fb.daily_metric(d["nombre"], "fb", "page_video_views")
                if df is not None and not df.empty:
                    ymax_fb = max(ymax_fb, int(df["metric_value"].max()))
                    fig_fb.add_trace(go.Scatter(
                        x=df["metric_date"], y=df["metric_value"],
                        mode="lines+markers", name=d["nombre"] + " (FB)",
                        connectgaps=False, line=dict(color=_colores_trend[d["nombre"]], width=2),
                        marker=dict(size=4, color=_colores_trend[d["nombre"]], opacity=0.7)))
                    hay_fb = True
        except Exception:
            hay_fb = None

    if hay_fb:
        import math as _math_fb
        techo = _math_fb.log10(ymax_fb) + 0.15 if ymax_fb > 0 else 6.5
        fig_fb.update_layout(
            showlegend=True,
            legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left",
                        x=0, font=dict(size=10.5), bgcolor="rgba(0,0,0,0)", title=None),
            margin=dict(l=0, r=0, t=10, b=110),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="rgba(255,255,255,0.08)", showgrid=True),
            yaxis=dict(type="log", title="Reproducciones (escala log.)",
                       range=[max(0, techo - 4.5), techo],
                       gridcolor="rgba(255,255,255,0.08)", tickformat=".2s"),
            hovermode="x unified")
        st.plotly_chart(fig_fb, width='stretch')
        st.caption("Cada línea = **reproducciones de reels y videos** de Facebook por "
                   "día y por portal (page_video_views). Es el consumo de contenido real "
                   "de FB; Meta ya no expone el alcance de página.")
    elif hay_fb is False:
        st.info("Sin reproducciones de video de Facebook para esta fuente todavía "
                "(corré la ingesta para cargar el histórico).")

st.markdown("---")

# ── Tabla comparativa ────────────────────────────────────────────────
st.subheader("📋 Tabla comparativa de portales")

# Tabla en HTML para controlar el color de los encabezados (st.dataframe los
# dibuja en canvas y no se pueden recolorear). Solo portales activos.
_filas_html = ""
for d in datos_portales:
    if d.get("pendiente") or d["total_imp"] <= 0:
        continue
    # Tasa de engagement = interacciones (IG+FB) ÷ visualizaciones del portal.
    _tasa_p = (_interacc_map.get(d["nombre"], 0) / d["total_imp"] * 100) if d["total_imp"] else 0
    _filas_html += (
        "<tr>"
        f"<td class='tc-portal'>{d['nombre']}</td>"
        f"<td>{d['ig_imp']:,}</td>"
        f"<td>{d['fb_imp']:,}</td>"
        f"<td>{d['total_imp']:,}</td>"
        f"<td>{d['total_seg']:,}</td>"
        f"<td>{d['fb_eng']:,}</td>"
        f"<td>{_tasa_p:.1f}%</td>"
        f"<td>{d['ig_reach']:,}</td>"
        f"<td>{d['ig_engaged']:,}</td>"
        "</tr>"
    )
st.markdown(f"""
<div class="tc-wrap"><table class="tc"><thead><tr>
<th>Portal</th><th>📸 IG visualiz.</th><th>▶️ Reproducc. FB</th><th>🎯 Total visualiz.</th>
<th>👥 Seguidores</th><th>💬 Engagement FB</th><th>📊 Tasa eng.</th>
<th>🎯 Alcance IG</th><th>💬 Interacc. IG</th>
</tr></thead><tbody>{_filas_html}</tbody></table></div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── Interacciones de la red (reacciones / comentarios / envíos) ───────
# Suma de las interacciones de las publicaciones del último mes, combinando
# AMBAS plataformas: reacciones = likes IG + reacciones FB; comentarios de las
# dos; envíos = envíos por DM (IG) + compartidos (FB).
st.markdown('<div class="grupo-titulo">💬 Interacciones de la red</div>', unsafe_allow_html=True)
st.subheader("💬 Reacciones, comentarios y envíos — Instagram + Facebook")
st.caption("Interacciones de las publicaciones del último mes, sumando ambas "
           "plataformas. Reacciones = likes (IG) + reacciones (FB); "
           "envíos = compartidos por DM (IG) + compartidos (FB).")

# _filas_int y los totales (_tot_reac/_tot_com/_tot_env) ya se calcularon arriba,
# junto a los KPIs, para no recorrer los posts dos veces.
if _filas_int:
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card"><div class="k-label">❤️ Reacciones</div>
        <div class="k-value">{_tot_reac:,}</div><div class="k-sub">Likes (IG) + reacciones (FB) · último mes</div></div>
      <div class="kpi-card"><div class="k-label">💬 Comentarios</div>
        <div class="k-value">{_tot_com:,}</div><div class="k-sub">IG + FB · último mes</div></div>
      <div class="kpi-card"><div class="k-label">📤 Envíos y compartidos</div>
        <div class="k-value">{_tot_env:,}</div><div class="k-sub">Envíos por DM (IG) + compartidos (FB) · último mes</div></div>
    </div>
    """, unsafe_allow_html=True)

    _filas_int.sort(key=lambda x: (x[1] + x[2] + x[3]), reverse=True)
    _rows_html = "".join(
        f"<tr><td class='tc-portal'>{n}</td><td>{r:,}</td><td>{c:,}</td><td>{e:,}</td></tr>"
        for n, r, c, e in _filas_int)
    _rows_html += (
        f"<tr><td class='tc-portal'>🌐 Total de la red</td>"
        f"<td><b>{_tot_reac:,}</b></td><td><b>{_tot_com:,}</b></td><td><b>{_tot_env:,}</b></td></tr>")
    st.markdown(
        '<div class="tc-wrap"><table class="tc"><thead><tr>'
        '<th>Portal</th><th>❤️ Reacciones</th><th>💬 Comentarios</th><th>📤 Envíos</th>'
        f'</tr></thead><tbody>{_rows_html}</tbody></table></div>',
        unsafe_allow_html=True)
else:
    st.info("Sin interacciones cargadas todavía.")

st.markdown("---")

# ── Seguidores y su aporte a la audiencia ────────────────────────────
st.markdown('<div class="grupo-titulo">👥 Audiencia</div>', unsafe_allow_html=True)
st.subheader("👥 Seguidores y su aporte a la audiencia")
st.caption(
    "El tamaño y el crecimiento de la audiencia de la red, y cuánto aporta cada "
    "portal a la base de seguidores."
)

if activos:
    contrib = contribucion_audiencia(activos)
    cf = contrib["filas"]
    alc = _alcance_por_tipo(activos)
    hay_cob = bool(alc)

    tot_fr = sum(v["follower"] for v in alc.values()) if hay_cob else 0
    tot_nf = sum(v["non_follower"] for v in alc.values()) if hay_cob else 0
    cob_global = (tot_fr / contrib["total_seguidores"]) if (hay_cob and contrib["total_seguidores"]) else 0

    nf_str = f"{int(tot_nf):,}" if hay_cob else "—"
    # Crecimiento del último mes (seguidores netos, FB + IG) y su tasa sobre la base.
    _base_seg   = contrib['total_seguidores']
    _seg_nuevos = f"{d_seg:+,}" if d_seg is not None else "—"
    _seg_col    = "#22c55e" if (d_seg or 0) >= 0 else "#f87171"
    _crec       = (d_seg / _base_seg * 100) if (d_seg is not None and _base_seg) else None
    _crec_str   = f"{_crec:+.1f}%" if _crec is not None else "—"
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card"><div class="k-label">👥 Seguidores totales</div>
        <div class="k-value">{_base_seg:,}</div><div class="k-sub">FB + IG · toda la red</div></div>
      <div class="kpi-card"><div class="k-label">📈 Nuevos seguidores · mes</div>
        <div class="k-value" style="color:{_seg_col}">{_seg_nuevos}</div><div class="k-sub">Netos (FB + IG) · 30d</div></div>
      <div class="kpi-card"><div class="k-label">📊 Crecimiento mensual</div>
        <div class="k-value" style="color:{_seg_col}">{_crec_str}</div><div class="k-sub">Nuevos ÷ base de seguidores</div></div>
      <div class="kpi-card"><div class="k-label">🌐 Alcance a no-seguidores</div>
        <div class="k-value">{nf_str}</div><div class="k-sub">Personas nuevas · día promedio</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Aporte de cada portal a la base de seguidores.
    df_share = pd.DataFrame([
        {"Portal": f["nombre"], "Seguidores": f["seguidores"],
         "pct": f["share_seguidores"] * 100}
        for f in sorted(cf, key=lambda x: x["seguidores"], reverse=True)
    ])
    fig_share = go.Figure(go.Bar(
        x=df_share["Seguidores"], y=df_share["Portal"], orientation="h",
        marker_color="#0EA5E9",
        text=[f"{p:.0f}%" for p in df_share["pct"]], textposition="auto"))
    fig_share.update_layout(
        title="Aporte a la base de seguidores",
        margin=dict(l=0, r=0, t=40, b=0), height=max(220, 56 * len(df_share)),
        yaxis=dict(autorange="reversed"), xaxis_title="seguidores",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_share, width='stretch')

    # Detalle por portal (tabla HTML isla-oscura, igual que la comparativa).
    _det_rows = ""
    for f in cf:
        a = alc.get(f["nombre"]) if hay_cob else None
        _nf = f"{int(a['non_follower']):,}" if a else "—"
        _det_rows += (
            f"<tr><td class='tc-portal'>{f['nombre']}</td>"
            f"<td>{f['seguidores']:,}</td>"
            f"<td>{f['share_seguidores']*100:.0f}%</td>"
            f"<td>{_nf}</td></tr>")
    st.markdown(
        '<div class="tc-wrap"><table class="tc"><thead><tr>'
        '<th>Portal</th><th>👥 Seguidores</th><th>📊 % de seguidores</th>'
        '<th>🌐 No-seg/día</th>'
        f'</tr></thead><tbody>{_det_rows}</tbody></table></div>',
        unsafe_allow_html=True)

    st.caption(
        "📊 **% de seguidores** = cuánto pesa cada portal en la base total. "
        "🌐 **No-seg/día** = personas nuevas alcanzadas por día (promedio)."
    )
else:
    st.info("No hay portales activos con datos de audiencia para analizar todavía.")

st.markdown("---")

# ── Evolución histórica de audiencia (base de datos) ─────────────────

# ── 1) Crecimiento de seguidores por portal ─────────────────────────
st.subheader("📈 Crecimiento de seguidores — por portal")
st.caption(
    "Cuántos seguidores netos (FB + IG) sumó cada portal en el período guardado. "
    "Barra a la derecha = creció; a la izquierda = perdió."
)

_series_seg = {}
for d in activos:
    _cols = []
    for plat in ("fb", "ig"):
        h = _df_seguro(_wr.followers_history, d["nombre"], plat)
        if not h.empty:
            s = (h.dropna(subset=["followers_count"])
                   .assign(snapshot_date=lambda x: pd.to_datetime(x["snapshot_date"]))
                   .set_index("snapshot_date")["followers_count"])
            _cols.append(s.rename(plat))
    if _cols:
        dfp = pd.concat(_cols, axis=1).sort_index().ffill().fillna(0)
        _series_seg[d["nombre"]] = dfp.sum(axis=1)

if _series_seg:
    df_seg = pd.concat(_series_seg, axis=1).sort_index().ffill().fillna(0)
    # Crecimiento neto en el período (último - primero) por portal.
    crec = (df_seg.iloc[-1] - df_seg.iloc[0]).sort_values(ascending=False)
    df_crec = crec.reset_index()
    df_crec.columns = ["Portal", "delta"]
    fig_crec = go.Figure(go.Bar(
        x=df_crec["delta"], y=df_crec["Portal"], orientation="h",
        marker_color=["#22C55E" if v >= 0 else "#EA580C" for v in df_crec["delta"]],
        text=[f"{'+' if v >= 0 else ''}{int(v):,}" for v in df_crec["delta"]],
        textposition="auto"))
    fig_crec.add_vline(x=0, line_color="rgba(255,255,255,0.3)")
    fig_crec.update_layout(
        margin=dict(l=0, r=0, t=10, b=0), height=max(200, 56 * len(df_crec)),
        yaxis=dict(autorange="reversed"), xaxis_title="altas netas en el período",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_crec, width='stretch')

    # Altas netas por día (total de todos los portales), si hay días suficientes.
    altas_dia = df_seg.sum(axis=1).diff().dropna()
    if len(altas_dia) >= 3:
        st.markdown("**Seguidores netos sumados por día — toda la red**")
        fig_ad = go.Figure(go.Bar(
            x=altas_dia.index, y=altas_dia.values,
            marker_color=["#22C55E" if v >= 0 else "#EA580C" for v in altas_dia.values]))
        fig_ad.update_layout(
            margin=dict(l=0, r=0, t=10, b=0), height=200,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="altas netas/día (total)", gridcolor="rgba(255,255,255,0.08)"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.08)"))
        st.plotly_chart(fig_ad, width='stretch')

    desde = df_seg.index.min().strftime("%d/%m")
    hasta = df_seg.index.max().strftime("%d/%m")
    total_delta = int(crec.sum())
    st.caption(
        f"📅 Período guardado: **{desde} → {hasta}** · la red sumó "
        f"**{'+' if total_delta >= 0 else ''}{total_delta:,}** seguidores en total."
    )
else:
    st.info("Todavía no hay histórico de seguidores cargado en la base.")

st.markdown("---")

# ── 2) Demografía de la audiencia (Instagram) ───────────────────────
st.subheader("🧭 Demografía de la audiencia — Instagram")
st.caption(
    "Quiénes son las personas detrás de los números. Elegí qué audiencia mirar y "
    "con qué corte: **Seguidores** es tu base fija; **Audiencia que interactúa** "
    "es quien engancha con tu contenido (incluye no-seguidores). Cambiá el "
    "**segmento** para verla por edad, género, país o ciudad."
)

_AUD = {"Seguidores": "follower", "Audiencia que interactúa": "engaged"}
_BD  = {"Edad": "age", "Género": "gender", "País": "country", "Ciudad": "city"}
_GEN_LABEL = {"F": "Femenino", "M": "Masculino", "U": "No especificado"}

_c1, _c2 = st.columns(2)
_aud_label = _c1.radio("Audiencia", list(_AUD), horizontal=True, key="demo_aud")
_bd_label  = _c2.radio("Segmento", list(_BD), horizontal=True, key="demo_bd")
_audience_type, _breakdown = _AUD[_aud_label], _BD[_bd_label]

_acc = {}
for d in activos:
    dem = _df_seguro(_wr.demographics, d["nombre"], _audience_type, _breakdown)
    for _, row in dem.iterrows():
        dim = row["dimension"]
        _acc[dim] = _acc.get(dim, 0) + int(row["value"] or 0)

if _acc:
    df_dem = pd.DataFrame(sorted(_acc.items(), key=lambda kv: kv[1], reverse=True),
                          columns=["dimension", "value"])
    if _breakdown in ("country", "city"):
        df_dem = df_dem.head(12)
    if _breakdown == "gender":
        df_dem["dimension"] = df_dem["dimension"].map(lambda v: _GEN_LABEL.get(v, v))
    fig_dem = px.bar(df_dem, x="value", y="dimension", orientation="h",
                     color="value", color_continuous_scale="Tealgrn")
    fig_dem.update_layout(
        yaxis=dict(autorange="reversed"), coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=10, b=0), height=max(240, 34 * len(df_dem)),
        xaxis_title="personas", yaxis_title="",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_dem, width='stretch')
    st.caption(
        f"**{_aud_label}** por **{_bd_label.lower()}**, sumando todos los portales "
        "con Instagram."
    )
else:
    st.info("Todavía no hay demografía cargada para mostrar.")

st.markdown("---")

# ── Ranking por visualizaciones ─────────────────────────────────────
st.markdown('<div class="grupo-titulo">🎬 Contenido y posicionamiento</div>', unsafe_allow_html=True)
if activos:


    # ── Rendimiento de reels por portal ──────────────────────────────
    st.subheader("🎬 Rendimiento de reels por portal")
    st.caption(
        "Cuánto rinde, en promedio, un reel de cada portal. El gráfico ordena los "
        "portales por **reproducciones promedio** (qué portal hace los reels que más "
        "circulan); la tabla suma el alcance, los **envíos** (la señal de viralidad "
        "más fuerte) y cuál fue el mejor reel de cada uno."
    )

    todos_posts_ig = []
    for d in activos:
        for post in d["posts_ig"]:
            todos_posts_ig.append({**post, "portal": d["nombre"]})

    reels_portal = {}
    for d in activos:
        reels = [p for p in d.get("posts_ig", []) if p.get("tipo") == "reel"]
        if not reels:
            continue
        con_plays = [p for p in reels if (p.get("plays") or 0) > 0]
        reels_portal[d["nombre"]] = {
            "n":          len(reels),
            "avg_plays":  (sum(p.get("plays", 0) for p in con_plays) / len(con_plays)) if con_plays else 0,
            "avg_reach":  sum(p.get("reach", 0) for p in reels) / len(reels),
            "avg_shares": sum(p.get("shares", 0) or 0 for p in reels) / len(reels),
            "best":       max(reels, key=lambda p: (p.get("plays", 0) or p.get("reach", 0))),
        }

    if reels_portal:
        orden_r = sorted(reels_portal.items(), key=lambda kv: kv[1]["avg_plays"], reverse=True)
        # Un solo gráfico claro: reproducciones promedio por reel, por portal.
        df_rm = pd.DataFrame([{"Portal": n, "Promedio": int(v["avg_plays"])}
                              for n, v in orden_r])
        fig_r = px.bar(df_rm, x="Promedio", y="Portal", orientation="h",
                       color_discrete_sequence=["#c026d3"],
                       text=[f"{x:,}" for x in df_rm["Promedio"]])
        fig_r.update_traces(textposition="outside", cliponaxis=False)
        fig_r.update_layout(margin=dict(l=0, r=0, t=10, b=10),
                            yaxis=dict(autorange="reversed", title=""),
                            xaxis=dict(title="reproducciones promedio por reel"),
                            height=max(220, 56 * len(reels_portal)),
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_r, width='stretch')

        import html as _html_r
        _reel_rows = ""
        for n, v in orden_r:
            _mejor_val = (v['best'].get('plays', 0) or v['best'].get('reach', 0))
            _mejor_cap = _html_r.escape((v['best'].get('caption', '') or '')[:40])
            _reel_rows += (
                f"<tr><td class='tc-portal'>{n}</td>"
                f"<td>{v['n']:,}</td>"
                f"<td>{int(v['avg_plays']):,}</td>"
                f"<td>{int(v['avg_reach']):,}</td>"
                f"<td>{int(v['avg_shares']):,}</td>"
                f"<td class='tc-text'>{_mejor_val:,} · {_mejor_cap}</td></tr>")
        st.markdown(
            '<div class="tc-wrap"><table class="tc"><thead><tr>'
            "<th>Portal</th><th>🎬 Reels</th><th>▶️ Reproduc./reel</th>"
            "<th>🎯 Alcance/reel</th><th>📤 Envíos/reel</th>"
            "<th style='text-align:left'>🏆 Mejor reel</th>"
            f'</tr></thead><tbody>{_reel_rows}</tbody></table></div>',
            unsafe_allow_html=True)
    else:
        st.info("Todavía no hay reels con métricas cargadas para comparar.")

    # ── Top 10 IG último mes (por difusión: reproducciones/alcance) ──
    if todos_posts_ig:
        st.markdown("---")
        st.subheader("📸 Top 20 publicaciones Instagram — último mes")
        st.caption("Ordenadas por **difusión real**: reproducciones (reels) o "
                   "alcance (otros formatos), no por likes.")
        from datetime import timedelta
        limite_ig = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        def _difusion(p):
            return (p.get("plays", 0) or 0) or (p.get("reach", 0) or 0)

        cand_ig = [p for p in todos_posts_ig if p.get("ts", "") >= limite_ig]
        if not cand_ig:
            cand_ig = todos_posts_ig
        top10_ig = sorted(cand_ig, key=_difusion, reverse=True)[:20]

        if top10_ig and _difusion(top10_ig[0]) > 0:
            _TL = {"reel": "🎬 Reel", "video": "▶️ Video", "carousel_album": "🖼️ Carrusel"}
            mostrar_top([{
                "ts":     post["ts"],
                "tipo":   _TL.get(post.get("tipo"), "📷 Imagen"),
                "titulo": post.get("caption", ""),
                "portal": post["portal"],
                "link":   post.get("permalink", ""),
                "views":  _difusion(post),
                "likes":  post.get("likes", 0),
                "com":    post.get("comments", 0),
                "shares": post.get("shares", 0),
            } for post in top10_ig], "ig", n=20)
        else:
            st.info("Sin métricas de difusión cargadas todavía (corré la ingesta para verlas).")

    # ── Top 10 FB último mes ─────────────────────────────────────
    st.markdown("---")
    st.subheader("📘 Top 20 publicaciones Facebook — último mes")
    st.caption("Ordenadas por **reproducciones de video**.")
    from datetime import timedelta
    limite_30 = datetime.now() - timedelta(days=30)
    todos_posts_fb = []
    for d in activos:
        for post in d.get("posts_fb", []):
            try:
                fecha = datetime.strptime(post.get("created_time","")[:10], "%Y-%m-%d")
                if fecha < limite_30:
                    continue
                reac  = post.get("reactions") or post.get("likes") or {}
                likes = reac.get("summary", {}).get("total_count", 0)
                com   = post.get("comments", {}).get("summary", {}).get("total_count", 0)
                shares= post.get("shares", {}).get("count", 0)
                todos_posts_fb.append({
                    "portal":  d["nombre"],
                    "fecha":   post.get("created_time","")[:10],
                    "mensaje": (post.get("message") or "")[:100],
                    "views":   int(post.get("video_views", 0) or 0),
                    "likes":   likes,
                    "comentarios": com,
                    "compartidos": shares,
                })
            except:
                pass

    if todos_posts_fb:
        top10_fb = sorted(todos_posts_fb, key=lambda x: (x["views"], x["likes"]), reverse=True)[:20]
        mostrar_top([{
            "ts":     post["fecha"],
            "titulo": post["mensaje"],
            "portal": post["portal"],
            "views":  post["views"],
            "likes":  post["likes"],
            "com":    post["comentarios"],
            "shares": post["compartidos"],
        } for post in top10_fb], "fb", n=20)
    else:
        st.info("Sin datos de publicaciones de Facebook en los último mes.")

else:
    st.info("No hay portales activos con datos disponibles aún.")

# ── Informe ejecutivo en PDF (OCULTO hasta actualizarlo) ──────────────
# Deshabilitado a pedido: el PDF todavía no refleja las métricas nuevas
# (reproducciones FB, envíos, interacciones). Reactivar: _PDF_HABILITADO = True.
_PDF_HABILITADO = False
if _PDF_HABILITADO:
    st.markdown("---")
    st.subheader("📄 Informe ejecutivo en PDF")
    st.markdown(
        "Generá un **informe en PDF** listo para compartir o presentar, con el resumen "
        "del último mes de **toda la red**: los KPIs y totales, el ranking de portales por "
        "visualizaciones, las tendencias de alcance, el desglose por portal y el top de "
        "publicaciones de Instagram. *(Es una primera versión; la vamos a seguir "
        "mejorando.)*"
    )

    if st.button("📄 Generar informe PDF", type="primary", key="gen_pdf"):
        with st.spinner("Generando informe… (puede tardar unos segundos)"):
            try:
                from pdf_report import generar_brief
                resumenes = [{**d, "ig_daily_seg": d.get("ig_daily_seg", {})}
                             for d in datos_portales]
                totales = {
                    "total_imp": total_viz,
                    "total_seg": total_seg,
                    "total_eng": total_eng,
                    "total_fb":  sum(d.get("fb_imp", 0) for d in datos_portales),
                    "total_ig":  sum(d.get("ig_imp", 0) for d in datos_portales),
                }
                top_ig = [{**p, "portal": d["nombre"]}
                          for d in activos for p in d.get("posts_ig", [])]
                pdf_bytes = generar_brief(resumenes=resumenes, totales=totales,
                                          top_ig=top_ig, top_fb=[])
                st.download_button(
                    "⬇️ Descargar informe PDF", data=pdf_bytes,
                    file_name=f"informe_fstats_{datetime.now():%Y%m%d}.pdf",
                    mime="application/pdf", type="primary", key="dl_pdf")
                st.success("Informe generado — tocá **Descargar informe PDF**.")
            except Exception as e:
                st.error(f"No se pudo generar el PDF: {e}")
