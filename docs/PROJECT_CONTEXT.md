# Contexto del proyecto

Trabajo Práctico de Grado II, Maestría en Inteligencia Analítica para la Toma de Decisiones,
Universidad de los Andes. Autor: Eduar Felipe Riaño Torres. Asesor: Juan Pablo Gómez Bravo.

**Tema.** Perfilamiento funcional de jugadores de fútbol más allá de la posición nominal.

**Pregunta de negocio.** ¿Cómo apoyar la preselección de jugadores comparables con una necesidad deportiva o con
un jugador de referencia a partir de su comportamiento observado en campo?

**Pregunta de investigación.** ¿En qué medida es posible identificar perfiles funcionales de jugadores a partir de
sus patrones de comportamiento en campo, más allá de su posición nominal?

**Usuario de referencia.** Analista jefe de scouting de un club de primera división colombiana con un equipo de
búsqueda reducido que debe reemplazar a un jugador vendido.

**Alcance.**
- Núcleo: eventos de Wyscout, cinco grandes ligas, 2017/18.
- Replicación: Mundial 2018 en Wyscout y StatsBomb.
- Estudio complementario: Mundial 2022 con StatsBomb 360 y PFF.
- Transfermarkt: posición fina de referencia y contexto. No entra en los perfiles.
- SkillCorner y DFL: auditadas, fuera del núcleo.

**Documentos de referencia en este repositorio.**
- `docs/protocolo_modelado.md`: protocolo congelado (representaciones, modelos, selección, hipótesis).
- `docs/decisiones.md`: registro de decisiones.
- `docs/diccionario_datos.md`: diccionario generado de las tablas derivadas.
- `reports/documento/`: documento del trabajo de grado (estructura de nueve capítulos del tutor).

**Reglas.** `data/raw` es inmutable. Toda cifra reportada en el documento debe poder reproducirse con
`python -m src.pipeline`. No se inventan referencias, resultados ni cifras.
