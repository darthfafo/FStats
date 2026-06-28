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
    color: #94a3b8;
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
.kpi-grid { display: flex; gap: 14px; flex-wrap: wrap; margin: 4px 0 22px 0; }
.kpi-card {
    flex: 1 1 165px;
    background: linear-gradient(135deg, #0f172a, #1e3a5f);
    border: 1px solid rgba(148,163,184,0.12);
    border-radius: 14px;
    padding: 16px 18px;
}
.kpi-card .k-label {
    color: #e2e8f0; font-size: 11.5px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase;
}
.kpi-card .k-value {
    color: #fff; font-size: clamp(22px, 4vw, 30px); font-weight: 800;
    line-height: 1.1; margin-top: 6px;
}
/* Subtítulo legible (claro) en cualquier tema, porque la tarjeta es oscura fija */
.kpi-card .k-sub { color: #cbd5e1; font-size: 11.5px; margin-top: 4px; }

/* st.container(border=True) con look de tarjeta (Detalle por portal) */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px !important;
    border-color: rgba(148,163,184,0.18) !important;
    background: rgba(148,163,184,0.04);
}

/* Tarjetas de portal: mismo azul que los KPI de arriba, con texto claro */
div[class*="st-key-pcard"] {
    background: linear-gradient(135deg, #0f172a, #1e3a5f) !important;
    border: 1px solid rgba(148,163,184,0.20) !important;
    border-radius: 14px !important;
}
div[class*="st-key-pcard"] h4,
div[class*="st-key-pcard"] [data-testid="stMarkdownContainer"],
div[class*="st-key-pcard"] [data-testid="stMetricValue"] { color: #f1f5f9 !important; }
div[class*="st-key-pcard"] [data-testid="stMetricLabel"] * { color: #cbd5e1 !important; }

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

PORTALES_ACTIVOS = [p for p in PORTALES if portal_activo(p) and not p.get("oculto")]

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
        # Visualizaciones de FB = reproducciones de video (reels/videos), no las
        # vistas de perfil (page_views_total), que son un número ínfimo.
        res["fb_imp"]    = imp_fb.get("video_views", 0)
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
gran_total_imp   = sum(r["total_imp"]   for r in resumenes)
gran_total_ig    = sum(r.get("ig_imp", 0) for r in resumenes)   # visualizaciones de IG
gran_total_fb    = sum(r.get("fb_imp", 0) for r in resumenes)   # reproducciones de video de FB
gran_total_seg   = sum(r["total_seg"]   for r in resumenes)
gran_total_eng   = sum(r.get("fb_eng",0) + r.get("ig_engaged",0) for r in resumenes)
gran_total_reach = sum(r.get("ig_reach", 0) for r in resumenes)  # personas únicas (reach real de IG)

# Crecimiento neto de seguidores en ~30 días, leído de la base histórica (FB+IG,
# sumando por portal). Usa la mayor ventana disponible hasta 30 días; None si la
# base todavía no tiene dos fotos para comparar.
import warehouse.reader as _wr
def _crecimiento_seguidores(dias=30):
    total, hubo = 0, False
    for r in resumenes:
        for plat in ("fb", "ig"):
            try:
                h = _wr.followers_history(r["nombre"], plat)
            except Exception:
                continue
            if h is None or h.empty:
                continue
            vals = (h.dropna(subset=["followers_count"]).sort_values("snapshot_date")
                      ["followers_count"].astype(int).tolist())
            if len(vals) < 2:
                continue
            w = min(dias, len(vals) - 1)
            total += vals[-1] - vals[-1 - w]
            hubo = True
    return total if hubo else None
crec_seg  = _crecimiento_seguidores()
crec_str  = f"{crec_seg:+,}" if crec_seg is not None else "—"
crec_sub  = ("Seguidores netos ganados en ~30 días (FB + IG)"
             if crec_seg is not None else "Necesita histórico cargado")

# ── HERO — Total de visualizaciones ────────────────────────────────
st.markdown(f"""
<div class="hero">
    <div class="label">🎯 Total visualizaciones — Últimos 30 días — Todas las fuentes</div>
    <div class="total">{gran_total_imp:,}</div>
    <div class="sub">📸 {gran_total_ig:,} de Instagram · 📘 {gran_total_fb:,} de Facebook · {len(PORTALES_ACTIVOS)} portal(es)</div>
</div>
""", unsafe_allow_html=True)

# ── KPIs en tarjetas azules (estilo dashboard) ─────────────────────
st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card"><div class="k-label">🎯 Alcance</div>
    <div class="k-value">{gran_total_reach:,}</div><div class="k-sub">Personas distintas alcanzadas en el mes (reach de Instagram)</div></div>
  <div class="kpi-card"><div class="k-label">📈 Crecimiento</div>
    <div class="k-value">{crec_str}</div><div class="k-sub">{crec_sub}</div></div>
  <div class="kpi-card"><div class="k-label">💬 Engagement</div>
    <div class="k-value">{gran_total_eng:,}</div><div class="k-sub">Interacciones del mes (FB + IG): reacciones, comentarios, compartidos</div></div>
  <div class="kpi-card"><div class="k-label">👥 Seguidores</div>
    <div class="k-value">{gran_total_seg:,}</div><div class="k-sub">Audiencia total propia hoy (FB + IG)</div></div>
</div>
""", unsafe_allow_html=True)

with st.expander("📖 Qué significa cada dato"):
    st.markdown(
        "- **🎯 Total visualizaciones:** cuánto se *vio* el contenido de toda la red en "
        "30 días — visualizaciones de Instagram (reproducciones de reels/videos/fotos) "
        "+ vistas de página de Facebook. Es el termómetro de difusión general; cuenta "
        "**reproducciones**, no personas.\n"
        "- **🎯 Alcance:** a cuántas **personas distintas** llegó la red en el mes "
        "(reach real de Instagram). A diferencia de las visualizaciones, cuenta "
        "**personas**, no reproducciones (una persona que vio 5 veces cuenta 1).\n"
        "- **📈 Crecimiento:** cuántos seguidores **netos** ganó (o perdió) la red en "
        "los últimos ~30 días, sumando Facebook + Instagram. En verde si creció.\n"
        "- **💬 Engagement:** total de **interacciones** del mes (reacciones, comentarios "
        "y compartidos, FB + IG). Mide qué tan involucrada está la audiencia, no solo "
        "cuánta gente la ve.\n"
        "- **👥 Seguidores:** el tamaño de tu **audiencia propia** hoy (suma de "
        "seguidores de Facebook + Instagram de todos los portales)."
    )

st.markdown("---")
st.subheader("🔍 Cada portal bajo la lupa")
st.markdown(
    "El desempeño de cada marca por separado: sus visualizaciones del mes, su alcance, "
    "engagement y seguidores (Facebook + Instagram), y cuánto pesa en el total de la "
    "red. Tocá **Ver estadísticas** para entrar al detalle completo de cada una."
)

# ── Banner por portal: uno full-width por portal, apilados, cada uno con el
# color de su marca (borde + tinte). Aprovecha el ancho y despliega FB/IG sin
# amontonar. En el celular las columnas se apilan solas. ───────────────────────
COLOR_PORTAL = {
    "Chubut Noticias": "#64748b", "Atento Chubut": "#22d3ee",
    "La Calle Online": "#f97316", "El Americano": "#22c55e",
    "Viste esto?":     "#a855f7", "Boca en Linea": "#fbbf24",
}
_PAL_BANNER = ["#38bdf8", "#a855f7", "#f472b6", "#fbbf24", "#14b8a6"]
def _color_banner(nombre, i):
    return COLOR_PORTAL.get(nombre) or _PAL_BANNER[i % len(_PAL_BANNER)]

_css_banner = """
[class*="st-key-pbanner_"] { padding: 16px 22px !important; margin-bottom: 14px !important; overflow: hidden; }
/* Contenido en una fila flexible que se reacomoda sola: en compu todo en una
   línea; en el celular el bloque principal toma el ancho y los stats se acomodan
   abajo en una grilla (en vez de apilarse feo de a uno). */
.pb-row { display:flex; flex-wrap:wrap; align-items:center; gap:10px 18px; }
.pb-main { flex:0 1 200px; }
.pb-head { display:flex; align-items:center; gap:8px; margin-bottom:2px; }
.pb-icon { font-size:1.35rem; }
.pb-name { font-size:1.2rem; font-weight:800; line-height:1.15; }
.pb-label { color:#cbd5e1; font-size:0.7rem; font-weight:600; text-transform:uppercase; letter-spacing:0.6px; }
.pb-num { color:#fff; font-size:clamp(1.7rem,2.4vw,2.3rem); font-weight:900; line-height:1.05; white-space:nowrap; }
.pb-pct { color:#cbd5e1; font-size:0.8rem; margin-top:2px; }
.pb-stat { flex:0 1 auto; min-width:94px; }
.pb-stat-label { color:#cbd5e1; font-size:0.8rem; font-weight:700; }
.pb-stat-val { color:#fff; font-size:clamp(1.1rem,1.6vw,1.45rem); font-weight:800; line-height:1.1; margin-top:1px; white-space:nowrap; }
.pb-stat-sub { color:#cbd5e1; font-size:0.72rem; }
"""
_css_colores = ""
for i, r in enumerate(resumenes):
    _c = _color_banner(r["nombre"], i)
    # Si el acento es gris (Chubut), el nombre va casi blanco para que se lea.
    _name_c = "#e2e8f0" if _c == "#64748b" else _c
    _css_colores += (
        # Fondo oscuro propio (isla) con el color de la marca tiñendo desde la
        # izquierda: se lee bien en tema claro y oscuro, igual que las KPI cards.
        f".st-key-pbanner_{i} {{ border:1px solid rgba(148,163,184,0.20) !important; "
        f"border-left:6px solid {_c} !important; "
        f"background:linear-gradient(90deg,{_c}40,#0f172a 42%) !important; }}"
        f".st-key-pbanner_{i} .pb-name {{ color:{_name_c}; }}"
    )
st.markdown(f"<style>{_css_banner}{_css_colores}</style>", unsafe_allow_html=True)

for i, resumen in enumerate(resumenes):
    pct     = (resumen["total_imp"] / gran_total_imp * 100) if gran_total_imp else 0
    eng_tot = resumen.get("fb_eng", 0) + resumen.get("ig_engaged", 0)
    with st.container(border=True, key=f"pbanner_{i}"):
        c_content, c_btn = st.columns([6.2, 1.3], vertical_alignment="center")
        with c_content:
            st.markdown(
                '<div class="pb-row">'
                  '<div class="pb-main">'
                    f'<div class="pb-head"><span class="pb-icon">{resumen["icono"]}</span>'
                    f'<span class="pb-name">{resumen["nombre"]}</span></div>'
                    '<div class="pb-label">Visualizaciones · último mes</div>'
                    f'<div class="pb-num">{resumen["total_imp"]:,}</div>'
                    f'<div class="pb-pct">{pct:.1f}% de la difusión de la red</div>'
                  '</div>'
                  '<div class="pb-stat"><div class="pb-stat-label">🎯 Alcance</div>'
                    f'<div class="pb-stat-val">{resumen.get("ig_reach", 0):,}</div>'
                    '<div class="pb-stat-sub">personas únicas</div></div>'
                  '<div class="pb-stat"><div class="pb-stat-label">💬 Engagement</div>'
                    f'<div class="pb-stat-val">{eng_tot:,}</div>'
                    '<div class="pb-stat-sub">interacciones</div></div>'
                  '<div class="pb-stat"><div class="pb-stat-label">👥 Seguidores</div>'
                    f'<div class="pb-stat-val">{resumen["total_seg"]:,}</div>'
                    '<div class="pb-stat-sub">FB + IG</div></div>'
                '</div>',
                unsafe_allow_html=True)
        with c_btn:
            if st.button("Ver estadísticas →", key=f"btn_{i}",
                         use_container_width=True, type="primary"):
                st.switch_page(resumen["pagina"])

# ── Participación de cada portal — barra minimalista de porciones ─────
if len(resumenes) > 1:
    st.markdown("---")
    st.subheader("📊 Participación de cada portal en las visualizaciones")
    st.caption(
        "Cuánto aporta cada portal al total de visualizaciones de la red. "
        "El ancho de cada porción es proporcional a su aporte."
    )

    partes = sorted([r for r in resumenes if r["total_imp"] > 0],
                    key=lambda r: r["total_imp"], reverse=True)
    total_part = sum(r["total_imp"] for r in partes)
    if partes and total_part:
        _PAL = ["#0EA5E9", "#a855f7", "#EA580C", "#22C55E", "#f472b6", "#fbbf24"]
        segs, leyenda = "", ""
        for i, r in enumerate(partes):
            p   = r["total_imp"] / total_part * 100
            col = _PAL[i % len(_PAL)]
            # etiqueta adentro solo si la porción es lo bastante ancha
            dentro = (f'{r["nombre"]} · {p:.0f}%' if p >= 12
                      else (f'{p:.0f}%' if p >= 4 else ""))
            segs += (f'<div title="{r["nombre"]}: {r["total_imp"]:,} ({p:.1f}%)" '
                     f'style="width:{p}%;background:{col};display:flex;align-items:center;'
                     f'justify-content:center;color:#fff;font-size:0.8rem;font-weight:700;'
                     f'white-space:nowrap;overflow:hidden;padding:0 2px">{dentro}</div>')
            leyenda += (f'<span style="display:inline-flex;align-items:center;gap:6px;'
                        f'margin:0 16px 6px 0;font-size:0.85rem;color:var(--text-color);opacity:0.85">'
                        f'<span style="width:12px;height:12px;border-radius:3px;'
                        f'background:{col};display:inline-block"></span>'
                        f'{r["nombre"]} · {r["total_imp"]:,} ({p:.1f}%)</span>')
        st.markdown(
            f'<div style="display:flex;height:52px;border-radius:10px;overflow:hidden;'
            f'gap:2px;margin-top:4px">{segs}</div>'
            f'<div style="margin-top:12px;line-height:1.9">{leyenda}</div>',
            unsafe_allow_html=True)
    else:
        st.info("Todavía no hay visualizaciones cargadas para mostrar la participación.")

# El informe PDF se genera ahora desde la página de Estadísticas Globales, así la
# barra lateral queda igual en todas las páginas (solo la navegación).
