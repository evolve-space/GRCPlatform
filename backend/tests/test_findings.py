from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.asset import Asset
from app.models.control import Control
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.framework import Requirement
from app.models.organization import Organization
from app.models.risk import Risk
from app.models.user import User

from .conftest import auth_headers


def _payload_hallazgo(**overrides) -> dict:
    base = {
        "finding_id": "FND-100",
        "title": "Hallazgo de prueba",
        "description": "Descripción del hallazgo de prueba",
        "finding_type": "control_review",
        "severity": "high",
        "source": "control",
        "owner": "Responsable de pruebas",
        "discovered_at": "2027-01-01",
        "due_date": "2027-02-01",
    }
    base.update(overrides)
    return base


# --- Creación y validación ---


def test_crear_hallazgo_valido(client: TestClient, admin_org_a: User, organizacion_a: Organization):
    response = client.post(
        "/api/v1/findings", headers=auth_headers(admin_org_a), json=_payload_hallazgo()
    )
    assert response.status_code == 201
    body = response.json()
    assert body["finding_id"] == "FND-100"
    assert body["organization_id"] == str(organizacion_a.id)
    assert body["status"] == "open"
    assert body["closed_at"] is None


def test_no_se_puede_crear_hallazgo_con_codigo_duplicado(client: TestClient, admin_org_a: User):
    client.post("/api/v1/findings", headers=auth_headers(admin_org_a), json=_payload_hallazgo())
    response = client.post(
        "/api/v1/findings", headers=auth_headers(admin_org_a), json=_payload_hallazgo()
    )
    assert response.status_code == 409


def test_severidad_invalida_es_rechazada(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/findings", headers=auth_headers(admin_org_a), json=_payload_hallazgo(severity="urgente")
    )
    assert response.status_code == 422


def test_estado_invalido_es_rechazado(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/findings", headers=auth_headers(admin_org_a), json=_payload_hallazgo(status="pausado")
    )
    assert response.status_code == 422


def test_fecha_limite_anterior_a_descubrimiento_es_rechazada(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/findings",
        headers=auth_headers(admin_org_a),
        json=_payload_hallazgo(discovered_at="2027-06-01", due_date="2027-01-01"),
    )
    assert response.status_code == 422


def test_crear_hallazgo_cerrado_sin_resolucion_es_rechazado(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/findings",
        headers=auth_headers(admin_org_a),
        json=_payload_hallazgo(status="closed"),
    )
    assert response.status_code == 422


