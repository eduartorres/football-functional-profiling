"""
Adquisición del snapshot de transfermarkt-datasets (proyecto dcaribou) en formato DuckDB.

Descarga la base del 6 de julio de 2026 en data/raw/transfermarkt y registra tamaño y SHA-256 en
manifests/transfermarkt_manifest.json. En el proyecto, Transfermarkt aporta la posición fina de referencia y el
contexto del jugador; sus variables no intervienen en los perfiles.

Uso, desde la raíz del repositorio:
    python -m src.ingestion.ingest_transfermarkt --download
    python -m src.ingestion.ingest_transfermarkt --verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Configuración

DATASET_URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfermarkt-datasets.duckdb"

SNAPSHOT_DATE = "2026-07-06"

RAW_DIR = Path("data/raw/transfermarkt")

DATABASE_PATH = RAW_DIR / "transfermarkt-datasets.duckdb"

MANIFEST_PATH = Path("manifests/transfermarkt_manifest.json")

SOURCE_PATH = Path("manifests/transfermarkt_source.txt")

CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB


# Utilidades


def human_size(num_bytes: int) -> str:

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

    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(CHUNK_SIZE)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


# Consultar archivo remoto


def get_remote_info():

    request = Request(
        DATASET_URL,
        method="HEAD",
        headers={"User-Agent": "football-functional-profiling/1.0"},
    )

    try:
        with urlopen(
            request,
            timeout=60,
        ) as response:
            size = int(
                response.headers.get(
                    "Content-Length",
                    0,
                )
            )

            return {
                "size_bytes": size,
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
            }

    except HTTPError as exc:
        print(f"ERROR HTTP {exc.code}")

        raise

    except URLError as exc:
        print(f"ERROR de conexión: {exc.reason}")

        raise


# Descarga


def download_file():

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    remote = get_remote_info()

    expected_size = remote["size_bytes"]

    print()

    print("=" * 74)

    print("TRANSFERMARKT DATASET")

    print("=" * 74)

    print(f"Snapshot    : {SNAPSHOT_DATE}")

    print(f"Destino     : {DATABASE_PATH}")

    if expected_size:
        print(f"Tamaño      : {human_size(expected_size)}")

    print("=" * 74)

    if DATABASE_PATH.exists():
        local_size = DATABASE_PATH.stat().st_size

        if expected_size and local_size == expected_size:
            print()

            print("El archivo ya existe con el tamaño esperado.")

            return remote

        print()

        print("Existe una copia local, pero su tamaño no coincide.")

        print("Se descargará nuevamente.")

        DATABASE_PATH.unlink()

    temporary = DATABASE_PATH.with_suffix(".duckdb.part")

    request = Request(
        DATASET_URL,
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
                        f"\r{percentage:6.2f}% ({human_size(downloaded)} / {human_size(total)})",
                        end="",
                    )

    print()

    temporary.replace(DATABASE_PATH)

    return remote


# Manifiesto


def create_manifest(
    remote_info,
):

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"No existe {DATABASE_PATH}")

    print()

    print("Calculando SHA-256...")

    checksum = sha256_file(DATABASE_PATH)

    local_size = DATABASE_PATH.stat().st_size

    manifest = {
        "provider": "Transfermarkt",
        "dataset_project": "dcaribou/transfermarkt-datasets",
        "dataset_format": "DuckDB",
        "snapshot_date": SNAPSHOT_DATE,
        "source_url": DATASET_URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "local_path": str(DATABASE_PATH),
        "size_bytes": local_size,
        "size_human": human_size(local_size),
        "sha256": checksum,
        "remote_etag": remote_info.get("etag"),
        "remote_last_modified": remote_info.get("last_modified"),
        "purpose": (
            "Contextual enrichment: "
            "player attributes, clubs, "
            "career history, transfers "
            "and market valuations."
        ),
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

    SOURCE_PATH.write_text(
        "\n".join(
            [
                "provider=Transfermarkt",
                ("dataset_project=dcaribou/transfermarkt-datasets"),
                (f"snapshot_date={SNAPSHOT_DATE}"),
                (f"source_url={DATASET_URL}"),
                (f"local_path={DATABASE_PATH}"),
                (f"size_bytes={local_size}"),
                (f"sha256={checksum}"),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print()

    print("=" * 74)

    print("TRANSFERMARKT FINALIZADO")

    print("=" * 74)

    print(f"Datos      : {DATABASE_PATH}")

    print(f"Manifiesto : {MANIFEST_PATH}")

    print(f"Fuente     : {SOURCE_PATH}")

    print(f"Tamaño     : {human_size(local_size)}")

    print(f"SHA-256    : {checksum}")

    print("=" * 74)


# Verificación


def verify():

    if not MANIFEST_PATH.exists():
        raise FileNotFoundError("Primero genera el manifiesto.")

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"No existe {DATABASE_PATH}")

    with MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    expected_hash = manifest["sha256"]

    expected_size = manifest["size_bytes"]

    print("Verificando Transfermarkt...")

    if DATABASE_PATH.stat().st_size != expected_size:
        print("ERROR: el tamaño cambió.")

        return False

    current_hash = sha256_file(DATABASE_PATH)

    if current_hash != expected_hash:
        print("ERROR: SHA-256 no coincide.")

        return False

    print("Archivo íntegro y consistente con el manifiesto.")

    return True


# Punto de entrada


def main():

    parser = argparse.ArgumentParser(description=("Descarga reproducible del Transfermarkt DuckDB dataset."))

    parser.add_argument(
        "--download",
        action="store_true",
        help=("Descarga el snapshot y genera el manifiesto."),
    )

    parser.add_argument(
        "--verify",
        action="store_true",
        help=("Verifica el archivo contra el manifiesto."),
    )

    args = parser.parse_args()

    if not args.download and not args.verify:
        parser.print_help()

        sys.exit(0)

    if args.download:
        remote_info = download_file()

        create_manifest(remote_info)

    if args.verify:
        valid = verify()

        sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
