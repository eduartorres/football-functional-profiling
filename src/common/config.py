"""Acceso a la configuración central (config/project.yaml) y a las rutas del proyecto."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def load_config() -> dict:
    with open(ROOT / "config" / "project.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def path(key: str) -> Path:
    """Ruta absoluta de una entrada de la sección paths; crea la carpeta si es un directorio de salida."""
    p = ROOT / load_config()["paths"][key]
    if not p.suffix:
        p.mkdir(parents=True, exist_ok=True)
    return p
