"""
Brief PDF - tema claro profesional. FStats.
"""
from fpdf import FPDF
from datetime import datetime
import math

WHITE      = (255, 255, 255)
HERO_BG    = (15,  23,  42)
CARD_BG    = (241, 245, 249)
TEXT_DARK  = (15,  23,  42)
TEXT_MID   = (25,  25,  25)
TEXT_LIGHT = (45,  45,  45)
BLUE_FB    = (24,  119, 242)
PINK_IG    = (193, 53,  132)
GREEN      = (22,  163, 74)
DIVIDER    = (203, 213, 225)

PORTAL_COLOR_MAP = {
    "Chubut Noticias": (30,  30,  30),
    "Atento Chubut":   (14,  165, 233),
    "La Calle Online": (234, 88,  12),
    "El Americano":    (22,  163, 74),
}
FALLBACK_COLORS = [(14,165,233),(234,88,12),(22,163,74),(139,92,246)]


def _c(nombre, i=0):
    return PORTAL_COLOR_MAP.get(nombre, FALLBACK_COLORS[i % len(FALLBACK_COLORS)])


def _n(v):
    try:
        return f"{int(v):,}".replace(",", ".")
    except Exception:
        return "0"


def _s(t):
    t = str(t or "")
    replacements = [
        ("—", "|"), ("–", "-"), ("'", "'"),
        ("é", "e"), ("ó", "o"), ("ñ", "n"),
        ("á", "a"), ("í", "i"), ("ú", "u"),
        ("É", "E"), ("Á", "A"), ("Ó", "O"),
        ("Í", "I"), ("Ú", "U"), ("Ñ", "N"),
        ("ü", "u"), ("ö", "o"),
    ]
    for src, dst in replacements:
        t = t.replace(src, dst)
    return t.encode("latin-1", errors="replace").decode("latin-1")


def _p(part, total):
    if not total:
        return 0.0
    return round(part / total * 100, 1)


