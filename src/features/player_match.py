"""
Tabla jugador-partido de Wyscout: minutos, posesión del equipo, conteos por indicador y por categoría
de acción, y sumas espaciales que permiten agregar sin sesgo a cualquier ventana.

Entrada : data/interim/wyscout/events_parquet/*.parquet, data/interim/wyscout/matches/*.json,
          data/raw/wyscout/players__*/players.json, data/raw/wyscout/teams__*/teams.json
Salida  : data/interim/wyscout/player_match.parquet
          data/interim/wyscout/team_match.parquet  (posesión por equipo y partido)
          data/interim/wyscout/teams.parquet       (nombre decodificado de cada equipo)
          data/interim/wyscout/players.parquet     (atributos del jugador; incluye fecha de nacimiento,
                                                    se usa solo para enlazar fuentes y no se publica)

Minutos. Wyscout no los registra; se reconstruyen con la alineación y los cambios de cada partido:
la duración es la suma, por periodo, del último eventSec observado; los titulares entran en 0, los
suplentes en el minuto del cambio, y salen en el minuto del cambio, de la roja o al final.

Posesión. Aproximada como la proporción de pases del equipo en el partido (config: possession.method).
"""

from __future__ import annotations

import json

import duckdb
import pandas as pd

from src.config import ROOT, load_config, path

EV = str(path("interim") / "wyscout" / "events_parquet" / "*.parquet")
OUT = path("interim") / "wyscout"


def fix_escapes(s):
    # players.json trae nombres con secuencias \uXXXX literales (doble escape en el origen)
    if isinstance(s, str) and "\\u" in s:
        try:
            return s.encode("latin-1", "backslashreplace").decode("unicode_escape")
        except UnicodeDecodeError:
            return s
    return s


def _int(v):
    try:
        v = int(v)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def lineups(con) -> pd.DataFrame:
    """Minutos por jugador y partido a partir de alineaciones, sustituciones y expulsiones."""
    dur = con.execute(f"""
        SELECT match_id, sum(last_sec) / 60.0 AS match_minutes FROM (
            SELECT match_id, match_period, max(event_sec) last_sec FROM read_parquet('{EV}')
            WHERE match_period IN ('1H','2H','E1','E2') GROUP BY 1, 2) GROUP BY 1""").fetchdf()
    dur = dur.set_index("match_id").match_minutes
    rows = []
    for f in sorted((OUT / "matches").glob("matches_*.json")):
        comp = f.stem.replace("matches_", "")
        for m in json.loads(f.read_text()):
            mid, end = m["wyId"], float(dur.get(m["wyId"], 90.0))
            for team in m["teamsData"].values():
                form = team.get("formation") or {}
                subs = form.get("substitutions") or []
                subs = [] if isinstance(subs, str) else subs
                s_in = {s["playerIn"]: s["minute"] for s in subs}
                s_out = {s["playerOut"]: s["minute"] for s in subs}
                for status, plist in (
                    ("starter", form.get("lineup") or []),
                    ("bench", form.get("bench") or []),
                ):
                    for p in plist:
                        pid = p["playerId"]
                        if status == "bench" and pid not in s_in:
                            continue
                        t_in = 0.0 if status == "starter" else float(s_in[pid])
                        t_out = float(s_out.get(pid, end))
                        red = _int(p.get("redCards"))
                        if red is not None:
                            t_out = min(t_out, float(red))
                        rows.append(
                            {
                                "match_id": mid,
                                "competition_file": comp,
                                "season_id": m["seasonId"],
                                "gameweek": m.get("gameweek"),
                                "date_utc": m["dateutc"],
                                "team_id": team["teamId"],
                                "player_id": pid,
                                "started": status == "starter",
                                "minute_in": t_in,
                                "minute_out": t_out,
                                "minutes": max(0.0, min(t_out, end) - t_in),
                                "match_minutes": end,
                            }
                        )
    return pd.DataFrame(rows)


def team_possession(con) -> pd.DataFrame:
    """Posesión aproximada de cada equipo en cada partido: su proporción de pases."""
    tm = con.execute(f"""
        WITH p AS (SELECT match_id, team_id, count(*) n FROM read_parquet('{EV}')
                   WHERE event_name = 'Pass' GROUP BY 1, 2)
        SELECT match_id, team_id, n AS passes, n / sum(n) OVER (PARTITION BY match_id) AS possession_share
        FROM p""").fetchdf()
    return tm


