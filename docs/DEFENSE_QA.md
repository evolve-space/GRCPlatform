# Preguntas de defensa

> Respuestas cortas y defendibles, pensadas para hablarlas de memoria, no
> para leerlas. Cada una referencia dónde está implementado por si hace
> falta profundizar en vivo.

## GRC

**¿Qué es GRC?**
Governance, Risk & Compliance — el conjunto de prácticas para gobernar
una organización, gestionar sus riesgos y demostrar que cumple con normas,
leyes o marcos de referencia (ISO 27001, NIST, etc.). GRCPlatform modela
las cuatro piezas centrales de esa práctica: riesgo, control, evidencia y
cumplimiento, conectadas entre sí.

**¿Por qué separar riesgo inherente y residual?**
El riesgo inherente es "cuánto riesgo hay si no hiciera nada al respecto";
el residual es "cuánto queda después de aplicar el tratamiento". Sin esa
distinción no se puede demostrar que un control realmente reduce el
riesgo — solo se vería un número, sin saber si mejoró o no.

**¿Qué relación existe entre riesgo y control?**
Un control mitiga uno o varios riesgos (relación muchos-a-muchos). El
riesgo residual de un riesgo debería reflejar el efecto de sus controles,
aunque en esta plataforma el residual se introduce explícitamente (no se
recalcula automáticamente a partir del estado de los controles) — es una
simplificación deliberada, no un descuido.

**¿Cómo calculas el Compliance Score?**
Cuatro dimensiones ponderadas (Controles 40%, Evidencias 20%, Hallazgos
20%, Remediación 20%) combinadas en un número 0-100, con renormalización
automática si una dimensión no tiene datos, y "Sin datos" en vez de un
cero inventado cuando no hay una base razonable para calcular nada. Ver
`backend/app/core/compliance_score.py`.

**¿Por qué el Compliance Score no es una certificación?**
Porque es un índice propio, con una fórmula propia, no auditada por un
organismo de certificación ni alineada 1:1 con el proceso de auditoría
real de ISO 27001 u otro estándar. Presentarlo como una certificación
sería engañoso — por eso el propio dashboard lo etiqueta como indicador
interno.

## Seguridad

**¿Cómo evitas IDOR (Insecure Direct Object Reference)?**
El `organization_id` de cada recurso se compara siempre contra el
`organization_id` del actor autenticado (usuario o credencial de
integración) en cada consulta — nunca se acepta un `organization_id` del
cliente. Un recurso de otra organización responde 404, no 403, para no
confirmar ni negar su existencia.

**¿Cómo funciona el multi-tenancy?**
Cada fila relevante tiene una columna `organization_id`. Toda query de
lectura/escritura filtra por ella, derivada siempre del JWT o la API key
autenticada. No hay una tabla ni un esquema separado por organización —
es aislamiento lógico, no físico, verificado con tests que crean datos en
dos organizaciones distintas y comprueban que ninguna ve a la otra.

**¿Por qué JWT?**
Es estándar, sin estado en el servidor (no hace falta una tabla de
sesiones), y permite que el mismo mecanismo de autenticación funcione
igual para el frontend que para cualquier cliente HTTP futuro. El token
lleva una expiración corta (60 minutos por defecto) y se firma con un
secreto que es obligatorio y no tiene valor por defecto inseguro.

**¿Por qué bcrypt?**
Es un hash lento diseñado específicamente para contraseñas humanas —
resiste ataques de fuerza bruta offline mucho mejor que un hash rápido
como SHA-256. Para las claves de integración (API keys) se usa SHA-256 en
cambio, deliberadamente, porque esas claves ya tienen alta entropía
generada por el servidor y necesitan una búsqueda indexada rápida, no
resistencia a diccionario.

**¿Cómo proteges las evidencias?**
Lista blanca de tipos de archivo permitidos, comprobación de "magic
bytes" (no solo la extensión declarada), lista negra de firmas de
ejecutables/scripts, límite de tamaño, nombre físico generado siempre por
el servidor (nunca el nombre subido por el usuario), y comprobación de
que la ruta resuelta nunca sale del directorio de almacenamiento (path
traversal). El contenido nunca se sirve como estático — siempre pasa por
un endpoint autenticado.

**¿Por qué SHA-256 para la integridad de evidencias?**
Es un hash criptográfico estándar, rápido de calcular, con una
probabilidad de colisión despreciable para este caso de uso. Se calcula
al subir el archivo y se puede recalcular bajo demanda para comprobar que
el archivo en disco no ha cambiado desde entonces.

**¿Cómo funciona RBAC en este proyecto?**
Cuatro roles (Admin, GRC Manager, Analyst, Viewer), comprobados siempre en
el backend mediante una dependencia de FastAPI (`require_roles`) — nunca
solo ocultando un botón en el frontend. Un intento de saltárselo llamando
directamente a la API responde 403.

**¿Qué diferencia hay entre rol y scope?**
El rol autoriza a un **usuario humano** (JWT) para un conjunto de acciones
según su función en la organización. El scope autoriza a una
**credencial de integración** (API key, como la que usa el servidor MCP)
para un permiso concreto y explícito (p. ej. `risks:read`). Un rol da
acceso a varias funcionalidades relacionadas; un scope da acceso a una
sola, de forma mucho más granular — es el principio de mínimo privilegio
aplicado a máquinas en vez de a personas.

