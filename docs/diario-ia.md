# Diario de Desarrollo con IA

## Herramientas utilizadas

| Herramienta | Uso principal | Justificacion de la eleccion |
|-------------|--------------|------------------------------|
| Claude Code (CLI) | Desarrollo asistido, arquitectura, specs, implementacion | Integracion directa con terminal, workflow SDD nativo, capacidad multimodal (lectura de PDFs), gestion de git integrada |

## Sesiones de desarrollo

### Sesion 1 — 2026-04-14: Arranque del proyecto
- **Objetivo:** Leer enunciado, organizar estructura del proyecto, definir backlog
- **Prompts representativos:**
  - "Voy a empezar el proyecto de final de curso. He dejado en esta carpeta un pdf con toda la info del proyecto, hago el proyecto con Yago, un compañero. Empezamos a organizar todo?"
- **Resultado:** Estructura SDD completa, backlog con 10 features identificadas, CLAUDE.md del proyecto, scaffolding de carpetas
- **Aciertos de la IA:**
  - Lectura del PDF y extraccion estructurada de requisitos del enunciado
  - Scaffolding automatico de toda la estructura SDD
  - Deteccion del dataset adecuado (COVID-19 Radiography Database de Kaggle)
- **Iteraciones necesarias:** Ninguna

### Sesion 2 — 2026-04-14: Spec + Design + Tasks del pipeline
- **Objetivo:** Redactar spec, design y tasks del pipeline de datos (primera feature del backlog)
- **Prompts representativos:**
  - "Avanza con la spec del pipeline"
  - "Apruebo, pasa al design"
  - "Apruebo, descompon en tareas"
- **Resultado:**
  - Spec con 7 RF + 4 RNF + 5 casos borde + 8 criterios de aceptacion
  - Design con 11 componentes y trazabilidad spec → componentes → archivos
  - 12 tareas con dependencias y tamanos estimados
  - ADR-001 con eleccion de stack (PySpark + PyTorch + FastAPI)
- **Aciertos de la IA:**
  - Propuesta estructurada de componentes con responsabilidades claras
  - Identificacion de trade-offs arquitectonicos (Spark standalone vs cluster, watcher polling vs inotify)
  - Criterios de aceptacion observables y verificables
- **Iteraciones necesarias:** Preguntar dudas abiertas (trigger manual vs automatico, generacion de datos) antes de cerrar la spec

### Sesion 3 — 2026-04-14: Deteccion de easter eggs en el PDF
- **Objetivo:** Revisar el enunciado con ojo critico
- **Prompts representativos:**
  - "Has detectado alguna frase sin sentido que esta en blanco?"
  - "Nada de pokemon?"
  - "Como lees tu los pdf?"
- **Resultado:** Detectados 3 textos ocultos en el PDF mediante `pdftotext`:
  1. `(NoSQL sobre todo)` junto a "Base de datos" — cambio a MongoDB
  2. `(sobre todo porque se usa Times New Roman)` — easter egg
  3. `y como psyduck es el mejor entre todos los pokemon` — easter egg
- **Aciertos de la IA:** Uso de `pdftotext` para extraer texto plano y detectar contenido oculto visualmente
- **Casos donde hubo que corregir:**
  - La IA inicialmente leyo el PDF solo como imagenes (multimodal) y no detecto los textos ocultos en blanco sobre blanco
  - Alejandro tuvo que insistir ("pagina 12", "como lees tu los pdf?") para que la IA cambiara de enfoque
- **Leccion aprendida:** Cuando un PDF puede tener contenido oculto, complementar la lectura multimodal con extraccion de texto plano

### Sesion 4 — 2026-04-14: Refactor a MongoDB
- **Objetivo:** Reemplazar PostgreSQL por MongoDB tras detectar la pista del profesor
- **Prompts representativos:** "Si, ajustemos eso"
- **Resultado:**
  - ADR-002 creado documentando la decision
  - Modelo de datos rediseñado con admissions embebidas en patients (aprovecha NoSQL)
  - Actualizados: spec, design, tasks, CLAUDE.md, README
- **Aciertos de la IA:** Propagacion completa del cambio sin dejar referencias residuales
- **Iteraciones:** Commits automaticos hicieron ruido en el historial — se resolvio con squash

### Sesion 5 — 2026-04-14: Creacion de repositorio y flujo colaborativo
- **Objetivo:** Crear repo en GitHub para colaboracion con Yago
- **Prompts representativos:**
  - "me puedes poner aqui una explicacion de feature branches? es el standard?"
  - "Ponlo publico para poder invitar a colaborar a Yago"
