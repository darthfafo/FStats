"""
Generador de brief PDF profesional -Panel de Estadisticas FStats.
"""
from fpdf import FPDF
from datetime import datetime
import io

# ── Paleta ───────────────────────────────────────────────────────────
DARK    = (15,  23,  42)
DARK2   = (30,  41,  59)
BLUE    = (24,  119, 242)
PINK    = (193, 53,  132)
GREEN   = (22,  163, 74)
AMBER   = (245, 158, 11)
PURPLE  = (139, 92,  246)
TEAL    = (20,  184, 166)
SLATE   = (100, 116, 139)
LIGHT   = (241, 245, 249)
WHITE   = (255, 255, 255)

PORTAL_COLORS = [BLUE, PINK, GREEN, AMBER, PURPLE, TEAL]


def _fmt(n):
    try:
        return f"{int(n):,}".replace(",", ".")
    except Exception:
        return "0"


def _safe(text):
    return (str(text) or "").encode("latin-1", errors="replace").decode("latin-1")


def _pct(part, total):
    if total <= 0:
        return 0.0
    return round(part / total * 100, 1)


# ── Clase principal ───────────────────────────────────────────────────
class Brief(FPDF):

    def header(self):
        self.set_fill_color(*DARK)
        self.rect(0, 0, 210, 24, "F")
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 14)
        self.set_y(5)
        self.cell(0, 8, "INFORME DE RENDIMIENTO DIGITAL", align="C",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 5,
                  f"Ultimos 30 dias  |  {datetime.now().strftime('%d/%m/%Y')}  |  FStats Panel",
                  align="C")
        self.ln(16)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*SLATE)
        self.cell(0, 5,
                  f"FStats  |  Pagina {self.page_no()} de {{nb}}  |  Confidencial",
                  align="C")

    # ── Helpers de dibujo ─────────────────────────────────────────────

    def _section_title(self, text, color=DARK):
        self.set_fill_color(*LIGHT)
        self.set_draw_color(*LIGHT)
        self.rect(self.l_margin, self.get_y(), 182, 8, "F")
        self.set_fill_color(*color)
        self.rect(self.l_margin, self.get_y(), 3, 8, "F")
        self.set_xy(self.l_margin + 6, self.get_y() + 1)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*DARK)
        self.cell(0, 6, _safe(text.upper()))
        self.ln(11)

    def _kpi_boxes(self, items, height=20):
        """items = [(label, valor, sublabel, color)]"""
        w = 182 / len(items)
        x0, y0 = self.l_margin, self.get_y()
        for label, valor, sublabel, color in items:
            self.set_fill_color(*LIGHT)
            self.rect(x0, y0, w - 2, height, "F")
            self.set_fill_color(*color)
            self.rect(x0, y0, w - 2, 2.5, "F")
            # Label
            self.set_xy(x0 + 2, y0 + 4)
            self.set_font("Helvetica", "", 6)
            self.set_text_color(*SLATE)
            self.cell(w - 4, 3.5, _safe(label.upper()))
            # Valor
            self.set_xy(x0 + 2, y0 + 7.5)
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*DARK)
            self.cell(w - 4, 6, _safe(valor))
            # Sub
            if sublabel:
                self.set_xy(x0 + 2, y0 + 13.5)
                self.set_font("Helvetica", "", 5.5)
                self.set_text_color(*SLATE)
                self.cell(w - 4, 3, _safe(sublabel))
            x0 += w
        self.set_xy(self.l_margin, y0 + height + 3)

    def _participation_chart(self, resumenes, total):
        """Grafico horizontal de barras por portal."""
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*DARK)
        self.cell(0, 6, "Participacion en el impacto total (%)", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

        bar_w = 120
        bar_h = 7
        x0 = self.l_margin

        for i, d in enumerate(resumenes):
            pct = _pct(d.get("total_imp", 0), total)
            color = PORTAL_COLORS[i % len(PORTAL_COLORS)]
            y = self.get_y()

            # Nombre portal
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*DARK)
            self.set_xy(x0, y + 1)
            nombre_corto = _safe(d["nombre"])[:18]
            self.cell(44, bar_h - 2, nombre_corto)

            # Fondo barra
            self.set_fill_color(*LIGHT)
            self.rect(x0 + 45, y + 1, bar_w, bar_h - 2, "F")

            # Barra rellena
            fill_w = bar_w * pct / 100
            if fill_w > 0:
                self.set_fill_color(*color)
                self.rect(x0 + 45, y + 1, fill_w, bar_h - 2, "F")

            # Porcentaje
            self.set_font("Helvetica", "B", 7)
            self.set_text_color(*DARK)
            self.set_xy(x0 + 45 + bar_w + 3, y + 1)
            self.cell(20, bar_h - 2, f"{pct}%")

            # Valor absoluto
            self.set_font("Helvetica", "", 6.5)
            self.set_text_color(*SLATE)
            self.set_xy(x0 + 45 + bar_w + 20, y + 1)
            self.cell(25, bar_h - 2, _fmt(d.get("total_imp", 0)))

            self.ln(bar_h + 1)

    def _text_block(self, text, color=DARK, bold=False):
        font_style = "B" if bold else ""
        self.set_font("Helvetica", font_style, 8)
        self.set_text_color(*color)
        self.multi_cell(182, 4.5, _safe(text))
        self.ln(2)

    def _concept_box(self, title, body, color=BLUE):
        y0 = self.get_y()
        # Borde izquierdo de color
        self.set_fill_color(*color)
        self.rect(self.l_margin, y0, 2, 999, "F")  # se dibujara mas abajo

        self.set_xy(self.l_margin + 5, y0)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*color)
        self.cell(0, 5, _safe(title), new_x="LMARGIN", new_y="NEXT")
        self.set_x(self.l_margin + 5)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*DARK)
        self.multi_cell(177, 4, _safe(body))

        y1 = self.get_y()
        # Redibujar borde con altura correcta
        self.set_fill_color(*color)
        self.rect(self.l_margin, y0, 2, y1 - y0 + 1, "F")
        self.ln(4)

    def _portal_section(self, d, total, color):
        nombre = _safe(d["nombre"])

        # Encabezado del portal
        self.set_fill_color(*DARK2)
        self.set_draw_color(*DARK2)
        self.rect(self.l_margin, self.get_y(), 182, 9, "F")
        self.set_fill_color(*color)
        self.rect(self.l_margin, self.get_y(), 4, 9, "F")
        self.set_xy(self.l_margin + 7, self.get_y() + 1.5)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*WHITE)
        pct = _pct(d.get("total_imp", 0), total)
        self.cell(120, 6, nombre.upper())
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(148, 163, 184)
        self.cell(0, 6, f"{pct}% del total  |  {_fmt(d.get('total_imp', 0))} visualizaciones", align="R")
        self.ln(12)

        # Total visualizaciones
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(*DARK)
        self.cell(0, 10, _fmt(d.get("total_imp", 0)), new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*SLATE)
        self.cell(0, 4, "visualizaciones totales  (Facebook alcance unico + Instagram reproducciones) -ultimos 30 dias",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

        # KPIs Facebook
        fb_imp = d.get("fb_imp", 0)
        fb_seg = d.get("fb_seg", 0)
        fb_eng = d.get("fb_eng", 0)
        ig_imp = d.get("ig_imp", 0)
        ig_reach = d.get("ig_reach", 0)
        ig_seg = d.get("ig_seg", 0)
        ig_eng = d.get("ig_engaged", 0)

        if fb_imp > 0 or fb_seg > 0:
            self.set_font("Helvetica", "B", 7)
            self.set_text_color(*BLUE)
            self.cell(0, 5, "FACEBOOK", new_x="LMARGIN", new_y="NEXT")
            tasa = _pct(fb_eng, fb_seg)
            self._kpi_boxes([
                ("Alcance unico",     _fmt(fb_imp), "personas distintas que vieron contenido", BLUE),
                ("Engagement total",  _fmt(fb_eng), "likes + comentarios + compartidos", BLUE),
                ("Tasa engagement",   f"{tasa}%",   "engagement / seguidores x 100", BLUE),
                ("Seguidores",        _fmt(fb_seg), "fans de la pagina", BLUE),
            ], height=22)

        if ig_imp > 0 or ig_seg > 0:
            self.set_font("Helvetica", "B", 7)
            self.set_text_color(*PINK)
            self.cell(0, 5, "INSTAGRAM", new_x="LMARGIN", new_y="NEXT")
            self._kpi_boxes([
                ("Reproducciones",    _fmt(ig_imp),   "plays de Reels + videos + fotos", PINK),
                ("Alcance unico",     _fmt(ig_reach), "cuentas distintas que vieron algo", PINK),
                ("Interacciones",     _fmt(ig_eng),   "cuentas que interactuaron (30d)", PINK),
                ("Seguidores",        _fmt(ig_seg),   "seguidores actuales", PINK),
            ], height=22)

        self.ln(3)
        # Linea separadora
        self.set_draw_color(*LIGHT)
        self.line(self.l_margin, self.get_y(), 210 - self.r_margin, self.get_y())
        self.ln(6)


# ── Funcion principal ─────────────────────────────────────────────────
def generar_brief(resumenes: list, totales: dict) -> bytes:
    """Genera el PDF y devuelve bytes para descargar."""

    pdf = Brief()
    pdf.alias_nb_pages()
    pdf.add_page()

    gran_total = totales.get("total_imp", 1) or 1
    total_fb   = totales.get("total_fb", 0)
    total_ig   = totales.get("total_ig", 0)
    total_eng  = totales.get("total_eng", 0)
    total_seg  = totales.get("total_seg", 0)

    # ════════════════════════════════════════════════════════════════
    # PAGINA 1: RESUMEN EJECUTIVO
    # ════════════════════════════════════════════════════════════════

    # Numero hero
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 14, _fmt(gran_total), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 5, "TOTAL DE IMPACTO DIGITAL | SUMA DE ALCANCE FB + REPRODUCCIONES IG | ULTIMOS 30 DIAS",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # KPI row
    pdf._kpi_boxes([
        ("Alcance Facebook",   _fmt(total_fb),  f"{_pct(total_fb, gran_total)}% del total", BLUE),
        ("Visualiz. Instagram",_fmt(total_ig),  f"{_pct(total_ig, gran_total)}% del total", PINK),
        ("Engagement FB total",_fmt(total_eng), "interacciones en publicaciones", GREEN),
        ("Seguidores totales", _fmt(total_seg), f"{len(resumenes)} portal(es) activo(s)", DARK2),
    ], height=22)

    # Grafico de participacion
    pdf._section_title("Participacion de cada portal en el impacto total", DARK)
    pdf._participation_chart(resumenes, gran_total)
    pdf.ln(4)

    # ════════════════════════════════════════════════════════════════
    # PAGINA 2: CONCEPTOS CLAVE
    # ════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf._section_title("Como se construye el total de impacto", DARK)

    pdf._text_block(
        "El numero de impacto total que ves en este informe combina dos metricas distintas "
        "segun la red social, porque cada plataforma mide la exposicion de manera diferente:",
        color=SLATE
    )

    pdf._concept_box(
        "Facebook -Alcance unico (personas)",
        "En Facebook, contamos el ALCANCE UNICO: la cantidad de personas distintas que vieron "
        "al menos una publicacion de la pagina durante los ultimos 30 dias. "
        "Esta metrica no se repite si la misma persona vio 10 publicaciones: cuenta como 1. "
        "Es una medida real del tamano de la audiencia impactada. "
        "Fuente: Meta Business Insights (page_impressions_unique).",
        color=BLUE
    )

    pdf._concept_box(
        "Instagram -Reproducciones totales (visualizaciones)",
        "En Instagram, contamos las REPRODUCCIONES TOTALES: la suma de todas las veces que "
        "se reproducio o vio cualquier contenido (Reels, videos, fotos). "
        "A diferencia de Facebook, una misma persona puede sumar multiples visualizaciones. "
        "Este numero refleja el volumen total de consumo de contenido. "
        "Fuente: Meta Business Insights (views total_value).",
        color=PINK
    )

    pdf._text_block(
        "Por eso el total de impacto no es una metrica homogenea: Facebook aporta personas reales "
        "y Instagram aporta visualizaciones totales. Ambas son valiosas pero miden cosas distintas.",
        color=SLATE
    )

    pdf.ln(3)
    pdf._section_title("Que es el Engagement y como se mide", DARK)

    pdf._concept_box(
        "Engagement -Definicion",
        "El ENGAGEMENT mide la interaccion activa del publico con el contenido: "
        "no alcanza con que alguien lo vea, tiene que hacer algo (darle like, comentar o compartir). "
        "Un alto engagement indica que el contenido resuena con la audiencia y genera respuesta.",
        color=GREEN
    )

    pdf._concept_box(
        "Componentes del Engagement en Facebook",
        "LIKES/REACCIONES: muestra aprobacion o emocion ante una publicacion.\n"
        "COMENTARIOS: el nivel mas alto de participacion; el usuario dedica tiempo a escribir.\n"
        "COMPARTIDOS: la maxima amplificacion; el usuario difunde el contenido a su red.\n\n"
        "Formula: Tasa de Engagement = (Likes + Comentarios + Compartidos) / Seguidores x 100\n"
        "Una tasa superior al 1-3% es considerada buena en medios digitales.",
        color=GREEN
    )

    pdf._concept_box(
        "Interacciones en Instagram",
        "Instagram reporta las CUENTAS QUE INTERACTUARON: la cantidad de perfiles unicos "
        "que dieron like, comentaron, guardaron o compartieron algun contenido en los ultimos 30 dias. "
        "Este numero es mas conservador que el de Facebook porque cuenta personas, no acciones.",
        color=PINK
    )

    pdf.ln(3)
    pdf._section_title("Por que importa el alcance organico", DARK)
    pdf._text_block(
        "Todo el impacto reflejado en este informe es ORGANICO: generado sin inversion publicitaria. "
        "Representa la audiencia real y fiel que consume el contenido de forma voluntaria. "
        "El crecimiento organico sostenido es el indicador mas solido de la salud digital "
        "de un medio, porque refleja relevancia genuina en la comunidad.",
        color=SLATE
    )

    # ════════════════════════════════════════════════════════════════
    # PAGINAS SIGUIENTES: DETALLE POR PORTAL
    # ════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf._section_title("Detalle por portal -metricas individuales", DARK)

    for i, d in enumerate(resumenes):
        color = PORTAL_COLORS[i % len(PORTAL_COLORS)]
        if pdf.get_y() > 220:
            pdf.add_page()
            pdf._section_title("Detalle por portal (continuacion)", DARK)
        pdf._portal_section(d, gran_total, color)

    # ════════════════════════════════════════════════════════════════
    # NOTAS METODOLOGICAS
    # ════════════════════════════════════════════════════════════════
    if pdf.get_y() > 240:
        pdf.add_page()
    pdf.ln(2)
    pdf.set_draw_color(*LIGHT)
    pdf.line(pdf.l_margin, pdf.get_y(), 210 - pdf.r_margin, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 4, "NOTAS METODOLOGICAS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 6.5)
    pdf.multi_cell(0, 3.8,
        "Fuente de datos: Meta Graph API v25.0 consultada al momento de generacion de este informe. "
        "Los datos se actualizan cada hora en el panel en linea. "
        "Facebook: alcance unico proviene de page_impressions_unique (Meta Business Insights). "
        "Instagram: visualizaciones provienen de la metrica 'views' (total_value) de la cuenta profesional. "
        "Engagement: suma de interacciones en publicaciones de Facebook segun page_post_engagements. "
        "Los portales marcados como 'solo Instagram' no tienen datos de Facebook. "
        "Porcentajes calculados sobre el total combinado FB+IG de todos los portales activos."
    )

    return bytes(pdf.output())
