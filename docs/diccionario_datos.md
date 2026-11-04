# Diccionario de datos

Generado por `src/reports/data_dictionary.py`. No editar a mano.

Categorías de composición (juego abierto):

- `pase_simple`: Simple pass
- `pase_largo`: High pass, Launch
- `pase_cabeza`: Head pass
- `pase_filtrado`: Smart pass
- `centro`: Cross
- `remate`: Shot
- `conduccion`: Acceleration
- `toque`: Touch
- `despeje`: Clearance
- `duelo_ofensivo`: Ground attacking duel
- `duelo_defensivo`: Ground defending duel
- `duelo_aereo`: Air duel
- `balon_dividido`: Ground loose ball duel

## `data/interim/wyscout/player_match.parquet`

Una fila por jugador y partido (Wyscout, todas las competiciones).

Filas: 53,791

| Columna | Tipo | % faltante | Rango | Descripción |
|---|---|---|---|---|
| `match_id` | int64 | 0.0 | 1.694e+06 a 2.576e+06 | Identificador de partido de Wyscout |
| `competition_file` | object | 0.0 |  | Competición según el archivo de origen |
| `season_id` | int64 | 0.0 | 9291 a 1.812e+05 | Identificador de temporada de Wyscout |
| `gameweek` | int64 | 0.0 | 0 a 38 | Jornada del partido |
| `date_utc` | object | 0.0 |  | Fecha y hora del partido (UTC) |
| `team_id` | int64 | 0.0 | 674 a 1.983e+04 | Identificador de equipo de Wyscout |
| `player_id` | int64 | 0.0 | 12 a 5.686e+05 | Identificador de jugador de Wyscout |
| `started` | bool | 0.0 |  | Titular en el partido |
| `minute_in` | float64 | 0.0 | 0 a 120 | Minuto de ingreso reconstruido |
| `minute_out` | float64 | 0.0 | 3 a 133.3 | Minuto de salida reconstruido |
| `minutes` | float64 | 0.0 | 0 a 133.3 | Minutos jugados reconstruidos |
| `match_minutes` | float64 | 0.0 | 87.88 a 133.3 | Duración del partido según el último evento de cada periodo |
| `n_actions` | int64 | 0.0 | 0 a 225 | Eventos del jugador |
| `passes` | int64 | 0.0 | 0 a 174 | Pases |
| `passes_accurate` | int64 | 0.0 | 0 a 165 | Pases con etiqueta 1801 (preciso) |
| `prog_passes` | int64 | 0.0 | 0 a 30 | Pases precisos con avance de al menos 20 unidades en x |
| `final_third_entries` | int64 | 0.0 | 0 a 55 | Pases precisos de x < 66,7 a x >= 66,7 |
| `key_passes` | int64 | 0.0 | 0 a 7 | Pases con etiqueta 302 (pase clave) |
| `crosses` | int64 | 0.0 | 0 a 21 | Centros (subevento Cross) |
| `carries` | int64 | 0.0 | 0 a 12 | Conducciones (subevento Acceleration) |
| `shots` | int64 | 0.0 | 0 a 13 | Remates |
| `box_actions` | int64 | 0.0 | 0 a 37 | Acciones iniciadas con x >= 84 e y entre 19 y 81 |
| `duels` | int64 | 0.0 | 0 a 69 | Duelos |
| `duels_won` | int64 | 0.0 | 0 a 34 | Duelos ganados (etiqueta 703) |
| `air_duels` | int64 | 0.0 | 0 a 34 | Duelos aéreos |
| `interceptions` | int64 | 0.0 | 0 a 21 | Eventos con etiqueta 1401 (intercepción) |
| `def_duels` | int64 | 0.0 | 0 a 29 | Duelos defensivos en el suelo |
| `dribbles_won` | int64 | 0.0 | 0 a 32 | Duelos ofensivos en el suelo ganados |
| `clearances` | int64 | 0.0 | 0 a 16 | Despejes |
| `n_loc` | int64 | 0.0 | 0 a 225 | Eventos con coordenada inicial |
| `sum_x` | int64 | 0.0 | 0 a 1.522e+04 | Suma de x inicial |
| `sum_x2` | int64 | 0.0 | 0 a 1.088e+06 | Suma de x inicial al cuadrado |
| `sum_absy` | int64 | 0.0 | 0 a 7730 | Suma de |y - 50| |
| `sum_y` | int64 | 0.0 | 0 a 1.524e+04 | Suma de y inicial |
| `sum_y2` | int64 | 0.0 | 0 a 1.388e+06 | Suma de y inicial al cuadrado |
| `cat_pase_simple` | int64 | 0.0 | 0 a 163 | Conteo de acciones de juego abierto de la categoría pase_simple |
| `cat_pase_largo` | int64 | 0.0 | 0 a 33 | Conteo de acciones de juego abierto de la categoría pase_largo |
| `cat_pase_cabeza` | int64 | 0.0 | 0 a 18 | Conteo de acciones de juego abierto de la categoría pase_cabeza |
| `cat_pase_filtrado` | int64 | 0.0 | 0 a 13 | Conteo de acciones de juego abierto de la categoría pase_filtrado |
| `cat_centro` | int64 | 0.0 | 0 a 21 | Conteo de acciones de juego abierto de la categoría centro |
| `cat_remate` | int64 | 0.0 | 0 a 13 | Conteo de acciones de juego abierto de la categoría remate |
| `cat_conduccion` | int64 | 0.0 | 0 a 12 | Conteo de acciones de juego abierto de la categoría conduccion |
| `cat_toque` | int64 | 0.0 | 0 a 28 | Conteo de acciones de juego abierto de la categoría toque |
| `cat_despeje` | int64 | 0.0 | 0 a 16 | Conteo de acciones de juego abierto de la categoría despeje |
| `cat_duelo_ofensivo` | int64 | 0.0 | 0 a 42 | Conteo de acciones de juego abierto de la categoría duelo_ofensivo |
| `cat_duelo_defensivo` | int64 | 0.0 | 0 a 29 | Conteo de acciones de juego abierto de la categoría duelo_defensivo |
| `cat_duelo_aereo` | int64 | 0.0 | 0 a 34 | Conteo de acciones de juego abierto de la categoría duelo_aereo |
| `cat_balon_dividido` | int64 | 0.0 | 0 a 23 | Conteo de acciones de juego abierto de la categoría balon_dividido |
| `possession_share` | float64 | 0.0 | 0.152 a 0.848 | Proporción de pases del equipo en el partido |
| `half` | object | 0.0 |  | Mitad de temporada (h1, h2) o full en torneos |
| `role` | object | 0.0 |  | Rol de Wyscout (GK, DF, MD, FW) |

