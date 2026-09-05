"""Fixtures de pytest.

Los tests corren contra una base de datos PostgreSQL de pruebas independiente
(``grcplatform_test``, creada automáticamente si no existe) para no tocar
nunca la base de datos de desarrollo/demo. Las tablas se crean directamente
desde los modelos (``Base.metadata.create_all``) en lugar de ejecutar el
histórico completo de migraciones de Alembic, ya que en los tests los
modelos son la fuente de verdad del esquema.
"""

import hashlib
import shutil
import tempfile
from collections.abc import Generator
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.rate_limit import limitador_api_key_por_ip, limitador_api_key_por_token, limitador_login
from app.core.security import create_access_token, hash_password
from app.core.storage import storage_service
from app.main import app
from app.core.risk_scoring import calcular_score
from app.models.asset import Asset, AssetCriticality, AssetStatus, AssetType, DataClassification
from app.models.control import Control, ControlFrequency, ControlStatus
from app.models.evidence import Evidence
from app.models.finding import Finding, FindingSource, FindingStatus, FindingType
from app.models.framework import Framework, FrameworkStatus, Requirement
from app.models.organization import Organization
from app.models.risk import Risk, RiskStatus, RiskTreatment
from app.models.user import User, UserRole
from app.models.integration_token import IntegrationToken
from app.models.vendor import Vendor, VendorDueDiligenceStatus, VendorStatus

TEST_DB_NAME = "grcplatform_test"


def _admin_database_url() -> str:
    base_url = settings.DATABASE_URL.rsplit("/", 1)[0]
    return f"{base_url}/postgres"


def _test_database_url() -> str:
    base_url = settings.DATABASE_URL.rsplit("/", 1)[0]
    return f"{base_url}/{TEST_DB_NAME}"


def _ensure_test_database_exists() -> None:
    admin_engine = create_engine(_admin_database_url(), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        existe = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :nombre"),
            {"nombre": TEST_DB_NAME},
        ).scalar()
        if not existe:
            connection.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin_engine.dispose()


_ensure_test_database_exists()

engine = create_engine(_test_database_url())
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(scope="session", autouse=True)
def _setup_database() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _almacenamiento_de_evidencias_aislado() -> Generator[None, None, None]:
    """Redirige el almacenamiento de archivos de Evidence a un directorio temporal
    durante toda la sesión de tests. Los tests usan una transacción de BD que se
    revierte al final de cada test, pero los archivos escritos en disco por
    ``storage_service`` NO forman parte de esa transacción: sin esto, cada
    ejecución de la suite dejaría archivos huérfanos en el almacenamiento real
    de desarrollo (``backend/storage/evidence``)."""
    directorio_temporal = tempfile.mkdtemp(prefix="grcplatform_test_evidence_")
    base_original = storage_service._base_path
    storage_service._base_path = Path(directorio_temporal)
    yield
    storage_service._base_path = base_original
    shutil.rmtree(directorio_temporal, ignore_errors=True)


@pytest.fixture(autouse=True)
def _limitadores_de_peticiones_reiniciados() -> None:
    """Los limitadores de peticiones (Fase 10) son estado de proceso global,
    no por test — sin este reinicio, tests que llaman muchas veces a
    ``/auth/login`` o a un endpoint con API key desde el mismo `TestClient`
    (que comparte una única "IP" de origen) podrían empezar a fallar con
    429 según el orden de ejecución de la suite completa."""
    limitador_login.reiniciar()
    limitador_api_key_por_ip.reiniciar()
    limitador_api_key_por_token.reiniciar()


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def organizacion_a(db_session: Session) -> Organization:
    org = Organization(name="Organización de Pruebas A")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture()
def organizacion_b(db_session: Session) -> Organization:
    org = Organization(name="Organización de Pruebas B")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


def _crear_usuario(db_session: Session, organizacion: Organization, email: str, role: UserRole) -> User:
    usuario = User(
        organization_id=organizacion.id,
        email=email,
        hashed_password=hash_password("Password123!"),
        full_name=f"Usuario de prueba ({role.value})",
        role=role,
    )
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)
    return usuario


