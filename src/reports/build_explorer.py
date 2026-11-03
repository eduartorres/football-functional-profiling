"""
Construye el explorador autocontenido: inserta reports/explorer/explorer_data.json en la plantilla.

Salida: reports/explorer/explorer.html (abre directamente en el navegador, sin servidor)
"""

from __future__ import annotations

from src.config import ROOT

HEAD = (
    '<!doctype html><html lang="es"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>'
)


def main() -> None:
    d = ROOT / "reports" / "explorer"
    page = (d / "explorer_template.html").read_text(encoding="utf-8")
    data = (d / "explorer_data.json").read_text(encoding="utf-8")
    (d / "explorer.html").write_text(
        HEAD + page.replace("/*__DATA__*/", data) + "</body></html>", encoding="utf-8"
    )
    print("reports/explorer/explorer.html")


if __name__ == "__main__":
    main()
