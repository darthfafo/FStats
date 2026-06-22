import streamlit as st
from config import RESPONSIVE_CSS, sidebar_nav
from version import APP_VERSION, CHANGELOG

st.set_page_config(page_title="Bitácora", page_icon="📓", layout="wide")
st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)
sidebar_nav(current="")

st.title("📓 Bitácora de versiones")
st.markdown(
    f"Versión actual: **FStats v{APP_VERSION}**. Acá queda registrado el historial "
    "de mejoras de la aplicación, versión por versión."
)
st.markdown("---")

for v in CHANGELOG:
    es_actual = v["version"] == APP_VERSION
    with st.container(border=True):
        etiqueta = "🟢 versión actual" if es_actual else v["fecha"]
        st.markdown(
            f"#### v{v['version']} — {v['titulo']}  \n"
            f"<span style='color:#94a3b8;font-size:13px'>{v['fecha']} · {etiqueta}</span>",
            unsafe_allow_html=True,
        )
        st.markdown("\n".join(f"- {c}" for c in v["cambios"]))
