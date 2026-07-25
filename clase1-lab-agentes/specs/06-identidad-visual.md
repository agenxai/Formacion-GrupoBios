# 06 · Identidad visual

## Niveles de obligatoriedad

Esta spec mezcla requisitos duros con orientación de diseño. Se distinguen para que la
implementación no se frene por detalles que no importan:

**`DEBE` — no negociable, verificable:**
- Los valores `#00657F` y `#AACF00` son exactos y no se alteran.
- Ningún par (texto, fondo) baja de 4.5:1 — medido por `scripts/validar_contraste.py`.
- El lima nunca es color de texto sobre fondo claro.
- El logo de Grupo Bios conserva su proporción 2410×668 y no se recolorea, recorta ni
  filtra.
- Tamaño mínimo de texto: 14 px.
- El color nunca es el único portador de significado.

**Orientativo — ajústese al implementar:** la escala completa de tokens CSS, los
tamaños exactos por rol tipográfico, y los detalles de los componentes. Son un punto de
partida coherente, no un contrato. Si el implementador necesita un gris intermedio más,
lo agrega sin pedir permiso.

## Origen de los colores

Extraídos por muestreo de píxeles del logo oficial entregado por el cliente
(`Clase 1 - Agentes/Grupo Bios.png`, 2410×668 px), no estimados a ojo. El logo es
plano: **dos tintas, sin degradados**.

| Color | Hex | RGB | Cobertura del logo | Elemento |
|---|---|---|---|---|
| **Teal Bios** | `#00657F` | `0, 101, 127` | 82.5% | Wordmark "Bios", "GRUPO", arco inferior |
| **Lima Bios** | `#AACF00` | `170, 207, 0` | 17.5% | Hojas del sol, punto de la "i" |

Logo de Qypher (`images/cypher-logo.png`): degradado naranja de `#F84F00` a `#FF8900`.

**Regla de co-marca:** el naranja Qypher queda reservado exclusivamente al crédito de
marca en el pie y a la insignia del encabezado. **NO DEBE** usarse como color de
interfaz. La UI es de Bios; Qypher facilita.

## Paleta de interfaz

Derivada de las dos tintas más una escala de grises fría (matiz sesgado hacia el teal,
para que los grises no se sientan ajenos al logo).

```css
:root {
  /* Marca — valores exactos del logo, NO se alteran */
  --bios-teal:   #00657F;
  --bios-lima:   #AACF00;
  --qypher:      #F84F00;

  /* Escala del teal, derivada */
  --teal-900: #00323F;
  --teal-800: #004A5D;
  --teal-700: #00657F;   /* = marca */
  --teal-500: #0A87A6;
  --teal-300: #5FB6CC;
  --teal-100: #D6EDF3;
  --teal-050: #F0F8FA;

  /* Escala del lima, derivada */
  --lima-700: #607400;   /* corregido: #6E8600 daba 4.14:1 sobre blanco */
  --lima-500: #8CAB00;
  --lima-400: #AACF00;   /* = marca */
  --lima-100: #F0F7CC;

  /* Grises fríos */
  --gris-900: #0E1A1F;
  --gris-700: #33474E;
  --gris-500: #5E7276;   /* corregido: #63797F daba 4.38:1 sobre --gris-050 */
  --gris-300: #B9C7CB;
  --gris-100: #EDF1F2;
  --gris-050: #F8FAFA;

  /* Semánticos */
  --exito:  #0F7B4F;
  --alerta: #B45309;
  --error:  #B3261E;
  --info:   var(--teal-700);
}
```

## Reglas de uso, no negociables

### El lima NO se usa para texto sobre blanco
`#AACF00` sobre blanco da un contraste aproximado de **1.8:1** — muy por debajo del
mínimo de 4.5:1 para texto. Es un lima brillante, y esto no es negociable por gusto:
proyectado en un salón con luz ambiente, texto lima sobre blanco es simplemente
ilegible.

Usos permitidos del lima:
- Relleno de insignias y *chips*, **con texto `--gris-900` encima** (contraste ≈ 11:1).
- Barras, indicadores y elementos gráficos de más de 3 px (mínimo 3:1 — cumple).
- Acento de estado "activo" o "completado".
- Subrayado y borde de elemento seleccionado.

### Jerarquía de color
- **Teal** — estructura: encabezado, títulos, bordes activos, enlaces, botón primario.
- **Lima** — solo lo que ya ocurrió o está activo: paso completado, nivel corriendo.
- **Grises** — todo el cuerpo: texto, contenedores, separadores.
- **Semánticos** — únicamente estado real. `--alerta` para el aviso de alucinación de
  N1; `--error` para fallos de tool.

Un elemento de la UI NO DEBE usar teal y lima como fondos adyacentes: su contraste
mutuo es ≈3.7:1, aceptable para gráficos pero vibrante y cansado en superficies
grandes.

### Modo oscuro
El tablero DEBERÍA soportarlo (`prefers-color-scheme`), porque se proyecta en salón y
a veces con las luces bajas. En oscuro, `--bios-teal` no alcanza contraste sobre fondo
oscuro: se sustituye por `--teal-300` (`#5FB6CC`) para texto y bordes, **manteniendo
el teal exacto solo en el logo**. El logo nunca se recolorea.

