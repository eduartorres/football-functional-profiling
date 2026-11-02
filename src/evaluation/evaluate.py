"""
Evaluación de la solución seleccionada (protocolo, secciones 4 y 7; capítulo 7 del documento).

1. Reserva temporal: el transformador y el modelo ajustados en h1 asignan h2 sin reajuste.
2. H1: NMI entre perfiles y posición fina, en desarrollo y en reserva.
3. H2: proporción de los 10 vecinos de otra posición fina (reserva) y autoidentificación entre mitades,
   contra la línea base de indicadores por 90 sin ajuste.
4. H3: estabilidad bootstrap (grilla confirmada) y consistencia temporal por jugador.
5. Generalización a jugadores nuevos: validación agrupada por jugador (5 particiones) en la temporada completa.

Salida: data/processed/evaluation/evaluation_core.json y archivos auxiliares.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score
from sklearn.model_selection import GroupKFold

from src.common.config import load_config, path
from src.evaluation.common import baseline_space, fitted_model, selected, transformer, window
from src.models import clustering as cl
from src.models.representation import Transformer


def knn_other_position(X, groups, k):
    D = ((X[:, None, :] - X[None, :, :]) ** 2).sum(-1)
    np.fill_diagonal(D, np.inf)
    nn = np.argsort(D, axis=1)[:, :k]
    return float((groups[nn] != groups[:, None]).mean())


def self_identification(A, B, ks=(1, 10)):
    """A y B: matrices de los mismos jugadores (mismo orden) en h1 y h2. Rango del propio jugador."""
    D = ((A[:, None, :] - B[None, :, :]) ** 2).sum(-1)
    rank = (D < np.diag(D)[:, None]).sum(axis=1)  # cuántos jugadores de h2 están más cerca que él mismo
    out = {f"top{k}": float((rank < k).mean()) for k in ks}
    out["mrr"] = float(np.mean(1 / (rank + 1)))
    out["n"] = int(len(A))
    return out


def main() -> None:
    cfg = load_config()
    H = cfg["hypotheses"]
    rep, conf = selected()
    h1, h2, full = window("h1"), window("h2"), window("full")
    T = transformer(rep)
    X1, X2 = T.transform(h1), T.transform(h2)
    model, lab1 = fitted_model(rep, conf, X1)
    lab2 = model.predict(X2)
    _, lab2_refit = fitted_model(rep, conf, X2)
    res = {"representation": rep, **conf, "n_h1": len(h1), "n_h2": len(h2)}

    # 1. reserva temporal
    res["reserve"] = {
        "silhouette_h2_assigned": float(silhouette_score(X2, lab2)),
        "ari_assigned_vs_refit_h2": float(adjusted_rand_score(lab2, lab2_refit)),
        "cluster_sizes_h1": np.bincount(lab1).tolist(), "cluster_sizes_h2": np.bincount(lab2).tolist(),
        "nmi_team_h2": float(normalized_mutual_info_score(h2.main_team_id, lab2)),
        "cramers_v_team_h2": cl.cramers_v(lab2, h2.main_team_id.to_numpy()),
    }

    # 2. H1
    nmi1 = float(normalized_mutual_info_score(h1.fine_group, lab1))
    nmi2 = float(normalized_mutual_info_score(h2.fine_group, lab2))
    res["H1"] = {"nmi_fine_group_h1": nmi1, "nmi_fine_group_h2": nmi2,
                 "threshold": H["h1_max_nmi_fine_position"], "rejected": bool(nmi2 >= H["h1_max_nmi_fine_position"])}

    # 3. H2: vecinos y autoidentificación
    k = H["h2_neighbors_k"]
    both = h1.merge(h2[["player_id", "competition_file"]], on=["player_id", "competition_file"])
    a = h1.set_index(["player_id", "competition_file"]).loc[list(zip(both.player_id, both.competition_file))].reset_index()
    b = h2.set_index(["player_id", "competition_file"]).loc[list(zip(both.player_id, both.competition_file))].reset_index()
    base = baseline_space(h1)
    other = {"functional": knn_other_position(X2, h2.fine_group.to_numpy(), k),
             "baseline_p90": knn_other_position(base.transform(h2), h2.fine_group.to_numpy(), k)}
    si = {"functional": self_identification(T.transform(a), T.transform(b)),
          "baseline_p90": self_identification(base.transform(a), base.transform(b))}
    # sensibilidad: la otra representación
    alt = "volume" if rep == "composition" else "composition"
    Ta = transformer(alt)
    si[f"functional_{alt}"] = self_identification(Ta.transform(a), Ta.transform(b))
    other[f"functional_{alt}"] = knn_other_position(Ta.transform(h2), h2.fine_group.to_numpy(), k)
    res["H2"] = {"share_neighbors_other_position": other, "self_identification": si,
                 "thresholds": {"min_share": H["h2_min_share_neighbors_other_position"],
                                "min_top1": H["h2_min_self_identification_top1"]},
                 "rejected": bool(other["functional"] < H["h2_min_share_neighbors_other_position"]
                                  or si["functional"]["top1"] < H["h2_min_self_identification_top1"])}

    # 4. H3: estabilidad bootstrap de la grilla confirmada + consistencia temporal por jugador
    g = pd.read_csv(path("models") / "grid_confirm.csv")
    row = g[(g.representation == rep) & (g.algorithm == conf["algorithm"]) & (g.k == conf["k"])].iloc[0]
    la = model.predict(T.transform(a))
    lb = model.predict(T.transform(b))
    same = float((la == lb).mean())
    p = np.bincount(lab1, minlength=conf["k"]) / len(lab1)
    res["H3"] = {"ari_bootstrap_mean": float(row.ari_mean), "jaccard_by_cluster": row.jaccard_by_cluster,
                 "temporal_same_profile_share": same, "temporal_chance_share": float((p ** 2).sum()),
                 "temporal_ari_players": float(adjusted_rand_score(la, lb)), "n_players_both_halves": len(a),
                 "rejected": bool(row.ari_mean < H["h3_min_mean_ari"] or row.share_clusters_jaccard_ok <= 0.5)}
    transitions = pd.crosstab(pd.Series(la, name="perfil_h1"), pd.Series(lb, name="perfil_h2"))
    transitions.to_csv(path("evaluation") / "temporal_transitions.csv")

    # 5. generalización a jugadores nuevos (temporada completa, particiones agrupadas por jugador)
    Tf = Transformer(rep, scaler=T.scaler, variance=T.variance).fit(full)
    Xf = Tf.transform(full)
    _, lab_full = fitted_model(rep, conf, Xf)
    aris = []
    for tr, te in GroupKFold(n_splits=5).split(Xf, groups=full.player_id):
        Tt = Transformer(rep, scaler=T.scaler, variance=T.variance).fit(full.iloc[tr])
        m, _ = fitted_model(rep, conf, Tt.transform(full.iloc[tr]))
        aris.append(adjusted_rand_score(lab_full[te], m.predict(Tt.transform(full.iloc[te]))))
    res["generalization"] = {"ari_heldout_mean": float(np.mean(aris)), "ari_heldout_min": float(np.min(aris)),
                             "folds": 5}

    out = path("evaluation") / "evaluation_core.json"
    out.write_text(json.dumps(res, indent=2, ensure_ascii=False))
    print(json.dumps(res, indent=2, ensure_ascii=False))
    print(transitions)


if __name__ == "__main__":
    main()
