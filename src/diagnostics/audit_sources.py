"""
Auditoría reproducible de las seis fuentes del proyecto.

Uso:
    python src/diagnostics/audit_sources.py --source wyscout      # una fuente
    python src/diagnostics/audit_sources.py --source all          # todas
    python src/diagnostics/audit_sources.py --combine             # solo consolida

Salidas (data/processed/diagnostics/):
    audit_<fuente>.json      detalle por fuente (conteos, vocabulario de eventos, campos)
    inventory.csv            matriz fuente x {competiciones, temporadas, partidos, jugadores, eventos, tracking}
    coverage_matrix.csv      dimensión funcional x fuente, con la evidencia encontrada en el dato

Reglas:
    - data/raw no se modifica. Wyscout se lee desde data/interim (ver src/harmonization/wyscout_to_parquet.py).
    - La matriz de cobertura se deriva del vocabulario observado en los archivos, no de la documentación.
    - Las fuentes muy pesadas (eventos StatsBomb, tracking) se cuentan por streaming o por muestra;
      cuando se usa muestra queda indicado en el JSON.
"""

from __future__ import annotations

import argparse
import bz2
import collections
import json
import random
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw"
INTERIM = ROOT / "data/interim"
OUT = ROOT / "data/processed/diagnostics"
SEED = 2026


