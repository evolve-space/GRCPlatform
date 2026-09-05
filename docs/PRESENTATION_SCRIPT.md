# Guion de presentación oral (5–10 minutos)

> Escrito para hablarlo, no para leerlo en voz alta palabra por palabra.
> Cada bloque indica un tiempo orientativo — la suma da ~8 minutos; si hay
> que recortar, los bloques marcados con "(recortable)" son los primeros
> candidatos.

## 1. Problema (45s)

"Cualquier organización que quiera gestionar su riesgo y su cumplimiento
de forma seria acaba necesitando llevar el control de un montón de piezas:
qué activos tiene, qué riesgos les afectan, qué controles los mitigan, qué
evidencia demuestra que esos controles funcionan de verdad, qué hallazgos
ha dejado la última auditoría, quién es responsable de corregirlos y para
cuándo, y qué proveedores externos meten riesgo adicional en la ecuación.

En la práctica, esto casi siempre vive repartido entre hojas de cálculo,
carpetas compartidas y el correo. Nada está conectado, y demostrar el
estado real de cumplimiento ante una auditoría es un ejercicio manual,
lento y propenso a errores."

## 2. Objetivo (30s)

"El objetivo de este proyecto era construir una plataforma que modelara
esa realidad como lo que es: un grafo de entidades relacionadas, con una
única fuente de verdad, un registro de auditoría inmutable, y un
indicador de cumplimiento calculado de verdad a partir de los datos — no
un PDF que alguien actualiza una vez al trimestre."

## 3. Qué es GRCPlatform (45s)

"GRCPlatform es una plataforma GRC self-hosted: gestiona activos, riesgos,
controles, marcos de cumplimiento, evidencias, hallazgos, acciones de
remediación y proveedores, con un dashboard con Compliance Score, una API
REST completa, y una integración real con MCP — el protocolo que usa
Claude para conectarse a herramientas externas — para poder consultar y
operar la plataforma en lenguaje natural.

Es un proyecto de portfolio, pensado para demostrar dos cosas a la vez:
diseño de producto GRC, y arquitectura de software con garantías reales de
seguridad."

## 4. Arquitectura (60s)

"La arquitectura tiene una idea central: **hay un único camino hacia los
datos**. El frontend web y el servidor MCP son dos clientes distintos de
la misma API REST — ninguno de los dos tiene un atajo propio a la base de
datos. Frontend en React, API en FastAPI con SQLAlchemy sobre PostgreSQL,
y en producción, Nginx delante haciendo de reverse proxy y terminando
HTTPS.

Esto importa especialmente para MCP: cuando conecto Claude a esta
plataforma, Claude no habla nunca con PostgreSQL — habla con el servidor
MCP, que a su vez es un cliente HTTP más de la API REST, con la misma
autenticación, el mismo control de acceso, y el mismo registro de
auditoría que cualquier otro cliente."

## 5. Modelo de datos (45s) *(recortable)*

"El modelo de datos sigue el ciclo GRC de forma literal: un Activo puede
tener Riesgos, un Riesgo se mitiga con Controles, un Control se demuestra
con Evidencias, un Control mal implementado o sin evidencia puede generar
un Hallazgo, un Hallazgo se cierra con una Acción de remediación asignada
a un responsable, y un Proveedor externo reutiliza la misma entidad Riesgo
en lugar de tener su propio motor de scoring paralelo — para no acabar con
dos fuentes de verdad distintas sobre 'cuánto riesgo hay'."

## 6. Flujo GRC (30s)

"Dicho como un solo flujo: Riesgo → Control → Evidencia → Hallazgo →
Acción → Proveedor → Auditoría → Compliance Score. Cada flecha es una
relación real en la base de datos, no solo un diagrama — y os lo voy a
enseñar navegando entre ellas en la demo."

## 7. Seguridad (60s)

"En seguridad, lo que quiero destacar no es una lista de features, sino
el criterio: cada dato pertenece siempre a una organización, y esa
organización se determina siempre a partir de quién ha iniciado sesión —
nunca de un valor que envía el cliente. Si alguien intenta acceder a un
recurso de otra organización, la respuesta es 404, no 403 — ni siquiera
confirmamos que ese recurso existe.

Además: JWT con bcrypt para usuarios humanos, control de acceso por rol,
credenciales de integración con permisos de mínimo privilegio para
sistemas como MCP, límite de peticimientos para frenar fuerza bruta, y
protección real de los archivos que se suben como evidencia."

## 8. API (30s) *(recortable)*

"Toda esta lógica se expone mediante una API REST completa, documentada
automáticamente con OpenAPI — Swagger interactivo incluido — con dos
formas de autenticarse: JWT para el frontend, y claves de API con permisos
concretos (scopes) para integraciones como MCP."

## 9. MCP (60s)

"Esta es la parte que más me interesa destacar. MCP es el protocolo que
usa Claude para conectarse a herramientas externas. Aquí he implementado
un servidor MCP real — no una simulación — con 14 herramientas: listar y
consultar riesgos, controles, evidencias, hallazgos, proveedores, el
dashboard, el Compliance Score, y una de escritura, crear un riesgo.

Y la regla de diseño que gobierna todo esto: el servidor MCP **nunca**
accede directamente a PostgreSQL. Siempre pasa por la API REST, con la
misma autorización que cualquier otro cliente. Si una credencial de
integración no tiene el permiso necesario, la API responde 403 — y esa
respuesta la genera exactamente el mismo código que protege al frontend."

## 10. Compliance Score (45s)

"El dashboard incluye un Compliance Score, un índice interno de 0 a 100
que combina cuatro dimensiones ponderadas: controles al 40%, evidencias al
20%, hallazgos al 20% y remediación al 20%. Si una dimensión no tiene
datos suficientes, se recalculan los pesos automáticamente en vez de
inventar un cero. Y quiero ser explícito en esto: **no es una
certificación** — es un indicador interno de cobertura y madurez, nunca
una declaración de cumplimiento ISO 27001 ni de ningún otro estándar."

## 11. Docker / producción (45s)

"Todo el stack corre en Docker: PostgreSQL, backend, servidor MCP y
frontend en desarrollo. Para producción hay una configuración
independiente con Nginx delante, terminando HTTPS, y sin PostgreSQL, el
backend ni el servidor MCP expuestos directamente a Internet — Nginx es el
único punto de entrada público."

## 12. Backup / restore (30s)

"También implementé y probé de verdad un procedimiento de backup y
restauración — no solo de la base de datos, también del almacenamiento de
evidencias, porque una evidencia sin su archivo físico no sirve de nada.
Hice una recuperación completa en un entorno aislado y verifiqué que el
hash SHA-256 de una evidencia restaurada coincidía exactamente con el
original."

## 13. Limitaciones (30s)

"Soy explícito con lo que falta: no hay autenticación multifactor, no hay
un antivirus real sobre los archivos subidos, el rate limiting es por IP y
no todavía por usuario, y el despliegue en HTTPS lo he verificado
funcionalmente con un certificado de prueba, pero no todavía contra un
dominio público real. Prefiero decir esto claramente a presentar el
proyecto como algo que no es."

## 14. Conclusión (30s)

"En resumen: GRCPlatform conecta todo el ciclo GRC en una sola plataforma,
con una arquitectura donde tanto un usuario humano como una IA conectada
por MCP pasan exactamente por las mismas reglas de seguridad. Es un
proyecto pensado para demostrar tanto criterio de producto en GRC como
disciplina de ingeniería en seguridad y arquitectura de software."
