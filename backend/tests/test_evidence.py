import hashlib
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.storage import storage_service
from app.models.asset import Asset
from app.models.control import Control
from app.models.evidence import Evidence
from app.models.framework import Requirement
from app.models.organization import Organization
from app.models.risk import Risk
from app.models.user import User

from .conftest import auth_headers

CONTENIDO_TXT = b"Este es un documento de prueba ficticio para los tests de Evidencias."


def _subir(
    client: TestClient,
    usuario: User,
    *,
    filename: str = "documento_prueba.txt",
    contenido: bytes = CONTENIDO_TXT,
    content_type: str = "text/plain",
    **overrides,
):
    datos = {
        "name": "Evidencia de prueba",
        "classification": "internal",
        "evidence_type": "Prueba",
        "collected_at": "2027-01-01",
    }
    datos.update(overrides)
    return client.post(
        "/api/v1/evidence",
        headers=auth_headers(usuario),
        data=datos,
        files={"file": (filename, contenido, content_type)},
    )


# --- Subida ---


def test_subida_valida_con_metadata_correcta(client: TestClient, admin_org_a: User, organizacion_a: Organization):
    response = _subir(client, admin_org_a, name="Política de prueba", description="Descripción de prueba")
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Política de prueba"
    assert body["description"] == "Descripción de prueba"
    assert body["organization_id"] == str(organizacion_a.id)
    assert body["original_filename"] == "documento_prueba.txt"
    assert body["mime_type"] == "text/plain"
    assert body["file_size"] == len(CONTENIDO_TXT)
    assert body["classification"] == "internal"
    assert body["status"] == "active"
    assert body["is_expired"] is False
    assert body["effective_status"] == "active"
    assert "storage_key" not in body


def test_archivo_se_almacena_fisicamente(client: TestClient, admin_org_a: User, db_session: Session):
    response = _subir(client, admin_org_a)
    evidencia = db_session.get(Evidence, response.json()["id"])
    assert storage_service.existe(evidencia.storage_key)


def test_hash_sha256_correcto(client: TestClient, admin_org_a: User):
    response = _subir(client, admin_org_a)
    esperado = hashlib.sha256(CONTENIDO_TXT).hexdigest()
    assert response.json()["sha256"] == esperado


# --- Validación ---


def test_archivo_demasiado_grande_es_rechazado(client: TestClient, admin_org_a: User, monkeypatch):
    monkeypatch.setattr("app.api.routes.evidence.settings.MAX_EVIDENCE_FILE_SIZE_MB", 0)
    response = _subir(client, admin_org_a)
    assert response.status_code == 422
    assert "tamaño máximo" in response.json()["detail"]["message"]


def test_extension_prohibida_es_rechazada(client: TestClient, admin_org_a: User):
    response = _subir(client, admin_org_a, filename="script.exe", contenido=b"contenido cualquiera")
    assert response.status_code == 422
    assert "no permitida" in response.json()["detail"]["message"]


def test_contenido_no_coincide_con_extension(client: TestClient, admin_org_a: User):
    response = _subir(
        client, admin_org_a, filename="informe.pdf", contenido=b"esto no es un PDF real", content_type="application/pdf"
    )
    assert response.status_code == 422
    assert "no coincide" in response.json()["detail"]["message"]


def test_firma_peligrosa_es_rechazada_sin_importar_extension(client: TestClient, admin_org_a: User):
    response = _subir(client, admin_org_a, filename="normal.txt", contenido=b"MZ contenido de un ejecutable falso")
    assert response.status_code == 422


def test_nombre_de_archivo_peligroso_se_sanea(client: TestClient, admin_org_a: User):
    response = _subir(client, admin_org_a, filename="../../../etc/passwd.txt")
    assert response.status_code == 201
    assert response.json()["original_filename"] == "passwd.txt"


