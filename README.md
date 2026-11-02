# Perfilamiento funcional de jugadores de fútbol más allá de la posición nominal

Repositorio del Trabajo Práctico de Grado II (MIIA, Universidad de los Andes).
Este README es provisional; la versión completa se escribirá al cierre del proyecto.

## Estructura

```
config/        parámetros del proyecto (project.yaml)
data/          raw (inmutable), interim y processed; ver data/README.md
docs/          contexto, protocolo de modelado, registro de decisiones, diccionario de datos
manifests/     procedencia e integridad de las fuentes
notebooks/     exploración (no forma parte del pipeline)
reports/       documento, casebook y figuras
src/           código: ingestion, harmonization, features, diagnostics, models, evaluation, reports
tests/         verificaciones de las tablas derivadas
```

## Ejecución

```
pip install -r requirements.txt
python -m src.pipeline --list
python -m src.pipeline
python -m pytest tests
```
