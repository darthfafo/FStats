import os
import tempfile

import streamlit as st

from config import RESPONSIVE_CSS, sidebar_nav, require_pin

st.set_page_config(page_title="Analizador de Viralidad", page_icon="🚀", layout="wide")
st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)
sidebar_nav(current="")
require_pin("el Analizador")

st.title("🚀 Analizador de Potencial de Viralidad")
st.caption("Subí un reel/video y obtené un score de potencial de viralidad + explicación.")
st.markdown("---")


def _color(score):
    return "#22c55e" if score >= 70 else "#eab308" if score >= 45 else "#ef4444"


uploaded = st.file_uploader("🎬 Video (mp4 / mov / m4v)", type=["mp4", "mov", "m4v"])
caption = st.text_area("📝 Caption / copy actual (opcional)", height=70,
                       placeholder="El texto que acompañaría al reel...")
descripcion = st.text_area(
    "📋 ¿Qué pasa en el video? (para generarte un copy completo)", height=70,
    placeholder="Ej: Un perro rescata a un nene que se estaba ahogando en el río.")
c1, c2 = st.columns(2)
transcribir = c1.checkbox("Transcribir audio (no afecta el score)", value=False,
                          help="Solo informativo. Whisper es lento y el score no lo usa.")
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
        modelo = sr.get("model", "heuristic")

        # ── Potencial (hero) ──
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0f172a,#1e293b);border-radius:16px;
                    padding:28px 32px;margin:8px 0 6px;text-align:center">
          <div style="color:#94a3b8;font-size:12px;font-weight:700;letter-spacing:2px;
                      text-transform:uppercase">Potencial de viralidad</div>
          <div style="color:{_color(score)};font-size:clamp(40px,10vw,72px);font-weight:900;
                      line-height:1;margin:6px 0">{score}<span style="font-size:24px;color:#94a3b8">/100</span></div>
        </div>""", unsafe_allow_html=True)
        st.caption(sr.get("explanation", ""))

        # ── Desglose del video ──
        st.markdown("#### 🎬 Desglose del video")
        subs = sr.get("subscores", {}) or {}
        from analyzer.score import describe
        desc = describe(res["features"])
        meta = [
            ("gancho", "🎣 Gancho",
             "¿Los primeros 3s capturan la atención? Cortes y movimiento al inicio, "
             "una cara temprana, formato vertical y colores llamativos."),
            ("ritmo", "🥁 Ritmo",
             "¿Sostiene la atención? Cortes por segundo, duración apropiada (7-40s) "
             "y ritmo del audio. Penaliza monotonía o videos muy largos."),
            ("audio", "🔊 Audio",
             "¿Hay sonido con energía y presencia de voz? El audio aporta enganche."),
            ("claridad", "💡 Claridad",
             "¿Se entiende sin sonido? Texto en pantalla, caras y buen contraste."),
        ]
        cols = st.columns(4)
        for col, (k, label, h) in zip(cols, meta):
            col.metric(label, subs.get(k, 0), help=h)
            col.caption(desc.get(k, ""))

        # ── Título / copy (la gente lo lee además del video) ──
        st.markdown("#### 📝 Título / copy")
        st.caption("Es lo que la gente lee además del video, así que pesa en el potencial.")
        from analyzer.copy import analyze_copy, generate_copy
        cp = analyze_copy(caption)
        cc1, cc2 = st.columns([1, 3])
        cc1.metric("🎣 Gancho del título actual",
                   f"{cp['score']}/100" if cp["has_copy"] else "—",
                   help="¿El título engancha? Curiosidad, pregunta, intriga, palabras de impacto.")
        with cc2:
            for fnd in (cp["found"] if cp["has_copy"] else []):
                st.markdown(f"- ✅ {fnd}")
            for tip in cp["tips"]:
                st.markdown(f"- 💡 {tip}")

        # ── Copy completo sugerido (título + descripción + cierre) ──
        st.markdown("#### ✨ Copy sugerido (título + descripción + cierre)")
        fuente = (descripcion or "").strip() or (caption or "").strip()
        gen = generate_copy(fuente)
        if gen:
            st.caption("Listo para editar y publicar (de más a menos gancho):")
            for g in gen:
                with st.container(border=True):
                    st.markdown(f"**{g['titulo']}**")
                    st.write(g["descripcion"])
                    st.markdown(f"_{g['cierre']}_")
                    st.caption(f"Gancho del copy: {g['score']}/100")
        else:
            st.caption("Completá «¿Qué pasa en el video?» arriba para generar un copy completo.")

        # ── Detalle técnico ──
        st.caption(f"Motor: **{modelo}**" + (" · entrená el modelo para calibrar con tus datos"
                                             if modelo == "heuristic" else ""))
        with st.expander("🔬 Features (detalle técnico)"):
            st.json(res["features"])
        if res.get("transcript"):
            with st.expander("🗣️ Transcripción"):
                st.write(res["transcript"])
        if res.get("run_id"):
            st.caption(f"Guardado · run_id `{res['run_id']}`")
        elif res.get("persist_error"):
            st.caption("ℹ️ No se guardó en la base (modo sin warehouse), pero el "
                       "análisis es válido.")

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