def _save(name: str, obj: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    obj["_audited_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (OUT / f"audit_{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str))
    print(f"[ok] audit_{name}.json")


def _top(counter: collections.Counter, n: int = 60) -> dict:
    return dict(counter.most_common(n))


# ------------------------------------------------------------------
# WYSCOUT (núcleo)
# ------------------------------------------------------------------
def audit_wyscout() -> dict:
    import duckdb

    base = RAW / "wyscout"
    ev_glob = str(INTERIM / "wyscout/events_parquet/*.parquet")
    con = duckdb.connect()

    players = json.loads(next(base.glob("players__*/players.json")).read_text())
    teams = json.loads(next(base.glob("teams__*/teams.json")).read_text())
    comps = json.loads(next(base.glob("competitions__*/competitions.json")).read_text())

    matches = []
    for f in sorted((INTERIM / "wyscout/matches").glob("matches_*.json")):
        for m in json.loads(f.read_text()):
            m["_file"] = f.stem.replace("matches_", "")
            matches.append(m)
    mdf = pd.DataFrame(
        [
            {
                "match_id": m["wyId"],
                "competition_file": m["_file"],
                "competition_id": m["competitionId"],
                "season_id": m["seasonId"],
                "date_utc": m["dateutc"],
                "duration": m.get("duration"),
            }
            for m in matches
        ]
    )

    def q(sql: str) -> pd.DataFrame:
        return con.execute(sql).fetchdf()

    totals = (
        q(f"""
        SELECT count(*) n_events, count(DISTINCT match_id) n_matches,
               count(DISTINCT player_id) FILTER (WHERE player_id <> 0) n_players_with_events,
               count(DISTINCT team_id) n_teams,
               avg((player_id = 0)::INT) share_events_without_player,
               avg((x_start IS NULL)::INT) share_missing_start_xy,
               avg((x_end IS NULL)::INT) share_missing_end_xy,
               min(x_start) min_x, max(x_start) max_x, min(y_start) min_y, max(y_start) max_y
        FROM read_parquet('{ev_glob}')""")
        .iloc[0]
        .to_dict()
    )
    by_comp = q(f"""
        SELECT competition_file, count(*) n_events, count(DISTINCT match_id) n_matches,
               count(DISTINCT player_id) FILTER (WHERE player_id <> 0) n_players
        FROM read_parquet('{ev_glob}') GROUP BY 1 ORDER BY 1""")
    ev_types = q(
        f"""SELECT event_name, count(*) n FROM read_parquet('{ev_glob}') GROUP BY 1 ORDER BY 2 DESC"""
    )
    sub_types = q(f"""SELECT event_name, sub_event_name, count(*) n FROM read_parquet('{ev_glob}')
                      GROUP BY 1,2 ORDER BY 3 DESC""")

    # tags: el diccionario oficial traduce ids a etiquetas (interception, accurate, key pass, ...)
    tag_map = pd.read_csv(next(base.glob("mapping_of_tag_identifiers*/tags2name.csv")))
    tag_counts = q(
        f"""SELECT t AS Tag, count(*) n FROM (SELECT unnest(tag_ids) t FROM read_parquet('{ev_glob}')) GROUP BY 1"""
    )
    tag_counts = tag_counts.merge(tag_map, on="Tag", how="left").sort_values("n", ascending=False)
    tag_label = "Label" if "Label" in tag_counts else tag_counts.columns[-1]

    roles = collections.Counter(p["role"]["code2"] for p in players)
    period = {"min_date": mdf.date_utc.min(), "max_date": mdf.date_utc.max()}

    return {
        "source": "Wyscout (Pappalardo et al., 2019; figshare c.4415000.v5)",
        "competitions": [c["name"] for c in comps],
        "n_competitions": len(comps),
        "n_seasons": int(mdf.season_id.nunique()),
        "season_ids": sorted(mdf.season_id.unique().tolist()),
        "period": period,
        "n_matches_metadata": int(len(mdf)),
        "n_teams_metadata": len(teams),
        "n_players_metadata": len(players),
        "player_roles_metadata": dict(roles),
        "totals": totals,
        "by_competition": by_comp.to_dict("records"),
        "event_types": ev_types.to_dict("records"),
        "sub_event_types": sub_types.to_dict("records"),
        "tags": tag_counts.to_dict("records"),
        "vocab": sorted(
            set(ev_types.event_name)
            | set(sub_types.sub_event_name.dropna())
            | set(tag_counts[tag_label].dropna().astype(str))
        ),
        "coordinates": "0-100 en ambos ejes, relativas a la dirección de ataque del equipo que ejecuta",
        "tracking": False,
        "minutes_field": "no directo; reconstruible con teamsData (formation.lineup/bench/substitutions)",
        "position_field": "players.role: GK/DF/MF/FW (4 categorías)",
    }


# ------------------------------------------------------------------
# STATSBOMB (validación)
# ------------------------------------------------------------------
def audit_statsbomb(sample_events: int = 120) -> dict:
    base = RAW / "statsbomb/data"
    comps = json.loads((base / "competitions.json").read_text())
    rows = []
    for f in sorted((base / "matches").glob("*/*.json")):
        for m in json.loads(f.read_text()):
            rows.append(
                {
                    "match_id": m["match_id"],
                    "competition": m["competition"]["competition_name"],
                    "season": m["season"]["season_name"],
                    "date": m["match_date"],
                    "gender": next(
                        (
                            c["competition_gender"]
                            for c in comps
                            if c["competition_id"] == m["competition"]["competition_id"]
                        ),
                        None,
                    ),
                }
            )
    mdf = pd.DataFrame(rows)

    event_files = sorted((base / "events").glob("*.json"))
    ff_files = {p.stem for p in (base / "three-sixty").glob("*.json")}

    # conteo de eventos por streaming: el JSON viene indentado con una clave "index" por evento
    counts = {}
    chunk = [str(p) for p in event_files]
    for i in range(0, len(chunk), 400):
        out = subprocess.run(
            ["grep", "-c", '"index" :'] + chunk[i : i + 400], capture_output=True, text=True
        ).stdout
        for line in out.strip().splitlines():
            path, n = line.rsplit(":", 1)
            counts[int(Path(path).stem)] = int(n)
    mdf["n_events"] = mdf.match_id.map(counts)
    mdf["has_360"] = mdf.match_id.astype(str).isin(ff_files)

    # jugadores desde alineaciones (todas)
    players, positions = set(), collections.Counter()
    for f in (base / "lineups").glob("*.json"):
        for team in json.loads(f.read_text()):
            for p in team["lineup"]:
                players.add(p["player_id"])
                for pos in p.get("positions", []):
                    positions[pos["position"]] += 1

    # vocabulario de tipos y campos a partir de una muestra fija de partidos
    random.seed(SEED)
    sample = random.sample(event_files, min(sample_events, len(event_files)))
    types, keys = collections.Counter(), collections.Counter()
    has_xg = 0
    for f in sample:
        for e in json.loads(f.read_text()):
            types[e["type"]["name"]] += 1
            for k in e:
                keys[k] += 1
            if e["type"]["name"] == "Shot" and "statsbomb_xg" in e.get("shot", {}):
                has_xg += 1

    comp_season = (
        mdf.groupby(["competition", "season", "gender"])
        .agg(n_matches=("match_id", "size"), n_events=("n_events", "sum"), n_360=("has_360", "sum"))
        .reset_index()
        .sort_values(["n_matches"], ascending=False)
    )
    big5_1516 = comp_season[
        (comp_season.season == "2015/2016")
        & comp_season.competition.isin(["La Liga", "Premier League", "Serie A", "1. Bundesliga", "Ligue 1"])
    ]
    return {
        "source": "StatsBomb Open Data (git commit en manifests/statsbomb_commit.txt)",
        "n_competition_seasons": len(comps),
        "n_competitions": len({c["competition_name"] for c in comps}),
        "n_matches": int(len(mdf)),
        "n_matches_male": int((mdf.gender == "male").sum()),
        "n_event_files": len(event_files),
        "n_events_total": int(sum(counts.values())),
        "n_matches_with_360": int(mdf.has_360.sum()),
        "n_players_lineups": len(players),
        "lineup_positions": _top(positions, 30),
        "period": {"min_date": mdf.date.min(), "max_date": mdf.date.max()},
        "big5_2015_16": big5_1516.to_dict("records"),
        "by_competition_season": comp_season.to_dict("records"),
        "event_types_sample": _top(types, 50),
        "event_keys_sample": _top(keys, 60),
        "sample_n_matches": len(sample),
        "shots_with_xg_in_sample": has_xg,
        "vocab": sorted(types) + (["statsbomb_xg"] if has_xg else []),
        "coordinates": "120 x 80 yardas, dirección de ataque del equipo en posesión",
        "tracking": "no continuo; 360 = freeze frames por evento en un subconjunto",
        "minutes_field": "reconstruible con lineups.positions[from/to] y eventos de sustitución",
        "position_field": "posición detallada por partido y tramo (lineups.positions)",
    }


# ------------------------------------------------------------------
# SKILLCORNER (tracking + eventos dinámicos)
# ------------------------------------------------------------------
def audit_skillcorner() -> dict:
    base = RAW / "skillcorner/data/matches"
    rows, players, roles = [], {}, collections.Counter()
    ev_types, ev_sub = collections.Counter(), collections.Counter()
    dyn_cols = set()
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        mid = d.name
        m = json.loads((d / f"{mid}_match.json").read_text())
        trk = d / f"{mid}_tracking_extrapolated.jsonl"
        n_frames = int(
            subprocess.run(["wc", "-l", str(trk)], capture_output=True, text=True).stdout.split()[0]
        )
        dyn = pd.read_csv(d / f"{mid}_dynamic_events.csv", low_memory=False)
        dyn_cols |= set(dyn.columns)
        ev_types.update(dyn.event_type.value_counts().to_dict())
        ev_sub.update(dyn.event_subtype.dropna().value_counts().to_dict())
        for p in m["players"]:
            players[p["id"]] = p
            roles[p["player_role"]["name"]] += 1
        rows.append(
            {
                "match_id": mid,
                "date": m["date_time"],
                "competition": m["competition_edition"]["name"],
                "n_frames": n_frames,
                "n_dynamic_events": len(dyn),
                "tracking_mb": round(trk.stat().st_size / 1e6, 1),
            }
        )
    mdf = pd.DataFrame(rows)
    aggr = [p.name for p in (RAW / "skillcorner/data/aggregates").glob("*.csv")]
    return {
        "source": "SkillCorner Open Data (commit 4340d27)",
        "competitions": sorted(mdf.competition.unique()),
        "n_matches": len(mdf),
        "n_players": len(players),
        "player_roles": dict(roles),
        "period": {"min_date": mdf.date.min(), "max_date": mdf.date.max()},
        "n_frames_total": int(mdf.n_frames.sum()),
        "frames_per_match_mean": float(mdf.n_frames.mean()),
        "frame_rate_hz": 10,
        "n_dynamic_events_total": int(mdf.n_dynamic_events.sum()),
        "dynamic_event_types": dict(ev_types),
        "dynamic_event_subtypes": _top(ev_sub, 40),
        "dynamic_event_n_columns": len(dyn_cols),
        "dynamic_columns_selected": sorted(
            c for c in dyn_cols if re.search(r"xthreat|speed|pass_outcome|end_type|lead_to_shot", c)
        ),
        "aggregates_files": aggr,
        "matches": mdf.to_dict("records"),
        "vocab": sorted(set(ev_types) | set(ev_sub) | dyn_cols),
        "coordinates": "metros, centro del campo en (0,0), 105 x 68",
        "tracking": True,
        "minutes_field": "players.playing_time en match.json",
        "position_field": "players.player_role (posición detallada por partido)",
    }


# ------------------------------------------------------------------
# DFL (eventos + posiciones sincronizados)
# ------------------------------------------------------------------
def audit_dfl() -> dict:
    base = RAW / "dfl"
    rows, ev_types, positions, players = [], collections.Counter(), collections.Counter(), set()
    for f in sorted(base.glob("DFL_02_01_matchinformation_*.xml")):
        r = ET.parse(f).getroot()
        g = r.find(".//General").attrib
        mid = g["MatchId"]
        for p in r.iter("Player"):
            players.add(p.attrib["PersonId"])
            positions[p.attrib.get("PlayingPosition", "NA")] += 1
        n_ev = 0
        evf = next(base.glob(f"DFL_03_02_events_raw_*_{mid}.xml"))
        for _, el in ET.iterparse(evf):
            if el.tag == "Event":
                n_ev += 1
                for ch in el:
                    ev_types[ch.tag] += 1
                el.clear()
        posf = next(base.glob(f"DFL_04_03_positions_raw_observed_*_{mid}.xml"))
        n_frames = int(
            subprocess.run(["grep", "-c", "<Frame ", str(posf)], capture_output=True, text=True).stdout
        )
        n_sets = int(
            subprocess.run(["grep", "-c", "<FrameSet ", str(posf)], capture_output=True, text=True).stdout
        )
        rows.append(
            {
                "match_id": mid,
                "competition": g["CompetitionName"],
                "season": g["Season"],
                "match": g["MatchTitle"],
                "n_events": n_ev,
                "n_position_rows": n_frames,
                "n_framesets": n_sets,
                "positions_mb": round(posf.stat().st_size / 1e6, 1),
            }
        )
    mdf = pd.DataFrame(rows)
    return {
        "source": "DFL integrated dataset (Bassek et al., figshare 28196177.v1)",
        "competitions": sorted(mdf.competition.unique()),
        "seasons": sorted(mdf.season.unique()),
        "n_matches": len(mdf),
        "n_players": len(players),
        "playing_positions": dict(positions),
        "n_events_total": int(mdf.n_events.sum()),
        "n_position_rows_total": int(mdf.n_position_rows.sum()),
        "frame_rate_hz": 25,
        "event_types": dict(ev_types),
        "matches": mdf.to_dict("records"),
        "vocab": sorted(ev_types),
        "coordinates": "metros, centro en (0,0), 105 x 68; posiciones incluyen velocidad (S) y aceleración (A)",
        "tracking": True,
        "minutes_field": "derivable de alineación y Substitution",
        "position_field": "PlayingPosition por partido (códigos DFL)",
    }


# ------------------------------------------------------------------
# PFF FC (Mundial 2022)
# ------------------------------------------------------------------
def audit_pff(sample_tracking: int = 1) -> dict:
    base = RAW / "pff"
    ev_dir = base / "Event Data"
    folders = {"root": sorted(ev_dir.glob("*.json"))}
    for sub in sorted(p for p in ev_dir.iterdir() if p.is_dir()):
        folders[sub.name] = sorted(sub.glob("*.json"))

    meta = {}
    for f in (base / "Metadata").glob("*.json"):
        m = json.loads(f.read_text())
        m = m[0] if isinstance(m, list) else m
        meta[f.stem] = m

    # eventos: carpeta raíz completa (una versión por partido) y vocabulario de tipos
    ge, pe, keys = collections.Counter(), collections.Counter(), collections.Counter()
    n_events, game_ids, pressure = 0, set(), 0
    for f in folders["root"]:
        evs = json.loads(f.read_text())
        n_events += len(evs)
        for e in evs:
            game_ids.add(e.get("gameId"))
            ge[(e.get("gameEvents") or {}).get("gameEventType")] += 1
            pe[(e.get("possessionEvents") or {}).get("possessionEventType")] += 1
            if (e.get("initialTouch") or {}).get("initialPressureType") not in (None, "N"):
                pressure += 1
            for k in e:
                keys[k] += 1

    roster_players, roster_pos = set(), collections.Counter()
    for f in (base / "Rosters").glob("*.json"):
        for r in json.loads(f.read_text()):
            roster_players.add(r["player"]["id"])
            roster_pos[r.get("positionGroupType")] += 1

    # tracking: tamaño de todos los archivos y conteo de frames en una muestra
    trk = sorted((base / "Tracking Data").glob("*.jsonl.bz2"))
    random.seed(SEED)
    smp = random.sample(trk, sample_tracking)
    frames = {}
    for f in smp:
        with bz2.open(f, "rt") as fh:
            frames[f.name] = sum(1 for _ in fh)

    return {
        "source": "PFF FC FIFA World Cup 2022 (rclone desde Google Drive)",
        "competition": sorted({m.get("competition", {}).get("name") for m in meta.values()}),
        "n_matches_metadata": len(meta),
        "event_folders": {k: len(v) for k, v in folders.items()},
        "event_folders_ids": {k: sorted(p.stem for p in v)[:3] + ["..."] for k, v in folders.items()},
        "n_events_root": n_events,
        "n_games_root": len(game_ids),
        "events_with_pressure_on_touch": pressure,
        "game_event_types": dict(ge),
        "possession_event_types": dict(pe),
        "event_keys": dict(keys),
        "n_players_rosters": len(roster_players),
        "roster_positions": dict(roster_pos),
        "n_tracking_files": len(trk),
        "tracking_gb_compressed": round(sum(p.stat().st_size for p in trk) / 1e9, 2),
        "tracking_frames_sample": frames,
        "frame_rate_hz": 30,
        # initialPressureType se agrega al vocabulario solo si se observa presión distinta de "N"
        "vocab": sorted(k for k in list(ge) + list(pe) if k) + (["initialPressureType"] if pressure else []),
        "coordinates": "metros, centro en (0,0); eventos incluyen posiciones de los 22 jugadores",
        "tracking": True,
        "minutes_field": "derivable de eventos SUB y metadatos de periodos",
        "position_field": "positionGroupType por partido (Rosters)",
    }


# ------------------------------------------------------------------
# TRANSFERMARKT (contexto)
# ------------------------------------------------------------------
def audit_transfermarkt() -> dict:
    import duckdb

    con = duckdb.connect(str(RAW / "transfermarkt/transfermarkt-datasets.duckdb"), read_only=True)
    tables = {}
    for (t,) in con.execute("SELECT table_name FROM information_schema.tables").fetchall():
        tables[t] = int(con.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0])

    def q(sql: str) -> pd.DataFrame:
        return con.execute(sql).fetchdf()

    seasons = q("SELECT min(season) min_season, max(season) max_season FROM games").iloc[0].to_dict()
    big5 = q("""
        SELECT g.competition_id, c.name, g.season, count(*) n_games
        FROM games g JOIN competitions c USING (competition_id)
        WHERE g.competition_id IN ('GB1','ES1','IT1','L1','FR1') AND g.season IN (2015, 2017)
        GROUP BY ALL ORDER BY 1, 3""")
    pos = q("SELECT position, sub_position, count(*) n FROM players GROUP BY ALL ORDER BY 1, 3 DESC")
    dob = (
        q(
            "SELECT avg((date_of_birth IS NULL)::INT) share_missing_dob, avg((sub_position IS NULL)::INT) share_missing_subpos FROM players"
        )
        .iloc[0]
        .to_dict()
    )
    return {
        "source": "Transfermarkt (dcaribou/transfermarkt-datasets, snapshot 2026-07-06)",
        "tables": tables,
        "games_season_range": seasons,
        "big5_games_2015_2017": big5.to_dict("records"),
        "positions": pos.to_dict("records"),
        "missing": dob,
        "vocab": [],
        "tracking": False,
        "minutes_field": "appearances.minutes_played (por partido)",
        "position_field": "players.position / sub_position; game_lineups.position por partido",
    }