def test_crear_hallazgo_cerrado_con_resolucion_establece_closed_at(
    client: TestClient, admin_org_a: User
):
    response = client.post(
        "/api/v1/findings",
        headers=auth_headers(admin_org_a),
        json=_payload_hallazgo(status="closed", resolution_summary="Resuelto en pruebas."),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["closed_at"] == date.today().isoformat()


# --- CRUD ---


def test_listar_hallazgos(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    response = client.get("/api/v1/findings", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    codigos = {item["finding_id"] for item in response.json()["items"]}
    assert finding_org_a.finding_id in codigos


def test_obtener_detalle_con_relaciones_vacias(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    response = client.get(f"/api/v1/findings/{finding_org_a.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    body = response.json()
    assert body["risks"] == []
    assert body["controls"] == []
    assert body["assets"] == []
    assert body["requirements"] == []
    assert body["evidence"] == []
    assert body["actions"] == []


def test_actualizar_metadata(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    response = client.patch(
        f"/api/v1/findings/{finding_org_a.id}",
        headers=auth_headers(admin_org_a),
        json={"severity": "critical", "owner": "Nuevo responsable"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["severity"] == "critical"
    assert body["owner"] == "Nuevo responsable"


def test_eliminar_hallazgo(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    response = client.delete(f"/api/v1/findings/{finding_org_a.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 204
    consulta = client.get(f"/api/v1/findings/{finding_org_a.id}", headers=auth_headers(admin_org_a))
    assert consulta.status_code == 404


# --- Cierre ---


def test_cerrar_hallazgo_sin_resolucion_es_rechazado(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    response = client.patch(
        f"/api/v1/findings/{finding_org_a.id}", headers=auth_headers(admin_org_a), json={"status": "closed"}
    )
    assert response.status_code == 422


def test_cerrar_hallazgo_establece_closed_at_por_backend(
    client: TestClient, admin_org_a: User, finding_org_a: Finding
):
    response = client.patch(
        f"/api/v1/findings/{finding_org_a.id}",
        headers=auth_headers(admin_org_a),
        json={"status": "closed", "resolution_summary": "Cerrado en pruebas."},
    )
    assert response.status_code == 200
    assert response.json()["closed_at"] == date.today().isoformat()


def test_closed_at_no_se_puede_manipular_desde_el_cliente(
    client: TestClient, admin_org_a: User, finding_org_a: Finding
):
    """closed_at no es un campo aceptado por el esquema de actualización: cualquier
    valor enviado por el cliente se ignora silenciosamente."""
    response = client.patch(
        f"/api/v1/findings/{finding_org_a.id}",
        headers=auth_headers(admin_org_a),
        json={
            "status": "closed",
            "resolution_summary": "Cerrado en pruebas.",
            "closed_at": "2000-01-01",
        },
    )
    assert response.status_code == 200
    assert response.json()["closed_at"] == date.today().isoformat()


def test_reabrir_hallazgo_limpia_closed_at(client: TestClient, admin_org_a: User, finding_org_a: Finding):
    cerrado = client.patch(
        f"/api/v1/findings/{finding_org_a.id}",
        headers=auth_headers(admin_org_a),
        json={"status": "closed", "resolution_summary": "Cerrado en pruebas."},
    )
    assert cerrado.json()["closed_at"] is not None

    reabierto = client.patch(
        f"/api/v1/findings/{finding_org_a.id}",
        headers=auth_headers(admin_org_a),
        json={"status": "open"},
    )
    assert reabierto.status_code == 200
    assert reabierto.json()["closed_at"] is None


# --- Filtros ---


def test_filtro_por_severidad(client: TestClient, admin_org_a: User):
    client.post(
        "/api/v1/findings",
        headers=auth_headers(admin_org_a),
        json=_payload_hallazgo(finding_id="FND-SEV-1", severity="critical"),
    )
    response = client.get(
        "/api/v1/findings", headers=auth_headers(admin_org_a), params={"severity": "critical"}
    )
    codigos = {item["finding_id"] for item in response.json()["items"]}
    assert "FND-SEV-1" in codigos


def test_filtro_por_estado(client: TestClient, admin_org_a: User):
    client.post(
        "/api/v1/findings",
        headers=auth_headers(admin_org_a),
        json=_payload_hallazgo(finding_id="FND-EST-1", status="under_review"),
    )
    response = client.get(
        "/api/v1/findings", headers=auth_headers(admin_org_a), params={"status": "under_review"}
    )
    codigos = {item["finding_id"] for item in response.json()["items"]}
    assert "FND-EST-1" in codigos


def test_filtro_por_tipo_y_origen(client: TestClient, admin_org_a: User):
    client.post(
        "/api/v1/findings",
        headers=auth_headers(admin_org_a),
        json=_payload_hallazgo(finding_id="FND-TIPO-1", finding_type="incident", source="incident"),
    )
    response = client.get(
        "/api/v1/findings",
        headers=auth_headers(admin_org_a),
        params={"finding_type": "incident", "source": "incident"},
    )
    codigos = {item["finding_id"] for item in response.json()["items"]}
    assert "FND-TIPO-1" in codigos


def test_filtro_por_responsable(client: TestClient, admin_org_a: User):
    client.post(
        "/api/v1/findings",
        headers=auth_headers(admin_org_a),
        json=_payload_hallazgo(finding_id="FND-OWN-1", owner="Responsable Único XYZ"),
    )
    response = client.get(
        "/api/v1/findings", headers=auth_headers(admin_org_a), params={"owner": "Único XYZ"}
    )
    codigos = {item["finding_id"] for item in response.json()["items"]}
    assert "FND-OWN-1" in codigos


def test_filtro_vencidos(client: TestClient, admin_org_a: User):
    ayer = (date.today() - timedelta(days=1)).isoformat()
    client.post(
        "/api/v1/findings",
        headers=auth_headers(admin_org_a),
        json=_payload_hallazgo(
            finding_id="FND-VENC-1", discovered_at="2020-01-01", due_date=ayer, status="open"
        ),
    )
    response = client.get("/api/v1/findings", headers=auth_headers(admin_org_a), params={"overdue": "true"})
    codigos = {item["finding_id"] for item in response.json()["items"]}
    assert "FND-VENC-1" in codigos


def test_hallazgo_cerrado_no_cuenta_como_vencido(client: TestClient, admin_org_a: User):
    ayer = (date.today() - timedelta(days=1)).isoformat()
    client.post(
        "/api/v1/findings",
        headers=auth_headers(admin_org_a),
        json=_payload_hallazgo(
            finding_id="FND-VENC-CERRADO",
            discovered_at="2020-01-01",
            due_date=ayer,
            status="closed",
            resolution_summary="Resuelto.",
        ),
    )
    response = client.get("/api/v1/findings", headers=auth_headers(admin_org_a), params={"overdue": "true"})
    codigos = {item["finding_id"] for item in response.json()["items"]}
    assert "FND-VENC-CERRADO" not in codigos


def test_filtro_por_riesgo_y_control(
    client: TestClient, admin_org_a: User, risk_org_a: Risk, control_org_a: Control
):
    creado = client.post(
        "/api/v1/findings", headers=auth_headers(admin_org_a), json=_payload_hallazgo(finding_id="FND-REL-1")
    ).json()
    client.post(
        f"/api/v1/findings/{creado['id']}/risks",
        headers=auth_headers(admin_org_a),
        json={"risk_id": str(risk_org_a.id)},
    )
    client.post(
        f"/api/v1/findings/{creado['id']}/controls",
        headers=auth_headers(admin_org_a),
        json={"control_id": str(control_org_a.id)},
    )

    por_riesgo = client.get(
        "/api/v1/findings", headers=auth_headers(admin_org_a), params={"risk_id": str(risk_org_a.id)}
    )
    assert creado["id"] in {item["id"] for item in por_riesgo.json()["items"]}

    por_control = client.get(
        "/api/v1/findings", headers=auth_headers(admin_org_a), params={"control_id": str(control_org_a.id)}
    )
    assert creado["id"] in {item["id"] for item in por_control.json()["items"]}


# --- RBAC ---


def test_viewer_no_puede_crear(client: TestClient, viewer_org_a: User):
    response = client.post(
        "/api/v1/findings", headers=auth_headers(viewer_org_a), json=_payload_hallazgo()
    )
    assert response.status_code == 403


def test_viewer_no_puede_editar(client: TestClient, viewer_org_a: User, finding_org_a: Finding):
    response = client.patch(
        f"/api/v1/findings/{finding_org_a.id}", headers=auth_headers(viewer_org_a), json={"owner": "X"}
    )
    assert response.status_code == 403


def test_viewer_no_puede_eliminar(client: TestClient, viewer_org_a: User, finding_org_a: Finding):
    response = client.delete(f"/api/v1/findings/{finding_org_a.id}", headers=auth_headers(viewer_org_a))
    assert response.status_code == 403


def test_analyst_puede_crear_y_editar(client: TestClient, analyst_org_a: User):
    creado = client.post(
        "/api/v1/findings", headers=auth_headers(analyst_org_a), json=_payload_hallazgo()
    )
    assert creado.status_code == 201
    editado = client.patch(
        f"/api/v1/findings/{creado.json()['id']}",
        headers=auth_headers(analyst_org_a),
        json={"owner": "Otro"},
    )
    assert editado.status_code == 200


def test_analyst_no_puede_eliminar(client: TestClient, analyst_org_a: User, finding_org_a: Finding):
    response = client.delete(f"/api/v1/findings/{finding_org_a.id}", headers=auth_headers(analyst_org_a))
    assert response.status_code == 403


def test_admin_y_grc_manager_pueden_eliminar(
    client: TestClient, admin_org_a: User, grc_manager_org_a: User
):
    f1 = client.post(
        "/api/v1/findings", headers=auth_headers(admin_org_a), json=_payload_hallazgo(finding_id="FND-DEL-1")
    ).json()
    f2 = client.post(
        "/api/v1/findings", headers=auth_headers(admin_org_a), json=_payload_hallazgo(finding_id="FND-DEL-2")
    ).json()
    assert client.delete(f"/api/v1/findings/{f1['id']}", headers=auth_headers(admin_org_a)).status_code == 204
    assert (
        client.delete(f"/api/v1/findings/{f2['id']}", headers=auth_headers(grc_manager_org_a)).status_code
        == 204
    )


# --- Multi-tenant ---


def test_no_puede_listar_hallazgos_de_otra_organizacion(
    client: TestClient, admin_org_a: User, admin_org_b: User
):
    client.post(
        "/api/v1/findings", headers=auth_headers(admin_org_a), json=_payload_hallazgo(finding_id="FND-TENANT-A")
    )
    listado_b = client.get("/api/v1/findings", headers=auth_headers(admin_org_b))
    codigos = {item["finding_id"] for item in listado_b.json()["items"]}
    assert "FND-TENANT-A" not in codigos


def test_no_puede_consultar_hallazgo_de_otra_organizacion(
    client: TestClient, admin_org_a: User, finding_org_b: Finding
):
    response = client.get(f"/api/v1/findings/{finding_org_b.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 404


def test_no_puede_modificar_hallazgo_de_otra_organizacion(
    client: TestClient, admin_org_a: User, finding_org_b: Finding
):
    response = client.patch(
        f"/api/v1/findings/{finding_org_b.id}", headers=auth_headers(admin_org_a), json={"owner": "Hackeado"}
    )
    assert response.status_code == 404


def test_no_puede_eliminar_hallazgo_de_otra_organizacion(
    client: TestClient, admin_org_a: User, finding_org_b: Finding
):
    response = client.delete(f"/api/v1/findings/{finding_org_b.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 404


def test_no_puede_vincular_riesgo_de_otra_organizacion(
    client: TestClient, admin_org_a: User, finding_org_a: Finding, risk_org_b: Risk
):
    response = client.post(
        f"/api/v1/findings/{finding_org_a.id}/risks",
        headers=auth_headers(admin_org_a),
        json={"risk_id": str(risk_org_b.id)},
    )
    assert response.status_code == 404


def test_no_puede_vincular_control_de_otra_organizacion(
    client: TestClient, admin_org_a: User, finding_org_a: Finding, control_org_b: Control
):
    response = client.post(
        f"/api/v1/findings/{finding_org_a.id}/controls",
        headers=auth_headers(admin_org_a),
        json={"control_id": str(control_org_b.id)},
    )
    assert response.status_code == 404


def test_no_puede_vincular_activo_de_otra_organizacion(
    client: TestClient, admin_org_a: User, finding_org_a: Finding, asset_org_b: Asset
):
    response = client.post(
        f"/api/v1/findings/{finding_org_a.id}/assets",
        headers=auth_headers(admin_org_a),
        json={"asset_id": str(asset_org_b.id)},
    )
    assert response.status_code == 404


def test_no_puede_vincular_requisito_de_otra_organizacion(
    client: TestClient, admin_org_a: User, finding_org_a: Finding, requirement_org_b: Requirement
):
    response = client.post(
        f"/api/v1/findings/{finding_org_a.id}/requirements",
        headers=auth_headers(admin_org_a),
        json={"requirement_id": str(requirement_org_b.id)},
    )
    assert response.status_code == 404


def test_no_puede_vincular_evidencia_de_otra_organizacion(
    client: TestClient, admin_org_a: User, finding_org_a: Finding, evidence_org_b: Evidence
):
    response = client.post(
        f"/api/v1/findings/{finding_org_a.id}/evidence",
        headers=auth_headers(admin_org_a),
        json={"evidence_id": str(evidence_org_b.id)},
    )
    assert response.status_code == 404


# --- Relaciones (mismo tenant) ---


def test_vincular_y_desvincular_riesgo(client: TestClient, admin_org_a: User, finding_org_a: Finding, risk_org_a: Risk):
    vinculo = client.post(
        f"/api/v1/findings/{finding_org_a.id}/risks",
        headers=auth_headers(admin_org_a),
        json={"risk_id": str(risk_org_a.id)},
    )
    assert vinculo.status_code == 201
    assert any(r["id"] == str(risk_org_a.id) for r in vinculo.json()["risks"])

    desvinculo = client.delete(
        f"/api/v1/findings/{finding_org_a.id}/risks/{risk_org_a.id}", headers=auth_headers(admin_org_a)
    )
    assert desvinculo.json()["risks"] == []


def test_vincular_y_desvincular_control(
    client: TestClient, admin_org_a: User, finding_org_a: Finding, control_org_a: Control
):
    vinculo = client.post(
        f"/api/v1/findings/{finding_org_a.id}/controls",
        headers=auth_headers(admin_org_a),
        json={"control_id": str(control_org_a.id)},
    )
    assert vinculo.status_code == 201
    assert any(c["id"] == str(control_org_a.id) for c in vinculo.json()["controls"])


def test_vincular_y_desvincular_activo(
    client: TestClient, admin_org_a: User, finding_org_a: Finding, asset_org_a: Asset
):
    vinculo = client.post(
        f"/api/v1/findings/{finding_org_a.id}/assets",
        headers=auth_headers(admin_org_a),
        json={"asset_id": str(asset_org_a.id)},
    )
    assert vinculo.status_code == 201
    assert any(a["id"] == str(asset_org_a.id) for a in vinculo.json()["assets"])


def test_vincular_y_desvincular_requisito(
    client: TestClient, admin_org_a: User, finding_org_a: Finding, requirement_org_a: Requirement
):
    vinculo = client.post(
        f"/api/v1/findings/{finding_org_a.id}/requirements",
        headers=auth_headers(admin_org_a),
        json={"requirement_id": str(requirement_org_a.id)},
    )
    assert vinculo.status_code == 201
    assert any(r["id"] == str(requirement_org_a.id) for r in vinculo.json()["requirements"])


def test_vincular_y_desvincular_evidencia(
    client: TestClient, admin_org_a: User, finding_org_a: Finding, evidence_org_a: Evidence
):
    vinculo = client.post(
        f"/api/v1/findings/{finding_org_a.id}/evidence",
        headers=auth_headers(admin_org_a),
        json={"evidence_id": str(evidence_org_a.id)},
    )
    assert vinculo.status_code == 201
    assert any(e["id"] == str(evidence_org_a.id) for e in vinculo.json()["evidence"])

    desvinculo = client.delete(
        f"/api/v1/findings/{finding_org_a.id}/evidence/{evidence_org_a.id}",
        headers=auth_headers(admin_org_a),
    )
    assert desvinculo.json()["evidence"] == []


# --- Integridad hallazgo/acción ---


def test_hallazgo_con_varias_acciones_aparece_en_detalle(
    client: TestClient, admin_org_a: User, finding_org_a: Finding
):
    for codigo in ("ACT-D1", "ACT-D2"):
        client.post(
            "/api/v1/remediation-actions",
            headers=auth_headers(admin_org_a),
            json={
                "finding_id": str(finding_org_a.id),
                "action_id": codigo,
                "title": f"Acción {codigo}",
                "owner": "Responsable de pruebas",
                "priority": "medium",
                "due_date": "2027-03-01",
            },
        )

    response = client.get(f"/api/v1/findings/{finding_org_a.id}", headers=auth_headers(admin_org_a))
    codigos_accion = {a["action_id"] for a in response.json()["actions"]}
    assert codigos_accion == {"ACT-D1", "ACT-D2"}
