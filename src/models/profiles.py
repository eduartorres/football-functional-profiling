"""
Caracterización de los perfiles de la solución seleccionada (protocolo, sección 5, paso 4).

Ajusta la configuración de data/processed/models/selected_model.json en la ventana indicada y describe
cada perfil con variables originales, composición por posición fina y jugadores representativos
(los más cercanos al centroide en el espacio de componentes).

Uso: python -m src.models.profiles [--window h1]
Salidas en data/processed/models/: profiles_<window>_assignments.parquet, profiles_<window>_summary.csv,
profiles_<window>_positions.csv, profiles_<window>_representatives.csv
"""
from __future__ import annotations

import argparse
import json
import pickle

import numpy as np
import pandas as pd

from src.common.config import load_config, path
from src.models import clustering as cl
from src.models.representation import Transformer

DESCRIBE = ["p90_passes", "vol_precision_pase", "p90_prog_passes", "p90_key_passes", "p90_crosses", "p90_carries",
            "p90_dribbles_won", "p90_shots", "p90_box_actions", "p90_interceptions", "p90_def_duels",
            "p90_clearances", "p90_air_duels", "comp_pase_simple", "comp_pase_largo", "comp_centro", "comp_remate",
            "comp_toque", "comp_despeje", "comp_duelo_ofensivo", "comp_duelo_defensivo", "comp_duelo_aereo",
            "loc_depth", "loc_width"]


def main(window: str = "h1") -> None:
    cfg = load_config()
    sel = json.loads((path("models") / "selected_model.json").read_text())
    rep, conf = sel["representation"], {"algorithm": sel["algorithm"], "k": int(sel["k"])}
    d = pd.read_parquet(path("features") / f"player_features_{window}.parquet")
    d = d[d.eligible].reset_index(drop=True)
    tf = path("models") / f"transformer_{rep}.pkl"
    T: Transformer = pickle.loads(tf.read_bytes())
    if window != "h1":
        # D24: para los perfiles finales el transformador se reajusta en la ventana completa
        T = Transformer(rep, scaler=T.scaler, variance=T.variance).fit(d)
    X = T.transform(d)
    model, labels = cl.fit(conf, X, cfg["project"]["seed"])
    # orden estable de perfiles: por profundidad media creciente
    order = d.groupby(labels).loc_depth.mean().sort_values().index
    remap = {old: new for new, old in enumerate(order, 1)}
    d["profile"] = [remap[l] for l in labels]
    cent = np.vstack([X[labels == old].mean(axis=0) for old in order])
    d["dist_centroid"] = np.linalg.norm(X - cent[d.profile - 1], axis=1)

    out = path("models")
    d[["player_id", "short_name", "competition_file", "main_team_id", "minutes", "fine_position", "fine_group",
       "role", "profile", "dist_centroid"]].to_parquet(out / f"profiles_{window}_assignments.parquet", index=False)
    mu, sd = d[DESCRIBE].mean(), d[DESCRIBE].std()
    summ = d.groupby("profile")[DESCRIBE].mean()
    z = ((summ - mu) / sd).add_prefix("z_")
    summ = summ.join(z)
    summ.insert(0, "n", d.groupby("profile").size())
    summ.to_csv(out / f"profiles_{window}_summary.csv")
    pos = pd.crosstab(d.fine_group, d.profile)
    pos.to_csv(out / f"profiles_{window}_positions.csv")
    reps = (d.sort_values("dist_centroid").groupby("profile").head(8)
            [["profile", "short_name", "competition_file", "fine_position", "minutes", "dist_centroid"]])
    reps.to_csv(out / f"profiles_{window}_representatives.csv", index=False)

    pd.set_option("display.width", 220)
    print(f"{rep} / {conf} en {window}: {len(d)} jugadores")
    print(summ[["n"] + [f"z_{c}" for c in DESCRIBE]].round(2).T.to_string())
    print(pos.to_string())
    print((pos / pos.sum(axis=0)).round(2).to_string())
    print(reps.to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", default="h1")
    main(ap.parse_args().window)
