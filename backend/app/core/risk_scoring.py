"""Cálculo determinista del riesgo. Siempre se ejecuta en backend (nunca se confía
en un score enviado por el cliente): probabilidad × impacto, clasificado en
Bajo / Medio / Alto / Crítico según los umbrales de la especificación.
"""


def calcular_score(likelihood: int, impact: int) -> int:
    return likelihood * impact


def clasificar_nivel(score: int) -> str:
    if score <= 4:
        return "bajo"
    if score <= 9:
        return "medio"
    if score <= 16:
        return "alto"
    return "critico"
