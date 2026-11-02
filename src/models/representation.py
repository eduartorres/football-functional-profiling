"""
Transformación de las representaciones a un espacio común para el modelado (protocolo, sección 3).

estandarización -> ponderación 1/sqrt(n_bloque) -> PCA (80 % de varianza)

El transformador se ajusta en la partición de desarrollo (h1) y se aplica sin reajuste a otras ventanas.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

LOCATION = ["loc_depth", "loc_width", "loc_sd_x", "loc_sd_y"]

BLOCKS = {
    "volume": {
        "distribucion": ["vol_passes", "vol_precision_pase"],
        "progresion": ["vol_prog_passes", "vol_final_third_entries", "vol_carries", "vol_dribbles_won"],
        "creacion": ["vol_key_passes", "vol_crosses"],
        "finalizacion": ["vol_shots", "vol_box_actions"],
        "recuperacion": ["vol_interceptions", "vol_def_duels", "vol_clearances", "vol_air_duels"],
        "localizacion": LOCATION,
    },
    "composition": {
        "composicion": ["clr_pase_simple", "clr_pase_largo", "clr_pase_cabeza", "clr_pase_filtrado", "clr_centro",
                        "clr_remate", "clr_conduccion", "clr_toque", "clr_despeje", "clr_duelo_ofensivo",
                        "clr_duelo_defensivo", "clr_duelo_aereo", "clr_balon_dividido"],
        "localizacion": LOCATION,
    },
    # espacio descriptivo completo: solo para la pertinencia analítica de H4
    "descriptive": {},
}
BLOCKS["descriptive"] = {**{f"v_{k}": v for k, v in BLOCKS["volume"].items() if k != "localizacion"},
                         "composicion": BLOCKS["composition"]["composicion"], "localizacion": LOCATION}

# indicadores sin ajuste para la consulta de la línea base
BASELINE_COLUMNS = ["p90_passes", "p90_prog_passes", "p90_final_third_entries", "p90_key_passes", "p90_crosses",
                    "p90_carries", "p90_shots", "p90_box_actions", "p90_dribbles_won", "p90_interceptions",
                    "p90_def_duels", "p90_clearances", "p90_air_duels"]


def columns(rep: str) -> list[str]:
    return [c for cols in BLOCKS[rep].values() for c in cols]


@dataclass
class Transformer:
    rep: str
    scaler: str = "standard"
    variance: float = 0.80
    center_: np.ndarray = field(default=None, repr=False)
    scale_: np.ndarray = field(default=None, repr=False)
    weights_: np.ndarray = field(default=None, repr=False)
    pca_: PCA = field(default=None, repr=False)

    def fit(self, df: pd.DataFrame, use_pca: bool = True) -> "Transformer":
        X = df[columns(self.rep)].to_numpy(float)
        if self.scaler == "robust":
            self.center_ = np.median(X, axis=0)
            q75, q25 = np.percentile(X, [75, 25], axis=0)
            self.scale_ = np.where(q75 - q25 > 0, q75 - q25, 1.0)
        else:
            self.center_ = X.mean(axis=0)
            self.scale_ = np.where(X.std(axis=0) > 0, X.std(axis=0), 1.0)
        self.weights_ = np.concatenate([[1 / np.sqrt(len(c))] * len(c) for c in BLOCKS[self.rep].values()])
        Z = (X - self.center_) / self.scale_ * self.weights_
        if use_pca:
            self.pca_ = PCA(n_components=self.variance, svd_solver="full").fit(Z)
        return self

    def weighted(self, df: pd.DataFrame) -> np.ndarray:
        X = df[columns(self.rep)].to_numpy(float)
        return (X - self.center_) / self.scale_ * self.weights_

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        Z = self.weighted(df)
        return self.pca_.transform(Z) if self.pca_ is not None else Z

    def loadings(self) -> pd.DataFrame:
        return pd.DataFrame(self.pca_.components_.T, index=columns(self.rep),
                            columns=[f"PC{i + 1}" for i in range(self.pca_.n_components_)])