## Arquitectura

**¿Por qué PostgreSQL?**
Es una base de datos relacional madura, con buen soporte de tipos
avanzados (enums nativos, JSON) que este proyecto usa activamente, y
encaja de forma natural con un modelo de datos tan relacional como el
ciclo GRC (activo→riesgo→control→evidencia, todo con claves foráneas
reales).

**¿Por qué FastAPI?**
Genera documentación OpenAPI automáticamente a partir del propio código,
tiene un sistema de inyección de dependencias que encaja muy bien con
patrones como `require_roles`/`require_access`, y es asíncrono por
defecto — relevante para un servidor MCP que hace peticiones HTTP salientes.

**¿Por qué Docker?**
Para que el entorno de desarrollo sea idéntico para cualquiera que clone
el repositorio (un solo `docker compose up`), y para poder tener una
configuración de producción con los mismos Dockerfiles pero políticas de
red y usuarios distintas (sin publicar puertos internos, sin root).

**¿Por qué Nginx?**
Es el estándar de facto para terminar TLS y hacer de reverse proxy delante
de una aplicación — permite que ni el backend ni el servidor MCP necesiten
gestionar certificados ellos mismos, y centraliza el único punto de
entrada público en un solo componente, más fácil de asegurar y auditar.

**¿Por qué MCP no accede directamente a PostgreSQL?**
Porque si lo hiciera, tendría que reimplementar la autorización, el
aislamiento multi-tenant y la auditoría que ya existen en la API REST —
duplicando la superficie de fallo de seguridad más sensible del sistema.
Con la regla "MCP siempre pasa por la API REST", cualquier mejora de
seguridad en la API se aplica automáticamente también a MCP, sin tocar
nada en el servidor MCP.

## MCP

**¿Qué problema resuelve MCP aquí?**
Permite que un modelo de lenguaje como Claude consulte y opere sobre
GRCPlatform en lenguaje natural ("¿cuántos riesgos críticos hay?"), sin
que el modelo necesite conocer la API REST directamente — el servidor MCP
traduce esa intención a llamadas HTTP concretas.

**¿Cómo se autentica el servidor MCP?**
Con una credencial de integración (API key) igual que cualquier otro
cliente de integración — nunca con un usuario humano detrás. Esa
credencial se crea desde la propia API (solo un Admin puede crearla) y su
secreto se muestra una única vez.

**¿Cómo se aplica autorización a MCP?**
Cada credencial tiene un conjunto explícito de scopes (p. ej.
`risks:read`). Cada herramienta MCP exige un scope concreto en el mismo
punto del backend (`require_access`) que ya usan los endpoints normales —
no hay una capa de autorización distinta para MCP.

**¿Qué ocurre si un token no tiene el scope necesario?**
La API responde 403 con un mensaje que nombra el scope que falta; la
herramienta MCP devuelve ese error como un resultado estructurado al
modelo, en vez de lanzar una excepción sin control.

**¿Cómo se evita que MCP se salte la seguridad de la API?**
Porque no existe ningún camino alternativo: el cliente HTTP del servidor
MCP (`GRCApiClient`) solo sabe hablar con la REST API por HTTP, no importa
`sqlalchemy` ni ningún modelo del backend, y no recibe ninguna credencial
de PostgreSQL — verificado automáticamente con un test que analiza los
imports del propio paquete `mcp/`.

## Producción

**¿Cómo desplegarías esto en un servidor real?**
Con `docker-compose.prod.yml`: servidor Linux con Docker, SSH por clave,
firewall abierto solo en 22/80/443, certificado TLS (Let's Encrypt),
variables de entorno reales generadas para ese entorno, y Nginx como
único punto de entrada público. Guía completa en `docs/DEPLOYMENT.md`.

**¿Cómo harías backups?**
`scripts/backup.sh` hace un `pg_dump` de PostgreSQL y un `tar` del
almacenamiento de evidencias — las dos partes son necesarias, porque una
evidencia sin su archivo físico no sirve de nada. Recomendado en cron
diario, con copia fuera del propio servidor.

**¿Cómo recuperarías el sistema ante un desastre?**
`scripts/restore.sh` recrea la base de datos desde el dump y restaura el
almacenamiento de evidencias. Lo probé de verdad: backup real → restauración
en un entorno Docker aislado y vacío → verificación de que los datos
coinciden y de que el hash SHA-256 de una evidencia restaurada es idéntico
al original.

## Limitaciones

**¿Qué falta para producción pública real?**
Validar HTTPS con un dominio público y un certificado de Let's Encrypt
real (solo probado con uno autofirmado), ejecutar el pipeline de CI/CD
en GitHub Actions de verdad, y añadir autenticación multifactor — el resto
de controles de seguridad ya están implementados y verificados.

**¿Qué mejorarías en una v2?**
Rate limiting por usuario JWT (no solo por IP), un motor de antivirus real
para las evidencias subidas, automatización de backups con cron/systemd,
y probablemente SSO/OIDC si el proyecto fuera a usarse por varias
organizaciones con su propio proveedor de identidad.
