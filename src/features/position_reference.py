"""
Posición fina de referencia para cada jugador de las cinco ligas 2017/18 (sección 4.4.1 del documento).

1. Enlace Wyscout -> Transfermarkt por fecha de nacimiento y similitud de nombre.
2. Posición principal en 2017/18 según los minutos jugados en cada posición de alineación de Transfermarkt
   (game_lineups x appearances). Si el jugador no tiene alineaciones, se usa la sub-posición del registro.
3. Agrupación sin lado (fine_group), porque los indicadores espaciales son simétricos en el eje y.

Salida : data/processed/features/position_reference.parquet
         data/processed/diagnostics/linkage_summary.json
"""

from __future__ import annotations

import difflib
import json
import unicodedata

import duckdb
import pandas as pd

from src.common.config import load_config, path


def norm(s) -> str:
    """Normaliza un nombre: sin tildes, en minúsculas y sin guiones ni puntos."""
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(s.replace("-", " ").replace(".", " ").split())


def name_score(first, last, short, tm_name) -> float:
    """Similitud entre el nombre de Wyscout y el de Transfermarkt, entre 0 y 1."""
    b = norm(tm_name)
    s = difflib.SequenceMatcher(None, norm(f"{first} {last}"), b).ratio()
    # apellidos compuestos o nombres artísticos: basta con que un token del apellido coincida
    if any(t in b.split() for t in norm(last).split() if len(t) > 2):
        s = max(s, 0.85)
    sh = norm(short).split()[-1] if short else ""
    if sh and sh in b.split():
        s = max(s, 0.8)
    return s


def main() -> None:
    cfg = load_config()
    core = cfg["core"]
    pm = pd.read_parquet(path("interim") / "wyscout" / "player_match.parquet")
    pl = pd.read_parquet(path("interim") / "wyscout" / "players.parquet")
    pool = pl[pl.player_id.isin(pm.loc[pm.competition_file.isin(core["competitions"]), "player_id"])]

    con = duckdb.connect(str(path("transfermarkt_db")), read_only=True)
    tm = con.execute("""SELECT player_id tm_id, name tm_name, date_of_birth::DATE::VARCHAR dob,
                               position tm_position, sub_position tm_sub_position FROM players""").fetchdf()

    # 1. enlace
    by_dob = {k: g for k, g in tm.groupby("dob")}
    links = []
    for r in pool.itertuples():
        cands = by_dob.get(r.birth_date, tm.iloc[0:0])
        best, score = None, 0.0
        for c in cands.itertuples():
            s = name_score(r.first_name, r.last_name, r.short_name, c.tm_name)
            if s > score:
                best, score = c, s
        links.append(
            {
                "player_id": r.player_id,
                "tm_id": getattr(best, "tm_id", None),
                "tm_name": getattr(best, "tm_name", None),
                "tm_sub_position": getattr(best, "tm_sub_position", None),
                "n_dob_candidates": len(cands),
                "name_score": round(score, 3),
            }
        )
    L = pd.DataFrame(links)
    L["linked"] = L.name_score >= cfg["position_reference"]["linkage_min_name_score"]
    # un mismo jugador de Transfermarkt no puede quedar enlazado a dos de Wyscout: se conserva el de mayor puntaje
    dup = L[L.linked].sort_values("name_score", ascending=False).duplicated("tm_id")
    L.loc[dup[dup].index, "linked"] = False

    # 2. posición principal por minutos en la temporada
    ids = ", ".join(repr(c) for c in core["transfermarkt_competition_ids"])
    pos = con.execute(f"""
        SELECT l.player_id tm_id, l.position, sum(a.minutes_played) AS minutes
        FROM game_lineups l
        JOIN games g USING (game_id)
        JOIN appearances a ON a.game_id = l.game_id AND a.player_id = l.player_id
        WHERE g.season = '{core["transfermarkt_season"]}' AND g.competition_id IN ({ids})
          AND a.minutes_played > 0
        GROUP BY 1, 2""").fetchdf()
    tot = pos.groupby("tm_id").minutes.transform("sum")
    pos["share"] = pos.minutes / tot
    main_pos = (
        pos.sort_values(["tm_id", "minutes"], ascending=[True, False])
        .groupby("tm_id")
        .agg(
            tm_main_position=("position", "first"),
            main_share=("share", "first"),
            n_positions=("position", "nunique"),
            tm_minutes=("minutes", "sum"),
        )
        .reset_index()
    )
    R = L.merge(main_pos, on="tm_id", how="left")
    R.loc[~R.linked, ["tm_main_position", "main_share", "n_positions", "tm_minutes"]] = None
    R["position_source"] = "lineups_2017_18"
    fallback = R.linked & R.tm_main_position.isna()
    R.loc[fallback, "tm_main_position"] = R.loc[fallback, "tm_sub_position"]
    R.loc[fallback, "position_source"] = "registro_snapshot"
    R.loc[~R.linked, "position_source"] = "sin_enlace"
    R["fine_position"] = R.tm_main_position
    R["fine_group"] = R.tm_main_position.map(cfg["position_reference"]["fine_groups"])
    R = R.merge(pl[["player_id", "short_name", "role"]], on="player_id", how="left")
    R.to_parquet(path("features") / "position_reference.parquet", index=False)

    summ = {
        "players_in_pool": len(R),
        "linked": int(R.linked.sum()),
        "linked_share": round(R.linked.mean(), 4),
        "position_from_lineups": int((R.position_source == "lineups_2017_18").sum()),
        "position_from_snapshot": int((R.position_source == "registro_snapshot").sum()),
        "main_share_median": round(float(R.main_share.median()), 3),
        "rule": "misma fecha de nacimiento y similitud de nombre >= umbral; tm_id único",
    }
    (path("diagnostics") / "linkage_summary.json").write_text(json.dumps(summ, indent=2))
    print(json.dumps(summ, indent=2))
    print(R.fine_group.value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
