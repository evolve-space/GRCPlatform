from fastapi.testclient import TestClient

from app.models.control import Control
from app.models.framework import Framework, Requirement
from app.models.organization import Organization
from app.models.user import User

from .conftest import auth_headers


def test_crear_framework(client: TestClient, admin_org_a: User, organizacion_a: Organization):
    response = client.post(
        "/api/v1/frameworks",
        headers=auth_headers(admin_org_a),
        json={
            "name": "ISO/IEC 27001:2022",
            "short_name": "ISO 27001",
            "description": "Marco de prueba",
            "version": "2022",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["short_name"] == "ISO 27001"
    assert body["organization_id"] == str(organizacion_a.id)


def test_no_se_puede_crear_framework_duplicado(client: TestClient, admin_org_a: User):
    payload = {"name": "Marco X", "short_name": "MX", "version": "1.0"}
    client.post("/api/v1/frameworks", headers=auth_headers(admin_org_a), json=payload)
    response = client.post("/api/v1/frameworks", headers=auth_headers(admin_org_a), json=payload)
    assert response.status_code == 409


def test_listar_frameworks(client: TestClient, admin_org_a: User, framework_org_a: Framework):
    response = client.get("/api/v1/frameworks", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    nombres = {f["short_name"] for f in response.json()}
    assert framework_org_a.short_name in nombres


def test_aislamiento_de_frameworks_entre_organizaciones(
    client: TestClient, admin_org_a: User, framework_org_b: Framework
):
    response = client.get(f"/api/v1/frameworks/{framework_org_b.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 404


def test_detalle_framework_incluye_resumen_de_cumplimiento_vacio(
    client: TestClient, admin_org_a: User, framework_org_a: Framework
):
    response = client.get(f"/api/v1/frameworks/{framework_org_a.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    resumen = response.json()["compliance_summary"]
    assert resumen["total_requirements"] == 0
    assert resumen["implemented"] == 0


def test_resumen_de_cumplimiento_cuenta_controles_vinculados(
    client: TestClient,
    admin_org_a: User,
    framework_org_a: Framework,
    requirement_org_a,
    control_org_a: Control,
):
    client.post(
        f"/api/v1/controls/{control_org_a.id}/requirements",
        headers=auth_headers(admin_org_a),
        json={"requirement_id": str(requirement_org_a.id)},
    )
    client.patch(
        f"/api/v1/controls/{control_org_a.id}",
        headers=auth_headers(admin_org_a),
        json={"status": "implemented"},
    )

    response = client.get(f"/api/v1/frameworks/{framework_org_a.id}", headers=auth_headers(admin_org_a))
    resumen = response.json()["compliance_summary"]
    assert resumen["total_requirements"] == 1
    assert resumen["requirements_with_control"] == 1
    assert resumen["implemented"] == 1


def test_crear_requisito_en_framework(
    client: TestClient, admin_org_a: User, framework_org_a: Framework
):
    response = client.post(
        f"/api/v1/frameworks/{framework_org_a.id}/requirements",
        headers=auth_headers(admin_org_a),
        json={"code": "A.1.1", "name": "Requisito de prueba", "category": "Categoría"},
    )
    assert response.status_code == 201
    assert response.json()["framework_id"] == str(framework_org_a.id)


def test_no_se_puede_crear_requisito_con_codigo_duplicado(
    client: TestClient, admin_org_a: User, framework_org_a: Framework
):
    payload = {"code": "A.1.1", "name": "Requisito de prueba"}
    client.post(
        f"/api/v1/frameworks/{framework_org_a.id}/requirements",
        headers=auth_headers(admin_org_a),
        json=payload,
    )
    response = client.post(
        f"/api/v1/frameworks/{framework_org_a.id}/requirements",
        headers=auth_headers(admin_org_a),
        json=payload,
    )
    assert response.status_code == 409


def test_listar_requisitos_de_un_framework(
    client: TestClient, admin_org_a: User, framework_org_a: Framework, requirement_org_a: Requirement
):
    response = client.get(
        f"/api/v1/frameworks/{framework_org_a.id}/requirements", headers=auth_headers(admin_org_a)
    )
    assert response.status_code == 200
    codigos = {r["code"] for r in response.json()["items"]}
    assert requirement_org_a.code in codigos


def test_obtener_y_actualizar_requisito(
    client: TestClient, admin_org_a: User, requirement_org_a: Requirement
):
    response = client.get(f"/api/v1/requirements/{requirement_org_a.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 200

    actualizado = client.patch(
        f"/api/v1/requirements/{requirement_org_a.id}",
        headers=auth_headers(admin_org_a),
        json={"name": "Nombre actualizado"},
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["name"] == "Nombre actualizado"


def test_viewer_no_puede_editar_requisito(
    client: TestClient, viewer_org_a: User, requirement_org_a: Requirement
):
    response = client.patch(
        f"/api/v1/requirements/{requirement_org_a.id}",
        headers=auth_headers(viewer_org_a),
        json={"name": "Intento no autorizado"},
    )
    assert response.status_code == 403


# --- Mappings ---


def test_crear_mapping_entre_frameworks_distintos(
    client: TestClient,
    admin_org_a: User,
    requirement_org_a: Requirement,
    requirement_org_a_framework_2: Requirement,
):
    response = client.post(
        "/api/v1/mappings",
        headers=auth_headers(admin_org_a),
        json={
            "source_requirement_id": str(requirement_org_a.id),
            "target_requirement_id": str(requirement_org_a_framework_2.id),
            "notes": "Nota de prueba",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["source_requirement"]["id"] == str(requirement_org_a.id)
    assert body["target_requirement"]["id"] == str(requirement_org_a_framework_2.id)


def test_no_se_puede_mapear_requisitos_del_mismo_framework(
    client: TestClient, admin_org_a: User, requirement_org_a: Requirement, requirement_org_a_otro: Requirement
):
    response = client.post(
        "/api/v1/mappings",
        headers=auth_headers(admin_org_a),
        json={
            "source_requirement_id": str(requirement_org_a.id),
            "target_requirement_id": str(requirement_org_a_otro.id),
        },
    )
    assert response.status_code == 422


def test_no_se_puede_mapear_consigo_mismo(
    client: TestClient, admin_org_a: User, requirement_org_a: Requirement
):
    response = client.post(
        "/api/v1/mappings",
        headers=auth_headers(admin_org_a),
        json={
            "source_requirement_id": str(requirement_org_a.id),
            "target_requirement_id": str(requirement_org_a.id),
        },
    )
    assert response.status_code == 422


def test_no_se_puede_mapear_requisito_de_otra_organizacion(
    client: TestClient,
    admin_org_a: User,
    requirement_org_a: Requirement,
    requirement_org_b: Requirement,
):
    response = client.post(
        "/api/v1/mappings",
        headers=auth_headers(admin_org_a),
        json={
            "source_requirement_id": str(requirement_org_a.id),
            "target_requirement_id": str(requirement_org_b.id),
        },
    )
    assert response.status_code == 404


def test_listar_y_filtrar_mappings_por_requisito(
    client: TestClient,
    admin_org_a: User,
    requirement_org_a: Requirement,
    requirement_org_a_framework_2: Requirement,
):
    client.post(
        "/api/v1/mappings",
        headers=auth_headers(admin_org_a),
        json={
            "source_requirement_id": str(requirement_org_a.id),
            "target_requirement_id": str(requirement_org_a_framework_2.id),
        },
    )

    response = client.get(
        "/api/v1/mappings",
        headers=auth_headers(admin_org_a),
        params={"requirement_id": str(requirement_org_a.id)},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_aislamiento_de_mappings_entre_organizaciones(
    client: TestClient,
    admin_org_a: User,
    admin_org_b: User,
    requirement_org_b: Requirement,
    framework_org_b: Framework,
    db_session,
):
    from app.models.framework import Framework as FrameworkModel
    from app.models.framework import Requirement as RequirementModel

    otro_framework_b = FrameworkModel(
        organization_id=requirement_org_b.organization_id,
        name="Segundo marco de pruebas B",
        short_name="MB-2",
        version="1.0",
    )
    db_session.add(otro_framework_b)
    db_session.commit()
    db_session.refresh(otro_framework_b)

    otro_requisito_b = RequirementModel(
        organization_id=requirement_org_b.organization_id,
        framework_id=otro_framework_b.id,
        code="REQ-B-2",
        name="Otro requisito B",
    )
    db_session.add(otro_requisito_b)
    db_session.commit()
    db_session.refresh(otro_requisito_b)

    creado = client.post(
        "/api/v1/mappings",
        headers=auth_headers(admin_org_b),
        json={
            "source_requirement_id": str(requirement_org_b.id),
            "target_requirement_id": str(otro_requisito_b.id),
        },
    )
    assert creado.status_code == 201

    listado_a = client.get("/api/v1/mappings", headers=auth_headers(admin_org_a))
    assert listado_a.status_code == 200
    assert listado_a.json() == []


def test_eliminar_mapping(
    client: TestClient,
    admin_org_a: User,
    requirement_org_a: Requirement,
    requirement_org_a_framework_2: Requirement,
):
    creado = client.post(
        "/api/v1/mappings",
        headers=auth_headers(admin_org_a),
        json={
            "source_requirement_id": str(requirement_org_a.id),
            "target_requirement_id": str(requirement_org_a_framework_2.id),
        },
    )
    mapping_id = creado.json()["id"]

    response = client.delete(f"/api/v1/mappings/{mapping_id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 204

    listado = client.get("/api/v1/mappings", headers=auth_headers(admin_org_a))
    assert listado.json() == []
