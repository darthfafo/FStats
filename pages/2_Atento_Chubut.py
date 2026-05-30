import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from config import PORTALES, RESPONSIVE_CSS
from collectors.facebook import FacebookCollector
from collectors.instagram import InstagramCollector

st.set_page_config(page_title="Atento Chubut", page_icon="📡", layout="wide")

st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)
st.markdown("""
<style>
.bloque-imp {
    border-radius: 14px; padding: 28px 24px; text-align: center;
}
.bloque-imp .label {
    color: #bfdbfe; font-size: 13px; font-weight: 700;
    letter-spacing: 1.5px; text-transform: uppercase;
}
.bloque-imp .valor {
    color: white; font-size: 56px; font-weight: 900;
    margin: 8px 0 4px 0; line-height: 1;
}
.bloque-imp .sub { color: #93c5fd; font-size: 13px; }
.pendiente-box {
    background: linear-gradient(135deg, #1e293b, #334155);
    border-radius: 14px; padding: 40px; text-align: center; margin: 20px 0;
}
</style>
""", unsafe_allow_html=True)

portal = next((p for p in PORTALES if p["nombre"] == "Atento Chubut"), None)

with st.sidebar:
    st.title("📡 Atento Chubut")
    st.markdown("---")
    if st.button("🏠 Panel general", use_container_width=True):
        st.switch_page("app.py")
    if st.button("🔄 Actualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption(datetime.now().strftime("%d/%m/%Y %H:%M"))

st.title("📡 Atento Chubut")
st.markdown("---")

# ── Verificar si las credenciales están configuradas ────────────────
def credenciales_ok(p):
    pendientes = ("PENDIENTE", "", None)
    return (
        p.get("access_token") not in pendientes and
        p.get("facebook_page_id") not in pendientes and
        p.get("instagram_id") not in pendientes
    )

if portal is None or not credenciales_ok(portal):
    st.markdown("""
    <div class="pendiente-box">
        <div style="font-size:64px; margin-bottom:16px">⏳</div>
        <div style="color:#94a3b8; font-size:13px; font-weight:700; letter-spacing:2px; text-transform:uppercase">
            Esperando credenciales
        </div>
        <div style="color:white; font-size:28px; font-weight:800; margin:12px 0">
            Atento Chubut — Pendiente de configuración
        </div>
        <div style="color:#64748b; font-size:15px">
            Una vez que el administrador envíe el token de acceso,<br>
            completá los datos en el archivo <code>.env</code> y el panel se activa automáticamente.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📋 Qué completar en `.env` cuando llegue el token")
    st.code("""# Atento Chubut
META_PAGE_ID_ATENTO=ID_NUMÉRICO_DE_LA_PÁGINA
META_INSTAGRAM_ID_ATENTO=ID_NUMÉRICO_DE_INSTAGRAM
META_PAGE_ACCESS_TOKEN_ATENTO=TOKEN_QUE_MANDE_EL_ADMIN""", language="bash")

    st.info("💡 El ID numérico de la página se consigue ejecutando `python diagnostico.py` una vez que el admin comparte el token.")
    st.stop()

# ── A partir de acá solo corre si las credenciales están configuradas ─

@st.cache_data(ttl=3600)
def cargar_fb(page_id, token):
    fb = FacebookCollector(page_id=page_id, access_token=token)
    return {
        "info":        fb.get_page_info(),
        "impresiones": fb.get_posts_impressions(),
        "fan_growth":  fb.get_fan_growth(),
        "posts":       fb.get_recent_posts(limit=100),
    }

@st.cache_data(ttl=3600)
def cargar_ig(ig_id, token):
    ig = InstagramCollector(ig_id=ig_id, access_token=token)
    return {
        "info":        ig.get_account_info(),
        "impresiones": ig.get_media_impressions(limit=25),
        "media":       ig.get_all_media(max_posts=500),
    }

# ── Hero combinado ──────────────────────────────────────────────────
with st.spinner("Cargando estadísticas..."):
    try:
        datos    = cargar_fb(portal["facebook_page_id"], portal["access_token"])
        error_fb = None
    except Exception as e:
        datos    = {"info": {}, "impresiones": {"total_imp": 0, "total_reach": 0, "daily": {}},
                    "fan_growth": {"data": []}, "posts": {"data": []}}
        error_fb = str(e)
    try:
        datos_ig = cargar_ig(portal["instagram_id"], portal["access_token"])
        error_ig = None
    except Exception as e:
        datos_ig = {"info": {}, "impresiones": {"total_imp": 0, "total_reach": 0, "daily": {}},
                    "media": {"data": []}}
        error_ig = str(e)

imp_fb_total = datos["impresiones"].get("total_imp", 0)
imp_ig_total = datos_ig["impresiones"].get("total_imp", 0)
gran_total   = imp_fb_total + imp_ig_total
seg_fb       = datos["info"].get("followers_count", 0)
seg_ig       = datos_ig["info"].get("followers_count", 0)

st.markdown(f"""
<div style="background:linear-gradient(135deg,#0f172a,#1e3a5f);
            border-radius:16px; padding:28px 32px; margin-bottom:20px;
            display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:20px;">
    <div>
        <div style="color:#94a3b8;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase">
            📊 Total visualizaciones — últimos 30 días
        </div>
        <div style="color:white;font-size:clamp(26px,7vw,60px);font-weight:900;line-height:1;margin:8px 0 4px">
            {gran_total:,}
        </div>
        <div style="color:#64748b;font-size:13px">Facebook + Instagram</div>
    </div>
    <div style="display:flex;gap:32px;flex-wrap:wrap;">
        <div style="text-align:center">
            <div style="color:#60a5fa;font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase">📘 Facebook</div>
            <div style="color:white;font-size:clamp(18px,4vw,28px);font-weight:800">{imp_fb_total:,}</div>
            <div style="color:#475569;font-size:11px">alcance único · {seg_fb:,} seguidores</div>
        </div>
        <div style="text-align:center">
            <div style="color:#e879f9;font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase">📸 Instagram</div>
            <div style="color:white;font-size:clamp(18px,4vw,28px);font-weight:800">{imp_ig_total:,}</div>
            <div style="color:#475569;font-size:11px">visualizaciones · {seg_ig:,} seguidores</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
tab_fb, tab_ig = st.tabs(["📘 Facebook", "📸 Instagram"])

# ═══════════════════════ FACEBOOK ═══════════════════════════════════
with tab_fb:
    if error_fb:
        st.error(f"⚠️ Error al cargar Facebook: {error_fb}")

    info      = datos["info"]
    imp       = datos["impresiones"]
    eng_total = imp.get("engagement", 0)

    fan_data = {}
    for m in datos["fan_growth"].get("data", []):
        mname = m.get("name", "")
        if "follow" in mname or "fan" in mname:
            for v in m.get("values", []):
                dt = v.get("end_time","")[:10]
                if dt:
                    fan_data[dt] = fan_data.get(dt, 0) + v.get("value", 0)

    st.markdown(f"""
    <div class="bloque-imp" style="background:linear-gradient(135deg,#1e40af,#2563eb)">
        <div class="label">🎯 Personas alcanzadas en Facebook — últimos 30 días</div>
        <div class="valor">{imp['total_imp']:,}</div>
        <div class="sub">Alcance único · personas distintas que vieron el contenido</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("👥 Seguidores",        f"{info.get('followers_count', 0):,}")
    c2.metric("💬 Engagement (30d)",  f"{eng_total:,}",
              help="Interacciones totales (fuente: Meta insights)")
    c3.metric("🖥️ Vistas de página",  f"{imp.get('vistas', 0):,}")

    st.markdown("---")
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.subheader("📈 Alcance diario")
        if imp["daily"]:
            df = pd.DataFrame([{"Fecha": k, "Personas alcanzadas": v}
                                for k, v in sorted(imp["daily"].items())])
            fig = px.line(df, x="Fecha", y="Personas alcanzadas",
                          color_discrete_sequence=["#2563eb"])
            fig.update_traces(fill="tozeroy", fillcolor="rgba(37,99,235,0.15)", line_width=2)
            fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Sin datos de alcance diario.")

    with col_der:
        if fan_data:
            st.subheader("👥 Nuevos seguidores por día")
            df = pd.DataFrame([{"Fecha": k, "Nuevos": v}
                                for k, v in sorted(fan_data.items())])
            fig = px.bar(df, x="Fecha", y="Nuevos", color_discrete_sequence=["#16a34a"])
            fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Sin datos de seguidores por día.")


    # ── Top 10 publicaciones FB históricas ───────────────────────────
    st.markdown("---")
    st.subheader("📝 Top 10 publicaciones de Facebook")
    posts_data_fb = datos.get("posts", {})
    if posts_data_fb.get("data"):
        lista_fb = []
        for post in posts_data_fb["data"]:
            msg   = post.get("message", "(Sin texto)")
            reac  = post.get("reactions") or post.get("likes") or {}
            likes = reac.get("summary", {}).get("total_count", 0)
            com   = post.get("comments", {}).get("summary", {}).get("total_count", 0)
            shares= post.get("shares", {}).get("count", 0)
            lista_fb.append({
                "Fecha":          post.get("created_time", "")[:10],
                "Publicación":    msg[:140] + "..." if len(msg) > 140 else msg,
                "❤️ Likes":       likes,
                "💬 Comentarios": com,
                "🔁 Compartidos": shares,
                "📊 Engagement":  likes + com + shares,
            })
        df_fb_top = pd.DataFrame(lista_fb).sort_values("❤️ Likes", ascending=False)
        for _, row in df_fb_top.head(10).iterrows():
            with st.container(border=True):
                cols = st.columns([5, 1, 1, 1])
                cols[0].markdown(f"📅 `{row['Fecha']}`  
{row['Publicación']}")
                cols[1].metric("❤️", f"{row['❤️ Likes']:,}" if row["❤️ Likes"] > 0 else "—")
                cols[2].metric("💬", f"{row['💬 Comentarios']:,}")
                cols[3].metric("🔁", f"{row['🔁 Compartidos']:,}" if row["🔁 Compartidos"] > 0 else "—")
        with st.expander("📋 Ver todas las publicaciones de Facebook"):
            st.dataframe(df_fb_top, width='stretch', hide_index=True)
    else:
        st.info("Sin datos de publicaciones de Facebook.")

# ═══════════════════════ INSTAGRAM ══════════════════════════════════
with tab_ig:
    if error_ig:
        st.error(f"⚠️ Error al cargar Instagram: {error_ig}")

    info_ig   = datos_ig["info"]
    imp_ig    = datos_ig["impresiones"]
    seg_ig    = info_ig.get("followers_count", 0)
    med_count = info_ig.get("media_count", 0)

    st.markdown(f"""
    <div class="bloque-imp" style="background:linear-gradient(135deg,#7c3aed,#c026d3)">
        <div class="label">▶️ Visualizaciones Instagram — últimos 30 días</div>
        <div class="valor">{imp_ig['total_imp']:,}</div>
        <div class="sub">Plays de Reels + reproducciones de videos + vistas (incluye repeticiones)</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Seguidores",          f"{seg_ig:,}")
    c2.metric("🖼️ Publicaciones",       f"{med_count:,}")
    c3.metric("🎯 Alcance único (30d)", f"{imp_ig['total_reach']:,}")
    c4.metric("💬 Interacciones (30d)", f"{imp_ig.get('engaged', 0):,}")

    st.markdown("---")
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.subheader("📈 Alcance diario")
        if imp_ig["daily"]:
            df = pd.DataFrame([{"Fecha": k, "Alcance": v}
                                for k, v in sorted(imp_ig["daily"].items())])
            fig = px.line(df, x="Fecha", y="Alcance",
                          color_discrete_sequence=["#c026d3"])
            fig.update_traces(fill="tozeroy",
                              fillcolor="rgba(192,38,211,0.12)", line_width=2)
            fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Sin datos de alcance diario.")

    with col_der:
        st.subheader("👥 Nuevos seguidores por día")
        daily_seg = imp_ig.get("daily_followers", {})
        if daily_seg:
            df_seg = pd.DataFrame([{"Fecha": k, "Nuevos seguidores": v}
                                    for k, v in sorted(daily_seg.items()) if v > 0])
            if not df_seg.empty:
                fig = px.bar(df_seg, x="Fecha", y="Nuevos seguidores",
                             color_discrete_sequence=["#c026d3"])
                fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig, width='stretch')
            else:
                st.info("Sin datos de seguidores por día.")
        else:
            st.info("Sin datos de seguidores por día.")

    # ── Segmentación por tipo de contenido ──────────────────────────
    st.markdown("---")
    st.subheader("📊 Rendimiento por tipo de contenido")
    all_media = datos_ig.get("media", {}).get("data", [])
    if all_media:
        tipos_map = {}
        iconos_t  = {"Reel": "🎬", "Video": "▶️", "Imagen": "📷", "Carrusel": "🖼️"}
        for post in all_media:
            mt = post.get("media_type", "IMAGE")
            pt = post.get("product_type", "")
            if pt == "clips":            t = "Reel"
            elif mt == "VIDEO":          t = "Video"
            elif mt == "CAROUSEL_ALBUM": t = "Carrusel"
            else:                        t = "Imagen"
            if t not in tipos_map:
                tipos_map[t] = {"count": 0, "likes": 0, "comments": 0}
            tipos_map[t]["count"]    += 1
            tipos_map[t]["likes"]    += post.get("like_count", 0)
            tipos_map[t]["comments"] += post.get("comments_count", 0)

        tipo_cols = st.columns(len(tipos_map))
        for idx, (tipo, data) in enumerate(tipos_map.items()):
            avg = data["likes"] / data["count"] if data["count"] else 0
            with tipo_cols[idx]:
                with st.container(border=True):
                    st.markdown(f"**{iconos_t.get(tipo,'')} {tipo}**")
                    st.metric("Publicaciones",  data["count"])
                    st.metric("Likes totales",  f"{data['likes']:,}")
                    st.metric("Likes promedio", f"{avg:.0f}")

        df_seg = pd.DataFrame([
            {"Tipo": t, "Publicaciones": d["count"],
             "Likes totales": d["likes"],
             "Avg Likes": round(d["likes"]/d["count"], 1) if d["count"] else 0,
             "Comentarios": d["comments"]}
            for t, d in tipos_map.items()
        ])
        col_pie, col_bar = st.columns(2)
        with col_pie:
            fig_p = px.pie(df_seg, values="Publicaciones", names="Tipo",
                           title="Distribución por tipo",
                           color_discrete_sequence=["#c026d3","#7c3aed","#db2777","#9333ea"])
            fig_p.update_layout(margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_p, width='stretch')
        with col_bar:
            fig_b = px.bar(df_seg, x="Tipo", y="Avg Likes",
                           title="Promedio de likes por tipo",
                           color_discrete_sequence=["#c026d3"])
            fig_b.update_layout(showlegend=False, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_b, width='stretch')

    st.markdown("---")
    st.subheader("🖼️ Publicaciones recientes")

    media_data = datos_ig.get("media", {})
    if media_data.get("data"):
        lista_ig = []
        for post in media_data["data"]:
            cap = post.get("caption", "(Sin descripción)")
            lista_ig.append({
                "Fecha":          post.get("timestamp","")[:10],
                "Tipo":           post.get("media_type",""),
                "Publicación":    cap[:140] + "..." if len(cap) > 140 else cap,
                "❤️ Likes":       post.get("like_count", 0),
                "💬 Comentarios": post.get("comments_count", 0),
                "🔗 Link":        post.get("permalink",""),
            })
        df_ig = pd.DataFrame(lista_ig)
        if not df_ig.empty and "❤️ Likes" in df_ig.columns:
            df_ig = df_ig.sort_values("❤️ Likes", ascending=False)

        st.markdown("#### 🏆 Top 10 publicaciones")
        for _, row in df_ig.head(10).iterrows():
            with st.container(border=True):
                cols = st.columns([5, 1, 1, 1])
                cols[0].markdown(f"📅 `{row['Fecha']}` · {row['Tipo']}  \n{row['Publicación']}")
                cols[1].metric("❤️", row["❤️ Likes"])
                cols[2].metric("💬", row["💬 Comentarios"])
                cols[3].markdown(f"[🔗 Ver]({row['🔗 Link']})")

        with st.expander("📋 Ver todas las publicaciones"):
            st.dataframe(df_ig, width='stretch', hide_index=True)
    else:
        st.warning("No se pudieron cargar las publicaciones de Instagram.")
