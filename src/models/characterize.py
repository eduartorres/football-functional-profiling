"""
Caracterización de negocio de los perfiles finales (temporada completa, decisión D24).

Para cada perfil resume, en unidades que un analista de scouting puede leer:
- las variables que más lo distinguen de la población (diferencia estandarizada), con su valor típico en el
  perfil y en la población;
- las reglas de un árbol de decisión de profundidad 3 que imita la asignación del modelo. El árbol no reemplaza
  al modelo: traduce sus fronteras a umbrales legibles, y su fidelidad (acuerdo con el modelo en validación
  cruzada) indica qué tanto se puede confiar en esa traducción. Se ajustan dos árboles: uno con todas las
  variables del modelo en unidades originales (proporciones de acción y localización) y otro solo con las
  proporciones de acción, para saber qué parte de los perfiles se explica por el tipo de acciones y no por la
  zona del campo;
- su composición por posición fina y por liga, la exposición típica y los jugadores más cercanos al centroide.

Entrada : data/processed/models/profiles_full_assignments.parquet,
          data/processed/models/profiles_full_representatives.csv,
          data/processed/features/player_features_full.parquet
Salida  : data/processed/models/profile_cards.json, profile_tree_rules.txt
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score
from sklearn.tree import DecisionTreeClassifier, export_text

from src.config import load_config, path

NAMES = {1: "Construcción y defensa posicional", 2: "Carril lateral", 3: "Ataque y finalización"}

# variable -> (etiqueta, unidad, factor de escala para mostrar)
LABELS = {
    "p90_passes": ("Pases por 90 minutos", "", 1),
    "vol_precision_pase": ("Precisión de pase", "%", 100),
    "p90_prog_passes": ("Pases progresivos por 90", "", 1),
    "p90_key_passes": ("Pases clave por 90", "", 1),
    "p90_crosses": ("Centros por 90", "", 1),
    "p90_carries": ("Conducciones por 90", "", 1),
    "p90_dribbles_won": ("Regates ganados por 90", "", 1),
    "p90_shots": ("Remates por 90", "", 1),
    "p90_box_actions": ("Acciones en el área por 90", "", 1),
    "p90_interceptions": ("Intercepciones por 90", "", 1),
    "p90_def_duels": ("Duelos defensivos por 90", "", 1),
    "p90_clearances": ("Despejes por 90", "", 1),
    "p90_air_duels": ("Duelos aéreos por 90", "", 1),
    "comp_pase_simple": ("Pases simples, % de sus acciones", "%", 100),
    "comp_pase_largo": ("Pases largos, % de sus acciones", "%", 100),
    "comp_pase_cabeza": ("Pases de cabeza, % de sus acciones", "%", 100),
    "comp_pase_filtrado": ("Pases filtrados, % de sus acciones", "%", 100),
    "comp_centro": ("Centros, % de sus acciones", "%", 100),
    "comp_remate": ("Remates, % de sus acciones", "%", 100),
    "comp_conduccion": ("Conducciones, % de sus acciones", "%", 100),
    "comp_toque": ("Toques, % de sus acciones", "%", 100),
    "comp_despeje": ("Despejes, % de sus acciones", "%", 100),
    "comp_duelo_ofensivo": ("Duelos ofensivos, % de sus acciones", "%", 100),
    "comp_duelo_defensivo": ("Duelos defensivos, % de sus acciones", "%", 100),
    "comp_duelo_aereo": ("Duelos aéreos, % de sus acciones", "%", 100),
    "comp_balon_dividido": ("Balones divididos, % de sus acciones", "%", 100),
    "loc_depth": ("Profundidad media (0 propia portería, 100 rival)", "", 1),
    "loc_width": ("Distancia media al eje central (0 a 50)", "", 1),
    "loc_sd_x": ("Dispersión a lo largo del campo", "", 1),
    "loc_sd_y": ("Dispersión a lo ancho del campo", "", 1),
}
DESCRIBE = [c for c in LABELS if not c.startswith("loc_sd")]
TREES = {
    "composicion_y_localizacion": [c for c in LABELS if c.startswith(("comp_", "loc_"))],
    "solo_composicion": [c for c in LABELS if c.startswith("comp_")],
}
LEAGUES = {"England": "Premier League", "Spain": "LaLiga", "Italy": "Serie A", "Germany": "Bundesliga",
           "France": "Ligue 1"}  # fmt: skip


def _shown(col: str, v: float) -> float:
    return round(float(v) * LABELS[col][2], 1)


def main() -> None:
    seed = load_config()["project"]["seed"]
    a = pd.read_parquet(path("models") / "profiles_full_assignments.parquet")
    f = pd.read_parquet(path("features") / "player_features_full.parquet")
    keys = ["player_id", "competition_file"]
    d = a.merge(f[keys + list(LABELS)], on=keys, how="left")
    reps = pd.read_csv(path("models") / "profiles_full_representatives.csv")

    mu, sd = d[DESCRIBE].mean(), d[DESCRIBE].std()

    # árboles sustitutos: traducen las fronteras del modelo a umbrales sobre variables legibles
    y = d.profile.to_numpy()
    trees, texts = {}, []
    for name, feats in TREES.items():
        X = d[feats].to_numpy(float)
        tree = DecisionTreeClassifier(max_depth=3, min_samples_leaf=30, random_state=seed)
        fidelity_cv = float(cross_val_score(tree, X, y, cv=5).mean())
        tree.fit(X, y)
        imp = pd.Series(tree.feature_importances_, index=feats).sort_values(ascending=False)
        trees[name] = {
            "max_depth": 3,
            "fidelity_cv": round(fidelity_cv, 3),
            "fidelity_train": round(float((tree.predict(X) == y).mean()), 3),
            "importance": {k: round(float(v), 3) for k, v in imp[imp > 0].items()},
        }
        rules = export_text(tree, feature_names=feats, decimals=3, show_weights=True)
        texts.append(
            f"Árbol {name}: fidelidad {fidelity_cv:.3f} en validación cruzada (5 particiones), "
            f"{trees[name]['fidelity_train']:.3f} en ajuste. Clases: perfiles 1, 2 y 3.\n\n{rules}"
        )
    (path("models") / "profile_tree_rules.txt").write_text("\n".join(texts), encoding="utf-8")

    cards = []
    for p, g in d.groupby("profile"):
        z = ((g[DESCRIBE].mean() - mu) / sd).sort_values(key=np.abs, ascending=False)
        top = [
            {
                "variable": c,
                "label": LABELS[c][0],
                "unit": LABELS[c][1],
                "z": round(float(z[c]), 2),
                "profile_mean": _shown(c, g[c].mean()),
                "population_mean": _shown(c, mu[c]),
            }
            for c in z.index[:8]
        ]
        pos = g.fine_group.value_counts(normalize=True).round(3)
        lg = g.competition_file.map(LEAGUES).value_counts(normalize=True).round(3)
        cards.append(
            {
                "profile": int(p),
                "name": NAMES[int(p)],
                "n": len(g),
                "share": round(len(g) / len(d), 3),
                "minutes_median": round(float(g.minutes.median())),
                "top_variables": top,
                "positions": pos.to_dict(),
                "leagues": lg.to_dict(),
                "representatives": reps[reps.profile == p]
                .head(6)[["short_name", "fine_position"]]
                .to_dict("records"),
            }
        )

    out = {
        "window": "full",
        "n_players": len(d),
        "trees": trees,
        "profiles": cards,
    }
    (path("models") / "profile_cards.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(trees, indent=2, ensure_ascii=False))
    for c in cards:
        print(
            f"\n{c['profile']}. {c['name']} n={c['n']} ({c['share']:.0%}), minutos mediana {c['minutes_median']}"
        )
        for t in c["top_variables"]:
            print(f"   {t['z']:+.2f}  {t['label']}: {t['profile_mean']} frente a {t['population_mean']}")
        print("   posiciones:", c["positions"])
        print("   ligas:", c["leagues"])
    print("\n" + "\n".join(texts))


if __name__ == "__main__":
    main()