@pytest.fixture()
def admin_org_a(db_session: Session, organizacion_a: Organization) -> User:
    return _crear_usuario(db_session, organizacion_a, "admin.a@example.com", UserRole.ADMIN)


@pytest.fixture()
def viewer_org_a(db_session: Session, organizacion_a: Organization) -> User:
    return _crear_usuario(db_session, organizacion_a, "viewer.a@example.com", UserRole.VIEWER)


@pytest.fixture()
def admin_org_b(db_session: Session, organizacion_b: Organization) -> User:
    return _crear_usuario(db_session, organizacion_b, "admin.b@example.com", UserRole.ADMIN)


@pytest.fixture()
def analyst_org_a(db_session: Session, organizacion_a: Organization) -> User:
    return _crear_usuario(db_session, organizacion_a, "analyst.a@example.com", UserRole.ANALYST)


@pytest.fixture()
def grc_manager_org_a(db_session: Session, organizacion_a: Organization) -> User:
    return _crear_usuario(db_session, organizacion_a, "grc.manager.a@example.com", UserRole.GRC_MANAGER)


@pytest.fixture()
def asset_org_a(db_session: Session, organizacion_a: Organization) -> Asset:
    activo = Asset(
        organization_id=organizacion_a.id,
        name="Servidor de pruebas A",
        description="Activo de prueba en la organización A",
        asset_type=AssetType.SERVER,
        owner="Responsable de pruebas",
        criticality=AssetCriticality.HIGH,
        data_classification=DataClassification.INTERNAL,
        status=AssetStatus.ACTIVE,
    )
    db_session.add(activo)
    db_session.commit()
    db_session.refresh(activo)
    return activo


@pytest.fixture()
def asset_org_b(db_session: Session, organizacion_b: Organization) -> Asset:
    activo = Asset(
        organization_id=organizacion_b.id,
        name="Servidor de pruebas B",
        description="Activo de prueba en la organización B",
        asset_type=AssetType.SERVER,
        owner="Responsable de pruebas",
        criticality=AssetCriticality.LOW,
        data_classification=DataClassification.PUBLIC,
        status=AssetStatus.ACTIVE,
    )
    db_session.add(activo)
    db_session.commit()
    db_session.refresh(activo)
    return activo


@pytest.fixture()
def risk_org_a(db_session: Session, organizacion_a: Organization) -> Risk:
    riesgo = Risk(
        organization_id=organizacion_a.id,
        title="Riesgo de pruebas A",
        category="Ciberseguridad",
        threat="Amenaza de pruebas",
        vulnerability="Vulnerabilidad de pruebas",
        likelihood=3,
        impact=3,
        inherent_score=calcular_score(3, 3),
        treatment=RiskTreatment.MITIGATE,
        owner="Responsable de pruebas",
        review_date=date(2027, 1, 1),
        status=RiskStatus.IDENTIFIED,
    )
    db_session.add(riesgo)
    db_session.commit()
    db_session.refresh(riesgo)
    return riesgo


@pytest.fixture()
def risk_org_b(db_session: Session, organizacion_b: Organization) -> Risk:
    riesgo = Risk(
        organization_id=organizacion_b.id,
        title="Riesgo de pruebas B",
        category="Ciberseguridad",
        threat="Amenaza de pruebas",
        vulnerability="Vulnerabilidad de pruebas",
        likelihood=2,
        impact=2,
        inherent_score=calcular_score(2, 2),
        treatment=RiskTreatment.ACCEPT,
        owner="Responsable de pruebas",
        review_date=date(2027, 1, 1),
        status=RiskStatus.IDENTIFIED,
    )
    db_session.add(riesgo)
    db_session.commit()
    db_session.refresh(riesgo)
    return riesgo


@pytest.fixture()
def control_org_a(db_session: Session, organizacion_a: Organization) -> Control:
    control = Control(
        organization_id=organizacion_a.id,
        control_id="CTRL-TEST-A",
        name="Control de pruebas A",
        category="Control de acceso",
        owner="Responsable de pruebas",
        status=ControlStatus.NOT_IMPLEMENTED,
        frequency=ControlFrequency.ANNUAL,
    )
    db_session.add(control)
    db_session.commit()
    db_session.refresh(control)
    return control


