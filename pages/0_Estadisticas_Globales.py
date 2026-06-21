import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from config import PORTALES, RESPONSIVE_CSS, sidebar_nav, fb_source, ig_source
from audience import contribucion_audiencia

st.set_page_config(page_title="Estadísticas Globales", page_icon="📊", layout="wide")

st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)
sidebar_nav(current="")

st.title("📊 Estadísticas Globales — Todos los portales")
st.markdown("Análisis comparativo · último mes")
st.markdown("---")

# ── Carga de datos ──────────────────────────────────────────────────
def pendiente(v):
    return v in ("PENDIENTE", "", None)

@st.cache_data(ttl=3600)
def cargar_portal(nombre, page_id, ig_id, token, ig_only=False, live=False):
    r = {"nombre": nombre, "fb_seg":0,"fb_imp":0,"fb_eng":0,"fb_vistas":0,
         "ig_seg":0,"ig_imp":0,"ig_reach":0,"ig_engaged":0,
         "fb_daily":{},"ig_daily":{},"posts_ig":[],"posts_fb":[],"all_media_ig":[]}
    if not ig_only and not pendiente(page_id) and not pendiente(token):
        try:
            fb = fb_source(nombre, page_id, token, live)
            info = fb.get_page_info()
            r["fb_seg"] = info.get("followers_count", 0)
            imp = fb.get_posts_impressions()
            r["fb_imp"]   = imp.get("total_imp", 0)
            r["fb_eng"]   = imp.get("engagement", 0)
            r["fb_vistas"]= imp.get("vistas", 0)
            r["fb_daily"] = imp.get("daily", {})
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
        token = p.get("access_token","")
        if pendiente(token):
            datos_portales.append({"nombre": p["nombre"], "pendiente": True,
                                   "fb_seg":0,"fb_imp":0,"fb_eng":0,"fb_vistas":0,
                                   "ig_seg":0,"ig_imp":0,"ig_reach":0,"ig_engaged":0,
                                   "fb_daily":{},"ig_daily":{},"posts_ig":[],"posts_fb":[],"all_media_ig":[],
                                   "total_imp":0,"total_seg":0,"tasa_eng":0})
        else:
            d = cargar_portal(p["nombre"], p.get("facebook_page_id"),
                              p.get("instagram_id"), token, p.get("ig_only", False), live)
            datos_portales.append(d)

activos = [d for d in datos_portales if not d.get("pendiente") and d["total_imp"] > 0]

# ── KPIs globales ───────────────────────────────────────────────────
total_viz   = sum(d["total_imp"] for d in datos_portales)
total_seg   = sum(d["total_seg"] for d in datos_portales)
total_eng   = sum(d["fb_eng"]    for d in datos_portales)
total_reach = sum(d["ig_reach"]  for d in datos_portales)
tasa_global = round(total_eng / total_seg * 100, 2) if total_seg else 0
portales_activos = len(activos)

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("🎯 Visualizaciones totales", f"{total_viz:,}")
c2.metric("👥 Seguidores totales",      f"{total_seg:,}")
c3.metric("💬 Engagement FB total",     f"{total_eng:,}")
c4.metric("🎯 Alcance único IG total",  f"{total_reach:,}")
c5.metric("📊 Tasa eng. global",        f"{tasa_global:.2f}%",
          help="Engagement FB / seguidores totales")

st.markdown("---")

# ── Tabla comparativa ────────────────────────────────────────────────
st.subheader("📋 Tabla comparativa de portales")

filas = []
for d in datos_portales:
    filas.append({
        "Portal":             d["nombre"],
        "Estado":             "✅ Activo" if not d.get("pendiente") and d["total_imp"]>0 else "⏳ Pendiente",
        "📘 FB Alcance":      d["fb_imp"],
        "📸 IG Visualiz.":    d["ig_imp"],
        "🎯 Total":           d["total_imp"],
        "👥 Seguidores":      d["total_seg"],
        "💬 Engagement FB":   d["fb_eng"],
        "📊 Tasa eng.":       f"{d['tasa_eng']:.2f}%",
        "🎯 Alcance único IG":d["ig_reach"],
        "💬 Interacc. IG":    d["ig_engaged"],
    })

