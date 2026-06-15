import os

import pandas as pd
import streamlit as st

from config import PORTALES, RESPONSIVE_CSS, sidebar_nav

st.set_page_config(page_title="Realimentación", page_icon="🔁", layout="wide")
st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)
sidebar_nav(current="")

st.title("🔁 Realimentación y entrenamiento")
st.caption("Traé reels reales del warehouse (ganadores y perdedores según cómo "
           "interactuó la gente) y entrená el regresor que aprende qué funciona.")
st.markdown("---")

_PENDIENTES = ("PENDIENTE", "", None)
ig_portales = [p for p in PORTALES if p.get("instagram_id") not in _PENDIENTES
               and p.get("access_token") not in _PENDIENTES]

if not ig_portales:
    st.warning("No hay portales con credenciales de Instagram configuradas.")
    st.stop()

# Pesos del "éxito" combinado (configurables por entorno).
we = float(os.getenv("SUCCESS_W_ENG", "0.5"))
wp = float(os.getenv("SUCCESS_W_PLAYS", "0.3"))
wr = float(os.getenv("SUCCESS_W_REACH", "0.2"))
st.caption(f"🎯 Éxito = combinación ponderada por portal · engagement {we:g} · "
           f"reproducciones {wp:g} · alcance {wr:g}  (ajustable con "
           "`SUCCESS_W_ENG/PLAYS/REACH`)")

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
c1, c2, c3 = st.columns(3)
top_pct = c1.slider("Ganadores: éxito ≥", 0.50, 0.99, 0.80, 0.01)
bottom_pct = c2.slider("Perdedores: éxito ≤", 0.01, 0.50, 0.20, 0.01)
block_size = c3.number_input("Máx. por clase", min_value=1, max_value=100, value=10)

# ── 1) Previsualizar ──────────────────────────────────────────────────────────
st.markdown("##### 1) Previsualizar selección")
if st.button("👀 Ver ganadores y perdedores"):
    try:
        from analyzer.feedback import select_winners, select_losers
        w = select_winners(nombre, top_pct)
        l = select_losers(nombre, bottom_pct)
        cols = ["post_id", "success", "reach", "plays", "like_count",
                "comments_count", "permalink"]
        st.write(f"🏆 **{len(w)}** ganadores (éxito ≥ {top_pct:.2f})")
        if w:
            st.dataframe(pd.DataFrame(w)[cols].head(100), width="stretch", hide_index=True)
        st.write(f"📉 **{len(l)}** perdedores (éxito ≤ {bottom_pct:.2f})")
        if l:
            st.dataframe(pd.DataFrame(l)[cols].head(100), width="stretch", hide_index=True)
        if not w and not l:
            from analyzer.feedback import diagnose
            d = diagnose(nombre)
            st.warning(
                f"Sin resultados. En el warehouse, para `{d['portal_id_buscado']}`: "
                f"{d['posts']} posts · {d['reels']} reels · "
                f"{d['reels_con_reach']} con reach>0 · {d['reels_con_plays']} con plays>0.")
            st.caption("portal_ids que existen en ig_posts (revisá si el de arriba coincide):")
            st.dataframe(pd.DataFrame(d["portales_en_warehouse"]),
                         width="stretch", hide_index=True)
            st.caption("tipos de contenido guardados para este portal "
                       "(si los reels aparecen como product_type 'REELS' pero "
                       "reels=0 arriba, falta re-ingestar con el colector arreglado):")
            st.dataframe(pd.DataFrame(d["tipos"]), width="stretch", hide_index=True)
    except Exception as e:
        st.error(f"Error consultando el warehouse: {e}")

# ── 2) Ingestar bloque de entrenamiento ───────────────────────────────────────
st.markdown("##### 2) Ingestar bloque (ganadores + perdedores)")
st.caption("Baja cada mp4 vía Graph API, lo analiza (features visuales + audio) y "
           "guarda con su etiqueta real. Idempotente: saltea los ya procesados.")
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
            s = ingest_training_block(portal, top_pct=top_pct, bottom_pct=bottom_pct,
                                      block_size=int(block_size), progress_cb=cb)
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
st.caption("Aprende de TODO lo ingestado. Reentrená cada vez que sumes bloques nuevos.")
if st.button("🧠 Entrenar modelo"):
    try:
        from analyzer import trainer
        with st.spinner("Entrenando..."):
            res = trainer.train()
        (st.success if res["ok"] else st.warning)(res["message"])
    except Exception as e:
        st.error(f"Error entrenando: {e}")
