"""
Procesamiento de la contribución de los seguidores a la audiencia total.

Funciones PURAS (sin Streamlit ni red) para poder testearlas aisladas. Toman
los dicts de portal que ya arma la página de Estadísticas Globales y derivan:

  - base de seguidores (FB + IG),
  - audiencia alcanzada (alcance ÚNICO de FB + IG en el período),
  - factor de amplificación = alcance / seguidores,
  - cota inferior de NO-seguidores alcanzados = max(0, alcance - seguidores),
  - cuota de cada portal en la audiencia total y en la base de seguidores.

Sobre la cota de no-seguidores: el alcance es de personas ÚNICAS, y no podés
alcanzar más seguidores únicos que los que tenés. Por eso, cuando el alcance
supera a la base de seguidores, el excedente son necesariamente personas que
(en su mayoría) no te siguen. Es una COTA INFERIOR honesta: el número real de
no-seguidores puede ser mayor (no todos tus seguidores ven cada publicación).
El dato exacto requiere el desglose `follow_type` de la API, que se incorpora
cuando esa métrica se cargue al warehouse.
"""


def _num(v):
    """Normaliza None/strings a int/float >= 0."""
    try:
        n = float(v or 0)
    except (TypeError, ValueError):
        n = 0.0
    return n if n > 0 else 0.0


def fila_portal(d):
    """
    Calcula los indicadores de contribución de un solo portal.

    d: dict con (al menos) fb_seg, ig_seg, fb_imp (alcance único FB),
       ig_reach (alcance único IG) y nombre.
    """
    seguidores = _num(d.get("fb_seg")) + _num(d.get("ig_seg"))
    alcance    = _num(d.get("fb_imp")) + _num(d.get("ig_reach"))
    no_seg     = max(0.0, alcance - seguidores)
    return {
        "nombre":            d.get("nombre", ""),
        "seguidores":        int(seguidores),
        "alcance":           int(alcance),
        "no_seguidores_min": int(no_seg),
        "amplificacion":     (alcance / seguidores) if seguidores else 0.0,
        "pct_no_seg":        (no_seg / alcance) if alcance else 0.0,
    }


def contribucion_audiencia(portales):
    """
    Agrega la contribución de seguidores de una lista de portales.

    Devuelve un dict con:
      - filas: lista por portal (incluye share_seguidores y share_audiencia),
        ordenada por alcance descendente,
      - totales globales y factor de amplificación global.
    """
    filas = [fila_portal(d) for d in portales]

    tot_seg   = sum(f["seguidores"] for f in filas)
    tot_alc   = sum(f["alcance"] for f in filas)
    tot_noseg = sum(f["no_seguidores_min"] for f in filas)

    for f in filas:
        f["share_seguidores"] = (f["seguidores"] / tot_seg) if tot_seg else 0.0
        f["share_audiencia"]  = (f["alcance"] / tot_alc) if tot_alc else 0.0
        # "Sobre-rendimiento": cuánto pesa en la audiencia frente a lo que pesa
        # en seguidores. >1 = atrae más audiencia de la que su base sugiere.
        f["indice_aporte"] = (
            f["share_audiencia"] / f["share_seguidores"]
            if f["share_seguidores"] else 0.0
        )

    filas.sort(key=lambda f: f["alcance"], reverse=True)

    return {
        "filas":                filas,
        "total_seguidores":     tot_seg,
        "total_alcance":        tot_alc,
        "total_no_seg_min":     tot_noseg,
        "amplificacion_global": (tot_alc / tot_seg) if tot_seg else 0.0,
        "pct_no_seg_global":    (tot_noseg / tot_alc) if tot_alc else 0.0,
    }


if __name__ == "__main__":
    # Auto-test rápido con datos sintéticos.
    demo = [
        {"nombre": "A", "fb_seg": 10000, "ig_seg": 5000,  "fb_imp": 40000, "ig_reach": 30000},
        {"nombre": "B", "fb_seg": 2000,  "ig_seg": 8000,  "fb_imp": 5000,  "ig_reach": 60000},
        {"nombre": "C", "fb_seg": 0,     "ig_seg": 1000,  "fb_imp": 0,     "ig_reach": 500},  # alcance < base
    ]
    r = contribucion_audiencia(demo)
    assert r["total_seguidores"] == 26000, r
    assert r["total_alcance"] == 135500, r   # 70000 + 65000 + 500
    # A: 70000-15000=55000 ; B: 65000-10000=55000 ; C: 500<1000 -> 0
    assert r["total_no_seg_min"] == 110000, r
    fa = {f["nombre"]: f for f in r["filas"]}
    assert fa["C"]["no_seguidores_min"] == 0, fa["C"]
    assert round(r["amplificacion_global"], 4) == round(135500 / 26000, 4), r
    # B atrae más audiencia (65k) que A (70k)? A>B, así que orden: A primero
    assert r["filas"][0]["nombre"] == "A", r["filas"]
    # índice de aporte de B debe ser > 1 (pesa más en audiencia que en seguidores)
    assert fa["B"]["indice_aporte"] > 1, fa["B"]
    print("OK — contribucion_audiencia:")
    for f in r["filas"]:
        print(f"  {f['nombre']}: seg={f['seguidores']:,} alc={f['alcance']:,} "
              f"amp={f['amplificacion']:.2f} %noseg={f['pct_no_seg']*100:.0f} "
              f"aporte={f['indice_aporte']:.2f}")
    print(f"  GLOBAL amp={r['amplificacion_global']:.2f} "
          f"%noseg={r['pct_no_seg_global']*100:.0f}")
