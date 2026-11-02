# Protocolo de modelado

Versión 1.0, congelada el 2 de noviembre de 2026, antes de ajustar cualquier modelo.
Los parámetros numéricos están en `config/project.yaml`. Cualquier cambio posterior se registra en
`docs/decisiones.md` indicando si se tomó antes o después de ver resultados de evaluación.

## 1. Población y unidad de análisis

- Unidad: jugador x competición x ventana, en las cinco grandes ligas de Wyscout 2017/18.
- Población elegible (ventana completa): jugadores de campo con al menos 900 minutos y posición fina
  disponible. Resultado de la preparación: 1.500 jugadores-temporada.
- Ventanas temporales: `h1` (jornadas 1 a 19; 1 a 17 en Bundesliga) y `h2` (resto). Umbral por mitad: 450 minutos.
- Sensibilidad de exposición: 450 y 1.350 minutos en la ventana completa.

## 2. Representaciones

Se evalúan dos representaciones, ambas acompañadas del bloque de localización:

| Representación | Bloques |
|---|---|
| Volumen | distribución (`vol_passes`, `vol_precision_pase`), progresión (`vol_prog_passes`, `vol_final_third_entries`, `vol_carries`, `vol_dribbles_won`), creación (`vol_key_passes`, `vol_crosses`), finalización (`vol_shots`, `vol_box_actions`), recuperación (`vol_interceptions`, `vol_def_duels`, `vol_clearances`, `vol_air_duels`) |
| Composición | 13 variables `clr_*` de las categorías de juego abierto |
| Localización (en ambas) | `loc_depth`, `loc_width`, `loc_sd_x`, `loc_sd_y` |

- Volumen: acciones con balón por 90 minutos de posesión propia y acciones defensivas por 90 minutos de
  posesión rival, expresadas a 50 % de posesión. La posesión se aproxima con la proporción de pases.
- Composición: proporciones con reemplazo multiplicativo de ceros (medio conteo) y log-ratio centrado.
- La posición nominal, el equipo y las variables de Transfermarkt no entran en ninguna representación.

## 3. Preprocesamiento

1. Estandarización con media y desviación estándar estimadas en la partición de desarrollo.
   Alternativa evaluada: mediana y rango intercuartílico.
2. Ponderación por bloque: cada variable se multiplica por `1/sqrt(n_bloque)` para que cada bloque
   aporte varianza comparable.
3. PCA reteniendo el 80 % de la varianza. Las cargas se reportan para interpretar los componentes.
4. Distancia euclidiana en el espacio de componentes. Alternativa evaluada: coseno.

## 4. Particiones

- Desarrollo: ventana `h1`. Reserva temporal: ventana `h2`. El escalador, la ponderación y la PCA se ajustan
  en `h1` y se aplican sin reajuste a `h2`.
- Generalización a jugadores nuevos: validación agrupada por jugador (5 particiones) en la ventana completa.
- La selección del modelo se hace solo con desarrollo y validación agrupada. La reserva `h2` se usa una vez,
  para la evaluación final.

## 5. Modelos

- Algoritmos: K-means, mezclas gaussianas (covarianza completa y diagonal), jerárquico de Ward,
  análisis de arquetipos y HDBSCAN.
- Número de grupos o arquetipos: 3 a 12.
- Semilla: 2026. Remuestreo bootstrap por jugador: 200 réplicas.

### Regla de selección (en este orden)

1. Estabilidad: ARI promedio bootstrap >= 0,60 y Jaccard bootstrap >= 0,60 en la mayoría de los grupos.
2. Confusión por equipo: NMI y V de Cramér entre grupo y equipo < 0,20.
3. Separación: silueta más alta y Davies-Bouldin más bajo entre las soluciones que cumplen 1 y 2.
4. Interpretabilidad: perfiles describibles con variables originales y jugadores representativos.

Si ninguna solución cumple 1 y 2, se mantiene la representación continua (PCA) para la consulta de similitud
y se reporta que no hay grupos estables; este resultado responde H3 en sentido negativo.

## 6. Línea base

- Posición fina agrupada sin lado (`fine_group`, 9 categorías), a partir de los minutos en cada posición de
  alineación de Transfermarkt en 2017/18.
- Consulta base: candidatos de la misma posición fina ordenados por distancia en indicadores por 90 minutos
  sin ajuste (`p90_*`) estandarizados.

## 7. Evaluación de hipótesis

| Hipótesis | Medida | Criterio de rechazo |
|---|---|---|
| H1 | NMI entre grupos y `fine_group` | NMI >= 0,50 |
| H2 | Proporción de los 10 vecinos de otra `fine_group`; autoidentificación top-1 entre `h1` y `h2` | < 20 % de vecinos de otra posición, o top-1 < 0,50 |
| H3 | ARI bootstrap promedio; Jaccard bootstrap por grupo | ARI < 0,60 o mayoría de grupos con Jaccard < 0,60 |
| H4 | Casos de reemplazo, listas de 20 | proporción pertinente funcional < base, o menos de 2 pertinentes nuevos |
| Condición | NMI grupo-equipo | >= 0,20 invalida la lectura funcional |

Autoidentificación: para cada jugador elegible en ambas mitades se calcula su representación en `h1` y en `h2`
(transformaciones ajustadas en `h1`) y se mide si su vecino más cercano en `h2` es él mismo (top-1) o está
entre los 10 primeros (top-10). La línea base es la misma medida con indicadores `p90_*`.

### H4 sin revisores deportivos (evaluación analítica)

- Casos: jugadores elegibles de las cinco ligas que Transfermarkt registra como transferidos fuera de su club
  entre el 1 de junio y el 31 de agosto de 2018; se toman 30 casos con muestreo estratificado por `fine_group`
  y semilla 2026.
- Listas: 20 candidatos de otros clubes, construidas con la ventana `h1`, por la consulta funcional y por la
  consulta base.
- Pertinencia analítica: un candidato es pertinente si en la ventana reservada `h2` se ubica dentro del 10 %
  más cercano al jugador de referencia en el espacio descriptivo completo (todas las variables `vol_*`, `clr_*`
  y `loc_*` estandarizadas con parámetros de `h1`).
- Limitación declarada: la pertinencia analítica comparte variables con la representación funcional; se
  reporta como evidencia de consistencia y no sustituye el juicio de expertos.

## 8. Replicación con StatsBomb

Mundial 2018 (64 partidos en ambos proveedores). Se construyen los indicadores equivalentes según la matriz de
definiciones, se enlazan jugadores por nombre, fecha de nacimiento y selección, y se comparan cargas de PCA
(congruencia de Tucker), asignaciones (ARI) y vecinos de los mismos jugadores.
