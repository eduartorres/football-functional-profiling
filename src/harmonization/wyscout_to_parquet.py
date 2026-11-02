"""
Extrae los ZIP de Wyscout (Pappalardo et al., 2019) y convierte los eventos a Parquet.

Entrada : data/raw/wyscout/events__*/events.zip, data/raw/wyscout/matches__*/matches.zip
Salida  : data/interim/wyscout/events/*.json, data/interim/wyscout/matches/*.json
          data/interim/wyscout/events_parquet/<competicion>.parquet (una fila por evento)

data/raw no se modifica. Las coordenadas Wyscout van de 0 a 100 en ambos ejes, en la dirección
de ataque del equipo que ejecuta la acción.
"""

from __future__ import annotations

import zipfile

import duckdb

from src.common.config import ROOT, path

RAW = ROOT / "data/raw/wyscout"


def extract_zips() -> None:
    out = path("interim") / "wyscout"
    for name in ("events", "matches"):
        target = out / name
        zf = next(RAW.glob(f"{name}__*/{name}.zip"))
        with zipfile.ZipFile(zf) as z:
            members = [m for m in z.namelist() if m.endswith(".json")]
            if target.exists() and all((target / m).exists() for m in members):
                continue
            target.mkdir(parents=True, exist_ok=True)
            z.extractall(target, members)
            print(f"extraído {zf.name} -> {target.relative_to(ROOT)}")


def to_parquet(memory_limit: str = "1500MB") -> None:
    src = path("interim") / "wyscout" / "events"
    out_dir = path("interim") / "wyscout" / "events_parquet"
    out_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{memory_limit}'")
    con.execute("SET preserve_insertion_order=false")
    total = 0
    for f in sorted(src.glob("events_*.json")):
        comp = f.stem.replace("events_", "")
        part = out_dir / f"{comp}.parquet"
        con.execute(f"""
            COPY (
                SELECT '{comp}' AS competition_file, id AS event_uid, matchId AS match_id, teamId AS team_id,
                       playerId AS player_id, matchPeriod AS match_period, eventSec AS event_sec,
                       eventId AS event_id, eventName AS event_name,
                       TRY_CAST(subEventId AS VARCHAR) AS sub_event_id, subEventName AS sub_event_name,
                       positions[1].x AS x_start, positions[1].y AS y_start,
                       positions[2].x AS x_end, positions[2].y AS y_end,
                       list_transform(tags, t -> t.id) AS tag_ids
                FROM read_json_auto('{f}', maximum_object_size=200000000)
            ) TO '{part}' (FORMAT PARQUET, COMPRESSION ZSTD)""")
        n = con.execute(f"SELECT count(*) FROM read_parquet('{part}')").fetchone()[0]
        total += n
        print(f"{comp}: {n:,} eventos")
    print(f"total: {total:,} eventos")


def main() -> None:
    extract_zips()
    to_parquet()


if __name__ == "__main__":
    main()
