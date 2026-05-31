"""
Generador de brief PDF profesional - Panel de Estadisticas FStats.
"""
from fpdf import FPDF
from datetime import datetime
import math

# ── Paleta global ────────────────────────────────────────────────────
DARK   = (15,  23,  42)
DARK2  = (30,  41,  59)
BLUE   = (24,  119, 242)   # Facebook azul
PINK   = (193, 53,  132)   # Instagram rosa
GREEN  = (22,  163, 74)
SLATE  = (100, 116, 139)
LIGHT  = (241, 245, 249)
WHITE  = (255, 255, 255)

# Colores por portal (en orden fijo)
PORTAL_COLOR_MAP = {
    "Chubut Noticias": (30,  30,  30),    # negro
    "Atento Chubut":   (14,  165, 233),   # celeste
    "La Calle Online": (234, 88,  12),    # naranja
    "El Americano":    (22,  163, 74),    # verde
}
PORTAL_COLORS_DEFAULT = [
    (30, 30, 30), (14, 165, 233), (234, 88, 12), (22, 163, 74),
    (139, 92, 246), (20, 184, 166)
]


def _get_color(nombre, index):
    return PORTAL_COLOR_MAP.get(nombre, PORTAL_COLORS_DEFAULT[index % len(PORTAL_COLORS_DEFAULT)])


def _fmt(n):
    try:
        return f"{int(n):,}".replace(",", ".")
    except Exception:
        return "0"


def _safe(text):
    return (str(text) or "").encode("latin-1", errors="replace").decode("latin-1")


def _pct(part, total):
    if not total:
        return 0.0
    return round(part / total * 100, 1)


