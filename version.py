"""
Versión de la aplicación y bitácora de cambios (changelog).

Cubre el historial desde la creación del repo (2026-05-30). Para registrar una
nueva versión: agregá un dict al principio de CHANGELOG y actualizá APP_VERSION.
"""

APP_VERSION = "1.9.0"

# Más reciente primero. fecha en formato YYYY-MM-DD.
CHANGELOG = [
    {
        "version": "1.9.0",
        "fecha":   "2026-06-24",
        "titulo":  "Tokens reconectados y Viste con Facebook",
        "cambios": [
            "Se regeneraron los accesos de Meta como System User Tokens sin vencimiento (uno por portafolio); cada portal con su token propio. La Calle y El Americano pasaron a app/portafolio propios.",
            "Viste Esto ahora muestra Facebook además de Instagram (pestañas FB/IG, como el resto de los portales).",
            "Aviso: durante el período con tokens vencidos quedaron días sin datos; las series diarias se recuperan solo hasta ~30 días atrás (límite de la API de Meta); los huecos más viejos no son recuperables.",
        ],
    },
    {
        "version": "1.8.1",
        "fecha":   "2026-06-22",
        "titulo":  "Atento y Viste reconectados",
        "cambios": [
            "Viste Esto vuelve al panel y a la ingesta (token de usuario del admin de Atento, con ambas páginas).",
        ],
    },
    {
        "version": "1.8.0",
        "fecha":   "2026-06-22",
        "titulo":  "Estadísticas Globales tipo dashboard",
        "cambios": [
            "Indicadores principales en tarjetas azules (estilo del inicio) con variación verde/roja.",
            "Título más compacto y secciones agrupadas por temática (alcance, audiencia, contenido).",
            "Diagnóstico en el gráfico histórico: avisa qué portales aún no tienen alcance cargado en la base.",
        ],
    },
    {
        "version": "1.7.0",
        "fecha":   "2026-06-22",
        "titulo":  "Inicio tipo dashboard",
        "cambios": [
            "Nuevo encabezado de marketing y KPIs en tarjetas azules con explicación siempre visible.",
            "La participación de cada portal pasa de anillo a treemap (aprovecha mejor el espacio).",
            "Tarjetas de portal azules (estilo KPI), responsive en widescreen, con 👁️ que resume lo visto (alcance/visualizaciones).",
            "Mejor legibilidad del texto gris en toda la app (tema claro y oscuro).",
            "Bitácora de versiones (esta sección).",
            "Viste Esto queda oculto del panel y la ingesta hasta configurar su acceso.",
        ],
    },
    {
        "version": "1.6.0",
        "fecha":   "2026-06-21",
        "titulo":  "Estadísticas Globales profesional",
        "cambios": [
            "KPIs con variación de período (últimos 30 días vs los 30 anteriores) y explicaciones.",
            "El gráfico de alcance en escala logarítmica se mueve arriba; tendencia 'En vivo' a 30 días.",
            "Selector en vivo / histórico unificado y generador de informe PDF al final de la sección.",
            "Rendimiento de reels por portal y Top 10 ordenado por difusión real.",
            "Alcance de Facebook resiliente ante la deprecación de métricas de Meta.",
            "Barra lateral consistente en todas las páginas.",
        ],
    },
    {
        "version": "1.5.0",
        "fecha":   "2026-06-21",
        "titulo":  "Audiencia, demografía y conexiones",
        "cambios": [
            "Contribución de seguidores: cobertura y alcance a no-seguidores (desglose por tipo de seguidor).",
            "Demografía de la audiencia (edad, género, geografía) y evolución del crecimiento de seguidores.",
            "Conexión de Viste Esto y El Americano reutilizando el token de su administrador.",
            "Instagram adopta el page token de la página vinculada; la ingesta avisa si a un token le faltan permisos.",
        ],
    },
    {
        "version": "1.4.0",
        "fecha":   "2026-06-15",
        "titulo":  "Analizador de viralidad",
        "cambios": [
            "Análisis del potencial de viralidad de un reel, con puntaje explicado.",
            "Generador de copy y de títulos; modelo entrenado respaldado en la base de datos.",
            "Arreglos en la detección de reels y en las métricas de Instagram.",
        ],
    },
    {
        "version": "1.3.0",
        "fecha":   "2026-06-14",
        "titulo":  "Base de datos histórica",
        "cambios": [
            "Warehouse en MotherDuck con ingesta diaria automática (GitHub Actions).",
            "El panel se sirve desde la base de datos (instantáneo), con respaldo a la API en vivo.",
            "Gráfico de alcance histórico acumulado que crece día a día.",
        ],
    },
    {
        "version": "1.2.0",
        "fecha":   "2026-05-31",
        "titulo":  "Navegación y tendencias",
        "cambios": [
            "Barra lateral unificada en todas las páginas.",
            "Gráfico de tendencia de alcance en escala logarítmica, con colores por portal y manejo de brechas.",
            "Refinamiento del informe PDF (engagement FB+IG, explicaciones, gráficos por portal).",
        ],
    },
    {
        "version": "1.1.0",
        "fecha":   "2026-05-30",
        "titulo":  "Informe PDF",
        "cambios": [
            "Generador de brief PDF profesional (fpdf2) con KPIs, participación y Top 10 de Instagram y Facebook.",
            "Paginación de Instagram hasta 500 publicaciones para el histórico.",
        ],
    },
    {
        "version": "1.0.0",
        "fecha":   "2026-05-30",
        "titulo":  "Lanzamiento",
        "cambios": [
            "Panel de estadísticas multi-portal (Facebook + Instagram).",
            "Diseño responsive para móvil.",
        ],
    },
]
