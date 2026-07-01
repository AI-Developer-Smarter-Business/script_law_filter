#!/usr/bin/env python3
"""
Filtrador de leads de despachos de abogados.

Herramienta reutilizable para procesar exportaciones CSV del scraper
sin modificar el código en cada campaña.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Configuración por defecto
# ---------------------------------------------------------------------------

CONFIG_DEFAULT: dict[str, Any] = {
    "archivo_entrada": "findlaw.csv",
    "archivo_salida": "firmas_filtradas.xlsx",
    "estados": [],
    "areas": [],
    "ciudades": [],
    "tamanio_min": None,
    "tamanio_max": None,
    "columna_tamanio": None,
    "columnas_salida": [
        "name",
        "address/city",
        "address/region",
        "phone",
        "email",
        "website",
        "areas",
    ],
    "separar_areas": True,
    "delimitador_csv": ";",
}

COLUMNAS_MINIMAS = ["name", "address/region"]
PREFIJO_AREAS = "practiceAreas/"
COLUMNA_AREAS = "areas"
COLUMNA_TAMANIO_CALCULADA = "num_areas_practica"
COLUMNA_CIUDAD = "address/city"
COLUMNA_ESTADO = "address/region"


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


class ErrorFiltrado(Exception):
    """Error amigable para el usuario final."""


def configurar_salida_consola() -> None:
    """Evita errores de encoding en terminales Windows."""
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def imprimir_ok(mensaje: str) -> None:
    print(f"  [OK] {mensaje}")


def imprimir_info(mensaje: str) -> None:
    print(f"  -> {mensaje}")


def imprimir_error(mensaje: str) -> None:
    print(f"\n[ERROR] {mensaje}\n", file=sys.stderr)


def cargar_config(ruta: str | None) -> dict[str, Any]:
    """Carga configuración desde YAML o devuelve valores por defecto."""
    config = CONFIG_DEFAULT.copy()

    if not ruta:
        return config

    path = Path(ruta)
    if not path.exists():
        raise ErrorFiltrado(
            f"No encontré el archivo de configuración: {path}\n"
            "Copia 'config.ejemplo.yaml' como 'config.yaml' y edítalo."
        )

    if yaml is None:
        raise ErrorFiltrado(
            "Falta instalar PyYAML. Activa .venv e instala: pip install -r requirements.txt"
        )

    with path.open(encoding="utf-8") as f:
        datos = yaml.safe_load(f) or {}

    if not isinstance(datos, dict):
        raise ErrorFiltrado("El archivo de configuración debe ser un listado YAML válido.")

    config.update(datos)
    return config


# ---------------------------------------------------------------------------
# Etapa 1: Cargar datos
# ---------------------------------------------------------------------------


def cargar_datos(ruta: str) -> pd.DataFrame:
    """Lee el CSV de entrada y valida que el archivo exista."""
    path = Path(ruta)

    if not path.exists():
        raise ErrorFiltrado(
            f"No encontré el archivo de entrada: {path}\n"
            "Verifica el nombre del archivo o la ruta en config.yaml."
        )

    if path.suffix.lower() != ".csv":
        raise ErrorFiltrado(
            f"El archivo '{path.name}' no parece ser un CSV.\n"
            "Usa la exportación directa del scraper en formato .csv."
        )

    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        raise ErrorFiltrado(f"El archivo '{path.name}' está vacío.") from None
    except Exception as exc:
        raise ErrorFiltrado(
            f"No pude leer '{path.name}'. ¿Está corrupto o abierto en Excel?\n"
            f"Detalle técnico: {exc}"
        ) from exc

    if df.empty:
        raise ErrorFiltrado(f"El archivo '{path.name}' no contiene filas de datos.")

    imprimir_ok(f"Archivo cargado: {path.name} ({len(df)} registros)")
    return df


# ---------------------------------------------------------------------------
# Etapa 2: Validar y preparar columnas
# ---------------------------------------------------------------------------


def validar_columnas(
    df: pd.DataFrame,
    columnas_salida: list[str],
    columna_tamanio: str | None,
) -> None:
    """Verifica que existan las columnas necesarias."""
    faltantes = [c for c in COLUMNAS_MINIMAS if c not in df.columns]
    if faltantes:
        raise ErrorFiltrado(
            "El CSV no tiene las columnas mínimas requeridas:\n"
            f"  Faltan: {', '.join(faltantes)}\n"
            "¿Es una exportación del scraper de FindLaw?"
        )

    columnas_practica = obtener_columnas_practica(df)
    if not columnas_practica:
        imprimir_info(
            "No encontré columnas practiceAreas/*. "
            "El filtro por áreas no estará disponible."
        )

    salida_sin_areas = [c for c in columnas_salida if c != COLUMNA_AREAS]
    faltantes_salida = [c for c in salida_sin_areas if c not in df.columns]
    if faltantes_salida:
        raise ErrorFiltrado(
            "Algunas columnas de salida no existen en el archivo:\n"
            f"  {', '.join(faltantes_salida)}\n"
            "Revisa 'columnas_salida' en config.yaml o usa --listar-columnas."
        )

    if columna_tamanio and columna_tamanio not in df.columns:
        raise ErrorFiltrado(
            f"La columna de tamaño '{columna_tamanio}' no existe en el CSV.\n"
            "Quita 'columna_tamanio' del config o usa el tamaño calculado por defecto."
        )


def obtener_columnas_practica(df: pd.DataFrame) -> list[str]:
    """Devuelve las columnas de áreas de práctica."""
    return [c for c in df.columns if PREFIJO_AREAS in c]


def combinar_areas(df: pd.DataFrame) -> pd.DataFrame:
    """Crea la columna 'areas' juntando todas las áreas de práctica."""
    df = df.copy()
    columnas_practica = obtener_columnas_practica(df)

    if not columnas_practica:
        df[COLUMNA_AREAS] = ""
        return df

    df[COLUMNA_AREAS] = (
        df[columnas_practica]
        .fillna("")
        .astype(str)
        .apply(
            lambda fila: " ".join(parte for parte in fila if parte and parte != "nan"),
            axis=1,
        )
        .str.strip()
    )
    return df


def calcular_tamanio(df: pd.DataFrame, columna_tamanio: str | None) -> pd.DataFrame:
    """Agrega columna numérica para filtrar por tamaño del despacho."""
    df = df.copy()

    if columna_tamanio and columna_tamanio in df.columns:
        df[COLUMNA_TAMANIO_CALCULADA] = pd.to_numeric(
            df[columna_tamanio], errors="coerce"
        ).fillna(0)
        return df

    columnas_practica = obtener_columnas_practica(df)
    if columnas_practica:
        df[COLUMNA_TAMANIO_CALCULADA] = df[columnas_practica].notna().sum(axis=1)
    else:
        df[COLUMNA_TAMANIO_CALCULADA] = 0

    return df


# ---------------------------------------------------------------------------
# Etapa 3: Filtros
# ---------------------------------------------------------------------------


def filtrar_por_estados(df: pd.DataFrame, estados: list[str]) -> pd.DataFrame:
    if not estados:
        return df

    estados_upper = [e.upper() for e in estados]
    filtrado = df[df[COLUMNA_ESTADO].astype(str).str.upper().isin(estados_upper)]
    imprimir_ok(f"Filtro estados {estados_upper}: {len(filtrado)} registros")
    return filtrado


def filtrar_por_areas(df: pd.DataFrame, areas: list[str]) -> pd.DataFrame:
    if not areas:
        return df

    mascara = pd.Series(False, index=df.index)
    for area in areas:
        mascara = mascara | df[COLUMNA_AREAS].str.contains(area, case=False, na=False)

    filtrado = df[mascara]
    imprimir_ok(f"Filtro áreas {areas}: {len(filtrado)} registros")
    return filtrado


def filtrar_por_ciudades(df: pd.DataFrame, ciudades: list[str]) -> pd.DataFrame:
    if not ciudades:
        return df

    ciudades_lower = [c.lower() for c in ciudades]
    filtrado = df[df[COLUMNA_CIUDAD].astype(str).str.lower().isin(ciudades_lower)]
    imprimir_ok(f"Filtro ciudades {ciudades}: {len(filtrado)} registros")
    return filtrado


def filtrar_por_tamanio(
    df: pd.DataFrame,
    tamanio_min: int | None,
    tamanio_max: int | None,
) -> pd.DataFrame:
    if tamanio_min is None and tamanio_max is None:
        return df

    filtrado = df.copy()
    if tamanio_min is not None:
        filtrado = filtrado[filtrado[COLUMNA_TAMANIO_CALCULADA] >= tamanio_min]
    if tamanio_max is not None:
        filtrado = filtrado[filtrado[COLUMNA_TAMANIO_CALCULADA] <= tamanio_max]

    max_label = tamanio_max if tamanio_max is not None else "sin maximo"
    min_label = tamanio_min if tamanio_min is not None else "sin minimo"
    imprimir_ok(f"Filtro tamano ({min_label} - {max_label}): {len(filtrado)} registros")
    return filtrado


def aplicar_filtros(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Aplica todos los filtros configurados en secuencia."""
    df = combinar_areas(df)
    df = calcular_tamanio(df, config.get("columna_tamanio"))

    estados = config.get("estados") or []
    areas = config.get("areas") or []
    ciudades = config.get("ciudades") or []

    if estados:
        df = filtrar_por_estados(df, estados)
    else:
        imprimir_info("Sin filtro de estados (se incluyen todos)")

    if areas:
        df = filtrar_por_areas(df, areas)
    else:
        imprimir_info("Sin filtro de áreas (se incluyen todas)")

    df = filtrar_por_ciudades(df, ciudades)

    tamanio_min = config.get("tamanio_min")
    tamanio_max = config.get("tamanio_max")
    df = filtrar_por_tamanio(df, tamanio_min, tamanio_max)

    return df