df_tabla = pd.DataFrame(filas)
st.dataframe(df_tabla, width='stretch', hide_index=True)

st.markdown("---")

# ── Contribución de seguidores a la audiencia ────────────────────────
st.subheader("👥 Contribución de seguidores a la audiencia")

if activos:
    contrib = contribucion_audiencia(activos)
    cf = contrib["filas"]

    k1, k2, k3 = st.columns(3)
    k1.metric("🎯 Audiencia única alcanzada", f"{contrib['total_alcance']:,}",
              help="Personas únicas alcanzadas en el período (alcance único FB + IG).")
    k2.metric("📣 Factor de amplificación", f"{contrib['amplificacion_global']:.1f}×",
              help="Audiencia alcanzada ÷ base de seguidores. >1× = llegás a más "
                   "gente que tu base de seguidores.")
    k3.metric("🌐 Audiencia de no-seguidores", f"{contrib['pct_no_seg_global']*100:.0f}%",
              help="Cota mínima del alcance que cae fuera de tu base de seguidores. "
                   "El valor real puede ser mayor.")

    col_a, col_b = st.columns(2)

    # Gráfico 1: base de seguidores vs audiencia alcanzada, por portal.
    with col_a:
        df_sa = pd.DataFrame([
            {"Portal": f["nombre"], "👥 Seguidores": f["seguidores"],
             "🎯 Audiencia": f["alcance"]}
            for f in cf
        ])
        df_sa_m = df_sa.melt(id_vars="Portal",
                             value_vars=["👥 Seguidores", "🎯 Audiencia"],
                             var_name="Métrica", value_name="Personas")
        fig_sa = px.bar(df_sa_m, x="Personas", y="Portal", color="Métrica",
                        orientation="h", barmode="group",
                        color_discrete_map={"👥 Seguidores": "#64748B",
                                            "🎯 Audiencia": "#22C55E"},
                        title="Base de seguidores vs audiencia alcanzada")
        fig_sa.update_layout(margin=dict(l=0, r=0, t=40, b=0),
                             yaxis=dict(autorange="reversed"), legend_title="",
                             height=max(220, 60 * len(cf)),
                             plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                             legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig_sa, width='stretch')

    # Gráfico 2: índice de aporte (cuánto pesa en audiencia vs en seguidores).
    with col_b:
        df_ap = pd.DataFrame([
            {"Portal": f["nombre"], "Índice": f["indice_aporte"]}
            for f in sorted(cf, key=lambda x: x["indice_aporte"], reverse=True)
            if f["seguidores"] > 0
        ])
        if not df_ap.empty:
            df_ap["color"] = df_ap["Índice"].apply(
                lambda v: "#22C55E" if v >= 1 else "#EA580C")
            fig_ap = go.Figure(go.Bar(
                x=df_ap["Índice"], y=df_ap["Portal"], orientation="h",
                marker_color=df_ap["color"],
                text=[f"{v:.2f}×" for v in df_ap["Índice"]], textposition="auto"))
            fig_ap.add_vline(x=1, line_dash="dot", line_color="rgba(255,255,255,0.5)")
            fig_ap.update_layout(
                title="Índice de aporte a la audiencia",
                margin=dict(l=0, r=0, t=40, b=0),
                yaxis=dict(autorange="reversed"),
                height=max(220, 60 * len(df_ap)),
                xaxis_title="cuota de audiencia ÷ cuota de seguidores",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_ap, width='stretch')

    # Detalle por portal.
    df_det = pd.DataFrame([
        {
            "Portal":              f["nombre"],
            "👥 Seguidores":       f["seguidores"],
            "🎯 Audiencia":        f["alcance"],
            "📣 Amplificación":    f"{f['amplificacion']:.1f}×",
            "🌐 % no-seguidores":  f"{f['pct_no_seg']*100:.0f}%",
            "📊 % de la audiencia": f"{f['share_audiencia']*100:.0f}%",
            "🧭 Índice de aporte": f"{f['indice_aporte']:.2f}×" if f["seguidores"] else "—",
        }
        for f in cf
    ])
    st.dataframe(df_det, width='stretch', hide_index=True)

    st.caption(
        "📣 **Factor de amplificación** = audiencia alcanzada ÷ base de seguidores. "
        "Más de 1× significa que el contenido llega a más personas que tu propia "
        "base de seguidores.  \n"
        "🌐 **% de no-seguidores** es una **cota mínima**: como el alcance cuenta "
        "personas únicas, todo lo que supera tu base de seguidores son personas "
        "que (en su mayoría) no te siguen. El valor real puede ser mayor.  \n"
        "🧭 **Índice de aporte** = cuánto pesa el portal en la audiencia total frente "
        "a cuánto pesa en seguidores. Mayor a 1 = atrae más audiencia de la que su "
        "base de seguidores sugeriría.  \n"
        "ℹ️ FB e IG se suman como audiencias separadas; una persona que sigue ambas "
        "puede contarse en las dos."
    )
