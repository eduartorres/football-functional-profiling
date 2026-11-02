"""
Homologación Wyscout - StatsBomb para el Mundial 2018 (64 partidos en ambos proveedores).

Categorías comunes de juego abierto (matriz de definiciones):

| Categoría        | Wyscout                         | StatsBomb                                                     |
|------------------|---------------------------------|---------------------------------------------------------------|
| pase_raso        | Simple pass                     | Pass de juego abierto, altura Ground o Low, sin cabeza/centro/filtrado |
| pase_largo       | High pass, Launch               | Pass de juego abierto, altura High, sin cabeza/centro/filtrado |
| pase_cabeza      | Head pass                       | Pass de juego abierto con body_part Head                     |
| pase_filtrado    | Smart pass                      | Pass de juego abierto con through_ball                        |
| centro           | Cross                           | Pass de juego abierto con cross                               |
| remate           | Shot                            | Shot de juego abierto                                         |
| despeje          | Clearance                       | Clearance                                                     |
| duelo_ofensivo   | Ground attacking duel           | Dribble                                                       |
| duelo_defensivo  | Ground defending duel           | Duel de tipo Tackle, Dribbled Past                            |
| duelo_aereo      | Air duel                        | Duel Aerial Lost y eventos con aerial_won                     |

Conducciones, toques y balones divididos se excluyen: sus definiciones no son equivalentes entre proveedores
(Acceleration de Wyscout frente a Carry de StatsBomb). Coordenadas de StatsBomb (120 x 80) se reescalan a 0-100.

Salida: data/interim/replication/wc2018_{wyscout,statsbomb}.parquet  (una fila por jugador del torneo)
        data/interim/replication/wc2018_player_link.parquet
"""
from __future__ import annotations

import difflib
import json
import unicodedata

import duckdb
import numpy as np
import pandas as pd

from src.common.config import ROOT, path

CATS = ["pase_raso", "pase_largo", "pase_cabeza", "pase_filtrado", "centro", "remate", "despeje",
        "duelo_ofensivo", "duelo_defensivo", "duelo_aereo"]
SB = ROOT / "data/raw/statsbomb/data"
OUT = path("interim") / "replication"


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(s.replace("-", " ").replace(".", " ").split())


def _clock(s: str) -> float:
    m, sec = s.split(":")
    return int(m) + int(sec) / 60


def statsbomb() -> pd.DataFrame:
    comps = json.loads((SB / "competitions.json").read_text())
    c = next(x for x in comps if x["competition_name"] == "FIFA World Cup" and x["season_name"] == "2018")
    matches = json.loads((SB / f"matches/{c['competition_id']}/{c['season_id']}.json").read_text())
    rows, mins = [], []
    for m in matches:
        mid = m["match_id"]
        ev = json.loads((SB / f"events/{mid}.json").read_text())
        end = max(e["minute"] + e["second"] / 60 for e in ev)
        for team in json.loads((SB / f"lineups/{mid}.json").read_text()):
            for p in team["lineup"]:
                if not p["positions"]:
                    continue
                start = min(_clock(s["from"]) for s in p["positions"])
                stop = max(_clock(s["to"]) if s["to"] else end for s in p["positions"])
                mins.append({"sb_player_id": p["player_id"], "sb_name": p["player_name"],
                             "sb_nickname": p.get("player_nickname"), "team": team["team_name"],
                             "match_id": mid, "minutes": max(0.0, stop - start)})
        for e in ev:
            t = e["type"]["name"]
            if "player" not in e:
                continue
            cat = None
            if t == "Pass" and "type" not in e["pass"]:  # sin tipo = juego abierto
                p = e["pass"]
                if p.get("cross"):
                    cat = "centro"
                elif p.get("through_ball"):
                    cat = "pase_filtrado"
                elif p.get("body_part", {}).get("name") == "Head":
                    cat = "pase_cabeza"
                elif p.get("height", {}).get("name") == "High Pass":
                    cat = "pase_largo"
                else:
                    cat = "pase_raso"
            elif t == "Shot" and e["shot"]["type"]["name"] == "Open Play":
                cat = "remate"
            elif t == "Clearance":
                cat = "despeje"
            elif t == "Dribble":
                cat = "duelo_ofensivo"
            elif t == "Dribbled Past" or (t == "Duel" and e["duel"]["type"]["name"] == "Tackle"):
                cat = "duelo_defensivo"
            elif t == "Duel" and e["duel"]["type"]["name"] == "Aerial Lost":
                cat = "duelo_aereo"
            aerial = any(isinstance(v, dict) and v.get("aerial_won") for v in e.values())
            loc = e.get("location")
            for cc in ([cat] if cat else []) + (["duelo_aereo"] if aerial and cat != "duelo_aereo" else []):
                rows.append({"sb_player_id": e["player"]["id"], "cat": cc,
                             "x": loc[0] / 120 * 100 if loc else np.nan, "y": loc[1] / 80 * 100 if loc else np.nan})
    ev = pd.DataFrame(rows)
    mn = pd.DataFrame(mins)
    players = mn.groupby("sb_player_id").agg(sb_name=("sb_name", "first"), sb_nickname=("sb_nickname", "first"),
                                             team=("team", "first"), minutes=("minutes", "sum"),
                                             matches=("match_id", "nunique")).reset_index()
    return aggregate(ev, players, "sb_player_id")


