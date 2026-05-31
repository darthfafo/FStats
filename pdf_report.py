"""
Brief PDF - estilo oscuro igual al panel FStats. v2
"""
from fpdf import FPDF
from datetime import datetime
import math

# ── Colores ──────────────────────────────────────────────────────────
BG      = (15,  23,  42)      # fondo oscuro principal
CARD    = (30,  41,  59)      # tarjetas
CARD2   = (51,  65,  85)      # tarjetas mas claras
BLUE    = (24,  119, 242)     # Facebook
PINK    = (193, 53,  132)     # Instagram
GREEN   = (22,  163, 74)      # verde
SLATE   = (100, 116, 139)     # gris medio
LIGHT   = (148, 163, 184)     # gris claro
WHITE   = (255, 255, 255)
ACCENT  = (56,  189, 248)     # celeste claro para highlights

PORTAL_COLOR_MAP = {
    "Chubut Noticias": (80,  80,  80),    # gris oscuro (negro legible en PDF oscuro)
    "Atento Chubut":   (14,  165, 233),   # celeste
    "La Calle Online": (234, 88,  12),    # naranja
    "El Americano":    (34,  197, 94),    # verde
}
FALLBACK_COLORS = [(14,165,233),(234,88,12),(34,197,94),(139,92,246),(20,184,166)]


def _c(nombre, i=0):
    return PORTAL_COLOR_MAP.get(nombre, FALLBACK_COLORS[i % len(FALLBACK_COLORS)])


def _n(v):
    """Numero grande con puntos como separador."""
    try:
        return f"{int(v):,}".replace(",", ".")
    except Exception:
        return "0"


def _s(t):
    """Texto seguro latin-1."""
    return str(t or "").encode("latin-1", errors="replace").decode("latin-1")


def _p(part, total):
    if not total:
        return 0.0
    return round(part / total * 100, 1)


