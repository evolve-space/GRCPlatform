# Privacidad

## Qué datos almacena GRCPlatform

Por cada organización cliente (multi-tenant, siempre aislado por
`organization_id`):

- **Usuarios**: nombre, email, rol, contraseña (hash bcrypt, nunca en
  texto plano ni en respuestas de la API).
- **Datos GRC**: activos, riesgos, controles, marcos de cumplimiento,
  hallazgos, acciones de remediación, proveedores — información de
  gestión, no datos personales de terceros salvo los que la propia
  organización decida incluir en campos de texto libre (p. ej. el nombre
  de un responsable en `owner`).
- **Evidencias**: archivos subidos por la organización (políticas,
  certificados, capturas, informes) — pueden contener información
  sensible o confidencial de esa organización, según su propia
  clasificación (`public/internal/confidential/restricted`).
- **Credenciales de integración**: nunca el secreto en texto plano, solo
  su hash SHA-256 y metadatos (nombre, scopes, fechas).
- **Registro de auditoría**: quién (usuario o credencial de integración),
  qué acción, sobre qué entidad, desde qué IP y cuándo — nunca el
  contenido de un archivo, una contraseña, un token ni ningún otro secreto.

## Datos ficticios en la demo

Todos los datos de la organización de demostración **"Acme Security
Labs"** (usuarios, riesgos, controles, hallazgos, proveedores, evidencias)
son **completamente ficticios**, generados para ilustrar el funcionamiento
de la plataforma. Ningún nombre, email, riesgo o documento corresponde a
una persona, empresa o incidente real. La contraseña de los usuarios demo
(`Demo1234!`) es intencionadamente pública (documentada en el
[README](../README.md)) y solo tiene sentido en una instalación local/de
demostración — nunca debe reutilizarse en una instalación real.

## Qué puede contener Evidence Vault

Evidence Vault almacena archivos subidos por cada organización cliente
(políticas, certificados, capturas de pantalla, informes de auditoría,
etc.). GRCPlatform **no inspecciona el contenido** de esos archivos más
allá de las comprobaciones de seguridad de la subida (tipo, magic bytes,
tamaño — ver `docs/SECURITY.md`): no hay ningún análisis de contenido, ni
extracción de texto, ni envío a un servicio externo. Las evidencias
clasificadas como `confidential` o `restricted` **nunca se envían a ningún
servicio externo de ningún tipo** — clasificación y tratamiento son
responsabilidad de quien sube el archivo.

## Qué queda en el Registro de auditoría

El AuditLog registra metadatos de cada operación sensible (acción, entidad
afectada, actor, IP, fecha), nunca el contenido de lo que se creó o
modificó más allá de un resumen mínimo ya público en la propia interfaz
(p. ej. el título de un riesgo creado). Es inmutable por diseño (sin
endpoints de edición/borrado) y de solo lectura para Admin/GRC Manager.

## Tratamiento de datos por el servidor MCP

El servidor MCP (ver [docs/MCP.md](MCP.md)) es un cliente más de la REST
API, autenticado con una credencial de integración con scopes explícitos.
Cuando se usa junto a un modelo de lenguaje (p. ej. Claude) para responder
preguntas en lenguaje natural sobre los datos GRC de una organización:

- Los datos que las herramientas MCP devuelven pasan a formar parte del
  contexto de la conversación con ese modelo — exactamente los mismos
  datos (y solo esos) a los que esa credencial ya tendría acceso vía la
  REST API, nunca más.
- `list_evidence`/`get_evidence` **nunca devuelven el contenido binario**
  de un archivo, solo sus metadatos — un modelo de lenguaje conectado vía
  MCP no puede "leer" el contenido de una evidencia a través de estas
  herramientas.
- GRCPlatform no decide por el operador de la credencial de integración
  qué modelo de IA se usa al otro lado del servidor MCP, ni qué política
  de retención tiene ese proveedor sobre el contexto que recibe — es
  responsabilidad de quien despliega y opera esa credencial.
- **Recomendación explícita**: no conceder una credencial de integración
  con scopes de lectura sobre evidencias `confidential`/`restricted` a un
  servidor MCP conectado a un proveedor de IA externo, salvo que la
  organización tenga controles organizativos adecuados para ello (acuerdo
  de tratamiento de datos con el proveedor, revisión legal, etc.). Una
  instalación self-hosted puede conectar el servidor MCP a un modelo local
  (on-premise) si quiere evitar por completo el envío de datos a un
  tercero — la arquitectura (MCP → REST API, nunca al revés) es la misma
  en ambos casos.

## Límites del uso de servicios externos de IA

**La funcionalidad GRC principal de GRCPlatform no depende de ningún
proveedor externo de IA.** El servidor MCP es una capa opcional de
automatización/integración, no un requisito del núcleo de la aplicación:
gestión de activos, riesgos, controles, evidencias, hallazgos, acciones,
proveedores, auditoría y Compliance Score funcionan completamente sin él.
GRCPlatform en sí mismo no envía datos a ningún servicio de IA por su
cuenta — solo lo hace, indirectamente, si un operador conecta
voluntariamente un cliente MCP (como Claude) usando una credencial de
integración que él mismo crea y a la que decide qué scopes concede.

## Datos que NO recoge GRCPlatform

- No hay analítica de terceros, píxeles de seguimiento ni telemetría de
  uso enviada fuera de la propia instalación.
- No se recogen datos de navegación del usuario más allá de lo estrictamente
  necesario para la sesión (el JWT en `localStorage` del navegador).
- No se comparte ningún dato con terceros salvo la excepción explícita y
  opcional de MCP descrita arriba, bajo control total del operador de la
  instalación.
