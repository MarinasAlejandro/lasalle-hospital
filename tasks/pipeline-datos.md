# Tasks: Pipeline de datos hospitalario

> Spec: specs/pipeline-datos.md
> Design: design/pipeline-datos.md

## Tareas

| # | Tarea | Requisitos | Dependencias | Tamano | Estado |
|---|-------|-----------|-------------|--------|--------|
| 1 | Infraestructura base: docker-compose con MongoDB + MinIO, indices y buckets iniciales | RNF-1 | — | M | done |
| 2 | Configuracion PySpark + logging centralizado: Dockerfile con PySpark, SparkSession factory, logging config | RNF-2, RNF-4 | T1 | S | done |
| 3 | Generador de datos simulados: script con Faker para CSVs de pacientes/ingresos con casos borde intencionados | Soporte | — | M | pending |
| 4 | Storage layer: MinIO client (subir/descargar objetos) + MongoWriter (upserts a colecciones) | RF-2, RF-5, CB-4 | T1 | M | pending |
| 5 | Ingesta de CSVs: CSVIngester lee CSVs a DataFrames PySpark, valida columnas esperadas | RF-1, CB-1 | T2 | S | pending |
| 6 | Ingesta de imagenes: ImageIngester lee PNGs, valida formato, sube a MinIO con metadatos | RF-2, CB-2 | T4 | S | pending |
| 7 | Validacion y limpieza PySpark: DataValidator (separa validos/rechazados) + DataCleaner (duplicados, nulos, formatos) | RF-3, CB-1, CB-3 | T5 | M | pending |
| 8 | Transformacion PySpark: DataTransformer (calculo edad, categorias diagnostico, agregaciones) | RF-4 | T7 | M | pending |
| 9 | Orquestador + watcher: PipelineOrchestrator (coordina flujo, registra runs) + FileWatcher (detecta ficheros nuevos) | RF-7, CB-4, CB-5 | T4, T5, T6, T7, T8 | M | pending |
| 10 | API REST: FastAPI endpoints para consultar datos + trigger manual del pipeline | RF-6 | T4, T9 | M | pending |
| 11 | Docker Compose completo: todos los servicios integrados, un comando para levantar. Actualizar README con instrucciones reales | RNF-1, CA-7 | T9, T10 | S | pending |
| 12 | Tests de integracion E2E: verificar criterios de aceptacion CA-1 a CA-8 | CA-1..CA-8 | T11 | M | pending |

Tamanos: S (< 1h) | M (1-4h) | L (> 4h, considerar dividir)
Estados: pending | in-progress | done | blocked

## Detalle por tarea

### T1: Infraestructura base
- `docker-compose.yml` con servicios mongodb y minio
- Script de inicializacion de MongoDB: crear DB `hospital`, colecciones e indices (unico en external_id)
- Script de inicializacion de buckets MinIO (radiographies, raw-backups)
- `.env` con variables de configuracion (puertos, credenciales)
- **Verificacion:** `docker-compose up` levanta mongodb y minio accesibles

### T2: Configuracion PySpark + logging
- `Dockerfile.pipeline` con python:3.11 + pyspark
- `src/pipeline/spark_session.py` — factory para crear SparkSession (standalone, configurable)
- `src/pipeline/logging_config.py` — logging con formato estandar, niveles por modulo
- **Verificacion:** SparkSession se crea correctamente dentro del contenedor

### T3: Generador de datos simulados
- `src/pipeline/scripts/generate_data.py` usando Faker
- Genera `patients.csv` (~5000 registros) y `admissions.csv` (~10000 registros)
- Incluye casos borde: ~5% nulos en campos obligatorios, ~3% duplicados, fechas mal formateadas
- Genera datos clinicos realistas: codigos ICD-10, departamentos hospitalarios, grupos sanguineos
- **Verificacion:** CSVs generados pasan revision manual de formato y variedad

### T4: Storage layer
- `src/pipeline/storage/minio_client.py` — upload, download, list, check_exists
- `src/pipeline/storage/mongo_writer.py` — upsert_patients (con admissions embebidas), upsert_radiography_metadata, write_rejected, write_pipeline_run
- Tests unitarios para ambos
- **Verificacion:** Tests pasan contra servicios Docker de T1

