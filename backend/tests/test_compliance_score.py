import math

from app.core.compliance_score import (
    calcular_compliance_score,
    calcular_nivel,
    calcular_pct_controles,
    calcular_pct_evidencias,
    calcular_pct_hallazgos,
    calcular_pct_remediacion,
)
from app.models.control import ControlStatus


def _aprox(a: float, b: float, tol: float = 0.01) -> bool:
    return math.isclose(a, b, abs_tol=tol)


# --- Controles ---


def test_controles_todos_implementados():
    conteo = {ControlStatus.IMPLEMENTED: 10}
    assert calcular_pct_controles(conteo) == 100.0


def test_controles_todos_parciales():
    conteo = {ControlStatus.PARTIALLY_IMPLEMENTED: 10}
    assert calcular_pct_controles(conteo) == 50.0


def test_controles_todos_no_implementados():
    conteo = {ControlStatus.NOT_IMPLEMENTED: 10}
    assert calcular_pct_controles(conteo) == 0.0


def test_controles_no_aplicable_excluido_del_denominador():
    # Ejemplo de la especificación: 10 controles; 6 implementados; 2 parciales;
    # 1 no implementado; 1 no aplicable -> aplicables = 9
    conteo = {
        ControlStatus.IMPLEMENTED: 6,
        ControlStatus.PARTIALLY_IMPLEMENTED: 2,
        ControlStatus.NOT_IMPLEMENTED: 1,
        ControlStatus.NOT_APPLICABLE: 1,
    }
    resultado = calcular_pct_controles(conteo)
    esperado = (6 * 1.0 + 2 * 0.5 + 1 * 0.0) / 9 * 100  # 77.777...
    assert _aprox(resultado, esperado)


def test_controles_todos_no_aplicables_devuelve_sin_datos():
    conteo = {ControlStatus.NOT_APPLICABLE: 5}
    assert calcular_pct_controles(conteo) is None


def test_controles_sin_controles_devuelve_sin_datos():
    assert calcular_pct_controles({}) is None


# --- Evidencias ---


def test_evidencias_todos_los_controles_aplicables_con_evidencia():
    assert calcular_pct_evidencias(controles_aplicables=4, controles_con_evidencia_vigente=4) == 100.0


def test_evidencias_algunos_sin_evidencia():
    assert calcular_pct_evidencias(controles_aplicables=4, controles_con_evidencia_vigente=1) == 25.0


def test_evidencias_ninguno_con_evidencia():
    assert calcular_pct_evidencias(controles_aplicables=4, controles_con_evidencia_vigente=0) == 0.0


def test_evidencias_sin_controles_aplicables_devuelve_sin_datos():
    assert calcular_pct_evidencias(controles_aplicables=0, controles_con_evidencia_vigente=0) is None


# --- Hallazgos ---


def test_hallazgos_sin_hallazgos_abiertos_es_100():
    assert calcular_pct_hallazgos({}) == 100.0


def test_hallazgos_solo_bajos():
    assert calcular_pct_hallazgos({"low": 3}) == 100.0 - 3 * 2.0


def test_hallazgos_solo_altos():
    assert calcular_pct_hallazgos({"high": 2}) == 100.0 - 2 * 10.0


def test_hallazgos_solo_criticos():
    assert calcular_pct_hallazgos({"critical": 2}) == 100.0 - 2 * 15.0


def test_hallazgos_mezcla():
    conteo = {"critical": 1, "high": 1, "medium": 1, "low": 1}
    esperado = 100.0 - (15.0 + 10.0 + 5.0 + 2.0)
    assert calcular_pct_hallazgos(conteo) == esperado


def test_hallazgos_penalizacion_nunca_baja_de_cero():
    conteo = {"critical": 10}
    assert calcular_pct_hallazgos(conteo) == 0.0


# --- Remediación ---


def test_remediacion_todas_completadas():
    assert calcular_pct_remediacion(completadas=5, total=5) == 100.0


def test_remediacion_ninguna_completada():
    assert calcular_pct_remediacion(completadas=0, total=5) == 0.0


def test_remediacion_mezcla():
    assert calcular_pct_remediacion(completadas=3, total=4) == 75.0


def test_remediacion_sin_acciones_devuelve_sin_datos():
    assert calcular_pct_remediacion(completadas=0, total=0) is None


# --- Niveles ---


def test_nivel_excelente():
    assert calcular_nivel(90) == "excelente"
    assert calcular_nivel(100) == "excelente"


def test_nivel_bueno():
    assert calcular_nivel(75) == "bueno"
    assert calcular_nivel(89) == "bueno"


def test_nivel_mejorable():
    assert calcular_nivel(60) == "mejorable"
    assert calcular_nivel(74) == "mejorable"


def test_nivel_critico():
    assert calcular_nivel(59) == "critico"
    assert calcular_nivel(0) == "critico"


# --- Score final combinado ---


def test_score_sin_controles_es_sin_datos():
    score, nivel = calcular_compliance_score(
        controles_pct=None, evidencias_pct=50.0, hallazgos_pct=100.0, remediacion_pct=50.0
    )
    assert score is None
    assert nivel is None


def test_score_todas_las_dimensiones_con_datos():
    # Controles 80%, Evidencias 60%, Hallazgos 90%, Remediación 70%
    # Score = 80*0.4 + 60*0.2 + 90*0.2 + 70*0.2 = 32+12+18+14 = 76
    score, nivel = calcular_compliance_score(
        controles_pct=80.0, evidencias_pct=60.0, hallazgos_pct=90.0, remediacion_pct=70.0
    )
    assert score == 76.0
    assert nivel == "bueno"


def test_score_sin_evidencias_ni_remediacion_renormaliza_pesos():
    # Solo Controles (40) y Hallazgos (20) tienen datos -> pesos normalizados 40/60 y 20/60
    # Controles 100%, Hallazgos 50% -> score = (100*40 + 50*20) / 60 = 83.333...
    score, nivel = calcular_compliance_score(
        controles_pct=100.0, evidencias_pct=None, hallazgos_pct=50.0, remediacion_pct=None
    )
    assert _aprox(score, (100 * 40 + 50 * 20) / 60, tol=0.05)
    assert nivel == "bueno"


def test_score_perfecto_es_100_excelente():
    score, nivel = calcular_compliance_score(
        controles_pct=100.0, evidencias_pct=100.0, hallazgos_pct=100.0, remediacion_pct=100.0
    )
    assert score == 100.0
    assert nivel == "excelente"


def test_score_peor_caso_es_0_critico():
    score, nivel = calcular_compliance_score(
        controles_pct=0.0, evidencias_pct=0.0, hallazgos_pct=0.0, remediacion_pct=0.0
    )
    assert score == 0.0
    assert nivel == "critico"


def test_score_nunca_produce_nan_ni_infinito():
    casos = [
        (None, None, 100.0, None),
        (0.0, None, 100.0, None),
        (100.0, None, 0.0, None),
        (50.0, 50.0, 50.0, 50.0),
    ]
    for controles, evidencias, hallazgos, remediacion in casos:
        score, _nivel = calcular_compliance_score(
            controles_pct=controles, evidencias_pct=evidencias, hallazgos_pct=hallazgos, remediacion_pct=remediacion
        )
        if score is not None:
            assert not math.isnan(score)
            assert not math.isinf(score)
            assert 0.0 <= score <= 100.0
