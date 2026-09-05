"""Datos de demostración ficticios para desarrollo local.

Ejecutar con: python -m app.db.seed
No utilizar en producción ni con datos reales de ninguna empresa.

Los datos de ISO 27001 y NIST CSF son un subconjunto reducido y representativo,
suficiente para demostrar la funcionalidad de marcos de cumplimiento. No es una
reproducción del contenido oficial de ninguno de los dos estándares.
"""

import hashlib
import struct
import zlib
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.core.audit import registrar_evento
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.file_validation import determinar_tipo_seguro, sanear_nombre_original
from app.core.risk_scoring import calcular_score
from app.core.security import hash_password
from app.core.storage import storage_service
from app.models.asset import Asset, AssetCriticality, AssetStatus, AssetType, DataClassification
from app.models.control import Control, ControlFrequency, ControlStatus
from app.models.evidence import Evidence
from app.models.finding import Finding, FindingSource, FindingStatus, FindingType
from app.models.framework import Framework, FrameworkMapping, FrameworkStatus, Requirement
from app.models.organization import Organization
from app.models.remediation_action import ActionStatus, RemediationAction
from app.models.risk import Risk, RiskStatus, RiskTreatment
from app.models.user import User, UserRole
from app.models.vendor import Vendor, VendorDueDiligenceStatus, VendorStatus

DEMO_PASSWORD = "Demo1234!"

DEMO_USERS = [
    ("admin@acme-labs.demo", "Ana Administradora", UserRole.ADMIN),
    ("grc.manager@acme-labs.demo", "Gonzalo Gestor GRC", UserRole.GRC_MANAGER),
    ("analista@acme-labs.demo", "Alicia Analista", UserRole.ANALYST),
    ("visor@acme-labs.demo", "Víctor Visor", UserRole.VIEWER),
]

HOY = date.today()

DEMO_ASSETS = [
    {
        "name": "Portal de Clientes (Web)",
        "description": "Aplicación web pública donde los clientes consultan y gestionan su cuenta.",
        "asset_type": AssetType.APPLICATION,
        "owner": "Gonzalo Gestor GRC",
        "criticality": AssetCriticality.CRITICAL,
        "data_classification": DataClassification.CONFIDENTIAL,
        "status": AssetStatus.ACTIVE,
    },
    {
        "name": "Base de datos de clientes",
        "description": "Base de datos PostgreSQL con datos personales y de facturación de clientes.",
        "asset_type": AssetType.DATABASE,
        "owner": "Alicia Analista",
        "criticality": AssetCriticality.CRITICAL,
        "data_classification": DataClassification.RESTRICTED,
        "status": AssetStatus.ACTIVE,
    },
    {
        "name": "Servidor de ficheros interno",
        "description": "Almacenamiento compartido de documentación interna de los departamentos.",
        "asset_type": AssetType.SERVER,
        "owner": "Alicia Analista",
        "criticality": AssetCriticality.MEDIUM,
        "data_classification": DataClassification.INTERNAL,
        "status": AssetStatus.ACTIVE,
    },
    {
        "name": "Pasarela de pagos",
        "description": "Servicio que procesa los cobros con tarjeta de los pedidos online.",
        "asset_type": AssetType.SERVICE,
        "owner": "Gonzalo Gestor GRC",
        "criticality": AssetCriticality.CRITICAL,
        "data_classification": DataClassification.RESTRICTED,
        "status": AssetStatus.ACTIVE,
    },
    {
        "name": "Portátiles corporativos",
        "description": "Flota de portátiles asignados al personal con acceso a sistemas internos.",
        "asset_type": AssetType.ENDPOINT,
        "owner": "Alicia Analista",
        "criticality": AssetCriticality.MEDIUM,
        "data_classification": DataClassification.INTERNAL,
        "status": AssetStatus.ACTIVE,
    },
    {
        "name": "VPN de acceso remoto",
        "description": "Acceso remoto cifrado para el personal en teletrabajo.",
        "asset_type": AssetType.SYSTEM,
        "owner": "Gonzalo Gestor GRC",
        "criticality": AssetCriticality.HIGH,
        "data_classification": DataClassification.CONFIDENTIAL,
        "status": AssetStatus.ACTIVE,
    },
    {
        "name": "Proceso de alta de empleados",
        "description": "Proceso de onboarding: creación de cuentas, permisos y activos asignados.",
        "asset_type": AssetType.PROCESS,
        "owner": "Ana Administradora",
        "criticality": AssetCriticality.LOW,
        "data_classification": DataClassification.INTERNAL,
        "status": AssetStatus.ACTIVE,
    },
    {
        "name": "Proveedor de nóminas externo",
        "description": "Gestoría externa que procesa las nóminas mensuales del personal.",
        "asset_type": AssetType.VENDOR,
        "owner": "Ana Administradora",
        "criticality": AssetCriticality.HIGH,
        "data_classification": DataClassification.CONFIDENTIAL,
        "status": AssetStatus.ACTIVE,
    },
    {
        "name": "Copia de seguridad histórica (cinta)",
        "description": "Servidor de backups en cinta ya sustituido, pendiente de retirada.",
        "asset_type": AssetType.SERVER,
        "owner": "Alicia Analista",
        "criticality": AssetCriticality.LOW,
        "data_classification": DataClassification.INTERNAL,
        "status": AssetStatus.DECOMMISSIONED,
    },
]

