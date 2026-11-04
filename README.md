# Perfilamiento funcional de jugadores de fútbol más allá de la posición nominal

Trabajo Práctico de Grado II, Maestría en Inteligencia Analítica para la Toma de Decisiones (MIIA),
Universidad de los Andes.
Autor: Eduar Felipe Riaño Torres. Asesor: Juan Pablo Gómez Bravo.

El proyecto construye perfiles funcionales de jugadores de campo a partir de datos de eventos y evalúa qué
información aportan frente a la posición nominal. El núcleo empírico usa los eventos públicos de Wyscout de las
cinco grandes ligas europeas en 2017/18; Transfermarkt aporta la posición fina de referencia y StatsBomb permite
replicar las dimensiones en los 64 partidos del Mundial 2018. El resultado se ofrece como un explorador de
perfiles y jugadores similares para apoyar la preselección de candidatos en scouting.

**Pregunta de negocio.** ¿Cómo apoyar la preselección de jugadores comparables con una necesidad deportiva o con
un jugador de referencia a partir de su comportamiento observado en campo?

**Pregunta de investigación.** ¿En qué medida es posible identificar perfiles funcionales de jugadores a partir de
sus patrones de comportamiento en campo, más allá de su posición nominal?

**Usuario de referencia.** Analista de scouting de un club colombiano con un equipo de búsqueda reducido que debe
reemplazar a un jugador vendido.

## Resultados principales

Se compararon 108 configuraciones de agrupamiento (K-means, mezclas gaussianas, Ward, arquetipos y HDBSCAN, con
k de 3 a 12) sobre dos representaciones: volumen por 90 minutos ajustado por posesión y composición de acciones
con transformación log-ratio centrada. La regla de selección y los umbrales de las hipótesis se fijaron en
`docs/protocolo_modelado.md` antes de ajustar el primer modelo.

| Resultado | Valor |
|---|---|
| Población elegible (900 minutos o más, con posición fina) | 1.500 jugadores-temporada |
| Solución seleccionada | K-means, k = 3, representación de composición |
| Perfiles | Construcción y defensa posicional; carril lateral; ataque y finalización |
| Estabilidad bootstrap (200 réplicas) | ARI 0,969; Jaccard por grupo entre 0,975 y 0,983 |
| Mismo perfil entre mitades de temporada | 91,8 % de 1.155 jugadores (36,7 % por azar) |
| Asociación con el equipo | NMI 0,009 |
| Asociación con la posición fina | NMI 0,495 |
| Replicación con StatsBomb, Mundial 2018 | ARI 0,943 entre particiones; congruencia de Tucker entre 0,86 y 0,97 |
| Casos de reemplazo (30, listas de 20) | Pertinencia 0,62 frente a 0,61 de la búsqueda por posición; 9,6 candidatos pertinentes nuevos por caso |

H1 (información adicional a la posición), H3 (estabilidad) y H4 (candidatos pertinentes nuevos) no se rechazan;
H2 se rechaza por el criterio de autoidentificación. El detalle está en los capítulos 6 y 7 del documento.

## Productos

| Producto | Ubicación | Cómo se usa |
|---|---|---|
| Documento del trabajo de grado | `reports/documento/` | Archivo Word; su fuente está en `reports/documento/build/` |
| Explorador de perfiles (prototipo) | `reports/explorer/explorer.html` | Se descarga y se abre en el navegador; no requiere servidor |
| Casebook de resultados | `reports/casebook/casebook.html` | Igual que el explorador |
| Material del avance de octubre de 2026 | `reports/casebook/*_avance_2026-10-11.html` | Casebook y guion del video de avance |

## Estructura

