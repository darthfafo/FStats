import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from config import PORTALES, fb_source, ig_source, sidebar_nav
import importlib, pdf_report as _pdf_mod
from datetime import timedelta

def generar_brief(resumenes, totales, top_ig=None, top_fb=None):
    importlib.reload(_pdf_mod)
    return _pdf_mod.generar_brief(resumenes, totales, top_ig=top_ig, top_fb=top_fb)

@st.cache_data(ttl=3600)
def cargar_posts_pdf(nombre, page_id, ig_id, access_token, ig_only, live=False):
    """Carga posts para el PDF (solo se llama al generar)."""
    posts_ig, posts_fb = [], []
    limite_str = (datetime.now() - timedelta(days=31)).strftime("%Y-%m-%d")
    limite_dt  = datetime.now() - timedelta(days=31)
    try:
        ig = ig_source(nombre, ig_id, access_token, live)
        # Obtener plays (visualizaciones) por ID exacto del post
        plays_lookup = {}
        try:
            imp_data = ig.get_media_impressions(limit=200, days=35)
            for pd_item in imp_data.get("posts_data", []):
                post_id = pd_item.get("id", "")
                if post_id:
                    # plays para Reels, reach para otros
                    val = pd_item.get("plays", 0) or pd_item.get("reach", 0)
                    plays_lookup[post_id] = val
        except Exception:
            pass
        all_m = ig.get_all_media(max_posts=500)
        for p in all_m.get("data", []):
            ts = p.get("timestamp", "")[:10]
            if ts >= limite_str:
                post_id = p.get("id", "")
                posts_ig.append({
                    "portal":    nombre,
                    "ts":        ts,
                    "tipo":      "reel" if p.get("product_type") == "clips"
                                 else p.get("media_type", "IMAGE").lower(),
                    "likes":     p.get("like_count", 0),
                    "comments":  p.get("comments_count", 0),
                    "plays":     plays_lookup.get(post_id, 0),
                    "caption":   (p.get("caption") or "")[:80],
                    "permalink": p.get("permalink", ""),
                })
    except Exception as e:
        print(f"[{nombre}] PDF IG posts: {e}")
    if not ig_only:
        try:
            fb = fb_source(nombre, page_id, access_token, live)
            raw = fb.get_recent_posts(limit=50)
            for p in raw.get("data", []):
                try:
                    fecha = datetime.strptime(p.get("created_time", "")[:10], "%Y-%m-%d")
                    if fecha < limite_dt:
                        continue
                    reac  = p.get("reactions") or p.get("likes") or {}
                    likes = reac.get("summary", {}).get("total_count", 0)
                    com   = p.get("comments", {}).get("summary", {}).get("total_count", 0)
                    shares= p.get("shares", {}).get("count", 0)
                    posts_fb.append({
                        "portal":      nombre,
                        "fecha":       p.get("created_time", "")[:10],
                        "mensaje":     (p.get("message") or "")[:80],
                        "likes":       likes,
                        "comentarios": com,
                        "compartidos": shares,
                        "engagement":  likes + com + shares,
                    })
                except Exception:
                    pass
        except Exception as e:
            print(f"[{nombre}] PDF FB posts: {e}")
    return posts_ig, posts_fb

