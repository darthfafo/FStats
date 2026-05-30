import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from config import PORTALES
from collectors.instagram import InstagramCollector

st.set_page_config(page_title="VISTE ESTO?", page_icon="👁️", layout="wide")

st.markdown("""
<style>
.pendiente-box { background:linear-gradient(135deg,#1e293b,#334155); border-radius:14px; padding:40px; text-align:center; margin:20px 0; }
</style>
""", unsafe_allow_html=True)

portal = next((p for p in PORTALES if p["nombre"] == "VISTE ESTO?"), None)

with st.sidebar:
    st.title("👁️ VISTE ESTO?")
    st.markdown("---")
    if st.button("🏠 Panel general", use_container_width=True):
        st.switch_page("app.py")
    if st.button("🔄 Actualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption(datetime.now().strftime("%d/%m/%Y %H:%M"))

st.title("👁️ VISTE ESTO?")
st.markdown("---")

def credenciales_ok(p):
    pendientes = ("PENDIENTE", "", None)
    return (p.get("access_token") not in pendientes and
            p.get("instagram_id") not in pendientes)

if portal is None or not credenciales_ok(portal):
    st.markdown("""
    <div class="pendiente-box">
        <div style="font-size:64px;margin-bottom:16px">⏳</div>
        <div style="color:#94a3b8;font-size:13px;font-weight:700;letter-spacing:2px;text-transform:uppercase">Esperando credenciales</div>
        <div style="color:white;font-size:28px;font-weight:800;margin:12px 0">VISTE ESTO? — Pendiente de configuración</div>
        <div style="color:#64748b;font-size:15px">Una vez que el administrador envíe el token de acceso,<br>
        completá los datos en el archivo <code>.env</code> y el panel se activa automáticamente.</div>
    </div>""", unsafe_allow_html=True)
    st.markdown("### 📋 Qué completar en `.env`")
    st.code("""META_INSTAGRAM_ID_VISTE=ID_NUMÉRICO_DE_INSTAGRAM
META_PAGE_ACCESS_TOKEN_VISTE=TOKEN_QUE_MANDE_EL_ADMIN""", language="bash")
    st.stop()

@st.cache_data(ttl=3600)
def cargar_ig(ig_id, token):
    ig = InstagramCollector(ig_id=ig_id, access_token=token)
    return {
        "info":        ig.get_account_info(),
        "impresiones": ig.get_media_impressions(limit=25),
        "media":       ig.get_recent_media(limit=30),
    }

with st.spinner("Cargando estadísticas de Instagram..."):
    try:
        datos_ig = cargar_ig(portal["instagram_id"], portal["access_token"])
        error_ig = None
    except Exception as e:
        datos_ig = {"info":{},"impresiones":{"total_imp":0,"total_reach":0,"daily":{},"posts_data":[]},"media":{"data":[]}}
        error_ig = str(e)

info_ig   = datos_ig["info"]
imp_ig    = datos_ig["impresiones"]
seg_ig    = info_ig.get("followers_count", 0)
med_count = info_ig.get("media_count", 0)

# Hero
st.markdown(f"""
<div style="background:linear-gradient(135deg,#0f172a,#3b0764);border-radius:16px;padding:28px 32px;margin-bottom:20px;
            display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:20px;">
  <div>
    <div style="color:#94a3b8;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase">📸 Total visualizaciones Instagram — últimos 30 días</div>
    <div style="color:white;font-size:60px;font-weight:900;line-height:1;margin:8px 0 4px">{imp_ig['total_imp']:,}</div>
    <div style="color:#64748b;font-size:13px">Plays de Reels + reproducciones + vistas</div>
  </div>
  <div style="display:flex;gap:32px;flex-wrap:wrap;">
    <div style="text-align:center">
      <div style="color:#a855f7;font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase">👥 Seguidores</div>
      <div style="color:white;font-size:28px;font-weight:800">{seg_ig:,}</div>
    </div>
    <div style="text-align:center">
      <div style="color:#a855f7;font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase">🎯 Alcance único</div>
      <div style="color:white;font-size:28px;font-weight:800">{imp_ig['total_reach']:,}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

if error_ig: st.error(f"⚠️ Error: {error_ig}")

c1,c2,c3,c4 = st.columns(4)
c1.metric("👥 Seguidores",          f"{seg_ig:,}")
c2.metric("🖼️ Publicaciones",       f"{med_count:,}")
c3.metric("🎯 Alcance único (30d)", f"{imp_ig['total_reach']:,}")
c4.metric("💬 Interacciones (30d)", f"{imp_ig.get('engaged',0):,}")

st.markdown("---")
col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader("📈 Alcance diario")
    if imp_ig.get("daily"):
        df = pd.DataFrame([{"Fecha":k,"Personas alcanzadas":v} for k,v in sorted(imp_ig["daily"].items())])
        fig = px.line(df, x="Fecha", y="Personas alcanzadas", color_discrete_sequence=["#a855f7"])
        fig.update_traces(fill="tozeroy", fillcolor="rgba(168,85,247,0.12)", line_width=2)
        fig.update_layout(showlegend=False, margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig, width='stretch')
    else: st.info("Sin datos de alcance diario.")

with col_der:
    st.subheader("🏆 Top 5 contenidos por rendimiento")
    posts_perf = imp_ig.get("posts_data", [])
    if posts_perf:
        top5 = sorted(posts_perf, key=lambda x: x.get("plays",0) or x.get("reach",0), reverse=True)[:5]
        items = [{"Publicación":("🎬" if p["tipo"]=="reel" else "▶️" if p["tipo"]=="video" else "🖼️" if p["tipo"]=="carousel_album" else "📷")+f" {p['ts']}",
                  "Plays / Alcance": p.get("plays") or p.get("reach",0)} for p in top5]
        df_top = pd.DataFrame(items)
        fig = px.bar(df_top, x="Plays / Alcance", y="Publicación", orientation="h", color_discrete_sequence=["#a855f7"])
        fig.update_layout(showlegend=False, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, width='stretch')
    else: st.info("Sin datos de rendimiento.")

st.markdown("---")
st.subheader("📊 Rendimiento por tipo de contenido")
all_media = datos_ig.get("media",{}).get("data",[])
if all_media:
    tipos_map = {}
    iconos_t = {"Reel":"🎬","Video":"▶️","Imagen":"📷","Carrusel":"🖼️"}
    for post in all_media:
        mt=post.get("media_type","IMAGE"); pt=post.get("product_type","")
        t = "Reel" if pt=="clips" else "Video" if mt=="VIDEO" else "Carrusel" if mt=="CAROUSEL_ALBUM" else "Imagen"
        if t not in tipos_map: tipos_map[t] = {"count":0,"likes":0,"comments":0}
        tipos_map[t]["count"]+=1; tipos_map[t]["likes"]+=post.get("like_count",0); tipos_map[t]["comments"]+=post.get("comments_count",0)

    tipo_cols = st.columns(len(tipos_map))
    for idx,(tipo,data) in enumerate(tipos_map.items()):
        avg = data["likes"]/data["count"] if data["count"] else 0
        with tipo_cols[idx]:
            with st.container(border=True):
                st.markdown(f"**{iconos_t.get(tipo,'')} {tipo}**")
                st.metric("Publicaciones",  data["count"])
                st.metric("Likes totales",  f"{data['likes']:,}")
                st.metric("Likes promedio", f"{avg:.0f}")

    df_seg = pd.DataFrame([{"Tipo":t,"Publicaciones":d["count"],
                            "Avg Likes":round(d["likes"]/d["count"],1) if d["count"] else 0}
                           for t,d in tipos_map.items()])
    col_pie,col_bar = st.columns(2)
    with col_pie:
        fig_p = px.pie(df_seg, values="Publicaciones", names="Tipo", title="Distribución por tipo",
                       color_discrete_sequence=["#a855f7","#7c3aed","#d946ef","#9333ea"])
        fig_p.update_layout(margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig_p, width='stretch')
    with col_bar:
        fig_b = px.bar(df_seg, x="Tipo", y="Avg Likes", title="Promedio de likes por tipo",
                       color_discrete_sequence=["#a855f7"])
        fig_b.update_layout(showlegend=False, margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig_b, width='stretch')

st.markdown("---")
st.subheader("🖼️ Publicaciones recientes")
media_data = datos_ig.get("media",{})
if media_data.get("data"):
    lista_ig = []
    for post in media_data["data"]:
        cap=post.get("caption","(Sin descripción)"); mt=post.get("media_type",""); pt=post.get("product_type","")
        tl = "🎬 Reel" if pt=="clips" else "▶️ Video" if mt=="VIDEO" else "🖼️ Carrusel" if mt=="CAROUSEL_ALBUM" else "📷 Imagen"
        lista_ig.append({"Fecha":post.get("timestamp","")[:10],"Tipo":tl,
                         "Publicación":cap[:140]+("..." if len(cap)>140 else ""),
                         "❤️ Likes":post.get("like_count",0),"💬 Comentarios":post.get("comments_count",0),
                         "🔗 Link":post.get("permalink","")})
    df_ig = pd.DataFrame(lista_ig)
    if not df_ig.empty: df_ig = df_ig.sort_values("❤️ Likes", ascending=False)
    st.markdown("#### 🏆 Top 5 publicaciones")
    for _, row in df_ig.head(5).iterrows():
        with st.container(border=True):
            cols = st.columns([5,1,1,1])
            cols[0].markdown(f"📅 `{row['Fecha']}` · {row['Tipo']}  \n{row['Publicación']}")
            cols[1].metric("❤️", row["❤️ Likes"]); cols[2].metric("💬", row["💬 Comentarios"])
            cols[3].markdown(f"[🔗 Ver]({row['🔗 Link']})")
    with st.expander("📋 Ver todas"):
        st.dataframe(df_ig, width='stretch', hide_index=True)
else:
    st.warning("No se pudieron cargar las publicaciones.")
