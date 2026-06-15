# Métricas Potenciales — Meta Graph API v25.0

Documento de análisis sobre qué datos adicionales podrían extraerse de la API de Meta
para enriquecer FStats, ordenados por valor para portales de noticias.

---

## Estado Actual (lo que ya se recolecta)

### Facebook
- Información de página: nombre, seguidores, fans, categoría
- Posts recientes: mensaje, fecha, reacciones, comentarios, compartidos
- Insights de página (30 días): alcance único (`page_impressions_unique`), engagement total (`page_post_engagements`), vistas de página (`page_views_total`)
- Crecimiento de seguidores (cuando está disponible)

### Instagram
- Información de cuenta: seguidores, seguidos, cantidad de publicaciones, biografía
- Posts recientes: likes, comentarios, tipo (Reel/Video/Imagen/Carrusel), permalink
- Insights de cuenta (30 días): alcance, visualizaciones, interacciones totales, cuentas alcanzadas, vistas de perfil
- Insights por post: plays (Reels), alcance, guardados, interacciones

---

## Facebook — Lo que NO se recolecta aún

| Métrica | Campo en API | Valor para el proyecto |
|---|---|---|
| **Datos demográficos de audiencia** | `page_fans_city`, `page_fans_country`, `page_fans_gender_age` | Saber **quienes** son los lectores por ciudad, edad y género — clave para portales regionales. Permitiría un **mapa de calor geográfico** por portal |
| **Alcance orgánico vs viral vs pago** | `page_posts_impressions_organic`, `page_posts_impressions_viral`, `page_posts_impressions_paid` | Entender **cómo** se difunde el contenido (de forma natural, viral, o por anuncios). Fundamental para estrategia editorial |
| **Feedback negativo** | `page_negative_feedback`, `page_negative_feedback_reason` (`hide_all_clicks`, `unfollows`, `reports_spam`) | Saber **por qué** la gente oculta posts o deja de seguir. Muy valioso para portales de noticias que pueden generar reacciones encontradas |
| **Métricas de video** | `page_video_views`, `page_video_complete_views_30s`, `page_video_views_by_distribution_type` | Si publican videos informativos, conocer reproducciones, tasa de completitud y fuentes de distribución |
| **Historias (Stories)** | `/{page_id}/stories` + insights de historia | Las historias son un formato cada vez más usado; no hay ningún tracking de stories actualmente |
| **Fuentes de tráfico** | `page_views_by_section`, `page_views_by_referrer` | Ver qué secciones de Facebook generan más visitas a la página |
| **Impresiones por post** | `page_posts_impressions`, `page_posts_impressions_unique` por post | Ya tenemos reacciones por post, pero no las impresiones/alcance individual de cada post |
| **Mejor horario de publicación** | Correlacionar hora de creación vs engagement | Solo requiere analizar el timestamp que ya se recolecta |

---

## Instagram — Lo que NO se recolecta aún

| Métrica | Campo en API | Valor para el proyecto |
|---|---|---|
| **Datos demográficos de audiencia** | `audience_city`, `audience_country`, `audience_gender_age` | Igual que en Facebook — saber la ubicación y perfil de la audiencia es vital para medios locales |
| **Historias (Stories)** | `/{ig-id}/stories` + `/{story-id}/insights` (`impressions`, `reach`, `replies`, `exits`, `taps_forward`, `taps_back`) | **Mayor omisión actual**. Las historias son un formato principal para noticias y no se recolecta ningún dato de ellas |
| **Desglose de descubrimiento** | `reach` segmentado por `follow`/`non_follow` y fuente (`home`, `search`, `hashtags`, `profile`, `explore`, `other`) | Entender **cómo** encuentran el contenido los usuarios — esencial para optimizar hashtags y estrategia de contenido |
| **Clics al sitio web** | `clicks` (métrica de cuenta o por post) | Rastrear cuántos clics recibe el link en la bio y desde las publicaciones |
| **Guardados (sistemático)** | `saved` — se recolecta para imágenes/carruseles pero no para Reels/videos | Los guardados son una señal fuerte de engagement (marcar para leer después) |
| **Métricas de completitud de Reels** | `ig_reels_avg_watch_time`, `ig_reels_video_view_total_time` | Datos más profundos de engagement en Reels más allá del simple conteo de reproducciones |
| **Datos demográficos de alcanzados** | `reached_audience_demographics` (edad/género/ciudades de las cuentas alcanzadas) | Ver no solo quién te sigue, sino a quién estás llegando realmente |
| **Interacciones en historias** | `taps_forward`, `taps_back`, `taps_exit` por historia | Medir calidad de engagement en stories (¿la gente las ve completas o las saltea?) |

---

## Las 3 incorporaciones de mayor impacto

### 1. Datos demográficos de audiencia (FB + IG)
Permitiría generar un **mapa de calor geográfico** mostrando en qué ciudades/departamentos/provincias tiene más lectores cada portal. Para 6 portales de noticias argentinos, esto sería un diferenciador enorme — poder decir "nuestros lectores en Comodoro Rivadavia vs Trelew vs Rawson".

**Datos necesarios:** `page_fans_city` (FB) + `audience_city` (IG) — ambos disponibles en Graph API v25.0.

### 2. Historias de Instagram (Stories)
Las stories son uno de los formatos de mayor engagement en Instagram, especialmente para medios de noticias que publican contenido efímero (titulares flash, encuestas, coberturas en vivo). Actualmente no se recolecta **ningún** dato de stories.

**Datos disponibles por story:** impresiones, alcance, respuestas, taps adelante/atrás/salir — todo vía `/{ig-id}/stories` + `/{story-id}/insights`.

### 3. Desglose de fuentes de alcance (FB: orgánico/viral/pago; IG: home/search/hashtags)
Entender **cómo** llega la audiencia permite tomar decisiones estratégicas:
- ¿Está funcionando el SEO de hashtags?
- ¿El contenido se está volviendo viral orgánicamente o solo llega a seguidores?
- ¿Tiene sentido invertir en pauta?

**Datos disponibles:** `page_posts_impressions_organic/viral/paid` (FB) + segmentación por `follow`/`non_follow` y fuente de descubrimiento (IG).

---

## Notas técnicas

- **API:** Meta Graph API v25.0 (misma que ya usa el proyecto)
- **Autenticación:** Misma — Page Access Token para Facebook, mismo token sirve para Instagram Business/Creator
- **Permisos adicionales:** Para datos demográficos se necesita `pages_read_engagement` + `pages_manage_metadata` (Facebook) y `instagram_basic` + `instagram_manage_insights` (Instagram) — probablemente ya están habilitados
- **Frecuencia:** Todos estos datos están disponibles en la misma ventana de 30 días que ya usa el proyecto
- **Caché:** Podría integrarse al mismo sistema de `@st.cache_data` con TTL de 1 hora