# ---------------------------------------------------------------------------
# Etapa 4: Exportar
# ---------------------------------------------------------------------------


def obtener_columnas_practica_con_datos(df: pd.DataFrame) -> list[str]:
    """Columnas practiceAreas/* del archivo original que tienen datos."""
    return [c for c in obtener_columnas_practica(df) if df[c].notna().any()]


def preparar_datos_exportacion(
    df: pd.DataFrame,
    columnas_salida: list[str],
    separar_areas: bool,
) -> pd.DataFrame:
    """Selecciona columnas conservando los nombres originales del CSV de entrada."""
    columnas = [c for c in columnas_salida if c in df.columns or c == COLUMNA_AREAS]

    if COLUMNA_AREAS in columnas_salida and COLUMNA_AREAS not in columnas:
        columnas.append(COLUMNA_AREAS)

    incluir_areas = COLUMNA_AREAS in columnas
    columnas_base = [c for c in columnas if c != COLUMNA_AREAS]
    resultado = df[columnas_base].copy()

    if incluir_areas:
        if separar_areas:
            columnas_practica = obtener_columnas_practica_con_datos(df)
            for col in columnas_practica:
                resultado[col] = df[col]
        else:
            resultado[COLUMNA_AREAS] = df[COLUMNA_AREAS]

    return resultado


