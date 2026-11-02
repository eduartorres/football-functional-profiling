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
| D19 | 2026-11-02 | Antes | H4 evaluada de forma analítica, sin revisores deportivos | No hay revisores disponibles; protocolo en `docs/protocolo_modelado.md` |
| D20 | 2026-11-02 | Antes | Protocolo de modelado v1.0 congelado | Separar decisiones previas de las tomadas tras ver resultados |
