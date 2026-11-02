"""
Registro de procedencia de los datos de PFF FC del Mundial 2022.

PFF distribuye el conjunto por una carpeta compartida de Google Drive, previa inscripción; la copia local se hizo
con rclone en data/raw/pff. Este script no descarga: inventaría la carpeta, calcula SHA-256 por archivo, escribe
manifests/pff_manifest.json y manifests/pff_source.txt, y verifica la copia local contra el manifiesto.

Uso, desde la raíz del repositorio:
    python -m src.ingestion.ingest_pff --list
    python -m src.ingestion.ingest_pff --manifest
    python -m src.ingestion.ingest_pff --verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Configuración

RAW_DIR = Path("data/raw/pff")

MANIFEST_PATH = Path("manifests/pff_manifest.json")

SOURCE_PATH = Path("manifests/pff_source.txt")

CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB


# Archivos generados por macOS que no pertenecen
# realmente al dataset.
IGNORE_NAMES = {
    ".DS_Store",
}

IGNORE_PREFIXES = ("._",)


# Utilidades


def human_size(num_bytes: int) -> str:
    """
    Convierte bytes a una representación legible.
    """

    value = float(num_bytes)

    for unit in [
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    ]:
        if value < 1024:
            return f"{value:.2f} {unit}"

        value /= 1024

    return f"{value:.2f} PB"


def sha256_file(path: Path) -> str:
    """
    Calcula el SHA-256 de un archivo.
    """

    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(CHUNK_SIZE)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def should_ignore(path: Path) -> bool:
    """
    Excluye metadatos creados localmente por macOS.
    """

    if path.name in IGNORE_NAMES:
        return True

    if path.name.startswith(IGNORE_PREFIXES):
        return True

    return False


def get_top_level_group(
    relative_path: Path,
) -> str:
    """
    Devuelve la carpeta principal del archivo.

    Ejemplo:
    Tracking Data/123/file.json
    -> Tracking Data

    Si el archivo está directamente en la raíz:
    competitions.csv
    -> ROOT
    """

    if len(relative_path.parts) > 1:
        return relative_path.parts[0]

    return "ROOT"


# Inventario


def collect_files():
    """
    Localiza todos los archivos pertenecientes
    al snapshot RAW de PFF.
    """

    if not RAW_DIR.exists():
        raise FileNotFoundError(f"No existe la carpeta {RAW_DIR}")

    files = []

    ignored = []

    for path in RAW_DIR.rglob("*"):
        if not path.is_file():
            continue

        if should_ignore(path):
            ignored.append(path)
            continue

        files.append(path)

    files.sort(key=lambda p: str(p).lower())

    return files, ignored


# Resumen inicial


def print_inventory_summary(
    files,
    ignored,
):
    """
    Muestra el contenido general antes de
    calcular hashes.
    """

    groups = defaultdict(
        lambda: {
            "files": 0,
            "bytes": 0,
        }
    )

    total_bytes = 0

    for path in files:
        relative = path.relative_to(RAW_DIR)

        group = get_top_level_group(relative)

        size = path.stat().st_size

        groups[group]["files"] += 1
        groups[group]["bytes"] += size

        total_bytes += size

    print()

    print("=" * 74)

    print("PFF FC — FIFA WORLD CUP 2022")

    print("=" * 74)

    print(f"Directorio : {RAW_DIR}")

    print(f"Archivos   : {len(files)}")

    print(f"Tamaño     : {human_size(total_bytes)}")

    if ignored:
        print(f"Ignorados  : {len(ignored)} (metadatos locales)")

    print()

    print("CONTENIDO POR GRUPO")

    print("-" * 74)

    for group in sorted(groups.keys()):
        info = groups[group]

        print(f"{group:<30}{info['files']:>8} archivos{human_size(info['bytes']):>18}")

    print("-" * 74)

    return groups, total_bytes


# Manifiesto


def build_manifest(
    files,
    ignored,
    groups,
    total_bytes,
):
    """
    Calcula SHA-256 de todos los archivos y
    genera el manifiesto reproducible.
    """

    records = []

    total_files = len(files)

    print()

    print("=" * 74)

    print("GENERANDO MANIFIESTO Y SHA-256")

    print("=" * 74)

    print("Este proceso puede tardar unos minutos porque se leerán los ~5 GB completos.")

    print()

    for index, path in enumerate(
        files,
        start=1,
    ):
        relative = path.relative_to(RAW_DIR)

        size = path.stat().st_size

        print(f"[{index:03d}/{total_files:03d}] {relative} ({human_size(size)})")

        checksum = sha256_file(path)

        stat = path.stat()

        records.append(
            {
                "relative_path": relative.as_posix(),
                "file_name": path.name,
                "top_level_group": get_top_level_group(relative),
                "extension": path.suffix.lower(),
                "size_bytes": size,
                "sha256": checksum,
                "local_modified_at_utc": datetime.fromtimestamp(
                    stat.st_mtime,
                    tz=timezone.utc,
                ).isoformat(),
            }
        )

    group_summary = {}

    for group, info in groups.items():
        group_summary[group] = {
            "file_count": info["files"],
            "size_bytes": info["bytes"],
            "size_human": human_size(info["bytes"]),
        }

    manifest = {
        "provider": "PFF FC",
        "dataset": "FIFA World Cup 2022",
        "source_type": "Google Drive shared dataset",
        "acquisition_method": "rclone",
        "remote_name": "pff_drive",
        "remote_path": "FIFA World Cup 2022",
        "local_raw_path": str(RAW_DIR),
        "retrieved_and_manifested_at_utc": datetime.now(timezone.utc).isoformat(),
        "integrity_algorithm": "SHA-256",
        "total_files": total_files,
        "total_size_bytes": total_bytes,
        "total_size_human": human_size(total_bytes),
        "groups": group_summary,
        "ignored_local_files": [str(path.relative_to(RAW_DIR)) for path in ignored],
        "files": records,
    }

    MANIFEST_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with MANIFEST_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            manifest,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return manifest


# Registro simple de fuente


def write_source_file(
    total_files,
    total_bytes,
):
    """
    Genera un registro legible y breve de
    procedencia del dataset.
    """

    SOURCE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    lines = [
        "provider=PFF FC",
        "dataset=FIFA World Cup 2022",
        "source=Google Drive shared dataset",
        "acquisition_method=rclone",
        "remote=pff_drive:FIFA World Cup 2022",
        f"local_path={RAW_DIR}",
        f"files={total_files}",
        f"size_bytes={total_bytes}",
        (f"manifest={MANIFEST_PATH}"),
        (f"recorded_at_utc={datetime.now(timezone.utc).isoformat()}"),
    ]

    SOURCE_PATH.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


# Verificación del manifiesto


def verify_manifest():
    """
    Compara los archivos actuales contra
    el manifiesto previamente generado.
    """

    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"No existe {MANIFEST_PATH}. Primero ejecuta --manifest.")

    with MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    records = manifest["files"]

    problems = []

    print()

    print("=" * 74)

    print("VERIFICANDO INTEGRIDAD DE PFF")

    print("=" * 74)

    total = len(records)

    for index, record in enumerate(
        records,
        start=1,
    ):
        path = RAW_DIR / record["relative_path"]

        print(f"[{index:03d}/{total:03d}] {record['relative_path']}")

        if not path.exists():
            problems.append(
                {
                    "path": record["relative_path"],
                    "problem": "missing",
                }
            )

            continue

        if path.stat().st_size != record["size_bytes"]:
            problems.append(
                {
                    "path": record["relative_path"],
                    "problem": "size_mismatch",
                }
            )

            continue

        current_hash = sha256_file(path)

        if current_hash != record["sha256"]:
            problems.append(
                {
                    "path": record["relative_path"],
                    "problem": "sha256_mismatch",
                }
            )

    print()

    if problems:
        print("Se encontraron problemas:")

        for problem in problems:
            print(f"  - {problem['path']}: {problem['problem']}")

        return False

    print("Todos los archivos coinciden con el manifiesto.")

    return True


# Punto de entrada


def main():

    parser = argparse.ArgumentParser(
        description=("Inventario y control de integridad del PFF FC FIFA World Cup 2022 dataset.")
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help=("Muestra el inventario general sin calcular SHA-256."),
    )

    parser.add_argument(
        "--manifest",
        action="store_true",
        help=("Calcula SHA-256 y genera el manifiesto completo."),
    )

    parser.add_argument(
        "--verify",
        action="store_true",
        help=("Verifica los archivos actuales contra el manifiesto."),
    )

    args = parser.parse_args()

    if not (args.list or args.manifest or args.verify):
        parser.print_help()

        sys.exit(0)

    if args.verify:
        valid = verify_manifest()

        sys.exit(0 if valid else 1)

    files, ignored = collect_files()

    groups, total_bytes = print_inventory_summary(
        files,
        ignored,
    )

    if args.manifest:
        build_manifest(
            files,
            ignored,
            groups,
            total_bytes,
        )

        write_source_file(
            len(files),
            total_bytes,
        )

        print()

        print("=" * 74)

        print("PFF FINALIZADO")

        print("=" * 74)

        print(f"Datos      : {RAW_DIR}")

        print(f"Manifiesto : {MANIFEST_PATH}")

        print(f"Fuente     : {SOURCE_PATH}")

        print(f"Archivos   : {len(files)}")

        print(f"Tamaño     : {human_size(total_bytes)}")

        print("=" * 74)


if __name__ == "__main__":
    main()