else:
    st.info("No hay portales activos con datos de audiencia para analizar todavía.")

st.markdown("---")

# ── Evolución histórica de audiencia (base de datos) ─────────────────
import warehouse.reader as _wr

_COLORES_PORTAL = {
    "Chubut Noticias": "#E2E8F0", "Atento Chubut": "#0EA5E9",
    "La Calle Online": "#EA580C", "El Americano": "#22C55E",
    "VISTE ESTO?": "#a855f7", "Boca en Linea": "#fbbf24",
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

# ── 1) Evolución de seguidores totales (aporte por portal) ──────────
st.subheader("📈 Evolución de seguidores totales — aporte por portal")

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
    orden = df_seg.iloc[-1].sort_values(ascending=False).index.tolist()
    fig_seg = go.Figure()
    for i, nombre in enumerate(orden):
        fig_seg.add_trace(go.Scatter(
            x=df_seg.index, y=df_seg[nombre], name=nombre,
            mode="lines", stackgroup="one",
            line=dict(width=0.5, color=_color_portal(nombre, i)),
            fillcolor=_color_portal(nombre, i),
            hovertemplate="%{y:,.0f}<extra>" + nombre + "</extra>"))
    fig_seg.update_layout(
        margin=dict(l=0, r=0, t=10, b=80), height=360,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.2, font=dict(size=10.5)),
        yaxis=dict(title="Seguidores totales", gridcolor="rgba(255,255,255,0.08)",
                   tickformat=".2s"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
        hovermode="x unified")
    st.plotly_chart(fig_seg, width='stretch')
    st.caption(
        f"👥 Suma de seguidores FB + IG por portal, apilada. "
        f"Total actual: **{int(df_seg.iloc[-1].sum()):,}**. "
        "El histórico se acumula día a día con cada ingesta."
    )
else:
    st.info("Todavía no hay histórico de seguidores cargado en la base.")

st.markdown("---")

# ── 2) Evolución de la audiencia de NO-seguidores ───────────────────
st.subheader("🌐 Evolución de la audiencia de no-seguidores — por portal")

_series_nf, _series_tot = {}, {}
for d in activos:
    rt = _df_seguro(_wr.reach_by_follow_type, d["nombre"])
    if rt.empty:
        continue
    rt = rt.assign(metric_date=lambda x: pd.to_datetime(x["metric_date"]))
    piv = rt.pivot_table(index="metric_date", columns="follow_type",
                         values="reach_value", aggfunc="sum").fillna(0)
    if "non_follower" in piv.columns:
        _series_nf[d["nombre"]] = piv["non_follower"]
    _series_tot[d["nombre"]] = piv.sum(axis=1)

if _series_nf:
    df_nf = pd.concat(_series_nf, axis=1).sort_index().fillna(0)
    orden = df_nf.sum().sort_values(ascending=False).index.tolist()
    fig_nf = go.Figure()
    for i, nombre in enumerate(orden):
        fig_nf.add_trace(go.Scatter(
            x=df_nf.index, y=df_nf[nombre], name=nombre,
            mode="lines", stackgroup="one",
            line=dict(width=0.5, color=_color_portal(nombre, i)),
            fillcolor=_color_portal(nombre, i),
            hovertemplate="%{y:,.0f}<extra>" + nombre + "</extra>"))
    fig_nf.update_layout(
        margin=dict(l=0, r=0, t=10, b=80), height=340,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.2, font=dict(size=10.5)),
        yaxis=dict(title="No-seguidores alcanzados",
                   gridcolor="rgba(255,255,255,0.08)", tickformat=".2s"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
        hovermode="x unified")
    st.plotly_chart(fig_nf, width='stretch')

    # Aporte % de no-seguidores al alcance total (global por día)
    df_tot = pd.concat(_series_tot, axis=1).sort_index().fillna(0)
    idx = df_nf.index.union(df_tot.index)
    nf_tot = df_nf.reindex(idx).fillna(0).sum(axis=1)
    al_tot = df_tot.reindex(idx).fillna(0).sum(axis=1)
    pct = (nf_tot / al_tot.where(al_tot > 0)).dropna() * 100
    if not pct.empty:
        fig_pct = go.Figure(go.Scatter(
            x=pct.index, y=pct.values, mode="lines+markers",
            line=dict(color="#38bdf8", width=2), name="% no-seguidores"))
        fig_pct.update_layout(
            margin=dict(l=0, r=0, t=10, b=0), height=200,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="% del alcance total", gridcolor="rgba(255,255,255,0.08)",
                       ticksuffix="%"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.08)"))
        st.plotly_chart(fig_pct, width='stretch')
    st.caption(
        "🌐 Personas alcanzadas que **no** te siguen (alcance IG con desglose "
        "`follow_type`), apiladas por portal. La línea inferior muestra qué "
        "porcentaje del alcance total diario proviene de no-seguidores: un valor "
        "alto indica contenido que se expande más allá de tu base."
    )
else:
    st.info(
        "🛠️ La audiencia de no-seguidores se nutre de una tabla nueva del "
        "warehouse que se llena con la ingesta. Apenas corra (automática de "
        "madrugada o disparo manual), este gráfico empieza a acumular histórico."
    )

st.markdown("---")

# ── 3) Demografía de la audiencia (Instagram) ───────────────────────
st.subheader("🧭 Demografía de la audiencia — Instagram")

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
        f"Demografía de **{_aud_label.lower()}** por **{_bd_label.lower()}**, "
        "agregando todos los portales con Instagram. *Seguidores* = tu base; "
        "*Audiencia que interactúa* incluye también a no-seguidores. "
        "Meta solo entrega demografía para cuentas con ≥100 seguidores."
    )
