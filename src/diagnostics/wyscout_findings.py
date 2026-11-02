"""
Hallazgos preliminares de Wyscout reportados en la sección 5.7 del documento (sin agrupamiento).

1. Población elegible según umbral de minutos.
2. Proporción de la varianza de 18 indicadores explicada por la posición (eta cuadrado, ANOVA de una vía),
   con la posición de Wyscout (3 categorías de campo), la sub-posición del registro de Transfermarkt,
   la posición fina por minutos en 2017/18 y su agrupación sin lado; y por el equipo.
3. Datos de mediocampistas para las figuras del casebook.

Entrada : data/processed/features/player_features_full.parquet, position_reference.parquet
Salida  : data/processed/diagnostics/{eligibility.csv, position_variance.csv, midfielders_scatter.csv}
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.common.config import load_config, path

THRESHOLDS = [0, 450, 900, 1350, 1800]


def eta2(y, g) -> float:
    m = pd.DataFrame({"y": y, "g": g}).dropna()
    if m.g.nunique() < 2:
        return np.nan
    grand = m.y.mean()
    ssb = m.groupby("g").y.apply(lambda s: len(s) * (s.mean() - grand) ** 2).sum()
    sst = ((m.y - grand) ** 2).sum()
    return ssb / sst if sst else np.nan


def indicators(d: pd.DataFrame) -> pd.DataFrame:
    p90 = 90.0 / d.minutes
    return pd.DataFrame(
        {
            "pases_p90": d.passes * p90,
            "precision_pase": d.passes_accurate / d.passes.replace(0, np.nan),
            "pases_progresivos_p90": d.prog_passes * p90,
            "entradas_ultimo_tercio_p90": d.final_third_entries * p90,
            "pases_clave_p90": d.key_passes * p90,
            "centros_p90": d.crosses * p90,
            "conducciones_p90": d.carries * p90,
            "remates_p90": d.shots * p90,
            "acciones_area_p90": d.box_actions * p90,
            "duelos_p90": d.duels * p90,
            "duelos_aereos_p90": d.air_duels * p90,
            "intercepciones_p90": d.interceptions * p90,
            "regates_ganados_p90": d.dribbles_won * p90,
            "profundidad_media_x": d.loc_depth,
            "distancia_al_centro_y": d.loc_width,
            "share_pases": d.passes / d.n_actions,
            "share_duelos": d.duels / d.n_actions,
            "share_remates": d.shots / d.n_actions,
        },
        index=d.index,
    )


def main() -> None:
    cfg = load_config()
    out = path("diagnostics")
    f = pd.read_parquet(path("features") / "player_features_full.parquet")
    pref = pd.read_parquet(path("features") / "position_reference.parquet")
    lg = f[f.is_core].merge(pref[["player_id", "tm_sub_position"]], on="player_id", how="left")

    elig = []
    for t in THRESHOLDS:
        s = lg[lg.minutes >= t]
        elig.append(
            {
                "min_minutes": t,
                "player_seasons": len(s),
                "outfield": int((s.role != "GK").sum()),
                **{f"role_{r}": int((s.role == r).sum()) for r in ["DF", "MD", "FW", "GK"]},
            }
        )
    pd.DataFrame(elig).to_csv(out / "eligibility.csv", index=False)

    d = lg[(lg.role != "GK") & (lg.minutes >= cfg["exposure"]["min_minutes"])].copy()
    F = indicators(d)
    groupings = {
        "wyscout_role": d.role,
        "tm_subposition_snapshot": d.tm_sub_position.where(d.linked.fillna(False).astype(bool)),
        "fine_position": d.fine_position,
        "fine_group": d.fine_group,
        "team": d.main_team_id,
    }
    rows = []
    for c in F.columns:
        r = {"feature": c}
        for k, g in groupings.items():
            r[f"eta2_{k}"] = round(eta2(F[c], g), 3)
        rows.append(r)
    V = pd.DataFrame(rows)
    # referencia sin efecto: (k - 1) / (n - 1)
    V.attrs["n"] = len(d)
    V.to_csv(out / "position_variance.csv", index=False)

    md = d[d.role == "MD"].join(F)
    md[
        [
            "player_id",
            "short_name",
            "competition_file",
            "minutes",
            "tm_sub_position",
            "fine_position",
            "fine_group",
            "profundidad_media_x",
            "pases_progresivos_p90",
            "intercepciones_p90",
            "remates_p90",
            "pases_p90",
            "duelos_p90",
            "distancia_al_centro_y",
        ]
    ].to_csv(out / "midfielders_scatter.csv", index=False)

    print(pd.DataFrame(elig).to_string(index=False))
    print(V.median(numeric_only=True).round(3).to_string())
    print(
        "n:",
        len(d),
        "| equipos:",
        d.main_team_id.nunique(),
        "| referencia sin efecto equipo:",
        round((d.main_team_id.nunique() - 1) / (len(d) - 1), 3),
    )


if __name__ == "__main__":
    main()
