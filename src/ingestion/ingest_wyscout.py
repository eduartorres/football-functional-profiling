"""
Adquisición del conjunto público de eventos de Wyscout (Pappalardo et al., 2019).

Descarga los artículos de la colección de Figshare 4415000, versión 5 (DOI 10.6084/m9.figshare.c.4415000.v5),
en data/raw/wyscout y registra procedencia, tamaños y SHA-256 en manifests/wyscout_manifest.json.
Los ZIP se conservan tal como se descargaron; la extracción ocurre en src/harmonization.

Uso, desde la raíz del repositorio:
    python -m src.ingestion.ingest_wyscout --list
    python -m src.ingestion.ingest_wyscout --download
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Configuración fija de la fuente

API_BASE = "https://api.figshare.com/v2"

COLLECTION_ID = 4415000
EXPECTED_VERSION = 5
EXPECTED_DOI = "10.6084/m9.figshare.c.4415000.v5"

RAW_DIR = Path("data/raw/wyscout")
MANIFEST_PATH = Path("manifests/wyscout_manifest.json")

REQUEST_DELAY_SECONDS = 1.05
CHUNK_SIZE = 1024 * 1024  # 1 MB


# Utilidades


def api_get(path: str):
    """Realiza una consulta GET a la API pública de Figshare."""
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


def slugify(text: str) -> str:
    """Convierte un título en un nombre seguro para carpeta."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def human_size(num_bytes: int) -> str:
    """Convierte bytes a una representación legible."""
    value = float(num_bytes)

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024:
            return f"{value:.2f} {unit}"
        value /= 1024

    return f"{value:.2f} PB"


def sha256_file(path: Path) -> str:
    """Calcula SHA-256 para verificar integridad local."""
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(CHUNK_SIZE)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


# Figshare


def get_collection():
    collection = api_get(f"/collections/{COLLECTION_ID}")

    current_version = collection.get("version")

    if current_version != EXPECTED_VERSION:
        raise RuntimeError(
            f"La colección está actualmente en versión {current_version}, "
            f"pero este proyecto está fijado en versión {EXPECTED_VERSION}. "
            "No se descargará nada automáticamente."
        )

    return collection


def get_collection_articles():
    """Obtiene todos los artículos pertenecientes a la colección."""
    articles = []
    page = 1
    page_size = 100

    while True:
        batch = api_get(f"/collections/{COLLECTION_ID}/articles?page={page}&page_size={page_size}")

        articles.extend(batch)

        if len(batch) < page_size:
            break

        page += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    return articles


def get_article_details(article_id: int):
    time.sleep(REQUEST_DELAY_SECONDS)
    return api_get(f"/articles/{article_id}")


def get_article_files(article_id: int):
    time.sleep(REQUEST_DELAY_SECONDS)
    return api_get(f"/articles/{article_id}/files")


# Inventario


def build_inventory():
    collection = get_collection()

    print()
    print("=" * 70)
    print("WYSCOUT / FIGSHARE")
    print("=" * 70)
    print(f"Colección : {collection.get('title')}")
    print(f"ID        : {COLLECTION_ID}")
    print(f"Versión   : {collection.get('version')}")
    print(f"DOI       : {collection.get('doi') or EXPECTED_DOI}")
    print()

    articles = get_collection_articles()

    inventory = []
    total_size = 0
    total_files = 0

    for article_summary in articles:
        article_id = article_summary["id"]
        article = get_article_details(article_id)
        files = get_article_files(article_id)

        article_record = {
            "article_id": article_id,
            "title": article.get("title"),
            "version": article.get("version"),
            "doi": article.get("doi"),
            "published_date": article.get("published_date"),
            "modified_date": article.get("modified_date"),
            "files": [],
        }

        article_size = 0

        print(f"\n[{article_id}] {article.get('title')}")

        for file_info in files:
            file_size = int(file_info.get("size", 0))

            total_size += file_size
            article_size += file_size
            total_files += 1

            record = {
                "file_id": file_info.get("id"),
                "name": file_info.get("name"),
                "size": file_size,
                "download_url": file_info.get("download_url"),
            }

            article_record["files"].append(record)

            print(f"    {file_info.get('name'):<45} {human_size(file_size):>12}")

        print(f"    Total artículo: {human_size(article_size)}")

        inventory.append(article_record)

    print()
    print("=" * 70)
    print(f"Artículos : {len(inventory)}")
    print(f"Archivos  : {total_files}")
    print(f"Tamaño    : {human_size(total_size)}")
    print("=" * 70)
    print()

    return collection, inventory, total_size


