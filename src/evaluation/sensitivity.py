"""
Análisis de sensibilidad de la solución seleccionada (sección 7.4 del documento).

Variantes en la temporada completa: umbral de minutos (450, 900, 1.350), escalamiento robusto, distancia
coseno (normalización de filas antes de K-means), número de grupos (k = 4 y 5) y representación de volumen.
Para cada variante: silueta, NMI con posición fina y con equipo, y ARI con la solución de referencia sobre
los jugadores comunes.

Salida: data/processed/evaluation/sensitivity.csv
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score

from src.config import load_config, path
from src.evaluation.common import fitted_model, selected
from src.models.representation import Transformer


def full_window(min_minutes: int) -> pd.DataFrame:
    """Población de la temporada completa con un umbral de minutos distinto al de referencia."""
    d = pd.read_parquet(path("features") / "player_features_full.parquet")
    keep = d.is_core & (d.role != "GK") & (d.minutes >= min_minutes) & d.fine_group.notna()
    return d[keep].reset_index(drop=True)


def solve(d, rep, conf, scaler="standard", cosine=False):
    """Ajusta transformador y modelo sobre una variante y devuelve coordenadas y etiquetas."""
    T = Transformer(rep, scaler=scaler).fit(d)
    X = T.transform(d)
    if cosine:
        X = X / np.linalg.norm(X, axis=1, keepdims=True)
    _, lab = fitted_model(rep, conf, X)
    return X, lab


def main() -> None:
    cfg = load_config()
    rep, conf = selected()
    base_d = full_window(cfg["exposure"]["min_minutes"])
    _, base_lab = solve(base_d, rep, conf)
    ref = pd.Series(base_lab, index=list(zip(base_d.player_id, base_d.competition_file)))
    variants = [("referencia", 900, rep, conf, "standard", False)]
    variants += [
        (f"minutos >= {m}", m, rep, conf, "standard", False) for m in cfg["exposure"]["alt_min_minutes"]
    ]
    variants += [
        ("escalamiento robusto", 900, rep, conf, "robust", False),
        ("distancia coseno", 900, rep, conf, "standard", True),
        ("k = 4", 900, rep, {**conf, "k": 4}, "standard", False),
        ("k = 5", 900, rep, {**conf, "k": 5}, "standard", False),
        ("representación de volumen", 900, "volume", conf, "standard", False),
    ]
    rows = []
    for name, mm, r, c, sc, cos in variants:
        d = full_window(mm)
        X, lab = solve(d, r, c, sc, cos)
        idx = list(zip(d.player_id, d.competition_file))
        common = [i for i, key in enumerate(idx) if key in ref.index]
        ari = adjusted_rand_score(ref.loc[[idx[i] for i in common]].to_numpy(), lab[common])
        rows.append(
            {
                "variante": name,
                "n": len(d),
                "k": c["k"],
                "silueta": silhouette_score(X, lab),
                "nmi_posicion_fina": normalized_mutual_info_score(d.fine_group, lab),
                "nmi_equipo": normalized_mutual_info_score(d.main_team_id, lab),
                "ari_con_referencia": ari,
            }
        )
    R = pd.DataFrame(rows)
    R.to_csv(path("evaluation") / "sensitivity.csv", index=False)
    print(R.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
