"""
Versión de la aplicación y bitácora de cambios (changelog).

Para registrar una nueva versión: agregá un dict al principio de CHANGELOG y
actualizá APP_VERSION. Cada entrada documenta las mejoras de esa sub-versión.
"""

APP_VERSION = "1.6.0"

# Más reciente primero. fecha en formato YYYY-MM-DD.
CHANGELOG = [
    {
        "version": "1.6.0",
        "fecha":   "2026-06-22",
        "titulo":  "Inicio tipo dashboard",
        "cambios": [
            "Nuevo encabezado de marketing y KPIs en tarjetas azules con explicación siempre visible.",
            "La participación de cada portal pasa de anillo a treemap (aprovecha mejor el espacio).",
            "Tarjetas de portal en grilla responsive, con los datos reordenados y más legibles.",
            "Mejor legibilidad del texto gris en toda la app (tema claro y oscuro).",
            "Bitácora de versiones (esta sección).",
            "Viste Esto queda oculto del panel y la ingesta hasta configurar su acceso.",
        ],
    },
    {
        "version": "1.5.0",
        "fecha":   "2026-06-21",
        "titulo":  "Estadísticas Globales profesional",
        "cambios": [
            "KPIs con variación de período (últimos 30 días vs los 30 anteriores) y explicaciones.",
            "El gráfico de alcance en escala logarítmica se mueve arriba, debajo de los KPIs.",
            "Tendencia 'En vivo' limitada a 30 días; selector en vivo / histórico unificado.",
            "Generador de informe PDF al final de la sección.",
            "Barra lateral consistente en todas las páginas.",
        ],
    },
    {
        "version": "1.4.0",
        "fecha":   "2026-06-21",
        "titulo":  "Conexiones e ingesta más robustas",
        "cambios": [
            "Instagram adopta el page token de la página vinculada (arregla métricas con user token).",
            "Alcance de Facebook resiliente ante la deprecación de métricas de Meta.",
            "La ingesta corta temprano y avisa cuando a un token le faltan permisos o páginas.",
        ],
    },
    {
        "version": "1.3.0",
        "fecha":   "2026-06-21",
        "titulo":  "Audiencia y demografía",
        "cambios": [
            "Cobertura de seguidores y alcance a no-seguidores (desglose por tipo de seguidor).",
            "Evolución del crecimiento de seguidores y demografía (edad, género, geografía).",
            "Todo el histórico se acumula en la base de datos día a día.",
        ],
    },
    {
        "version": "1.2.0",
        "fecha":   "2026-06-21",
        "titulo":  "Contribución de seguidores",
        "cambios": [
            "Sección de aporte de cada portal a la base de seguidores y a la audiencia total.",
        ],
    },
    {
        "version": "1.1.0",
        "fecha":   "2026-06-21",
        "titulo":  "Más portales conectados",
        "cambios": [
            "Atento, La Calle Online y El Americano conectados; tokens compartidos por administrador.",
        ],
    },
    {
        "version": "1.0.0",
        "fecha":   "2026-06-15",
        "titulo":  "Versión base",
        "cambios": [
            "Panel multi-portal (Facebook + Instagram), analizador de viralidad y warehouse histórico.",
        ],
    },
]