st.set_page_config(
    page_title="Panel General",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
/* Ocultar navegación automática de Streamlit */
[data-testid="stSidebarNav"],
[data-testid="stSidebarNavItems"],
[data-testid="stSidebarNavSeparator"],
.css-1544g2n, .css-k1vhr4,
section[data-testid="stSidebar"] ul { display: none !important; }

.hero {
    background: linear-gradient(135deg, #0f172a, #1e3a5f);
    border-radius: 16px;
    padding: 32px 24px;
    text-align: center;
    margin-bottom: 24px;
}
.hero .label {
    color: #94a3b8;
    font-size: clamp(11px, 2vw, 14px);
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
}
.hero .total {
    color: white;
    font-size: clamp(36px, 10vw, 72px);
    font-weight: 900;
    line-height: 1;
    margin: 12px 0 8px 0;
    word-break: keep-all;
}
.hero .sub {
    color: #64748b;
    font-size: clamp(12px, 2vw, 15px);
}

/* Encabezado del panel */
.panel-head { margin: 4px 0 14px 0; }
.panel-head .h-title {
    color: #f8fafc; font-size: clamp(20px, 4vw, 30px); font-weight: 800;
    line-height: 1.15; margin: 0;
}
.panel-head .h-sub {
    color: #94a3b8; font-size: clamp(12px, 2vw, 14.5px); margin-top: 4px;
}

/* Tarjetas KPI azules (mismo estilo que el hero, en chico) */
.kpi-grid { display: flex; gap: 14px; flex-wrap: wrap; margin: 4px 0 6px 0; }
.kpi-card {
    flex: 1 1 165px;
    background: linear-gradient(135deg, #0f172a, #1e3a5f);
    border: 1px solid rgba(148,163,184,0.12);
    border-radius: 14px;
    padding: 16px 18px;
}
.kpi-card .k-label {
    color: #94a3b8; font-size: 11.5px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase;
}
.kpi-card .k-value {
    color: #fff; font-size: clamp(22px, 4vw, 30px); font-weight: 800;
    line-height: 1.1; margin-top: 6px;
}
.kpi-card .k-sub { color: #64748b; font-size: 11.5px; margin-top: 4px; }

/* Responsive: hero inline divs en portales */
@media (max-width: 768px) {
    div[style*="font-size:60px"], div[style*="font-size: 60px"] {
        font-size: 38px !important;
    }
    div[style*="font-size:56px"], div[style*="font-size: 56px"] {
        font-size: 34px !important;
    }
    div[style*="font-size:28px"], div[style*="font-size: 28px"] {
        font-size: 20px !important;
    }
    div[style*="justify-content:space-between"][style*="display:flex"] {
        flex-direction: column !important;
    }
    div[style*="gap:32px"] {
        gap: 16px !important;
        flex-wrap: wrap !important;
    }
    /* Padding en heroes de portales */
    div[style*="padding:28px 32px"] {
        padding: 20px 16px !important;
    }
}
</style>
""", unsafe_allow_html=True)

def portal_activo(p):
    pendientes = ("PENDIENTE", "", None)
    if p.get("ig_only"):
        return (p.get("access_token") not in pendientes and
                p.get("instagram_id") not in pendientes)
    return (p.get("access_token") not in pendientes and
            p.get("facebook_page_id") not in pendientes)

PORTALES_ACTIVOS = [p for p in PORTALES if portal_activo(p)]

# ── Sidebar (navegación unificada con el resto del panel) ──────────
sidebar_nav(current="")

# ── Carga de datos ─────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def cargar_resumen(nombre, page_id, ig_id, access_token, live=False):
    res = {
        "nombre":   nombre,
        "fb_imp":   0, "fb_reach": 0, "fb_seg": 0,
        "fb_eng":   0, "fb_vistas": 0,
        "ig_imp":   0, "ig_reach": 0, "ig_seg": 0, "ig_engaged": 0,
        "fb_daily": {}, "ig_daily": {}, "ig_daily_seg": {},
    }
    try:
        fb        = fb_source(nombre, page_id, access_token, live)
        info      = fb.get_page_info()
        res["fb_seg"] = info.get("followers_count", 0)
        imp_fb    = fb.get_posts_impressions()
        res["fb_imp"]    = imp_fb["total_imp"]
        res["fb_reach"]  = imp_fb["total_reach"]
        res["fb_eng"]    = imp_fb.get("engagement", 0)
        res["fb_vistas"] = imp_fb.get("vistas", 0)
        res["fb_daily"]  = imp_fb.get("daily", {})
    except Exception as e:
        print(f"[{nombre}] FB: {e}")
    try:
        ig        = ig_source(nombre, ig_id, access_token, live)
        info_ig   = ig.get_account_info()
        res["ig_seg"] = info_ig.get("followers_count", 0)
        imp_ig    = ig.get_media_impressions(limit=25)
        res["ig_imp"]       = imp_ig["total_imp"]
        res["ig_reach"]     = imp_ig["total_reach"]
        res["ig_engaged"]   = imp_ig.get("engaged", 0)
        res["ig_daily"]     = imp_ig.get("daily", {})
        res["ig_daily_seg"] = imp_ig.get("daily_followers", {})
    except Exception as e:
        print(f"[{nombre}] IG: {e}")

    res["total_imp"]   = res["fb_imp"]   + res["ig_imp"]
    res["total_reach"] = res["fb_reach"] + res["ig_reach"]
    res["total_seg"]   = res["fb_seg"]   + res["ig_seg"]
    res["total_eng"]   = res["fb_eng"]
    return res

live = st.session_state.get("fstats_live", False)
with st.spinner("Cargando datos de todos los portales..."):
    resumenes = []
    for p in PORTALES_ACTIVOS:
        if p.get("ig_only"):
            r = {"nombre": p["nombre"], "icono": p["icono"],
                 "fb_imp": 0, "fb_reach": 0, "fb_seg": 0, "fb_eng": 0, "fb_vistas": 0,
                 "ig_imp": 0, "ig_reach": 0, "ig_seg": 0, "ig_engaged": 0,
                 "fb_daily": {}, "ig_daily": {}, "ig_daily_seg": {},
                 "total_imp": 0, "total_reach": 0, "total_seg": 0, "total_eng": 0,
                 "pagina": p["pagina"]}
            try:
                ig = ig_source(p["nombre"], p["instagram_id"], p["access_token"], live)
                info_ig = ig.get_account_info()
                r["ig_seg"] = info_ig.get("followers_count", 0)
                imp_ig = ig.get_media_impressions(limit=25)
                r["ig_imp"]       = imp_ig["total_imp"]
                r["ig_reach"]     = imp_ig["total_reach"]
                r["ig_engaged"]   = imp_ig.get("engaged", 0)
                r["ig_daily"]     = imp_ig.get("daily", {})
                r["ig_daily_seg"] = imp_ig.get("daily_followers", {})
            except Exception as e:
                print(f"[{p['nombre']}] IG: {e}")
            r["total_imp"]   = r["ig_imp"]
            r["total_reach"] = r["ig_reach"]
            r["total_seg"]   = r["ig_seg"]
        else:
            r = cargar_resumen(p["nombre"], p["facebook_page_id"],
                               p["instagram_id"], p["access_token"], live)
            r["icono"]  = p["icono"]
            r["pagina"] = p["pagina"]
        resumenes.append(r)

# Totales globales
gran_total_imp = sum(r["total_imp"]   for r in resumenes)
gran_total_seg = sum(r["total_seg"]   for r in resumenes)
gran_total_eng = sum(r.get("fb_eng",0) + r.get("ig_engaged",0) for r in resumenes)
gran_total_fb  = sum(r["fb_imp"]      for r in resumenes)
gran_total_ig  = sum(r["ig_imp"]      for r in resumenes)
tasa_eng       = (gran_total_eng / gran_total_seg * 100) if gran_total_seg > 0 else 0

# ── Encabezado del panel ───────────────────────────────────────────
st.markdown(f"""
<div class="panel-head">
    <div class="h-title">📊 Panel general</div>
    <div class="h-sub">Resumen en vivo de toda la red — los números clave de los últimos 30 días,
    sumando {len(PORTALES_ACTIVOS)} portal(es) de Facebook e Instagram.</div>
</div>
""", unsafe_allow_html=True)

# ── HERO — Total de visualizaciones ────────────────────────────────
st.markdown(f"""
<div class="hero">
    <div class="label">🎯 Total visualizaciones — Últimos 30 días — Todas las fuentes</div>
    <div class="total">{gran_total_imp:,}</div>
    <div class="sub">Facebook alcance único + Instagram visualizaciones totales · {len(PORTALES_ACTIVOS)} portal(es)</div>
</div>
""", unsafe_allow_html=True)

# ── KPIs en tarjetas azules (estilo dashboard) ─────────────────────
st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card"><div class="k-label">📘 Facebook</div>
    <div class="k-value">{gran_total_fb:,}</div><div class="k-sub">Alcance único · 30d</div></div>
  <div class="kpi-card"><div class="k-label">📸 Instagram</div>
    <div class="k-value">{gran_total_ig:,}</div><div class="k-sub">Visualizaciones · 30d</div></div>
  <div class="kpi-card"><div class="k-label">💬 Engagement</div>
    <div class="k-value">{gran_total_eng:,}</div><div class="k-sub">Interacciones · 30d</div></div>
  <div class="kpi-card"><div class="k-label">👥 Seguidores</div>
    <div class="k-value">{gran_total_seg:,}</div><div class="k-sub">Audiencia propia (hoy)</div></div>
  <div class="kpi-card"><div class="k-label">📊 Tasa engagement</div>
    <div class="k-value">{tasa_eng:.1f}%</div><div class="k-sub">Engagement ÷ seguidores</div></div>
</div>
""", unsafe_allow_html=True)

with st.expander("📖 Qué significa cada dato"):
    st.markdown(
        "- **🎯 Total visualizaciones:** la suma de todo lo que se *vio* en la red en "
        "30 días — alcance único de Facebook + visualizaciones de Instagram. Es el "
        "termómetro de difusión general.\n"
        "- **📘 Facebook:** personas **únicas** alcanzadas en Facebook en el mes.\n"
        "- **📸 Instagram:** **visualizaciones** totales en Instagram (reproducciones de "
        "Reels, videos y fotos) del mes.\n"
        "- **💬 Engagement (30d):** interacciones con el contenido — reacciones, "
        "comentarios y compartidos. Mide qué tan involucrada está la audiencia.\n"
        "- **👥 Seguidores totales:** el tamaño de tu audiencia propia (FB + IG), foto "
        "de hoy.\n"
        "- **📊 Tasa de engagement:** engagement ÷ seguidores. Pone el engagement en "
        "contexto del tamaño de la audiencia."
    )

st.markdown("---")
st.subheader("📊 Detalle por portal")

# ── Tarjetas por portal ────────────────────────────────────────────
cols_portales = st.columns(max(len(resumenes), 1))

for i, resumen in enumerate(resumenes):
    with cols_portales[i]:
        with st.container(border=True):
            st.markdown(f"### {resumen['icono']} {resumen['nombre']}")

            st.metric("🎯 Personas alcanzadas",
                      f"{resumen['total_imp']:,}",
                      help="Facebook alcance único + Instagram visualizaciones — último mes")

            if gran_total_imp > 0:
                prop = resumen["total_imp"] / gran_total_imp
                st.progress(prop, text=f"{prop*100:.1f}% del total general")

            st.markdown("---")

            col_fb, col_ig = st.columns(2)
            with col_fb:
                st.markdown("**📘 Facebook**")
                st.markdown(f"Alcance único: **{resumen['fb_imp']:,}**")
                st.markdown(f"Engagement: **{resumen['fb_eng']:,}**")
                st.markdown(f"Seguidores: **{resumen['fb_seg']:,}**")
            with col_ig:
                st.markdown("**📸 Instagram**")
                st.markdown(f"Visualizaciones: **{resumen['ig_imp']:,}**")
                st.markdown(f"Alcance: **{resumen['ig_reach']:,}**")
                st.markdown(f"Seguidores: **{resumen['ig_seg']:,}**")

            st.markdown("")
            if st.button("Ver estadísticas completas →",
                         key=f"btn_{i}", use_container_width=True, type="primary"):
                st.switch_page(resumen["pagina"])

# ── Gráfico comparativo (cuando haya más de 1 portal) ─────────────
if len(resumenes) > 1:
    st.markdown("---")
    st.subheader("📊 Distribución de alcance entre portales")

    col_donut, col_bars = st.columns(2)

    with col_donut:
        df_donut = pd.DataFrame([
            {"Portal": r["nombre"], "Visualizaciones": r["total_imp"]}
            for r in resumenes
        ])
        fig_d = px.pie(
            df_donut, values="Visualizaciones", names="Portal",
            hole=0.55,
            color_discrete_sequence=["#1877F2", "#E1306C", "#16a34a", "#f59e0b"],
            title="Participación total"
        )
        fig_d.update_traces(textposition="outside", textinfo="percent+label")
        fig_d.update_layout(showlegend=False, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_d, width='stretch')

    with col_bars:
        df_dist = pd.DataFrame([
            {"Portal": r["nombre"], "Facebook": r["fb_imp"], "Instagram": r["ig_imp"]}
            for r in resumenes
        ])
        df_melt = df_dist.melt(id_vars="Portal", var_name="Red", value_name="Alcance")
        fig_b = px.bar(
            df_melt, x="Portal", y="Alcance", color="Red",
            color_discrete_map={"Facebook": "#1877F2", "Instagram": "#E1306C"},
            barmode="group", title="FB vs IG por portal"
        )
        fig_b.update_layout(margin=dict(l=0, r=0, t=40, b=0), legend_title="")
        st.plotly_chart(fig_b, width='stretch')

# El informe PDF se genera ahora desde la página de Estadísticas Globales, así la
# barra lateral queda igual en todas las páginas (solo la navegación).
