# Lessons Learned - Sistema Inteligente de Soporte Hospitalario

## Patrones a evitar

| Fecha | Error | Causa raiz | Regla |
|-------|-------|-----------|-------|
| 2026-04-20 | Variables en `.env` que no se aplican en `docker-compose` (MONGO_USER/PASSWORD definidas pero MongoDB sin auth) | Generar configuracion sin verificar que cada variable tiene consumidor real | Regla: cada variable de `.env` debe tener al menos un consumidor en compose o codigo. Si no, o se usa o se elimina |
| 2026-04-20 | Redundancia entre `MONGO_INITDB_DATABASE` en compose y `db.getSiblingDB('hospital')` en script de init | Configuracion defensiva duplicando la misma informacion en dos sitios | Regla: una sola fuente de verdad. Si el script crea la DB, el compose no necesita declararla |
| 2026-04-20 | IA anadio entrada nueva al diario rompiendo el orden cronologico (sesion 7 encima de sesion 6) | La IA inserta contenido nuevo en la posicion que le parece relevante, no por fecha | Regla: al editar documentos cronologicos (diario, changelog, ADRs), verificar explicitamente que la nueva entrada va al final o en su posicion cronologica correcta |
| 2026-04-20 | IA uso tipo `refactor` en un commit que en realidad era limpieza de configuracion + documentacion | La IA no distingue con precision entre tipos de Conventional Commits cuando hay un mix de cambios | Regla: refactor = reestructurar codigo sin cambiar comportamiento. Limpieza de config o deps = `chore`. Cambios en docs/diarios/lecciones = `docs`. Si hay mix, priorizar el cambio dominante |
| 2026-04-20 | IA uso `refactor:` en el commit de migracion PostgreSQL → MongoDB cuando solo cambiaban archivos de documentacion (no habia codigo todavia) | Sin codigo implementado no puede haber refactor. Uso del tipo por inercia del lenguaje coloquial ("refactorizar la decision") | Regla: `refactor:` SOLO aplica cuando hay codigo que se reestructura sin cambiar comportamiento. Si solo cambian specs/design/decisions/README → `docs:` |
| 2026-04-20 | Tests de logging fallaban dentro de pytest porque el plugin `pytest-logging` instala su propio handler en el root logger, interfiriendo con aserciones sobre `root.handlers`/`root.level` | Los tests inspeccionaban estado interno del root logger en lugar de comportamiento observable | Regla: para testear configuracion de logging, asertar comportamiento observable (nombre del logger, mensajes capturados via `caplog`, formato de constantes) en vez de inspeccionar handlers/level del root logger |
| 2026-04-20 | La IA repitio el error de orden cronologico en el diario (anadio sesion 8 encima de sesion 7) a pesar de que la leccion ya estaba documentada | Tener una regla documentada no garantiza que la IA la aplique. La IA tiende a anadir entradas "donde la conversacion esta" sin verificar orden | Regla reforzada: CADA vez que se anade entrada a `docs/diario-ia.md` o `CHANGELOG.md`, leer las ultimas lineas primero y verificar explicitamente que la nueva entrada va al final |
| 2026-04-20 | Cambios en codigo dentro del contenedor no se reflejaban en pytest porque la imagen Docker ya tenia la version antigua copiada | El Dockerfile hace `COPY src/ ./src/` en build-time, no en run-time | Regla: tras editar codigo Python que corre en contenedor, hacer `docker compose build <service>` antes de re-ejecutar. Alternativa para iteracion rapida: montar `src/` como bind mount volume en modo dev |

## Decisiones tomadas

| Fecha | Decision | Alternativas | Por que |
|-------|----------|-------------|---------|
| 2026-04-14 | PySpark como framework de procesamiento distribuido | Dask, Apache Beam | Estandar industria, muy valorado por evaluadores de Big Data. Codigo standalone se ejecuta igual en cluster real — demuestra escalabilidad sin necesitar infraestructura real. Ver ADR-001 |
| 2026-04-14 | PyTorch para Deep Learning (modelo de radiografias) | TensorFlow/Keras | Dominante en investigacion, debug intuitivo, mas flexible para la parte de "Investigacion y Desarrollo" que el enunciado pide. Ver ADR-001 |
| 2026-04-14 | MongoDB como BBDD principal | PostgreSQL, PostgreSQL+MongoDB | Texto oculto en el enunciado (`NoSQL sobre todo`) indica preferencia del profesor. Modelo de documentos encaja con datos clinicos semi-estructurados — admissions embebidas en patients evita joins. Ver ADR-002 |
| 2026-04-14 | MinIO como almacenamiento de objetos | AWS S3, GridFS en MongoDB | Compatible con S3 (estandar industrial), gratis y local. Las imagenes binarias no rinden en MongoDB. Cumple el requisito de "2 tipos de almacenamiento" del enunciado |
| 2026-04-14 | Dataset COVID-19 Radiography Database (Kaggle) | Otros datasets publicos de chest X-ray | Exactamente las 3 clases que pide el enunciado (Normal/Pneumonia/COVID), dataset citado en papers, de Qatar University + University of Dhaka |
| 2026-04-14 | Feature branches como estrategia git | Rama por persona, trunk-based | Estandar industria, aislamiento de cambios, PRs revisables. Mas limpio que rama/persona cuando hay 2 colaboradores |
| 2026-04-20 | Streamlit como dashboard (pendiente de implementar) | Grafana, Dash | Mas simple, todo en Python, ideal para demos. El enunciado no fija ninguno concreto. Ver CLAUDE.md |
| 2026-04-20 | Spark en modo standalone (local[*]) dentro del contenedor | Cluster Spark master + workers | Volumen simulado no justifica cluster. Codigo PySpark identico al que correria en cluster real — escala sin cambiar logica |

## Cosas que funcionan

- **Metodologia SDD:** Aprobar spec → design → tasks antes de codificar evita reworks. Cada fase descubre problemas antes que la siguiente
- **Trazabilidad con IDs:** RF-x / RNF-x / CB-x / CA-x permite conectar cada pieza de codigo con un requisito — facilita code review y memoria tecnica
- **ADRs:** Documentar el "por que" de cada decision tecnica al tomarla ahorra preguntas futuras y evita revisiones
- **`pdftotext` para detectar easter eggs:** Leer PDFs solo como imagen deja escapar texto oculto. Complementar con extraccion plana detecta pistas del profesor
- **Docker Compose con healthchecks + depends_on:** Evita race conditions en arranque. El servicio pipeline espera a mongodb y minio healthy antes de iniciar
- **Smoke test dentro del contenedor (`verify_pyspark.py`):** Forma rapida y visible de validar que la imagen Docker arranca y PySpark funciona correctamente
- **Logging centralizado con guard idempotente:** Evita duplicacion de handlers cuando multiples modulos llaman `setup_logging()`
- **Squash de auto-commits:** El hook genera commits atomicos por archivo; squashear manualmente antes del push deja un historial legible