# Descarga


def download_file(url: str, destination: Path):
    """
    Descarga utilizando un archivo .part temporal.
    Solo renombra al finalizar correctamente.
    """

    destination.parent.mkdir(parents=True, exist_ok=True)

    temporary = destination.with_suffix(destination.suffix + ".part")

    request = Request(
        url,
        headers={"User-Agent": "football-functional-profiling/1.0"},
    )

    with urlopen(request, timeout=120) as response:
        total = int(response.headers.get("Content-Length", 0))
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
                        f"\r        {percentage:6.2f}% ({human_size(downloaded)} / {human_size(total)})",
                        end="",
                    )

    temporary.replace(destination)

    print()


def download_inventory(collection, inventory):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    downloaded_files = []

    for article in inventory:
        article_id = article["article_id"]
        article_slug = slugify(article["title"])

        article_dir = RAW_DIR / (f"{article_slug}__article_{article_id}")

        article_dir.mkdir(parents=True, exist_ok=True)

        print()
        print("=" * 70)
        print(article["title"])
        print("=" * 70)

        for file_info in article["files"]:
            filename = file_info["name"]
            expected_size = file_info["size"]
            url = file_info["download_url"]

            destination = article_dir / filename

            print(f"\nDescargando {filename}")

            if destination.exists():
                existing_size = destination.stat().st_size

                if existing_size == expected_size:
                    print("    Ya existe con el tamaño esperado. No se vuelve a descargar.")

                else:
                    print("    Existe pero el tamaño no coincide. Se descargará nuevamente.")

                    destination.unlink()

                    download_file(url, destination)

            else:
                download_file(url, destination)

            local_sha256 = sha256_file(destination)

            downloaded_files.append(
                {
                    "article_id": article_id,
                    "article_title": article["title"],
                    "article_version": article["version"],
                    "article_doi": article["doi"],
                    "file_id": file_info["file_id"],
                    "file_name": filename,
                    "figshare_size_bytes": expected_size,
                    "local_path": str(destination),
                    "local_size_bytes": destination.stat().st_size,
                    "sha256": local_sha256,
                    "download_url": url,
                }
            )

    manifest = {
        "provider": "Wyscout",
        "repository": "Figshare",
        "collection_title": collection.get("title"),
        "collection_id": COLLECTION_ID,
        "collection_version": EXPECTED_VERSION,
        "collection_doi": EXPECTED_DOI,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "articles": inventory,
        "downloaded_files": downloaded_files,
    }

    with MANIFEST_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            manifest,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 70)
    print("DESCARGA FINALIZADA")
    print("=" * 70)
    print(f"Datos     : {RAW_DIR}")
    print(f"Manifiesto: {MANIFEST_PATH}")
    print(f"Archivos  : {len(downloaded_files)}")
    print("=" * 70)


# Punto de entrada


def main():

    parser = argparse.ArgumentParser(
        description=("Ingestión reproducible del Wyscout Public Dataset publicado en Figshare.")
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="Lista artículos y archivos sin descargar.",
    )

    parser.add_argument(
        "--download",
        action="store_true",
        help="Descarga todos los archivos y genera manifiesto.",
    )

    args = parser.parse_args()

    if not args.list and not args.download:
        parser.print_help()
        sys.exit(0)

    collection, inventory, _ = build_inventory()

    if args.download:
        download_inventory(collection, inventory)


if __name__ == "__main__":
    main()