@pytest.fixture()
def control_org_b(db_session: Session, organizacion_b: Organization) -> Control:
    control = Control(
        organization_id=organizacion_b.id,
        control_id="CTRL-TEST-B",
        name="Control de pruebas B",
        category="Control de acceso",
        owner="Responsable de pruebas",
        status=ControlStatus.NOT_IMPLEMENTED,
        frequency=ControlFrequency.ANNUAL,
    )
    db_session.add(control)
    db_session.commit()
    db_session.refresh(control)
    return control


def _crear_framework(db_session: Session, organizacion: Organization, short_name: str) -> Framework:
    framework = Framework(
        organization_id=organizacion.id,
        name=f"Marco de pruebas {short_name}",
        short_name=short_name,
        version="1.0",
        status=FrameworkStatus.ACTIVE,
    )
    db_session.add(framework)
    db_session.commit()
    db_session.refresh(framework)
    return framework


@pytest.fixture()
def framework_org_a(db_session: Session, organizacion_a: Organization) -> Framework:
    return _crear_framework(db_session, organizacion_a, "ISO-TEST")


@pytest.fixture()
def framework_org_a_2(db_session: Session, organizacion_a: Organization) -> Framework:
    return _crear_framework(db_session, organizacion_a, "NIST-TEST")


@pytest.fixture()
def framework_org_b(db_session: Session, organizacion_b: Organization) -> Framework:
    return _crear_framework(db_session, organizacion_b, "ISO-TEST-B")


def _crear_requisito(
    db_session: Session, organizacion: Organization, framework: Framework, code: str
) -> Requirement:
    requisito = Requirement(
        organization_id=organizacion.id,
        framework_id=framework.id,
        code=code,
        name=f"Requisito {code}",
        category="Categoría de pruebas",
    )
    db_session.add(requisito)
    db_session.commit()
    db_session.refresh(requisito)
    return requisito


@pytest.fixture()
def requirement_org_a(
    db_session: Session, organizacion_a: Organization, framework_org_a: Framework
) -> Requirement:
    return _crear_requisito(db_session, organizacion_a, framework_org_a, "REQ-1")


@pytest.fixture()
def requirement_org_a_otro(
    db_session: Session, organizacion_a: Organization, framework_org_a: Framework
) -> Requirement:
    return _crear_requisito(db_session, organizacion_a, framework_org_a, "REQ-2")


@pytest.fixture()
def requirement_org_a_framework_2(
    db_session: Session, organizacion_a: Organization, framework_org_a_2: Framework
) -> Requirement:
    return _crear_requisito(db_session, organizacion_a, framework_org_a_2, "REQ-3")


@pytest.fixture()
def requirement_org_b(
    db_session: Session, organizacion_b: Organization, framework_org_b: Framework
) -> Requirement:
    return _crear_requisito(db_session, organizacion_b, framework_org_b, "REQ-B")


def _crear_evidencia(db_session: Session, organizacion: Organization, nombre: str) -> Evidence:
    contenido = f"Contenido de evidencia de pruebas ({nombre})".encode()
    storage_key = storage_service.generar_storage_key(organizacion.id, ".txt")
    storage_service.guardar(storage_key, contenido)
    evidencia = Evidence(
        organization_id=organizacion.id,
        name=nombre,
        original_filename="evidencia_pruebas.txt",
        storage_key=storage_key,
        mime_type="text/plain",
        file_size=len(contenido),
        sha256=hashlib.sha256(contenido).hexdigest(),
        classification=DataClassification.INTERNAL,
        evidence_type="Prueba",
        collected_at=date(2027, 1, 1),
    )
    db_session.add(evidencia)
    db_session.commit()
    db_session.refresh(evidencia)
    return evidencia


@pytest.fixture()
def evidence_org_a(db_session: Session, organizacion_a: Organization) -> Evidence:
    return _crear_evidencia(db_session, organizacion_a, "Evidencia de pruebas A")


