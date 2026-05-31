import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from config import PORTALES
from collectors.facebook import FacebookCollector
from collectors.instagram import InstagramCollector  # también usado para portales ig_only
import importlib, pdf_report as _pdf_mod
from datetime import timedelta

def generar_brief(resumenes, totales, top_ig=None, top_fb=None):
    importlib.reload(_pdf_mod)
    return _pdf_mod.generar_brief(resumenes, totales, top_ig=top_ig, top_fb=top_fb)

@st.cache_data(ttl=3600)
def cargar_posts_pdf(nombre, page_id, ig_id, access_token, ig_only):
    """Carga posts para el PDF (solo se llama al generar)."""
    posts_ig, posts_fb = [], []
    limite_str = (datetime.now() - timedelta(days=31)).strftime("%Y-%m-%d")
    limite_dt  = datetime.now() - timedelta(days=31)
    try:
        ig = InstagramCollector(ig_id=ig_id, access_token=access_token)
        # Obtener plays (visualizaciones) por ID exacto del post
        plays_lookup = {}
        try:
            imp_data = ig.get_media_impressions(limit=100)
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
            fb = FacebookCollector(page_id=page_id, access_token=access_token)
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
    /* Ocultar sidebar en mobile para dar más espacio */
    section[data-testid="stSidebar"] {
        display: none;
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

# ── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 Panel General")
    st.markdown("---")
    if st.button("🔄 Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown(f"*{datetime.now().strftime('%d/%m/%Y %H:%M')}*")
    st.markdown("---")
    st.caption(f"{len(PORTALES_ACTIVOS)} portal(es) activo(s)")

# ── Carga de datos ─────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def cargar_resumen(nombre, page_id, ig_id, access_token):
    res = {
        "nombre":   nombre,
        "fb_imp":   0, "fb_reach": 0, "fb_seg": 0,
        "fb_eng":   0, "fb_vistas": 0,
        "ig_imp":   0, "ig_reach": 0, "ig_seg": 0, "ig_engaged": 0,
        "fb_daily": {}, "ig_daily": {}, "ig_daily_seg": {},
    }
    try:
        fb        = FacebookCollector(page_id=page_id, access_token=access_token)
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
        ig        = InstagramCollector(ig_id=ig_id, access_token=access_token)
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
                ig = InstagramCollector(ig_id=p["instagram_id"], access_token=p["access_token"])
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
                               p["instagram_id"], p["access_token"])
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

# ── HERO — Alcance total ───────────────────────────────────────────
st.markdown(f"""
<div class="hero">
    <div class="label">🎯 Total visualizaciones — Últimos 30 días — Todas las fuentes</div>
    <div class="total">{gran_total_imp:,}</div>
    <div class="sub">Facebook alcance único + Instagram visualizaciones totales · {len(PORTALES_ACTIVOS)} portal(es)</div>
</div>
""", unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("📘 Facebook",              f"{gran_total_fb:,}",  help="Alcance único 30d")
c2.metric("📸 Instagram",             f"{gran_total_ig:,}",  help="Visualizaciones 30d")
c3.metric("💬 Engagement (30d)",      f"{gran_total_eng:,}", help="Likes + comentarios + compartidos en Facebook")
c4.metric("👥 Seguidores totales",    f"{gran_total_seg:,}")
c5.metric("📊 Tasa de engagement",    f"{tasa_eng:.2f}%",    help="Engagement FB / seguidores totales")

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

# ── Botón PDF — va aquí, después de que resumenes está disponible ────
with st.sidebar:
    st.markdown("---")
    if st.button("📄 Generar brief PDF", use_container_width=True, type="primary"):
        with st.spinner("Generando PDF... (puede tardar 30s por los posts)"):
            try:
                # Cargar posts de cada portal para el top 10
                all_posts_ig, all_posts_fb = [], []
                for p in PORTALES_ACTIVOS:
                    pig, pfb = cargar_posts_pdf(
                        p["nombre"], p.get("facebook_page_id"),
                        p.get("instagram_id"), p["access_token"],
                        p.get("ig_only", False)
                    )
                    all_posts_ig.extend(pig)
                    all_posts_fb.extend(pfb)

                pdf_bytes = generar_brief(
                    resumenes=resumenes,
                    totales={
                        "total_imp": gran_total_imp,
                        "total_seg": gran_total_seg,
                        "total_eng": gran_total_eng,
                        "total_fb":  gran_total_fb,
                        "total_ig":  gran_total_ig,
                    },
                    top_ig=all_posts_ig,
                    top_fb=all_posts_fb,
                )
                fecha = datetime.now().strftime("%Y%m%d")
                st.sidebar.download_button(
                    label="⬇️ Descargar informe",
                    data=pdf_bytes,
                    file_name=f"informe_fstats_{fecha}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.sidebar.error(f"Error: {e}")
