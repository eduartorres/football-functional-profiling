"""
Adquisición del conjunto integrado de eventos y posiciones de la DFL (Bassek et al., 2025).

Descarga el artículo de Figshare 28196177 (siete partidos de Bundesliga y 2. Bundesliga 2022/23, archivos XML)
en data/raw/dfl. La primera ejecución fija la versión del artículo en manifests/dfl_source_lock.json para que
descargas posteriores no mezclen versiones; el inventario con SHA-256 queda en manifests/dfl_manifest.json.

Uso, desde la raíz del repositorio:
    python -m src.ingestion.ingest_dfl --list
    python -m src.ingestion.ingest_dfl --download
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Configuración

API_BASE = "https://api.figshare.com/v2"

ARTICLE_ID = 28196177
EXPECTED_DOI = "10.6084/m9.figshare.28196177"

RAW_DIR = Path("data/raw/dfl")
MANIFEST_PATH = Path("manifests/dfl_manifest.json")
LOCK_PATH = Path("manifests/dfl_source_lock.json")

REQUEST_DELAY_SECONDS = 1.05
CHUNK_SIZE = 1024 * 1024  # 1 MB


# Utilidades


def api_get(path: str):
    """
    Realiza una consulta GET a la API pública de Figshare.
    """

    url = f"{API_BASE}{path}"

    request = Request(
        url,
        headers={"User-Agent": "football-functional-profiling/1.0"},
    )

    try:
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    except HTTPError as exc:
        print(f"ERROR HTTP {exc.code}: {url}")
        raise

    except URLError as exc:
        print(f"ERROR de conexión: {exc.reason}")
        raise


def human_size(num_bytes: int) -> str:
    """
    Convierte bytes a una representación legible.
    """

    value = float(num_bytes)

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024:
            return f"{value:.2f} {unit}"

        value /= 1024

    return f"{value:.2f} PB"


def sha256_file(path: Path) -> str:
    """
    Calcula SHA-256 de un archivo local.
    """

    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(CHUNK_SIZE)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


# Consultas a Figshare


def get_article():
    """
    Consulta los metadatos generales del artículo DFL.
    """

    return api_get(f"/articles/{ARTICLE_ID}")


def get_files(version: int):
    """
    Obtiene todos los archivos correspondientes a una
    versión específica del artículo, manejando la
    paginación de Figshare.
    """

    files = []

    page = 1
    page_size = 100

    while True:
        batch = api_get(f"/articles/{ARTICLE_ID}/versions/{version}/files?page={page}&page_size={page_size}")

        files.extend(batch)

        if len(batch) < page_size:
            break

        page += 1

        time.sleep(REQUEST_DELAY_SECONDS)

    return files


# Bloqueo de versión


def validate_or_create_lock(article):
    """
    Guarda la versión del dataset utilizada por el proyecto.

    Si posteriormente Figshare publica una versión nueva,
    el script se detendrá en lugar de cambiar los datos
    silenciosamente.
    """

    LOCK_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    remote_version = article.get("version")

    remote_doi = article.get("doi") or EXPECTED_DOI

    if LOCK_PATH.exists():
        with LOCK_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            lock = json.load(file)

        locked_version = lock["version"]

        if remote_version != locked_version:
            raise RuntimeError(
                "\n"
                "La versión del dataset DFL cambió.\n\n"
                f"Versión utilizada por el proyecto: "
                f"{locked_version}\n"
                f"Versión actual en Figshare: "
                f"{remote_version}\n\n"
                "El script no descargará automáticamente "
                "una versión diferente."
            )

    else:
        lock = {
            "provider": "DFL / Sportec Solutions",
            "dataset": article.get("title"),
            "figshare_article_id": ARTICLE_ID,
            "version": remote_version,
            "doi": remote_doi,
            "locked_at_utc": datetime.now(timezone.utc).isoformat(),
        }

        with LOCK_PATH.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                lock,
                file,
                indent=2,
                ensure_ascii=False,
            )

        print(f"Versión {remote_version} fijada en {LOCK_PATH}")


# Inventario


def build_inventory():
    """
    Consulta el artículo, valida la versión y recupera
    todos los archivos asociados.
    """

    article = get_article()

    validate_or_create_lock(article)

    version = article.get("version")

    files = get_files(version)

    total_size = sum(
        int(
            file_info.get(
                "size",
                0,
            )
        )
        for file_info in files
    )

    print()

    print("=" * 78)

    print("DFL / IDSSE — FIGSHARE")

    print("=" * 78)

    print(f"Título     : {article.get('title')}")

    print(f"Article ID : {ARTICLE_ID}")

    print(f"Versión    : {version}")

    print(f"DOI        : {article.get('doi') or EXPECTED_DOI}")

    license_info = article.get("license")

    if isinstance(
        license_info,
        dict,
    ):
        license_name = license_info.get("name") or "Consultar Figshare"

    else:
        license_name = license_info or "Consultar Figshare"

    print(f"Licencia   : {license_name}")

    print()

    print("ARCHIVOS")

    print("-" * 78)

    inventory = []

    for file_info in files:
        size = int(
            file_info.get(
                "size",
                0,
            )
        )

        print(f"{file_info.get('name'):<60}{human_size(size):>16}")

        inventory.append(
            {
                "file_id": file_info.get("id"),
                "name": file_info.get("name"),
                "size": size,
                "download_url": file_info.get("download_url"),
            }
        )

    print("-" * 78)

    print(f"Archivos : {len(files)}")

    print(f"Tamaño   : {human_size(total_size)}")

    print("=" * 78)

    return (
        article,
        inventory,
    )


# Descarga


def download_file(
    url: str,
    destination: Path,
):
    """
    Descarga un archivo utilizando un .part temporal.

    El archivo final solo aparece cuando la descarga
    termina correctamente.
    """

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = destination.with_suffix(destination.suffix + ".part")

    request = Request(
        url,
        headers={"User-Agent": "football-functional-profiling/1.0"},
    )

    with urlopen(
        request,
        timeout=300,
    ) as response:
        total = int(
            response.headers.get(
                "Content-Length",
                0,
            )
        )

        downloaded = 0

        with temporary.open("wb") as output:
            while True:
                chunk = response.read(CHUNK_SIZE)

                if not chunk:
                    break

                output.write(chunk)

                downloaded += len(chunk)

                if total:
                    percentage = downloaded / total * 100

                    print(
                        f"\r    {percentage:6.2f}% ({human_size(downloaded)} / {human_size(total)})",
                        end="",
                    )

    temporary.replace(destination)

    print()


# Descarga completa del dataset


def download_dataset(
    article,
    inventory,
):
    """
    Descarga todos los archivos y genera el manifiesto
    reproducible del dataset.
    """

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    MANIFEST_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    downloaded_files = []

    total_files = len(inventory)

    for index, file_info in enumerate(
        inventory,
        start=1,
    ):
        destination = RAW_DIR / file_info["name"]

        expected_size = file_info["size"]

        print()

        print(f"[{index}/{total_files}] {file_info['name']}")

        if destination.exists():
            local_size = destination.stat().st_size

            if local_size == expected_size:
                print("    Ya existe con el tamaño esperado.")

            else:
                print("    El archivo existe pero el tamaño no coincide.")

                print("    Se descargará nuevamente.")

                destination.unlink()

                download_file(
                    file_info["download_url"],
                    destination,
                )

        else:
            download_file(
                file_info["download_url"],
                destination,
            )

        print("    Calculando SHA-256...")

        local_sha256 = sha256_file(destination)

        downloaded_files.append(
            {
                "file_id": file_info["file_id"],
                "file_name": file_info["name"],
                "figshare_size_bytes": expected_size,
                "local_size_bytes": destination.stat().st_size,
                "local_path": str(destination),
                "sha256": local_sha256,
                "download_url": file_info["download_url"],
            }
        )

    manifest = {
        "provider": "DFL / Sportec Solutions",
        "repository": "Springer Nature Figshare",
        "dataset_title": article.get("title"),
        "article_id": ARTICLE_ID,
        "article_version": article.get("version"),
        "doi": article.get("doi") or EXPECTED_DOI,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "number_of_files": len(downloaded_files),
        "downloaded_files": downloaded_files,
    }

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

    print()

    print("=" * 78)

    print("DESCARGA DFL FINALIZADA")

    print("=" * 78)

    print(f"Datos      : {RAW_DIR}")

    print(f"Manifiesto : {MANIFEST_PATH}")

    print(f"Lock       : {LOCK_PATH}")

    print(f"Archivos   : {len(downloaded_files)}")

    print("=" * 78)


# Punto de entrada


def main():

    parser = argparse.ArgumentParser(
        description=("Ingestión reproducible del DFL / IDSSE dataset desde Figshare.")
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help=("Lista todos los archivos sin descargarlos."),
    )

    parser.add_argument(
        "--download",
        action="store_true",
        help=("Descarga todos los archivos y genera el manifiesto."),
    )

    args = parser.parse_args()

    if not args.list and not args.download:
        parser.print_help()

        sys.exit(0)

    article, inventory = build_inventory()

    if args.download:
        download_dataset(
            article,
            inventory,
        )


if __name__ == "__main__":
    main()