```
config/project.yaml     parámetros, umbrales de las hipótesis y semillas
data/                   tablas intermedias y procesadas versionadas; ver data/README.md
docs/                   protocolo de modelado, registro de decisiones y diccionario de datos
manifests/              procedencia e integridad de cada fuente
reports/documento/      documento del trabajo de grado y su fuente (build/)
reports/explorer/       explorador de perfiles (prototipo)
reports/casebook/       casebook de resultados y material del avance
reports/figures/        figuras usadas en el documento
src/ingestion/          adquisición de las fuentes (se ejecuta una vez)
src/harmonization/      extracción de Wyscout y homologación con StatsBomb
src/features/           jugador-partido, posición fina y representaciones
src/diagnostics/        auditoría de fuentes y hallazgos preliminares
src/models/             representación, algoritmos, grilla, selección y perfiles
src/evaluation/         reserva temporal, hipótesis, casos de reemplazo, sensibilidad y replicación
src/reports/            diccionario de datos, explorador y casebook
src/config.py           lectura de config/project.yaml y rutas del proyecto
src/pipeline.py         orquestador de las etapas
tests/                  pruebas de consistencia de las tablas y de la evaluación
```

## Reproducción

Requiere Python 3.10 o superior.

```
pip install -r requirements.txt
```

**Desde el repositorio.** Las tablas versionadas en `data/` permiten repetir la selección del modelo, los
perfiles, la evaluación, la sensibilidad, el explorador, el diccionario y el casebook sin descargar las fuentes.
Las etapas que necesitan datos no versionados se omiten y conservan sus resultados.

```
python -m pytest
python -m src.pipeline --from findings --skip-unavailable
```

**Desde las fuentes.** Con las fuentes descargadas en `data/raw/` según `data/README.md`:

```
python -m src.pipeline --until features                # extracción, auditoría, posición fina y variables
python -m src.models.select_model --stage screen       # grilla de 108 configuraciones; repetir hasta 'quedan 0'
python -m src.models.select_model --stage confirm      # confirmación con 200 réplicas; repetir hasta 'quedan 0'
python -m src.pipeline --from findings                 # selección, evaluación, replicación y productos
python reports/documento/build/build.py                # regenera el documento
```

`python -m src.pipeline --list` muestra las etapas y los insumos que requiere cada una. Todas las cifras del
documento provienen de `data/processed/` y se regeneran con estos comandos.

## Fuentes de datos

| Fuente | Uso en el proyecto | Condición de uso |
|---|---|---|
| Wyscout, eventos públicos (Pappalardo et al., 2019) | Núcleo: cinco ligas 2017/18 y Mundial 2018 | CC BY 4.0 |
| StatsBomb Open Data | Replicación en el Mundial 2018 | Acuerdo de uso de StatsBomb: investigación, con atribución y sin redistribución |
| transfermarkt-datasets | Posición fina de referencia y transferencias del verano de 2018 | CC0 1.0 |
| PFF FC, Mundial 2022 | Auditada; estudio espacial reservado como trabajo futuro | Acceso previo registro, sin redistribución |
| SkillCorner Open Data | Auditada; fuera del núcleo | Licencia MIT del repositorio |
| DFL (Bassek et al., 2025) | Auditada; fuera del núcleo | CC BY 4.0 |

Pappalardo, L., Cintia, P., Rossi, A., Massucco, E., Ferragina, P., Pedreschi, D., & Giannotti, F. (2019). A public
data set of spatio-temporal match events in soccer competitions. *Scientific Data*, 6, 236.
https://doi.org/10.1038/s41597-019-0247-7

Bassek, M., Rein, R., Weber, H., & Memmert, D. (2025). An integrated dataset of spatiotemporal and event data in
elite soccer. *Scientific Data*. https://doi.org/10.1038/s41597-025-04505-y

Datos de StatsBomb: StatsBomb Open Data, https://github.com/hudl/open-data.

## Cómo citar

Riaño Torres, E. F. (2026). *Perfilamiento funcional de jugadores de fútbol más allá de la posición nominal*
[Trabajo de grado de maestría, Universidad de los Andes]. https://github.com/eduartorres/football-functional-profiling
