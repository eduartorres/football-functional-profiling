"""
Construye el casebook autocontenido a partir de reports/casebook/casebook_data.json.

Reduce el JSON a los campos que dibuja la plantilla, inserta la captura del explorador como imagen
embebida y escribe una sola página HTML que abre sin servidor.

Salida: reports/casebook/casebook.html
"""

from __future__ import annotations

import base64
import json

from src.config import ROOT

D = ROOT / "reports" / "casebook"
SCREENSHOT = ROOT / "reports" / "figures" / "explorer_consulta.png"
HEAD = (
    '<!doctype html><html lang="es"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>'
)


def compact(data: dict) -> dict:
    """Selecciona y renombra los campos que usa la plantilla para mantener la página liviana."""
    r = data["results"]
    md = [
        {
            "n": m["short_name"],
            "c": m["competition_file"],
            "s": m["fine_position"] if isinstance(m["fine_position"], str) else None,
            "x": m["profundidad_media_x"],
            "p": m["pases_progresivos_p90"],
            "m": round(m["minutes"]),
        }
        for m in data["midfielders"]
    ]
    grid = [
        {
            "r": g["representation"],
            "a": g["algorithm"],
            "k": g["k"],
            "sil": g["silhouette"],
            "ari": g["ari_mean"],
            "noise": g["noise_share"],
            "ok": g["confirmed"],
        }
        for g in r["grid"]
    ]
    cases = [
        {
            "n": c["short_name"],
            "g": c["fine_group"],
            "to": c["to_club"],
            "f": c["pertinent_share_functional"],
            "b": c["pertinent_share_baseline"],
            "new": c["new_pertinent"],
        }
        for c in r["replacement_cases"]
    ]
    return {
        "variance": [
            {k: v[k] for k in ["feature", "eta2_wyscout_role", "eta2_fine_group", "eta2_team"]}
            for v in data["variance"]
        ],
        "elig": data["eligibility"],
        "md": md,
        "pair": data["example_pair"],
        "coverage": data["coverage"],
        "inventory": data["inventory"],
        "linkage": data["linkage"],
        "grid": grid,
        "selected": r["selected"],
        "positions": r["profiles_positions"],
        "transitions": r["temporal_transitions"],
        "cases": cases,
        "replication": r["replication"],
    }


def main() -> None:
    data = json.loads((D / "casebook_data.json").read_text(encoding="utf-8"))
    page = (D / "casebook_template.html").read_text(encoding="utf-8")
    img = "data:image/png;base64," + base64.b64encode(SCREENSHOT.read_bytes()).decode()
    page = page.replace("/*__DATA__*/", json.dumps(compact(data), ensure_ascii=False))
    page = page.replace("__EXPLORER_PNG__", img)
    (D / "casebook.html").write_text(HEAD + page + "</body></html>", encoding="utf-8")
    print("reports/casebook/casebook.html")


if __name__ == "__main__":
    main()
