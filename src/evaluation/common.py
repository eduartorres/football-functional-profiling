"""Utilidades compartidas por la evaluación: carga de ventanas, modelo seleccionado y espacios."""
from __future__ import annotations

import json
import pickle

import numpy as np
import pandas as pd

from src.common.config import load_config, path
from src.models import clustering as cl
from src.models.representation import BASELINE_COLUMNS, Transformer


def window(w: str, eligible_only: bool = True) -> pd.DataFrame:
    d = pd.read_parquet(path("features") / f"player_features_{w}.parquet")
    return (d[d.eligible] if eligible_only else d).reset_index(drop=True)


def selected():
    sel = json.loads((path("models") / "selected_model.json").read_text())
    return sel["representation"], {"algorithm": sel["algorithm"], "k": int(sel["k"])}


def transformer(rep: str) -> Transformer:
    return pickle.loads((path("models") / f"transformer_{rep}.pkl").read_bytes())


def fitted_model(rep: str, conf: dict, X: np.ndarray):
    model, labels = cl.fit(conf, X, load_config()["project"]["seed"])
    return model, labels


class Standardizer:
    """Estandarización simple ajustada en desarrollo (para la línea base y el espacio descriptivo)."""

    def __init__(self, cols):
        self.cols = cols

    def fit(self, d):
        X = d[self.cols].to_numpy(float)
        self.mu, self.sd = X.mean(0), np.where(X.std(0) > 0, X.std(0), 1)
        return self

    def transform(self, d):
        return (d[self.cols].to_numpy(float) - self.mu) / self.sd


def baseline_space(dev: pd.DataFrame) -> Standardizer:
    return Standardizer(BASELINE_COLUMNS).fit(dev)