class Brief(FPDF):

    def header(self):
        self.set_fill_color(*WHITE)
        self.rect(0, 0, 210, 297, "F")
        self.set_fill_color(*HERO_BG)
        self.rect(0, 0, 210, 10, "F")
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(*WHITE)
        self.set_y(2.8)
        self.cell(0, 4.5, "INFORME DE RENDIMIENTO DIGITAL  |  FStats", align="C",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_y(14)

    def footer(self):
        self.set_y(-10)
        self.set_draw_color(*DIVIDER)
        self.line(14, self.get_y(), 196, self.get_y())
        self.set_font("Helvetica", "I", 6.5)
        self.set_text_color(*TEXT_LIGHT)
        self.cell(0, 6,
                  f"FStats | Pagina {self.page_no()} de {{nb}} | {datetime.now().strftime('%d/%m/%Y')} | Confidencial",
                  align="C")

    def _section(self, text, color=None):
        color = color or HERO_BG
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*color)
        self.cell(0, 6, _s(text.upper()), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*color)
        self.line(self.l_margin, self.get_y(), 196, self.get_y())
        self.ln(3)

    def _kpi_box(self, x, y, w, h, val, lbl, sub, color):
        self.set_fill_color(*CARD_BG)
        self.rect(x, y, w, h, "F")
        self.set_fill_color(*color)
        self.rect(x, y, w, 2.5, "F")
        self.set_xy(x+2, y+4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*TEXT_DARK)
        self.cell(w-4, 6.5, _s(val))
        self.set_xy(x+2, y+12)
        self.set_font("Helvetica", "B", 6)
        self.set_text_color(*color)
        self.cell(w-4, 3.5, _s(lbl.upper()))
        self.set_xy(x+2, y+16)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*TEXT_LIGHT)
        self.cell(w-4, 4, _s(sub))

    def _kpi_row(self, items):
        y0 = self.get_y()
        n = len(items)
        w = 182 / n
        h = 23
        self.set_auto_page_break(False)
        for i, (val, lbl, sub, color) in enumerate(items):
            self._kpi_box(self.l_margin + i*(w+0.5), y0, w-0.5, h, val, lbl, sub, color)
        self.set_auto_page_break(True, margin=14)
        self.set_y(y0 + h + 3)

    def _hero_box(self, numero, subtitulo):
        y0 = self.get_y()
        h  = 26
        self.set_auto_page_break(False)
        self.set_fill_color(*HERO_BG)
        self.rect(self.l_margin, y0, 182, h, "F")
        self.set_xy(self.l_margin, y0+3)
        self.set_font("Helvetica", "B", 26)
        self.set_text_color(*WHITE)
        self.cell(182, 11, _s(numero), align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_xy(self.l_margin, y0+15)
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(148, 163, 184)
        self.cell(182, 5, _s(subtitulo), align="C")
        self.set_auto_page_break(True, margin=14)
        self.set_y(y0 + h + 4)

    def _sector_poly(self, xc, yc, r, a0, a1, color):
        steps = max(3, int(abs(a1-a0)/4))
        pts = [(xc, yc)]
        for i in range(steps+1):
            a = math.radians(a0 + (a1-a0)*i/steps)
            pts.append((xc + r*math.cos(a), yc + r*math.sin(a)))
        self.set_fill_color(*color)
        self.set_draw_color(*WHITE)
        self.polygon(pts, style="FD")

    def _donut(self, resumenes, total, xc, yc, r):
        if not total:
            return
        angle = -90.0
        for i, d in enumerate(resumenes):
            pct = d.get("total_imp", 0) / total
            if pct < 0.001:
                continue
            self._sector_poly(xc, yc, r, angle, angle + pct*360, _c(d["nombre"], i))
            angle += pct*360
        steps = 40
        pts = [(xc + r*0.55*math.cos(math.radians(i*9)),
                yc + r*0.55*math.sin(math.radians(i*9))) for i in range(steps)]
        self.set_fill_color(*WHITE)
        self.set_draw_color(*WHITE)
        self.polygon(pts, style="FD")
        self.set_xy(xc-18, yc-5)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*TEXT_DARK)
        self.cell(36, 5, _n(total), align="C")
        self.set_xy(xc-18, yc+1)
        self.set_font("Helvetica", "", 5)
        self.set_text_color(*TEXT_LIGHT)
        self.cell(36, 3, "VISUALIZACIONES", align="C")

    def _donut_legend(self, resumenes, total, x, y):
        for i, d in enumerate(resumenes):
            color = _c(d["nombre"], i)
            pct = _p(d.get("total_imp", 0), total)
            self.set_fill_color(*color)
            self.rect(x, y+1.5, 4.5, 4.5, "F")
            self.set_xy(x+7, y)
            self.set_font("Helvetica", "B", 9.5)
            self.set_text_color(*TEXT_DARK)
            self.cell(50, 8, _s(d["nombre"]))
            self.set_xy(x+57, y)
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*color)
            self.cell(14, 8, f"{pct}%")
            self.set_xy(x+72, y)
            self.set_font("Helvetica", "", 8.5)
            self.set_text_color(*TEXT_MID)
            self.cell(40, 8, _n(d.get("total_imp", 0)) + " viz.")
            y += 11

    def _line_chart(self, data_dict, x, y, w, h, color, title=""):
        if not data_dict or len(data_dict) < 2:
            self.set_fill_color(*CARD_BG)
            self.rect(x, y, w, h, "F")
            self.set_xy(x, y + h/2 - 3)
            self.set_font("Helvetica", "I", 6)
            self.set_text_color(*TEXT_LIGHT)
            self.cell(w, 5, "Sin datos", align="C")
            return
        vals = [v for _, v in sorted(data_dict.items())]
        max_v = max(vals) or 1
        n = len(vals)
        self.set_fill_color(*CARD_BG)
        self.rect(x, y, w, h, "F")
        if title:
            self.set_xy(x+2, y+2)
            self.set_font("Helvetica", "B", 5.5)
            self.set_text_color(*TEXT_MID)
            self.cell(w-4, 3.5, _s(title))
        pad = 7
        ch = h - pad - 3
        pts = [(x, y+h-3)]
        for i, v in enumerate(vals):
            px = x + (i/(n-1))*w
            py = y + pad + ch - (v/max_v)*ch
            pts.append((px, py))
        pts.append((x+w, y+h-3))
        r2, g2, b2 = color
        self.set_fill_color(min(255,r2+130), min(255,g2+130), min(255,b2+130))
        self.polygon(pts, style="F")
        self.set_draw_color(*color)
        line_pts = [(x + (i/(n-1))*w, y + pad + ch - (v/max_v)*ch) for i, v in enumerate(vals)]
        for i in range(len(line_pts)-1):
            self.line(line_pts[i][0], line_pts[i][1], line_pts[i+1][0], line_pts[i+1][1])
        self.set_xy(x+1, y+pad-1)
        self.set_font("Helvetica", "", 4.5)
        self.set_text_color(*TEXT_LIGHT)
        self.cell(w-2, 3, _n(max_v), align="R")

    def _bar_chart(self, data_dict, x, y, w, h, color, title=""):
        if not data_dict:
            return
        vals = [(k, v) for k, v in sorted(data_dict.items())]
        max_v = max(v for _, v in vals) or 1
        n = len(vals)
        self.set_fill_color(*CARD_BG)
        self.rect(x, y, w, h, "F")
        if title:
            self.set_xy(x+2, y+2)
            self.set_font("Helvetica", "B", 5.5)
            self.set_text_color(*TEXT_MID)
            self.cell(w-4, 3.5, _s(title))
        pad = 7
        ch = h - pad - 3
        bw = max(1, w/n*0.7)
        gap = w/n*0.3
        for i, (k, v) in enumerate(vals):
            bx = x + i*(w/n) + gap/2
            bh = (v/max_v)*ch
            by = y + pad + ch - bh
            self.set_fill_color(*color)
            self.rect(bx, by, bw, bh, "F")

    def _split_bar(self, fb, ig):
        total = (fb or 0) + (ig or 0)
        if not total:
            return
        w = 182
        x0, y0 = self.l_margin, self.get_y()
        h = 11
        fb_w = w * fb / total
        ig_w = w * ig / total
        self.set_auto_page_break(False)
        if fb_w > 0:
            self.set_fill_color(*BLUE_FB)
            self.rect(x0, y0, fb_w, h, "F")
        if ig_w > 0:
            self.set_fill_color(*PINK_IG)
            self.rect(x0+fb_w, y0, ig_w, h, "F")
        self.set_font("Helvetica", "B", 6.5)
        self.set_text_color(*WHITE)
        fb_p = _p(fb, total)
        ig_p = _p(ig, total)
        if fb_w > 35:
            self.set_xy(x0+2, y0+1)
            self.cell(fb_w-4, 4, f"FB  {fb_p}%")
            self.set_xy(x0+2, y0+5.5)
            self.set_font("Helvetica", "", 5.5)
            self.cell(fb_w-4, 3.5, _n(fb))
        if ig_w > 35:
            self.set_xy(x0+fb_w+2, y0+1)
            self.set_font("Helvetica", "B", 6.5)
            self.cell(ig_w-4, 4, f"IG  {ig_p}%")
            self.set_xy(x0+fb_w+2, y0+5.5)
            self.set_font("Helvetica", "", 5.5)
            self.cell(ig_w-4, 3.5, _n(ig))
        self.set_auto_page_break(True, margin=14)
        self.ln(h + 3)

    def _metric_row(self, items, accent):
        n = len(items)
        w = 182 / n
        h = 20
        if self.get_y() + h + 5 > self.h - self.b_margin:
            self.add_page()
        x0, y0 = self.l_margin, self.get_y()
        self.set_auto_page_break(False)
        for val, lbl, sub in items:
            self.set_fill_color(*CARD_BG)
            self.rect(x0, y0, w-1.5, h, "F")
            self.set_fill_color(*accent)
            self.rect(x0, y0, w-1.5, 2.5, "F")
            self.set_xy(x0+2, y0+4)
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(*TEXT_DARK)
            self.cell(w-4, 6, _s(val))
            self.set_xy(x0+2, y0+11)
            self.set_font("Helvetica", "", 7.5)
            self.set_text_color(*TEXT_MID)
            self.cell(w-4, 4.5, _s(lbl))
            self.set_xy(x0+2, y0+15.5)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*TEXT_LIGHT)
            self.cell(w-4, 4, _s(sub))
            x0 += w
        self.set_auto_page_break(True, margin=14)
        self.set_y(y0 + h + 2)

    def _chart_note(self, text):
        """Nota explicativa debajo de un grafico."""
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*TEXT_DARK)
        self.multi_cell(0, 5, _s(text))
        self.ln(2)

    def _metric_note(self, text):
        """Nota explicativa debajo de una fila de metricas."""
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*TEXT_DARK)
        self.multi_cell(0, 5, _s(text))
        self.ln(3)

    def _portal_page(self, d, total, i):
        self.add_page()
        color    = _c(d["nombre"], i)
        nombre   = _s(d["nombre"])
        pct      = _p(d.get("total_imp", 0), total)
        fb_imp   = d.get("fb_imp", 0)
        fb_seg   = d.get("fb_seg", 0)
        fb_eng   = d.get("fb_eng", 0)
        ig_imp   = d.get("ig_imp", 0)
        ig_reach = d.get("ig_reach", 0)
        ig_seg   = d.get("ig_seg", 0)
        ig_eng   = d.get("ig_engaged", 0)
        fb_daily = d.get("fb_daily", {})
        ig_daily = d.get("ig_daily", {})
        ig_seg_d = d.get("ig_daily_seg", {})
        t_imp    = d.get("total_imp", 0)

        # Barra color arriba
        self.set_fill_color(*color)
        self.rect(self.l_margin, self.get_y(), 182, 2, "F")
        self.ln(4)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*color)
        self.cell(0, 8, nombre.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*TEXT_MID)
        self.cell(0, 5, _s(f"{pct}% del total  |  {_n(t_imp)} visualizaciones  |  ultimo mes"),
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

        self._hero_box(_n(t_imp),
                       "TOTAL VISUALIZACIONES  |  FB alcance unico + IG reproducciones")
        self._split_bar(fb_imp, ig_imp)

        # Facebook
        if fb_imp > 0 or fb_seg > 0:
            self._section("Facebook", BLUE_FB)
            tasa_s = "N/D"
            if fb_seg > 0 and fb_eng > 0:
                tv = fb_eng / fb_seg * 100
                tasa_s = f"{tv:.1f}%" if tv <= 200 else "N/D"
            self._metric_row([
                (_n(fb_imp), "Alcance unico", "personas distintas"),
                (_n(fb_eng) if fb_eng > 0 else "N/D", "Engagement", "likes + comentarios"),
                (tasa_s, "Tasa engagement", "engagement / seguidores x100"),
                (_n(fb_seg), "Seguidores", "fans de la pagina"),
            ], BLUE_FB)
            self._metric_note(
                "Alcance unico: personas distintas que vieron al menos 1 publicacion (sin repeticion). "
                "Engagement: suma de likes + comentarios + compartidos. "
                "Tasa de engagement: que tan activa es la audiencia en proporcion a su tamano (1-3% = excelente)."
            )
            if fb_daily:
                yc_fb = self.get_y()
                self._line_chart(fb_daily, self.l_margin, yc_fb, 182, 22,
                                 BLUE_FB, "Alcance diario Facebook")
                self.set_y(yc_fb + 22)
                self._chart_note(
                    "Personas distintas alcanzadas cada dia. Los picos coinciden con dias "
                    "en que se publicaron contenidos de mayor difusion organica."
                )
                self.ln(2)

        # Instagram
        if ig_imp > 0 or ig_seg > 0:
            self._section("Instagram", PINK_IG)
            self._metric_row([
                (_n(ig_imp), "Reproducciones", "plays Reels + videos + fotos"),
                (_n(ig_reach), "Alcance unico", "cuentas distintas"),
                (_n(ig_eng), "Interacciones", "cuentas que actuaron"),
                (_n(ig_seg), "Seguidores", "seguidores actuales"),
            ], PINK_IG)
            self._metric_note(
                "Reproducciones: total de vistas de todos los contenidos (incluye repeticiones de la misma persona). "
                "Alcance unico: cuentas distintas que vieron algo. "
                "Interacciones: perfiles que dieron like, comentaron o guardaron algun contenido del mes."
            )
            # Alcance diario IG (anchura completa)
            if ig_daily:
                yc_ig = self.get_y()
                self._line_chart(ig_daily, self.l_margin, yc_ig, 182, 22,
                                 PINK_IG, "Alcance diario Instagram")
                self.set_y(yc_ig + 22)
                self._chart_note(
                    "Visualizaciones totales de todos los contenidos publicados por dia. "
                    "Los picos suelen coincidir con la publicacion de Reels o videos virales."
                )
                self.ln(2)
            # Nuevos seguidores por dia (anchura completa, debajo del alcance)
            if ig_seg_d:
                yc_seg = self.get_y()
                self._bar_chart(ig_seg_d, self.l_margin, yc_seg, 182, 20,
                                (14,165,233), "Nuevos seguidores por dia")
                self.set_y(yc_seg + 20)
                self._chart_note(
                    "Seguidores nuevos ganados organicamente cada dia. "
                    "Refleja el crecimiento de la audiencia: un pico indica "
                    "que una publicacion atrajo nuevos seguidores ese dia."
                )
                self.ln(2)

    def _global_page(self, resumenes, totales):
        self.add_page()
        total    = totales.get("total_imp", 1) or 1
        total_fb = totales.get("total_fb", 0)
        total_ig = totales.get("total_ig", 0)
        total_eng = totales.get("total_eng", 0)
        total_seg = totales.get("total_seg", 0)

        self._section("Estadisticas globales — comparativa de portales", HERO_BG)
        self._kpi_row([
            (_n(total),     "Total visualizaciones", "FB + IG",  HERO_BG),
            (_n(total_fb),  "Alcance Facebook",      f"{_p(total_fb,total)}% del total", BLUE_FB),
            (_n(total_ig),  "Reproducciones IG",     f"{_p(total_ig,total)}% del total", PINK_IG),
            (_n(total_seg), "Seguidores totales",    "suma de todos los portales", GREEN),
        ])
        self.ln(2)

        self._section("Participacion por portal", HERO_BG)
        activos = sorted([d for d in resumenes if d.get("total_imp",0) > 0],
                         key=lambda x: -x.get("total_imp",0))
        for i, d in enumerate(activos):
            color = _c(d["nombre"], i)
            pct = _p(d.get("total_imp",0), total)
            bar_w = 130 * pct / 100
            y0 = self.get_y()
            self.set_xy(self.l_margin, y0)
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*TEXT_DARK)
            self.cell(52, 8, _s(d["nombre"]))
            self.set_fill_color(*color)
            self.rect(self.l_margin+52, y0+2, bar_w, 4.5, "F")
            self.set_xy(self.l_margin+52+bar_w+2, y0)
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*color)
            self.cell(20, 8, f"{pct}%")
            self.set_xy(self.l_margin+52+bar_w+22, y0)
            self.set_font("Helvetica", "", 7.5)
            self.set_text_color(*TEXT_MID)
            self.cell(40, 8, _n(d.get("total_imp",0)) + " viz.")
            self.ln(9)

        self.ln(3)
        self._section("Tendencia de alcance diario — Instagram", HERO_BG)
        chart_y = self.get_y()
        activos_ig = [d for d in resumenes if d.get("ig_daily")]
        if activos_ig:
            cw = (182 - 4) / 2
            for i, d in enumerate(activos_ig[:4]):
                col_i = i % 2
                row_i = i // 2
                cx = self.l_margin + col_i*(cw+4)
                cy = chart_y + row_i*30
                self._line_chart(d.get("ig_daily",{}), cx, cy, cw, 26,
                                 _c(d["nombre"],i), _s(d["nombre"]) + " - IG")
            rows = math.ceil(len(activos_ig[:4])/2)
            self.set_y(chart_y + rows*30 + 2)

    def _top10_ig_page(self, posts, resumenes):
        if not posts:
            return
        self.add_page()
        self._section("Top 10 publicaciones Instagram — ultimo mes", PINK_IG)
        top10 = sorted(posts, key=lambda x: x.get("likes",0), reverse=True)[:10]
        h_row = 14
        h_row = 18   # un poco mas alto para caber todo
        self.set_auto_page_break(False)
        for i, p in enumerate(top10, 1):
            portal    = _s(p.get("portal",""))
            fecha     = _s(p.get("ts",""))
            texto     = _s(p.get("caption",""))
            likes     = p.get("likes", 0)
            comms     = p.get("comments", 0)
            permalink = p.get("permalink", "")
            tipo      = p.get("tipo","")
            tipo_s    = "REEL" if tipo=="reel" else ("VID" if tipo=="video" else "IMG")
            p_idx     = next((j for j,r in enumerate(resumenes)
                              if r.get("nombre")==p.get("portal")), 0)
            color     = _c(p.get("portal",""), p_idx)
            y0        = self.get_y()
            if y0 + h_row > self.h - 42:
                break
            self.set_fill_color(*CARD_BG)
            self.rect(self.l_margin, y0, 182, h_row, "F")
            self.set_fill_color(*color)
            self.rect(self.l_margin, y0, 3, h_row, "F")
            # Numero ranking
            self.set_xy(self.l_margin+5, y0+1)
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*color)
            self.cell(10, 6, f"#{i}")
            # Portal + tipo + fecha
            self.set_xy(self.l_margin+16, y0+1)
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*TEXT_DARK)
            self.cell(88, 5, f"{portal}  [{tipo_s}]  {fecha}"[:55])
            # Link "Ver post" clickeable
            if permalink:
                self.set_xy(self.l_margin+16, y0+7)
                self.set_font("Helvetica", "U", 7.5)
                self.set_text_color(24, 119, 242)
                self.cell(30, 5, "Ver publicacion", link=permalink)
            # Caption
            self.set_xy(self.l_margin+16+30+(2 if permalink else 0), y0+7)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*TEXT_MID)
            self.cell(55, 5, texto[:50])
            # Metricas: Likes y Comentarios
            mx = self.l_margin + 118
            for val, lbl in [(likes,"Likes"),(comms,"Coment.")]:
                self.set_xy(mx, y0+1)
                self.set_font("Helvetica", "B", 9.5)
                self.set_text_color(*TEXT_DARK)
                self.cell(32, 6, _n(val), align="R")
                self.set_xy(mx, y0+8)
                self.set_font("Helvetica", "", 6.5)
                self.set_text_color(*TEXT_LIGHT)
                self.cell(32, 4, lbl, align="R")
                mx += 32
            self.set_y(y0 + h_row + 2)
        self.set_auto_page_break(True, margin=14)
        self.ln(4)

        # ── Explicacion del impacto ──────────────────────────────────
        self._section("Por que estas publicaciones generan mas impacto", PINK_IG)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*TEXT_DARK)
        self.multi_cell(0, 5, _s(
            "Las publicaciones con mas likes e interacciones son distribuidas por el algoritmo "
            "de Instagram a usuarios que no siguen la cuenta, amplificando su alcance organico. "
            "Un Reel con 200.000 likes puede alcanzar 5 a 10 veces mas personas que el numero "
            "de seguidores del portal. Cada comentario indica que el contenido genero una "
            "reaccion activa, lo que Instagram interpreta como senal de calidad."
        ))
        self.ln(4)

        # ── Grafico de participacion visual ─────────────────────────
        self._section("Participacion de cada portal en el top 10", PINK_IG)
        from collections import Counter
        conteo = Counter(p.get("portal") for p in top10)
        total_p = sum(conteo.values())
        portal_sorted = sorted(conteo.items(), key=lambda x: -x[1])

        for nombre, cnt in portal_sorted:
            p_idx = next((j for j,r in enumerate(resumenes)
                          if r.get("nombre")==nombre), 0)
            color = _c(nombre, p_idx)
            pct_p = round(cnt/total_p*100, 1)
            bar_w = 110 * pct_p / 100
            y0 = self.get_y()
            # Nombre del portal
            self.set_xy(self.l_margin, y0)
            self.set_font("Helvetica", "B", 9.5)
            self.set_text_color(*TEXT_DARK)
            self.cell(52, 10, _s(nombre))
            # Barra de color
            self.set_fill_color(*color)
            self.rect(self.l_margin+52, y0+2.5, bar_w, 5, "F")
            # Porcentaje en color
            self.set_xy(self.l_margin+52+bar_w+3, y0)
            self.set_font("Helvetica", "B", 9.5)
            self.set_text_color(*color)
            self.cell(22, 10, f"{pct_p}%")
            # Conteo de posts
            self.set_font("Helvetica", "", 8.5)
            self.set_text_color(*TEXT_DARK)
            self.cell(30, 10, f"{cnt} post{'s' if cnt>1 else ''}")
            self.ln(11)

        self.ln(3)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*TEXT_DARK)
        self.multi_cell(0, 5, _s(
            "El portal con mayor presencia en el top es el que mejor ha logrado conectar "
            "con su audiencia a traves de contenido de alto impacto emocional o relevancia local. "
            "La frecuencia de publicacion y el uso de formatos virales (Reels) son factores clave."
        ))