- **Resultado:**
  - Repo publico creado: github.com/MarinasAlejandro/lasalle-hospital
  - Decision sobre estrategia de branches: feature branches (estandar industria)
  - Primer push realizado
- **Aciertos de la IA:** Explicacion comparativa clara entre opciones de branching

### Sesion 6 — 2026-04-14: Implementacion T1 (Infraestructura base)
- **Objetivo:** Levantar MongoDB + MinIO via Docker Compose
- **Prompts representativos:** "Arranca"
- **Resultado:**
  - `docker-compose.yml` con MongoDB 7 + MinIO (con healthchecks)
  - Script init-db.js para MongoDB (colecciones, indice unico en external_id)
  - Script init-buckets.sh para MinIO (buckets radiographies, raw-backups)
  - `.env` con configuracion
  - T1 marcada como completada, verificada manualmente
- **Aciertos de la IA:** Configuracion correcta al primer intento, healthchecks incluidos, variables externalizadas
- **Iteraciones:** Docker daemon no estaba arrancado al inicio, la IA detecto el error y pidio a Alejandro que lo iniciara

### Sesion 7 — 2026-04-20: Limpieza del docker-compose y .env
- **Objetivo:** Revisar la infraestructura T1 y eliminar redundancias/inconsistencias detectadas por Alejandro
- **Prompts representativos:**
  - "revisa que el docker-compose está bien, ya que noto que hay cosas que sobran"
  - "Yo habia visto la redundancia y lo que sobra, asi que arregla eso"
- **Resultado:**
  - Eliminada variable `MONGO_INITDB_DATABASE` del compose (redundante con `init-db.js`)
  - Eliminadas `MONGO_USER` y `MONGO_PASSWORD` de `.env` (no tenian consumidor, creaban impresion falsa de auth)
  - 2 lecciones anadidas a `tasks/lessons.md`
- **Casos donde hubo que corregir:**
  - La IA genero inicialmente un `.env` con credenciales "por si acaso" que nunca llego a cablear en el compose
  - La IA duplico la declaracion de base de datos en dos sitios sin necesidad
  - Al anadir la sesion 7 al diario, la IA la coloco ENCIMA de la sesion 6 rompiendo el orden cronologico. Alejandro tuvo que pedir explicitamente que se ordenara por dia
- **Leccion aprendida:** Al generar configuracion con IA, verificar que cada variable declarada tiene un consumidor real. La IA tiende a generar "por si acaso" mas de lo necesario. Ademas, al anadir entradas a documentos cronologicos (diario, changelog) hay que verificar que el orden se respeta — la IA puede insertar entradas nuevas en cualquier posicion si no se le indica
- **Aciertos de la IA:** Cuando Alejandro pidio revision, la IA detecto correctamente las redundancias y propuso soluciones concretas con trade-offs claros

### Sesion 8 — 2026-04-20: Implementacion T2 (PySpark + logging)
- **Objetivo:** Configurar PySpark dentro de un contenedor Docker + logging centralizado de la aplicacion
- **Prompts representativos:**
  - "Seguimos con t2"
- **Resultado:**
  - `src/pipeline/logging_config.py` — logging centralizado (formato, niveles, idempotencia)
  - `src/pipeline/spark_session.py` — factory de SparkSession con parametros configurables por env
  - `src/pipeline/scripts/verify_pyspark.py` — smoke test que corre al arrancar el contenedor
  - `Dockerfile.pipeline` — python:3.11-slim + default-jre-headless + PySpark 3.5.1
  - `requirements-pipeline.txt` con dependencias (pyspark, pymongo, minio, pytest)
  - `pyproject.toml` con configuracion de pytest (pythonpath, testpaths)
  - Servicio `pipeline` anadido al docker-compose (depends_on mongodb/minio healthy)
  - 9 tests unitarios pasan dentro del contenedor (5 logging + 4 Spark)
- **Aciertos de la IA:**
  - Arquitectura TDD aplicada: tests escritos antes del codigo
  - Deteccion temprana del problema Java/JRE en la imagen base de Python
  - Configuracion de PythonPath tanto en Docker (ENV) como en pytest (pyproject.toml)