else:
    st.info(
        "🛠️ La demografía (geo · edad · género) se llena con la ingesta nueva. "
        "Tras la próxima corrida vas a ver acá la distribución de seguidores y de "
        "la audiencia que interactúa. Requiere cuentas con ≥100 seguidores."
    )

st.markdown("---")

# ── Ranking por visualizaciones ─────────────────────────────────────
st.subheader("🏆 Ranking de portales por visualizaciones totales")

if activos:
    df_rank = pd.DataFrame([
        {"Portal": d["nombre"], "Facebook": d["fb_imp"], "Instagram": d["ig_imp"],
         "Total": d["total_imp"]}
        for d in sorted(activos, key=lambda x: x["total_imp"], reverse=True)
    ])

    # Solo el gráfico FB vs IG (sin el duplicado de Total)
    df_melt = df_rank.melt(id_vars="Portal", value_vars=["Facebook","Instagram"],
                           var_name="Red", value_name="Alcance")
    fig2 = px.bar(df_melt, x="Alcance", y="Portal", color="Red", orientation="h",
                  color_discrete_map={"Facebook":"#1877F2","Instagram":"#E1306C"},
                  barmode="group")
    fig2.update_layout(margin=dict(l=0,r=0,t=10,b=0),
                       yaxis=dict(autorange="reversed"), legend_title="",
                       height=220)
    st.plotly_chart(fig2, width='stretch')

    st.markdown("---")

    # ── Tendencia de alcance diario combinada (escala logarítmica) ─────
    st.subheader("📈 Tendencia de alcance diario — todos los portales")

    # Colores por portal (iguales al brief)
    PORTAL_COLOR = {
        "Chubut Noticias": "#E2E8F0",  # blanco/gris claro (tema oscuro)
        "Atento Chubut":   "#0EA5E9",  # celeste
        "La Calle Online": "#EA580C",  # naranja
        "El Americano":    "#22C55E",  # verde
    }
    FALLBACK = ["#a855f7","#fbbf24","#14b8a6"]

    # Calcular fecha de inicio global (para marcar portales con datos tardíos)
    from datetime import datetime as _dt, timedelta as _td
    fecha_inicio_global = (_dt.now() - _td(days=29)).strftime("%Y-%m-%d")

    fig_trend = go.Figure()
    notas_inicio = []   # para el caption explicativo
    fallback_i = 0

    for d in activos:
        color = PORTAL_COLOR.get(d["nombre"])
        if not color:
            color = FALLBACK[fallback_i % len(FALLBACK)]
            fallback_i += 1

        # IG = línea continua + marcadores en cada punto
        if d["ig_daily"]:
            items_ig = sorted(d["ig_daily"].items())
            fechas_ig = [k for k,v in items_ig]
            vals_ig   = [v for k,v in items_ig]
            primer_ig = fechas_ig[0] if fechas_ig else None
            # Nombre con fecha de inicio si arranca tarde
            nombre_ig = d["nombre"] + " (IG)"
            if primer_ig and primer_ig > fecha_inicio_global:
                dia = _dt.strptime(primer_ig, "%Y-%m-%d").strftime("%-d/%-m") if hasattr(_dt, 'strftime') else primer_ig[8:10]+"/"+primer_ig[5:7]
                nombre_ig += f" · desde {primer_ig[8:10]}/{primer_ig[5:7]}"
                notas_inicio.append(f"**{d['nombre']} IG**: datos desde {primer_ig[8:10]}/{primer_ig[5:7]}")
            fig_trend.add_trace(go.Scatter(
                x=fechas_ig, y=vals_ig,
                mode="lines+markers",
                name=nombre_ig,
                connectgaps=False,
                line=dict(color=color, width=2),
                marker=dict(size=4, color=color, opacity=0.7),
                opacity=0.95
            ))

        # FB = línea punteada + marcadores pequeños
        if d["fb_daily"]:
            items_fb = sorted(d["fb_daily"].items())
            fechas_fb = [k for k,v in items_fb]
            vals_fb   = [v for k,v in items_fb]
            primer_fb = fechas_fb[0] if fechas_fb else None
            nombre_fb = d["nombre"] + " (FB)"
            if primer_fb and primer_fb > fecha_inicio_global:
                nombre_fb += f" · desde {primer_fb[8:10]}/{primer_fb[5:7]}"
                notas_inicio.append(f"**{d['nombre']} FB**: datos desde {primer_fb[8:10]}/{primer_fb[5:7]}")
            fig_trend.add_trace(go.Scatter(
                x=fechas_fb, y=vals_fb,
                mode="lines+markers",
                name=nombre_fb,
                connectgaps=False,
                line=dict(color=color, width=1.5, dash="dot"),
                marker=dict(size=3, color=color, opacity=0.5),
                opacity=0.7
            ))

    # Verificar si realmente hay brechas significativas en los datos
    from datetime import datetime as _dt2
    _hoy = _dt2.now()
    tiene_brechas = any(
        len(d.get("ig_daily", {})) < 25
        for d in activos if d.get("ig_daily")
    )

    fig_trend.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.12,
            xanchor="left",
            x=0,
            font=dict(size=10.5),
            bgcolor="rgba(0,0,0,0)",
            title=None,
        ),
        margin=dict(l=0, r=0, t=10, b=130),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)", showgrid=True),
        yaxis=dict(
            type="log",
            title="Alcance (escala log.)",
            gridcolor="rgba(255,255,255,0.08)",
            tickformat=".2s",
        ),
        hovermode="x unified",
    )
    st.plotly_chart(fig_trend, width='stretch')

    # Nota explicativa — solo lo relevante
    partes = [
        "📐 **Escala logarítmica**: cada división = 10× el valor anterior, "
        "permite comparar portales con audiencias muy distintas.",
        "**Línea continua** = Instagram (reproducciones diarias) · **Punteada** = Facebook (alcance único).",
    ]
    if tiene_brechas:
        partes.append("Los puntos (•) marcan días con dato; una brecha indica día sin datos.")
    if notas_inicio:
        partes.append(
            "⚠️ Inicio tardío: " + " | ".join(notas_inicio) +
            " — Meta solo provee histórico desde la conexión al panel."
        )
    partes.append(
        "ℹ️ Los datos del día actual pueden no estar disponibles para todos los portales "
        "hasta que la API los procese (suele tardar horas)."
    )
    st.caption("  \n".join(partes))

    st.markdown("---")

    # ── Histórico acumulado desde el warehouse (MotherDuck) ──────────
    # A diferencia del gráfico de arriba (API en vivo, máx 30 días), este se
    # nutre de la base histórica y sigue creciendo indefinidamente día a día.
    st.subheader("📈 Alcance diario — histórico acumulado (base de datos)")
    try:
        import warehouse.reader as wreader

        fig_hist = go.Figure()
        _fi = 0
        hay_hist = False
        for d in activos:
            color = PORTAL_COLOR.get(d["nombre"])
            if not color:
                color = FALLBACK[_fi % len(FALLBACK)]
                _fi += 1

            # IG = alcance (reach) diario · línea continua
            df_ig = wreader.daily_metric(d["nombre"], "ig", "reach")
            if not df_ig.empty:
                hay_hist = True
                fig_hist.add_trace(go.Scatter(
                    x=df_ig["metric_date"], y=df_ig["metric_value"],
                    mode="lines+markers", name=d["nombre"] + " (IG)",
                    connectgaps=False,
                    line=dict(color=color, width=2),
                    marker=dict(size=4, color=color, opacity=0.7),
                ))

            # FB = alcance único diario · línea punteada
            df_fb = wreader.daily_metric(d["nombre"], "fb", "page_impressions_unique")
            if not df_fb.empty:
                hay_hist = True
                fig_hist.add_trace(go.Scatter(
                    x=df_fb["metric_date"], y=df_fb["metric_value"],
                    mode="lines+markers", name=d["nombre"] + " (FB)",
                    connectgaps=False,
                    line=dict(color=color, width=1.5, dash="dot"),
                    marker=dict(size=3, color=color, opacity=0.5),
                ))

        if hay_hist:
            fig_hist.update_layout(
                showlegend=True,
                legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left",
                            x=0, font=dict(size=10.5), bgcolor="rgba(0,0,0,0)", title=None),
                margin=dict(l=0, r=0, t=10, b=130),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="rgba(255,255,255,0.08)", showgrid=True),
                yaxis=dict(type="log", title="Alcance (escala log.)",
                           gridcolor="rgba(255,255,255,0.08)", tickformat=".2s"),
                hovermode="x unified",
            )
            st.plotly_chart(fig_hist, width='stretch')
            st.caption(
                "🗄️ A diferencia del gráfico anterior (API en vivo, máximo 30 días), "
                "este se nutre de la base de datos histórica: se actualiza cada día y "
                "**va a seguir creciendo indefinidamente**, acumulando todo el histórico."
            )
        else:
            st.info("La base histórica todavía no tiene datos de alcance para mostrar.")

    except Exception:
        st.info(
            "📦 La base de datos histórica todavía no está conectada. Agregá "
            "`MOTHERDUCK_TOKEN` en los *secrets* de Streamlit (Settings → Secrets) "
            "para ver el histórico acumulado que se va guardando cada día."
        )

    st.markdown("---")

    # ── Segmentación por tipo de contenido (IG, todos los portales) ─
    st.subheader("🎬 Tipo de contenido más efectivo — Instagram (todos los portales)")

    todos_posts_ig = []
    for d in activos:
        for post in d["posts_ig"]:
            todos_posts_ig.append({**post, "portal": d["nombre"]})

    if todos_posts_ig:
        df_posts = pd.DataFrame(todos_posts_ig)

        col_tipo1, col_tipo2 = st.columns(2)
        with col_tipo1:
            res_tipo = df_posts.groupby("tipo").agg(
                count=("likes","count"),
                avg_likes=("likes","mean"),
                avg_plays=("plays","mean"),
                total_reach=("reach","sum")
            ).reset_index()
            res_tipo["tipo_label"] = res_tipo["tipo"].map(
                {"reel":"🎬 Reel","video":"▶️ Video","image":"📷 Imagen","carousel_album":"🖼️ Carrusel"}).fillna(res_tipo["tipo"])
            fig_t = px.bar(res_tipo, x="tipo_label", y="avg_plays",
                           title="Plays/Alcance promedio por tipo",
                           color="tipo_label",
                           color_discrete_sequence=["#c026d3","#7c3aed","#0ea5e9","#f59e0b"])
            fig_t.update_layout(showlegend=False, margin=dict(l=0,r=0,t=40,b=0), xaxis_title="")
            st.plotly_chart(fig_t, width='stretch')

        with col_tipo2:
            fig_pie = px.pie(res_tipo, values="count", names="tipo_label",
                             title="Distribución de contenido publicado",
                             color_discrete_sequence=["#c026d3","#7c3aed","#0ea5e9","#f59e0b"])
            fig_pie.update_layout(margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig_pie, width='stretch')

        # ── Top 10 IG último mes ─────────────────────────────────
        st.markdown("---")
        st.subheader("📸 Top 10 publicaciones Instagram — último mes")
        # Usar all_media_ig (hasta 500 posts) filtrado a 30 días, ordenado por likes
        # posts_ig solo tiene 25 posts recientes y puede perder posts virales más viejos
        from datetime import timedelta
        limite_ig = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        todos_30d_ig = []
        for d in activos:
            for post in d.get("all_media_ig", []):
                if post.get("ts", "") >= limite_ig:
                    todos_30d_ig.append({**post, "portal": d["nombre"]})

        # Fallback: si no hay all_media_ig, usar posts_ig
        fuente_30d = todos_30d_ig if todos_30d_ig else todos_posts_ig
        top10_ig = sorted(fuente_30d, key=lambda x: x.get("likes", 0), reverse=True)[:10]

        if top10_ig:
            for i, post in enumerate(top10_ig, 1):
                icono = "🎬" if post["tipo"]=="reel" else "▶️" if post["tipo"]=="video" else "🖼️" if post["tipo"]=="carousel_album" else "📷"
                with st.container(border=True):
                    cols = st.columns([0.4, 3.5, 1, 1, 0.5])
                    cols[0].markdown(f"**#{i}**")
                    cols[1].markdown(f"{icono} **{post['portal']}** · `{post['ts']}`  \n{post.get('caption','')[:100]}")
                    cols[2].metric("❤️ Likes",       f"{post.get('likes',0):,}")
                    cols[3].metric("💬 Comentarios", f"{post.get('comments',0):,}")
                    cols[4].markdown(f"[🔗]({post.get('permalink','')})" if post.get("permalink") else "")
        else:
            st.info("Sin datos de publicaciones en los último mes.")

    # ── Top 10 FB último mes ─────────────────────────────────────
    st.markdown("---")
    st.subheader("📘 Top 10 publicaciones Facebook — último mes")
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
                    "likes":   likes,
                    "comentarios": com,
                    "compartidos": shares,
                    "engagement": likes + com + shares,
                })
            except:
                pass

    if todos_posts_fb:
        top10_fb = sorted(todos_posts_fb, key=lambda x: x["engagement"], reverse=True)[:10]
        for i, post in enumerate(top10_fb, 1):
            with st.container(border=True):
                cols = st.columns([0.4, 3.5, 1, 1, 1])
                cols[0].markdown(f"**#{i}**")
                cols[1].markdown(f"📘 **{post['portal']}** · `{post['fecha']}`  \n{post['mensaje']}")
                cols[2].metric("❤️ Likes",       f"{post['likes']:,}")
                cols[3].metric("💬 Comentarios", f"{post['comentarios']:,}")
                cols[4].metric("🔁 Compartidos", f"{post['compartidos']:,}")
    else:
        st.info("Sin datos de publicaciones de Facebook en los último mes.")

else:
    st.info("No hay portales activos con datos disponibles aún.")