# ── Clase ────────────────────────────────────────────────────────────
class DarkBrief(FPDF):

    def header(self):
        # Fondo oscuro de toda la pagina
        self.set_fill_color(*BG)
        self.rect(0, 0, 210, 297, "F")
        # Barra superior azul oscura con texto
        self.set_fill_color(*CARD)
        self.rect(0, 0, 210, 20, "F")
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 12)
        self.set_y(4)
        self.cell(0, 6, "INFORME DE RENDIMIENTO DIGITAL", align="C",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*LIGHT)
        self.cell(0, 5,
                  _s(f"Ultimo mes  |  {datetime.now().strftime('%d/%m/%Y')}  |  FStats"),
                  align="C")
        self.set_y(24)

    def footer(self):
        self.set_y(-10)
        self.set_font("Helvetica", "I", 6)
        self.set_text_color(*LIGHT)
        self.cell(0, 4,
                  f"FStats  |  Pagina {self.page_no()} de {{nb}}  |  Confidencial",
                  align="C")

    # ── Helpers ───────────────────────────────────────────────────────

    def _big_number(self, number_str, label, sublabel="", y_offset=0):
        """Numero hero con etiqueta."""
        y = self.get_y() + y_offset
        self.set_xy(self.l_margin, y)
        self.set_font("Helvetica", "B", 40)
        self.set_text_color(*WHITE)
        self.cell(0, 16, _s(number_str), align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*ACCENT)
        self.cell(0, 4, _s(label.upper()).replace("?", "|"), align="C", new_x="LMARGIN", new_y="NEXT")
        if sublabel:
            self.set_font("Helvetica", "", 6.5)
            self.set_text_color(*LIGHT)
            self.cell(0, 4, _s(sublabel), align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def _kpi_card(self, x, y, w, h, value, label, sub, accent):
        """Tarjeta individual de KPI."""
        self.set_fill_color(*CARD)
        self.rect(x, y, w, h, "F")
        self.set_fill_color(*accent)
        self.rect(x, y, w, 3, "F")
        # Value
        self.set_xy(x + 3, y + 6)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*WHITE)
        self.cell(w - 6, 8, _s(value))
        # Label
        self.set_xy(x + 3, y + 14)
        self.set_font("Helvetica", "B", 6)
        self.set_text_color(*accent)
        self.cell(w - 6, 4, _s(label.upper()))
        # Sub
        self.set_xy(x + 3, y + 18)
        self.set_font("Helvetica", "", 5.5)
        self.set_text_color(*LIGHT)
        self.cell(w - 6, 4, _s(sub))

    def _kpi_grid(self, items):
        """Grid 2x2 de KPIs."""
        n = len(items)
        cols = 2
        w = (182 - (cols - 1) * 2) / cols
        h = 26
        x0 = self.l_margin
        y0 = self.get_y()
        for i, (val, lbl, sub, color) in enumerate(items):
            col = i % cols
            row = i // cols
            self._kpi_card(x0 + col * (w + 2), y0 + row * (h + 2), w, h,
                           val, lbl, sub, color)
        rows = math.ceil(n / cols)
        self.set_y(y0 + rows * (h + 2) + 3)

    def _section_title(self, text, color=ACCENT):
        """Titulo de seccion con estilo."""
        y = self.get_y()
        self.set_fill_color(*CARD)
        self.rect(self.l_margin, y, 182, 8, "F")
        self.set_fill_color(*color)
        self.rect(self.l_margin, y, 3, 8, "F")
        self.set_xy(self.l_margin + 7, y + 1.5)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*color)
        self.cell(0, 5, _s(text.upper()))
        self.ln(11)

    # ── Torta (donut) con poligonos ───────────────────────────────────
    def _sector_poly(self, xc, yc, r, a_start, a_end, color):
        steps = max(4, int(abs(a_end - a_start) / 3))
        pts = [(xc, yc)]
        for i in range(steps + 1):
            ang = math.radians(a_start + (a_end - a_start) * i / steps)
            pts.append((xc + r * math.cos(ang), yc + r * math.sin(ang)))
        self.set_fill_color(*color)
        self.set_draw_color(*BG)
        self.polygon(pts, style="FD")

    def _donut(self, resumenes, total, xc, yc, r):
        if not total:
            return
        angle = -90.0
        for i, d in enumerate(resumenes):
            pct = d.get("total_imp", 0) / total
            if pct < 0.001:
                continue
            color = _c(d["nombre"], i)
            self._sector_poly(xc, yc, r, angle, angle + pct * 360, color)
            angle += pct * 360
        # Agujero central
        steps = 40
        pts = [(xc + r * 0.52 * math.cos(math.radians(i * 9)),
                yc + r * 0.52 * math.sin(math.radians(i * 9))) for i in range(steps)]
        self.set_fill_color(*BG)
        self.set_draw_color(*BG)
        self.polygon(pts, style="FD")
        # Texto central
        self.set_xy(xc - 16, yc - 5)
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(*WHITE)
        self.cell(32, 5, _n(total), align="C")
        self.set_xy(xc - 16, yc + 1)
        self.set_font("Helvetica", "", 5)
        self.set_text_color(*LIGHT)
        self.cell(32, 3, "VISUALIZACIONES", align="C")

    def _donut_legend(self, resumenes, total, x, y):
        for i, d in enumerate(resumenes):
            color = _c(d["nombre"], i)
            pct   = _p(d.get("total_imp", 0), total)
            nombre = _s(d["nombre"])
            # Cuadrado color
            self.set_fill_color(*color)
            self.rect(x, y + 1.5, 5, 5, "F")
            # Nombre
            self.set_xy(x + 8, y)
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*WHITE)
            self.cell(55, 7, nombre)
            # %
            self.set_xy(x + 63, y)
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(*color)
            self.cell(18, 7, f"{pct}%")
            # valor
            self.set_xy(x + 82, y)
            self.set_font("Helvetica", "", 7.5)
            self.set_text_color(*LIGHT)
            self.cell(40, 7, _n(d.get("total_imp", 0)))
            y += 10

    # ── Barra FB vs IG ────────────────────────────────────────────────
    def _split_bar(self, fb, ig, label_fb="FB", label_ig="IG"):
        total = (fb or 0) + (ig or 0)
        if not total:
            return
        w = 182
        x0, y0 = self.l_margin, self.get_y()
        fb_w = w * fb / total
        ig_w = w * ig / total
        h = 12
        if fb_w > 0:
            self.set_fill_color(*BLUE)
            self.rect(x0, y0, fb_w, h, "F")
        if ig_w > 0:
            self.set_fill_color(*PINK)
            self.rect(x0 + fb_w, y0, ig_w, h, "F")
        self.set_font("Helvetica", "B", 6.5)
        self.set_text_color(*WHITE)
        fb_pct = _p(fb, total)
        ig_pct = _p(ig, total)
        if fb_w > 30:
            self.set_xy(x0 + 2, y0 + 1)
            self.cell(fb_w - 4, 4, f"{label_fb}  {fb_pct}%")
            self.set_xy(x0 + 2, y0 + 5.5)
            self.set_font("Helvetica", "", 5.5)
            self.cell(fb_w - 4, 4, _n(fb))
        if ig_w > 30:
            self.set_xy(x0 + fb_w + 2, y0 + 1)
            self.set_font("Helvetica", "B", 6.5)
            self.cell(ig_w - 4, 4, f"{label_ig}  {ig_pct}%")
            self.set_xy(x0 + fb_w + 2, y0 + 5.5)
            self.set_font("Helvetica", "", 5.5)
            self.cell(ig_w - 4, 4, _n(ig))
        self.ln(h + 4)

    # ── Metricas en fila ──────────────────────────────────────────────
    def _metric_row(self, items, accent):
        """Fila de metricas: (valor, label, sub)"""
        n = len(items)
        w = 182 / n
        x0, y0 = self.l_margin, self.get_y()
        h = 24
        for val, lbl, sub in items:
            self.set_fill_color(*CARD2)
            self.rect(x0, y0, w - 1.5, h, "F")
            self.set_fill_color(*accent)
            self.rect(x0, y0, w - 1.5, 2.5, "F")
            # valor
            self.set_xy(x0 + 2, y0 + 5)
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(*WHITE)
            self.cell(w - 4, 8, _s(val))
            # label
            self.set_xy(x0 + 2, y0 + 14)
            self.set_font("Helvetica", "", 6)
            self.set_text_color(*LIGHT)
            self.cell(w - 4, 4, _s(lbl))
            # sub
            self.set_xy(x0 + 2, y0 + 19)
            self.set_font("Helvetica", "", 5.2)
            self.set_text_color(*LIGHT)
            self.cell(w - 4, 3, _s(sub))
            x0 += w
        self.set_y(y0 + h + 4)

    # ── Tarjeta de portal ─────────────────────────────────────────────
    def _portal_card(self, d, total, i):
        color   = _c(d["nombre"], i)
        nombre  = _s(d["nombre"])
        pct     = _p(d.get("total_imp", 0), total)
        t_imp   = d.get("total_imp", 0)
        fb_imp  = d.get("fb_imp", 0)
        fb_seg  = d.get("fb_seg", 0)
        fb_eng  = d.get("fb_eng", 0)
        ig_imp  = d.get("ig_imp", 0)
        ig_reach = d.get("ig_reach", 0)
        ig_seg  = d.get("ig_seg", 0)
        ig_eng  = d.get("ig_engaged", 0)

        if self.get_y() > 230:
            self.add_page()
            self._section_title("Detalle por portal (continuacion)", ACCENT)

        # Barra encabezado del portal
        y0 = self.get_y()
        self.set_fill_color(*CARD)
        self.rect(self.l_margin, y0, 182, 10, "F")
        self.set_fill_color(*color)
        self.rect(self.l_margin, y0, 5, 10, "F")
        # Nombre
        self.set_xy(self.l_margin + 9, y0 + 1.5)
        self.set_font("Helvetica", "B", 9.5)
        self.set_text_color(*WHITE)
        self.cell(100, 7, nombre.upper())
        # % y total
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*LIGHT)
        self.cell(0, 7, f"{pct}% del total  |  {_n(t_imp)} visualizaciones", align="R")
        self.ln(13)

        # Numero total grande
        self.set_font("Helvetica", "B", 36)
        self.set_text_color(*WHITE)
        self.cell(0, 14, _n(t_imp), new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*LIGHT)
        self.cell(0, 5, "visualizaciones totales (FB alcance unico + IG reproducciones) - ultimo mes",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

        # Barra FB vs IG
        self._split_bar(fb_imp, ig_imp)

        # Facebook
        if fb_imp > 0 or fb_seg > 0:
            self.set_font("Helvetica", "B", 7)
            self.set_text_color(*BLUE)
            self.cell(0, 5, "FACEBOOK", new_x="LMARGIN", new_y="NEXT")
            # tasa engagement
            if fb_seg > 0 and fb_eng > 0:
                tasa_v = fb_eng / fb_seg * 100
                tasa_s = f"{tasa_v:.1f}%" if tasa_v <= 200 else "N/D"
            else:
                tasa_s = "N/D"
            self._metric_row([
                (_n(fb_imp),  "Alcance unico",    "personas distintas"),
                (_n(fb_eng) if fb_eng > 0 else "N/D", "Engagement",  "likes + comentarios"),
                (tasa_s,      "Tasa engagement",  "eng/seguidores x100"),
                (_n(fb_seg),  "Seguidores",       "fans de la pagina"),
            ], BLUE)

        # Instagram
        if ig_imp > 0 or ig_seg > 0:
            self.set_font("Helvetica", "B", 7)
            self.set_text_color(*PINK)
            self.cell(0, 5, "INSTAGRAM", new_x="LMARGIN", new_y="NEXT")
            self._metric_row([
                (_n(ig_imp),   "Reproducciones",  "plays Reels + videos"),
                (_n(ig_reach), "Alcance unico",   "cuentas distintas"),
                (_n(ig_eng),   "Interacciones",   "cuentas que actuaron (31d)"),
                (_n(ig_seg),   "Seguidores",      "seguidores actuales"),
            ], PINK)

        self.ln(4)
        # Separador
        self.set_draw_color(*CARD)
        self.line(self.l_margin, self.get_y(), 210 - self.r_margin, self.get_y())
        self.ln(5)


    # ── Pagina Top 10 posts ───────────────────────────────────────────
    def _top10_page(self, posts, titulo, icono, campo_valor, campo_val_label,
                    campo2, campo2_label, campo3, campo3_label, accent):
        """Pagina de top 10 publicaciones."""
        if not posts:
            return
        self.add_page()
        self._section_title(titulo, accent)

        top10 = sorted(posts, key=lambda x: x.get(campo_valor, 0), reverse=True)[:10]

        for i, p in enumerate(top10, 1):
            portal  = _s(p.get("portal", ""))
            fecha   = _s(p.get("ts") or p.get("fecha", ""))
            texto   = _s(p.get("caption") or p.get("mensaje", ""))
            v1 = p.get(campo_valor, 0)
            v2 = p.get(campo2, 0)
            v3 = p.get(campo3, 0)

            # Tipo icono para IG
            tipo = p.get("tipo", "")
            tipo_icon = "[REEL]" if tipo == "reel" else ("[VID]" if tipo == "video" else "[IMG]")

            # Color del portal
            p_idx = next((j for j, r in enumerate(self._portales_ref)
                          if r.get("nombre") == p.get("portal")), 0)
            color = _c(p.get("portal", ""), p_idx)

            y0 = self.get_y()
            if y0 > 258:
                break

            # Fila
            self.set_fill_color(*CARD)
            self.rect(self.l_margin, y0, 182, 18, "F")
            self.set_fill_color(*color)
            self.rect(self.l_margin, y0, 3, 18, "F")

            # Numero
            self.set_xy(self.l_margin + 5, y0 + 2)
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(*color)
            self.cell(8, 5, f"#{i}")

            # Portal + fecha
            self.set_xy(self.l_margin + 14, y0 + 1.5)
            self.set_font("Helvetica", "B", 7)
            self.set_text_color(*WHITE)
            self.cell(60, 4, f"{portal}  {tipo_icon}  {fecha}")

            # Texto
            self.set_xy(self.l_margin + 14, y0 + 6)
            self.set_font("Helvetica", "", 6.2)
            self.set_text_color(*LIGHT)
            self.cell(100, 4, texto[:72])

            # Metricas a la derecha
            mx = self.l_margin + 120
            for val, lbl, clr in [(v1, campo_val_label, WHITE),
                                   (v2, campo2_label, LIGHT),
                                   (v3, campo3_label, LIGHT)]:
                self.set_xy(mx, y0 + 1.5)
                self.set_font("Helvetica", "B", 8)
                self.set_text_color(*clr)
                self.cell(20, 5, _n(val), align="R")
                self.set_xy(mx, y0 + 7)
                self.set_font("Helvetica", "", 5)
                self.set_text_color(*LIGHT)
                self.cell(20, 3, lbl, align="R")
                mx += 21

            self.set_y(y0 + 20)

        # Participacion por portal en el top10
        self.ln(3)
        self._section_title("Participacion de cada portal en este top 10", accent)
        from collections import Counter
        conteo = Counter(p.get("portal") for p in top10)
        total_p = sum(conteo.values())
        x0 = self.l_margin
        for nombre, cnt in sorted(conteo.items(), key=lambda x: -x[1]):
            pct_p = round(cnt / total_p * 100, 1)
            p_idx = next((j for j, r in enumerate(self._portales_ref)
                          if r.get("nombre") == nombre), 0)
            color = _c(nombre, p_idx)
            self.set_fill_color(*color)
            self.rect(x0, self.get_y() + 1, 4, 4, "F")
            self.set_xy(x0 + 6, self.get_y())
            self.set_font("Helvetica", "B", 7.5)
            self.set_text_color(*WHITE)
            self.cell(60, 6, _s(nombre))
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*color)
            self.cell(20, 6, f"{cnt} posts  ({pct_p}%)")
            self.ln(7)