## `data/interim/wyscout/team_match.parquet`

Una fila por equipo y partido con la posesión aproximada.

Filas: 3,882

| Columna | Tipo | % faltante | Rango | Descripción |
|---|---|---|---|---|
| `match_id` | int64 | 0.0 | 1.694e+06 a 2.576e+06 | Identificador de partido de Wyscout |
| `team_id` | int64 | 0.0 | 674 a 1.983e+04 | Identificador de equipo de Wyscout |
| `passes` | int64 | 0.0 | 121 a 1078 | Pases |
| `possession_share` | float64 | 0.0 | 0.152 a 0.848 | Proporción de pases del equipo en el partido |

## `data/interim/wyscout/teams.parquet`

Una fila por equipo de Wyscout con su nombre decodificado.

Filas: 142

| Columna | Tipo | % faltante | Rango | Descripción |
|---|---|---|---|---|
| `team_id` | int64 | 0.0 | 674 a 1.983e+04 | Identificador de equipo de Wyscout |
| `team_name` | object | 0.0 |  | Nombre del equipo en Wyscout |
| `area` | object | 0.0 |  | País o región del equipo |
| `team_type` | object | 0.0 |  | Tipo de equipo (club o selección) |

## `data/processed/features/position_reference.parquet`

Enlace Wyscout-Transfermarkt y posición fina de referencia (cinco ligas 2017/18).

Filas: 2,570