### Validación obligatoria
El repo DEBE incluir `scripts/validar_contraste.py` que compute los ratios WCAG de
cada par (texto, fondo) declarado en `estilos.css` y falle si alguno destinado a texto
queda bajo 4.5:1 (o 3:1 para texto ≥ 24 px). Los ratios de esta spec son cálculos de
referencia; el script es la autoridad. No se afirma accesibilidad sin medirla.

**Y la autoridad ya corrigió a la spec.** Al ejecutarlo por primera vez encontró cuatro
incumplimientos en la paleta propuesta acá: `--lima-700` sobre blanco daba 4.14:1,
`--gris-500` sobre `--gris-050` daba 4.38:1, y la escala tipográfica orientativa usaba
13 px contra el mínimo duro de 14 px. Los dos tonos se oscurecieron lo mínimo necesario
—medido, no estimado— y los tamaños subieron a 14 px. Es exactamente para lo que se pidió
el script: los números escritos a mano en una spec de diseño son una hipótesis.

## Logos

### Archivos
| Destino | Origen | Notas |
|---|---|---|
| `frontend/assets/grupo-bios.png` | `Clase 1 - Agentes/Grupo Bios.png` | Copiar sin recomprimir. Nombre sin espacios. |
| `frontend/assets/qypher.png` | `Clase 1 - Agentes/images/cypher-logo.png` | |

### Uso
- **Encabezado:** logo de Grupo Bios a la izquierda, altura fija de 32 px, `width:
  auto`. Proporción original 2410×668 (≈3.6:1) — **DEBE preservarse**. Deformar el
  logo del cliente es inaceptable.
- El logo se sirve sobre fondo blanco o `--gris-050`. **NO DEBE** colocarse sobre
  teal, lima ni ninguna superficie de color: el wordmark es teal y desaparecería.
- **Pie:** insignia Qypher, altura 20 px, con el texto *«Qypher · Formación en
  Inteligencia Artificial»*.
- Ninguno de los dos logos DEBE recolorearse, rotarse, recortarse ni recibir sombra,
  filtro u opacidad menor a 1.
- Ambos DEBEN llevar `alt` descriptivo.

### Favicon
Se genera a partir del sol de hojas lima del logo, recortado cuadrado. Si el recorte
no queda legible a 32 px, se usa un cuadrado teal con la letra "B" en lima.

## Tipografía

**Stack del sistema, sin fuentes web** (ADR-004: nada de red en tiempo de ejecución):

```css
--fuente-ui:   -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               "Helvetica Neue", Arial, sans-serif;
--fuente-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas,
               "Liberation Mono", monospace;
```

El logo de Bios usa una humanista redondeada que no se intenta imitar; el stack
neutro no compite con él.

### Escala
Pensada para proyección: el mínimo es 14 px, no 12. Nadie lee 12 px desde la cuarta
fila.

| Rol | Tamaño / peso | Fuente |
|---|---|---|
| Título del tablero | 20 px / 600 | UI |
| Título de columna de nivel | 16 px / 600 | UI |
| Cuerpo | 15 px / 400 | UI |
| Etiqueta y métrica | 14 px / 500, `letter-spacing: .02em` | UI |
| **JSON de tool call** | 14 px / 400, `line-height: 1.5` | **Mono** |
| Respuesta final del agente | 16 px / 400 | UI |

El JSON crudo va en monoespaciada y con resaltado de sintaxis mínimo (claves en
`--teal-700`, strings en `--gris-700`, números en `--lima-700`). Es el elemento que se
proyecta y se compara contra el ebook: tiene que leerse cómodo.

## Componentes visuales

### Insignia de nivel
Estrellas del ebook (`☆☆☆` … `★★★★`) en un *chip*. Estrellas llenas en teal, vacías en
`--gris-300`. Se reusa la notación del documento a propósito: el participante la
reconoce.

### Columna de nivel (modo comparación)
```
┌──────────────────────────────┐
│ ★★☆  N3 · Tool caller        │  ← encabezado teal-050, borde superior teal 3px
│ run_function(tool, args)     │  ← mono 14px, gris-500
├──────────────────────────────┤
│ ○ llamada 1 al modelo        │  ← timeline vertical
│ ● tool_call  ▾               │     ● = completado (lima)
│   { "name": "consultar_...   │     ○ = en curso (teal, pulsando)
│ ● tool_result  12 ms  1 fila │     ✕ = error (error)
│ ○ llamada 2 al modelo        │
├──────────────────────────────┤
│ «La planta de Itagüí tiene…» │  ← respuesta, fondo blanco
├──────────────────────────────┤
│ 2 LLM · 1 tool · 1.4 s ·     │  ← pie de métricas, mono 14px
│ $0.0011                      │
└──────────────────────────────┘
```

### Estados de la línea de tiempo
| Estado | Color | Marca |
|---|---|---|
| Pendiente | `--gris-300` | `○` |
| En curso | `--teal-700` | `○` con pulso |
| Completado | `--lima-400` | `●` |
| Error | `--error` | `✕` |
| Aviso | `--alerta` | `⚠` |

La animación de pulso DEBE respetar `prefers-reduced-motion`.

### Medidor de gasto
En el encabezado, a la derecha: barra fina con el gasto acumulado contra `TOPE_USD`.
Teal hasta el 70%, `--alerta` de 70 a 90, `--error` sobre 90. Es control operativo
real (spec 09) y a la vez didáctico: el grupo ve el costo subir mientras experimenta.
