"""
Construye la presentación del Analytics Pitch Awards (cinco láminas de 1920 x 1080).

Reutiliza los datos del casebook (reports/casebook/casebook_data.json) para que las cifras y los gráficos
del pitch salgan de las mismas tablas que el documento. La página resultante se imprime a PDF desde un
navegador; cada lámina ocupa una página.

Salida: reports/pitch/pitch.html
"""

from __future__ import annotations

import base64
import json

from src.config import ROOT
from src.reports.build_casebook import compact

D = ROOT / "reports" / "pitch"
SCREENSHOT = ROOT / "reports" / "figures" / "explorer_consulta.png"
HEAD = (
    '<!doctype html><html lang="es"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=1920"></head><body>'
)


def main() -> None:
    data = json.loads((ROOT / "reports" / "casebook" / "casebook_data.json").read_text(encoding="utf-8"))
    payload = compact(data)
    payload["replacement"] = data["results"]["replacement"]
    page = (D / "pitch_template.html").read_text(encoding="utf-8")
    img = "data:image/png;base64," + base64.b64encode(SCREENSHOT.read_bytes()).decode()
    page = page.replace("/*__DATA__*/", json.dumps(payload, ensure_ascii=False))
    page = page.replace("__EXPLORER_PNG__", img)
    (D / "pitch.html").write_text(HEAD + page + "</body></html>", encoding="utf-8")
    print("reports/pitch/pitch.html")


if __name__ == "__main__":
    main()
