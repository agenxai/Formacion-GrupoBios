# Los MCPs de la demo — Clase 4

> **MCP — Model Context Protocol.** Un estándar para que el harness conecte
> capacidades externas (leer una hoja, leer un issue, leer un recurso de
> Azure) **sin que vos escribas el código de la integración**. Configurás la
> conexión (auth, alcance); el harness hace el resto.
>
> Ver [`../specs/04-mcps-demo.md`](../specs/04-mcps-demo.md) para el detalle
> pedagógico (rol de cada MCP en la clase, candados, riesgos).

## Los tres MCPs de la demo

| MCP | Rol en la clase | Demo en vivo | Cuenta usada |
|---|---|---|---|
| **Linear MCP** | "Así lo usamos nosotros" — referencia de un caso de uso real | No (se muestra config + se narra) | Cuenta Linear de la agencia |
| **Google Sheets / Drive MCP** | Demo en vivo: el harness lee y escribe sobre una hoja real | **Sí** | Cuenta Google de la agencia |
| **Azure MCP Server** | Mención conceptual — "existe, mismo patrón, cuando TI les habilite Azure" | No (sólo slide / nota) | Ninguna (no hay cuenta propia) |

---

## 1 · Linear MCP — referencia

**Por qué lo mostramos:** es el MCP que la agencia ya usa internamente. La
demo es creíble porque es real, no montada para la clase. Muestra el patrón
"leer un sistema externo de gestión de trabajo" — el equivalente en Bios
podría ser Jira, ServiceNow, o el sistema de tickets de TI.

**Cómo reproducirlo con tu propia cuenta:**

1. Conseguí un Personal API Key de Linear (Linear → Settings → API →
   Personal API keys).
2. En el archivo de config del harness, agregá el MCP de Linear con tu
   token. La configuración exacta depende del MCP community que elijas
   (hay varios; buscalos en el directorio de MCPs de tu harness).
3. Probá: pedí al harness *"liste los issues en estado In Progress de mi
   proyecto X"*.

**Candado:** nunca pegues el token en un chat ni lo subas a un repo. Si
proyectás el config, redactá los campos sensibles antes.

---

## 2 · Google Sheets / Drive MCP — demo en vivo

**Por qué lo mostramos:** Compras, Logística y Producción ya usan hojas de
cálculo a diario. El harness puede leer y escribir sobre esa hoja **sin
que nadie programe una integración**. Es la lección más útil de la sesión
para los Champions no-software.

### Setup (paso a paso, para reproducir con tu propia cuenta)

#### 2.1 · Creá la hoja de prueba

1. Abrí Google Sheets y creá una hoja nueva: `Seguimiento Demo Clase 4
   Bios` (o el nombre que prefieras).
2. Encabezados en la fila 1: `Pedido`, `Estado`.
3. Tres filas de ejemplo:
   - `PD-24-00871` · `en muelle`
   - `PD-24-00902` · `en tránsito`
   - `PD-24-00993` · `entregado`
4. Copiá el ID de la URL:
   `https://docs.google.com/spreadsheets/d/<ESTE-ID>/edit` → pegalo en
   `.env` como `GOOGLE_SHEETS_DEMO_ID`.

#### 2.2 · Autenticá el MCP

Dos caminos, según el MCP community que elijas:

**(a) OAuth (usuario):** el MCP abre el navegador la primera vez y te pide
autorizar el acceso a tu Google Drive. Más simple para uso personal.

**(b) Service account (organización):** creás una service account en Google
Cloud Console, le descargás el JSON de credenciales, y compartís la hoja
con el email de la service account (`xxx@yyy.iam.gserviceaccount.com`).
Más adecuado para producción, cuando no querés depender de un usuario
concreto.

#### 2.3 · Conectá el MCP al harness

En el archivo de config del harness, agregá la entrada `mcp` con el
servidor de Google Sheets. La configuración exacta depende del MCP —
consultá la documentación del MCP community que elijas.

#### 2.4 · Verificá lectura y escritura

Con el harness abierto:

```
> leé la hoja "Seguimiento Demo Clase 4 Bios" y mostrame las filas
> añadí una fila a esa hoja con pedido PD-24-01050, estado "en muelle"
```

Refrescá la hoja en el navegador — la fila nueva debe aparecer.

### Candados

- **Cuenta de la agencia / tuya, nunca de Bios en clase.** Si un Champion
  pregunta "¿puedo conectar mi cuenta de Bios?", la respuesta es: *"sí, en
  su proyecto. Hoy usamos la nuestra para no tocar datos de Bios. El
  `INSTALL-HARNESS-N8N-CLI.md` te enseña a conectar la tuya."*