def wyscout() -> pd.DataFrame:
    con = duckdb.connect()
    ev = con.execute(f"""
        SELECT player_id, x_start x, y_start y,
          CASE WHEN sub_event_name = 'Simple pass' THEN 'pase_raso'
               WHEN sub_event_name IN ('High pass', 'Launch') THEN 'pase_largo'
               WHEN sub_event_name = 'Head pass' THEN 'pase_cabeza'
               WHEN sub_event_name = 'Smart pass' THEN 'pase_filtrado'
               WHEN sub_event_name = 'Cross' THEN 'centro'
               WHEN event_name = 'Shot' THEN 'remate'
               WHEN sub_event_name = 'Clearance' THEN 'despeje'
               WHEN sub_event_name = 'Ground attacking duel' THEN 'duelo_ofensivo'
               WHEN sub_event_name = 'Ground defending duel' THEN 'duelo_defensivo'
               WHEN sub_event_name = 'Air duel' THEN 'duelo_aereo' END AS cat
        FROM read_parquet('{path("interim") / "wyscout/events_parquet/World_Cup.parquet"}')
        WHERE player_id <> 0""").fetchdf().dropna(subset=["cat"])
    pm = pd.read_parquet(path("interim") / "wyscout" / "player_match.parquet")
    pm = pm[pm.competition_file == "World_Cup"]
    pl = pd.read_parquet(path("interim") / "wyscout" / "players.parquet")
    teams = {t["wyId"]: t["name"] for t in json.loads(next((ROOT / "data/raw/wyscout").glob("teams__*/teams.json")).read_text())}
    players = pm.groupby("player_id").agg(minutes=("minutes", "sum"), matches=("match_id", "nunique"),
                                          team_id=("team_id", "first")).reset_index()
    players["team"] = players.team_id.map(teams)
    players = players.merge(pl[["player_id", "short_name", "first_name", "last_name", "role"]], on="player_id")
    return aggregate(ev, players, "player_id")


def aggregate(ev: pd.DataFrame, players: pd.DataFrame, key: str) -> pd.DataFrame:
    counts = ev.pivot_table(index=key, columns="cat", values="x", aggfunc="size", fill_value=0)
    counts = counts.reindex(columns=CATS, fill_value=0).add_prefix("cat_")
    loc = ev.groupby(key).agg(loc_depth=("x", "mean"), loc_sd_x=("x", "std"), loc_sd_y=("y", "std"))
    loc["loc_width"] = ev.assign(w=(ev.y - 50).abs()).groupby(key).w.mean()
    return players.merge(counts, left_on=key, right_index=True, how="left").merge(
        loc, left_on=key, right_index=True, how="left")


TEAM_ALIASES = {"south korea": "korea republic"}  # nombre de StatsBomb -> nombre de Wyscout


def link(w: pd.DataFrame, s: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in s.itertuples():
        team = TEAM_ALIASES.get(norm(r.team), norm(r.team))
        cand = w[w.team.map(norm) == team]
        best, sc = None, 0.0
        for c in cand.itertuples():
            full = norm(f"{c.first_name} {c.last_name}")
            score = max(difflib.SequenceMatcher(None, full, norm(r.sb_name)).ratio(),
                        difflib.SequenceMatcher(None, norm(c.short_name), norm(r.sb_nickname)).ratio() if r.sb_nickname else 0,
                        0.9 if norm(c.last_name) and norm(c.last_name) in norm(r.sb_name).split() else 0)
            if score > sc:
                best, sc = c, score
        rows.append({"sb_player_id": r.sb_player_id, "player_id": getattr(best, "player_id", None), "score": sc})
    L = pd.DataFrame(rows)
    L = L[L.score >= 0.75].sort_values("score", ascending=False).drop_duplicates("player_id")
    return L


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s, w = statsbomb(), wyscout()
    L = link(w, s)
    s.to_parquet(OUT / "wc2018_statsbomb.parquet", index=False)
    w.to_parquet(OUT / "wc2018_wyscout.parquet", index=False)
    L.to_parquet(OUT / "wc2018_player_link.parquet", index=False)
    print(f"StatsBomb: {len(s)} jugadores | Wyscout: {len(w)} | enlazados: {len(L)} | equipos sin cruce: "
          f"{sorted(set(s.team.map(norm).replace(TEAM_ALIASES)) - set(w.team.map(norm)))}")


if __name__ == "__main__":
    main()
