# Filtrador de Leads — Despachos de Abogados

Herramienta para filtrar exportaciones CSV del scraper de FindLaw y generar listas de leads listas para campañas de marketing.

**No necesitas saber programar.** Puedes usar el modo guiado o editar un archivo de configuración simple.

## Índice

- [Requisitos previos e instalación](#instalacion)
- [Activar el entorno virtual (.venv)](#activar-venv)
- [Inicio rápido (modo guiado)](#inicio-rapido)
- [Archivo de configuración](#configuracion)
- [Línea de comandos](#linea-de-comandos)
  - [Opciones disponibles](#opciones-disponibles)
- [Explorar el CSV](#explorar-csv)
- [Filtro por tamaño del despacho](#filtro-tamano)
- [Formato de salida (Excel vs CSV)](#formato-salida)
- [Columnas de salida](#columnas-salida)
- [Errores frecuentes](#errores-frecuentes)
- [Estructura del proyecto](#estructura-proyecto)
- [Flujo de trabajo típico](#flujo-trabajo)
- [Soporte](#soporte)

---

<a id="instalacion"></a>

## Requisitos previos (solo la primera vez)

1. Tener **Python 3.10+** instalado.  
   Descarga: [python.org/downloads](https://www.python.org/downloads/)  
   Durante la instalación, marca la casilla **"Add Python to PATH"**.

2. Abre una terminal **en esta carpeta** y crea el entorno virtual `.venv`:

```bash
python -m venv .venv
```

3. [Activa el entorno virtual](#activar-venv) e instala las dependencias:

```bash
pip install -r requirements.txt
```

> **Importante:** La instalación solo se hace una vez. Pero **cada vez** que abras una terminal nueva debes [activar `.venv`](#activar-venv) antes de ejecutar el script.

---

<a id="activar-venv"></a>

## Activar el entorno virtual (.venv)

**Haz esto siempre antes de usar el script** — en cada sesión nueva de terminal.

1. Abre una terminal en la carpeta `Law-firms`.
2. Ejecuta **uno** de estos comandos según tu terminal:

**Windows (CMD):**
```bash
.venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (Git Bash) / Mac / Linux:**
```bash
source .venv/Scripts/activate
```

3. Comprueba que funcionó: debe aparecer `(.venv)` al inicio de la línea, por ejemplo:

```
(.venv) C:\...\Law-firms>
```

4. Ya puedes ejecutar el script:

```bash
python filtrar_leads.py --interactivo
```

**Para desactivar** el entorno virtual cuando termines:

```bash
deactivate
```

> Si ves `ModuleNotFoundError: pandas` u otro error de módulo, casi siempre significa que **no activaste `.venv`**. Vuelve al paso 2.

---

<a id="inicio-rapido"></a>

## Inicio rápido (modo guiado)

La forma más fácil. **Primero [activa `.venv`](#activar-venv)**, luego ejecuta:

```bash
python filtrar_leads.py --interactivo
```

Te pedirá:
- Archivo CSV de entrada
- Estados (ej: `CA, IL, TX`)
- Áreas de práctica (ej: `Personal Injury, Employment Law`)
- Ciudades (opcional)
- Tamaño mínimo/máximo (opcional)
- Archivo de salida

Al terminar, encontrarás el CSV filtrado en la carpeta del proyecto.

---

<a id="configuracion"></a>

## Usar un archivo de configuración (recomendado para campañas repetidas)

1. Copia el archivo de ejemplo:

```bash
copy config.ejemplo.yaml config.yaml
```

2. Abre `config.yaml` con el Bloc de notas y edita los valores:

```yaml
archivo_entrada: findlaw.csv
archivo_salida: firmas_filtradas.csv
estados:
  - CA
  - IL
areas:
  - Personal Injury
ciudades: []
tamanio_min: null
tamanio_max: null
columnas_salida:
  - name
  - address/city
  - address/region
  - phone
  - email
  - website
  - areas
```

3. Ejecuta:

```bash
python filtrar_leads.py --config config.yaml
```

Para la próxima campaña, solo cambias `config.yaml` — **no hace falta tocar el código**.

---

<a id="linea-de-comandos"></a>

## Línea de comandos (sin archivo de configuración)

Todos los filtros se pueden pasar directamente:

```bash
# Varios estados y una área
python filtrar_leads.py --archivo findlaw.csv --estados CA IL --areas "Personal Injury"

# Filtrar por ciudades concretas
python filtrar_leads.py --estados CA --areas "Personal Injury" --ciudades Oakland Sacramento

# Filtrar por tamaño (número de áreas de práctica)
python filtrar_leads.py --estados CA --tamanio-min 3 --tamanio-max 15

# Vista previa sin exportar (muestra 10 filas en pantalla)
python filtrar_leads.py --config config.yaml --vista-previa 10
```

<a id="opciones-disponibles"></a>

### Opciones disponibles

| Opción | Descripción |
|--------|-------------|
| `--interactivo`, `-i` | Modo guiado paso a paso |
| `--config` | Archivo YAML de configuración |
| `--archivo` | CSV de entrada |
| `--salida` | CSV de salida |
| `--estados` | Uno o más estados (códigos de 2 letras) |
| `--areas` | Una o más áreas de práctica |
| `--ciudades` | Una o más ciudades |
| `--tamanio-min` | Mínimo de áreas de práctica |
| `--tamanio-max` | Máximo de áreas de práctica |
| `--vista-previa N` | Muestra N filas sin exportar |
| `--listar-estados` | Muestra estados disponibles en el CSV |
| `--listar-areas` | Muestra áreas de práctica disponibles |
| `--listar-ciudades` | Muestra ciudades disponibles |
| `--listar-columnas` | Muestra todas las columnas del CSV |

---

<a id="explorar-csv"></a>

## Explorar qué hay en tu CSV

Antes de filtrar, puedes ver qué valores existen:

```bash
python filtrar_leads.py --archivo findlaw.csv --listar-estados
python filtrar_leads.py --archivo findlaw.csv --listar-areas
python filtrar_leads.py --archivo findlaw.csv --listar-ciudades
python filtrar_leads.py --archivo findlaw.csv --listar-columnas
```

---

<a id="filtro-tamano"></a>

## Filtro por tamaño del despacho

El CSV actual no incluye una columna de tamaño. El script calcula automáticamente **`num_areas_practica`**: cuántas áreas de práctica tiene registradas cada despacho.

- Despachos pequeños suelen tener 1–3 áreas.
- Despachos medianos: 4–10.
- Despachos grandes: 11 o más.

Ejemplo en `config.yaml`:

```yaml
tamanio_min: 4
tamanio_max: 20
```

Si una exportación futura trae una columna propia (ej: `num_attorneys`), puedes usarla:

```yaml
columna_tamanio: num_attorneys
tamanio_min: 5
```

---

<a id="formato-salida"></a>

## Formato de salida (Excel vs CSV)

**Recomendado: `.xlsx`** — cada columna aparece en su propia celda al abrir en Excel, sin configuración extra.

```yaml
archivo_salida: firmas_filtradas.xlsx
```

Si prefieres CSV, usa extensión `.csv`. En Excel con configuración regional en español/portugués, las comas dentro de los datos hacen que todo quede en una sola celda si el delimitador no es el correcto. Por eso el CSV usa **`;`** como separador por defecto:

```yaml
archivo_salida: firmas_filtradas.csv
delimitador_csv: ";"
```

| Extensión | Comportamiento |
|-----------|----------------|
| `.xlsx` | Excel nativo, columnas siempre separadas |
| `.csv` | Texto plano con delimitador `;` (compatible con Excel regional) |

---

<a id="columnas-salida"></a>

## Columnas de salida

El CSV exportado **conserva los nombres originales en inglés** del archivo de entrada (`name`, `address/city`, `phone`, `practiceAreas/0`, etc.).

Por defecto se exportan:

| Columna | Descripción |
|---------|-------------|
| `name` | Nombre del despacho |
| `address/city` | Ciudad |
| `address/region` | Estado |
| `phone` | Teléfono |
| `email` | Email |
| `website` | Sitio web |
| `practiceAreas/0`, `practiceAreas/1`... | Cada área en su columna original |

Si incluyes `areas` en `columnas_salida` y `separar_areas: true`, se exportan las columnas `practiceAreas/*` del scraper en lugar de la columna combinada.

```yaml
separar_areas: false   # exporta una sola columna "areas" (generada al filtrar)
```

Puedes personalizar qué columnas exportar bajo `columnas_salida`. Usa `--listar-columnas` para ver todas las opciones del archivo.

---

<a id="errores-frecuentes"></a>

## Errores frecuentes

| Mensaje | Qué hacer |
|---------|-----------|
| `No encontré el archivo de entrada` | Verifica que el CSV esté en la carpeta o indica la ruta completa |
| `No pude guardar... ¿Lo tienes abierto en Excel?` | Cierra el archivo Excel y vuelve a ejecutar |
| `No hay resultados con esos filtros` | Amplía estados, áreas o ciudades; usa `--listar-*` para ver opciones |
| `Faltan columnas` | Confirma que el archivo sea una exportación del scraper FindLaw |
| `ModuleNotFoundError: pandas` | [Activa `.venv`](#activar-venv) e instala: `pip install -r requirements.txt` |

---

<a id="estructura-proyecto"></a>

## Estructura del proyecto

```
Law-firms/
├── .venv/                ← Entorno virtual (crear con python -m venv .venv)
├── filtrar_leads.py      ← Script principal (usa este)
├── config.ejemplo.yaml   ← Plantilla de configuración
├── config.yaml           ← Tu configuración (créala tú)
├── requirements.txt      ← Dependencias de Python
├── findlaw.csv           ← Exportación del scraper (ejemplo)
├── firmas_filtradas.xlsx  ← Resultado generado (recomendado)
```

---

<a id="flujo-trabajo"></a>

## Flujo de trabajo típico

```
0. Activas .venv          →  source .venv/Scripts/activate  (ver sección Activar venv)
1. Scraper exporta CSV    →  findlaw.csv
2. Editas config.yaml     →  estados, áreas, ciudades
3. Ejecutas el script     →  python filtrar_leads.py --config config.yaml
4. Abres el resultado     →  firmas_filtradas.xlsx en Excel
```

---

<a id="soporte"></a>

## Soporte

Si algo no funciona, anota el mensaje de error completo y contactame
