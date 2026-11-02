"""
Evaluación analítica de H4 con casos de reemplazo (protocolo, sección 7).

Casos: jugadores elegibles en ambas mitades de 2017/18 que Transfermarkt registra transferidos entre el
1 de junio y el 31 de agosto de 2018; 30 casos con muestreo estratificado por posición fina (semilla 2026).
Universo de candidatos: jugadores elegibles en ambas mitades, de un equipo distinto al del caso.
Listas (ventana h1): consulta funcional (vecinos en el espacio de la solución seleccionada) y consulta base
(misma posición fina, ordenada por distancia en indicadores por 90 sin ajuste). Tamaño: 20.
Pertinencia analítica (ventana h2): el candidato está dentro del 10 % más cercano al caso en el espacio
descriptivo completo (vol_*, clr_*, loc_* estandarizados con parámetros de h1).

Salida: data/processed/evaluation/replacement_cases.csv y replacement_summary.json
"""
from __future__ import annotations

import json

import duckdb
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

from src.common.config import load_config, path
from src.evaluation.common import baseline_space, selected, transformer, window
from src.models.representation import Transformer

N_CASES = 30
TOP_SHARE = 0.10


def cases(pool: pd.DataFrame, seed: int) -> pd.DataFrame:
    con = duckdb.connect(str(path("transfermarkt_db")), read_only=True)
    t = con.execute("""SELECT player_id tm_id, min(transfer_date) transfer_date, any_value(from_club_name) from_club,
                              any_value(to_club_name) to_club, max(transfer_fee) fee
                       FROM transfers WHERE transfer_date BETWEEN '2018-06-01' AND '2018-08-31'
                         AND to_club_name NOT ILIKE '%retired%' AND to_club_name NOT ILIKE '%without club%'
                       GROUP BY 1""").fetchdf()
    c = pool.merge(t, on="tm_id")
    # muestreo estratificado proporcional por posición fina
    share = c.fine_group.value_counts(normalize=True)
    n_by = (share * N_CASES).round().astype(int).clip(lower=1)
    while n_by.sum() > N_CASES:
        n_by[n_by.idxmax()] -= 1
    parts = [g.sample(min(len(g), n_by[k]), random_state=seed) for k, g in c.groupby("fine_group") if k in n_by]
    return pd.concat(parts).reset_index(drop=True)


def main(space_variant: str = "pca") -> None:
    cfg = load_config()
    seed, L = cfg["project"]["seed"], cfg["hypotheses"]["h4_list_size"]
    rep, _ = selected()
    h1, h2 = window("h1"), window("h2")
    keys = ["player_id", "competition_file"]
    pool1 = h1.merge(h2[keys], on=keys).reset_index(drop=True)
    pool2 = h2.set_index(keys).loc[list(zip(pool1.player_id, pool1.competition_file))].reset_index()
    T = transformer(rep)
    if space_variant == "pca":
        F = T.transform(pool1)
    else:  # sensibilidad: espacio ponderado completo, sin reducción
        F = Transformer(rep, scaler=T.scaler).fit(h1, use_pca=False).transform(pool1)
    Bs = baseline_space(h1).transform(pool1)
    Dsc = Transformer("descriptive", scaler=T.scaler).fit(h1, use_pca=False).transform(pool2)

    cs = cases(pool1, seed)
    rows = []
    for c in cs.itertuples():
        i = int(np.where((pool1.player_id == c.player_id) & (pool1.competition_file == c.competition_file))[0][0])
        cand = (pool1.main_team_id != pool1.main_team_id[i]).to_numpy()
        cand[i] = False
        # pertinencia en h2
        dd = np.linalg.norm(Dsc - Dsc[i], axis=1)
        thr = np.quantile(dd[cand], TOP_SHARE)
        pertinent = cand & (dd <= thr)
        # lista funcional
        df = np.linalg.norm(F - F[i], axis=1); df[~cand] = np.inf
        lf = np.argsort(df)[:L]
        # lista base: misma posición fina
        same = cand & (pool1.fine_group == pool1.fine_group[i]).to_numpy()
        db = np.linalg.norm(Bs - Bs[i], axis=1); db[~same] = np.inf
        lb = [j for j in np.argsort(db)[:L] if np.isfinite(db[j])]
        new = set(lf) - set(lb)
        rows.append({"player_id": c.player_id, "short_name": c.short_name, "fine_group": c.fine_group,
                     "to_club": c.to_club, "list_size_baseline": len(lb),
                     "pertinent_share_functional": float(pertinent[lf].mean()),
                     "pertinent_share_baseline": float(pertinent[lb].mean()) if lb else np.nan,
                     "new_pertinent": int(sum(pertinent[j] for j in new)),
                     "overlap": len(set(lf) & set(lb)),
                     "functional_other_position_share": float((pool1.fine_group.to_numpy()[lf] != c.fine_group).mean())})
    R = pd.DataFrame(rows)
    H = cfg["hypotheses"]
    summ = {"variant": space_variant, "n_cases": len(R), "list_size": L, "pool": len(pool1),
            "pertinent_share_functional_mean": float(R.pertinent_share_functional.mean()),
            "pertinent_share_baseline_mean": float(R.pertinent_share_baseline.mean()),
            "new_pertinent_mean": float(R.new_pertinent.mean()), "new_pertinent_median": float(R.new_pertinent.median()),
            "overlap_mean": float(R.overlap.mean()),
            "functional_other_position_share_mean": float(R.functional_other_position_share.mean()),
            "chance_pertinent_share": TOP_SHARE,
            "wilcoxon_p": float(wilcoxon(R.pertinent_share_functional, R.pertinent_share_baseline).pvalue)}
    summ["rejected"] = bool(summ["pertinent_share_functional_mean"] < summ["pertinent_share_baseline_mean"]
                            or summ["new_pertinent_mean"] < H["h4_min_new_relevant"])
    suffix = "" if space_variant == "pca" else f"_{space_variant}"
    R.to_csv(path("evaluation") / f"replacement_cases{suffix}.csv", index=False)
    (path("evaluation") / f"replacement_summary{suffix}.json").write_text(json.dumps(summ, indent=2))
    print(json.dumps(summ, indent=2))
    print(R.groupby("fine_group")[["pertinent_share_functional", "pertinent_share_baseline", "new_pertinent"]].mean().round(2))


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "pca")
