# Perfilamiento funcional de jugadores de fútbol más allá de la posición nominal

Trabajo Práctico de Grado II, Maestría en Inteligencia Analítica para la Toma de Decisiones,
Universidad de los Andes. Autor: Eduar Felipe Riaño Torres. Asesor: Juan Pablo Gómez Bravo.

El proyecto construye perfiles funcionales de jugadores de campo a partir de datos de eventos (Wyscout, cinco
grandes ligas 2017/18), los evalúa frente a una línea base por posición fina (Transfermarkt), replica sus
dimensiones con StatsBomb en el Mundial 2018 y ofrece un explorador de jugadores similares.

## Estructura

```
config/project.yaml     parámetros, umbrales de hipótesis y semillas
data/                   raw (inmutable, no versionado), interim y processed; ver data/README.md
docs/                   contexto, protocolo de modelado, registro de decisiones, diccionario de datos
manifests/              procedencia e integridad de las fuentes
notebooks/              exploración (fuera del pipeline)
reports/documento/      documento del trabajo de grado y su fuente (build/)
reports/explorer/       explorador de perfiles (prototipo)
reports/casebook/       casebook y guion del video de avances
reports/figures/        figuras
src/ingestion/          adquisición de fuentes (se ejecuta una vez)
src/harmonization/      extracción de Wyscout y homologación con StatsBomb
src/features/           jugador-partido, posición fina y representaciones
src/diagnostics/        auditoría de fuentes y hallazgos preliminares
src/models/             representación, algoritmos, grilla, selección y perfiles
src/evaluation/         reserva temporal, hipótesis, casos de reemplazo, sensibilidad y replicación
src/reports/            diccionario, casebook y explorador
src/pipeline.py         orquestador
tests/                  pruebas de consistencia
```

## Reproducción

```
pip install -r requirements.txt
python -m src.pipeline --until findings                # preparación (o --only <etapa>)
python -m src.models.select_model --stage screen       # repetir hasta 'quedan 0'
python -m src.models.select_model --stage confirm      # repetir hasta 'quedan 0'
python -m src.pipeline --from model_select             # selección, evaluación, explorador y reportes
python -m pytest tests
python reports/documento/build/build.py                # regenera el documento
```

`python -m src.pipeline --list` muestra las etapas. Las cifras del documento provienen de
`data/processed/` y se regeneran con estos comandos.
