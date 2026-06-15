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

with st.expander("ℹ️ ¿Cómo funciona esto? (explicación para cualquiera)"):
    st.markdown("""
**La idea en una frase:** el sistema *aprende de tus propios reels* —mirando los que
funcionaron y los que no— para después poder darle un **puntaje de potencial** a un
video nuevo.

**Los 3 pasos de abajo:**
1. **Previsualizar** — De todos tus reels reales, elige los **ganadores** (los que más
   enganchó la gente) y los **perdedores** (los que menos), según un *"éxito"* que
   combina **engagement + reproducciones + alcance**, comparando cada reel contra los
   de su propio portal.
2. **Ingestar bloque** — Baja esos videos y de cada uno mide cosas objetivas: **lo
   visual** (cortes, gancho de los primeros segundos, caras, texto en pantalla, color,
   movimiento) y **el audio** (energía, ritmo, voz). Guarda esas mediciones junto con
   el dato real de si ganó o no.
3. **Entrenar** — Junta todo lo guardado y **busca los patrones** que separan a los
   ganadores de los perdedores.

**Cómo "aprende" el modelo:** cada reel queda convertido en ~30 números (sus
mediciones) + una etiqueta (ganó / no ganó). El modelo prueba miles de combinaciones
hasta encontrar qué mezcla de esos números tiende a ganar (por ejemplo: *arranque con
cortes + una cara temprana + audio con energía*). Con eso, ante un **video nuevo**,
estima la **probabilidad de que funcione → ese es el score 0-100**.

**Importante:** aprende de lo que le gustó a **tu** audiencia real, no de reglas
genéricas. Y mira la **forma** del video (ritmo, imagen, audio), no el **tema** (de qué
trata) — eso también pesa en la viralidad, pero no se mide acá.
""")

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
def _auc_words(a):
    if a is None:
        return ""
    if a < 0.60:
        return "casi al azar — sumá más reels"
    if a < 0.70:
        return "flojo — sumá más reels"
    if a < 0.80:
        return "útil 👍"
    if a < 0.90:
        return "bueno 💪"
    return "muy bueno 🔥"


try:
    from analyzer import trainer
    info = trainer.model_info()
    if info:
        a = info.get("cv_auc")
        auc = f" · AUC {a:.2f} ({_auc_words(a)})" if a is not None else ""
        st.success(f"🧠 Modelo entrenado: {info['n']} reels "
                   f"({info['n_pos']} ganadores / {info['n_neg']} perdedores){auc}")
    else:
        st.info("🧠 Todavía no hay modelo entrenado. Ingestá ganadores y perdedores, "
                "después entrenalo abajo.")
except Exception as e:
    st.info(f"No se pudo leer el estado del modelo: {e}")

with st.expander("📊 ¿Qué es el AUC y cuándo el modelo ya aprendió suficiente?"):
    st.markdown("""
**El AUC** mide qué tan bien el modelo **separa** ganadores de perdedores. En criollo:
si agarrás al azar un ganador y un perdedor reales, es la probabilidad de que le dé
**más puntaje al ganador**.

| AUC | Lectura |
|---|---|
| 0.50 | no distingue nada (moneda al aire) |
| 0.70 – 0.80 | útil 👍 |
| 0.80 – 0.90 | bueno 💪 |
| 0.90+ | muy bueno 🔥 |
| 1.00 | perfecto |

Se calcula probando con reels que el modelo **no vio** al entrenar, así que es una
estimación honesta de cómo le iría con videos nuevos.

**¿Cuándo "ya aprendió suficiente"?** No hay número mágico. La señal práctica: sumá
bloques y reentrená — mientras el AUC **sube**, te falta data; cuando se **estabiliza**
(deja de mejorar al agregar más reels), ya aprendió lo que estas mediciones permiten.
Un AUC estable de **0.78–0.85** es muy bueno para este enfoque (no esperes 0.95: el
*tema* del video, que pesa mucho, no se mide acá).
""")

st.markdown("---")
nombre = st.selectbox("Portal", [p["nombre"] for p in ig_portales])
portal = next(p for p in PORTALES if p["nombre"] == nombre)
c1, c2, c3 = st.columns(3)
top_pct = c1.slider(
    "Ganadores: éxito ≥", 0.50, 0.99, 0.80, 0.01,
    help="Más alto = ganadores más 'claros' y mejor contraste (AUC más alto), pero "
         "menos reels. Más bajo = más data pero etiquetas más borrosas (AUC más bajo, "
         "no peor: tarea más difícil). No conviene partir al medio (0.5).")
bottom_pct = c2.slider(
    "Perdedores: éxito ≤", 0.01, 0.50, 0.20, 0.01,
    help="Más bajo = perdedores más 'claros'. No lo subas cerca de 0.5: las dos clases "
         "se confunden. La palanca más fuerte para mejorar el modelo es sumar más "
         "reels, no ampliar el rango.")
block_size = c3.number_input("Máx. por clase", min_value=1, max_value=100, value=10,
                             help="Cuántos reels nuevos baja y analiza por clase en este bloque.")

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
