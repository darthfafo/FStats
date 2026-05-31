from dotenv import load_dotenv
import os
import streamlit as st

load_dotenv()

RESPONSIVE_CSS = """
<style>
/* Ocultar la navegación automática de Streamlit */
[data-testid="stSidebarNav"],
[data-testid="stSidebarNavItems"],
[data-testid="stSidebarNavSeparator"],
.css-1544g2n, .css-k1vhr4,
section[data-testid="stSidebar"] ul {
    display: none !important;
}

@media (max-width: 768px) {
    div[style*="font-size:60px"], div[style*="font-size: 60px"] {
        font-size: 36px !important;
    }
    div[style*="font-size:56px"], div[style*="font-size: 56px"] {
        font-size: 32px !important;
    }
    div[style*="font-size:28px"], div[style*="font-size: 28px"] {
        font-size: 20px !important;
    }
    div[style*="justify-content:space-between"] {
        flex-direction: column !important;
        gap: 16px !important;
    }
    div[style*="padding:28px 32px"] {
        padding: 18px 14px !important;
    }
    div[style*="gap:32px"] {
        gap: 12px !important;
    }
    section[data-testid="stSidebar"] > div {
        padding-top: 1rem !important;
    }
}
</style>
"""

_NAV_PORTALES = [
    ("📰", "Chubut Noticias",  "pages/1_Chubut_Noticias.py"),
    ("📡", "Atento Chubut",    "pages/2_Atento_Chubut.py"),
    ("🗞️", "La Calle Online", "pages/3_La_Calle_Online.py"),
    ("🌎", "El Americano",     "pages/4_El_Americano.py"),
]

def sidebar_nav(current="", show_update=True, extra_widgets=None):
    """
    Sidebar de navegación unificado para todas las páginas.
    current: nombre del portal activo (para resaltarlo).
    extra_widgets: callable que se ejecuta antes del separador final.
    """
    from datetime import datetime as _dt
    with st.sidebar:
        st.markdown("### 📊 FStats")
        st.markdown("---")
        # Panel general
        if st.button("🏠 Panel general", use_container_width=True, key="nav_home"):
            st.switch_page("app.py")
        # Estadísticas globales
        if st.button("📊 Estadísticas Globales", use_container_width=True, key="nav_stats"):
            st.switch_page("pages/0_Estadisticas_Globales.py")
        st.markdown("---")
        st.caption("PORTALES")
        for icono, nombre, pagina in _NAV_PORTALES:
            btn_type = "primary" if nombre == current else "secondary"
            if st.button(f"{icono} {nombre}", use_container_width=True,
                         key=f"nav_{nombre}", type=btn_type):
                st.switch_page(pagina)
        st.markdown("---")
        # Widgets extra (botón PDF, etc.)
        if extra_widgets:
            extra_widgets()
        if show_update:
            if st.button("🔄 Actualizar", use_container_width=True, key="nav_update"):
                st.cache_data.clear()
                st.rerun()
        st.caption(_dt.now().strftime("%d/%m/%Y %H:%M"))


def _secret(key, default="PENDIENTE"):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)

PORTALES = [
    {
        "nombre":           "Chubut Noticias",
        "icono":            "📰",
        "ig_only":          False,
        "facebook_page_id": _secret("META_PAGE_ID",        "2152363811519964"),
        "instagram_id":     _secret("META_INSTAGRAM_ID",   "17841434190465198"),
        "access_token":     _secret("META_PAGE_ACCESS_TOKEN"),
        "color_fb":         "#1877F2",
        "color_ig":         "#E1306C",
        "pagina":           "pages/1_Chubut_Noticias.py"
    },
    {
        "nombre":           "Atento Chubut",
        "icono":            "📡",
        "ig_only":          False,
        "facebook_page_id": _secret("META_PAGE_ID_ATENTO",        "PENDIENTE"),
        "instagram_id":     _secret("META_INSTAGRAM_ID_ATENTO",   "PENDIENTE"),
        "access_token":     _secret("META_PAGE_ACCESS_TOKEN_ATENTO", "PENDIENTE"),
        "color_fb":         "#1877F2",
        "color_ig":         "#E1306C",
        "pagina":           "pages/2_Atento_Chubut.py"
    },
    {
        "nombre":           "La Calle Online",
        "icono":            "🗞️",
        "ig_only":          False,
        "facebook_page_id": _secret("META_PAGE_ID_LACALLE",          "1095764473614285"),
        "instagram_id":     _secret("META_INSTAGRAM_ID_LACALLE",     "17841480120934998"),
        "access_token":     _secret("META_PAGE_ACCESS_TOKEN_LACALLE", "PENDIENTE"),
        "color_fb":         "#1877F2",
        "color_ig":         "#E1306C",
        "pagina":           "pages/3_La_Calle_Online.py"
    },
    {
        "nombre":           "El Americano",
        "icono":            "🌎",
        "ig_only":          False,
        "facebook_page_id": _secret("META_PAGE_ID_AMERICANO",          "542904062233857"),
        "instagram_id":     _secret("META_INSTAGRAM_ID_AMERICANO",     "17841472028591526"),
        "access_token":     _secret("META_PAGE_ACCESS_TOKEN_AMERICANO", "PENDIENTE"),
        "color_fb":         "#1877F2",
        "color_ig":         "#E1306C",
        "pagina":           "pages/4_El_Americano.py"
    },
    {
        "nombre":           "VISTE ESTO?",
        "icono":            "👁️",
        "ig_only":          True,
        "facebook_page_id": None,
        "instagram_id":     _secret("META_INSTAGRAM_ID_VISTE",     "PENDIENTE"),
        "access_token":     _secret("META_PAGE_ACCESS_TOKEN_VISTE", "PENDIENTE"),
        "color_fb":         "#1877F2",
        "color_ig":         "#E1306C",
        "pagina":           "pages/5_Viste_Esto.py"
    },
    {
        "nombre":           "Boca en Linea",
        "icono":            "🇸🇪",
        "ig_only":          True,
        "facebook_page_id": None,
        "instagram_id":     _secret("META_INSTAGRAM_ID_BOCA",     "PENDIENTE"),
        "access_token":     _secret("META_PAGE_ACCESS_TOKEN_BOCA", "PENDIENTE"),
        "color_fb":         "#1877F2",
        "color_ig":         "#E1306C",
        "pagina":           "pages/6_Boca_En_Linea.py"
    },
]