# ------------------------------------------------------------------
# CONSOLIDACIÓN
# ------------------------------------------------------------------
# Para cada dimensión: términos que, si aparecen en el vocabulario observado de la fuente, cuentan como evidencia.
COVERAGE_RULES = {
    "Pases": {
        "wyscout": ["Pass"],
        "statsbomb": ["Pass"],
        "skillcorner": ["pass_outcome"],
        "dfl": ["Play"],
        "pff": ["PA"],
    },
    "Conducciones": {
        "wyscout": ["Acceleration"],
        "statsbomb": ["Carry"],
        "skillcorner": ["player_possession"],
        "dfl": [],
        "pff": ["BC"],
    },
    "Remates": {
        "wyscout": ["Shot"],
        "statsbomb": ["Shot"],
        "skillcorner": ["lead_to_shot"],
        "dfl": ["ShotAtGoal"],
        "pff": ["SH"],
    },
    "Duelos": {
        "wyscout": ["Duel"],
        "statsbomb": ["Duel"],
        "skillcorner": ["on_ball_engagement"],
        "dfl": ["TacklingGame"],
        "pff": ["CH"],
    },
    "Recuperaciones/intercep.": {
        "wyscout": ["interception"],
        "statsbomb": ["Ball Recovery", "Interception"],
        "skillcorner": ["recovery_press"],
        "dfl": ["BallClaiming"],
        "pff": [],
    },
    "Presión sobre el rival": {
        "wyscout": [],
        "statsbomb": ["Pressure"],
        "skillcorner": ["pressing", "pressure", "counter_press"],
        "dfl": [],
        "pff": ["initialPressureType"],
    },
    "Carreras sin balón": {
        "wyscout": [],
        "statsbomb": [],
        "skillcorner": ["off_ball_run"],
        "dfl": [],
        "pff": [],
    },
    "Valor de acción (xG/xT)": {
        "wyscout": [],
        "statsbomb": ["statsbomb_xg"],
        "skillcorner": ["xthreat"],
        "dfl": [],
        "pff": [],
    },
}


