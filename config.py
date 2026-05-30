from dotenv import load_dotenv
import os
import streamlit as st

load_dotenv()

RESPONSIVE_CSS = """
<style>
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
