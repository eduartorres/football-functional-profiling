# Registro de decisiones

Cada decisión indica fecha, si se tomó antes o después de ver resultados de evaluación, y su sustento.

| # | Fecha | Momento | Decisión | Sustento |
|---|---|---|---|---|
| D01 | 2026-10-06 | Antes | Seis fuentes adquiridas con manifiesto y verificación de integridad; adquisición cerrada | Trazabilidad; `manifests/` |
| D02 | 2026-10-06 | Antes | Sofascore excluido | Acceso por endpoints no oficiales y redundancia con las fuentes disponibles |
| D03 | 2026-10-11 | Antes | Núcleo: Wyscout, cinco ligas 2017/18 | Única fuente pública con temporadas completas y cobertura homogénea |
| D04 | 2026-10-11 | Antes | Minutos reconstruidos con alineación, cambios y expulsiones | Wyscout no trae minutos; promedio de 10,97 jugadores por equipo y partido |
| D05 | 2026-10-11 | Antes | Replicación entre proveedores en el Mundial 2018 | Mismos 64 partidos en Wyscout y StatsBomb (auditoría) |
| D06 | 2026-10-11 | Antes | Estudio espacial limitado al Mundial 2022 (StatsBomb 360 y PFF), complementario | Coincidencia de partidos; restricción de tiempo |
| D07 | 2026-10-11 | Antes | Perfil base con acciones con balón y duelos | Wyscout no registra presión ni carreras sin balón |
| D08 | 2026-10-25 | Antes | Posición fina como referencia externa | Rol de Wyscout de 4 categorías vuelve trivial H1 (nota del docente); eta cuadrado mediano 0,36 frente a 0,56 |
| D09 | 2026-10-25 | Antes | Dos representaciones: volumen ajustado por posesión y composición con clr | Sesgo por estilo de equipo (nota del docente); el equipo explica 37 % de la varianza de pases por 90 |
| D10 | 2026-10-25 | Antes | Umbrales tentativos de H1 a H4 | Falsabilidad (nota del docente) |
| D11 | 2026-11-02 | Antes | Posición fina = posición principal por minutos en alineaciones de Transfermarkt 2017/18; respaldo: sub-posición del registro | Disponible para 2.485 de 2.493 jugadores enlazados; mediana de 92 % de minutos en la posición principal |
| D12 | 2026-11-02 | Antes | Referencia agrupada sin lado (`fine_group`, 9 categorías) | Los indicadores espaciales son simétricos en y; con lados, la NMI quedaría artificialmente baja |
| D13 | 2026-11-02 | Antes | Población elegible exige posición fina; 1.500 jugadores-temporada (antes 1.550) | Sin posición fina no se puede evaluar H1, H2 ni la línea base |
| D14 | 2026-11-02 | Antes | Enlace con Transfermarkt: un `tm_id` no puede asignarse a dos jugadores de Wyscout | Se elimina un enlace duplicado (2.493 enlaces) |
| D15 | 2026-11-02 | Antes | Posesión aproximada como proporción de pases del equipo en el partido | Medida transparente y disponible en todos los partidos; Wyscout no registra posesión |
| D16 | 2026-11-02 | Antes | Composición en juego abierto con 13 categorías; balón parado excluido | Los lanzamientos de banda, córners y tiros libres dependen de asignaciones del entrenador |
| D17 | 2026-11-02 | Antes | Reemplazo multiplicativo de ceros con medio conteo; clr solo si la masa reemplazada es menor que 1 | Requisito de la transformación log-ratio |
| D18 | 2026-11-02 | Antes | Mitades de temporada por jornada (19; 17 en Bundesliga) como desarrollo y reserva | El núcleo tiene una sola temporada |
| D19 | 2026-11-02 | Antes | H4 evaluada con un criterio analítico de pertinencia | La evaluación de la consulta se diseña con datos históricos, sin participación de usuarios; protocolo en `docs/protocolo_modelado.md` |
| D20 | 2026-11-02 | Antes | Protocolo de modelado v1.0 congelado | Separar decisiones previas de las tomadas tras ver resultados |
| D21 | 2026-11-02 | Antes de seleccionar | V de Cramér con corrección de sesgo de Bergsma (2013) | Prueba de humo: sin corrección, el valor esperado bajo independencia con 98 equipos ronda 0,26 y el umbral de 0,20 rechazaría cualquier partición |
| D22 | 2026-11-02 | Antes de seleccionar | Proporción máxima de jugadores sin grupo (ruido de HDBSCAN) de 20 % | Una solución que deja fuera a la mayoría de jugadores no sirve para la consulta; prueba de humo: HDBSCAN dejó 75 % como ruido |
| D23 | 2026-11-02 | Antes de seleccionar | Tamizaje de la grilla con 50 réplicas bootstrap y confirmación con 200 réplicas para las candidatas | Costo de cómputo del análisis de arquetipos; la regla de selección se aplica sobre las 200 réplicas |
| D24 | 2026-11-02 | Antes de seleccionar | Tras la evaluación, la configuración elegida se reajusta en la temporada completa para describir los perfiles finales | Los perfiles del producto deben usar toda la exposición disponible; la evaluación se hace con h1 y h2 |
| D25 | 2026-11-02 | Después | Solución seleccionada por la regla del protocolo: K-means, k = 3, representación de composición | Silueta 0,422; ARI 0,969; Jaccard >= 0,975; NMI equipo 0,009. Sin cambios a la regla |
| D26 | 2026-11-02 | Después | K-means k = 5 (composición) se reporta como sensibilidad de mayor resolución, sin reemplazar la selección | ARI 0,943 y Jaccard mínimo 0,935; la silueta favorece k pequeños |
| D27 | 2026-11-02 | Después | La consulta de similitud del producto usará el espacio ponderado completo, sin reducción por PCA; la PCA se mantiene para el agrupamiento | Autoidentificación top-1: 0,10 con 4 componentes frente a 0,25 sin reducción; en casos de reemplazo la pertinencia sube de 0,62 a 0,67. Decisión posterior a la evaluación, reportada como tal |
| D28 | 2026-11-02 | Antes de replicar | Replicación con 10 categorías homologadas; se excluyen conducción, toque y balón dividido; umbral de 270 minutos en el torneo | Definiciones no equivalentes entre Wyscout y StatsBomb (Acceleration frente a Carry) |
| D29 | 2026-11-03 | Después | Se publican en el repositorio las tablas procesadas y las tablas livianas de jugador-partido, sin fecha de nacimiento; quedan fuera los datos crudos, los eventos completos, los atributos personales y los derivados de StatsBomb | Permite repetir la selección, la evaluación y los productos desde una copia del repositorio; respeta la Ley 1581 de 2012 y las condiciones de uso de cada fuente. No cambia ningún resultado |
