# Guion de demo (3–5 minutos)

> Objetivo: mostrar el ciclo GRC completo y la integración MCP en vivo,
> contra la organización de demostración **Acme Security Labs**. Datos
> reales del seed — antes de grabar/presentar, comprobar que
> `docker compose ps` muestra los 4 servicios `healthy`/`running` y que
> `python -m app.db.seed` ya se ejecutó. Credenciales demo en
> `docs/DEVELOPMENT.md` (no se repiten aquí).

**Duración objetivo: 3–5 minutos.** Los tiempos son orientativos — ajusta
sobre la marcha, pero no te quedes más de 30s en ningún paso individual.

## 1. Login (15s)

Entra como usuario Admin de la demo en `http://localhost:5173`. Frase
puente: *"Esto es GRCPlatform, una plataforma GRC self-hosted — todo lo
que vais a ver es real, no es una maqueta."*

## 2. Panel (30s)

Se abre directamente en `/` tras el login. Señalar, en este orden:

- Los KPI de cabecera (riesgos críticos/altos, hallazgos abiertos,
  acciones vencidas, evidencias próximas a caducar, proveedores críticos).
- La tarjeta de **Compliance Score** con su desglose por dimensión.
- La lista **"Requiere atención"**.

Frase puente: *"Todo esto se calcula en tiempo real contra PostgreSQL —
no hay ningún número fijado a mano."*

## 3. Riesgo (30–40s)

Clic en el KPI "Riesgos críticos" (enlaza directamente a la lista
filtrada) → abrir el riesgo **"Fuga de datos de clientes por credenciales
débiles"**. Mostrar:

- Probabilidad e impacto (likelihood/impact) y el score resultante.
- Nivel inherente vs. nivel/score **residual** (tras el tratamiento).
- El activo relacionado.
- El tratamiento elegido (mitigar).

Frase puente: *"El score no lo escribe nadie a mano: se recalcula en el
backend cada vez que cambian probabilidad o impacto."*

## 4. Control (20s)

Desde el mismo riesgo (o desde `/controles`), abrir un control
relacionado — p. ej. uno de categoría "Control de acceso". Mostrar su
estado de implementación y su vínculo con el riesgo.

## 5. Evidencia (30s)

Abrir una evidencia vinculada a ese control (p. ej. "Política de
contraseñas"). Mostrar:

- El hash **SHA-256** y el botón/acción de verificación de integridad.
- La clasificación (Confidencial/Interna/etc.).
- La fecha de caducidad.
- Las entidades a las que está vinculada.

Frase puente: *"El hash se calcula al subir el archivo y se puede volver
a verificar en cualquier momento — si alguien manipulara el archivo en
disco, esto lo detectaría."*

## 6. Hallazgo (20s)

Ir a `/hallazgos` y abrir uno abierto — p. ej. "Deficiencia en la política
de contraseñas". Mostrar severidad, estado y las entidades relacionadas
(riesgo/control/evidencia).

## 7. Acción (20s)

Desde el hallazgo, mostrar su acción de remediación asociada:
responsable, prioridad, fecha límite y estado.

## 8. Proveedor (30s)

Ir a `/proveedores`, abrir uno con criticidad **Crítica** (p. ej.
"CloudStack Solutions"). Mostrar due diligence, contrato, próxima
revisión de seguridad, y sus riesgos/evidencias/hallazgos vinculados.

Frase puente: *"El riesgo del proveedor no es un número aparte — reutiliza
exactamente la misma entidad Riesgo que ya habéis visto antes."*

## 9. Auditoría (20s)

Ir a `/auditoria`. Mostrar el filtro de acción y localizar un evento
`mcp_tool_call` reciente (o generarlo en vivo justo antes, con el paso
10). Señalar que el actor es "Sistema" (integración), no un usuario.

## 10. MCP — demo en vivo (40–50s)

Con el servidor MCP corriendo (`http://localhost:8001/mcp`), lanzar en
vivo (terminal o cliente MCP conectado):

- *"¿Cómo está el nivel de cumplimiento?"* → `get_compliance_summary`.
- *"Muéstrame los riesgos críticos"* → `list_risks(level="critico")`.

Volver a `/auditoria` y refrescar: el nuevo evento `mcp_tool_call` debe
aparecer. Frase puente: *"Claude no tiene ningún acceso especial — está
usando la misma API REST, con las mismas reglas, y queda auditado igual
que cualquier otra integración."*

## 11. Seguridad — demo en vivo (30–40s)

Dos demostraciones rápidas, con una credencial de integración de prueba
con solo el scope `vendors:read`:

- Invocar `list_risks` con esa credencial → **403** ("no tiene el scope
  necesario"). *"MCP no puede saltarse la autorización de la API."*
- Pedir un recurso de otra organización con un UUID válido (p. ej. otro
  riesgo) → **404**, no 403 — *"ni siquiera confirma que existe."*

(Opcional si hay tiempo: iniciar sesión como Viewer y mostrar que los
botones de creación/edición no aparecen.)

## 12. Cierre (15–20s)

Resumir el ciclo completo señalando la pantalla:

> *"Riesgo → Control → Evidencia → Hallazgo → Acción → Proveedor →
> Auditoría → Compliance Score — y todo eso, además, accesible por API REST
> y por MCP, con la misma seguridad en los tres caminos."*

## Notas para quien presenta

- Si algo falla en vivo (un contenedor caído, latencia), no te pares a
  depurar — sigue con el siguiente paso y coméntalo con naturalidad
  ("esto normalmente responde al instante, pero seguimos").
- Ten una segunda pestaña ya logueada como Viewer por si se usa el punto
  opcional del paso 11.
- Ten `docker compose logs -f backend` abierto en una terminal aparte
  para poder señalar en vivo la petición real que llega desde MCP si
  alguien pregunta "¿eso es real o está simulado?".
