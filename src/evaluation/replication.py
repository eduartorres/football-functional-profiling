"""
Replicación de las dimensiones funcionales con StatsBomb en el Mundial 2018 (protocolo, sección 8).

Población: jugadores de campo enlazados entre proveedores con al menos 270 minutos en ambos.
Representación: composición homologada (10 categorías, clr) + localización, misma ponderación por bloque.

Medidas
- acuerdo por variable: correlación de Spearman entre proveedores para los mismos jugadores;
- congruencia de Tucker entre las cargas de PCA ajustadas por separado en cada proveedor;
- concordancia de perfiles: ARI entre K-means (k del modelo seleccionado) ajustado en cada proveedor, y
  entre la asignación Wyscout y la de StatsBomb proyectada con el transformador y el modelo de Wyscout;
- vecinos: superposición de los 10 vecinos de cada jugador en ambos espacios (Jaccard) frente al azar;
- identificación cruzada: rango del mismo jugador al buscar su vector de StatsBomb entre los de Wyscout.

Salida: data/processed/evaluation/replication.json, replication_variables.csv
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import spearmanr
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score

from src.config import load_config, path
from src.evaluation.common import selected
from src.features.player_features import clr, multiplicative_replacement
from src.harmonization.statsbomb_wc2018 import CATS

LOC = ["loc_depth", "loc_width", "loc_sd_x", "loc_sd_y"]
MIN_MINUTES = 270


def represent(d: pd.DataFrame, hc: float) -> pd.DataFrame:
    """Composición homologada (proporciones y clr) y bloque de localización de cada jugador."""
    C = d[[f"cat_{c}" for c in CATS]].to_numpy(float)
    out = pd.DataFrame(
        clr(multiplicative_replacement(C, hc)), columns=[f"clr_{c}" for c in CATS], index=d.index
    )
    comp = pd.DataFrame(C / C.sum(1, keepdims=True), columns=[f"comp_{c}" for c in CATS], index=d.index)
    return pd.concat([out, comp, d[LOC]], axis=1)


class Space:
    def __init__(self, var=0.80):
        self.var = var

    def fit(self, R):
        cols = [f"clr_{c}" for c in CATS] + LOC
        X = R[cols].to_numpy(float)
        self.mu, self.sd = X.mean(0), np.where(X.std(0) > 0, X.std(0), 1)
        self.w = np.array([1 / np.sqrt(len(CATS))] * len(CATS) + [1 / np.sqrt(len(LOC))] * len(LOC))
        self.cols = cols
        self.pca = PCA(n_components=self.var, svd_solver="full").fit(self._z(R))
        return self

    def _z(self, R):
        return (R[self.cols].to_numpy(float) - self.mu) / self.sd * self.w

    def transform(self, R):
        return self.pca.transform(self._z(R))


def tucker(a, b):
    """Coeficiente de congruencia de Tucker entre dos vectores de cargas."""
    return float(a @ b / np.sqrt((a @ a) * (b @ b)))


def knn_sets(X, k):
    """Índices de los k vecinos más cercanos de cada fila."""
    D = ((X[:, None] - X[None]) ** 2).sum(-1)
    np.fill_diagonal(D, np.inf)
    return np.argsort(D, axis=1)[:, :k]


def main() -> None:
    cfg = load_config()
    seed, hc = cfg["project"]["seed"], cfg["composition"]["zero_replacement_counts"]
    _, conf = selected()
    k = conf["k"]
    src = path("interim") / "replication"
    w = pd.read_parquet(src / "wc2018_wyscout.parquet")
    s = pd.read_parquet(src / "wc2018_statsbomb.parquet")
    L = pd.read_parquet(src / "wc2018_player_link.parquet")
    m = L.merge(w, on="player_id").merge(s, on="sb_player_id", suffixes=("_w", "_s"))
    m = m[(m.role != "GK") & (m.minutes_w >= MIN_MINUTES) & (m.minutes_s >= MIN_MINUTES)].reset_index(
        drop=True
    )
    ok = np.ones(len(m), bool)
    for suf in ("_w", "_s"):
        C = m[[f"cat_{c}{suf}" for c in CATS]].to_numpy(float)
        ok &= (C == 0).sum(1) * hc / np.maximum(C.sum(1), 1) < 1
    m = m[ok].reset_index(drop=True)
    W = represent(m.rename(columns=lambda c: c[:-2] if c.endswith("_w") else c), hc)
    S = represent(m.rename(columns=lambda c: c[:-2] if c.endswith("_s") else c), hc)

    # acuerdo por variable
    var_rows = []
    for c in [f"comp_{x}" for x in CATS] + LOC:
        var_rows.append(
            {
                "variable": c,
                "spearman": spearmanr(W[c], S[c]).statistic,
                "media_wyscout": W[c].mean(),
                "media_statsbomb": S[c].mean(),
            }
        )
    V = pd.DataFrame(var_rows)
    V.to_csv(path("evaluation") / "replication_variables.csv", index=False)

    # congruencia de cargas
    sw, ss = Space().fit(W), Space().fit(S)
    n = min(sw.pca.n_components_, ss.pca.n_components_)
    A, B = sw.pca.components_[:n], ss.pca.components_[:n]
    M = np.array([[abs(tucker(a, b)) for b in B] for a in A])
    r, c = linear_sum_assignment(-M)
    congr = [float(M[i, j]) for i, j in zip(r, c)]

    # concordancia de perfiles
    Xw, Xs = sw.transform(W), ss.transform(S)
    kw = KMeans(k, n_init=10, random_state=seed).fit(Xw)
    ks = KMeans(k, n_init=10, random_state=seed).fit(Xs)
    ari_own = adjusted_rand_score(kw.labels_, ks.labels_)
    Xs_in_w = sw.transform(S)
    ari_proj = adjusted_rand_score(kw.labels_, kw.predict(Xs_in_w))

    # vecinos y identificación cruzada
    kk = 10
    nw, ns = knn_sets(Xw, kk), knn_sets(Xs, kk)
    jac = np.mean([len(set(a) & set(b)) / len(set(a) | set(b)) for a, b in zip(nw, ns)])
    p0 = kk / (len(m) - 1)
    jac_chance = p0 / (2 - p0)
    D = ((Xs_in_w[:, None] - Xw[None]) ** 2).sum(-1)
    rank = (D < np.diag(D)[:, None]).sum(1)

    res = {
        "n_players": len(m),
        "min_minutes": MIN_MINUTES,
        "k": k,
        "spearman_median": float(V.spearman.median()),
        "spearman_min": float(V.spearman.min()),
        "pca_components": {"wyscout": int(sw.pca.n_components_), "statsbomb": int(ss.pca.n_components_)},
        "tucker_congruence": congr,
        "ari_own_clusterings": float(ari_own),
        "ari_statsbomb_projected_on_wyscout_model": float(ari_proj),
        "knn_jaccard_mean": float(jac),
        "knn_jaccard_chance": float(jac_chance),
        "cross_identification_top1": float((rank < 1).mean()),
        "cross_identification_top10": float((rank < 10).mean()),
    }
    (path("evaluation") / "replication.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    print(V.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
