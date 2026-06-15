import os
import tempfile

import streamlit as st

from config import RESPONSIVE_CSS, sidebar_nav

st.set_page_config(page_title="Analizador de Viralidad", page_icon="🚀", layout="wide")
st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)
sidebar_nav(current="")

st.title("🚀 Analizador de Potencial de Viralidad")
st.caption("Subí un reel/video y obtené un score de potencial de viralidad + explicación.")
st.markdown("---")


def _color(score):
    return "#22c55e" if score >= 70 else "#eab308" if score >= 45 else "#ef4444"


uploaded = st.file_uploader("🎬 Video (mp4 / mov / m4v)", type=["mp4", "mov", "m4v"])
caption = st.text_area("📝 Caption / copy (opcional)", height=80,
                       placeholder="El texto que acompañaría al reel...")
c1, c2 = st.columns(2)
transcribir = c1.checkbox("Transcribir audio", value=True,
                          help="Requiere faster-whisper instalado. Si no está, se omite.")
guardar = c2.checkbox("Guardar análisis en la base", value=True)

if uploaded and st.button("⚡ Analizar", type="primary"):
    suffix = os.path.splitext(uploaded.name)[1] or ".mp4"
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(tmp, "wb") as fh:
        fh.write(uploaded.getbuffer())

    res = None
    try:
        with st.spinner("Analizando video (features → transcripción → score)..."):
            from analyzer import analyze_video
            res = analyze_video(tmp, caption=caption, source="upload",
                                persist=guardar, transcribe_audio=transcribir)
    except Exception as e:
        st.error(f"❌ Error analizando: {e}")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    if res:
        sr = res["score_result"]
        score = int(sr.get("score", 0))
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0f172a,#1e293b);border-radius:16px;
                    padding:28px 32px;margin:8px 0 20px;text-align:center">
          <div style="color:#94a3b8;font-size:12px;font-weight:700;letter-spacing:2px;
                      text-transform:uppercase">Potencial de viralidad</div>
          <div style="color:{_color(score)};font-size:clamp(40px,10vw,72px);font-weight:900;
                      line-height:1;margin:6px 0">{score}<span style="font-size:24px;color:#64748b">/100</span></div>
        </div>""", unsafe_allow_html=True)

        subs = sr.get("subscores", {}) or {}
        cols = st.columns(4)
        for col, (k, label) in zip(cols, [("gancho", "🎣 Gancho"), ("ritmo", "🥁 Ritmo"),
                                          ("audio", "🔊 Audio"), ("claridad", "💡 Claridad")]):
            col.metric(label, subs.get(k, 0))

        st.info(sr.get("explanation", ""))
        if sr.get("model") == "heuristic":
            st.warning("⚠️ Score heurístico (sin LLM). Instalá Ollama y un modelo de "
                       "visión (`ollama pull llama3.2-vision`) para el análisis completo.")
        else:
            st.caption(f"Modelo: {sr.get('model')}")

        with st.expander("🔬 Features deterministas"):
            st.json(res["features"])
        if res.get("transcript"):
            with st.expander("🗣️ Transcripción"):
                st.write(res["transcript"])
        if res.get("run_id"):
            st.caption(f"Guardado · run_id `{res['run_id']}`")

st.markdown("---")
st.subheader("🗂️ Análisis recientes")
try:
    from analyzer import store
    df = store.list_runs(20)
    if df is not None and not df.empty:
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("Todavía no hay análisis guardados.")
except Exception as e:
    st.info(f"No se pudo leer el historial: {e}")