@pytest.fixture()
def evidence_org_b(db_session: Session, organizacion_b: Organization) -> Evidence:
    return _crear_evidencia(db_session, organizacion_b, "Evidencia de pruebas B")


def _crear_hallazgo(db_session: Session, organizacion: Organization, finding_id: str) -> Finding:
    hallazgo = Finding(
        organization_id=organizacion.id,
        finding_id=finding_id,
        title=f"Hallazgo de pruebas ({finding_id})",
        finding_type=FindingType.OTHER,
        severity=AssetCriticality.MEDIUM,
        status=FindingStatus.OPEN,
        source=FindingSource.MANUAL,
        owner="Responsable de pruebas",
        discovered_at=date(2027, 1, 1),
        due_date=date(2027, 2, 1),
    )
    db_session.add(hallazgo)
    db_session.commit()
    db_session.refresh(hallazgo)
    return hallazgo


@pytest.fixture()
def finding_org_a(db_session: Session, organizacion_a: Organization) -> Finding:
    return _crear_hallazgo(db_session, organizacion_a, "FND-TEST-A")


@pytest.fixture()
def finding_org_b(db_session: Session, organizacion_b: Organization) -> Finding:
    return _crear_hallazgo(db_session, organizacion_b, "FND-TEST-B")


def _crear_proveedor(db_session: Session, organizacion: Organization, vendor_id: str) -> Vendor:
    proveedor = Vendor(
        organization_id=organizacion.id,
        vendor_id=vendor_id,
        name=f"Proveedor de pruebas ({vendor_id})",
        category="Categoría de pruebas",
        owner="Responsable de pruebas",
        criticality=AssetCriticality.MEDIUM,
        data_classification=DataClassification.INTERNAL,
        status=VendorStatus.ACTIVE,
        due_diligence_status=VendorDueDiligenceStatus.PENDING,
        relationship_start_date=date(2027, 1, 1),
    )
    db_session.add(proveedor)
    db_session.commit()
    db_session.refresh(proveedor)
    return proveedor


@pytest.fixture()
def vendor_org_a(db_session: Session, organizacion_a: Organization) -> Vendor:
    return _crear_proveedor(db_session, organizacion_a, "VEN-TEST-A")


@pytest.fixture()
def vendor_org_b(db_session: Session, organizacion_b: Organization) -> Vendor:
    return _crear_proveedor(db_session, organizacion_b, "VEN-TEST-B")


def _crear_integration_token(
    db_session: Session,
    organizacion: Organization,
    *,
    scopes: list[str],
    expires_at=None,
    revoked: bool = False,
    is_active: bool = True,
) -> tuple[str, IntegrationToken]:
    from app.core.security import generar_integration_token, hash_integration_token

    secreto = generar_integration_token()
    integracion = IntegrationToken(
        organization_id=organizacion.id,
        name="Token de pruebas",
        token_hash=hash_integration_token(secreto),
        token_prefix=secreto[:12],
        scopes=scopes,
        expires_at=expires_at,
        is_active=is_active,
        revoked_at=datetime.now(timezone.utc) if revoked else None,
    )
    db_session.add(integracion)
    db_session.commit()
    db_session.refresh(integracion)
    return secreto, integracion


@pytest.fixture()
def integration_token_org_a(db_session: Session, organizacion_a: Organization) -> tuple[str, IntegrationToken]:
    return _crear_integration_token(
        db_session,
        organizacion_a,
        scopes=["risks:read", "controls:read", "evidence:read", "findings:read", "remediation:read", "vendors:read", "dashboard:read", "compliance:read"],
    )


@pytest.fixture()
def integration_token_org_b(db_session: Session, organizacion_b: Organization) -> tuple[str, IntegrationToken]:
    return _crear_integration_token(db_session, organizacion_b, scopes=["risks:read"])


def token_para(usuario: User) -> str:
    return create_access_token(subject=str(usuario.id))


def auth_headers(usuario: User) -> dict:
    return {"Authorization": f"Bearer {token_para(usuario)}"}
