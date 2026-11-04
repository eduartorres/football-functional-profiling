# Datos

## Qué se versiona

| Ruta | Contenido | Versionado |
|---|---|---|
| `raw/` | Fuentes originales tal como se descargaron (unos 34 GB), verificadas con `manifests/` | No; ver "Obtener las fuentes" |
| `interim/wyscout/events/`, `events_parquet/`, `matches/` | Eventos y partidos extraídos de los ZIP de Wyscout (unos 950 MB) | No; los regenera la etapa `extract` |
| `interim/wyscout/players.parquet` | Atributos de los jugadores, incluida la fecha de nacimiento | No; contiene datos personales que solo sirven para enlazar fuentes |
| `interim/replication/` | Tablas del Mundial 2018 derivadas de StatsBomb | No; el acuerdo de uso de StatsBomb no permite redistribuirlas |
| `interim/wyscout/player_match.parquet` | Una fila por jugador y partido: minutos, posesión y conteos de acciones | Sí |
| `interim/wyscout/team_match.parquet` | Posesión aproximada por equipo y partido | Sí |
| `interim/wyscout/teams.parquet` | Nombre y país de cada equipo | Sí |
| `processed/diagnostics/` | Auditoría de las fuentes y hallazgos preliminares | Sí |
| `processed/features/` | Posición fina de referencia y representaciones por jugador (temporada completa y mitades) | Sí |
| `processed/models/` | Grilla de configuraciones, modelo seleccionado, transformadores y perfiles | Sí |
| `processed/evaluation/` | Hipótesis, casos de reemplazo, sensibilidad y replicación (solo resultados agregados) | Sí |

Las tablas versionadas no contienen fechas de nacimiento ni otros atributos personales; los jugadores se
identifican por su identificador y nombre corto de Wyscout. Las columnas de cada tabla se describen en
`docs/diccionario_datos.md`. `python -m src.pipeline --list` indica qué etapas pueden ejecutarse con los datos
presentes.

## Obtener las fuentes

Todas las fuentes son públicas. Cada una queda en `data/raw/<fuente>/` y se verifica contra su manifiesto.

| Fuente | Procedimiento | Manifiesto |
|---|---|---|
| Wyscout | `python -m src.ingestion.ingest_wyscout --download` (Figshare, colección 4415000 v5) | `wyscout_manifest.json` |
| StatsBomb | `git clone https://github.com/hudl/open-data data/raw/statsbomb` y `git checkout` del commit registrado | `statsbomb_commit.txt` |
| Transfermarkt | `python -m src.ingestion.ingest_transfermarkt --download` (snapshot del 6 de julio de 2026) | `transfermarkt_manifest.json` |
| SkillCorner | `git clone https://github.com/SkillCorner/opendata data/raw/skillcorner` con Git LFS y `git checkout` del commit registrado | `skillcorner_commit.txt` |
| DFL | `python -m src.ingestion.ingest_dfl --download` (Figshare, artículo 28196177) | `dfl_manifest.json` |
| PFF FC | Inscripción en el sitio de PFF FC y copia de la carpeta compartida; `python -m src.ingestion.ingest_pff --verify` | `pff_manifest.json` |

Con las fuentes en su lugar, `python -m src.pipeline` reconstruye `interim/` y `processed/` desde cero.
SkillCorner, DFL y PFF solo intervienen en la auditoría de fuentes.