# (título, activo, categoría, amenaza, vulnerabilidad, likelihood, impact, tratamiento,
#  responsable, días hasta revisión, estado, residual_likelihood, residual_impact, comentarios)
DEMO_RISKS = [
    (
        "Fuga de datos de clientes por credenciales débiles",
        "Base de datos de clientes",
        "Ciberseguridad",
        "Atacante externo con acceso a credenciales filtradas",
        "Política de contraseñas débil y ausencia de MFA en el acceso administrativo",
        5,
        5,
        RiskTreatment.MITIGATE,
        "Alicia Analista",
        20,
        RiskStatus.IN_TREATMENT,
        2,
        5,
        "Se está desplegando MFA para todos los accesos administrativos.",
    ),
    (
        "Interrupción del portal de clientes por caída del proveedor cloud",
        "Portal de Clientes (Web)",
        "Continuidad de negocio",
        "Indisponibilidad del proveedor de infraestructura cloud",
        "No existe plan de contingencia multi-región",
        2,
        5,
        RiskTreatment.MITIGATE,
        "Gonzalo Gestor GRC",
        45,
        RiskStatus.IN_EVALUATION,
        None,
        None,
        None,
    ),
    (
        "Fraude en pasarela de pagos por manipulación de transacciones",
        "Pasarela de pagos",
        "Ciberseguridad",
        "Atacante que manipula peticiones de pago desde el cliente",
        "Validación insuficiente de importes en el servidor",
        3,
        5,
        RiskTreatment.MITIGATE,
        "Gonzalo Gestor GRC",
        15,
        RiskStatus.IDENTIFIED,
        None,
        None,
        None,
    ),
    (
        "Pérdida de portátil corporativo con datos sin cifrar",
        "Portátiles corporativos",
        "Ciberseguridad",
        "Robo o extravío de un portátil fuera de las instalaciones",
        "El cifrado de disco no está activado en todos los equipos",
        3,
        3,
        RiskTreatment.MITIGATE,
        "Alicia Analista",
        30,
        RiskStatus.IN_TREATMENT,
        1,
        3,
        "Despliegue de cifrado de disco en curso mediante la política de MDM.",
    ),
    (
        "Acceso no autorizado por la VPN por fuga de certificados",
        "VPN de acceso remoto",
        "Ciberseguridad",
        "Ex-empleado o tercero con certificado de VPN no revocado",
        "El proceso de baja de empleados no revoca certificados de forma inmediata",
        3,
        4,
        RiskTreatment.MITIGATE,
        "Gonzalo Gestor GRC",
        25,
        RiskStatus.IN_EVALUATION,
        None,
        None,
        None,
    ),
    (
        "Incumplimiento contractual del proveedor de nóminas",
        "Proveedor de nóminas externo",
        "Terceros",
        "Incumplimiento de las cláusulas de protección de datos por el proveedor",
        "No se audita anualmente al proveedor externo",
        2,
        4,
        RiskTreatment.TRANSFER,
        "Ana Administradora",
        60,
        RiskStatus.ACCEPTED,
        None,
        None,
        "Riesgo transferido contractualmente al proveedor; revisión anual programada.",
    ),
    (
        "Errores en el alta de empleados por proceso manual",
        "Proceso de alta de empleados",
        "Operacional",
        "Error humano en la asignación de permisos durante el onboarding",
        "El proceso de alta no está automatizado ni checklisteado",
        3,
        2,
        RiskTreatment.MITIGATE,
        "Ana Administradora",
        40,
        RiskStatus.IDENTIFIED,
        None,
        None,
        None,
    ),
    (
        "Acceso indebido a documentación interna compartida",
        "Servidor de ficheros interno",
        "Ciberseguridad",
        "Empleado con permisos excesivos accede a documentación fuera de su ámbito",
        "Permisos de carpetas compartidas no revisados periódicamente",
        3,
        2,
        RiskTreatment.MITIGATE,
        "Alicia Analista",
        50,
        RiskStatus.IN_EVALUATION,
        None,
        None,
        None,
    ),
    (
        "Datos residuales en equipo de backup retirado",
        "Copia de seguridad histórica (cinta)",
        "Ciberseguridad",
        "Recuperación de datos desde soportes retirados sin destrucción segura",
        "No existe procedimiento formal de destrucción segura de soportes",
        2,
        3,
        RiskTreatment.MITIGATE,
        "Alicia Analista",
        10,
        RiskStatus.IN_TREATMENT,
        1,
        2,
        "Programada la destrucción certificada de los soportes en las próximas semanas.",
    ),
    (
        "Riesgo reputacional por incidente de seguridad público",
        None,
        "Reputacional",
        "Difusión pública de un incidente de seguridad mal gestionado",
        "No existe un plan de comunicación de crisis definido",
        2,
        4,
        RiskTreatment.ACCEPT,
        "Ana Administradora",
        90,
        RiskStatus.ACCEPTED,
        None,
        None,
        "Riesgo aceptado por dirección a la espera de definir el plan de comunicación.",
    ),
    (
        "Pérdida de material de oficina por gestión manual de inventario",
        None,
        "Operacional",
        "Extravío ocasional de pequeño material de oficina",
        "El inventario de material de oficina se lleva en una hoja de cálculo manual",
        2,
        2,
        RiskTreatment.ACCEPT,
        "Ana Administradora",
        120,
        RiskStatus.ACCEPTED,
        None,
        None,
        "Impacto económico irrelevante; se acepta sin plan de tratamiento adicional.",
    ),
]

# Subconjunto reducido y representativo de ISO 27001 (no reproduce el estándar completo).
DEMO_ISO_REQUIREMENTS = [
    ("A.5.1", "Políticas de seguridad de la información", "Controles organizativos"),
    ("A.5.15", "Control de acceso", "Controles organizativos"),
    ("A.5.23", "Seguridad de la información en el uso de servicios en la nube", "Controles organizativos"),
    ("A.6.3", "Concienciación, formación y capacitación en seguridad de la información", "Controles de personas"),
    ("A.8.5", "Autenticación segura", "Controles tecnológicos"),
    ("A.8.12", "Prevención de fuga de datos", "Controles tecnológicos"),
    ("A.8.13", "Copias de seguridad de la información", "Controles tecnológicos"),
    ("A.8.24", "Uso de criptografía", "Controles tecnológicos"),
]

# Subconjunto reducido y representativo de NIST CSF (no reproduce el estándar completo).
DEMO_NIST_REQUIREMENTS = [
    ("ID.AM-1", "Inventario de activos físicos", "Identify (ID)"),
    ("PR.AC-1", "Gestión de identidades y credenciales", "Protect (PR)"),
    ("PR.DS-1", "Protección de datos en reposo", "Protect (PR)"),
    ("PR.AT-1", "Formación en concienciación de seguridad", "Protect (PR)"),
    ("DE.CM-1", "Monitorización continua de la red", "Detect (DE)"),
    ("RS.RP-1", "Ejecución del plan de respuesta a incidentes", "Respond (RS)"),
    ("RC.RP-1", "Ejecución del plan de recuperación", "Recover (RC)"),
]

# (control_id, nombre, objetivo, categoría, responsable, estado, frecuencia)
DEMO_CONTROLS = [
    (
        "CTRL-001",
        "Autenticación multifactor (MFA)",
        "Reducir el riesgo de acceso no autorizado por robo de credenciales.",
        "Control de acceso",
        "Alicia Analista",
        ControlStatus.PARTIALLY_IMPLEMENTED,
        ControlFrequency.CONTINUOUS,
    ),
    (
        "CTRL-002",
        "Revisión periódica de permisos",
        "Garantizar que los permisos de acceso reflejan las necesidades actuales del puesto.",
        "Control de acceso",
        "Alicia Analista",
        ControlStatus.PARTIALLY_IMPLEMENTED,
        ControlFrequency.QUARTERLY,
    ),
    (
        "CTRL-003",
        "Cifrado de discos en portátiles",
        "Proteger la información en caso de pérdida o robo de un equipo.",
        "Protección de datos",
        "Alicia Analista",
        ControlStatus.PARTIALLY_IMPLEMENTED,
        ControlFrequency.CONTINUOUS,
    ),
    (
        "CTRL-004",
        "Copias de seguridad periódicas",
        "Garantizar la disponibilidad y recuperación de la información ante incidentes.",
        "Continuidad de negocio",
        "Gonzalo Gestor GRC",
        ControlStatus.IMPLEMENTED,
        ControlFrequency.DAILY,
    ),
    (
        "CTRL-005",
        "Gestión de vulnerabilidades",
        "Detectar y corregir vulnerabilidades técnicas antes de que sean explotadas.",
        "Ciberseguridad",
        "Gonzalo Gestor GRC",
        ControlStatus.PARTIALLY_IMPLEMENTED,
        ControlFrequency.MONTHLY,
    ),
    (
        "CTRL-006",
        "Formación y concienciación en seguridad",
        "Reducir el riesgo de error humano mediante formación periódica del personal.",
        "Recursos humanos",
        "Ana Administradora",
        ControlStatus.IMPLEMENTED,
        ControlFrequency.ANNUAL,
    ),
    (
        "CTRL-007",
        "Revisión de proveedores críticos",
        "Garantizar que los proveedores externos cumplen requisitos mínimos de seguridad.",
        "Terceros",
        "Ana Administradora",
        ControlStatus.NOT_IMPLEMENTED,
        ControlFrequency.ANNUAL,
    ),
    (
        "CTRL-008",
        "Destrucción segura de soportes",
        "Evitar la recuperación de información desde soportes de almacenamiento retirados.",
        "Protección de datos",
        "Alicia Analista",
        ControlStatus.NOT_IMPLEMENTED,
        ControlFrequency.AD_HOC,
    ),
    (
        "CTRL-009",
        "Plan de respuesta a incidentes",
        "Asegurar una respuesta coordinada y a tiempo ante incidentes de seguridad.",
        "Continuidad de negocio",
        "Gonzalo Gestor GRC",
        ControlStatus.PARTIALLY_IMPLEMENTED,
        ControlFrequency.ANNUAL,
    ),
    (
        "CTRL-010",
        "Verificación biométrica en accesos físicos",
        "Reforzar el control de acceso físico a instalaciones propias.",
        "Control de acceso",
        "Ana Administradora",
        ControlStatus.NOT_APPLICABLE,
        ControlFrequency.AD_HOC,
    ),
    (
        "CTRL-011",
        "Segmentación de red de producción",
        "Aislar los sistemas críticos de producción del resto de la red corporativa.",
        "Ciberseguridad",
        "Gonzalo Gestor GRC",
        ControlStatus.IMPLEMENTED,
        ControlFrequency.CONTINUOUS,
    ),
]

