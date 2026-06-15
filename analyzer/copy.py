"""
Análisis del copy / título de un reel (heurístico, en español).

Busca lo que engancha en contenido de noticias/viral: ganchos de curiosidad
("…y no vas a creer lo que pasó"), preguntas, intriga, palabras de impacto, etc.
Devuelve un puntaje + lo que encontró (positivo) + sugerencias concretas.
No usa LLM: son reglas y listas de patrones.
"""
import re

# Ganchos de curiosidad típicos del estilo (ES rioplatense / noticias).
HOOKS = [
    "no vas a creer", "no lo vas a creer", "no podrás creer", "no podras creer",
    "lo que pasó", "lo que paso", "lo que dijo", "lo que hizo", "lo que encontró",
    "lo que encontro", "lo que descubrió", "lo que descubrio", "mirá lo que",
    "mira lo que", "esto es lo que", "lo que nadie", "nadie esperaba",
    "sorprendió a todos", "sorprendio a todos", "te va a sorprender",
    "así fue", "asi fue", "así reaccionó", "asi reacciono", "el motivo",
    "la razón por la que", "la razon por la que", "lo que se viene",
    "tenés que ver", "tenes que ver", "no te lo pierdas", "lo que muestra",
]

# Palabras de impacto / emoción.
POWER = [
    "increíble", "increible", "impactante", "tremendo", "escándalo", "escandalo",
    "polémica", "polemica", "urgente", "alerta", "histórico", "historico",
    "exclusivo", "imperdible", "viral", "fuerte", "brutal", "insólito", "insolito",
    "récord", "record", "escalofriante", "conmovedor", "indignante",
]

_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF☀-➿←-⇿⬀-⯿]")


def analyze_copy(caption):
    """Devuelve {score, found, tips, has_copy, hook}."""
    cap = (caption or "").strip()
    low = cap.lower()
    found, tips = [], []
    score = 0

    if not cap:
        return {"score": 0, "has_copy": False, "hook": None, "found": [],
                "tips": ["No pusiste copy. Un buen título con gancho sube mucho el "
                         "potencial: probá «…y no vas a creer lo que pasó»."]}

    hook = next((h for h in HOOKS if h in low), None)
    if hook:
        found.append(f"Gancho de curiosidad: «{hook}»")
        score += 35
    else:
        tips.append("Sumá un gancho de curiosidad, tipo «…y no vas a creer lo que "
                    "pasó» o «…lo que pasó sorprendió a todos».")

    if cap.endswith("...") or "…" in cap:
        found.append("Termina en puntos suspensivos (genera intriga)")
        score += 12
    if "?" in cap:
        found.append("Hace una pregunta (invita a ver/responder)")
        score += 10
    else:
        tips.append("Probá una pregunta directa para enganchar (¿qué pasó?, ¿lo viste?).")

    pw = [w for w in POWER if w in low]
    if pw:
        found.append("Palabras de impacto: " + ", ".join(sorted(set(pw))[:3]))
        score += min(len(set(pw)) * 8, 16)
    else:
        tips.append("Una palabra de impacto ayuda (increíble, impactante, urgente, "
                    "polémica…).")

    if re.search(r"\d", cap):
        found.append("Incluye un número (dato/lista)")
        score += 6
    if _EMOJI.search(cap):
        found.append("Usa emojis (llaman la atención)")
        score += 6

    n = len(cap)
    if n < 15:
        tips.append("El copy es muy corto: un título un poco más descriptivo engancha más.")
    elif n > 220:
        tips.append("El copy es largo: poné el gancho al principio, no al final.")
    else:
        score += 5

    return {"score": max(0, min(100, score)), "has_copy": True, "hook": hook,
            "found": found, "tips": tips}