def test_path_traversal_no_escapa_del_directorio_de_almacenamiento(
    client: TestClient, admin_org_a: User, db_session: Session
):
    response = _subir(client, admin_org_a, filename="../../../etc/passwd.txt")
    evidencia = db_session.get(Evidence, response.json()["id"])
    assert "etc" not in evidencia.storage_key
    assert storage_service.existe(evidencia.storage_key)


def test_archivo_vacio_es_rechazado(client: TestClient, admin_org_a: User):
    response = _subir(client, admin_org_a, contenido=b"")
    assert response.status_code == 422
    assert "vacío" in response.json()["detail"]["message"]


def test_contenido_duplicado_esta_permitido(client: TestClient, admin_org_a: User):
    """Dos evidencias distintas pueden compartir el mismo contenido de archivo
    (p. ej. la misma política usada como evidencia de dos controles distintos)."""
    primera = _subir(client, admin_org_a, name="Copia 1")
    segunda = _subir(client, admin_org_a, name="Copia 2")
    assert primera.status_code == 201
    assert segunda.status_code == 201
    assert primera.json()["sha256"] == segunda.json()["sha256"]
    assert primera.json()["id"] != segunda.json()["id"]


def test_fecha_expiracion_anterior_a_recopilacion_es_rechazada(client: TestClient, admin_org_a: User):
    response = _subir(client, admin_org_a, collected_at="2027-06-01", expires_at="2027-01-01")
    assert response.status_code == 422


# --- CRUD ---


