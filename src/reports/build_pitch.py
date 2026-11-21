"""
Construye la presentación del Analytics Pitch Awards (portada y cinco láminas de 1920 x 1080).

Reutiliza los datos del casebook (reports/casebook/casebook_data.json) para que las cifras y los gráficos
del pitch salgan de las mismas tablas que el documento. El caso del clímax viene de
reports/pitch/caso_pitch.json. La página resultante se imprime a PDF desde un navegador; cada lámina
ocupa una página.

Salida: reports/pitch/pitch.html
"""

from __future__ import annotations

import base64
import json

from src.config import ROOT
from src.reports.build_casebook import compact

D = ROOT / "reports" / "pitch"
LEAGUES = {"England", "France", "Germany", "Italy", "Spain"}
SCREENSHOT = ROOT / "reports" / "figures" / "explorer_consulta.png"
HEAD = (
    '<!doctype html><html lang="es"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=1920"></head><body>'
)


def main() -> None:
    data = json.loads((ROOT / "reports" / "casebook" / "casebook_data.json").read_text(encoding="utf-8"))
    payload = compact(data)
    payload["replacement"] = data["results"]["replacement"]
    # caso narrado en el clímax del pitch (src/reports/pitch_case.py)
    payload["story"] = json.loads((D / "caso_pitch.json").read_text(encoding="utf-8"))
    # acciones registradas en las cinco ligas (auditoría de Wyscout), para la lámina de exposición
    audit = json.loads((ROOT / "data" / "processed" / "diagnostics" / "audit_wyscout.json").read_text())
    leagues = [c for c in audit["by_competition"] if c["competition_file"] in LEAGUES]
    payload["events_leagues"] = {
        "events": sum(c["n_events"] for c in leagues),
        "matches": sum(c["n_matches"] for c in leagues),
    }
    page = (D / "pitch_template.html").read_text(encoding="utf-8")
    img = "data:image/png;base64," + base64.b64encode(SCREENSHOT.read_bytes()).decode()
    page = page.replace("/*__DATA__*/", json.dumps(payload, ensure_ascii=False))
    page = page.replace("__EXPLORER_PNG__", img)
    (D / "pitch.html").write_text(HEAD + page + "</body></html>", encoding="utf-8")
    print("reports/pitch/pitch.html")


if __name__ == "__main__":
    main()
