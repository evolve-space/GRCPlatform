"""Cálculo determinista del Compliance Score.

Funciones puras (sin acceso a base de datos): reciben conteos/agregados ya
calculados y devuelven un porcentaje o `None` ("Sin datos"). Esto permite
testear la fórmula con datasets controlados, igual que ``risk_scoring.py``
calcula el score de un riesgo sin depender de la sesión de base de datos.

--- Fórmula (documentada también en README.md y docs/SECURITY.md) ---

El Compliance Score combina 4 dimensiones, cada una expresada como un
porcentaje 0-100, ponderadas así sobre el score global (0-100):

- Controles (40%): de los controles NO marcados como "No aplicable", qué
  proporción está cubierta, contando Implementado=100%, Parcialmente
  implementado=50%, No implementado=0%.
- Evidencias (20%): de los controles Implementados o Parcialmente
  implementados (los que "deberían" tener evidencia real que los respalde),
  qué proporción tiene al menos una evidencia vigente (activa y no caducada)
  vinculada.
- Hallazgos (20%): se parte de 100 y se resta una penalización por cada
  hallazgo ABIERTO según su severidad (Crítico -15, Alto -10, Medio -5,
  Bajo -2 puntos), sin bajar de 0. Un hallazgo cerrado/aceptado no penaliza.
- Remediación (20%): acciones de remediación completadas / acciones totales.

Si una dimensión no tiene datos aplicables (p. ej. no hay controles, o
ningún control implementado/parcial, o no hay acciones), se excluye tanto del
numerador como del denominador de la media ponderada, y el peso de las
dimensiones restantes se normaliza automáticamente para seguir sumando 100.
La dimensión "Hallazgos" siempre tiene un valor definido (100 si no hay
hallazgos abiertos), así que nunca fuerza un "Sin datos" global.

Si no existe ningún control aplicable (denominador de Controles = 0), el
Compliance Score global se considera "Sin datos": Controles es la dimensión
base sobre la que se apoyan las demás (un control es lo que un hallazgo
remedia y lo que una evidencia respalda), y sin inventario de controles no
hay una base razonable para expresar un único número de cumplimiento.

Los niveles de clasificación (0-100) son:
- 90-100 → Excelente
- 75-89  → Bueno
- 60-74  → Mejorable
- 0-59   → Crítico

El Compliance Score es un indicador interno determinista de cobertura/
madurez, NUNCA una certificación ni una declaración legal de cumplimiento.
"""

from app.models.control import ControlStatus

WEIGHT_CONTROLS = 40.0
WEIGHT_EVIDENCE = 20.0
WEIGHT_FINDINGS = 20.0
WEIGHT_REMEDIATION = 20.0

_CONTROL_COVERAGE = {
    ControlStatus.IMPLEMENTED: 1.0,
    ControlStatus.PARTIALLY_IMPLEMENTED: 0.5,
    ControlStatus.NOT_IMPLEMENTED: 0.0,
}

# Puntos que resta cada hallazgo ABIERTO, según severidad (reutiliza el enum
# AssetCriticality: Finding.severity y RemediationAction.priority ya lo usan).
FINDING_PENALTIES = {
    "critical": 15.0,
    "high": 10.0,
    "medium": 5.0,
    "low": 2.0,
}


def calcular_pct_controles(conteo_por_estado: dict[ControlStatus, int]) -> float | None:
    """Porcentaje de cobertura de controles (excluye 'No aplicable')."""
    aplicables = sum(cantidad for estado, cantidad in conteo_por_estado.items() if estado != ControlStatus.NOT_APPLICABLE)
    if aplicables == 0:
        return None
    puntos = sum(
        cantidad * _CONTROL_COVERAGE[estado]
        for estado, cantidad in conteo_por_estado.items()
        if estado != ControlStatus.NOT_APPLICABLE
    )
    return puntos / aplicables * 100


def calcular_pct_evidencias(controles_aplicables: int, controles_con_evidencia_vigente: int) -> float | None:
    """Porcentaje de controles Implementados/Parciales con evidencia vigente."""
    if controles_aplicables == 0:
        return None
    return controles_con_evidencia_vigente / controles_aplicables * 100


def calcular_pct_hallazgos(conteo_abiertos_por_severidad: dict[str, int]) -> float:
    """Siempre definido: 100 si no hay hallazgos abiertos, decrece con penalizaciones."""
    penalizacion = sum(
        cantidad * FINDING_PENALTIES.get(severidad, 0.0)
        for severidad, cantidad in conteo_abiertos_por_severidad.items()
    )
    return max(0.0, 100.0 - penalizacion)


def calcular_pct_remediacion(completadas: int, total: int) -> float | None:
    if total == 0:
        return None
    return completadas / total * 100


def calcular_nivel(score: float) -> str:
    if score >= 90:
        return "excelente"
    if score >= 75:
        return "bueno"
    if score >= 60:
        return "mejorable"
    return "critico"


def calcular_compliance_score(
    *,
    controles_pct: float | None,
    evidencias_pct: float | None,
    hallazgos_pct: float | None,
    remediacion_pct: float | None,
) -> tuple[float | None, str | None]:
    """Combina las 4 dimensiones en un único score 0-100 y su nivel.

    Devuelve ``(None, None)`` si no hay controles aplicables. Cualquier otra
    dimensión en ``None`` se excluye de la media ponderada (numerador y
    denominador), renormalizando el peso restante sobre 100.
    """
    if controles_pct is None:
        return None, None

    dimensiones = [(controles_pct, WEIGHT_CONTROLS)]
    if evidencias_pct is not None:
        dimensiones.append((evidencias_pct, WEIGHT_EVIDENCE))
    if hallazgos_pct is not None:
        dimensiones.append((hallazgos_pct, WEIGHT_FINDINGS))
    if remediacion_pct is not None:
        dimensiones.append((remediacion_pct, WEIGHT_REMEDIATION))

    peso_total = sum(peso for _, peso in dimensiones)
    score = sum(pct * peso for pct, peso in dimensiones) / peso_total
    return round(score, 1), calcular_nivel(score)