# ── Funcion publica ───────────────────────────────────────────────────
def generar_brief(resumenes: list, totales: dict,
                  top_ig: list = None, top_fb: list = None) -> bytes:
    total     = totales.get("total_imp", 1) or 1
    total_fb  = totales.get("total_fb", 0)
    total_ig  = totales.get("total_ig", 0)
    total_eng = totales.get("total_eng", 0)
    total_seg = totales.get("total_seg", 0)

    pdf = DarkBrief()
    pdf._portales_ref = resumenes  # referencia para colores en top10
    pdf.alias_nb_pages()
    pdf.set_margins(14, 14, 14)
    pdf.set_auto_page_break(auto=True, margin=14)

    # ════════════════════════════════════════════
    # PAGINA 1
    # ════════════════════════════════════════════
    pdf.add_page()

    # Hero number
    pdf._big_number(
        _n(total),
        "Total visualizaciones | Ultimo mes",
        "Alcance unico Facebook + Reproducciones Instagram"
    )

    # KPI grid 2x2
    pdf._kpi_grid([
        (_n(total_fb),  "Alcance Facebook",    f"{_p(total_fb, total)}% del total",  BLUE),
        (_n(total_ig),  "Visualiz. Instagram", f"{_p(total_ig, total)}% del total",  PINK),
        (_n(total_eng), "Engagement FB total", "likes + comentarios + compartidos",   GREEN),
        (_n(total_seg), "Seguidores totales",  f"{len(resumenes)} portal(es) activo(s)", CARD2),
    ])

    # Seccion donut + leyenda
    pdf._section_title("Participacion de cada portal en el impacto total", ACCENT)

    y_g  = pdf.get_y()
    radio = 32
    xc   = pdf.l_margin + 40
    yc   = y_g + radio + 4
    pdf._donut(resumenes, total, xc, yc, radio)
    pdf._donut_legend(resumenes, total, pdf.l_margin + 86, y_g + 8)
    pdf.set_y(yc + radio + 8)

    # Conceptos en 2 columnas reales (izquierda primero, luego derecha)
    pdf._section_title("Como se construyen estas estadisticas", ACCENT)

    col_w = 88
    xi = pdf.l_margin
    xd = pdf.l_margin + col_w + 6
    y_start = pdf.get_y()

    def _write_concept(x, y, color, title, body, width):
        """Escribe un bloque concepto en la posicion dada y retorna Y final."""
        pdf.set_xy(x, y)
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_text_color(*color)
        pdf.cell(width, 5, _s(title))
        pdf.set_xy(x, y + 5)
        pdf.set_font("Helvetica", "", 6.2)
        pdf.set_text_color(*LIGHT)
        pdf.multi_cell(width, 3.5, _s(body))
        return pdf.get_y() + 2

    # Columna izquierda (dos conceptos apilados)
    y_l = y_start
    y_l = _write_concept(xi, y_l, BLUE, "FACEBOOK - ALCANCE UNICO",
        "Cuenta las personas DISTINTAS que vieron al menos una publicacion "
        "en el ultimo mes. Si alguien vio 10 posts, cuenta como 1. "
        "Es la audiencia real impactada.", col_w)
    y_l = _write_concept(xi, y_l, GREEN, "ENGAGEMENT - INTERACCION ACTIVA",
        "Mide cuando el publico hace algo: like, comentario o compartido. "
        "Tasa = (L+C+C) / Seguidores x 100. "
        "Una tasa del 1-3% es excelente en medios digitales.", col_w)

    # Columna derecha (dos conceptos apilados, misma Y de inicio)
    y_r = y_start
    y_r = _write_concept(xd, y_r, PINK, "INSTAGRAM - REPRODUCCIONES TOTALES",
        "Suma todas las veces que se vio cualquier contenido (Reels, videos, fotos). "
        "Una persona puede sumar multiples reproducciones. "
        "Refleja el volumen total de consumo de contenido.", col_w)
    y_r = _write_concept(xd, y_r, ACCENT, "ALCANCE ORGANICO - SIN PUBLICIDAD",
        "Todo el impacto de este informe es ORGANICO: sin inversion publicitaria. "
        "Representa la audiencia fiel que consume el contenido de forma voluntaria.", col_w)

    pdf.set_y(max(y_l, y_r) + 3)

    # Nota metodologica al pie de pag 1
    pdf.set_font("Helvetica", "I", 5.5)
    pdf.set_text_color(*SLATE)
    pdf.multi_cell(0, 3.2, _s(
        "Fuente: Meta Graph API v25.0. Datos actualizados cada hora. "
        "FB alcance = page_impressions_unique. IG reproducciones = views (total_value). "
        "Engagement = page_post_engagements. Tasa N/D: datos insuficientes para ese portal."
    ))

    # ════════════════════════════════════════════
    # PAGINA 2+: PORTALES
    # ════════════════════════════════════════════
    pdf.add_page()
    pdf._section_title("Detalle por portal - metricas individuales", ACCENT)

    for i, d in enumerate(resumenes):
        pdf._portal_card(d, total, i)

    # ── Top 10 Instagram ─────────────────────────────────────────────
    if top_ig:
        pdf._top10_page(
            top_ig,
            titulo="Top 10 publicaciones Instagram — ultimo mes",
            icono="IG",
            campo_valor="likes",      campo_val_label="Likes",
            campo2="comments",        campo2_label="Comentarios",
            campo3="likes",           campo3_label="",
            accent=PINK,
        )

    # ── Top 10 Facebook ──────────────────────────────────────────────
    if top_fb:
        fb_con_datos = [p for p in top_fb if p.get("engagement", 0) > 0]
        if fb_con_datos:
            pdf._top10_page(
                fb_con_datos,
                titulo="Top 10 publicaciones Facebook — ultimo mes",
                icono="FB",
                campo_valor="engagement",  campo_val_label="Engagement",
                campo2="likes",            campo2_label="Likes",
                campo3="compartidos",      campo3_label="Compartidos",
                accent=BLUE,
            )

    return bytes(pdf.output())
