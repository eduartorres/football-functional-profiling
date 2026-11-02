"""
Análisis de arquetipos (Cutler & Breiman, 1994) por mínimos cuadrados alternados con proyección al simplex.

X ~ A Z,  Z = B X,  con filas de A y de B en el simplex. Cada jugador queda descrito como una mezcla de
k perfiles extremos (arquetipos), que a su vez son combinaciones convexas de jugadores observados.
"""
from __future__ import annotations

import numpy as np


def project_simplex(V: np.ndarray) -> np.ndarray:
    """Proyección euclidiana de cada fila de V al simplex (Duchi et al., 2008)."""
    n, k = V.shape
    U = np.sort(V, axis=1)[:, ::-1]
    css = np.cumsum(U, axis=1) - 1
    idx = np.arange(1, k + 1)
    cond = U - css / idx > 0
    rho = cond.shape[1] - 1 - np.argmax(cond[:, ::-1], axis=1)
    theta = css[np.arange(n), rho] / (rho + 1)
    return np.maximum(V - theta[:, None], 0)


def _solve_weights(X, Z, A, iters):
    # gradiente proyectado para min ||X - A Z||^2 con A en el simplex
    L = np.linalg.norm(Z @ Z.T, 2) + 1e-9
    for _ in range(iters):
        G = (A @ Z - X) @ Z.T
        A = project_simplex(A - G / L)
    return A


class Archetypes:
    def __init__(self, k: int, max_iter: int = 200, tol: float = 1e-5, random_state: int = 0):
        self.k, self.max_iter, self.tol, self.random_state = k, max_iter, tol, random_state

    def fit(self, X: np.ndarray) -> "Archetypes":
        rng = np.random.default_rng(self.random_state)
        n = X.shape[0]
        # inicialización con puntos alejados (furthest-first)
        idx = [int(rng.integers(n))]
        for _ in range(1, self.k):
            d = np.min(((X[:, None, :] - X[idx][None]) ** 2).sum(-1), axis=1)
            idx.append(int(np.argmax(d)))
        B = np.zeros((self.k, n)); B[np.arange(self.k), idx] = 1
        Z = B @ X
        A = project_simplex(rng.random((n, self.k)))
        prev = np.inf
        xx = np.linalg.norm(X, 2) ** 2  # norma espectral de X X^T, constante
        for _ in range(self.max_iter):
            A = _solve_weights(X, Z, A, 10)
            # Z debe minimizar ||X - A Z|| sujeto a Z = B X; se actualiza B por gradiente proyectado
            LB = np.linalg.norm(A.T @ A, 2) * xx + 1e-9
            for _ in range(10):
                G = (A.T @ (A @ (B @ X) - X)) @ X.T
                B = project_simplex(B - G / LB)
            Z = B @ X
            rss = np.sum((X - A @ Z) ** 2)
            if prev - rss < self.tol * prev:
                break
            prev = rss
        self.A_, self.B_, self.archetypes_, self.rss_ = A, B, Z, rss
        self.labels_ = A.argmax(axis=1)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        A = np.full((X.shape[0], self.k), 1 / self.k)
        return _solve_weights(X, self.archetypes_, A, 200)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.transform(X).argmax(axis=1)