def guardar_archivo(
    resultado: pd.DataFrame,
    ruta_salida: str,
    delimitador_csv: str,
    convertir: bool = False,
) -> Path:
    """Guarda en Excel (.xlsx) o CSV con delimitador compatible con Excel."""
    path = Path(ruta_salida)
    extension = path.suffix.lower()

    if convertir and extension not in (".xlsx", ".xls"):
        path = path.with_suffix(".xlsx")
        extension = path.suffix.lower()

    try:
        if extension in (".xlsx", ".xls"):
            resultado.to_excel(path, index=False, engine="openpyxl")
        else:
            resultado.to_csv(
                path,
                index=False,
                encoding="utf-8-sig",
                sep=delimitador_csv,
            )
    except ImportError as exc:
        if extension in (".xlsx", ".xls"):
            raise ErrorFiltrado(
                "Falta instalar openpyxl para exportar Excel. "
                "Activa .venv e instala: pip install -r requirements.txt"
            ) from exc
        raise
    except PermissionError:
        raise ErrorFiltrado(
            f"No pude guardar '{path.name}'. ¿Lo tienes abierto en Excel? "
            "Ciérralo e intenta de nuevo."
        ) from None

    return path


def exportar(
    df: pd.DataFrame,
    ruta_salida: str,
    columnas_salida: list[str],
    vista_previa: int | None = None,
    separar_areas: bool = True,
    delimitador_csv: str = ";",
) -> None:
    """Guarda el resultado o muestra una vista previa."""
    resultado = preparar_datos_exportacion(df, columnas_salida, separar_areas)

    if vista_previa:
        print(f"\n--- Vista previa (primeras {vista_previa} filas) ---\n")
        print(resultado.head(vista_previa).to_string(index=False))
        print(f"\nTotal despues de filtros: {len(resultado)} registros\n")
        return

    path = guardar_archivo(resultado, ruta_salida, delimitador_csv)
    formato = "Excel" if path.suffix.lower() in (".xlsx", ".xls") else "CSV"
    imprimir_ok(f"Archivo exportado ({formato}): {path.name} ({len(resultado)} leads)")


