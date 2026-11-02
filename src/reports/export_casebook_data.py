"""
Reúne en un solo JSON las cifras que usa el casebook del video de avances.
Todas las cifras salen de data/processed (diagnóstico y representaciones); ninguna se escribe a mano.

Salida: reports/casebook/casebook_data.json
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data/processed/diagnostics"
OUT = ROOT / "reports/casebook/casebook_data.json"
FEATS_EXAMPLE = [
    "profundidad_media_x",
    "pases_p90",
    "pases_progresivos_p90",
    "intercepciones_p90",
    "duelos_p90",
    "remates_p90",
]


def main() -> None:
    A = {
        n: json.loads((D / f"audit_{n}.json").read_text())
        for n in ["wyscout", "statsbomb", "skillcorner", "dfl", "pff", "transfermarkt"]
    }
    md = pd.read_csv(D / "midfielders_scatter.csv")
    pct = md[FEATS_EXAMPLE].rank(pct=True) * 100

    def example(name):
        i = md.index[md.short_name == name][0]
        return {
            "name": name,
            "competition": md.loc[i, "competition_file"],
            "minutes": round(float(md.loc[i, "minutes"])),
            "tm_sub_position": md.loc[i, "tm_sub_position"],
            "values": {f: round(float(md.loc[i, f]), 2) for f in FEATS_EXAMPLE},
            "percentiles": {f: round(float(pct.loc[i, f])) for f in FEATS_EXAMPLE},
        }

    sb = A["statsbomb"]
    overlap = [
        r
        for r in sb["by_competition_season"]
        if (r["competition"], r["season"])
        in {("FIFA World Cup", "2018"), ("FIFA World Cup", "2022"), ("La Liga", "2017/2018")}
    ]
    pm = pd.read_parquet(ROOT / "data/interim/wyscout/player_match.parquet")
    ps = pd.read_parquet(ROOT / "data/processed/features/player_features_full.parquet")
    tm_ratio = (
        pm.groupby(["match_id", "team_id"]).minutes.sum()
        / pm.groupby(["match_id", "team_id"]).match_minutes.first()
    )

    data = {
        "inventory": pd.read_csv(D / "inventory.csv").to_dict("records"),
        "coverage": pd.read_csv(D / "coverage_matrix.csv").to_dict("records"),
        "eligibility": pd.read_csv(D / "eligibility.csv").to_dict("records"),
        "variance": pd.read_csv(D / "position_variance.csv").to_dict("records"),
        "linkage": json.loads((D / "linkage_summary.json").read_text()),
        "midfielders": md.round(3).to_dict("records"),
        "example_pair": [example("M. Hamšík"), example("M. Diamé")],
        "wyscout": {
            k: A["wyscout"][k]
            for k in [
                "n_competitions",
                "competitions",
                "period",
                "n_matches_metadata",
                "totals",
                "by_competition",
                "player_roles_metadata",
                "event_types",
            ]
        },
        "wyscout_quality": {
            "players_per_team_match_mean": round(float(tm_ratio.mean()), 2),
            "player_match_rows": len(pm),
            "player_season_rows": len(ps),
            "share_events_without_player": A["wyscout"]["totals"]["share_events_without_player"],
            "share_missing_end_xy": A["wyscout"]["totals"]["share_missing_end_xy"],
        },
        "statsbomb_overlap": overlap,
        "statsbomb_big5_1516": sb["big5_2015_16"],
        "pff": {
            k: A["pff"][k]
            for k in [
                "n_matches_metadata",
                "n_events_root",
                "n_players_rosters",
                "n_tracking_files",
                "tracking_gb_compressed",
            ]
        },
        "skillcorner": {
            k: A["skillcorner"][k]
            for k in ["competitions", "n_matches", "n_players", "n_frames_total", "dynamic_event_types"]
        },
        "dfl": {
            k: A["dfl"][k]
            for k in [
                "competitions",
                "seasons",
                "n_matches",
                "n_players",
                "n_events_total",
                "n_position_rows_total",
            ]
        },
        "transfermarkt": {k: A["transfermarkt"][k] for k in ["tables", "games_season_range"]},
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, default=str))
    print(f"{OUT} ({OUT.stat().st_size / 1e3:.0f} KB)")


if __name__ == "__main__":
    main()
