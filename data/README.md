# Capas de datos

| Capa | Contenido | Regla |
|---|---|---|
| `raw/` | Fuentes originales tal como se descargaron (verificadas con `manifests/`) | Inmutable. No se versiona en git por tamaño (unos 34 GB) |
| `interim/` | Datos extraídos y parseados (JSON extraídos, Parquet de eventos, tablas jugador-partido) | Reproducible con `python -m src.pipeline` |
| `processed/` | Diagnósticos, representaciones de jugadores, modelos y evaluación | Reproducible con `python -m src.pipeline` |

Para reconstruir `raw/` se ejecutan los scripts de `src/ingestion/` (Wyscout, DFL, PFF, Transfermarkt) y se clonan
los repositorios de StatsBomb y SkillCorner en los commits registrados en `manifests/`.
