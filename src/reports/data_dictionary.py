"""
Genera el diccionario de datos de las tablas derivadas (anexo A del documento).

Para cada tabla: ruta, número de filas, y por columna su tipo, porcentaje de faltantes, rango y descripción.
Las descripciones provienen de DESCRIPTIONS; una columna sin descripción queda marcada para documentarla.

Salida: docs/diccionario_datos.md
"""

from __future__ import annotations

import pandas as pd

from src.common.config import ROOT, load_config

TABLES = {
    "data/interim/wyscout/player_match.parquet": "Una fila por jugador y partido (Wyscout, todas las competiciones).",
    "data/interim/wyscout/team_match.parquet": "Una fila por equipo y partido con la posesión aproximada.",
    "data/processed/features/position_reference.parquet": "Enlace Wyscout-Transfermarkt y posición fina de referencia (cinco ligas 2017/18).",
    "data/processed/features/player_features_full.parquet": "Representaciones por jugador y competición, temporada completa. Las tablas _h1 y _h2 tienen las mismas columnas por mitad de temporada.",
}

DESCRIPTIONS = {
    "match_id": "Identificador de partido de Wyscout",
    "player_id": "Identificador de jugador de Wyscout",
    "team_id": "Identificador de equipo de Wyscout",
    "competition_file": "Competición según el archivo de origen",
    "season_id": "Identificador de temporada de Wyscout",
    "gameweek": "Jornada del partido",
    "date_utc": "Fecha y hora del partido (UTC)",
    "started": "Titular en el partido",
    "minute_in": "Minuto de ingreso reconstruido",
    "minute_out": "Minuto de salida reconstruido",
    "minutes": "Minutos jugados reconstruidos",
    "match_minutes": "Duración del partido según el último evento de cada periodo",
    "n_actions": "Eventos del jugador",
    "passes": "Pases",
    "passes_accurate": "Pases con etiqueta 1801 (preciso)",
    "prog_passes": "Pases precisos con avance de al menos 20 unidades en x",
    "final_third_entries": "Pases precisos de x < 66,7 a x >= 66,7",
    "key_passes": "Pases con etiqueta 302 (pase clave)",
    "crosses": "Centros (subevento Cross)",
    "carries": "Conducciones (subevento Acceleration)",
    "shots": "Remates",
    "box_actions": "Acciones iniciadas con x >= 84 e y entre 19 y 81",
    "duels": "Duelos",
    "duels_won": "Duelos ganados (etiqueta 703)",
    "air_duels": "Duelos aéreos",
    "interceptions": "Eventos con etiqueta 1401 (intercepción)",
    "def_duels": "Duelos defensivos en el suelo",
    "dribbles_won": "Duelos ofensivos en el suelo ganados",
    "clearances": "Despejes",
    "n_loc": "Eventos con coordenada inicial",
    "sum_x": "Suma de x inicial",
    "sum_x2": "Suma de x inicial al cuadrado",
    "sum_absy": "Suma de |y - 50|",
    "sum_y": "Suma de y inicial",
    "sum_y2": "Suma de y inicial al cuadrado",
    "possession_share": "Proporción de pases del equipo en el partido",
    "passes_team": "Pases del equipo",
    "half": "Mitad de temporada (h1, h2) o full en torneos",
    "role": "Rol de Wyscout (GK, DF, MD, FW)",
    "own_min": "Minutos ponderados por la posesión propia",
    "opp_min": "Minutos ponderados por la posesión rival",
    "matches": "Partidos jugados",
    "starts": "Partidos como titular",
    "n_teams": "Equipos en la ventana",
    "team_possession_mean": "Posesión media del equipo ponderada por minutos",
    "main_team_id": "Equipo con más minutos en la ventana",
    "loc_depth": "Profundidad media de las acciones (x, 0 a 100)",
    "loc_width": "Distancia media al eje central (|y - 50|)",
    "loc_sd_x": "Desviación estándar de x",
    "loc_sd_y": "Desviación estándar de y",
    "n_open_play_actions": "Acciones de juego abierto usadas en la composición",
    "short_name": "Nombre corto (decodificado)",
    "birth_date": "Fecha de nacimiento",
    "tm_id": "Identificador de jugador en Transfermarkt",
    "linked": "Enlace aceptado con Transfermarkt",
    "fine_position": "Posición fina: principal por minutos en 2017/18 (alineaciones de Transfermarkt)",
    "fine_group": "Posición fina agrupada sin lado (referencia externa)",
    "position_source": "Origen de la posición fina",
    "main_share": "Proporción de minutos en la posición principal",
    "is_core": "Pertenece a las cinco ligas del núcleo",
    "eligible": "Pertenece a la población elegible de la ventana",
    "window": "Ventana temporal",
    "tm_name": "Nombre en Transfermarkt",
    "tm_sub_position": "Sub-posición del registro de Transfermarkt (snapshot 2026)",
    "n_dob_candidates": "Candidatos en Transfermarkt con la misma fecha de nacimiento",
    "name_score": "Similitud de nombre",
    "tm_main_position": "Posición principal en Transfermarkt",
    "n_positions": "Posiciones distintas en 2017/18",
    "tm_minutes": "Minutos en Transfermarkt 2017/18",
}
PREFIX = {
    "cat_": "Conteo de acciones de juego abierto de la categoría",
    "p90_": "Tasa por 90 minutos sin ajuste de",
    "vol_": "Tasa por 90 minutos ajustada a 50 % de posesión de",
    "comp_": "Proporción de la categoría sobre las acciones de juego abierto:",
    "clr_": "Log-ratio centrado de la proporción de la categoría",
}


def describe(col: str) -> str:
    if col in DESCRIPTIONS:
        return DESCRIPTIONS[col]
    for p, txt in PREFIX.items():
        if col.startswith(p):
            base = col[len(p) :]
            return f"{txt} {DESCRIPTIONS.get(base, base).lower() if base in DESCRIPTIONS else base}"
    return "PENDIENTE DE DOCUMENTAR"


def main() -> None:
    cfg = load_config()
    lines = [
        "# Diccionario de datos",
        "",
        "Generado por `src/reports/data_dictionary.py`. No editar a mano.",
        "",
        "Categorías de composición (juego abierto):",
        "",
    ]
    for k, v in cfg["composition"]["categories"].items():
        lines.append(f"- `{k}`: {', '.join(v)}")
    for rel, desc in TABLES.items():
        df = pd.read_parquet(ROOT / rel)
        lines += [
            "",
            f"## `{rel}`",
            "",
            desc,
            "",
            f"Filas: {len(df):,}",
            "",
            "| Columna | Tipo | % faltante | Rango | Descripción |",
            "|---|---|---|---|---|",
        ]
        for c in df.columns:
            s = df[c]
            rng = ""
            if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s) and s.notna().any():
                rng = f"{s.min():.4g} a {s.max():.4g}"
            lines.append(f"| `{c}` | {s.dtype} | {s.isna().mean() * 100:.1f} | {rng} | {describe(c)} |")
    out = ROOT / "docs" / "diccionario_datos.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    pending = sum("PENDIENTE" in line for line in lines)
    print(f"{out.relative_to(ROOT)} | columnas sin descripción: {pending}")


if __name__ == "__main__":
    main()