# ── Clase PDF ────────────────────────────────────────────────────────
class Brief(FPDF):

    def header(self):
        self.set_fill_color(*DARK)
        self.rect(0, 0, 210, 22, "F")
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 14)
        self.set_y(4)
        self.cell(0, 8, "INFORME DE RENDIMIENTO DIGITAL", align="C",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(148, 163, 184)
        self.cell(0, 5,
                  f"Ultimos 30 dias  |  {datetime.now().strftime('%d/%m/%Y')}  |  FStats Panel",
                  align="C")
        self.ln(14)

    def footer(self):
        self.set_y(-11)
        self.set_font("Helvetica", "I", 6.5)
        self.set_text_color(*SLATE)
        self.cell(0, 4,
                  f"FStats  |  Pagina {self.page_no()} de {{nb}}  |  Confidencial",
                  align="C")

    # ── Helpers ───────────────────────────────────────────────────────

    def _section_bar(self, text, color=DARK):
        self.set_fill_color(*LIGHT)
        self.rect(self.l_margin, self.get_y(), 182, 7.5, "F")
        self.set_fill_color(*color)
        self.rect(self.l_margin, self.get_y(), 3, 7.5, "F")
        self.set_xy(self.l_margin + 6, self.get_y() + 1)
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(*DARK)
        self.cell(0, 5.5, _safe(text.upper()))
        self.ln(10)

    def _kpi_row(self, items, height=21):
        w = 182 / len(items)
        x0, y0 = self.l_margin, self.get_y()
        for label, valor, sub, color in items:
            self.set_fill_color(*LIGHT)
            self.rect(x0, y0, w - 1.5, height, "F")
            self.set_fill_color(*color)
            self.rect(x0, y0, w - 1.5, 2.5, "F")
            self.set_xy(x0 + 2, y0 + 4)
            self.set_font("Helvetica", "", 5.8)
            self.set_text_color(*SLATE)
            self.cell(w - 4, 3.5, _safe(label.upper()))
            self.set_xy(x0 + 2, y0 + 7.5)
            self.set_font("Helvetica", "B", 10.5)
            self.set_text_color(*DARK)
            self.cell(w - 4, 6, _safe(valor))
            self.set_xy(x0 + 2, y0 + 14)
            self.set_font("Helvetica", "", 5.5)
            self.set_text_color(*SLATE)
            self.cell(w - 4, 3.5, _safe(sub))
            x0 += w
        self.set_xy(self.l_margin, y0 + height + 3)

    # ── Grafico de torta (donut) ──────────────────────────────────────
    def _draw_sector(self, xc, yc, r, a_start, a_end, color):
        """Dibuja un sector de torta como poligono relleno."""
        steps = max(3, int(abs(a_end - a_start) / 4))
        pts = [(xc, yc)]
        for i in range(steps + 1):
            angle = math.radians(a_start + (a_end - a_start) * i / steps)
            pts.append((xc + r * math.cos(angle),
                        yc + r * math.sin(angle)))
        self.set_fill_color(*color)
        self.set_draw_color(*WHITE)
        self.polygon(pts, style="FD")

    def _donut_chart(self, resumenes, total, xc, yc, r):
        """Dibuja un donut chart en (xc, yc) con radio r."""
        if total <= 0:
            return
        angle = -90.0   # empezar desde arriba (270 = -90)
        for i, d in enumerate(resumenes):
            pct = d.get("total_imp", 0) / total
            if pct <= 0:
                continue
            sweep = pct * 360.0
            color = _get_color(d["nombre"], i)
            self._draw_sector(xc, yc, r, angle, angle + sweep, color)
            angle += sweep

        # Circulo blanco central (efecto donut)
        self.set_fill_color(*WHITE)
        self.set_draw_color(*WHITE)
        hole_r = r * 0.52
        steps = 36
        pts = [(xc + hole_r * math.cos(math.radians(i * 10)),
                yc + hole_r * math.sin(math.radians(i * 10))) for i in range(steps)]
        self.polygon(pts, style="FD")

        # Texto central
        self.set_font("Helvetica", "B", 7.5)
        self.set_text_color(*DARK)
        self.set_xy(xc - 18, yc - 4)
        self.cell(36, 4, _fmt(total), align="C")
        self.set_xy(xc - 18, yc + 1)
        self.set_font("Helvetica", "", 5)
        self.set_text_color(*SLATE)
        self.cell(36, 3, "VISUALIZACIONES", align="C")

    def _donut_legend(self, resumenes, total, x, y):
        """Leyenda del donut con % y valores."""
        for i, d in enumerate(resumenes):
            color = _get_color(d["nombre"], i)
            pct = _pct(d.get("total_imp", 0), total)
            nombre = _safe(d["nombre"])[:18]
            # Cuadrado de color
            self.set_fill_color(*color)
            self.rect(x, y + 1, 4, 4, "F")
            # Nombre
            self.set_xy(x + 6, y)
            self.set_font("Helvetica", "B", 7)
            self.set_text_color(*DARK)
            self.cell(55, 6, nombre)
            # Porcentaje
            self.set_xy(x + 62, y)
            self.set_font("Helvetica", "B", 7)
            self.set_text_color(*color)
            self.cell(15, 6, f"{pct}%")
            # Valor
            self.set_xy(x + 77, y)
            self.set_font("Helvetica", "", 6.5)
            self.set_text_color(*SLATE)
            self.cell(30, 6, _fmt(d.get("total_imp", 0)))
            y += 8

    # ── Barra FB vs IG ────────────────────────────────────────────────
    def _fb_ig_bar(self, fb_imp, ig_imp, width=182, height=6):
        total = (fb_imp or 0) + (ig_imp or 0)
        if total <= 0:
            return
        x0, y0 = self.l_margin, self.get_y()
        fb_w = width * fb_imp / total
        ig_w = width * ig_imp / total
        # FB
        self.set_fill_color(*BLUE)
        if fb_w > 0:
            self.rect(x0, y0, fb_w, height, "F")
        # IG
        self.set_fill_color(*PINK)
        if ig_w > 0:
            self.rect(x0 + fb_w, y0, ig_w, height, "F")
        # Labels
        fb_pct = _pct(fb_imp, total)
        ig_pct = _pct(ig_imp, total)
        self.set_font("Helvetica", "B", 6)
        self.set_text_color(*WHITE)
        if fb_w > 18:
            self.set_xy(x0 + 2, y0 + 1)
            self.cell(fb_w - 4, 4, f"FB {fb_pct}%")
        if ig_w > 18:
            self.set_xy(x0 + fb_w + 2, y0 + 1)
            self.cell(ig_w - 4, 4, f"IG {ig_pct}%")
        self.ln(height + 3)

    # ── Caja de concepto compacta ─────────────────────────────────────
    def _mini_concept(self, icon_text, title, body, color=BLUE):
        y0 = self.get_y()
        self.set_fill_color(*color)
        self.rect(self.l_margin, y0, 2, 100, "F")  # placeholder, se redibuja
        self.set_fill_color(*LIGHT)
        self.rect(self.l_margin + 2, y0, 180, 100, "F")  # placeholder
        self.set_xy(self.l_margin + 5, y0 + 2)
        self.set_font("Helvetica", "B", 7.5)
        self.set_text_color(*color)
        self.cell(0, 4.5, _safe(f"{icon_text}  {title}"))
        self.set_x(self.l_margin + 5)
        self.set_font("Helvetica", "", 6.8)
        self.set_text_color(*DARK)
        self.multi_cell(175, 3.8, _safe(body))
        y1 = self.get_y() + 2
        # Redibujar con altura real
        self.set_fill_color(*color)
        self.rect(self.l_margin, y0, 2, y1 - y0, "F")
        self.set_fill_color(*LIGHT)
        self.rect(self.l_margin + 2, y0, 180, y1 - y0, "F")
        # Redibujar texto encima
        self.set_xy(self.l_margin + 5, y0 + 2)
        self.set_font("Helvetica", "B", 7.5)
        self.set_text_color(*color)
        self.cell(0, 4.5, _safe(f"{icon_text}  {title}"))
        self.set_x(self.l_margin + 5)
        self.set_font("Helvetica", "", 6.8)
        self.set_text_color(*DARK)
        self.multi_cell(175, 3.8, _safe(body))
        self.set_y(y1 + 2)

    # ── Tarjeta de portal ─────────────────────────────────────────────
    def _portal_card(self, d, total, color):
        nombre = _safe(d["nombre"])
        fb_imp  = d.get("fb_imp", 0)
        fb_seg  = d.get("fb_seg", 0)
        fb_eng  = d.get("fb_eng", 0)
        ig_imp  = d.get("ig_imp", 0)
        ig_reach = d.get("ig_reach", 0)
        ig_seg  = d.get("ig_seg", 0)
        ig_eng  = d.get("ig_engaged", 0)
        t_imp   = d.get("total_imp", 0)
        pct     = _pct(t_imp, total)

        # Encabezado
        self.set_fill_color(*DARK2)
        self.rect(self.l_margin, self.get_y(), 182, 8.5, "F")
        self.set_fill_color(*color)
        self.rect(self.l_margin, self.get_y(), 4, 8.5, "F")
        self.set_xy(self.l_margin + 7, self.get_y() + 1.5)
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(*WHITE)
        self.cell(100, 5.5, nombre.upper())
        self.set_font("Helvetica", "", 7)
        self.set_text_color(148, 163, 184)
        self.cell(0, 5.5, f"{pct}% del total  |  {_fmt(t_imp)} visualizaciones", align="R")
        self.ln(11)

        # Total grande
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(*DARK)
        self.cell(0, 10, _fmt(t_imp), new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(*SLATE)
        self.cell(0, 3.5,
                  "visualizaciones totales (FB alcance unico + IG reproducciones) - ultimos 30 dias",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

        # Barra FB vs IG
        self._fb_ig_bar(fb_imp, ig_imp)

        # KPIs FB
        if fb_imp > 0 or fb_seg > 0:
            self.set_font("Helvetica", "B", 6.5)
            self.set_text_color(*BLUE)
            self.cell(0, 4, "FACEBOOK", new_x="LMARGIN", new_y="NEXT")
            # Tasa engagement - cap si es absurda
            if fb_seg > 0 and fb_eng > 0:
                tasa_raw = fb_eng / fb_seg * 100
                tasa_str = f"{tasa_raw:.1f}%" if tasa_raw <= 200 else "N/D*"
            else:
                tasa_str = "0.0%"
            self._kpi_row([
                ("Alcance unico",    _fmt(fb_imp), "personas distintas que vieron contenido", BLUE),
                ("Engagement total", _fmt(fb_eng) if fb_eng > 0 else "—", "likes + comentarios + compartidos", BLUE),
                ("Tasa engagement",  tasa_str,    "engagement / seguidores x 100", BLUE),
                ("Seguidores",       _fmt(fb_seg), "fans de la pagina", BLUE),
            ], height=20)

        # KPIs IG
        if ig_imp > 0 or ig_seg > 0:
            self.set_font("Helvetica", "B", 6.5)
            self.set_text_color(*PINK)
            self.cell(0, 4, "INSTAGRAM", new_x="LMARGIN", new_y="NEXT")
            self._kpi_row([
                ("Reproducciones",  _fmt(ig_imp),   "plays Reels + videos + fotos", PINK),
                ("Alcance unico",   _fmt(ig_reach), "cuentas distintas que vieron algo", PINK),
                ("Interacciones",   _fmt(ig_eng),   "cuentas que interactuaron (30d)", PINK),
                ("Seguidores",      _fmt(ig_seg),   "seguidores actuales", PINK),
            ], height=20)

        self.ln(3)
        self.set_draw_color(*LIGHT)
        self.line(self.l_margin, self.get_y(), 210 - self.r_margin, self.get_y())
        self.ln(5)


# ── Funcion principal ─────────────────────────────────────────────────
def generar_brief(resumenes: list, totales: dict) -> bytes:
    pdf = Brief()
    pdf.alias_nb_pages()

    gran_total = totales.get("total_imp", 1) or 1
    total_fb   = totales.get("total_fb", 0)
    total_ig   = totales.get("total_ig", 0)
    total_eng  = totales.get("total_eng", 0)
    total_seg  = totales.get("total_seg", 0)

    # ════════════════════════════════════════════════════════════════
    # PAGINA 1 — RESUMEN EJECUTIVO + GRAFICOS + CONCEPTOS
    # ════════════════════════════════════════════════════════════════
    pdf.add_page()

    # ── Numero hero ──────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 34)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 12, _fmt(gran_total), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 4,
             "TOTAL DE IMPACTO DIGITAL | ALCANCE FB + REPRODUCCIONES IG | ULTIMOS 30 DIAS",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # ── KPI row ──────────────────────────────────────────────────────
    pdf._kpi_row([
        ("Alcance Facebook",    _fmt(total_fb),  f"{_pct(total_fb, gran_total)}% del total", BLUE),
        ("Visualiz. Instagram", _fmt(total_ig),  f"{_pct(total_ig, gran_total)}% del total", PINK),
        ("Engagement FB total", _fmt(total_eng), "interacciones en publicaciones", GREEN),
        ("Seguidores totales",  _fmt(total_seg), f"{len(resumenes)} portal(es) activo(s)", DARK2),
    ], height=21)

    # ── Seccion graficos: donut + leyenda en dos columnas ─────────────
    pdf._section_bar("Participacion de cada portal en el impacto total", DARK)

    y_graficos = pdf.get_y()
    radio   = 30
    xc      = pdf.l_margin + 38    # centro del donut
    yc      = y_graficos + radio + 4

    # Donut
    pdf._donut_chart(resumenes, gran_total, xc, yc, radio)

    # Leyenda a la derecha del donut
    leyenda_x = pdf.l_margin + 80
    leyenda_y = y_graficos + 6
    pdf._donut_legend(resumenes, gran_total, leyenda_x, leyenda_y)

    pdf.set_y(yc + radio + 6)

    # ── Conceptos clave (en la misma pagina) ─────────────────────────
    pdf._section_bar("Como se construye el impacto total y que es el engagement", DARK)

    # Dos columnas de conceptos
    col_w = 88
    x_izq = pdf.l_margin
    x_der = pdf.l_margin + col_w + 6
    y_cols = pdf.get_y()

    # Columna izquierda
    pdf.set_xy(x_izq, y_cols)
    pdf.set_fill_color(*LIGHT)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(BLUE[0], BLUE[1], BLUE[2])
    pdf.cell(col_w, 5, "FACEBOOK - ALCANCE UNICO (PERSONAS)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x_izq)
    pdf.set_font("Helvetica", "", 6.5)
    pdf.set_text_color(*DARK)
    fb_text = ("Contamos las personas DISTINTAS que vieron al menos una publicacion en 30 dias. "
               "Si la misma persona vio 10 posts, cuenta como 1. "
               "Refleja el tamano real de la audiencia impactada.")
    pdf.multi_cell(col_w, 3.6, _safe(fb_text))
    y_left_1 = pdf.get_y()

    pdf.set_x(x_izq)
    pdf.ln(3)
    pdf.set_x(x_izq)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(GREEN[0], GREEN[1], GREEN[2])
    pdf.cell(col_w, 5, "ENGAGEMENT - QUE ES Y COMO SE MIDE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x_izq)
    pdf.set_font("Helvetica", "", 6.5)
    pdf.set_text_color(*DARK)
    eng_text = ("El engagement mide la INTERACCION ACTIVA: no alcanza ver el contenido, hay que "
                "hacer algo (like, comentar, compartir). "
                "Tasa = (Likes+Comentarios+Compartidos) / Seguidores x 100. "
                "Una tasa del 1-3% es buena en medios digitales.")
    pdf.multi_cell(col_w, 3.6, _safe(eng_text))
    y_left_end = pdf.get_y()

    # Columna derecha
    pdf.set_xy(x_der, y_cols)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(PINK[0], PINK[1], PINK[2])
    pdf.cell(col_w, 5, "INSTAGRAM - REPRODUCCIONES TOTALES", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x_der)
    pdf.set_font("Helvetica", "", 6.5)
    pdf.set_text_color(*DARK)
    ig_text = ("Contamos TODAS LAS VECES que se vio cualquier contenido (Reels, videos, fotos). "
               "Una misma persona puede sumar multiples visualizaciones. "
               "Refleja el volumen total de consumo de contenido.")
    pdf.multi_cell(col_w, 3.6, _safe(ig_text))
    y_right_1 = pdf.get_y()

    pdf.set_x(x_der)
    pdf.ln(3)
    pdf.set_x(x_der)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*DARK)
    pdf.cell(col_w, 5, "POR QUE IMPORTA EL ALCANCE ORGANICO", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x_der)
    pdf.set_font("Helvetica", "", 6.5)
    pdf.set_text_color(*DARK)
    org_text = ("Todo el impacto de este informe es ORGANICO: sin inversion publicitaria. "
                "Representa la audiencia real y fiel. El crecimiento organico es el "
                "indicador mas solido de la salud digital de un medio.")
    pdf.multi_cell(col_w, 3.6, _safe(org_text))
    y_right_end = pdf.get_y()

    pdf.set_y(max(y_left_end, y_right_end) + 4)

    # Nota al pie sobre tasa engagement
    pdf.set_font("Helvetica", "I", 6)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 4,
             "* N/D: Tasa de engagement no disponible o fuera de rango para ese portal.",
             new_x="LMARGIN", new_y="NEXT")

    # ════════════════════════════════════════════════════════════════
    # PAGINA 2+: DETALLE POR PORTAL
    # ════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf._section_bar("Detalle por portal - metricas individuales", DARK)

    for i, d in enumerate(resumenes):
        color = _get_color(d["nombre"], i)
        if pdf.get_y() > 225:
            pdf.add_page()
            pdf._section_bar("Detalle por portal (continuacion)", DARK)
        pdf._portal_card(d, gran_total, color)

    # ── Notas metodologicas ───────────────────────────────────────────
    if pdf.get_y() > 252:
        pdf.add_page()
    else:
        pdf.ln(2)

    pdf.set_draw_color(*LIGHT)
    pdf.line(pdf.l_margin, pdf.get_y(), 210 - pdf.r_margin, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 6.5)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 4, "NOTAS METODOLOGICAS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 6)
    pdf.multi_cell(0, 3.5, _safe(
        "Fuente: Meta Graph API v25.0. Datos actualizados cada hora en el panel en linea. "
        "Facebook: alcance unico = page_impressions_unique. "
        "Instagram: reproducciones = metrica 'views' total_value. "
        "Engagement: page_post_engagements. "
        "(*) Tasa de engagement marcada como N/D cuando supera el 200%, "
        "lo que indica datos insuficientes de seguidores en Facebook para ese portal. "
        "Porcentajes sobre el total combinado FB+IG de todos los portales activos."
    ))

    return bytes(pdf.output())