| Columna | Tipo | % faltante | Rango | Descripción |
|---|---|---|---|---|
| `player_id` | int64 | 0.0 | 33 a 5.686e+05 | Identificador de jugador de Wyscout |
| `tm_id` | float64 | 0.2 | 26 a 7.244e+05 | Identificador de jugador en Transfermarkt |
| `tm_name` | object | 0.2 |  | Nombre en Transfermarkt |
| `tm_sub_position` | object | 0.2 |  | Sub-posición del registro de Transfermarkt (snapshot 2026) |
| `n_dob_candidates` | int64 | 0.0 | 0 a 25 | Candidatos en Transfermarkt con la misma fecha de nacimiento |
| `name_score` | float64 | 0.0 | 0 a 1 | Similitud de nombre |
| `linked` | bool | 0.0 |  | Enlace aceptado con Transfermarkt |
| `tm_main_position` | object | 3.0 |  | Posición principal en Transfermarkt |
| `main_share` | float64 | 3.3 | 0.2132 a 1 | Proporción de minutos en la posición principal |
| `n_positions` | float64 | 3.3 | 1 a 8 | Posiciones distintas en 2017/18 |
| `tm_minutes` | float64 | 3.3 | 1 a 3420 | Minutos en Transfermarkt 2017/18 |
| `position_source` | object | 0.0 |  | Origen de la posición fina |
| `fine_position` | object | 3.0 |  | Posición fina: principal por minutos en 2017/18 (alineaciones de Transfermarkt) |
| `fine_group` | object | 10.7 |  | Posición fina agrupada sin lado (referencia externa) |
| `short_name` | object | 0.0 |  | Nombre corto (decodificado) |
| `role` | object | 0.0 |  | Rol de Wyscout (GK, DF, MD, FW) |

## `data/processed/features/player_features_full.parquet`

Representaciones por jugador y competición, temporada completa. Las tablas _h1 y _h2 tienen las mismas columnas por mitad de temporada.

Filas: 3,676

