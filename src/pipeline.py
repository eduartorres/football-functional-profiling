"""
Orquestador del pipeline. Ejecuta las etapas en orden desde los datos crudos.

Uso:
    python -m src.pipeline                          # todas las etapas
    python -m src.pipeline --from features          # desde una etapa en adelante
    python -m src.pipeline --only audit             # una sola etapa
    python -m src.pipeline --until findings         # hasta una etapa, inclusive
    python -m src.pipeline --list                   # etapas y archivos que requiere cada una
    python -m src.pipeline --skip-unavailable       # omite las etapas cuyos insumos no están presentes

Cada etapa declara los insumos que no se versionan en el repositorio (datos crudos, eventos completos,
atributos personales de los jugadores y derivados de StatsBomb). En una copia del repositorio sin esos
archivos, `--skip-unavailable` vuelve a calcular todo lo que se puede obtener de las tablas versionadas
y deja intactos los resultados de las demás etapas.

La adquisición de fuentes (src/ingestion) no forma parte del pipeline: se ejecuta una sola vez y su
resultado queda fijado en manifests/. La grilla de modelos se ejecuta aparte, por etapas reanudables:
    python -m src.models.select_model --stage screen   (repetir hasta 'quedan 0')
    python -m src.models.select_model --stage confirm  (repetir hasta 'quedan 0')
"""

from __future__ import annotations

import argparse
import time

from src.config import ROOT, load_config

RAW_WYSCOUT = "data/raw/wyscout"
EVENTS = "data/interim/wyscout/events_parquet"
PLAYERS = "data/interim/wyscout/players.parquet"
STATSBOMB_WC = "data/interim/replication/wc2018_statsbomb.parquet"


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


def _tm_db() -> str:
    return load_config()["paths"]["transfermarkt_db"]


# nombre, descripción, función, insumos no versionados que requiere
STAGES = [
    (
        "extract",
        "Extracción de ZIP y eventos Wyscout a Parquet",
        _call("src.harmonization.wyscout_to_parquet"),
        [RAW_WYSCOUT],
    ),
    ("audit", "Auditoría de las seis fuentes", _audit, ["data/raw"]),
    (
        "player_match",
        "Tabla jugador-partido, minutos y posesión",
        _call("src.features.player_match"),
        [EVENTS, RAW_WYSCOUT],
    ),
    (
        "positions",
        "Enlace con Transfermarkt y posición fina",
        _call("src.features.position_reference"),
        [_tm_db(), PLAYERS],
    ),
    (
        "features",
        "Representaciones de volumen, composición y localización",
        _call("src.features.player_features"),
        [PLAYERS],
    ),
    ("findings", "Hallazgos preliminares de la sección 5.7", _call("src.diagnostics.wyscout_findings"), []),
    ("model_select", "Selección del modelo sobre la grilla confirmada", _select, []),
    ("profiles", "Caracterización de perfiles en desarrollo", _call("src.models.profiles"), []),
    ("evaluate", "Reserva temporal, H1 a H3 y generalización", _call("src.evaluation.evaluate"), []),
    ("replacement", "Casos de reemplazo y H4", _call("src.evaluation.replacement_cases"), [_tm_db()]),
    ("sensitivity", "Análisis de sensibilidad", _call("src.evaluation.sensitivity"), []),
    (
        "replication_prep",
        "Homologación StatsBomb, Mundial 2018",
        _call("src.harmonization.statsbomb_wc2018"),
        ["data/raw/statsbomb", EVENTS, PLAYERS],
    ),
    ("replication", "Replicación con StatsBomb", _call("src.evaluation.replication"), [STATSBOMB_WC]),
    ("profiles_final", "Perfiles finales en la temporada completa (D24)", _profiles_full, []),
    ("explorer", "Datos y página del explorador (prototipo)", _explorer, []),
    ("dictionary", "Diccionario de datos (anexo A)", _call("src.reports.data_dictionary"), []),
    ("casebook", "Datos y página del casebook de resultados", _casebook, []),
]


def missing(requires: list[str]) -> list[str]:
    return [r for r in requires if not (ROOT / r).exists()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start")
    ap.add_argument("--only")
    ap.add_argument("--until")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--skip-unavailable", action="store_true")
    a = ap.parse_args()
    names = [s[0] for s in STAGES]
    if a.list:
        for n, desc, _, req in STAGES:
            state = "disponible" if not missing(req) else "requiere " + ", ".join(missing(req))
            print(f"{n:17s} {desc:58s} {state}")
        return
    sel = STAGES
    if a.only:
        sel = [s for s in STAGES if s[0] == a.only]
    elif a.start or a.until:
        i = names.index(a.start) if a.start else 0
        j = names.index(a.until) + 1 if a.until else len(STAGES)
        sel = STAGES[i:j]
    for n, desc, fn, req in sel:
        absent = missing(req)
        if absent:
            if a.skip_unavailable:
                print(f"\n=== {n}: omitida, requiere {', '.join(absent)}")
                continue
            raise SystemExit(
                f"La etapa '{n}' requiere {', '.join(absent)}, que no se versiona en el repositorio. "
                "Ver data/README.md para obtenerlo, o usar --skip-unavailable."
            )
        t = time.time()
        print(f"\n=== {n}: {desc}")
        fn()
        print(f"--- {n} terminado en {time.time() - t:.1f} s")


if __name__ == "__main__":
    main()