- **Hoja de prueba, no hoja productiva.** Lo que se escribe en vivo es
  dato sintético en una hoja de demo. No se escribe nada en hojas reales
  de Bios.
- **No se exponen credenciales.** La auth vive en el config del harness,
  no se proyecta.

---

## 3 · Azure MCP Server — mención conceptual

**Por qué lo mencionamos (sin demo):** Grupo Bios usa Microsoft/Azure.
Azure MCP Server existe y expone recursos de Azure (Key Vault, Storage,
Cosmos DB, etc.) con el mismo patrón que vieron con Sheets. Cuando TI de
Bios les habilite acceso corporativo a Azure, el patrón es idéntico.

**Por qué no lo demostramos en vivo:**
- Las cuentas gratuitas de Azure piden tarjeta de crédito — candado de
  fricción cero roto.
- No tenemos cuenta Azure propia de la agencia para la demo.

### Configuración de referencia (comentada, no ejecutada en clase)

> Cuando TI te habilite acceso corporativo a Azure, podés replicar este
> patrón. La configuración exacta depende del Azure MCP Server que elijas
> (oficial de Microsoft o community). Lo típico:

```jsonc
// Ejemplo conceptual — no ejecutar en clase.
// Requiere: tenant_id, client_id, client_secret de un App Registration
// de Azure AD con permisos sobre los recursos que querés exponer.
{
  "mcp": {
    "azure": {
      "command": "npx",
      "args": ["-y", "@azure/mcp-server"],   // o el community que elijas
      "env": {
        "AZURE_TENANT_ID": "<tu-tenant-id>",
        "AZURE_CLIENT_ID": "<tu-client-id>",
        "AZURE_CLIENT_SECRET": "<tu-client-secret>",
        "AZURE_SUBSCRIPTION_ID": "<tu-subscription-id>"
      }
    }
  }
}
```

**Pasos para replicar en el acompañamiento S5-S7 (con TI de Bios):**

1. Coordiná con TI de Bios la creación de un App Registration en su
   Azure AD.
2. Asigná permisos sobre los recursos que tu proyecto necesita (Key Vault,
   Storage, Cosmos DB, etc.) — **mínimo privilegio**.
3. Cargá las credenciales en el config del harness (nunca en `.env` del
   repo ni en git).
4. Probá: pedí al harness que liste recursos de Azure del tipo que
   configuraste.
5. **Candado:** resolvé con TI / Legal el contrato de tratamiento **antes**
   de exponer cualquier dato productivo de Bios al LLM subyacente del
   harness.

### Candado verbal (escrito en el slide, dicho en voz alta)

> *"Esto existe, funciona igual que lo que acaban de ver con Sheets, y
> cuando su equipo de TI les habilite acceso corporativo a Azure, el
> patrón es el mismo. No lo demostramos hoy porque no tenemos cuenta
> propia; este README lo documenta para que lo repliquen."*

---

## Lo que NO hace esta sesión con MCPs

- **No construye un MCP propio.** Se muestra cómo *conectar* MCPs
  existentes. Construir uno es decisión de proyecto → acompañamiento
  S5-S7.
- **No demuestra Azure MCP Server en vivo.** Mención conceptual únicamente
  (ADR-005 de la spec 02).
- **No conecta MCPs a sistemas internos de Bios (SAP, ERP, etc.)** en
  clase. Se menciona que el patrón es el mismo; coordinar con TI en el
  acompañamiento.
- **No configura permisos finos / multi-tenancy.** La demo usa alcance de
  demo (una hoja, lectura+escritura). Producción con alcance restringido
  es tema de acompañamiento.

---

## Riesgos específicos (ver spec 06 para el plan B completo)

| Riesgo | Mitigación |
|---|---|
| Auth de Google falla en vivo | Auth probada 24-48 h antes; si caduca el token, plan B: transcripción de la verificación previa marcada como pre-grabada |
| El MCP de Sheets no responde | Bajar a lectura (escritura opcional); si tampoco lee, narrar con transcripción |
| Linear MCP expone tokens | Config con campos redacted antes de proyectar; nunca se pegan tokens en el chat |
| Alguien pregunta por conectar cuenta de Bios en clase | "No hoy — en su proyecto, con su cuenta, coordinando con TI. El `INSTALL-HARNESS-N8N-CLI.md` los guía." |