# control_id -> lista de nombres de activos
DEMO_CONTROL_ASSETS = {
    "CTRL-001": ["VPN de acceso remoto", "Base de datos de clientes"],
    "CTRL-002": ["Servidor de ficheros interno"],
    "CTRL-003": ["Portátiles corporativos"],
    "CTRL-004": ["Base de datos de clientes", "Copia de seguridad histórica (cinta)"],
    "CTRL-005": ["Pasarela de pagos", "Portal de Clientes (Web)"],
    "CTRL-007": ["Proveedor de nóminas externo"],
    "CTRL-008": ["Copia de seguridad histórica (cinta)"],
}

# control_id -> lista de títulos de riesgos
DEMO_CONTROL_RISKS = {
    "CTRL-001": ["Fuga de datos de clientes por credenciales débiles"],
    "CTRL-002": ["Acceso indebido a documentación interna compartida"],
    "CTRL-003": ["Pérdida de portátil corporativo con datos sin cifrar"],
    "CTRL-004": ["Interrupción del portal de clientes por caída del proveedor cloud"],
    "CTRL-005": ["Fraude en pasarela de pagos por manipulación de transacciones"],
    "CTRL-007": ["Incumplimiento contractual del proveedor de nóminas"],
    "CTRL-008": ["Datos residuales en equipo de backup retirado"],
    "CTRL-009": ["Riesgo reputacional por incidente de seguridad público"],
}

# control_id -> lista de (short_name framework, código requisito)
DEMO_CONTROL_REQUIREMENTS = {
    "CTRL-001": [("ISO 27001", "A.8.5"), ("NIST CSF", "PR.AC-1")],
    "CTRL-002": [("ISO 27001", "A.5.15"), ("NIST CSF", "PR.AC-1")],
    "CTRL-003": [("ISO 27001", "A.8.24"), ("NIST CSF", "PR.DS-1")],
    "CTRL-004": [("ISO 27001", "A.8.13"), ("NIST CSF", "RC.RP-1")],
    "CTRL-005": [("NIST CSF", "DE.CM-1")],
    "CTRL-006": [("ISO 27001", "A.6.3"), ("NIST CSF", "PR.AT-1")],
    "CTRL-008": [("ISO 27001", "A.8.12")],
    "CTRL-009": [("NIST CSF", "RS.RP-1")],
}

# (short_name origen, código origen, short_name destino, código destino, notas)
DEMO_MAPPINGS = [
    (
        "ISO 27001",
        "A.8.5",
        "NIST CSF",
        "PR.AC-1",
        "Ambos cubren la autenticación segura de usuarios.",
    ),
    (
        "ISO 27001",
        "A.8.13",
        "NIST CSF",
        "RC.RP-1",
        "La copia de seguridad apoya la capacidad de recuperación, no es una equivalencia exacta.",
    ),
    (
        "ISO 27001",
        "A.8.24",
        "NIST CSF",
        "PR.DS-1",
        "El cifrado es un control habitual para proteger datos en reposo.",
    ),
    (
        "ISO 27001",
        "A.6.3",
        "NIST CSF",
        "PR.AT-1",
        "Ambos marcos exigen formación periódica del personal.",
    ),
    (
        "ISO 27001",
        "A.5.15",
        "NIST CSF",
        "PR.AC-1",
        "Corresponden a la gestión de acceso; no implica equivalencia legal automática.",
    ),
]


