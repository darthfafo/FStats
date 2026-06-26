import streamlit as st
from config import RESPONSIVE_CSS, sidebar_nav, require_pin
from version import APP_VERSION, CHANGELOG

st.set_page_config(page_title="Bitácora", page_icon="📓", layout="wide")
st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)
sidebar_nav(current="")
require_pin("la Bitácora")

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

# ── Esquema de la base de datos (relevamiento en vivo del warehouse) ─────────
st.markdown("---")
st.subheader("🗄️ Esquema de la base de datos")
st.caption(
    "Relevamiento de las tablas del warehouse (MotherDuck). Las **`raw_*`** son "
    "append-only (una fila por ingesta); las **vistas** sin prefijo son las "
    "deduplicadas que lee el panel (último valor por clave)."
)

# Vistas conocidas de la app (lo demás con prefijo raw_ también entra; el resto
# son tablas de sistema de MotherDuck y se descartan).
_VISTAS_APP = {
    "fb_fan_growth", "fb_page_info_daily", "fb_page_insights", "fb_posts",
    "ig_account_info_daily", "ig_account_insights", "ig_demographics", "ig_posts",
    "ig_reach_by_follow_type", "analyzer_runs", "analyzer_outcomes", "analyzer_model",
}

@st.cache_data(ttl=3600, show_spinner=False)
def _relevar_esquema():
    from warehouse.db import get_connection
    con = get_connection(read_only=True)
    return con.execute(
        """select table_name, column_name, data_type
           from information_schema.columns
           where table_schema = 'main'
           order by table_name, ordinal_position""").fetchall()

try:
    _filas = _relevar_esquema()
except Exception as e:
    st.info(f"No pude leer el esquema en vivo del warehouse ({e}).")
else:
    from collections import OrderedDict
    _tabs = OrderedDict()
    for tname, col, dtype in _filas:
        if not (tname.startswith("raw_") or tname in _VISTAS_APP):
            continue
        _tabs.setdefault(tname, []).append((col, dtype))

    _raws  = {t: c for t, c in _tabs.items() if t.startswith("raw_")}
    _views = {t: c for t, c in _tabs.items() if not t.startswith("raw_")}

    col_raw, col_view = st.columns(2)
    with col_raw:
        st.markdown(f"**📥 Tablas `raw_*` — append-only ({len(_raws)})**")
        for t in sorted(_raws):
            with st.expander(f"{t} · {len(_raws[t])} campos"):
                st.markdown("\n".join(f"- `{c}` — {d.lower()}" for c, d in _raws[t]))
    with col_view:
        st.markdown(f"**🔎 Vistas deduplicadas — lo que lee el panel ({len(_views)})**")
        for t in sorted(_views):
            with st.expander(f"{t} · {len(_views[t])} campos"):
                st.markdown("\n".join(f"- `{c}` — {d.lower()}" for c, d in _views[t]))