### T5: Ingesta de CSVs
- `src/pipeline/ingesters/csv_ingester.py` — lee CSV, detecta encoding, mapea columnas, retorna DataFrame PySpark
- Maneja CB-1: columnas faltantes o en orden distinto
- Tests unitarios con CSVs de ejemplo (validos + malformados)
- **Verificacion:** DataFrame correcto con CSVs buenos, error controlado con CSVs malos

### T6: Ingesta de imagenes
- `src/pipeline/ingesters/image_ingester.py` — lee directorio de PNGs, valida formato, extrae metadatos (tamano, nombre), sube a MinIO
- Maneja CB-2: imagenes corruptas o formato no soportado
- **Verificacion:** Imagenes validas aparecen en MinIO, corruptas se loguean sin crashear

### T7: Validacion y limpieza PySpark
- `src/pipeline/processors/data_validator.py` — reglas por tipo de entidad (patient, admission), separa validos/rechazados con motivo
- `src/pipeline/processors/data_cleaner.py` — dedup por external_id, normaliza nulos opcionales, estandariza formatos de fecha/nombre
- Tests unitarios con DataFrames que contienen casos borde
- **Verificacion:** Documentos invalidos van a rechazados con motivo, validos salen limpios

### T8: Transformacion PySpark
- `src/pipeline/processors/data_transformer.py` — calcula edad desde birth_date, mapea diagnosis_code a categorias, agrega metricas (ingresos por departamento/mes)
- Tests unitarios
- **Verificacion:** Campos enriquecidos presentes, agregaciones correctas

### T9: Orquestador + watcher
- `src/pipeline/orchestrator.py` — ejecuta secuencia completa (ingesta → validacion → limpieza → transformacion → carga), crea/actualiza pipeline_run, maneja errores globales
- `src/pipeline/watcher.py` — usa watchdog para monitorizar `data/incoming/`, mueve procesados a `data/incoming/processed/`
- Maneja CB-4 (idempotencia via upsert en MongoDB) y CB-5 (servicios no disponibles)
- **Verificacion:** Pipeline completo ejecuta sin errores con datos de T3

### T10: API REST
- `src/api/main.py` — app FastAPI
- `src/api/routers/data.py` — GET /patients, /admissions, /radiographies (paginados)
- `src/api/routers/pipeline.py` — POST /pipeline/trigger, GET /pipeline/status, GET /pipeline/runs
- `Dockerfile.api`
- **Verificacion:** Endpoints responden con datos de MongoDB, trigger dispara pipeline

### T11: Docker Compose completo
- Actualizar `docker-compose.yml` con TODOS los servicios: mongodb, minio, pipeline-worker, api
- Volumenes compartidos para `data/incoming/`
- Health checks, depends_on con condicion
- **Verificacion:** `docker-compose up` levanta todo, pipeline procesa datos, API responde

### T12: Tests de integracion E2E
- Tests que verifican cada criterio de aceptacion (CA-1 a CA-8)
- Script que ejecuta el flujo completo: genera datos → coloca en incoming → espera procesamiento → verifica resultados
- **Verificacion:** Todos los CA pasan green

## Grafo de dependencias

```
T1 (infra base)──────┬──→ T2 (PySpark) ──→ T5 (CSV ingester) ──→ T7 (validacion) ──→ T8 (transformacion)──┐
                     │                                                                                     │
                     └──→ T4 (storage) ──→ T6 (image ingester) ─────────────────────────────────────────────┤
                                                                                                           │
T3 (datos simulados) [independiente]                                                                       │
                                                                                                           ▼
                                                                                              T9 (orquestador + watcher)
                                                                                                           │
                                                                                                           ▼
                                                                                                   T10 (API REST)
                                                                                                           │
                                                                                                           ▼
                                                                                              T11 (Docker Compose)
                                                                                                           │
                                                                                                           ▼
                                                                                                 T12 (Tests E2E)
```

## Ruta critica
T1 → T2 → T5 → T7 → T8 → T9 → T10 → T11 → T12

T3 (generador de datos) y T4 (storage) pueden avanzarse en paralelo desde el principio.
