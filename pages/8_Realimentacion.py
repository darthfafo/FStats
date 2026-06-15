import pandas as pd
import streamlit as st

from config import PORTALES, RESPONSIVE_CSS, sidebar_nav

st.set_page_config(page_title="Realimentación", page_icon="🔁", layout="wide")
st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)
sidebar_nav(current="")

st.title("🔁 Realimentación y entrenamiento")
st.caption("Traé reels reales del warehouse de FStats (ganadores y perdedores) y "
           "entrená el regresor que aprende qué hace que un reel funcione.")
st.markdown("---")

_PENDIENTES = ("PENDIENTE", "", None)
ig_portales = [p for p in PORTALES if p.get("instagram_id") not in _PENDIENTES
               and p.get("access_token") not in _PENDIENTES]

if not ig_portales:
    st.warning("No hay portales con credenciales de Instagram configuradas.")
    st.stop()

# ── Estado del modelo ─────────────────────────────────────────────────────────
try:
    from analyzer import trainer
    info = trainer.model_info()
    if info:
        auc = f" · AUC {info['cv_auc']:.2f}" if info.get("cv_auc") else ""
        st.success(f"🧠 Modelo entrenado: {info['n']} reels "
                   f"({info['n_pos']} ganadores / {info['n_neg']} perdedores){auc}")
    else:
        st.info("🧠 Todavía no hay modelo entrenado. Ingestá ganadores y perdedores, "
                "después entrenalo abajo.")
except Exception as e:
    st.info(f"No se pudo leer el estado del modelo: {e}")

st.markdown("---")
nombre = st.selectbox("Portal", [p["nombre"] for p in ig_portales])
portal = next(p for p in PORTALES if p["nombre"] == nombre)
c1, c2, c3, c4 = st.columns(4)
metric = c1.selectbox("Métrica", ["reach", "plays"])
top_pct = c2.slider("Ganadores: percentil ≥", 0.50, 0.99, 0.80, 0.01)
bottom_pct = c3.slider("Perdedores: percentil ≤", 0.01, 0.50, 0.20, 0.01)
block_size = c4.number_input("Máx. por clase", min_value=1, max_value=100, value=10)

# ── 1) Previsualizar ──────────────────────────────────────────────────────────
st.markdown("##### 1) Previsualizar selección")
if st.button("👀 Ver ganadores y perdedores"):
    try:
        from analyzer.feedback import select_winners, select_losers
        w = select_winners(nombre, metric, top_pct)
        l = select_losers(nombre, metric, bottom_pct)
        cols = ["post_id", "reach", "plays", "like_count", "comments_count", "permalink"]
        st.write(f"🏆 **{len(w)}** ganadores (≥ pct {top_pct:.2f})")
        if w:
            st.dataframe(pd.DataFrame(w)[cols].head(100), width="stretch", hide_index=True)
        st.write(f"📉 **{len(l)}** perdedores (≤ pct {bottom_pct:.2f})")
        if l:
            st.dataframe(pd.DataFrame(l)[cols].head(100), width="stretch", hide_index=True)
    except Exception as e:
        st.error(f"Error consultando el warehouse: {e}")

# ── 2) Ingestar bloque de entrenamiento ───────────────────────────────────────
st.markdown("##### 2) Ingestar bloque (ganadores + perdedores)")
st.caption("Baja cada mp4 vía Graph API, lo analiza y guarda con su etiqueta real. "
           "Idempotente: saltea los ya procesados.")
if st.button("⬇️ Ingestar bloque", type="primary"):
    from analyzer.feedback import ingest_training_block
    prog = st.progress(0.0)
    status = st.empty()

    def cb(i, total, item):
        if item is not None:
            status.write(f"Procesando {i + 1}/{total}: `{item.get('post_id')}`")
        prog.progress(min(i / total, 1.0) if total else 1.0)

    try:
        with st.spinner("Bajando y analizando reels..."):
            s = ingest_training_block(portal, metric=metric, top_pct=top_pct,
                                      bottom_pct=bottom_pct, block_size=int(block_size),
                                      progress_cb=cb)
        prog.progress(1.0)
        st.success(f"✅ Procesados {s['processed']} "
                   f"({s['winners']} ganadores / {s['losers']} perdedores) · "
                   f"errores {len(s['errors'])}")
        if s["errors"]:
            with st.expander("Ver errores"):
                st.dataframe(pd.DataFrame(s["errors"], columns=["post_id", "error"]),
                             width="stretch", hide_index=True)
    except Exception as e:
        st.error(f"Error en la ingesta: {e}")

# ── 3) Entrenar el regresor ───────────────────────────────────────────────────
st.markdown("##### 3) Entrenar / reentrenar el modelo")
st.caption("Aprende de TODO lo ingestado (todos los portales). Reentrená cada vez "
           "que sumes bloques nuevos.")
if st.button("🧠 Entrenar modelo"):
    try:
        from analyzer import trainer
        with st.spinner("Entrenando..."):
            res = trainer.train()
        (st.success if res["ok"] else st.warning)(res["message"])
    except Exception as e:
        st.error(f"Error entrenando: {e}")
