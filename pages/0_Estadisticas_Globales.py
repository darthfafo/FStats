import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from config import PORTALES, RESPONSIVE_CSS, sidebar_nav
from collectors.facebook import FacebookCollector
from collectors.instagram import InstagramCollector

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
def cargar_portal(nombre, page_id, ig_id, token, ig_only=False):
    r = {"nombre": nombre, "fb_seg":0,"fb_imp":0,"fb_eng":0,"fb_vistas":0,
         "ig_seg":0,"ig_imp":0,"ig_reach":0,"ig_engaged":0,
         "fb_daily":{},"ig_daily":{},"posts_ig":[],"posts_fb":[],"all_media_ig":[]}
    if not ig_only and not pendiente(page_id) and not pendiente(token):
        try:
            fb = FacebookCollector(page_id=page_id, access_token=token)
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
            ig = InstagramCollector(ig_id=ig_id, access_token=token)
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
                              p.get("instagram_id"), token, p.get("ig_only", False))
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

    fig_trend = go.Figure()
    fallback_i = 0
    for d in activos:
        color = PORTAL_COLOR.get(d["nombre"])
        if not color:
            color = FALLBACK[fallback_i % len(FALLBACK)]
            fallback_i += 1
        if d["fb_daily"]:
            df_fb = pd.DataFrame([{"Fecha":k,"Alcance":v} for k,v in sorted(d["fb_daily"].items())])
            fig_trend.add_trace(go.Scatter(
                x=df_fb["Fecha"], y=df_fb["Alcance"],
                mode="lines", name=f"{d['nombre']} (FB)",
                line=dict(color=color, width=2.5, dash="solid"),
                opacity=0.95
            ))
        if d["ig_daily"]:
            df_ig2 = pd.DataFrame([{"Fecha":k,"Alcance":v} for k,v in sorted(d["ig_daily"].items())])
            fig_trend.add_trace(go.Scatter(
                x=df_ig2["Fecha"], y=df_ig2["Alcance"],
                mode="lines", name=f"{d['nombre']} (IG)",
                line=dict(color=color, width=2.5, dash="dot"),
                opacity=0.75
            ))

    fig_trend.update_layout(
        legend_title="Portal · Red",
        margin=dict(l=0,r=0,t=10,b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
        yaxis=dict(
            type="log",
            title="Alcance (escala logarítmica)",
            gridcolor="rgba(255,255,255,0.1)",
            tickformat=".2s",
        ),
    )
    st.plotly_chart(fig_trend, width='stretch')
    st.caption(
        "📐 **Escala logarítmica**: cada división del eje Y representa 10× el valor anterior. "
        "Esto permite comparar portales con audiencias muy distintas en el mismo gráfico. "
        "Línea continua = Facebook (alcance único). Línea punteada = Instagram (reproducciones diarias)."
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