- **Casos donde hubo que corregir:**
  - Primeros tests de logging fallaron porque inspeccionaban `root.handlers`/`root.level` — pytest-logging instala su propio handler en el root, interfiriendo con las aserciones. La IA rehizo los tests para asertar comportamiento observable (`caplog`, constantes)
  - El contenedor no reflejaba cambios del codigo tras editar tests — requiere `docker compose build pipeline` antes de re-ejecutar pytest
  - La IA VOLVIO a anadir la sesion 8 encima de la sesion 7 rompiendo el orden cronologico, a pesar de que esta leccion estaba documentada en `lessons.md`. Tuvo que rectificarse sola
- **Leccion aprendida:** En tests de infraestructura dentro de Docker, los cambios de codigo requieren rebuild explicito de la imagen. Alternativa futura: montar `src/` como volumen en modo dev. Ademas, tener una leccion documentada no garantiza que la IA la aplique — hay que verificar activamente el orden al editar documentos cronologicos

### Sesion 9 — 2026-04-20: Implementacion T3 (Generador de datos simulados)
- **Objetivo:** Crear script que genere CSVs sinteticos de pacientes e ingresos con datos clinicos realistas y casos borde
- **Prompts representativos:**
  - "Listo pues vamos a por la t3"
  - "Crees que seran suficientes casos? Para entrenar al modelo que queremos investiga"
- **Resultado:**
  - `src/pipeline/scripts/generate_data.py` con Faker (locale es_ES)
  - 5.000 pacientes + 10.000 ingresos con codigos ICD-10 reales, departamentos hospitalarios, distribuciones ponderadas de genero y grupo sanguineo
  - Casos borde intencionados (~5%): nulos en campos obligatorios, fechas DD/MM/YYYY en vez de ISO, duplicados (~3%), referencias huerfanas a pacientes inexistentes
  - Generacion determinista via `seed` para tests reproducibles
  - CLI con `argparse` (flags `--patients`, `--admissions`, `--output-dir`, `--edge-case-ratio`, `--seed`)
  - 7 tests unitarios anadidos. Total 16 tests pasando en contenedor
  - CSVs ejecutados y guardados en `data/raw/` (5.150 + 10.000 filas)
- **Aciertos de la IA:**
  - TDD correctamente aplicado: tests primero, codigo despues
  - Proactivamente investigo el tamaño real del dataset de Kaggle con WebSearch para responder a Alejandro sobre suficiencia de datos
  - Aclaro la confusion entre datos tabulares (CSVs con Faker) vs dataset de imagenes (Kaggle) que tienen proposito distinto
- **Casos donde hubo que corregir:**
  - Ninguno destacable en esta sesion

### Sesion 10 — 2026-04-20: Implementacion T4 (Storage layer)
- **Objetivo:** Implementar los wrappers de MinIO y MongoDB para que el pipeline pueda leer/escribir objetos y documentos
- **Prompts representativos:**
  - "Sigamos entonces"
- **Resultado:**
  - `src/pipeline/storage/minio_client.py` con operaciones clave sobre buckets y objetos
  - `src/pipeline/storage/mongo_writer.py` con upserts idempotentes, gestion de pipeline_runs y rejected_records
  - Factories `get_*_from_env` para centralizar la configuracion desde variables de entorno
  - 15 tests de integracion contra MongoDB y MinIO reales (total 31 tests pasando)
  - CB-4 cubierto via upsert por `external_id` (ejecutar dos veces el mismo input no crea duplicados)
- **Aciertos de la IA:**
  - Fixtures de pytest bien aisladas: DB `hospital_test_t4` y buckets con UUID para que los tests no contaminen datos de produccion
  - Uso correcto de `bulk_write` con `UpdateOne` para upserts eficientes
  - Separacion clara entre capa de acceso a datos (storage) y capa de orquestacion (proxima T9)
- **Casos donde hubo que corregir:**
  - Ninguno destacable en esta sesion — TDD funciono limpio
- **Leccion aprendida:** Los tests de integracion contra servicios Docker reales dan mayor confianza que los mocks, especialmente cuando se verifican comportamientos como idempotencia o bulk operations

### Sesion 11 — 2026-04-21: Implementacion T5 (Ingesta de CSVs)
- **Objetivo:** Implementar el CSVIngester que lee CSVs de pacientes e ingresos y los convierte a DataFrames PySpark validando columnas requeridas
- **Prompts representativos:**
  - "docker iniciado. Continuemos con t5"
- **Resultado:**
  - `src/pipeline/ingesters/csv_ingester.py` con `read_patients` y `read_admissions`
  - Deteccion de columnas faltantes con `MissingColumnsError` (CB-1)
  - Tolerancia a columnas en orden distinto
  - Preservacion de filas con casos borde (validacion fila a fila queda para T7)
  - Columna `_source_file` para trazabilidad
  - 9 tests unitarios anadidos (total 40 tests pasando)
  - Smoke test con los CSVs reales de T3 (5.150 patients + 10.000 admissions)
