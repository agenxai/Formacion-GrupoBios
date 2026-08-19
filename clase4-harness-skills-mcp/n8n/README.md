# El flujo n8n del cierre — Clase 4

> **Estado: TODO abierto.** El caso concreto del cierre (dominio / disparador
> / acción) **todavía no está definido**. Abajo hay una **propuesta
> recomendada (no vinculante)**. El facilitador la confirma o la reemplaza
> con el cliente al menos **una semana antes** de la fecha, y este archivo
> se actualiza con el caso definitivo. Mientras tanto, esto es el candado
> que impide olvidar el cierre.
>
> Ver [`../specs/05-flujo-n8n-cierre.md`](../specs/05-flujo-n8n-cierre.md)
> para el detalle completo (requisitos, plan B, alternativas).

## El momento más importante de la clase

El cierre n8n es el gancho principal de S4. El mensaje:

> **"Lo que antes tomaba armar a mano en n8n 20-30 minutos, el harness lo
> arma hablando en 3-5 minutos."**

El harness no reemplaza n8n — **lo opera**. n8n sigue siendo donde vive el
flujo, donde se ve la ejecución, donde se controla. El harness es el que lo
arma hablando.

## Mecánica (15 min en vivo)

1. El facilitador abre el harness conectado a la CLI de n8n (auth probada
   24-48 h antes).
2. Le habla: le pide que arme un workflow con un disparador y una o dos
   acciones sobre el dominio del caso.
3. El harness invoca la CLI de n8n: crea el workflow, lo configura, lo
   activa.
4. Verificación: el facilitador dispara el flujo (webhook manual o evento
   de prueba) y muestra la ejecución en la UI de n8n de la agencia.
5. Cierre verbal: *"esto tomó 4 minutos hablando. La última vez que armamos
   un flujo así a mano, fueron 25 minutos."*

## TODO — caso concreto

> **Reemplazar este bloque por el caso definitivo y borrar el encabezado
> TODO.** Recordá generar `plantilla-cierre-rescate.json` después.

### Propuesta recomendada (no vinculante) — dominio Logística

**Por qué Logística:** es el dominio N3 de S1 (interfaz "tipo aeropuerto"),
el más concreto y autocontenido. Reusa `estado_pedido` + `turnos_muelle` de
`bios_ops.py` (continuidad con S2/S4) y se conecta natural con el MCP de
Google Sheets del Bloque 2. Cabe en 15 min.

| Componente | Valor |
|---|---|
| **Dominio** | Logística |
| **Disparador** | Webhook que recibe un cambio de estado de pedido. Payload: `{"pedido": "PD-24-00871", "estado": "en muelle", "planta": "Itagüí"}` |
| **Acción 1 — consulta** | Llamar a `estado_pedido` + `turnos_muelle` (via `bios_ops.py` expuesto por HTTP, o por el servicio de tools de S2) |
| **Acción 2 — escritura** | Escribir una fila en la Google Sheet `Seguimiento Demo Clase 4 Bios` con: `Pedido`, `Estado`, `Turno`, `Timestamp` (usa el MCP de Sheets del Bloque 2) |
| **Acción 3 (opcional)** | Notificar a Slack/Teams si el turno de muelle > 5 |
| **Resultado visible** | Una fila nueva en la hoja `Seguimiento Demo Clase 4 Bios` |

### Alternativas válidas

| Dominio | Disparador | Acción |
|---|---|---|
| Mantenimiento | Lectura de sensor supera umbral (5.5 mm/s) | `historial_fallas` + `retrieve_docs` (Guía de sensor) + fila en Sheet "Alertas de mantenimiento" |
| Compras | Inventario baja del mínimo (programado cada hora) | `consultar_inventario` + `consultar_demanda` + `retrieve_docs` (Política de abastecimiento) + Sheet "Alertas de abastecimiento" |
| Producción / TD | Demanda proyectada > producción planificada (programado diario) | `consultar_demanda` + `consultar_produccion` + Sheet "Brechas de planeación" |

> Producción / TD no se recomienda para un cierre de 15 min (requiere
> explicar planeación de demanda). Mantenimiento y Compras son tan válidos
> como Logística.

## Requisitos del caso definitivo (cualquiera que se elija)

1. Reusa al menos una tool de `bios_ops.py` (continuidad con S2/S4).
2. Recomendado: reusa `retrieve_docs` o menciona el vector store de OpenAI (continuidad
   con S3/S4) — para que el cierre toque las dos fuentes de la Skill.
3. Escribe su salida en la Google Sheet de la demo del Bloque 2 (usa el
   MCP que se acaba de mostrar — refuerza "lo de hace 15 min, ahora
   enchufado a un flujo").
4. Es disparado por un evento (webhook o programado), no por un botón
   manual — para que el concepto "automatización" quede claro.
5. Cabe en 15 minutos de armado en vivo con el harness (incluyendo
   narración).
6. Tiene plantilla de rescate pre-armada en `plantilla-cierre-rescate.json`.

## Plan B (si el harness se cae o la red oscila)

- **`plantilla-cierre-rescate.json`** — el workflow del caso definitivo,
  exportado en una sesión de práctica del facilitador. Se importa
  manualmente desde la UI de n8n (`Workflows → Import from File`).
- Narración: *"el harness se nos cayó; esto es lo que hubiera armado. Lo
  arman ustedes solos con el `INSTALL-HARNESS-N8N-CLI.md`."*
- **Nunca** se presenta la plantilla como si la hubiera armado el harness
  en vivo (mismo candado de S1/S2/S3).

> **TODO: generar `plantilla-cierre-rescate.json`** cuando se cierre el
> caso. Mientras tanto, este archivo no existe — el cierre depende de que
> el harness arme en vivo, con plan B no disponible. Es un candado más para
> cerrar el caso antes de la fecha.

## Archivos

| Archivo | Qué es | Estado |
|---|---|---|
| `README.md` | este documento | ✅ (con TODO del caso) |
| `plantilla-cierre-rescate.json` | export del workflow, plan B | ❌ TODO (generar al cerrar el caso) |

## Cómo reproducirlo tú mismo

Ver [`../INSTALL-HARNESS-N8N-CLI.md`](../INSTALL-HARNESS-N8N-CLI.md) §8
"Instalá la CLI de n8n y conectala (cierre)".

## Candados

- **Instancia n8n de la agencia, no de Bios.** Si en tu proyecto vas a usar
  la instancia de Bios, coordiná con TI el acceso en el acompañamiento
  S5-S7.
- **Datos sintéticos.** El webhook del cierre usa pedidos sintéticos de
  `bios_ops.db`. No se disparan eventos con datos reales de Bios.
- **No se despliega a producción en clase.** El workflow queda activo en
  la instancia n8n de la agencia durante la demo; se desactiva al terminar.
