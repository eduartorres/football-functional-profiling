"""
Representaciones del comportamiento por jugador y ventana (sección 4.4.2 del documento).

Ventanas: full (temporada completa), h1 y h2 (mitades por jornada). Unidad: jugador x competición x ventana.

Bloques de variables
  vol_*  volumen por 90 minutos ajustado por posesión, expresado a 50 % de posesión:
         acciones con balón sobre minutos de posesión propia, acciones defensivas sobre posesión rival.
  p90_*  las mismas tasas sin ajuste (solo para diagnóstico y comparación).
  comp_* proporción de cada categoría de acción en juego abierto sobre el total de esas acciones.
  clr_*  transformación log-ratio centrada de comp_*, con reemplazo multiplicativo de ceros.
  loc_*  localización: profundidad media, distancia media al eje central y dispersión en x e y.

Salida : data/processed/features/player_features_{full,h1,h2}.parquet
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.common.config import load_config, path

ON_BALL = [
    "passes",
    "prog_passes",
    "final_third_entries",
    "key_passes",
    "crosses",
    "carries",
    "shots",
    "box_actions",
    "dribbles_won",
]
DEFENSIVE = ["interceptions", "def_duels", "clearances"]
NEUTRAL = ["air_duels"]
RATIOS = {"precision_pase": ("passes_accurate", "passes")}


def multiplicative_replacement(counts: np.ndarray, half_count: float) -> np.ndarray:
    """Proporciones con reemplazo multiplicativo de ceros (Martín-Fernández et al., 2003).

    Cada cero recibe delta = half_count / total del jugador; los valores no nulos se reescalan
    para que la composición siga sumando uno.
    """
    tot = counts.sum(axis=1, keepdims=True)
    x = counts / tot
    delta = half_count / tot
    zeros = counts == 0
    k = zeros.sum(axis=1, keepdims=True)
    return np.where(zeros, delta, x * (1 - k * delta))


def clr(x: np.ndarray) -> np.ndarray:
    """Transformación log-ratio centrada de composiciones sin ceros (Aitchison, 1982)."""
    lx = np.log(x)
    return lx - lx.mean(axis=1, keepdims=True)


def aggregate(pm: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Agrega la tabla jugador-partido a jugador x competición y construye los bloques de variables."""
    p = pm.copy()
    p["own_min"] = p.minutes * p.possession_share
    p["opp_min"] = p.minutes * (1 - p.possession_share)
    keys = ["player_id", "competition_file"]
    cats = [c for c in p.columns if c.startswith("cat_")]
    sums = (
        [
            "minutes",
            "own_min",
            "opp_min",
            "n_actions",
            "passes_accurate",
            "duels",
            "duels_won",
            "n_loc",
            "sum_x",
            "sum_x2",
            "sum_absy",
            "sum_y",
            "sum_y2",
        ]
        + ON_BALL
        + DEFENSIVE
        + NEUTRAL
        + cats
    )
    sums = list(dict.fromkeys(sums))
    g = p.groupby(keys)
    a = g[sums].sum()
    a["matches"] = g.match_id.nunique()
    a["starts"] = g.started.sum()
    a["n_teams"] = g.team_id.nunique()
    a["team_possession_mean"] = g.apply(
        lambda d: np.average(d.possession_share, weights=d.minutes) if d.minutes.sum() > 0 else np.nan,
        include_groups=False,
    )
    a = a.reset_index()
    main_team = (
        p.groupby(keys + ["team_id"])
        .minutes.sum()
        .reset_index()
        .sort_values("minutes")
        .drop_duplicates(keys, keep="last")
        .rename(columns={"team_id": "main_team_id"})[keys + ["main_team_id"]]
    )
    a = a.merge(main_team, on=keys, how="left")

    ref = cfg["possession"]["reference_share"]
    for c in ON_BALL:
        a[f"p90_{c}"] = a[c] / a.minutes * 90
        a[f"vol_{c}"] = a[c] / a.own_min * 90 * ref
    for c in DEFENSIVE:
        a[f"p90_{c}"] = a[c] / a.minutes * 90
        a[f"vol_{c}"] = a[c] / a.opp_min * 90 * ref
    for c in NEUTRAL:
        a[f"p90_{c}"] = a[c] / a.minutes * 90
        a[f"vol_{c}"] = a[f"p90_{c}"]
    for name, (num, den) in RATIOS.items():
        a[f"vol_{name}"] = a[num] / a[den].replace(0, np.nan)

    # localización
    a["loc_depth"] = a.sum_x / a.n_loc
    a["loc_width"] = a.sum_absy / a.n_loc
    a["loc_sd_x"] = np.sqrt(np.maximum(a.sum_x2 / a.n_loc - a.loc_depth**2, 0))
    a["loc_sd_y"] = np.sqrt(np.maximum(a.sum_y2 / a.n_loc - (a.sum_y / a.n_loc) ** 2, 0))

    # composición en juego abierto
    C = a[cats].to_numpy(dtype=float)
    ok = C.sum(axis=1) > 0
    comp = np.full_like(C, np.nan)
    clr_ = np.full_like(C, np.nan)
    comp[ok] = C[ok] / C[ok].sum(axis=1, keepdims=True)
    # el reemplazo solo es válido si la masa asignada a los ceros es menor que uno (exposición suficiente)
    hc = cfg["composition"]["zero_replacement_counts"]
    tot = C.sum(axis=1)
    ok_clr = ok & ((C == 0).sum(axis=1) * hc / np.where(tot > 0, tot, 1) < 1)
    clr_[ok_clr] = clr(multiplicative_replacement(C[ok_clr], hc))
    names = [c.replace("cat_", "") for c in cats]
    a[[f"comp_{n}" for n in names]] = comp
    a[[f"clr_{n}" for n in names]] = clr_
    a["n_open_play_actions"] = C.sum(axis=1)
    return a


def main() -> None:
    cfg = load_config()
    pm = pd.read_parquet(path("interim") / "wyscout" / "player_match.parquet")
    pref = pd.read_parquet(path("features") / "position_reference.parquet")
    pl = pd.read_parquet(path("interim") / "wyscout" / "players.parquet")
    windows = {"full": pm, "h1": pm[pm.half == "h1"], "h2": pm[pm.half == "h2"]}
    for w, d in windows.items():
        a = aggregate(d, cfg)
        a = a.merge(pl[["player_id", "short_name", "role", "birth_date"]], on="player_id", how="left")
        a = a.merge(
            pref[
                [
                    "player_id",
                    "tm_id",
                    "linked",
                    "fine_position",
                    "fine_group",
                    "position_source",
                    "main_share",
                ]
            ],
            on="player_id",
            how="left",
        )
        min_m = cfg["exposure"]["min_minutes"] if w == "full" else cfg["exposure"]["min_minutes_half"]
        a["is_core"] = a.competition_file.isin(cfg["core"]["competitions"])
        a["eligible"] = a.is_core & (a.role != "GK") & (a.minutes >= min_m) & a.fine_group.notna()
        a["window"] = w
        a.to_parquet(path("features") / f"player_features_{w}.parquet", index=False)
        print(f"{w}: {len(a):,} filas | elegibles {int(a.eligible.sum()):,}")


if __name__ == "__main__":
    main()
