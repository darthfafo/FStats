"""
Generador de brief PDF profesional para el Panel de Estadísticas.
"""
from fpdf import FPDF
from datetime import datetime
import io


# ── Paleta ───────────────────────────────────────────────────────────
DARK       = (15,  23,  42)
DARK2      = (30,  41,  59)
BLUE_FB    = (24,  119, 242)
PINK_IG    = (193, 53,  132)
GREEN      = (22,  163, 74)
SLATE      = (100, 116, 139)
LIGHT      = (241, 245, 249)
WHITE      = (255, 255, 255)
ACCENT     = (56,  189, 248)


def _fmt(n):
    """Formatea un número grande con separador de miles."""
    try:
        return f"{int(n):,}".replace(",", ".")
    except Exception:
        return str(n)


def _safe(text):
    """Elimina caracteres fuera del rango latin-1 para evitar errores en fpdf."""
    return (text or "").encode("latin-1", errors="replace").decode("latin-1")


class Brief(FPDF):
    def __init__(self, portales_activos):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.portales_activos = portales_activos
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(14, 14, 14)

    # ── Cabecera de página ────────────────────────────────────────────
    def header(self):
        self.set_fill_color(*DARK)
        self.rect(0, 0, 210, 22, "F")
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 13)
        self.set_y(5)
        self.cell(0, 7, "INFORME DE RENDIMIENTO DIGITAL", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 5, f"Ultimos 30 dias  |  Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}",
                  align="C")
        self.ln(14)

    # ── Pie de página ─────────────────────────────────────────────────
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*SLATE)
        self.cell(0, 5,
                  f"Panel FStats  |  Pagina {self.page_no()} de {{nb}}",
                  align="C")

    # ── Helpers ───────────────────────────────────────────────────────
    def _titulo_seccion(self, texto, color=DARK):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*color)
        self.set_fill_color(*LIGHT)
        self.cell(0, 7, f"  {_safe(texto)}", fill=True,
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def _kpi_row(self, items, ancho=182, alto=18):
        """Dibuja una fila de KPI boxes. items = [(label, valor, color_accent)]"""
        w = ancho / len(items)
        x0 = self.get_x()
        y0 = self.get_y()
        for label, valor, color in items:
            # Fondo
            self.set_fill_color(*LIGHT)
            self.set_draw_color(*LIGHT)
            self.rect(x0, y0, w - 2, alto, "F")
            # Barra de color superior
            self.set_fill_color(*color)
            self.rect(x0, y0, w - 2, 2, "F")
            # Label
            self.set_xy(x0 + 2, y0 + 4)
            self.set_font("Helvetica", "", 6.5)
            self.set_text_color(*SLATE)
            self.cell(w - 4, 4, label.upper(), new_x="RIGHT", new_y="TOP")
            # Valor
            self.set_xy(x0 + 2, y0 + 8)
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*DARK)
            self.cell(w - 4, 7, valor, new_x="RIGHT", new_y="TOP")
            x0 += w
        self.set_xy(self.l_margin, y0 + alto + 3)

    def _portal_card(self, d):
        """Dibuja la tarjeta de un portal."""
        nombre = d["nombre"]
        icono  = {"Chubut Noticias": "[CN]", "Atento Chubut": "[AC]",
                  "La Calle Online": "[LCO]", "El Americano": "[EA]",
                  "VISTE ESTO?": "[VE]", "Boca en Linea": "[BEL]"}.get(nombre, "[ ]")

        # Encabezado del portal
        self.set_fill_color(*DARK2)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 7, f"  {icono}  {_safe(nombre).upper()}",
                  fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

        # Total visualizaciones (grande)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*DARK)
        total = _fmt(d.get("total_imp", 0))
        self.cell(0, 10, total, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*SLATE)
        self.cell(0, 4, "total visualizaciones (FB alcance unico + IG reproducciones)",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

        # KPIs Facebook
        fb_imp   = d.get("fb_imp", 0)
        fb_seg   = d.get("fb_seg", 0)
        fb_eng   = d.get("fb_eng", 0)
        ig_imp   = d.get("ig_imp", 0)
        ig_reach = d.get("ig_reach", 0)
        ig_seg   = d.get("ig_seg", 0)

        if fb_imp > 0 or fb_seg > 0:
            self.set_font("Helvetica", "B", 7.5)
            self.set_text_color(*BLUE_FB)
            self.cell(0, 5, "FACEBOOK", new_x="LMARGIN", new_y="NEXT")
            self._kpi_row([
                ("Alcance unico",  _fmt(fb_imp),  BLUE_FB),
                ("Engagement",     _fmt(fb_eng),  BLUE_FB),
                ("Seguidores",     _fmt(fb_seg),  BLUE_FB),
            ], alto=16)

        if ig_imp > 0 or ig_seg > 0:
            self.set_font("Helvetica", "B", 7.5)
            self.set_text_color(*PINK_IG)
            self.cell(0, 5, "INSTAGRAM", new_x="LMARGIN", new_y="NEXT")
            self._kpi_row([
                ("Visualizaciones", _fmt(ig_imp),   PINK_IG),
                ("Alcance unico",   _fmt(ig_reach), PINK_IG),
                ("Seguidores",      _fmt(ig_seg),   PINK_IG),
            ], alto=16)

        self.ln(4)
        # Separador
        self.set_draw_color(*LIGHT)
        self.line(self.l_margin, self.get_y(), 210 - self.r_margin, self.get_y())
        self.ln(5)


# ── Función principal ─────────────────────────────────────────────────
def generar_brief(resumenes, totales: dict) -> bytes:
    """
    Genera el PDF y devuelve los bytes listos para descargar.

    totales: dict con keys total_imp, total_seg, total_eng, total_fb, total_ig
    """
    pdf = Brief(portales_activos=resumenes)
    pdf.alias_nb_pages()
    pdf.add_page()

    # ── 1. Resumen ejecutivo ─────────────────────────────────────────
    pdf._titulo_seccion("RESUMEN EJECUTIVO — TODOS LOS PORTALES", DARK)

    # Número hero
    pdf.set_font("Helvetica", "B", 32)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 14, _fmt(totales["total_imp"]), align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 5, "TOTAL VISUALIZACIONES | ULTIMOS 30 DIAS", align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # KPI row global
    pdf._kpi_row([
        ("Facebook alcance", _fmt(totales["total_fb"]),  BLUE_FB),
        ("Instagram reprod.", _fmt(totales["total_ig"]),  PINK_IG),
        ("Engagement total",  _fmt(totales["total_eng"]), GREEN),
        ("Seguidores totales",_fmt(totales["total_seg"]), DARK2),
    ], alto=20)

    # Portales activos
    n = len(resumenes)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 5, _safe(f"{n} portal(es) activo(s): {', '.join(d['nombre'] for d in resumenes)}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # ── 2. Detalle por portal ────────────────────────────────────────
    pdf._titulo_seccion("DETALLE POR PORTAL", DARK)

    for d in resumenes:
        # Si no cabe la tarjeta completa (~60mm), nueva página
        if pdf.get_y() > 230:
            pdf.add_page()
            pdf._titulo_seccion("DETALLE POR PORTAL (continuacion)", DARK)
        pdf._portal_card(d)

    # ── 3. Notas ─────────────────────────────────────────────────────
    if pdf.get_y() > 250:
        pdf.add_page()
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(*SLATE)
    pdf.multi_cell(0, 4,
        "Fuente: Meta Graph API v25.0.  Facebook = alcance unico de pagina (personas distintas que "
        "vieron el contenido).  Instagram = reproducciones totales (incluye repeticiones de Reels, "
        "videos e imagenes).  Engagement = interacciones totales en publicaciones (likes + comentarios "
        "+ compartidos) segun Meta Insights.  Datos actualizados cada hora."
    )

    # Devolver bytes
    return bytes(pdf.output())
