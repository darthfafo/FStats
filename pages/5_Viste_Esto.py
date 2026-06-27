import streamlit as st
from config import RESPONSIVE_CSS, sidebar_nav
from portal_view import mostrar_portal

st.set_page_config(page_title="Viste esto?", page_icon="👁️", layout="wide")
st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)
sidebar_nav(current="Viste esto?")
mostrar_portal("Viste esto?")
