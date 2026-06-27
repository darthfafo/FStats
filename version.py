"""
Versión de la aplicación y bitácora de cambios (changelog).

Cubre el historial desde la creación del repo (2026-05-30). Para registrar una
nueva versión: agregá un dict al principio de CHANGELOG y actualizá APP_VERSION.
"""

APP_VERSION = "1.9.22"

# Más reciente primero. fecha en formato YYYY-MM-DD.
CHANGELOG = [
    {
        "version": "1.9.22",
        "fecha":   "2026-06-24",
        "titulo":  "Tabla comparativa más limpia y legible",
        "cambios": [
            "La tabla comparativa de Estadísticas Globales saca las columnas 'Estado' y 'FB Vistas', y los encabezados pasan de gris a un color legible (la tabla ahora es HTML, que sí permite recolorear los títulos).",
        ],
    },
    {
        "version": "1.9.21",
        "fecha":   "2026-06-24",
        "titulo":  "Banners del inicio responsive (compu y celular)",
        "cambios": [
            "El contenido de cada banner pasa a una fila flexible que se reacomoda sola: en computadora va todo en una línea y en el celular los stats se ordenan en una grilla prolija (antes se apilaban de a uno y quedaba feo).",
            "La etiqueta dice 'Último mes' en vez de '30 días' y los banners tienen separación entre sí.",
        ],
    },
    {
        "version": "1.9.20",
        "fecha":   "2026-06-24",
        "titulo":  "Banners del inicio: sin la barra problemática",
        "cambios": [
            "Se quitó la barra de participación de cada banner (quedaba cortada en computadora y fea en el celular); el porcentaje de difusión sigue como texto y la participación se ve en la barra de porciones de más abajo.",
            "El nombre de Chubut Noticias va en blanco (su acento es gris y antes no se leía).",
        ],
    },
    {
        "version": "1.9.19",
        "fecha":   "2026-06-24",
        "titulo":  "Inicio: banners más limpios y KPIs mejor explicados",
        "cambios": [
            "Cada banner de portal muestra menos datos y más claros: visualizaciones (grande), y al costado alcance (personas únicas), engagement total y seguidores totales (FB + IG combinados), en vez del desglose Facebook/Instagram que aportaba poco. Chubut Noticias pasa a gris oscuro y la barra de participación queda contenida dentro del banner.",
            "KPIs de arriba: se quitó 'Engagement por publicación' (confundía), 'Alcance' quedó como etiqueta corta, y se reescribieron las explicaciones de todas las cifras (las notas anteriores eran de la primera versión).",
        ],
    },
    {
        "version": "1.9.18",
        "fecha":   "2026-06-24",
        "titulo":  "Inicio: un banner por portal con su color",
        "cambios": [
            "Los portales del inicio pasan de 5 tarjetas angostas a un banner full-width por portal, apilados, cada uno con el color de su marca (borde y tinte). Facebook e Instagram se despliegan al costado, con etiquetas legibles (engagement, vistas, seguidores), y el número de visualizaciones queda grande a la izquierda.",
        ],
    },
    {
        "version": "1.9.17",
        "fecha":   "2026-06-24",
        "titulo":  "Secciones internas con PIN + esquema de la base",
        "cambios": [
            "El Analizador, la Realimentación y la Bitácora quedan protegidos con un PIN (se valida una vez por sesión). El PIN se guarda solo como hash, nunca en texto plano.",
            "La Bitácora suma una sección con el esquema de la base de datos (tablas y campos del warehouse), relevado en vivo.",
            "Estadísticas Globales: se quitó el gráfico 'seguidores vs no-seguidores' (el alcance a seguidores es chico y el de no-seguidores está inflado por los reels de prueba, así que confundía más de lo que aportaba).",
        ],
    },
    {
        "version": "1.9.16",
        "fecha":   "2026-06-24",
        "titulo":  "Viste Esto se escribe 'Viste esto?'; gráfico de tendencia más prolijo",
        "cambios": [
            "El portal pasa a mostrarse como 'Viste esto?' en toda la app (antes 'VISTE ESTO?'), manteniendo sus datos.",
            "Estadísticas Globales: se quitó el gráfico de barras 'Facebook vs Instagram'; el gráfico de tendencia reajusta la escala para no desperdiciar la mitad de abajo y el título ya no aclara 'Instagram' (se sobreentiende).",
        ],
    },
    {
        "version": "1.9.15",
        "fecha":   "2026-06-24",
        "titulo":  "Estadísticas Globales más claras",
        "cambios": [
            "El gráfico de tendencia muestra solo Instagram (se quitaron las líneas de Facebook, que ya no son alcance) y la escala se reajusta a esos valores.",
            "Se quitó la 'cobertura de seguidores' (métrica, gráfico y columna) por aportar poco; las métricas de audiencia pasan a tarjetas estilo KPI.",
            "Texto secundario (captions) ahora legible tanto en tema claro como oscuro (usa el color del tema en vez de un gris tenue).",
        ],
    },
    {
        "version": "1.9.14",
        "fecha":   "2026-06-24",
        "titulo":  "Hero de portal: solo el total",
        "cambios": [
            "El encabezado de cada página de portal ahora muestra únicamente el total de visualizaciones (Facebook + Instagram), centrado; se quitó el desglose FB/IG de al lado, que con FB en vistas ya no tenía sentido.",
        ],
    },
    {
        "version": "1.9.13",
        "fecha":   "2026-06-24",
        "titulo":  "Facebook lidera con engagement en todo el panel",
        "cambios": [
            "En las 5 páginas de portal, la pestaña de Facebook ahora encabeza con el engagement (real) en vez del alcance (que Meta deprecó); el gráfico 'Alcance diario' pasó a 'Difusión diaria' (vistas) y se quitó el alcance falso del encabezado.",
            "En Estadísticas Globales la columna 'FB Alcance' de la tabla pasó a 'FB Vistas'.",
        ],
    },
    {
        "version": "1.9.12",
        "fecha":   "2026-06-24",
        "titulo":  "KPI: Engagement por publicación",
        "cambios": [
            "Se reemplazó el KPI 'Tasa de engagement' (que daba >100% porque dividía interacciones de 30 días por seguidores) por 'Engagement por publicación': interacciones promedio que recibe cada post (FB + IG). Mucho más fácil de interpretar.",
        ],
    },
    {
        "version": "1.9.11",
        "fecha":   "2026-06-24",
        "titulo":  "Inicio: participación como barra minimalista",
        "cambios": [
            "Se reemplazó el treemap de participación por una barra minimalista con porciones proporcionales al aporte de cada portal, con leyenda.",
            "Se quitó el gráfico de barras 'Facebook vs Instagram por portal' (ya no tenía sentido sin el alcance de FB).",
            "El número de visualizaciones de cada tarjeta ahora tiene el mismo look que los KPIs de arriba (blanco, en negrita).",
        ],
    },
    {
        "version": "1.9.10",
        "fecha":   "2026-06-24",
        "titulo":  "Inicio: KPIs más relevantes y tarjetas más legibles",
        "cambios": [
            "Se reemplazaron los KPIs de Facebook (número bajo) e Instagram (redundante con el hero) por Alcance · personas únicas y Crecimiento de seguidores (30d).",
            "Las tarjetas de portal tienen el número y el título mucho más grandes (legibles), manteniéndose responsive (5 en escritorio, 2 en celular).",
        ],
    },
    {
        "version": "1.9.9",
        "fecha":   "2026-06-24",
        "titulo":  "Facebook lidera con engagement (Meta deprecó el alcance)",
        "cambios": [
            "Meta eliminó por completo el alcance de página de Facebook; el panel deja de mostrar ese dato (que ya era un proxy engañoso) y en el inicio Facebook pasa a liderar con el engagement (real), con las vistas de página como secundario.",
            "Se reemplazó 'alcance de la red' por 'difusión de la red' y 'Alcance total' por 'Visualizaciones' en las tarjetas del inicio.",
        ],
    },
    {
        "version": "1.9.8",
        "fecha":   "2026-06-24",
        "titulo":  "Texto más conciso en Estadísticas Globales",
        "cambios": [
            "Se acortó la introducción de Estadísticas Globales a una sola línea (antes era un párrafo largo).",
        ],
    },
    {
        "version": "1.9.7",
        "fecha":   "2026-06-24",
        "titulo":  "Tarjetas de portal responsive en el celular",
        "cambios": [
            "En el celular las tarjetas de portal pasan a 2 por fila (antes se apilaban de a una y desperdiciaban el ancho); en escritorio siguen las 5 en una fila.",
            "El número de alcance escala con el tamaño de pantalla y la etiqueta ya no se trunca en columnas angostas.",
        ],
    },
    {
        "version": "1.9.6",
        "fecha":   "2026-06-24",
        "titulo":  "Tarjetas de portal más legibles",
        "cambios": [
            "Número de alcance más grande (protagonista de la tarjeta) y stats de Facebook e Instagram una por línea, así no se desbordan y se aprovecha mejor el espacio con los 5 portales en fila.",
        ],
    },
    {
        "version": "1.9.5",
        "fecha":   "2026-06-24",
        "titulo":  "Los 5 portales en una sola fila",
        "cambios": [
            "Las tarjetas de portal del inicio entran las 5 en una misma fila; se compactó el número, el título y las etiquetas para que no se desborden.",
        ],
    },
    {
        "version": "1.9.4",
        "fecha":   "2026-06-24",
        "titulo":  "Ingesta de Facebook más limpia",
        "cambios": [
            "El alcance de página prueba una sola vez la métrica deprecada (en vez de tres) antes de usar el proxy, así el log no se llena de falsos errores.",
            "Las reacciones de los posts de Facebook ahora se enriquecen para los 100 posts (antes solo los primeros 50), recorriendo la Batch API en lotes.",
        ],
    },
    {
        "version": "1.9.3",
        "fecha":   "2026-06-24",
        "titulo":  "Viste Esto completo (FB + IG)",
        "cambios": [
            "Viste Esto queda totalmente conectado con su token propio sin vencimiento; se corrigió el ID de la página de Facebook (el correcto del Graph API es 1083370151536332).",
        ],
    },
    {
        "version": "1.9.2",
        "fecha":   "2026-06-24",
        "titulo":  "Fix: errores de la API ya no se confunden con token vencido",
        "cambios": [
            "Arreglo de un bug que abortaba los insights de Facebook cuando Meta deprecaba una métrica: el error 'code 100' se confundía con 'code 10' (token sin permiso) por coincidencia de subcadena. Ahora se distingue bien y el alcance/engagement de página deja de perderse de más.",
        ],
    },
    {
        "version": "1.9.1",
        "fecha":   "2026-06-24",
        "titulo":  "Boca en Línea oculto",
        "cambios": [
            "Boca en Línea queda oculto del panel, las Estadísticas Globales y la ingesta hasta nuevo aviso.",
        ],
    },
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
