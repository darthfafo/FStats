from dotenv import load_dotenv
import os
import hashlib
import time
import streamlit as st

load_dotenv()

# Color de marca de cada portal (usado en banners del inicio, tops de Globales,
# recaps, etc.). Mapa canónico para mantener la identidad consistente.
COLOR_PORTAL = {
    "Chubut Noticias": "#64748b", "Atento Chubut": "#22d3ee",
    "La Calle Online": "#f97316", "El Americano": "#22c55e",
    "Viste esto?":     "#a855f7", "Boca en Linea": "#fbbf24",
}

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

/* Títulos más compactos en móvil para que no ocupen toda la pantalla */
@media (max-width: 768px) {
    h1, [data-testid="stHeading"] h1 { font-size: 1.45rem !important; line-height: 1.2 !important; }
    h2 { font-size: 1.2rem !important; }
    h3 { font-size: 1.05rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.35rem !important; }
}

/* Un poco de aire entre secciones (evita que quede todo pegado) */
[data-testid="stHeading"] { margin-top: 0.5rem; }
hr { margin: 0.7rem 0 !important; }

/* Contenedores con borde con look de tarjeta, consistente en toda la app */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px !important;
    border-color: rgba(148,163,184,0.18) !important;
    background: rgba(148,163,184,0.04);
}

