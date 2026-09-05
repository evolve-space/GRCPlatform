from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.organization import Organization
from app.models.user import User

from .conftest import auth_headers


def _payload_accion(finding_id: str, **overrides) -> dict:
    base = {
        "finding_id": finding_id,
        "action_id": "ACT-100",
        "title": "Acción de prueba",
        "description": "Descripción de la acción de prueba",
        "owner": "Responsable de pruebas",
        "priority": "high",
        "due_date": "2027-02-01",
    }
    base.update(overrides)
    return base


# --- Creación y validación ---


def test_crear_accion_valida(client: TestClient, admin_org_a: User, finding_org_a: Finding, organizacion_a: Organization):
    response = client.post(
        "/api/v1/remediation-actions",
        headers=auth_headers(admin_org_a),
        json=_payload_accion(str(finding_org_a.id)),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["action_id"] == "ACT-100"
    assert body["finding_id"] == str(finding_org_a.id)
    assert body["organization_id"] == str(organizacion_a.id)
    assert body["status"] == "pending"
    assert body["completed_at"] is None


def test_no_se_puede_crear_accion_con_codigo_duplicado(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    payload = _payload_accion(str(finding_org_a.id))
    client.post("/api/v1/remediation-actions", headers=auth_headers(admin_org_a), json=payload)
    response = client.post("/api/v1/remediation-actions", headers=auth_headers(admin_org_a), json=payload)
    assert response.status_code == 409


def test_crear_accion_para_hallazgo_inexistente(client: TestClient, admin_org_a: User):
    import uuid

    response = client.post(
        "/api/v1/remediation-actions",
        headers=auth_headers(admin_org_a),
        json=_payload_accion(str(uuid.uuid4())),
    )
    assert response.status_code == 404


def test_prioridad_invalida_es_rechazada(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    response = client.post(
        "/api/v1/remediation-actions",
        headers=auth_headers(admin_org_a),
        json=_payload_accion(str(finding_org_a.id), priority="urgentisimo"),
    )
    assert response.status_code == 422


def test_estado_invalido_es_rechazado(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    response = client.post(
        "/api/v1/remediation-actions",
        headers=auth_headers(admin_org_a),
        json=_payload_accion(str(finding_org_a.id), status="pausada"),
    )
    assert response.status_code == 422


def test_no_se_pueden_anadir_acciones_a_hallazgo_cerrado(
    client: TestClient, admin_org_a: User, finding_org_a: Finding
):
    client.patch(
        f"/api/v1/findings/{finding_org_a.id}",
        headers=auth_headers(admin_org_a),
        json={"status": "closed", "resolution_summary": "Cerrado en pruebas."},
    )
    response = client.post(
        "/api/v1/remediation-actions",
        headers=auth_headers(admin_org_a),
        json=_payload_accion(str(finding_org_a.id)),
    )
    assert response.status_code == 422


# --- CRUD ---


def test_listar_acciones(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    client.post(
        "/api/v1/remediation-actions", headers=auth_headers(admin_org_a), json=_payload_accion(str(finding_org_a.id))
    )
    response = client.get("/api/v1/remediation-actions", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    codigos = {item["action_id"] for item in response.json()["items"]}
    assert "ACT-100" in codigos


def test_obtener_detalle_con_evidencias_vacias(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    creada = client.post(
        "/api/v1/remediation-actions", headers=auth_headers(admin_org_a), json=_payload_accion(str(finding_org_a.id))
    ).json()
    response = client.get(f"/api/v1/remediation-actions/{creada['id']}", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    assert response.json()["evidence"] == []


def test_actualizar_metadata(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    creada = client.post(
        "/api/v1/remediation-actions", headers=auth_headers(admin_org_a), json=_payload_accion(str(finding_org_a.id))
    ).json()
    response = client.patch(
        f"/api/v1/remediation-actions/{creada['id']}",
        headers=auth_headers(admin_org_a),
        json={"priority": "critical", "owner": "Nuevo responsable"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["priority"] == "critical"
    assert body["owner"] == "Nuevo responsable"


def test_eliminar_accion(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    creada = client.post(
        "/api/v1/remediation-actions", headers=auth_headers(admin_org_a), json=_payload_accion(str(finding_org_a.id))
    ).json()
    response = client.delete(f"/api/v1/remediation-actions/{creada['id']}", headers=auth_headers(admin_org_a))
    assert response.status_code == 204
    consulta = client.get(f"/api/v1/remediation-actions/{creada['id']}", headers=auth_headers(admin_org_a))
    assert consulta.status_code == 404


# --- Finalización ---


def test_completar_accion_establece_completed_at(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    creada = client.post(
        "/api/v1/remediation-actions", headers=auth_headers(admin_org_a), json=_payload_accion(str(finding_org_a.id))
    ).json()
    response = client.patch(
        f"/api/v1/remediation-actions/{creada['id']}",
        headers=auth_headers(admin_org_a),
        json={"status": "completed", "completion_notes": "Resuelto en pruebas."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["completed_at"] == date.today().isoformat()
    assert body["completion_notes"] == "Resuelto en pruebas."


def test_completed_at_no_se_puede_manipular_desde_el_cliente(
    client: TestClient, admin_org_a: User, finding_org_a: Finding
):
    creada = client.post(
        "/api/v1/remediation-actions", headers=auth_headers(admin_org_a), json=_payload_accion(str(finding_org_a.id))
    ).json()
    response = client.patch(
        f"/api/v1/remediation-actions/{creada['id']}",
        headers=auth_headers(admin_org_a),
        json={"status": "completed", "completed_at": "2000-01-01"},
    )
    assert response.status_code == 200
    assert response.json()["completed_at"] == date.today().isoformat()


def test_reabrir_accion_limpia_completed_at(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    creada = client.post(
        "/api/v1/remediation-actions", headers=auth_headers(admin_org_a), json=_payload_accion(str(finding_org_a.id))
    ).json()
    client.patch(
        f"/api/v1/remediation-actions/{creada['id']}",
        headers=auth_headers(admin_org_a),
        json={"status": "completed"},
    )
    reabierta = client.patch(
        f"/api/v1/remediation-actions/{creada['id']}",
        headers=auth_headers(admin_org_a),
        json={"status": "in_progress"},
    )
    assert reabierta.status_code == 200
    assert reabierta.json()["completed_at"] is None


# --- Filtros ---


def test_filtro_por_estado_y_prioridad(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    client.post(
        "/api/v1/remediation-actions",
        headers=auth_headers(admin_org_a),
        json=_payload_accion(str(finding_org_a.id), action_id="ACT-BLOQ", status="blocked", priority="low"),
    )
    por_estado = client.get(
        "/api/v1/remediation-actions", headers=auth_headers(admin_org_a), params={"status": "blocked"}
    )
    assert "ACT-BLOQ" in {i["action_id"] for i in por_estado.json()["items"]}

    por_prioridad = client.get(
        "/api/v1/remediation-actions", headers=auth_headers(admin_org_a), params={"priority": "low"}
    )
    assert "ACT-BLOQ" in {i["action_id"] for i in por_prioridad.json()["items"]}


def test_filtro_por_responsable(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    client.post(
        "/api/v1/remediation-actions",
        headers=auth_headers(admin_org_a),
        json=_payload_accion(str(finding_org_a.id), action_id="ACT-OWN", owner="Responsable Único ABC"),
    )
    response = client.get(
        "/api/v1/remediation-actions", headers=auth_headers(admin_org_a), params={"owner": "Único ABC"}
    )
    assert "ACT-OWN" in {i["action_id"] for i in response.json()["items"]}


def test_filtro_por_finding(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    client.post(
        "/api/v1/remediation-actions",
        headers=auth_headers(admin_org_a),
        json=_payload_accion(str(finding_org_a.id), action_id="ACT-FND"),
    )
    response = client.get(
        "/api/v1/remediation-actions",
        headers=auth_headers(admin_org_a),
        params={"finding_id": str(finding_org_a.id)},
    )
    assert "ACT-FND" in {i["action_id"] for i in response.json()["items"]}


def test_filtro_vencidas(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    ayer = (date.today() - timedelta(days=1)).isoformat()
    client.post(
        "/api/v1/remediation-actions",
        headers=auth_headers(admin_org_a),
        json=_payload_accion(str(finding_org_a.id), action_id="ACT-VENC", due_date=ayer),
    )
    response = client.get(
        "/api/v1/remediation-actions", headers=auth_headers(admin_org_a), params={"overdue": "true"}
    )
    assert "ACT-VENC" in {i["action_id"] for i in response.json()["items"]}


def test_accion_completada_no_cuenta_como_vencida(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    ayer = (date.today() - timedelta(days=1)).isoformat()
    creada = client.post(
        "/api/v1/remediation-actions",
        headers=auth_headers(admin_org_a),
        json=_payload_accion(str(finding_org_a.id), action_id="ACT-VENC-OK", due_date=ayer),
    ).json()
    client.patch(
        f"/api/v1/remediation-actions/{creada['id']}",
        headers=auth_headers(admin_org_a),
        json={"status": "completed"},
    )
    response = client.get(
        "/api/v1/remediation-actions", headers=auth_headers(admin_org_a), params={"overdue": "true"}
    )
    assert "ACT-VENC-OK" not in {i["action_id"] for i in response.json()["items"]}


# --- RBAC ---


def test_viewer_no_puede_crear(client: TestClient, viewer_org_a: User, finding_org_a: Finding):
    response = client.post(
        "/api/v1/remediation-actions",
        headers=auth_headers(viewer_org_a),
        json=_payload_accion(str(finding_org_a.id)),
    )
    assert response.status_code == 403


def test_viewer_no_puede_editar_ni_eliminar(client: TestClient, admin_org_a: User, viewer_org_a: User, finding_org_a: Finding):
    creada = client.post(
        "/api/v1/remediation-actions", headers=auth_headers(admin_org_a), json=_payload_accion(str(finding_org_a.id))
    ).json()
    assert (
        client.patch(
            f"/api/v1/remediation-actions/{creada['id']}", headers=auth_headers(viewer_org_a), json={"owner": "X"}
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/remediation-actions/{creada['id']}", headers=auth_headers(viewer_org_a)).status_code
        == 403
    )


def test_analyst_puede_crear_y_editar_no_eliminar(client: TestClient, analyst_org_a: User, finding_org_a: Finding):
    creada = client.post(
        "/api/v1/remediation-actions", headers=auth_headers(analyst_org_a), json=_payload_accion(str(finding_org_a.id))
    )
    assert creada.status_code == 201
    editada = client.patch(
        f"/api/v1/remediation-actions/{creada.json()['id']}",
        headers=auth_headers(analyst_org_a),
        json={"owner": "Otro"},
    )
    assert editada.status_code == 200
    eliminada = client.delete(
        f"/api/v1/remediation-actions/{creada.json()['id']}", headers=auth_headers(analyst_org_a)
    )
    assert eliminada.status_code == 403


def test_admin_y_grc_manager_pueden_eliminar(
    client: TestClient, admin_org_a: User, grc_manager_org_a: User, finding_org_a: Finding
):
    a1 = client.post(
        "/api/v1/remediation-actions",
        headers=auth_headers(admin_org_a),
        json=_payload_accion(str(finding_org_a.id), action_id="ACT-DEL-1"),
    ).json()
    a2 = client.post(
        "/api/v1/remediation-actions",
        headers=auth_headers(admin_org_a),
        json=_payload_accion(str(finding_org_a.id), action_id="ACT-DEL-2"),
    ).json()
    assert (
        client.delete(f"/api/v1/remediation-actions/{a1['id']}", headers=auth_headers(admin_org_a)).status_code
        == 204
    )
    assert (
        client.delete(
            f"/api/v1/remediation-actions/{a2['id']}", headers=auth_headers(grc_manager_org_a)
        ).status_code
        == 204
    )


# --- Multi-tenant ---


def test_no_puede_crear_accion_para_hallazgo_de_otra_organizacion(
    client: TestClient, admin_org_a: User, finding_org_b: Finding
):
    response = client.post(
        "/api/v1/remediation-actions",
        headers=auth_headers(admin_org_a),
        json=_payload_accion(str(finding_org_b.id)),
    )
    assert response.status_code == 404


def test_no_puede_listar_acciones_de_otra_organizacion(
    client: TestClient, admin_org_a: User, admin_org_b: User, finding_org_b: Finding
):
    client.post(
        "/api/v1/remediation-actions",
        headers=auth_headers(admin_org_b),
        json=_payload_accion(str(finding_org_b.id), action_id="ACT-TENANT-B"),
    )
    listado_a = client.get("/api/v1/remediation-actions", headers=auth_headers(admin_org_a))
    assert "ACT-TENANT-B" not in {i["action_id"] for i in listado_a.json()["items"]}


def test_no_puede_consultar_modificar_ni_eliminar_accion_de_otra_organizacion(
    client: TestClient, admin_org_a: User, admin_org_b: User, finding_org_b: Finding
):
    accion_b = client.post(
        "/api/v1/remediation-actions",
        headers=auth_headers(admin_org_b),
        json=_payload_accion(str(finding_org_b.id), action_id="ACT-TENANT-B2"),
    ).json()

    assert (
        client.get(f"/api/v1/remediation-actions/{accion_b['id']}", headers=auth_headers(admin_org_a)).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/remediation-actions/{accion_b['id']}",
            headers=auth_headers(admin_org_a),
            json={"owner": "Hackeado"},
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/v1/remediation-actions/{accion_b['id']}", headers=auth_headers(admin_org_a)
        ).status_code
        == 404
    )


def test_no_puede_vincular_evidencia_de_otra_organizacion(
    client: TestClient, admin_org_a: User, finding_org_a: Finding, evidence_org_b: Evidence
):
    creada = client.post(
        "/api/v1/remediation-actions", headers=auth_headers(admin_org_a), json=_payload_accion(str(finding_org_a.id))
    ).json()
    response = client.post(
        f"/api/v1/remediation-actions/{creada['id']}/evidence",
        headers=auth_headers(admin_org_a),
        json={"evidence_id": str(evidence_org_b.id)},
    )
    assert response.status_code == 404


# --- Relaciones (mismo tenant) ---


def test_vincular_y_desvincular_evidencia_de_cierre(
    client: TestClient, admin_org_a: User, finding_org_a: Finding, evidence_org_a: Evidence
):
    creada = client.post(
        "/api/v1/remediation-actions", headers=auth_headers(admin_org_a), json=_payload_accion(str(finding_org_a.id))
    ).json()

    vinculo = client.post(
        f"/api/v1/remediation-actions/{creada['id']}/evidence",
        headers=auth_headers(admin_org_a),
        json={"evidence_id": str(evidence_org_a.id)},
    )
    assert vinculo.status_code == 201
    assert any(e["id"] == str(evidence_org_a.id) for e in vinculo.json()["evidence"])

    desvinculo = client.delete(
        f"/api/v1/remediation-actions/{creada['id']}/evidence/{evidence_org_a.id}",
        headers=auth_headers(admin_org_a),
    )
    assert desvinculo.json()["evidence"] == []