# ---------------------------------------------------------------------------
# Comandos de exploración
# ---------------------------------------------------------------------------


def listar_valores_unicos(df: pd.DataFrame, tipo: str) -> None:
    if tipo == "estados":
        valores = sorted(df[COLUMNA_ESTADO].dropna().astype(str).unique())
        titulo = "Estados disponibles"
    elif tipo == "ciudades":
        valores = sorted(df[COLUMNA_CIUDAD].dropna().astype(str).unique())
        titulo = "Ciudades disponibles"
    elif tipo == "areas":
        columnas = obtener_columnas_practica(df)
        valores_set: set[str] = set()
        for col in columnas:
            valores_set.update(df[col].dropna().astype(str).unique())
        valores = sorted(valores_set)
        titulo = "Áreas de práctica disponibles"
    else:
        return

    print(f"\n{titulo} ({len(valores)}):\n")
    for valor in valores:
        print(f"  - {valor}")
    print()


def listar_columnas(df: pd.DataFrame) -> None:
    print("\nColumnas disponibles en el archivo:\n")
    for col in df.columns:
        print(f"  - {col}")
    print()


# ---------------------------------------------------------------------------
# Modo interactivo
# ---------------------------------------------------------------------------


def _preguntar(mensaje: str, valor_default: str) -> str | None:
    valor = input(f"{mensaje} [{valor_default}]: ").strip()
    return valor if valor else None


def _split_lista(texto: str) -> list[str]:
    """Separa valores por coma o punto y coma (CA, TX o CA; TX)."""
    return [parte.strip() for parte in re.split(r"[,;]", texto) if parte.strip()]


def modo_interactivo(config: dict[str, Any]) -> dict[str, Any]:
    print("\n" + "=" * 55)
    print("  FILTRADOR DE LEADS - Modo guiado")
    print("=" * 55 + "\n")

    entrada = _preguntar("Archivo CSV de entrada", config["archivo_entrada"])
    if entrada:
        config["archivo_entrada"] = entrada

    print("\nEstados (CA, TX — separados por coma; Enter = todos): ", end="")
    estados_raw = input().strip()
    if estados_raw:
        config["estados"] = [e.upper() for e in _split_lista(estados_raw)]

    print("Areas de practica (Enter = todas, sin filtrar por area): ", end="")
    areas_raw = input().strip()
    if areas_raw:
        config["areas"] = _split_lista(areas_raw)

    print("Ciudades (separadas por coma; Enter = todas): ", end="")
    ciudades_raw = input().strip()
    if ciudades_raw:
        config["ciudades"] = _split_lista(ciudades_raw)

    print("Tamaño mínimo (nº de áreas, Enter = sin mínimo): ", end="")
    min_raw = input().strip()
    if min_raw:
        config["tamanio_min"] = int(min_raw)

    print("Tamaño máximo (Enter = sin máximo): ", end="")
    max_raw = input().strip()
    if max_raw:
        config["tamanio_max"] = int(max_raw)

    salida = _preguntar("Archivo de salida", config["archivo_salida"])
    if salida:
        config["archivo_salida"] = salida

    print()
    return config


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filtrar_leads.py",
        description=(
            "Filtra leads de despachos de abogados desde un CSV del scraper.\n"
            "Pensado para marketing: usa --interactivo o un archivo config.yaml."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  python filtrar_leads.py --interactivo\n"
            "  python filtrar_leads.py --config config.yaml\n"
            "  python filtrar_leads.py --estados CA IL --areas \"Personal Injury\"\n"
            "  python filtrar_leads.py --listar-estados\n"
        ),
    )

    parser.add_argument(
        "--config",
        help="Archivo de configuración YAML (copia config.ejemplo.yaml como config.yaml).",
    )
    parser.add_argument(
        "--interactivo",
        "-i",
        action="store_true",
        help="Modo guiado paso a paso (recomendado si no programas).",
    )
    parser.add_argument(
        "--convertir",
        action="store_true",
        help="Convierte un CSV a XLSX preservando cada columna por su nombre original.",
    )
    parser.add_argument(
        "--archivo",
        help="Archivo CSV de entrada.",
    )
    parser.add_argument(
        "--salida",
        help="Archivo CSV de salida.",
    )
    parser.add_argument(
        "--estados",
        nargs="*",
        help="Estados a incluir (ej: CA IL TX).",
    )
    parser.add_argument(
        "--areas",
        nargs="*",
        help='Áreas de práctica (ej: "Personal Injury").',
    )
    parser.add_argument(
        "--ciudades",
        nargs="*",
        help="Ciudades a incluir.",
    )
    parser.add_argument(
        "--tamanio-min",
        type=int,
        help="Tamaño mínimo (número de áreas de práctica).",
    )
    parser.add_argument(
        "--tamanio-max",
        type=int,
        help="Tamaño máximo.",
    )
    parser.add_argument(
        "--vista-previa",
        type=int,
        metavar="N",
        help="Muestra N filas en pantalla sin exportar.",
    )
    parser.add_argument(
        "--listar-estados",
        action="store_true",
        help="Lista estados disponibles en el CSV.",
    )
    parser.add_argument(
        "--listar-areas",
        action="store_true",
        help="Lista áreas de práctica disponibles.",
    )
    parser.add_argument(
        "--listar-ciudades",
        action="store_true",
        help="Lista ciudades disponibles.",
    )
    parser.add_argument(
        "--listar-columnas",
        action="store_true",
        help="Lista todas las columnas del CSV.",
    )

    return parser