/* Tarjetas KPI azules (mismo estilo del inicio) reutilizables en las páginas */
.kpi-grid { display: flex; gap: 14px; flex-wrap: wrap; margin: 4px 0 14px 0; }
.kpi-card {
    flex: 1 1 165px;
    background: linear-gradient(135deg, #0f172a, #1e3a5f);
    border: 1px solid rgba(148,163,184,0.12);
    border-radius: 14px;
    padding: 16px 18px;
}
.kpi-card .k-label {
    color: #e2e8f0; font-size: 11.5px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase;
}
.kpi-card .k-value {
    color: #fff; font-size: clamp(20px, 3.5vw, 28px); font-weight: 800;
    line-height: 1.1; margin-top: 6px;
}
.kpi-card .k-sub   { color: #cbd5e1; font-size: 11.5px; margin-top: 4px; }
.kpi-card .k-delta { font-size: 12.5px; font-weight: 700; margin-top: 6px; }
.kpi-card .k-delta.up   { color: #22c55e; }
.kpi-card .k-delta.down { color: #f87171; }

/* Encabezado de grupo temático (separa secciones por tema) */
.grupo-titulo {
    font-size: clamp(15px, 2.4vw, 19px); font-weight: 800; color: #38bdf8;
    letter-spacing: 0.5px; margin: 2px 0 2px; text-transform: uppercase;
}
.grupo-sub { color: var(--text-color); font-size: 12.5px; margin: 0 0 4px; }

/* Texto secundario (st.caption) LEGIBLE en tema claro y oscuro: usa el color de
   texto del tema, SIN atenuar (el gris tenue por defecto no se leía). */
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p,
[data-testid="stCaptionContainer"] * {
    color: var(--text-color) !important;
    opacity: 1;
}
</style>
"""

_NAV_PORTALES = [
    ("📰", "Chubut Noticias",  "pages/1_Chubut_Noticias.py"),
    ("📡", "Atento Chubut",    "pages/2_Atento_Chubut.py"),
    ("🗞️", "La Calle Online", "pages/3_La_Calle_Online.py"),
    ("🌎", "El Americano",     "pages/4_El_Americano.py"),
    ("👁️", "Viste esto?",     "pages/5_Viste_Esto.py"),
]

def sidebar_nav(current="", show_update=True, extra_widgets=None):
    """
    Sidebar de navegación unificado para todas las páginas.
    current: nombre del portal activo (para resaltarlo).
    extra_widgets: callable que se ejecuta antes del separador final.
    """
    from datetime import datetime as _dt
    # Gate global: bloquea la página (y no muestra ni el sidebar) si el PIN no se
    # ingresó en la última hora. Va primero para no renderizar datos sensibles.
    require_app_pin()
    with st.sidebar:
        st.markdown("### 📊 FStats")
        # Navegación con page_link: es un ancla nativa, mucho más confiable en
        # móvil que button + switch_page (que a veces pedía doble toque o perdía
        # el estado del sidebar). page_link resalta sola la página activa.
        st.page_link("app.py", label="🏠 Panel general")
        st.page_link("pages/0_Estadisticas_Globales.py", label="📊 Estadísticas Globales")
        st.page_link("pages/7_Analizador.py", label="🚀 Analizador")
        st.page_link("pages/8_Realimentacion.py", label="🔁 Realimentación")
        st.page_link("pages/9_Bitacora.py", label="📓 Bitácora")
        st.markdown("---")
        st.caption("PORTALES")
        for icono, nombre, pagina in _NAV_PORTALES:
            st.page_link(pagina, label=f"{icono} {nombre}")
        st.markdown("---")
        # Widgets extra (botón PDF, etc.)
        if extra_widgets:
            extra_widgets()
        if show_update:
            if st.session_state.get("fstats_live", False):
                st.caption("🟢 Datos EN VIVO (API)")
                if st.button("⚡ Volver a modo rápido", use_container_width=True,
                             key="nav_fast"):
                    st.session_state["fstats_live"] = False
                    st.cache_data.clear()
                    st.rerun()
            else:
                if st.button("🔄 Actualizar (en vivo)", use_container_width=True,
                             key="nav_update"):
                    st.session_state["fstats_live"] = True
                    st.cache_data.clear()
                    st.rerun()
        try:
            from version import APP_VERSION
            st.caption(f"FStats v{APP_VERSION} · {_dt.now().strftime('%d/%m/%Y %H:%M')}")
        except Exception:
            st.caption(_dt.now().strftime("%d/%m/%Y %H:%M"))


def _secret(key, default="PENDIENTE"):
    try:
        val = st.secrets[key]
    except Exception:
        val = os.getenv(key, default)
    # Una env var presente pero vacía (típico en CI cuando falta el secret)
    # no debe pisar el valor por defecto.
    return val if val not in (None, "") else default


# ── PIN de acceso a TODO el panel (datos sensibles) ───────────────────────────
# Se guarda SOLO el hash SHA-256 (nunca el PIN en texto plano); se puede override
# desde secrets con FSTATS_PIN_HASH. El desbloqueo se recuerda 1 hora por sesión.
_PIN_HASH = _secret("FSTATS_PIN_HASH",
                    "251cd2d8d9d3d6281a8bf72251a7af1f3c4d323906806474772960f3968a7342")
_PIN_TTL_SEG = 3600   # validez del desbloqueo: 1 hora


def _pin_vigente():
    """¿El PIN se ingresó dentro de la última hora (en esta sesión)?"""
    return time.time() < st.session_state.get("fstats_pin_ok_until", 0)


def require_app_pin():
    """Gate GLOBAL del panel: si no se ingresó el PIN en la última hora, bloquea
    la página y lo pide. Pensado para llamarse en CADA página (va dentro de
    sidebar_nav, que corre en todas). El PIN se compara por hash, nunca en claro.
    Al refrescar el navegador (sesión nueva) se vuelve a pedir."""
    if _pin_vigente():
        return
    st.markdown("## 🔒 Panel protegido")
    st.caption("Los datos del panel son sensibles. Ingresá el PIN para acceder "
               "(se recordará durante 1 hora).")
    with st.form("pin_form_global"):
        pin    = st.text_input("PIN", type="password", max_chars=16)
        entrar = st.form_submit_button("Entrar")
    if entrar:
        if hashlib.sha256(pin.strip().encode()).hexdigest() == _PIN_HASH:
            st.session_state["fstats_pin_ok_until"] = time.time() + _PIN_TTL_SEG
            st.rerun()
        else:
            st.error("PIN incorrecto.")
    st.stop()


def require_pin(seccion="esta sección"):
    """Compatibilidad: el PIN ahora es global (mismo gate de 1 hora)."""
    require_app_pin()


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
        # Mismo administrador que La Calle Online: si no hay un token propio de
        # El Americano, reutilizamos el de La Calle (tiene permiso sobre esta cuenta).
        "access_token":     _secret("META_PAGE_ACCESS_TOKEN_AMERICANO",
                                    _secret("META_PAGE_ACCESS_TOKEN_LACALLE", "PENDIENTE")),
        "color_fb":         "#1877F2",
        "color_ig":         "#E1306C",
        "pagina":           "pages/4_El_Americano.py"
    },
    {
        "nombre":           "Viste esto?",
        "icono":            "👁️",
        "ig_only":          False,
        "facebook_page_id": _secret("META_PAGE_ID_VISTE",          "1083370151536332"),
        # Aceptamos el @usuario como valor por defecto: la ingesta resuelve el
        # ID numérico real consultando las cuentas que administra el token (ver
        # InstagramCollector._adopt_page_token). Si preferís fijar el ID numérico,
        # cargá META_INSTAGRAM_ID_VISTE en los secrets.
        "instagram_id":     _secret("META_INSTAGRAM_ID_VISTE",     "visteestook"),
        # Viste tiene su PROPIO token (portafolio distinto al de Atento; no comparte).
        "access_token":     _secret("META_PAGE_ACCESS_TOKEN_VISTE", "PENDIENTE"),
        "color_fb":         "#1877F2",
        "color_ig":         "#E1306C",
        "pagina":           "pages/5_Viste_Esto.py",
    },
    {
        "nombre":           "Boca en Linea",
        "icono":            "🇸🇪",
        "ig_only":          True,
        "oculto":           True,   # oculto del panel, stats e ingesta hasta nuevo aviso
        "facebook_page_id": None,
        "instagram_id":     _secret("META_INSTAGRAM_ID_BOCA",     "PENDIENTE"),
        "access_token":     _secret("META_PAGE_ACCESS_TOKEN_BOCA", "PENDIENTE"),
        "color_fb":         "#1877F2",
        "color_ig":         "#E1306C",
        "pagina":           "pages/6_Boca_En_Linea.py"
    },
]


# ── Fuente de datos: warehouse (rápido) por defecto, API en vivo si live=True ──
_warehouse_ok = None  # None = sin probar; True = anduvo (se cachea); False no se cachea


def _warehouse_disponible():
    """¿Se puede leer del warehouse? Solo cachea el ÉXITO: si falla, reintenta
    en la próxima llamada (evita quedar pegado en 'no disponible' si el token se
    arregló después de arrancar). Loguea el error real para diagnóstico."""
    global _warehouse_ok
    if _warehouse_ok:
        return True
    try:
        from warehouse import sources
        sources._q("SELECT 1")
        _warehouse_ok = True
        return True
    except Exception as e:
        print(f"[warehouse] no disponible (se usará API en vivo): {e!r}")
        return False


def fb_source(nombre, page_id, token, live=False):
    """Collector de Facebook: warehouse por defecto, API real si live=True
    (o si el warehouse no está disponible)."""
    if not live and _warehouse_disponible():
        from warehouse.sources import WarehouseFacebookCollector
        return WarehouseFacebookCollector(nombre=nombre, page_id=page_id, access_token=token)
    from collectors.facebook import FacebookCollector
    return FacebookCollector(page_id=page_id, access_token=token)


def ig_source(nombre, ig_id, token, live=False):
    """Collector de Instagram: warehouse por defecto, API real si live=True
    (o si el warehouse no está disponible)."""
    if not live and _warehouse_disponible():
        from warehouse.sources import WarehouseInstagramCollector
        return WarehouseInstagramCollector(nombre=nombre, ig_id=ig_id, access_token=token)
    from collectors.instagram import InstagramCollector
    return InstagramCollector(ig_id=ig_id, access_token=token)
