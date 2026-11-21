"""
Caso de reemplazo que se narra en el pitch: João Moutinho, vendido por el Mónaco en el verano de 2018.

Reconstruye las dos listas de 20 candidatos del caso con la misma lógica de la evaluación de H4
(src/evaluation/replacement_cases.py) y les agrega el último valor de mercado de Transfermarkt anterior
a la venta. También resume los movimientos de mediocampistas del club vendedor ese verano.
Es material de apoyo del pitch: no interviene en los perfiles ni en la evaluación.

Salida: reports/pitch/caso_pitch.json
"""

from __future__ import annotations

import json

import duckdb
import numpy as np
import pandas as pd

from src.config import ROOT, load_config, path
from src.evaluation.common import baseline_space, selected, transformer, window
from src.evaluation.replacement_cases import cases, lists_for
from src.models.representation import Transformer

CASE = "João Moutinho"
OUT = ROOT / "reports" / "pitch" / "caso_pitch.json"


def main() -> None:
    cfg = load_config()
    seed, L = cfg["project"]["seed"], cfg["hypotheses"]["h4_list_size"]
    rep, _ = selected()
    h1, h2 = window("h1"), window("h2")
    keys = ["player_id", "competition_file"]
    pool1 = h1.merge(h2[keys], on=keys).reset_index(drop=True)
    pool2 = h2.set_index(keys).loc[list(zip(pool1.player_id, pool1.competition_file))].reset_index()
    T = transformer(rep)
    F = T.transform(pool1)
    Bs = baseline_space(h1).transform(pool1)
    Dsc = Transformer("descriptive", scaler=T.scaler).fit(h1, use_pca=False).transform(pool2)

    c = cases(pool1, seed).query("short_name == @CASE").iloc[0]
    here = (pool1.player_id == c.player_id) & (pool1.competition_file == c.competition_file)
    i = int(np.where(here)[0][0])
    lf, lb, pertinent = lists_for(i, pool1, F, Bs, Dsc, L)

    con = duckdb.connect(str(path("transfermarkt_db")), read_only=True)
    sale = (
        con.execute(
            "SELECT transfer_date, from_club_id, from_club_name, to_club_name, transfer_fee FROM transfers "
            "WHERE player_id = ? AND transfer_date BETWEEN '2018-06-01' AND '2018-08-31'",
            [int(c.tm_id)],
        )
        .fetchdf()
        .iloc[0]
    )
    date = str(sale.transfer_date)[:10]
    # último valor de mercado conocido antes de la venta
    value = (
        con.execute(
            "SELECT player_id, market_value_in_eur FROM (SELECT *, row_number() OVER "
            "(PARTITION BY player_id ORDER BY date DESC) r FROM player_valuations WHERE date <= ?) "
            "WHERE r = 1",
            [date],
        )
        .fetchdf()
        .set_index("player_id")
        .market_value_in_eur
    )
    teams = pd.read_parquet(ROOT / "data" / "interim" / "wyscout" / "teams.parquet")
    teams = teams.set_index("team_id").team_name

    def player(j: int) -> dict:
        v = value.get(int(pool1.tm_id[j]))
        return {
            "name": pool1.short_name[j],
            "club": teams.get(pool1.main_team_id[j]),
            "position": pool1.fine_group[j],
            "pertinent": bool(pertinent[j]),
            "value_m_eur": None if v is None or pd.isna(v) else round(float(v) / 1e6, 2),
        }

    common = [player(j) for j in lf if j in lb]
    only_functional = [player(j) for j in lf if j not in lb]
    new_pertinent = [p for p in only_functional if p["pertinent"]]
    vals = [p["value_m_eur"] for p in new_pertinent if p["value_m_eur"] is not None]
    base_vals = [player(j)["value_m_eur"] for j in lb if player(j)["value_m_eur"] is not None]

    # movimientos de mediocampistas del club vendedor en el mismo verano, con monto pagado
    moves = con.execute(
        "SELECT t.player_name, t.from_club_name, t.to_club_name, t.transfer_fee, p.sub_position "
        "FROM transfers t JOIN players p USING (player_id) "
        "WHERE (t.from_club_id = ? OR t.to_club_id = ?) "
        "AND t.transfer_date BETWEEN '2018-06-01' AND '2018-08-31' "
        "AND p.position = 'Midfield' AND t.transfer_fee > 0 ORDER BY t.transfer_fee DESC",
        [int(sale.from_club_id), int(sale.from_club_id)],
    ).fetchdf()
    club = sale.from_club_name
    out = {
        "case": {
            "name": CASE,
            "from_club": club,
            "to_club": sale.to_club_name,
            "date": date,
            "fee_m_eur": round(float(sale.transfer_fee) / 1e6, 2),
            "value_m_eur": round(float(value.get(int(c.tm_id))) / 1e6, 2),
        },
        "list_size": L,
        "pertinent_functional": int(pertinent[lf].sum()),
        "pertinent_baseline": int(pertinent[lb].sum()),
        "common": common,
        "new_pertinent": sorted(new_pertinent, key=lambda p: -(p["value_m_eur"] or 0)),
        "new_pertinent_median_value_m_eur": float(np.median(vals)),
        "new_pertinent_at_or_below_median": int(sum(v <= np.median(vals) for v in vals)),
        "baseline_median_value_m_eur": float(np.median(base_vals)),
        "club_midfield_moves": [
            {
                "player": r.player_name,
                "direction": "salida" if r.from_club_name == club else "llegada",
                "other_club": r.to_club_name if r.from_club_name == club else r.from_club_name,
                "fee_m_eur": round(float(r.transfer_fee) / 1e6, 2),
                "sub_position": r.sub_position,
            }
            for r in moves.itertuples()
        ],
        "source": "transfermarkt-datasets (snapshot del 6 de julio de 2026): transfers y player_valuations",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("reports/pitch/caso_pitch.json")


if __name__ == "__main__":
    main()