def action_counts(con, categories: dict) -> pd.DataFrame:
    # indicadores de la versión de diagnóstico (mismas definiciones de la Tabla 3 del documento)
    """Conteos por indicador y por categoría de composición, y sumas espaciales, por jugador y partido."""
    cat_sql = ",\n".join(
        f"count(*) FILTER (sub_event_name IN ({', '.join(repr(s) for s in subs)})) AS cat_{name}"
        for name, subs in categories.items()
    )
    return con.execute(f"""
        SELECT match_id, player_id,
            count(*) AS n_actions,
            count(*) FILTER (event_name = 'Pass') AS passes,
            count(*) FILTER (event_name = 'Pass' AND list_contains(tag_ids, 1801)) AS passes_accurate,
            count(*) FILTER (event_name = 'Pass' AND x_end - x_start >= 20 AND list_contains(tag_ids, 1801)) AS prog_passes,
            count(*) FILTER (event_name = 'Pass' AND x_start < 66.7 AND x_end >= 66.7 AND list_contains(tag_ids, 1801)) AS final_third_entries,
            count(*) FILTER (event_name = 'Pass' AND list_contains(tag_ids, 302)) AS key_passes,
            count(*) FILTER (sub_event_name = 'Cross') AS crosses,
            count(*) FILTER (sub_event_name = 'Acceleration') AS carries,
            count(*) FILTER (event_name = 'Shot') AS shots,
            count(*) FILTER (x_start >= 84 AND y_start BETWEEN 19 AND 81) AS box_actions,
            count(*) FILTER (event_name = 'Duel') AS duels,
            count(*) FILTER (event_name = 'Duel' AND list_contains(tag_ids, 703)) AS duels_won,
            count(*) FILTER (sub_event_name = 'Air duel') AS air_duels,
            count(*) FILTER (list_contains(tag_ids, 1401)) AS interceptions,
            count(*) FILTER (sub_event_name = 'Ground defending duel') AS def_duels,
            count(*) FILTER (sub_event_name = 'Ground attacking duel' AND list_contains(tag_ids, 703)) AS dribbles_won,
            count(*) FILTER (sub_event_name = 'Clearance') AS clearances,
            -- sumas espaciales para agregar promedios y dispersión por cualquier ventana
            count(x_start) AS n_loc, sum(x_start) AS sum_x, sum(x_start * x_start) AS sum_x2,
            sum(abs(y_start - 50)) AS sum_absy, sum(y_start) AS sum_y, sum(y_start * y_start) AS sum_y2,
            {cat_sql}
        FROM read_parquet('{EV}')
        WHERE player_id <> 0
        GROUP BY 1, 2""").fetchdf()


def players_table() -> pd.DataFrame:
    """Atributos de los jugadores con nombres decodificados."""
    players = json.loads(next((ROOT / "data/raw/wyscout").glob("players__*/players.json")).read_text())
    return pd.DataFrame(
        [
            {
                "player_id": p["wyId"],
                "short_name": fix_escapes(p["shortName"]),
                "first_name": fix_escapes(p["firstName"]),
                "last_name": fix_escapes(p["lastName"]),
                "birth_date": p["birthDate"],
                "role": p["role"]["code2"],
                "foot": p.get("foot"),
                "height": p.get("height"),
                "current_team_id": _int(p.get("currentTeamId")),
            }
            for p in players
        ]
    )


def teams_table() -> pd.DataFrame:
    """Nombre y país de cada equipo, con nombres decodificados."""
    teams = json.loads(next((ROOT / "data/raw/wyscout").glob("teams__*/teams.json")).read_text())
    return pd.DataFrame(
        [
            {
                "team_id": t["wyId"],
                "team_name": fix_escapes(t["name"]),
                "area": fix_escapes(t["area"]["name"]),
                "team_type": t["type"],
            }
            for t in teams
        ]
    )


def main() -> None:
    cfg = load_config()
    con = duckdb.connect()
    con.execute("SET memory_limit='1500MB'")
    pm = lineups(con)
    tm = team_possession(con)
    ac = action_counts(con, cfg["composition"]["categories"])
    pm = pm.merge(ac, on=["match_id", "player_id"], how="left")
    pm = pm.merge(tm[["match_id", "team_id", "possession_share"]], on=["match_id", "team_id"], how="left")
    # mitad de temporada por jornada (solo ligas); torneos quedan como 'full'
    split = cfg["windows"]["half_split_gameweek"]
    pm["half"] = [
        ("h1" if gw <= split[c] else "h2") if c in split else "full"
        for c, gw in zip(pm.competition_file, pm.gameweek)
    ]
    count_cols = ac.columns.drop(["match_id", "player_id"])
    pm[count_cols] = pm[count_cols].fillna(0).astype("int64")
    pl = players_table()
    pm = pm.merge(pl[["player_id", "role"]], on="player_id", how="left")
    pm.to_parquet(OUT / "player_match.parquet", index=False)
    # orden fijo para que la tabla versionada no cambie entre ejecuciones
    tm.sort_values(["match_id", "team_id"]).to_parquet(OUT / "team_match.parquet", index=False)
    pl.to_parquet(OUT / "players.parquet", index=False)
    teams_table().to_parquet(OUT / "teams.parquet", index=False)
    ratio = (
        pm.groupby(["match_id", "team_id"]).minutes.sum()
        / pm.groupby(["match_id", "team_id"]).match_minutes.first()
    )
    print(f"player_match: {len(pm):,} filas | jugadores en cancha por equipo-partido: {ratio.mean():.2f}")


if __name__ == "__main__":
    main()