def generar_brief(resumenes: list, totales: dict,
                  top_ig: list = None, top_fb: list = None) -> bytes:
    pdf = Brief()
    pdf._portales_ref = resumenes
    pdf.alias_nb_pages()
    pdf.set_margins(14, 14, 14)
    pdf.set_auto_page_break(auto=True, margin=14)

    total     = totales.get("total_imp", 1) or 1
    total_fb  = totales.get("total_fb", 0)
    total_ig  = totales.get("total_ig", 0)
    total_eng = totales.get("total_eng", 0)
    total_seg = totales.get("total_seg", 0)

    # PAGINA 1 — HERO + KPIs + EXPLICACIONES + DONUT
    pdf.add_page()

    # Hero con numero total
    pdf._hero_box(
        _n(total),
        f"TOTAL VISUALIZACIONES | ULTIMO MES  |  FB {_p(total_fb,total)}% + IG {_p(total_ig,total)}%"
    )

    # 4 KPIs principales
    pdf._kpi_row([
        (_n(total_fb),  "Alcance Facebook",       f"{_p(total_fb,total)}% del total",  BLUE_FB),
        (_n(total_ig),  "Visualiz. Instagram",    f"{_p(total_ig,total)}% del total",  PINK_IG),
        (_n(total_eng), "Interacciones FB + IG",  "engagement FB + cuentas activas IG", GREEN),
        (_n(total_seg), "Seguidores totales",     f"{len(resumenes)} portales activos", (30,30,30)),
    ])

    # EXPLICACIONES despues de los KPIs
    pdf._section("Como se interpretan estas estadisticas", HERO_BG)

    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*BLUE_FB)
    pdf.cell(0, 6, "FACEBOOK | Alcance unico (personas reales)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(0, 5, _s(
        "En Facebook contamos las personas DISTINTAS que vieron al menos una publicacion "
        "de la pagina durante el ultimo mes. Si alguien vio 10 posts, cuenta como 1. "
        "Esta metrica (page_impressions_unique) mide la AUDIENCIA REAL impactada, sin repeticiones. "
        "Es la forma mas rigurosa de medir alcance en redes sociales."
    ))
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*PINK_IG)
    pdf.cell(0, 6, "INSTAGRAM | Reproducciones totales (visualizaciones de contenido)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(0, 5, _s(
        "En Instagram sumamos TODAS las veces que se vio cualquier contenido "
        "(Reels, videos, fotos) en el ultimo mes. Una misma persona puede sumar "
        "multiples reproducciones al ver varios videos. Esta metrica (views total_value) "
        "refleja el VOLUMEN TOTAL de consumo de contenido de la cuenta."
    ))
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 6, "INTERACCIONES FB + IG | Engagement combinado", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(0, 5, _s(
        "Suma de interacciones en Facebook (likes + comentarios + compartidos en publicaciones) "
        "e interacciones en Instagram (cuentas unicas que dieron like, comentaron o guardaron "
        "algun contenido del mes). Mide la actividad activa de la audiencia mas alla del alcance pasivo."
    ))
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 6, "SEGUIDORES TOTALES | Audiencia acumulada entre portales", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.multi_cell(0, 5, _s(
        "Suma de seguidores de Facebook e Instagram de todos los portales activos. "
        "Representa la base de audiencia que recibe el contenido de forma directa y habitual. "
        "Todo el impacto de este informe es 100% ORGANICO, sin inversion publicitaria."
    ))
    pdf.ln(4)

    # DONUT con leyenda — sin barras duplicadas
    pdf._section("Participacion de cada portal en el impacto total", HERO_BG)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 5, "Porcentaje de visualizaciones aportado por cada portal sobre el total del mes.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    y_g = pdf.get_y()
    r   = 30
    xc  = pdf.l_margin + 38
    yc  = y_g + r + 4
    pdf._donut(resumenes, total, xc, yc, r)
    pdf._donut_legend(resumenes, total, pdf.l_margin + 80, y_g + 5)
    pdf.set_y(yc + r + 5)

    # PAGINAS 2+ — UN PORTAL POR PAGINA
    for i, d in enumerate(resumenes):
        pdf._portal_page(d, total, i)

    # ULTIMA PAGINA — TOP 10 INSTAGRAM
    if top_ig:
        pdf._top10_ig_page(top_ig, resumenes)

    return bytes(pdf.output())