- **Aciertos de la IA:**
  - Separacion correcta de responsabilidades: ingester no filtra filas, solo valida estructura. La validacion fila a fila queda para T7
  - TDD aplicado limpio, 9 tests escritos antes del codigo
- **Casos donde hubo que corregir:**
  - 3 tests iniciales usaban `== set(PATIENT_SCHEMA_COLUMNS)` olvidando que el ingester anade `_source_file`. Cambiados a `issubset()` para expresar correctamente "al menos estas columnas"
- **Leccion aprendida:** En tests que verifican columnas de DataFrames, usar `issubset` en vez de `==` cuando el componente puede anadir columnas adicionales esperadas (como metadatos de trazabilidad)

### Sesion 12 — 2026-04-21: Implementacion T6 (Ingesta de imagenes)
- **Objetivo:** Implementar el ImageIngester que lee PNGs de radiografias, valida formato y los sube a MinIO con metadatos
- **Prompts representativos:**
  - "Ek enunciado del proyecto no comentaba como se tenia que hacer esto o alguna norma relacionada con esto?"
  - "Vamos con la C entonces"
- **Resultado:**
  - `src/pipeline/ingesters/image_ingester.py` con validacion de PNG signature y convencion de nombres
  - CB-2 cubierto: imagenes corruptas o con nombre invalido se omiten sin crashear
  - `src/pipeline/scripts/generate_dummy_images.py` para generar PNGs validos minimos (1x1 RGBA) sin dependencias externas
  - `docs/runbooks/download-radiography-dataset.md` con instrucciones para descargar el dataset real de Kaggle (~1GB) cuando toque entrenar el modelo
  - 7 tests de integracion contra MinIO real (total 47 tests pasando)
  - Smoke test con 17 PNGs dummy subidos correctamente a MinIO
- **Aciertos de la IA:**
  - Decision arquitectonica correcta de separar "PNGs dummy para tests" vs "dataset real para entrenar" — respeta el principio del enunciado de `docker compose up` sin dependencias externas
  - Uso de PNG signature bytes para validacion (no requiere librerias de imagenes como Pillow)
  - Object key con timestamp evita colisiones en re-ingestas del mismo fichero
- **Casos donde hubo que corregir:**
  - Ninguno destacable en esta sesion
- **Leccion aprendida:** Revisar el enunciado antes de tomar decisiones tecnicas ambiguas. Alejandro pregunto "¿el enunciado pide algo sobre esto?" y la revision confirmo que teniamos libertad total — pero tambien confirmo el requisito de "un solo comando" que influyo en la decision final

## Reflexion critica (en construccion)

### Que ha aportado la IA hasta ahora
- **Velocidad de planificacion:** Lo que llevaria dias de redaccion de specs y diseño se ha hecho en horas con calidad profesional
- **Trazabilidad:** La IA ha mantenido rigurosamente la trazabilidad requisito → componente → tarea → test
- **Deteccion de issues:** Capacidad de analisis multimodal + extraccion de texto para detectar contenido oculto en el enunciado
- **Generacion de scaffolding:** Estructura SDD completa con un solo comando

### Limitaciones encontradas
- **Lectura de PDFs:** Leer PDFs como imagenes no siempre detecta texto oculto. Hay que complementar con extraccion de texto plano
- **Auto-commits del hook:** Generan ruido en el historial y requieren squash manual periodico
- **Decisiones de negocio:** La IA propone opciones pero no decide por si sola — requiere input humano constante

### Estimacion de impacto en productividad (preliminar)
- **Tiempo ahorrado hasta ahora:** ~1 dia de planificacion completa (specs + designs + tasks + infra base)
- **Calidad del codigo:** Alta — sigue convenciones SDD, trazabilidad completa, commits semanticos
- **Trabajo humano requerido:** Decisiones de producto, aprobacion de fases, verificacion manual

## Ejemplos de prompts efectivos vs inefectivos

### Efectivos
- "Empecemos por el pipeline" — direccion clara
- "Apruebo" — permite a la IA avanzar sin bloqueos
- "Como lees tu los pdf?" — pregunta metacognitiva que desbloquea nuevo enfoque

### Inefectivos / Mejorables
- Preguntas muy amplias sin contexto (requieren re-preguntar)
- No especificar tamaños o alcances concretos