def combine() -> None:
    A = {}
    for name in ["wyscout", "statsbomb", "skillcorner", "dfl", "pff", "transfermarkt"]:
        p = OUT / f"audit_{name}.json"
        if p.exists():
            A[name] = json.loads(p.read_text())

    inv = []
    if "wyscout" in A:
        w = A["wyscout"]
        inv.append(
            {
                "fuente": "Wyscout",
                "rol": "núcleo eventos",
                "competiciones": w["n_competitions"],
                "temporadas": w["n_seasons"],
                "partidos": w["totals"]["n_matches"],
                "jugadores": w["totals"]["n_players_with_events"],
                "eventos": w["totals"]["n_events"],
                "tracking": "no",
                "periodo": f"{w['period']['min_date'][:10]} a {w['period']['max_date'][:10]}",
            }
        )
    if "statsbomb" in A:
        s = A["statsbomb"]
        inv.append(
            {
                "fuente": "StatsBomb",
                "rol": "validación",
                "competiciones": s["n_competitions"],
                "temporadas": s["n_competition_seasons"],
                "partidos": s["n_matches"],
                "jugadores": s["n_players_lineups"],
                "eventos": s["n_events_total"],
                "tracking": f"360 en {s['n_matches_with_360']} partidos",
                "periodo": f"{s['period']['min_date']} a {s['period']['max_date']}",
            }
        )
    if "skillcorner" in A:
        k = A["skillcorner"]
        inv.append(
            {
                "fuente": "SkillCorner",
                "rol": "tracking / sin balón",
                "competiciones": len(k["competitions"]),
                "temporadas": 1,
                "partidos": k["n_matches"],
                "jugadores": k["n_players"],
                "eventos": k["n_dynamic_events_total"],
                "tracking": f"sí, {k['n_frames_total']:,} frames (10 Hz)",
                "periodo": f"{k['period']['min_date'][:10]} a {k['period']['max_date'][:10]}",
            }
        )
    if "dfl" in A:
        d = A["dfl"]
        inv.append(
            {
                "fuente": "DFL",
                "rol": "eventos + tracking",
                "competiciones": len(d["competitions"]),
                "temporadas": len(d["seasons"]),
                "partidos": d["n_matches"],
                "jugadores": d["n_players"],
                "eventos": d["n_events_total"],
                "tracking": f"sí, {d['n_position_rows_total']:,} filas (25 Hz)",
                "periodo": ", ".join(d["seasons"]),
            }
        )
    if "pff" in A:
        p = A["pff"]
        inv.append(
            {
                "fuente": "PFF FC",
                "rol": "tracking internacional",
                "competiciones": 1,
                "temporadas": 1,
                "partidos": p["n_matches_metadata"],
                "jugadores": p["n_players_rosters"],
                "eventos": p["n_events_root"],
                "tracking": f"sí, {p['n_tracking_files']} archivos ({p['tracking_gb_compressed']} GB bz2)",
                "periodo": "Mundial 2022",
            }
        )
    if "transfermarkt" in A:
        t = A["transfermarkt"]
        inv.append(
            {
                "fuente": "Transfermarkt",
                "rol": "contexto externo",
                "competiciones": t["tables"].get("competitions"),
                "temporadas": int(t["games_season_range"]["max_season"])
                - int(t["games_season_range"]["min_season"])
                + 1,
                "partidos": t["tables"].get("games"),
                "jugadores": t["tables"].get("players"),
                "eventos": t["tables"].get("game_events"),
                "tracking": "no",
                "periodo": f"{int(t['games_season_range']['min_season'])} a {int(t['games_season_range']['max_season'])}",
            }
        )
    pd.DataFrame(inv).to_csv(OUT / "inventory.csv", index=False)

    cov = []
    for dim, rules in COVERAGE_RULES.items():
        row = {"dimension": dim}
        for src, terms in rules.items():
            vocab = set(A.get(src, {}).get("vocab", []))
            hit = [t for t in terms if t in vocab]
            row[src] = "sí: " + ", ".join(hit) if hit else "no observado"
        cov.append(row)
    # dimensiones estructurales que no dependen del vocabulario de eventos
    extra = {
        "Coordenadas de evento": {s: "sí" for s in ["wyscout", "statsbomb", "skillcorner", "dfl", "pff"]},
        "Contexto espacial por evento": {
            "wyscout": "no",
            "statsbomb": "parcial: 360 en subconjunto",
            "skillcorner": "sí: tracking",
            "dfl": "sí: tracking",
            "pff": "sí: 22 jugadores por evento",
        },
        "Tracking continuo": {
            s: ("sí" if A.get(s, {}).get("tracking") is True else "no")
            for s in ["wyscout", "statsbomb", "skillcorner", "dfl", "pff"]
        },
        "Minutos jugados": {
            s: A.get(s, {}).get("minutes_field", "")
            for s in ["wyscout", "statsbomb", "skillcorner", "dfl", "pff"]
        },
        "Posición nominal": {
            s: A.get(s, {}).get("position_field", "")
            for s in ["wyscout", "statsbomb", "skillcorner", "dfl", "pff"]
        },
    }
    for dim, vals in extra.items():
        cov.append({"dimension": dim, **vals})
    pd.DataFrame(cov).to_csv(OUT / "coverage_matrix.csv", index=False)
    print("[ok] inventory.csv, coverage_matrix.csv")


AUDITS = {
    "wyscout": audit_wyscout,
    "statsbomb": audit_statsbomb,
    "skillcorner": audit_skillcorner,
    "dfl": audit_dfl,
    "pff": audit_pff,
    "transfermarkt": audit_transfermarkt,
}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=list(AUDITS) + ["all"])
    ap.add_argument("--combine", action="store_true")
    a = ap.parse_args()
    if a.source:
        for name in AUDITS if a.source == "all" else [a.source]:
            _save(name, AUDITS[name]())
    if a.combine or a.source == "all":
        combine()
