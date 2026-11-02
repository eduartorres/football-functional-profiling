"""
Datos del explorador de jugadores (prototipo del capítulo 8).

Para los 1.500 jugadores-temporada elegibles de 2017/18: ficha, perfil final (temporada completa, D24),
percentiles de indicadores, composición de acciones, coordenadas en el plano de los dos primeros componentes
y los 30 jugadores más similares de otros clubes en el espacio ponderado completo de composición (D27).

Salida: reports/explorer/explorer_data.json
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.common.config import ROOT, path
from src.evaluation.common import selected, window
from src.features.player_match import fix_escapes
from src.models.representation import Transformer

PROFILE_NAMES = {1: "Construcción y defensa posicional", 2: "Carril lateral", 3: "Ataque y finalización"}
POSITION_NAMES = {
    "defensa_central": "Defensa central",
    "lateral": "Lateral",
    "pivote": "Pivote",
    "mediocentro": "Mediocentro",
    "mediapunta": "Mediapunta",
    "volante_banda": "Volante de banda",
    "extremo": "Extremo",
    "segundo_delantero": "Segundo delantero",
    "delantero_centro": "Delantero centro",
}
LEAGUES = {
    "England": "Premier League",
    "France": "Ligue 1",
    "Germany": "Bundesliga",
    "Italy": "Serie A",
    "Spain": "La Liga",
}
# indicadores mostrados con percentil, agrupados por dimensión
INDICATORS = [
    ("Distribución", "p90_passes", "Pases por 90"),
    ("Distribución", "vol_precision_pase", "Precisión de pase"),
    ("Progresión", "p90_prog_passes", "Pases progresivos por 90"),
    ("Progresión", "p90_carries", "Conducciones por 90"),
    ("Progresión", "p90_dribbles_won", "Regates ganados por 90"),
    ("Creación", "p90_key_passes", "Pases clave por 90"),
    ("Creación", "p90_crosses", "Centros por 90"),
    ("Finalización", "p90_shots", "Remates por 90"),
    ("Finalización", "p90_box_actions", "Acciones en el área por 90"),
    ("Recuperación", "p90_interceptions", "Intercepciones por 90"),
    ("Recuperación", "p90_def_duels", "Duelos defensivos por 90"),
    ("Recuperación", "p90_air_duels", "Duelos aéreos por 90"),
    ("Localización", "loc_depth", "Profundidad media"),
    ("Localización", "loc_width", "Distancia al eje central"),
]
COMP = [
    "pase_simple",
    "pase_largo",
    "pase_cabeza",
    "pase_filtrado",
    "centro",
    "remate",
    "conduccion",
    "toque",
    "despeje",
    "duelo_ofensivo",
    "duelo_defensivo",
    "duelo_aereo",
    "balon_dividido",
]
K = 30  # el explorador muestra 10 tras aplicar filtros


def main() -> None:
    rep, _ = selected()
    d = window("full")
    prof = pd.read_parquet(path("models") / "profiles_full_assignments.parquet")[
        ["player_id", "competition_file", "profile"]
    ]
    d = d.merge(prof, on=["player_id", "competition_file"], how="left").reset_index(drop=True)
    teams = {
        t["wyId"]: fix_escapes(t["name"])
        for t in json.loads(next((ROOT / "data/raw/wyscout").glob("teams__*/teams.json")).read_text())
    }

    Tfull = Transformer(rep).fit(d, use_pca=False)  # consulta de similitud (D27)
    Z = Tfull.weighted(d)
    Tmap = Transformer(rep).fit(d)  # plano de visualización (PCA)
    P = Tmap.transform(d)[:, :2]

    D = np.sqrt(((Z[:, None, :] - Z[None, :, :]) ** 2).sum(-1))
    same_team = d.main_team_id.to_numpy()[:, None] == d.main_team_id.to_numpy()[None, :]
    D[same_team] = np.inf
    scale = np.median(D[np.isfinite(D)])
    pct = {c: (d[c].rank(pct=True) * 100).round().astype(int) for _, c, _ in INDICATORS}

    players = []
    for i, r in d.iterrows():
        nn = np.argsort(D[i])[:K]
        players.append(
            {
                "id": int(i),
                "name": r.short_name,
                "league": LEAGUES[r.competition_file],
                "team": teams.get(int(r.main_team_id), str(r.main_team_id)),
                "minutes": int(round(r.minutes)),
                "matches": int(r.matches),
                "position": POSITION_NAMES[r.fine_group],
                "profile": int(r.profile),
                "x": round(float(P[i, 0]), 3),
                "y": round(float(P[i, 1]), 3),
                "pct": [int(pct[c][i]) for _, c, _ in INDICATORS],
                "val": [round(float(r[c]), 2) for _, c, _ in INDICATORS],
                "comp": [round(float(r[f"comp_{c}"]), 4) for c in COMP],
                "sim": [[int(j), round(float(np.exp(-D[i, j] / scale)) * 100)] for j in nn],
            }
        )
    out = {
        "profiles": PROFILE_NAMES,
        "indicators": [[group, label] for group, _, label in INDICATORS],
        "composition": COMP,
        "players": players,
        "meta": {
            "n": len(players),
            "season": "2017/18",
            "source": "Wyscout (Pappalardo et al., 2019)",
            "similarity": "espacio ponderado completo de composición y localización; candidatos de otros clubes",
            "min_minutes": 900,
        },
    }
    f = ROOT / "reports" / "explorer" / "explorer_data.json"
    f.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f.relative_to(ROOT), f"{f.stat().st_size / 1e3:.0f} KB", len(players))


if __name__ == "__main__":
    main()