| Columna | Tipo | % faltante | Rango | Descripción |
|---|---|---|---|---|
| `player_id` | int64 | 0.0 | 12 a 5.686e+05 | Identificador de jugador de Wyscout |
| `competition_file` | object | 0.0 |  | Competición según el archivo de origen |
| `minutes` | float64 | 0.0 | 1.937 a 3683 | Minutos jugados reconstruidos |
| `own_min` | float64 | 0.0 | 0.8869 a 2506 | Minutos ponderados por la posesión propia |
| `opp_min` | float64 | 0.0 | 0.8404 a 2201 | Minutos ponderados por la posesión rival |
| `n_actions` | int64 | 0.0 | 0 a 4060 | Eventos del jugador |
| `passes_accurate` | int64 | 0.0 | 0 a 2805 | Pases con etiqueta 1801 (preciso) |
| `duels` | int64 | 0.0 | 0 a 1349 | Duelos |
| `duels_won` | int64 | 0.0 | 0 a 539 | Duelos ganados (etiqueta 703) |
| `n_loc` | int64 | 0.0 | 0 a 4060 | Eventos con coordenada inicial |
| `sum_x` | int64 | 0.0 | 0 a 2.461e+05 | Suma de x inicial |
| `sum_x2` | int64 | 0.0 | 0 a 1.673e+07 | Suma de x inicial al cuadrado |
| `sum_absy` | int64 | 0.0 | 0 a 1.385e+05 | Suma de |y - 50| |
| `sum_y` | int64 | 0.0 | 0 a 2.866e+05 | Suma de y inicial |
| `sum_y2` | int64 | 0.0 | 0 a 2.473e+07 | Suma de y inicial al cuadrado |
| `passes` | int64 | 0.0 | 0 a 3118 | Pases |
| `prog_passes` | int64 | 0.0 | 0 a 403 | Pases precisos con avance de al menos 20 unidades en x |
| `final_third_entries` | int64 | 0.0 | 0 a 573 | Pases precisos de x < 66,7 a x >= 66,7 |
| `key_passes` | int64 | 0.0 | 0 a 36 | Pases con etiqueta 302 (pase clave) |
| `crosses` | int64 | 0.0 | 0 a 249 | Centros (subevento Cross) |
| `carries` | int64 | 0.0 | 0 a 104 | Conducciones (subevento Acceleration) |
| `shots` | int64 | 0.0 | 0 a 167 | Remates |
| `box_actions` | int64 | 0.0 | 0 a 428 | Acciones iniciadas con x >= 84 e y entre 19 y 81 |
| `dribbles_won` | int64 | 0.0 | 0 a 479 | Duelos ofensivos en el suelo ganados |
| `interceptions` | int64 | 0.0 | 0 a 306 | Eventos con etiqueta 1401 (intercepción) |
| `def_duels` | int64 | 0.0 | 0 a 433 | Duelos defensivos en el suelo |
| `clearances` | int64 | 0.0 | 0 a 171 | Despejes |
| `air_duels` | int64 | 0.0 | 0 a 497 | Duelos aéreos |
| `cat_pase_simple` | int64 | 0.0 | 0 a 2786 | Conteo de acciones de juego abierto de la categoría pase_simple |
| `cat_pase_largo` | int64 | 0.0 | 0 a 514 | Conteo de acciones de juego abierto de la categoría pase_largo |
| `cat_pase_cabeza` | int64 | 0.0 | 0 a 235 | Conteo de acciones de juego abierto de la categoría pase_cabeza |
| `cat_pase_filtrado` | int64 | 0.0 | 0 a 162 | Conteo de acciones de juego abierto de la categoría pase_filtrado |
| `cat_centro` | int64 | 0.0 | 0 a 249 | Conteo de acciones de juego abierto de la categoría centro |
| `cat_remate` | int64 | 0.0 | 0 a 167 | Conteo de acciones de juego abierto de la categoría remate |
| `cat_conduccion` | int64 | 0.0 | 0 a 104 | Conteo de acciones de juego abierto de la categoría conduccion |
| `cat_toque` | int64 | 0.0 | 0 a 326 | Conteo de acciones de juego abierto de la categoría toque |
| `cat_despeje` | int64 | 0.0 | 0 a 171 | Conteo de acciones de juego abierto de la categoría despeje |
| `cat_duelo_ofensivo` | int64 | 0.0 | 0 a 741 | Conteo de acciones de juego abierto de la categoría duelo_ofensivo |
| `cat_duelo_defensivo` | int64 | 0.0 | 0 a 433 | Conteo de acciones de juego abierto de la categoría duelo_defensivo |
| `cat_duelo_aereo` | int64 | 0.0 | 0 a 497 | Conteo de acciones de juego abierto de la categoría duelo_aereo |
| `cat_balon_dividido` | int64 | 0.0 | 0 a 276 | Conteo de acciones de juego abierto de la categoría balon_dividido |
| `matches` | int64 | 0.0 | 1 a 38 | Partidos jugados |
| `starts` | int64 | 0.0 | 0 a 38 | Partidos como titular |
| `n_teams` | int64 | 0.0 | 1 a 2 | Equipos en la ventana |
| `team_possession_mean` | float64 | 0.0 | 0.152 a 0.8171 | Posesión media del equipo ponderada por minutos |
| `main_team_id` | int64 | 0.0 | 674 a 1.983e+04 | Equipo con más minutos en la ventana |
| `p90_passes` | float64 | 0.0 | 0 a 128.7 | Tasa por 90 minutos sin ajuste de pases |
| `vol_passes` | float64 | 0.0 | 0 a 122.1 | Tasa por 90 minutos ajustada a 50 % de posesión de pases |
| `p90_prog_passes` | float64 | 0.0 | 0 a 27.74 | Tasa por 90 minutos sin ajuste de pases precisos con avance de al menos 20 unidades en x |
| `vol_prog_passes` | float64 | 0.0 | 0 a 27.14 | Tasa por 90 minutos ajustada a 50 % de posesión de pases precisos con avance de al menos 20 unidades en x |
| `p90_final_third_entries` | float64 | 0.0 | 0 a 35.9 | Tasa por 90 minutos sin ajuste de pases precisos de x < 66,7 a x >= 66,7 |
| `vol_final_third_entries` | float64 | 0.0 | 0 a 29.3 | Tasa por 90 minutos ajustada a 50 % de posesión de pases precisos de x < 66,7 a x >= 66,7 |
| `p90_key_passes` | float64 | 0.0 | 0 a 4.364 | Tasa por 90 minutos sin ajuste de pases con etiqueta 302 (pase clave) |
| `vol_key_passes` | float64 | 0.0 | 0 a 5.424 | Tasa por 90 minutos ajustada a 50 % de posesión de pases con etiqueta 302 (pase clave) |
| `p90_crosses` | float64 | 0.0 | 0 a 27.74 | Tasa por 90 minutos sin ajuste de centros (subevento cross) |
| `vol_crosses` | float64 | 0.0 | 0 a 24.84 | Tasa por 90 minutos ajustada a 50 % de posesión de centros (subevento cross) |
| `p90_carries` | float64 | 0.0 | 0 a 21.63 | Tasa por 90 minutos sin ajuste de conducciones (subevento acceleration) |
| `vol_carries` | float64 | 0.0 | 0 a 17.87 | Tasa por 90 minutos ajustada a 50 % de posesión de conducciones (subevento acceleration) |
| `p90_shots` | float64 | 0.0 | 0 a 14.76 | Tasa por 90 minutos sin ajuste de remates |
| `vol_shots` | float64 | 0.0 | 0 a 19.98 | Tasa por 90 minutos ajustada a 50 % de posesión de remates |
| `p90_box_actions` | float64 | 0.0 | 0 a 64.88 | Tasa por 90 minutos sin ajuste de acciones iniciadas con x >= 84 e y entre 19 y 81 |
| `vol_box_actions` | float64 | 0.0 | 0 a 53.6 | Tasa por 90 minutos ajustada a 50 % de posesión de acciones iniciadas con x >= 84 e y entre 19 y 81 |
| `p90_dribbles_won` | float64 | 0.0 | 0 a 25 | Tasa por 90 minutos sin ajuste de duelos ofensivos en el suelo ganados |
| `vol_dribbles_won` | float64 | 0.0 | 0 a 27.27 | Tasa por 90 minutos ajustada a 50 % de posesión de duelos ofensivos en el suelo ganados |
| `p90_interceptions` | float64 | 0.0 | 0 a 24.19 | Tasa por 90 minutos sin ajuste de eventos con etiqueta 1401 (intercepción) |
| `vol_interceptions` | float64 | 0.0 | 0 a 32.42 | Tasa por 90 minutos ajustada a 50 % de posesión de eventos con etiqueta 1401 (intercepción) |
| `p90_def_duels` | float64 | 0.0 | 0 a 46.45 | Tasa por 90 minutos sin ajuste de duelos defensivos en el suelo |
| `vol_def_duels` | float64 | 0.0 | 0 a 53.55 | Tasa por 90 minutos ajustada a 50 % de posesión de duelos defensivos en el suelo |
| `p90_clearances` | float64 | 0.0 | 0 a 15.2 | Tasa por 90 minutos sin ajuste de despejes |
| `vol_clearances` | float64 | 0.0 | 0 a 12.07 | Tasa por 90 minutos ajustada a 50 % de posesión de despejes |
| `p90_air_duels` | float64 | 0.0 | 0 a 43.17 | Tasa por 90 minutos sin ajuste de duelos aéreos |
| `vol_air_duels` | float64 | 0.0 | 0 a 43.17 | Tasa por 90 minutos ajustada a 50 % de posesión de duelos aéreos |
| `vol_precision_pase` | float64 | 0.4 | 0 a 1 | Tasa por 90 minutos ajustada a 50 % de posesión de precision_pase |
| `loc_depth` | float64 | 0.2 | 2.625 a 91 | Profundidad media de las acciones (x, 0 a 100) |
| `loc_width` | float64 | 0.2 | 6.25 a 46 | Distancia media al eje central (|y - 50|) |
| `loc_sd_x` | float64 | 0.2 | 0 a 45.28 | Desviación estándar de x |
| `loc_sd_y` | float64 | 0.2 | 0 a 40.22 | Desviación estándar de y |
| `comp_pase_simple` | float64 | 0.2 | 0 a 1 | Proporción de la categoría sobre las acciones de juego abierto: pase_simple |
| `comp_pase_largo` | float64 | 0.2 | 0 a 1 | Proporción de la categoría sobre las acciones de juego abierto: pase_largo |
| `comp_pase_cabeza` | float64 | 0.2 | 0 a 1 | Proporción de la categoría sobre las acciones de juego abierto: pase_cabeza |
| `comp_pase_filtrado` | float64 | 0.2 | 0 a 0.2 | Proporción de la categoría sobre las acciones de juego abierto: pase_filtrado |
| `comp_centro` | float64 | 0.2 | 0 a 0.5 | Proporción de la categoría sobre las acciones de juego abierto: centro |
| `comp_remate` | float64 | 0.2 | 0 a 0.3333 | Proporción de la categoría sobre las acciones de juego abierto: remate |
| `comp_conduccion` | float64 | 0.2 | 0 a 0.25 | Proporción de la categoría sobre las acciones de juego abierto: conduccion |
| `comp_toque` | float64 | 0.2 | 0 a 0.5 | Proporción de la categoría sobre las acciones de juego abierto: toque |
| `comp_despeje` | float64 | 0.2 | 0 a 0.3333 | Proporción de la categoría sobre las acciones de juego abierto: despeje |
| `comp_duelo_ofensivo` | float64 | 0.2 | 0 a 0.5 | Proporción de la categoría sobre las acciones de juego abierto: duelo_ofensivo |
| `comp_duelo_defensivo` | float64 | 0.2 | 0 a 0.6 | Proporción de la categoría sobre las acciones de juego abierto: duelo_defensivo |
| `comp_duelo_aereo` | float64 | 0.2 | 0 a 1 | Proporción de la categoría sobre las acciones de juego abierto: duelo_aereo |
| `comp_balon_dividido` | float64 | 0.2 | 0 a 1 | Proporción de la categoría sobre las acciones de juego abierto: balon_dividido |
| `clr_pase_simple` | float64 | 1.4 | -1.168 a 4.777 | Log-ratio centrado de la proporción de la categoría pase_simple |
| `clr_pase_largo` | float64 | 1.4 | -3.644 a 4.632 | Log-ratio centrado de la proporción de la categoría pase_largo |
| `clr_pase_cabeza` | float64 | 1.4 | -3.662 a 1.778 | Log-ratio centrado de la proporción de la categoría pase_cabeza |
| `clr_pase_filtrado` | float64 | 1.4 | -4.876 a 0.8719 | Log-ratio centrado de la proporción de la categoría pase_filtrado |
| `clr_centro` | float64 | 1.4 | -4.791 a 1.727 | Log-ratio centrado de la proporción de la categoría centro |
| `clr_remate` | float64 | 1.4 | -4.414 a 1.415 | Log-ratio centrado de la proporción de la categoría remate |
| `clr_conduccion` | float64 | 1.4 | -4.585 a 0.8494 | Log-ratio centrado de la proporción de la categoría conduccion |
| `clr_toque` | float64 | 1.4 | -1.522 a 2.794 | Log-ratio centrado de la proporción de la categoría toque |
| `clr_despeje` | float64 | 1.4 | -4.968 a 1.599 | Log-ratio centrado de la proporción de la categoría despeje |
| `clr_duelo_ofensivo` | float64 | 1.4 | -2.369 a 2.614 | Log-ratio centrado de la proporción de la categoría duelo_ofensivo |
| `clr_duelo_defensivo` | float64 | 1.4 | -2.508 a 2.422 | Log-ratio centrado de la proporción de la categoría duelo_defensivo |
| `clr_duelo_aereo` | float64 | 1.4 | -2.843 a 2.808 | Log-ratio centrado de la proporción de la categoría duelo_aereo |
| `clr_balon_dividido` | float64 | 1.4 | -2.053 a 2.214 | Log-ratio centrado de la proporción de la categoría balon_dividido |
| `n_open_play_actions` | float64 | 0.0 | 0 a 3877 | Acciones de juego abierto usadas en la composición |
| `short_name` | object | 0.0 |  | Nombre corto (decodificado) |
| `role` | object | 0.0 |  | Rol de Wyscout (GK, DF, MD, FW) |
| `tm_id` | float64 | 13.8 | 26 a 7.244e+05 | Identificador de jugador en Transfermarkt |
| `linked` | object | 13.7 |  | Enlace aceptado con Transfermarkt |
| `fine_position` | object | 16.1 |  | Posición fina: principal por minutos en 2017/18 (alineaciones de Transfermarkt) |
| `fine_group` | object | 22.4 |  | Posición fina agrupada sin lado (referencia externa) |
| `position_source` | object | 13.7 |  | Origen de la posición fina |
| `main_share` | float64 | 16.3 | 0.2132 a 1 | Proporción de minutos en la posición principal |
| `is_core` | bool | 0.0 |  | Pertenece a las cinco ligas del núcleo |
| `eligible` | bool | 0.0 |  | Pertenece a la población elegible de la ventana |
| `window` | object | 0.0 |  | Ventana temporal |
