"""
Grilla de modelos y selección según el protocolo (docs/protocolo_modelado.md, sección 5).

Etapas (reanudables; cada ejecución avanza hasta agotar su presupuesto de tiempo):
  screen  : todas las configuraciones en desarrollo (h1) con bootstrap reducido (modeling.screening_reps)
  confirm : candidatas que pasan el filtro de estabilidad y confusión, con bootstrap completo (modeling.bootstrap_reps)
  select  : aplica la regla de selección y guarda la solución elegida

Uso:
  python -m src.models.select_model --stage screen  [--budget 150]
  python -m src.models.select_model --stage confirm [--budget 150]
  python -m src.models.select_model --stage select

Salidas en data/processed/models/: transformer_<rep>.pkl, loadings_<rep>.csv, grid_screen.csv,
grid_confirm.csv, selected_model.json
"""
from __future__ import annotations

import argparse
import json
import pickle
import time

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from src.common.config import load_config, path
from src.models import clustering as cl
from src.models.representation import Transformer

REPS = ["volume", "composition"]


def development_data() -> pd.DataFrame:
    d = pd.read_parquet(path("features") / "player_features_h1.parquet")
    return d[d.eligible].reset_index(drop=True)


def get_space(rep: str, d: pd.DataFrame):
    cfg = load_config()["modeling"]
    out = path("models")
    f = out / f"transformer_{rep}.pkl"
    if f.exists():
        T = pickle.loads(f.read_bytes())
    else:
        T = Transformer(rep, scaler=cfg["scaler"], variance=cfg["pca_variance_retained"]).fit(d)
        f.write_bytes(pickle.dumps(T))
        T.loadings().to_csv(out / f"loadings_{rep}.csv")
    return T.transform(d)


def evaluate(rep, conf, X, fg, tm, B, seed):
    _, labels = cl.fit(conf, X, seed)
    row = {"representation": rep, **conf, **cl.internal_metrics(X, labels, fg, tm)}
    if row["n_clusters"] >= 2:
        row.update(cl.bootstrap_stability(conf, X, labels, B, seed))
    return row


def passes_filter(r: pd.Series, h: dict) -> bool:
    return (r.ari_mean >= h["h3_min_mean_ari"] and r.share_clusters_jaccard_ok > 0.5
            and r.nmi_team < h["max_nmi_team"] and r.cramers_v_team < h["max_nmi_team"]
            and r.noise_share <= load_config()["modeling"]["max_noise_share"])


def run(stage: str, budget: float) -> None:
    cfg = load_config()
    seed, m = cfg["project"]["seed"], cfg["modeling"]
    d = development_data()
    fg, tm = d.fine_group.to_numpy(), d.main_team_id.to_numpy()
    spaces = {rep: get_space(rep, d) for rep in REPS}
    out = path("models") / f"grid_{stage}.csv"
    done = pd.read_csv(out) if out.exists() else pd.DataFrame(columns=["representation", "algorithm", "k"])
    key = set(zip(done.representation, done.algorithm, done.k))
    if stage == "screen":
        todo = [(rep, c) for rep in REPS for c in cl.configs(m["k_range"])]
        B = m["screening_reps"]
    else:
        s = pd.read_csv(path("models") / "grid_screen.csv")
        cand = s[s.apply(passes_filter, axis=1, h=cfg["hypotheses"])]
        todo = [(r.representation, {"algorithm": r.algorithm, "k": int(r.k)}) for r in cand.itertuples()]
        B = m["bootstrap_reps"]
    todo = [(r, c) for r, c in todo if (r, c["algorithm"], c["k"]) not in key]
    print(f"{stage}: pendientes {len(todo)}")
    t0 = time.time()
    while todo and time.time() - t0 < budget:
        batch, todo = todo[:4], todo[4:]
        rows = Parallel(n_jobs=4)(delayed(evaluate)(r, c, spaces[r], fg, tm, B, seed) for r, c in batch)
        new = pd.DataFrame(rows)
        new.to_csv(out, mode="a", header=not out.exists(), index=False)
        for r in rows:
            print(f"  {r['representation']:11s} {r['algorithm']:10s} k={r['k']:<3} ARI={r.get('ari_mean', np.nan):.3f} "
                  f"sil={r.get('silhouette', np.nan):.3f} NMIpos={r.get('nmi_fine_group', np.nan):.3f}")
    print(f"{stage}: quedan {len(todo)}")


def select() -> None:
    cfg = load_config()
    c = pd.read_csv(path("models") / "grid_confirm.csv")
    ok = c[c.apply(passes_filter, axis=1, h=cfg["hypotheses"])].copy()
    result = {"n_confirmed": len(c), "n_passing": len(ok)}
    if ok.empty:
        result["decision"] = "sin grupos estables: se conserva la representación continua (protocolo, sección 5)"
    else:
        best = ok.sort_values(["silhouette", "davies_bouldin"], ascending=[False, True]).iloc[0]
        result.update({"decision": "solución seleccionada", **{k: (v.item() if hasattr(v, "item") else v)
                                                               for k, v in best.to_dict().items()}})
    (path("models") / "selected_model.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["screen", "confirm", "select"], required=True)
    ap.add_argument("--budget", type=float, default=150)
    a = ap.parse_args()
    select() if a.stage == "select" else run(a.stage, a.budget)