def fusionar_config(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    """Los argumentos de línea de comandos sobrescriben el config file."""
    if args.archivo:
        config["archivo_entrada"] = args.archivo
    if args.salida:
        config["archivo_salida"] = args.salida
    if args.estados is not None and len(args.estados) > 0:
        config["estados"] = args.estados
    if args.areas is not None and len(args.areas) > 0:
        config["areas"] = args.areas
    if args.ciudades is not None and len(args.ciudades) > 0:
        config["ciudades"] = args.ciudades
    if args.tamanio_min is not None:
        config["tamanio_min"] = args.tamanio_min
    if args.tamanio_max is not None:
        config["tamanio_max"] = args.tamanio_max
    return config


def main() -> int:
    configurar_salida_consola()
    parser = construir_parser()
    args = parser.parse_args()

    print("\nFiltrador de Leads - Despachos de Abogados\n")

    try:
        config = cargar_config(args.config)

        if args.convertir:
            config = fusionar_config(config, args)
        elif args.interactivo:
            config = modo_interactivo(config)
        else:
            config = fusionar_config(config, args)

        df = cargar_datos(config["archivo_entrada"])

        if args.convertir:
            guardar_archivo(
                df,
                config["archivo_salida"],
                config.get("delimitador_csv", ";"),
                convertir=True,
            )
            imprimir_ok(
                f"CSV convertido a Excel: {Path(config['archivo_salida']).with_suffix('.xlsx').name}"
            )
            print("\nProceso completado.\n")
            return 0

        if args.listar_estados:
            listar_valores_unicos(df, "estados")
            return 0
        if args.listar_areas:
            listar_valores_unicos(df, "areas")
            return 0
        if args.listar_ciudades:
            listar_valores_unicos(df, "ciudades")
            return 0
        if args.listar_columnas:
            listar_columnas(df)
            return 0

        validar_columnas(
            df,
            config["columnas_salida"],
            config.get("columna_tamanio"),
        )

        df_filtrado = aplicar_filtros(df, config)

        print(f"\n  Resultado: {len(df_filtrado)} leads encontrados\n")

        if len(df_filtrado) == 0:
            imprimir_info(
                "No hay resultados con esos filtros. "
                "Prueba ampliar estados, áreas o ciudades."
            )

        exportar(
            df_filtrado,
            config["archivo_salida"],
            config["columnas_salida"],
            vista_previa=args.vista_previa,
            separar_areas=config.get("separar_areas", True),
            delimitador_csv=config.get("delimitador_csv", ";"),
        )

        print("\nProceso completado.\n")
        return 0

    except ErrorFiltrado as exc:
        imprimir_error(str(exc))
        return 1
    except KeyboardInterrupt:
        print("\n\nOperación cancelada.\n")
        return 130
    except ValueError as exc:
        imprimir_error(f"Valor inválido en los filtros: {exc}")
        return 1
    except Exception as exc:
        imprimir_error(
            f"Ocurrió un error inesperado.\n"
            f"Detalle: {exc}\n"
            "Si persiste, contacta al equipo técnico."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
