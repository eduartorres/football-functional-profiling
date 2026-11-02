"""
Orquestador del pipeline. Ejecuta las etapas en orden desde los datos crudos.

Uso:
    python -m src.pipeline                 # todas las etapas
    python -m src.pipeline --from features # desde una etapa en adelante
    python -m src.pipeline --only audit    # una sola etapa
    python -m src.pipeline --until findings # hasta una etapa, inclusive
    python -m src.pipeline --list

La adquisición de fuentes (src/ingestion) no forma parte del pipeline: se ejecuta una sola vez y su
resultado queda fijado en manifests/. La grilla de modelos se ejecuta aparte, por etapas reanudables:
    python -m src.models.select_model --stage screen   (repetir hasta 'quedan 0')
    python -m src.models.select_model --stage confirm  (repetir hasta 'quedan 0')
"""

from __future__ import annotations

import argparse
import time


def _audit():
    from src.diagnostics import audit_sources as a

    for name, fn in a.AUDITS.items():
        a._save(name, fn())
    a.combine()


def _select():
    # la grilla (screen/confirm) se ejecuta aparte por su costo; ver README
    from src.models.select_model import select

    select()


def _explorer():
    from src.reports import build_explorer, export_explorer_data

    export_explorer_data.main()
    build_explorer.main()


def _casebook():
    from src.reports import build_casebook, export_casebook_data

    export_casebook_data.main()
    build_casebook.main()


def _profiles_full():
    from src.models.profiles import main

    main("full")


def _call(module: str):
    def run():
        import importlib

        importlib.import_module(module).main()

    return run


STAGES = [
    (
        "extract",
        "Extracción de ZIP y eventos Wyscout a Parquet",
        _call("src.harmonization.wyscout_to_parquet"),
    ),
    ("audit", "Auditoría de las seis fuentes", _audit),
    ("player_match", "Tabla jugador-partido, minutos y posesión", _call("src.features.player_match")),
    ("positions", "Enlace con Transfermarkt y posición fina", _call("src.features.position_reference")),
    (
        "features",
        "Representaciones de volumen, composición y localización",
        _call("src.features.player_features"),
    ),
    ("findings", "Hallazgos preliminares de la sección 5.7", _call("src.diagnostics.wyscout_findings")),
    ("model_select", "Selección del modelo sobre la grilla confirmada", _select),
    ("profiles", "Caracterización de perfiles en desarrollo", _call("src.models.profiles")),
    ("evaluate", "Reserva temporal, H1 a H3 y generalización", _call("src.evaluation.evaluate")),
    ("replacement", "Casos de reemplazo y H4", _call("src.evaluation.replacement_cases")),
    ("sensitivity", "Análisis de sensibilidad", _call("src.evaluation.sensitivity")),
    ("replication_prep", "Homologación StatsBomb, Mundial 2018", _call("src.harmonization.statsbomb_wc2018")),
    ("replication", "Replicación con StatsBomb", _call("src.evaluation.replication")),
    ("profiles_final", "Perfiles finales en la temporada completa (D24)", _profiles_full),
    ("explorer", "Datos y página del explorador (prototipo)", _explorer),
    ("dictionary", "Diccionario de datos (anexo A)", _call("src.reports.data_dictionary")),
    ("casebook", "Datos y página del casebook de resultados", _casebook),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start")
    ap.add_argument("--only")
    ap.add_argument("--until")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    names = [s[0] for s in STAGES]
    if a.list:
        for n, desc, _ in STAGES:
            print(f"{n:14s} {desc}")
        return
    sel = STAGES
    if a.only:
        sel = [s for s in STAGES if s[0] == a.only]
    elif a.start or a.until:
        i = names.index(a.start) if a.start else 0
        j = names.index(a.until) + 1 if a.until else len(STAGES)
        sel = STAGES[i:j]
    for n, desc, fn in sel:
        t = time.time()
        print(f"\n=== {n}: {desc}")
        fn()
        print(f"--- {n} terminado en {time.time() - t:.1f} s")


if __name__ == "__main__":
    main()
