"""Ajuste uniforme de los algoritmos candidatos (protocolo, sección 5) y métricas de una solución."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from sklearn.cluster import HDBSCAN, AgglomerativeClustering, KMeans
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    normalized_mutual_info_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture

from src.models.archetypes import Archetypes

HDBSCAN_SIZES = [10, 20, 30, 50]


def configs(k_range) -> list[dict]:
    """Grilla de configuraciones del protocolo. En HDBSCAN, k es el tamaño mínimo de grupo."""
    out = []
    for k in range(k_range[0], k_range[1] + 1):
        out += [
            {"algorithm": "kmeans", "k": k},
            {"algorithm": "gmm_full", "k": k},
            {"algorithm": "gmm_diag", "k": k},
            {"algorithm": "ward", "k": k},
            {"algorithm": "archetypes", "k": k},
        ]
    out += [{"algorithm": "hdbscan", "k": m} for m in HDBSCAN_SIZES]  # k = tamaño mínimo de grupo
    return out


def fit(cfg: dict, X: np.ndarray, seed: int):
    """Ajusta una configuración y devuelve el modelo y las etiquetas de las observaciones de entrenamiento."""
    a, k = cfg["algorithm"], cfg["k"]
    if a == "kmeans":
        m = KMeans(n_clusters=k, n_init=10, random_state=seed).fit(X)
        return m, m.labels_
    if a.startswith("gmm"):
        m = GaussianMixture(
            n_components=k, covariance_type=a.split("_")[1], n_init=3, random_state=seed, reg_covar=1e-4
        ).fit(X)
        return m, m.predict(X)
    if a == "ward":
        m = AgglomerativeClustering(n_clusters=k, linkage="ward").fit(X)
        return m, m.labels_
    if a == "archetypes":
        m = Archetypes(k, random_state=seed).fit(X)
        return m, m.labels_
    if a == "hdbscan":
        m = HDBSCAN(min_cluster_size=k, min_samples=5).fit(X)
        return m, m.labels_
    raise ValueError(a)


def cramers_v(a, b) -> float:
    """V de Cramér con corrección de sesgo (Bergsma, 2013).

    Sin corrección, con 98 equipos y unos 1.400 jugadores el valor esperado bajo independencia ronda 0,26,
    por encima del umbral de 0,20; la corrección lleva ese valor de referencia a cero (decisión D21).
    """
    t = pd.crosstab(a, b)
    r, k = t.shape
    if min(r, k) < 2:
        return np.nan
    n = t.to_numpy().sum()
    phi2 = chi2_contingency(t, correction=False)[0] / n
    phi2c = max(0.0, phi2 - (k - 1) * (r - 1) / (n - 1))
    rc, kc = r - (r - 1) ** 2 / (n - 1), k - (k - 1) ** 2 / (n - 1)
    return float(np.sqrt(phi2c / min(kc - 1, rc - 1)))


def internal_metrics(X, labels, fine_group, team) -> dict:
    """Separación, tamaño de grupos y asociación con la posición fina y con el equipo."""
    m = labels >= 0  # HDBSCAN marca ruido con -1
    lab = labels[m]
    out = {
        "n_clusters": int(len(np.unique(lab))),
        "noise_share": float(1 - m.mean()),
        "min_cluster_size": int(np.bincount(lab).min()) if len(lab) else 0,
    }
    if out["n_clusters"] >= 2:
        out["silhouette"] = float(silhouette_score(X[m], lab))
        out["davies_bouldin"] = float(davies_bouldin_score(X[m], lab))
        out["calinski_harabasz"] = float(calinski_harabasz_score(X[m], lab))
        out["nmi_fine_group"] = float(normalized_mutual_info_score(fine_group[m], lab))
        out["nmi_team"] = float(normalized_mutual_info_score(team[m], lab))
        out["cramers_v_team"] = cramers_v(lab, team[m])
    return out


def bootstrap_stability(cfg, X, labels, B, seed) -> dict:
    """ARI y Jaccard bootstrap por grupo (Hennig, 2007), remuestreando jugadores con reemplazo."""
    rng = np.random.default_rng(seed)
    n = len(X)
    clusters = [c for c in np.unique(labels) if c >= 0]
    jac = {c: [] for c in clusters}
    aris = []
    for b in range(B):
        idx = rng.integers(0, n, n)
        _, lb = fit(cfg, X[idx], seed + b + 1)
        u, first = np.unique(idx, return_index=True)
        lb_u, lo_u = lb[first], labels[u]
        keep = (lb_u >= 0) & (lo_u >= 0)
        aris.append(adjusted_rand_score(lo_u[keep], lb_u[keep]))
        for c in clusters:
            C = set(u[lo_u == c])
            if not C:
                continue
            best = 0.0
            for d in np.unique(lb_u[lb_u >= 0]):
                D = set(u[lb_u == d])
                best = max(best, len(C & D) / len(C | D))
            jac[c].append(best)
    jm = np.array([np.mean(v) if v else np.nan for v in jac.values()])
    return {
        "ari_mean": float(np.mean(aris)),
        "ari_sd": float(np.std(aris)),
        "jaccard_min": float(np.nanmin(jm)),
        "jaccard_median": float(np.nanmedian(jm)),
        "share_clusters_jaccard_ok": float(np.nanmean(jm >= 0.60)),
        "jaccard_by_cluster": ";".join(f"{c}:{v:.3f}" for c, v in zip(clusters, jm)),
    }