def _generar_png_minimo() -> bytes:
    """Genera un PNG 1x1 válido (un píxel rojo), sin depender de librerías de imagen."""
    firma = b"\x89PNG\r\n\x1a\n"

    def chunk(tipo: bytes, datos: bytes) -> bytes:
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos))

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)  # 1x1, 8 bits, color RGB
    raw = b"\x00" + bytes([200, 30, 30])  # filtro "none" + un píxel rojo
    idat = zlib.compress(raw)
    return firma + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _generar_pdf_minimo(texto: str) -> bytes:
    """Genera un PDF mínimo pero válido con una línea de texto, sin librerías externas."""
    contenido = f"BT /F1 12 Tf 72 700 Td ({texto}) Tj ET".encode("latin-1", "replace")
    objetos = [
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj",
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj",
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj",
        b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj",
        b"5 0 obj<</Length "
        + str(len(contenido)).encode()
        + b">>stream\n"
        + contenido
        + b"\nendstream endobj",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for obj in objetos:
        offsets.append(len(pdf))
        pdf += obj + b"\n"
    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += f"trailer<</Size {len(objetos) + 1}/Root 1 0 R>>\nstartxref\n{xref_offset}\n%%EOF".encode()
    return pdf


def _contenido_politica() -> bytes:
    return (
        "POLÍTICA DE CONTRASEÑAS (documento ficticio de demostración)\n\n"
        "1. Longitud mínima: 12 caracteres.\n"
        "2. Autenticación multifactor (MFA) obligatoria en accesos administrativos.\n"
        "3. Revisión de la política: anual.\n\n"
        "Este documento es ficticio y se genera únicamente con fines de demostración."
    ).encode("utf-8")


def _contenido_checklist_csv() -> bytes:
    filas = [
        "usuario,departamento,acceso_revisado,resultado",
        "ana.demo,Direccion,si,conforme",
        "gonzalo.demo,GRC,si,conforme",
        "alicia.demo,IT,si,conforme",
        "invitado.demo,Externo,si,acceso revocado",
    ]
    return "\n".join(filas).encode("utf-8")


def _contenido_informe() -> bytes:
    return (
        "INFORME DE CIFRADO DE DISCOS - LOTE 1 (documento ficticio)\n\n"
        "Equipos revisados: 24\n"
        "Equipos con cifrado activo: 19\n"
        "Equipos pendientes: 5\n\n"
        "Documento ficticio generado únicamente con fines de demostración."
    ).encode("utf-8")


@dataclass
class EvidenceSeedItem:
    name: str
    description: str
    filename: str
    contenido: bytes
    classification: DataClassification
    evidence_type: str
    dias_recopilacion: int
    dias_expiracion: int | None
    control_id: str | None
    risk_title: str | None
    asset_name: str | None
    uploaded_by: str
    requirements: list[tuple[str, str]] = field(default_factory=list)


# control_id, risk_title y asset_name son opcionales: no toda evidencia tiene
# por qué relacionarse con las tres entidades a la vez.
DEMO_EVIDENCE: list[EvidenceSeedItem] = [
    EvidenceSeedItem(
        name="Política de contraseñas (borrador)",
        description="Borrador de la política de contraseñas y MFA para accesos administrativos.",
        filename="politica_contrasenas.txt",
        contenido=_contenido_politica(),
        classification=DataClassification.INTERNAL,
        evidence_type="Política",
        dias_recopilacion=60,
        dias_expiracion=305,
        control_id="CTRL-001",
        risk_title="Fuga de datos de clientes por credenciales débiles",
        asset_name=None,
        requirements=[("ISO 27001", "A.8.5"), ("NIST CSF", "PR.AC-1")],
        uploaded_by="Alicia Analista",
    ),
    EvidenceSeedItem(
        name="Checklist de revisión de accesos - T1",
        description="Checklist de la revisión trimestral de permisos de acceso.",
        filename="checklist_revision_accesos_t1.csv",
        contenido=_contenido_checklist_csv(),
        classification=DataClassification.INTERNAL,
        evidence_type="Checklist",
        dias_recopilacion=20,
        dias_expiracion=None,
        control_id="CTRL-002",
        risk_title=None,
        asset_name="Servidor de ficheros interno",
        requirements=[("ISO 27001", "A.5.15")],
        uploaded_by="Alicia Analista",
    ),
    EvidenceSeedItem(
        name="Informe de cifrado de discos - lote 1",
        description="Resultado de la campaña de activación de cifrado de disco en portátiles.",
        filename="informe_cifrado_discos_lote1.txt",
        contenido=_contenido_informe(),
        classification=DataClassification.CONFIDENTIAL,
        evidence_type="Informe",
        dias_recopilacion=15,
        dias_expiracion=None,
        control_id="CTRL-003",
        risk_title="Pérdida de portátil corporativo con datos sin cifrar",
        asset_name="Portátiles corporativos",
        requirements=[("ISO 27001", "A.8.24"), ("NIST CSF", "PR.DS-1")],
        uploaded_by="Alicia Analista",
    ),
    EvidenceSeedItem(
        name="Captura de configuración de copias de seguridad",
        description="Captura de pantalla ficticia de la configuración del servicio de backups.",
        filename="captura_configuracion_backups.png",
        contenido=_generar_png_minimo(),
        classification=DataClassification.INTERNAL,
        evidence_type="Captura de pantalla",
        dias_recopilacion=5,
        dias_expiracion=None,
        control_id="CTRL-004",
        risk_title=None,
        asset_name="Base de datos de clientes",
        requirements=[("ISO 27001", "A.8.13")],
        uploaded_by="Gonzalo Gestor GRC",
    ),
    EvidenceSeedItem(
        name="Registro de formación en seguridad 2026",
        description="Registro ficticio de asistencia a la formación anual de concienciación en seguridad.",
        filename="registro_formacion_seguridad_2026.pdf",
        contenido=_generar_pdf_minimo("Registro ficticio de formacion en seguridad 2026"),
        classification=DataClassification.INTERNAL,
        evidence_type="Registro",
        dias_recopilacion=40,
        dias_expiracion=325,
        control_id="CTRL-006",
        risk_title=None,
        asset_name=None,
        requirements=[("ISO 27001", "A.6.3"), ("NIST CSF", "PR.AT-1")],
        uploaded_by="Ana Administradora",
    ),
    EvidenceSeedItem(
        name="Certificado de destrucción segura de soportes",
        description="Certificado ficticio de destrucción segura de los soportes de backup retirados.",
        filename="certificado_destruccion_soportes.pdf",
        contenido=_generar_pdf_minimo("Certificado ficticio de destruccion segura de soportes"),
        classification=DataClassification.CONFIDENTIAL,
        evidence_type="Certificado",
        dias_recopilacion=45,
        dias_expiracion=-10,  # ya caducado, para poder demostrar el filtro de caducadas
        control_id="CTRL-008",
        risk_title="Datos residuales en equipo de backup retirado",
        asset_name="Copia de seguridad histórica (cinta)",
        requirements=[("ISO 27001", "A.8.12")],
        uploaded_by="Alicia Analista",
    ),
]


@dataclass
class ActionSeedItem:
    action_id: str
    title: str
    description: str
    owner: str
    priority: AssetCriticality
    status: ActionStatus
    dias_vencimiento: int  # relativo a HOY; puede ser negativo (ya vencida)
    dias_completada: int | None = None  # si status == COMPLETED, hace cuántos días
    completion_notes: str | None = None


@dataclass
class FindingSeedItem:
    finding_id: str
    title: str
    description: str
    finding_type: FindingType
    severity: AssetCriticality
    source: FindingSource
    status: FindingStatus
    owner: str
    dias_descubrimiento: int
    dias_vencimiento: int
    control_id: str | None = None
    risk_title: str | None = None
    asset_name: str | None = None
    requirement_key: tuple[str, str] | None = None
    evidence_name: str | None = None
    dias_cierre: int | None = None  # si status == CLOSED, hace cuántos días se cerró
    resolution_summary: str | None = None
    actions: list[ActionSeedItem] = field(default_factory=list)


DEMO_FINDINGS: list[FindingSeedItem] = [
    FindingSeedItem(
        finding_id="FND-001",
        title="Deficiencia en la política de contraseñas",
        description="La política de contraseñas no exige MFA en accesos administrativos.",
        finding_type=FindingType.CONTROL_REVIEW,
        severity=AssetCriticality.HIGH,
        source=FindingSource.CONTROL,
        status=FindingStatus.REMEDIATION,
        owner="Alicia Analista",
        dias_descubrimiento=25,
        dias_vencimiento=15,
        control_id="CTRL-001",
        risk_title="Fuga de datos de clientes por credenciales débiles",
        requirement_key=("ISO 27001", "A.8.5"),
        evidence_name="Política de contraseñas (borrador)",
        actions=[
            ActionSeedItem(
                action_id="ACT-001",
                title="Desplegar MFA en todos los accesos administrativos",
                description="Activar autenticación multifactor para el personal con acceso administrativo.",
                owner="Alicia Analista",
                priority=AssetCriticality.HIGH,
                status=ActionStatus.IN_PROGRESS,
                dias_vencimiento=10,
            ),
        ],
    ),
    FindingSeedItem(
        finding_id="FND-002",
        title="Revisión de permisos pendiente",
        description="La revisión trimestral de permisos del servidor de ficheros no se ha completado.",
        finding_type=FindingType.AUDIT_INTERNAL,
        severity=AssetCriticality.MEDIUM,
        source=FindingSource.AUDIT,
        status=FindingStatus.OPEN,
        owner="Alicia Analista",
        dias_descubrimiento=10,
        dias_vencimiento=20,
        control_id="CTRL-002",
        asset_name="Servidor de ficheros interno",
        actions=[
            ActionSeedItem(
                action_id="ACT-002",
                title="Completar la revisión trimestral de permisos",
                description="Revisar y depurar los permisos de las carpetas compartidas.",
                owner="Alicia Analista",
                priority=AssetCriticality.MEDIUM,
                status=ActionStatus.PENDING,
                dias_vencimiento=20,
            ),
        ],
    ),
    FindingSeedItem(
        finding_id="FND-003",
        title="Evidencia de destrucción de soportes caducada",
        description="El certificado de destrucción segura de soportes ha caducado y debe renovarse.",
        finding_type=FindingType.COMPLIANCE,
        severity=AssetCriticality.MEDIUM,
        source=FindingSource.COMPLIANCE,
        status=FindingStatus.PENDING_VALIDATION,
        owner="Alicia Analista",
        dias_descubrimiento=5,
        dias_vencimiento=10,
        control_id="CTRL-008",
        evidence_name="Certificado de destrucción segura de soportes",
        actions=[
            ActionSeedItem(
                action_id="ACT-003",
                title="Renovar el certificado de destrucción segura",
                description="Solicitar al proveedor un nuevo certificado de destrucción de soportes.",
                owner="Alicia Analista",
                priority=AssetCriticality.MEDIUM,
                status=ActionStatus.BLOCKED,
                dias_vencimiento=7,
            ),
        ],
    ),
    FindingSeedItem(
        finding_id="FND-004",
        title="Control de gestión de vulnerabilidades parcialmente implementado",
        description="No existe un proceso periódico de escaneo de vulnerabilidades en la pasarela de pagos.",
        finding_type=FindingType.CONTROL_REVIEW,
        severity=AssetCriticality.HIGH,
        source=FindingSource.CONTROL,
        status=FindingStatus.OPEN,
        owner="Gonzalo Gestor GRC",
        dias_descubrimiento=60,
        dias_vencimiento=-10,
        control_id="CTRL-005",
        risk_title="Fraude en pasarela de pagos por manipulación de transacciones",
        actions=[
            ActionSeedItem(
                action_id="ACT-004",
                title="Implantar escaneo periódico de vulnerabilidades",
                description="Contratar y programar un escaneo mensual de vulnerabilidades.",
                owner="Gonzalo Gestor GRC",
                priority=AssetCriticality.CRITICAL,
                status=ActionStatus.PENDING,
                dias_vencimiento=-5,
            ),
        ],
    ),
    FindingSeedItem(
        finding_id="FND-005",
        title="Hallazgo de auditoría externa sobre respuesta a incidentes",
        description="La auditoría externa detectó que el plan de respuesta a incidentes no se ha probado en el último año.",
        finding_type=FindingType.AUDIT_EXTERNAL,
        severity=AssetCriticality.CRITICAL,
        source=FindingSource.AUDIT,
        status=FindingStatus.UNDER_REVIEW,
        owner="Gonzalo Gestor GRC",
        dias_descubrimiento=20,
        dias_vencimiento=5,
        control_id="CTRL-009",
        risk_title="Riesgo reputacional por incidente de seguridad público",
        actions=[
            ActionSeedItem(
                action_id="ACT-005",
                title="Realizar simulacro de respuesta a incidentes",
                description="Planificar y ejecutar un simulacro con el equipo de respuesta a incidentes.",
                owner="Gonzalo Gestor GRC",
                priority=AssetCriticality.HIGH,
                status=ActionStatus.IN_PROGRESS,
                dias_vencimiento=3,
            ),
        ],
    ),
    FindingSeedItem(
        finding_id="FND-006",
        title="Proveedor de nóminas pendiente de revisión anual",
        description="No se ha realizado la auditoría anual programada al proveedor de nóminas.",
        finding_type=FindingType.VENDOR,
        severity=AssetCriticality.LOW,
        source=FindingSource.VENDOR,
        status=FindingStatus.CLOSED,
        owner="Ana Administradora",
        dias_descubrimiento=90,
        dias_vencimiento=-30,
        control_id="CTRL-007",
        risk_title="Incumplimiento contractual del proveedor de nóminas",
        dias_cierre=5,
        resolution_summary=(
            "Se ha completado la revisión anual del proveedor y se ha renovado el contrato "
            "con las cláusulas de protección de datos actualizadas."
        ),
        actions=[
            ActionSeedItem(
                action_id="ACT-006",
                title="Revisar cláusulas de protección de datos del contrato",
                description="Actualizar el contrato con el proveedor de nóminas con cláusulas de protección de datos.",
                owner="Ana Administradora",
                priority=AssetCriticality.LOW,
                status=ActionStatus.COMPLETED,
                dias_vencimiento=-20,
                dias_completada=10,
                completion_notes="Contrato actualizado y firmado por ambas partes.",
            ),
        ],
    ),
]


def _crear_organizacion_y_usuarios(db) -> tuple[Organization, dict[str, User]]:
    organizacion = db.query(Organization).filter_by(name="Acme Security Labs").first()
    if organizacion is None:
        organizacion = Organization(name="Acme Security Labs")
        db.add(organizacion)
        db.commit()
        db.refresh(organizacion)
        print(f"Organización creada: {organizacion.name} ({organizacion.id})")
    else:
        print(f"Organización ya existente: {organizacion.name} ({organizacion.id})")

    usuarios_por_nombre: dict[str, User] = {}
    for email, full_name, role in DEMO_USERS:
        usuario = db.query(User).filter_by(email=email).first()
        if usuario is None:
            usuario = User(
                organization_id=organizacion.id,
                email=email,
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name=full_name,
                role=role,
            )
            db.add(usuario)
            db.commit()
            db.refresh(usuario)
            print(f"Usuario creado: {email} ({role.value})")
        else:
            print(f"Usuario ya existente: {email}")
        usuarios_por_nombre[full_name] = usuario

    return organizacion, usuarios_por_nombre


def _crear_activos(db, organizacion: Organization) -> dict[str, Asset]:
    activos_por_nombre: dict[str, Asset] = {}
    for datos in DEMO_ASSETS:
        activo = (
            db.query(Asset)
            .filter_by(organization_id=organizacion.id, name=datos["name"])
            .first()
        )
        if activo is None:
            activo = Asset(organization_id=organizacion.id, **datos)
            db.add(activo)
            db.commit()
            db.refresh(activo)
            print(f"Activo creado: {activo.name}")
        else:
            print(f"Activo ya existente: {activo.name}")
        activos_por_nombre[activo.name] = activo
    return activos_por_nombre


def _crear_riesgos(
    db, organizacion: Organization, activos_por_nombre: dict[str, Asset]
) -> dict[str, Risk]:
    riesgos_por_titulo: dict[str, Risk] = {}
    for (
        title,
        nombre_activo,
        category,
        threat,
        vulnerability,
        likelihood,
        impact,
        treatment,
        owner,
        dias_revision,
        status_,
        residual_likelihood,
        residual_impact,
        comments,
    ) in DEMO_RISKS:
        riesgo = db.query(Risk).filter_by(organization_id=organizacion.id, title=title).first()
        if riesgo is None:
            activo = activos_por_nombre.get(nombre_activo) if nombre_activo else None
            residual_score = (
                calcular_score(residual_likelihood, residual_impact)
                if residual_likelihood is not None and residual_impact is not None
                else None
            )
            riesgo = Risk(
                organization_id=organizacion.id,
                title=title,
                asset_id=activo.id if activo else None,
                category=category,
                threat=threat,
                vulnerability=vulnerability,
                likelihood=likelihood,
                impact=impact,
                inherent_score=calcular_score(likelihood, impact),
                treatment=treatment,
                owner=owner,
                review_date=HOY + timedelta(days=dias_revision),
                status=status_,
                residual_likelihood=residual_likelihood,
                residual_impact=residual_impact,
                residual_score=residual_score,
                comments=comments,
            )
            db.add(riesgo)
            db.commit()
            db.refresh(riesgo)
            print(f"Riesgo creado: {title}")
        else:
            print(f"Riesgo ya existente: {title}")
        riesgos_por_titulo[title] = riesgo
    return riesgos_por_titulo


def _crear_frameworks_y_requisitos(
    db, organizacion: Organization
) -> tuple[dict[str, Framework], dict[tuple[str, str], Requirement]]:
    frameworks_por_short_name: dict[str, Framework] = {}
    requisitos_por_clave: dict[tuple[str, str], Requirement] = {}

    definiciones_framework = [
        (
            "ISO/IEC 27001:2022",
            "ISO 27001",
            "Sistema de gestión de seguridad de la información. Subconjunto demo de referencias del Anexo A.",
            "2022",
            DEMO_ISO_REQUIREMENTS,
        ),
        (
            "NIST Cybersecurity Framework",
            "NIST CSF",
            "Marco de ciberseguridad del NIST. Subconjunto demo de subcategorías representativas.",
            "2.0",
            DEMO_NIST_REQUIREMENTS,
        ),
    ]

    for name, short_name, description, version, requisitos in definiciones_framework:
        framework = (
            db.query(Framework)
            .filter_by(organization_id=organizacion.id, short_name=short_name)
            .first()
        )
        if framework is None:
            framework = Framework(
                organization_id=organizacion.id,
                name=name,
                short_name=short_name,
                description=description,
                version=version,
                status=FrameworkStatus.ACTIVE,
            )
            db.add(framework)
            db.commit()
            db.refresh(framework)
            print(f"Marco de cumplimiento creado: {short_name}")
        else:
            print(f"Marco de cumplimiento ya existente: {short_name}")
        frameworks_por_short_name[short_name] = framework

        for code, req_name, category in requisitos:
            requisito = (
                db.query(Requirement)
                .filter_by(framework_id=framework.id, code=code)
                .first()
            )
            if requisito is None:
                requisito = Requirement(
                    organization_id=organizacion.id,
                    framework_id=framework.id,
                    code=code,
                    name=req_name,
                    category=category,
                )
                db.add(requisito)
                db.commit()
                db.refresh(requisito)
                print(f"Requisito creado: {short_name} {code}")
            else:
                print(f"Requisito ya existente: {short_name} {code}")
            requisitos_por_clave[(short_name, code)] = requisito

    return frameworks_por_short_name, requisitos_por_clave


def _crear_controles(db, organizacion: Organization) -> dict[str, Control]:
    controles_por_codigo: dict[str, Control] = {}
    for control_id, name, objective, category, owner, status_, frequency in DEMO_CONTROLS:
        control = (
            db.query(Control)
            .filter_by(organization_id=organizacion.id, control_id=control_id)
            .first()
        )
        if control is None:
            control = Control(
                organization_id=organizacion.id,
                control_id=control_id,
                name=name,
                objective=objective,
                category=category,
                owner=owner,
                status=status_,
                frequency=frequency,
            )
            db.add(control)
            db.commit()
            db.refresh(control)
            print(f"Control creado: {control_id} — {name}")
        else:
            print(f"Control ya existente: {control_id}")
        controles_por_codigo[control_id] = control
    return controles_por_codigo


def _vincular_relaciones(
    db,
    controles_por_codigo: dict[str, Control],
    activos_por_nombre: dict[str, Asset],
    riesgos_por_titulo: dict[str, Risk],
    requisitos_por_clave: dict[tuple[str, str], Requirement],
) -> None:
    for control_id, nombres_activos in DEMO_CONTROL_ASSETS.items():
        control = controles_por_codigo[control_id]
        for nombre_activo in nombres_activos:
            activo = activos_por_nombre[nombre_activo]
            if activo not in control.assets:
                control.assets.append(activo)

    for control_id, titulos_riesgos in DEMO_CONTROL_RISKS.items():
        control = controles_por_codigo[control_id]
        for titulo in titulos_riesgos:
            riesgo = riesgos_por_titulo[titulo]
            if riesgo not in control.risks:
                control.risks.append(riesgo)

    for control_id, claves_requisitos in DEMO_CONTROL_REQUIREMENTS.items():
        control = controles_por_codigo[control_id]
        for clave in claves_requisitos:
            requisito = requisitos_por_clave[clave]
            if requisito not in control.requirements:
                control.requirements.append(requisito)

    db.commit()
    print("Relaciones control-activo, control-riesgo y control-requisito vinculadas.")


def _crear_mappings(
    db, organizacion: Organization, requisitos_por_clave: dict[tuple[str, str], Requirement]
) -> None:
    for origen_short, origen_codigo, destino_short, destino_codigo, notes in DEMO_MAPPINGS:
        origen = requisitos_por_clave[(origen_short, origen_codigo)]
        destino = requisitos_por_clave[(destino_short, destino_codigo)]

        ya_existe = (
            db.query(FrameworkMapping)
            .filter_by(
                organization_id=organizacion.id,
                source_requirement_id=origen.id,
                target_requirement_id=destino.id,
            )
            .first()
        )
        if ya_existe is not None:
            print(f"Mapping ya existente: {origen_short} {origen_codigo} <-> {destino_short} {destino_codigo}")
            continue

        mapping = FrameworkMapping(
            organization_id=organizacion.id,
            source_requirement_id=origen.id,
            target_requirement_id=destino.id,
            notes=notes,
        )
        db.add(mapping)
        db.commit()
        print(f"Mapping creado: {origen_short} {origen_codigo} <-> {destino_short} {destino_codigo}")


def _crear_evidencias(
    db,
    organizacion: Organization,
    usuarios_por_nombre: dict[str, User],
    controles_por_codigo: dict[str, Control],
    riesgos_por_titulo: dict[str, Risk],
    activos_por_nombre: dict[str, Asset],
    requisitos_por_clave: dict[tuple[str, str], Requirement],
) -> dict[str, Evidence]:
    evidencias_por_nombre: dict[str, Evidence] = {}
    for item in DEMO_EVIDENCE:
        ya_existe = (
            db.query(Evidence).filter_by(organization_id=organizacion.id, name=item.name).first()
        )
        if ya_existe is not None:
            print(f"Evidencia ya existente: {item.name}")
            evidencias_por_nombre[item.name] = ya_existe
            continue

        nombre_saneado = sanear_nombre_original(item.filename)
        mime_type, extension = determinar_tipo_seguro(
            nombre_saneado, item.contenido, settings.max_evidence_file_size_bytes
        )
        sha256_hex = hashlib.sha256(item.contenido).hexdigest()
        storage_key = storage_service.generar_storage_key(organizacion.id, extension)
        storage_service.guardar(storage_key, item.contenido)

        uploader = usuarios_por_nombre.get(item.uploaded_by)
        expires_at = HOY + timedelta(days=item.dias_expiracion) if item.dias_expiracion is not None else None

        evidencia = Evidence(
            organization_id=organizacion.id,
            name=item.name,
            description=item.description,
            original_filename=nombre_saneado,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size=len(item.contenido),
            sha256=sha256_hex,
            classification=item.classification,
            evidence_type=item.evidence_type,
            collected_at=HOY - timedelta(days=item.dias_recopilacion),
            expires_at=expires_at,
            uploaded_by_id=uploader.id if uploader else None,
        )

        if item.control_id:
            control = controles_por_codigo.get(item.control_id)
            if control is not None:
                evidencia.controls.append(control)
        if item.risk_title:
            riesgo = riesgos_por_titulo.get(item.risk_title)
            if riesgo is not None:
                evidencia.risks.append(riesgo)
        if item.asset_name:
            activo = activos_por_nombre.get(item.asset_name)
            if activo is not None:
                evidencia.assets.append(activo)
        for clave in item.requirements:
            requisito = requisitos_por_clave.get(clave)
            if requisito is not None:
                evidencia.requirements.append(requisito)

        db.add(evidencia)
        db.commit()
        print(f"Evidencia creada: {item.name} ({nombre_saneado}, {len(item.contenido)} bytes)")
        evidencias_por_nombre[item.name] = evidencia

    return evidencias_por_nombre


def _crear_hallazgos_y_acciones(
    db,
    organizacion: Organization,
    usuarios_por_nombre: dict[str, User],
    controles_por_codigo: dict[str, Control],
    riesgos_por_titulo: dict[str, Risk],
    activos_por_nombre: dict[str, Asset],
    requisitos_por_clave: dict[tuple[str, str], Requirement],
    evidencias_por_nombre: dict[str, Evidence],
) -> dict[str, Finding]:
    hallazgos_por_codigo: dict[str, Finding] = {}
    for item in DEMO_FINDINGS:
        hallazgo = (
            db.query(Finding)
            .filter_by(organization_id=organizacion.id, finding_id=item.finding_id)
            .first()
        )
        if hallazgo is None:
            closed_at = HOY - timedelta(days=item.dias_cierre) if item.dias_cierre is not None else None
            propietario = usuarios_por_nombre.get(item.owner)
            hallazgo = Finding(
                organization_id=organizacion.id,
                finding_id=item.finding_id,
                title=item.title,
                description=item.description,
                finding_type=item.finding_type,
                severity=item.severity,
                status=item.status,
                source=item.source,
                owner=item.owner,
                discovered_at=HOY - timedelta(days=item.dias_descubrimiento),
                due_date=HOY + timedelta(days=item.dias_vencimiento),
                closed_at=closed_at,
                resolution_summary=item.resolution_summary,
                created_by_id=propietario.id if propietario else None,
            )

            if item.control_id:
                control = controles_por_codigo.get(item.control_id)
                if control is not None:
                    hallazgo.controls.append(control)
            if item.risk_title:
                riesgo = riesgos_por_titulo.get(item.risk_title)
                if riesgo is not None:
                    hallazgo.risks.append(riesgo)
            if item.asset_name:
                activo = activos_por_nombre.get(item.asset_name)
                if activo is not None:
                    hallazgo.assets.append(activo)
            if item.requirement_key:
                requisito = requisitos_por_clave.get(item.requirement_key)
                if requisito is not None:
                    hallazgo.requirements.append(requisito)
            if item.evidence_name:
                evidencia = evidencias_por_nombre.get(item.evidence_name)
                if evidencia is not None:
                    hallazgo.evidence.append(evidencia)

            db.add(hallazgo)
            db.commit()
            print(f"Hallazgo creado: {item.finding_id} — {item.title}")
        else:
            print(f"Hallazgo ya existente: {item.finding_id}")

        hallazgos_por_codigo[item.finding_id] = hallazgo

        for accion_item in item.actions:
            accion = (
                db.query(RemediationAction)
                .filter_by(organization_id=organizacion.id, action_id=accion_item.action_id)
                .first()
            )
            if accion is not None:
                print(f"Acción ya existente: {accion_item.action_id}")
                continue

            completed_at = (
                HOY - timedelta(days=accion_item.dias_completada)
                if accion_item.dias_completada is not None
                else None
            )
            propietario_accion = usuarios_por_nombre.get(accion_item.owner)
            accion = RemediationAction(
                organization_id=organizacion.id,
                finding_id=hallazgo.id,
                action_id=accion_item.action_id,
                title=accion_item.title,
                description=accion_item.description,
                owner=accion_item.owner,
                status=accion_item.status,
                priority=accion_item.priority,
                due_date=HOY + timedelta(days=accion_item.dias_vencimiento),
                completed_at=completed_at,
                completion_notes=accion_item.completion_notes,
                created_by_id=propietario_accion.id if propietario_accion else None,
            )
            db.add(accion)
            db.commit()
            print(f"Acción creada: {accion_item.action_id} — {accion_item.title}")

    return hallazgos_por_codigo


@dataclass
class VendorSeedItem:
    vendor_id: str
    name: str
    legal_name: str
    description: str
    category: str
    owner: str
    criticality: AssetCriticality
    data_classification: DataClassification
    status: VendorStatus
    due_diligence_status: VendorDueDiligenceStatus
    dias_inicio_relacion: int
    dias_fin_contrato: int | None
    dias_ultima_revision: int | None
    dias_proxima_revision: int | None
    risk_titles: list[str] = field(default_factory=list)
    evidence_names: list[str] = field(default_factory=list)
    finding_ids: list[str] = field(default_factory=list)


# Escenarios deliberadamente variados: activo de bajo riesgo, crítico, con datos
# confidenciales, con revisión vencida, con revisión próxima y suspendido/finalizado.
# Nombres claramente ficticios, sin relación con proveedores reales.
DEMO_VENDORS: list[VendorSeedItem] = [
    VendorSeedItem(
        vendor_id="VEN-001",
        name="Global Print Services",
        legal_name="Global Print Services S.L.",
        description="Suministro y mantenimiento de impresoras y consumibles de oficina.",
        category="Suministros de oficina",
        owner="Ana Administradora",
        criticality=AssetCriticality.LOW,
        data_classification=DataClassification.PUBLIC,
        status=VendorStatus.ACTIVE,
        due_diligence_status=VendorDueDiligenceStatus.APPROVED,
        dias_inicio_relacion=400,
        dias_fin_contrato=200,
        dias_ultima_revision=100,
        dias_proxima_revision=265,
    ),
    VendorSeedItem(
        vendor_id="VEN-002",
        name="CloudStack Solutions",
        legal_name="CloudStack Solutions Inc.",
        description="Proveedor de infraestructura cloud (IaaS) para el Portal de Clientes.",
        category="Infraestructura cloud",
        owner="Gonzalo Gestor GRC",
        criticality=AssetCriticality.CRITICAL,
        data_classification=DataClassification.CONFIDENTIAL,
        status=VendorStatus.ACTIVE,
        due_diligence_status=VendorDueDiligenceStatus.APPROVED_WITH_CONDITIONS,
        dias_inicio_relacion=500,
        dias_fin_contrato=180,
        dias_ultima_revision=200,
        dias_proxima_revision=165,
        risk_titles=["Interrupción del portal de clientes por caída del proveedor cloud"],
        evidence_names=["Captura de configuración de copias de seguridad"],
    ),
    VendorSeedItem(
        vendor_id="VEN-003",
        name="Nómina Gestión SL",
        legal_name="Nómina Gestión S.L.",
        description="Gestoría externa que procesa las nóminas mensuales del personal.",
        category="Gestión de nóminas",
        owner="Ana Administradora",
        criticality=AssetCriticality.HIGH,
        data_classification=DataClassification.RESTRICTED,
        status=VendorStatus.ACTIVE,
        due_diligence_status=VendorDueDiligenceStatus.APPROVED,
        dias_inicio_relacion=700,
        dias_fin_contrato=300,
        dias_ultima_revision=30,
        dias_proxima_revision=335,
        risk_titles=["Incumplimiento contractual del proveedor de nóminas"],
        finding_ids=["FND-006"],
    ),
    VendorSeedItem(
        vendor_id="VEN-004",
        name="SecureAudit Partners",
        legal_name="SecureAudit Partners LLP",
        description="Auditoría de seguridad externa y pruebas de intrusión anuales.",
        category="Auditoría de seguridad",
        owner="Gonzalo Gestor GRC",
        criticality=AssetCriticality.MEDIUM,
        data_classification=DataClassification.CONFIDENTIAL,
        status=VendorStatus.ACTIVE,
        due_diligence_status=VendorDueDiligenceStatus.EXPIRED,
        dias_inicio_relacion=600,
        dias_fin_contrato=120,
        dias_ultima_revision=400,
        dias_proxima_revision=-20,
    ),
    VendorSeedItem(
        vendor_id="VEN-005",
        name="DataVault Storage",
        legal_name="DataVault Storage Ltd.",
        description="Almacenamiento externo de copias de seguridad fuera de las instalaciones.",
        category="Almacenamiento de backups",
        owner="Alicia Analista",
        criticality=AssetCriticality.MEDIUM,
        data_classification=DataClassification.CONFIDENTIAL,
        status=VendorStatus.ACTIVE,
        due_diligence_status=VendorDueDiligenceStatus.APPROVED,
        dias_inicio_relacion=300,
        dias_fin_contrato=90,
        dias_ultima_revision=335,
        dias_proxima_revision=15,
        risk_titles=["Datos residuales en equipo de backup retirado"],
        evidence_names=["Certificado de destrucción segura de soportes"],
    ),
    VendorSeedItem(
        vendor_id="VEN-006",
        name="LegacySoft Systems",
        legal_name="LegacySoft Systems Corp.",
        description="Licencia de un sistema de gestión heredado, sustituido y en fase de baja.",
        category="Software heredado",
        owner="Alicia Analista",
        criticality=AssetCriticality.LOW,
        data_classification=DataClassification.INTERNAL,
        status=VendorStatus.TERMINATED,
        due_diligence_status=VendorDueDiligenceStatus.REJECTED,
        dias_inicio_relacion=900,
        dias_fin_contrato=-60,
        dias_ultima_revision=500,
        dias_proxima_revision=None,
    ),
]


def _crear_proveedores(
    db,
    organizacion: Organization,
    usuarios_por_nombre: dict[str, User],
    riesgos_por_titulo: dict[str, Risk],
    evidencias_por_nombre: dict[str, Evidence],
    hallazgos_por_codigo: dict[str, Finding],
) -> None:
    for item in DEMO_VENDORS:
        proveedor = (
            db.query(Vendor).filter_by(organization_id=organizacion.id, vendor_id=item.vendor_id).first()
        )
        if proveedor is not None:
            print(f"Proveedor ya existente: {item.vendor_id}")
            continue

        propietario = usuarios_por_nombre.get(item.owner)
        proveedor = Vendor(
            organization_id=organizacion.id,
            vendor_id=item.vendor_id,
            name=item.name,
            legal_name=item.legal_name,
            description=item.description,
            category=item.category,
            owner=item.owner,
            criticality=item.criticality,
            data_classification=item.data_classification,
            status=item.status,
            due_diligence_status=item.due_diligence_status,
            relationship_start_date=HOY - timedelta(days=item.dias_inicio_relacion),
            contract_end_date=(
                HOY + timedelta(days=item.dias_fin_contrato) if item.dias_fin_contrato is not None else None
            ),
            last_security_review_date=(
                HOY - timedelta(days=item.dias_ultima_revision) if item.dias_ultima_revision is not None else None
            ),
            next_security_review_date=(
                HOY + timedelta(days=item.dias_proxima_revision) if item.dias_proxima_revision is not None else None
            ),
            created_by_id=propietario.id if propietario else None,
        )

        for titulo in item.risk_titles:
            riesgo = riesgos_por_titulo.get(titulo)
            if riesgo is not None:
                proveedor.risks.append(riesgo)
        for nombre in item.evidence_names:
            evidencia = evidencias_por_nombre.get(nombre)
            if evidencia is not None:
                proveedor.evidence.append(evidencia)
        for finding_id in item.finding_ids:
            hallazgo = hallazgos_por_codigo.get(finding_id)
            if hallazgo is not None:
                proveedor.findings.append(hallazgo)

        db.add(proveedor)
        db.commit()
        db.refresh(proveedor)
        print(f"Proveedor creado: {item.vendor_id} — {item.name}")

        registrar_evento(
            db,
            organization_id=organizacion.id,
            user_id=propietario.id if propietario else None,
            action="create_vendor",
            entity_type="vendor",
            entity_id=proveedor.id,
            details={"vendor_id": item.vendor_id, "status": item.status.value},
        )
        db.commit()

        # VEN-006 se sembró ya en estado TERMINATED; se añade también el
        # evento de cambio de estado que llevó hasta ahí, para que la
        # pantalla de auditoría demuestre ese tipo de evento con datos reales.
        if item.vendor_id == "VEN-006":
            registrar_evento(
                db,
                organization_id=organizacion.id,
                user_id=propietario.id if propietario else None,
                action="change_vendor_status",
                entity_type="vendor",
                entity_id=proveedor.id,
                details={"from": "suspended", "to": "terminated"},
            )
            db.commit()


def run() -> None:
    db = SessionLocal()
    try:
        organizacion, usuarios_por_nombre = _crear_organizacion_y_usuarios(db)
        activos_por_nombre = _crear_activos(db, organizacion)
        riesgos_por_titulo = _crear_riesgos(db, organizacion, activos_por_nombre)
        _frameworks, requisitos_por_clave = _crear_frameworks_y_requisitos(db, organizacion)
        controles_por_codigo = _crear_controles(db, organizacion)
        _vincular_relaciones(
            db, controles_por_codigo, activos_por_nombre, riesgos_por_titulo, requisitos_por_clave
        )
        _crear_mappings(db, organizacion, requisitos_por_clave)
        evidencias_por_nombre = _crear_evidencias(
            db,
            organizacion,
            usuarios_por_nombre,
            controles_por_codigo,
            riesgos_por_titulo,
            activos_por_nombre,
            requisitos_por_clave,
        )
        hallazgos_por_codigo = _crear_hallazgos_y_acciones(
            db,
            organizacion,
            usuarios_por_nombre,
            controles_por_codigo,
            riesgos_por_titulo,
            activos_por_nombre,
            requisitos_por_clave,
            evidencias_por_nombre,
        )
        _crear_proveedores(
            db,
            organizacion,
            usuarios_por_nombre,
            riesgos_por_titulo,
            evidencias_por_nombre,
            hallazgos_por_codigo,
        )
        print(f"\nContraseña de todos los usuarios demo: {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