def test_listar_evidencias(client: TestClient, admin_org_a: User):
    _subir(client, admin_org_a, name="Evidencia listada")
    response = client.get("/api/v1/evidence", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    nombres = {item["name"] for item in response.json()["items"]}
    assert "Evidencia listada" in nombres


def test_obtener_detalle_con_relaciones_vacias(client: TestClient, admin_org_a: User):
    creada = _subir(client, admin_org_a).json()
    response = client.get(f"/api/v1/evidence/{creada['id']}", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    body = response.json()
    assert body["controls"] == []
    assert body["risks"] == []
    assert body["assets"] == []
    assert body["requirements"] == []


def test_modificar_metadata(client: TestClient, admin_org_a: User):
    creada = _subir(client, admin_org_a).json()
    response = client.patch(
        f"/api/v1/evidence/{creada['id']}",
        headers=auth_headers(admin_org_a),
        json={"classification": "restricted", "status": "archived", "name": "Nombre actualizado"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["classification"] == "restricted"
    assert body["status"] == "archived"
    assert body["name"] == "Nombre actualizado"
    assert body["effective_status"] == "archived"


def test_eliminar_evidencia_borra_metadata_y_archivo(
    client: TestClient, admin_org_a: User, db_session: Session
):
    creada = _subir(client, admin_org_a).json()
    evidencia = db_session.get(Evidence, creada["id"])
    storage_key = evidencia.storage_key
    assert storage_service.existe(storage_key)

    response = client.delete(f"/api/v1/evidence/{creada['id']}", headers=auth_headers(admin_org_a))
    assert response.status_code == 204

    consulta = client.get(f"/api/v1/evidence/{creada['id']}", headers=auth_headers(admin_org_a))
    assert consulta.status_code == 404
    assert not storage_service.existe(storage_key)


# --- Descarga ---


def test_descarga_correcta_y_contenido_coincide(client: TestClient, admin_org_a: User):
    creada = _subir(client, admin_org_a).json()
    response = client.get(f"/api/v1/evidence/{creada['id']}/download", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    assert response.content == CONTENIDO_TXT


def test_descarga_usa_nombre_de_archivo_original(client: TestClient, admin_org_a: User):
    creada = _subir(client, admin_org_a, filename="informe_original.txt").json()
    response = client.get(f"/api/v1/evidence/{creada['id']}/download", headers=auth_headers(admin_org_a))
    assert "informe_original.txt" in response.headers["content-disposition"]


def test_descarga_requiere_autenticacion(client: TestClient, admin_org_a: User):
    creada = _subir(client, admin_org_a).json()
    response = client.get(f"/api/v1/evidence/{creada['id']}/download")
    assert response.status_code == 401


# --- Integridad ---


def test_integridad_correcta(client: TestClient, admin_org_a: User):
    creada = _subir(client, admin_org_a).json()
    response = client.get(f"/api/v1/evidence/{creada['id']}/integrity", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["sha256_calculated"] == body["sha256_stored"]


def test_integridad_detecta_archivo_alterado(client: TestClient, admin_org_a: User, db_session: Session):
    creada = _subir(client, admin_org_a).json()
    evidencia = db_session.get(Evidence, creada["id"])
    storage_service.guardar(evidencia.storage_key, b"contenido manipulado por un tercero")

    response = client.get(f"/api/v1/evidence/{creada['id']}/integrity", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["status"] == "mismatch"
    assert body["sha256_calculated"] != body["sha256_stored"]


def test_integridad_archivo_inexistente(client: TestClient, admin_org_a: User, db_session: Session):
    creada = _subir(client, admin_org_a).json()
    evidencia = db_session.get(Evidence, creada["id"])
    storage_service.eliminar(evidencia.storage_key)

    response = client.get(f"/api/v1/evidence/{creada['id']}/integrity", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["status"] == "not_found"
    assert body["sha256_calculated"] is None


# --- RBAC ---


def test_viewer_no_puede_subir(client: TestClient, viewer_org_a: User):
    response = _subir(client, viewer_org_a)
    assert response.status_code == 403


def test_viewer_puede_listar_y_descargar(client: TestClient, admin_org_a: User, viewer_org_a: User):
    creada = _subir(client, admin_org_a).json()
    listado = client.get("/api/v1/evidence", headers=auth_headers(viewer_org_a))
    assert listado.status_code == 200
    descarga = client.get(f"/api/v1/evidence/{creada['id']}/download", headers=auth_headers(viewer_org_a))
    assert descarga.status_code == 200


def test_viewer_no_puede_modificar(client: TestClient, admin_org_a: User, viewer_org_a: User):
    creada = _subir(client, admin_org_a).json()
    response = client.patch(
        f"/api/v1/evidence/{creada['id']}", headers=auth_headers(viewer_org_a), json={"name": "Intento"}
    )
    assert response.status_code == 403


def test_viewer_no_puede_eliminar(client: TestClient, admin_org_a: User, viewer_org_a: User):
    creada = _subir(client, admin_org_a).json()
    response = client.delete(f"/api/v1/evidence/{creada['id']}", headers=auth_headers(viewer_org_a))
    assert response.status_code == 403


def test_analyst_puede_subir_y_modificar(client: TestClient, analyst_org_a: User):
    creada = _subir(client, analyst_org_a).json()
    response = client.patch(
        f"/api/v1/evidence/{creada['id']}", headers=auth_headers(analyst_org_a), json={"name": "Editado por analista"}
    )
    assert response.status_code == 200


def test_analyst_no_puede_eliminar(client: TestClient, analyst_org_a: User):
    creada = _subir(client, analyst_org_a).json()
    response = client.delete(f"/api/v1/evidence/{creada['id']}", headers=auth_headers(analyst_org_a))
    assert response.status_code == 403


def test_admin_y_grc_manager_pueden_eliminar(
    client: TestClient, admin_org_a: User, grc_manager_org_a: User
):
    creada_admin = _subir(client, admin_org_a, name="Para admin").json()
    creada_grc = _subir(client, admin_org_a, name="Para grc manager").json()

    assert client.delete(
        f"/api/v1/evidence/{creada_admin['id']}", headers=auth_headers(admin_org_a)
    ).status_code == 204
    assert client.delete(
        f"/api/v1/evidence/{creada_grc['id']}", headers=auth_headers(grc_manager_org_a)
    ).status_code == 204


# --- Multi-tenant ---


def test_no_puede_listar_evidencias_de_otra_organizacion(
    client: TestClient, admin_org_a: User, admin_org_b: User
):
    _subir(client, admin_org_a, name="Evidencia de A")
    listado_b = client.get("/api/v1/evidence", headers=auth_headers(admin_org_b))
    nombres = {item["name"] for item in listado_b.json()["items"]}
    assert "Evidencia de A" not in nombres


def test_no_puede_consultar_evidencia_de_otra_organizacion(
    client: TestClient, admin_org_a: User, admin_org_b: User
):
    creada = _subir(client, admin_org_a).json()
    response = client.get(f"/api/v1/evidence/{creada['id']}", headers=auth_headers(admin_org_b))
    assert response.status_code == 404


def test_no_puede_descargar_evidencia_de_otra_organizacion(
    client: TestClient, admin_org_a: User, admin_org_b: User
):
    creada = _subir(client, admin_org_a).json()
    response = client.get(f"/api/v1/evidence/{creada['id']}/download", headers=auth_headers(admin_org_b))
    assert response.status_code == 404


def test_no_puede_modificar_evidencia_de_otra_organizacion(
    client: TestClient, admin_org_a: User, admin_org_b: User
):
    creada = _subir(client, admin_org_a).json()
    response = client.patch(
        f"/api/v1/evidence/{creada['id']}", headers=auth_headers(admin_org_b), json={"name": "Hackeado"}
    )
    assert response.status_code == 404


def test_no_puede_eliminar_evidencia_de_otra_organizacion(
    client: TestClient, admin_org_a: User, admin_org_b: User
):
    creada = _subir(client, admin_org_a).json()
    response = client.delete(f"/api/v1/evidence/{creada['id']}", headers=auth_headers(admin_org_b))
    assert response.status_code == 404


def test_no_puede_vincular_control_de_otra_organizacion(
    client: TestClient, admin_org_a: User, control_org_b: Control
):
    creada = _subir(client, admin_org_a).json()
    response = client.post(
        f"/api/v1/evidence/{creada['id']}/controls",
        headers=auth_headers(admin_org_a),
        json={"control_id": str(control_org_b.id)},
    )
    assert response.status_code == 404


def test_no_puede_vincular_riesgo_de_otra_organizacion(
    client: TestClient, admin_org_a: User, risk_org_b: Risk
):
    creada = _subir(client, admin_org_a).json()
    response = client.post(
        f"/api/v1/evidence/{creada['id']}/risks",
        headers=auth_headers(admin_org_a),
        json={"risk_id": str(risk_org_b.id)},
    )
    assert response.status_code == 404


def test_no_puede_vincular_activo_de_otra_organizacion(
    client: TestClient, admin_org_a: User, asset_org_b: Asset
):
    creada = _subir(client, admin_org_a).json()
    response = client.post(
        f"/api/v1/evidence/{creada['id']}/assets",
        headers=auth_headers(admin_org_a),
        json={"asset_id": str(asset_org_b.id)},
    )
    assert response.status_code == 404


def test_no_puede_vincular_requisito_de_otra_organizacion(
    client: TestClient, admin_org_a: User, requirement_org_b: Requirement
):
    creada = _subir(client, admin_org_a).json()
    response = client.post(
        f"/api/v1/evidence/{creada['id']}/requirements",
        headers=auth_headers(admin_org_a),
        json={"requirement_id": str(requirement_org_b.id)},
    )
    assert response.status_code == 404


# --- Relaciones (mismo tenant) ---


def test_vincular_y_desvincular_control(client: TestClient, admin_org_a: User, control_org_a: Control):
    creada = _subir(client, admin_org_a).json()
    vinculo = client.post(
        f"/api/v1/evidence/{creada['id']}/controls",
        headers=auth_headers(admin_org_a),
        json={"control_id": str(control_org_a.id)},
    )
    assert vinculo.status_code == 201
    assert any(c["id"] == str(control_org_a.id) for c in vinculo.json()["controls"])

    desvinculo = client.delete(
        f"/api/v1/evidence/{creada['id']}/controls/{control_org_a.id}", headers=auth_headers(admin_org_a)
    )
    assert desvinculo.status_code == 200
    assert desvinculo.json()["controls"] == []


def test_vincular_y_desvincular_riesgo(client: TestClient, admin_org_a: User, risk_org_a: Risk):
    creada = _subir(client, admin_org_a).json()
    vinculo = client.post(
        f"/api/v1/evidence/{creada['id']}/risks",
        headers=auth_headers(admin_org_a),
        json={"risk_id": str(risk_org_a.id)},
    )
    assert vinculo.status_code == 201
    assert any(r["id"] == str(risk_org_a.id) for r in vinculo.json()["risks"])


def test_vincular_y_desvincular_activo(client: TestClient, admin_org_a: User, asset_org_a: Asset):
    creada = _subir(client, admin_org_a).json()
    vinculo = client.post(
        f"/api/v1/evidence/{creada['id']}/assets",
        headers=auth_headers(admin_org_a),
        json={"asset_id": str(asset_org_a.id)},
    )
    assert vinculo.status_code == 201
    assert any(a["id"] == str(asset_org_a.id) for a in vinculo.json()["assets"])


def test_vincular_y_desvincular_requisito(
    client: TestClient, admin_org_a: User, requirement_org_a: Requirement
):
    creada = _subir(client, admin_org_a).json()
    vinculo = client.post(
        f"/api/v1/evidence/{creada['id']}/requirements",
        headers=auth_headers(admin_org_a),
        json={"requirement_id": str(requirement_org_a.id)},
    )
    assert vinculo.status_code == 201
    assert any(r["id"] == str(requirement_org_a.id) for r in vinculo.json()["requirements"])


# --- Expiración ---


def test_evidencia_vigente_no_esta_caducada(client: TestClient, admin_org_a: User):
    en_30_dias = (date.today() + timedelta(days=30)).isoformat()
    respuesta = _subir(client, admin_org_a, collected_at="2020-01-01", expires_at=en_30_dias)
    assert respuesta.status_code == 201
    creada = respuesta.json()
    assert creada["is_expired"] is False
    assert creada["effective_status"] == "active"


def test_evidencia_caducada_se_refleja_en_effective_status(client: TestClient, admin_org_a: User):
    ayer = (date.today() - timedelta(days=1)).isoformat()
    respuesta = _subir(client, admin_org_a, collected_at="2020-01-01", expires_at=ayer)
    assert respuesta.status_code == 201
    creada = respuesta.json()
    assert creada["is_expired"] is True
    assert creada["effective_status"] == "expired"


def test_filtro_de_evidencias_caducadas(client: TestClient, admin_org_a: User):
    ayer = (date.today() - timedelta(days=1)).isoformat()
    manana = (date.today() + timedelta(days=30)).isoformat()
    vigente = _subir(client, admin_org_a, name="Vigente filtro", collected_at="2020-01-01", expires_at=manana)
    caducada = _subir(
        client, admin_org_a, name="Caducada filtro", collected_at="2020-01-01", expires_at=ayer
    )
    assert vigente.status_code == 201
    assert caducada.status_code == 201

    response = client.get(
        "/api/v1/evidence", headers=auth_headers(admin_org_a), params={"expired": "true"}
    )
    nombres = {item["name"] for item in response.json()["items"]}
    assert "Caducada filtro" in nombres
    assert "Vigente filtro" not in nombres


def test_filtro_proximas_a_caducar(client: TestClient, admin_org_a: User):
    en_10_dias = (date.today() + timedelta(days=10)).isoformat()
    en_90_dias = (date.today() + timedelta(days=90)).isoformat()
    _subir(client, admin_org_a, name="Próxima a caducar", collected_at="2020-01-01", expires_at=en_10_dias)
    _subir(client, admin_org_a, name="Lejos de caducar", collected_at="2020-01-01", expires_at=en_90_dias)

    response = client.get(
        "/api/v1/evidence",
        headers=auth_headers(admin_org_a),
        params={"expiring_within_days": 30},
    )
    nombres = {item["name"] for item in response.json()["items"]}
    assert "Próxima a caducar" in nombres
    assert "Lejos de caducar" not in nombres
