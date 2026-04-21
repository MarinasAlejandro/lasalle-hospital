# Changelog

Todas las entregas notables de este proyecto, en orden cronologico inverso.
Formato basado en [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Estructura inicial del proyecto SDD (specs, design, tasks, decisions, docs)
- Backlog con features identificadas del enunciado
- Spec, design y tasks aprobados del pipeline de datos (12 tareas)
- ADR-001: Decision de stack tecnologico (PySpark + PyTorch + FastAPI)
- ADR-002: MongoDB como BBDD principal (en lugar de PostgreSQL)
- Repositorio en GitHub (publico): MarinasAlejandro/lasalle-hospital
- Diario de desarrollo con IA (docs/diario-ia.md)
- **T1 (Infraestructura base):** docker-compose.yml con MongoDB 7 + MinIO funcionando
  - Script de inicializacion de MongoDB (DB hospital, colecciones, indices)
  - Script de inicializacion de buckets MinIO
  - Variables de entorno en .env
- **T2 (Configuracion PySpark + logging):**
  - `src/pipeline/logging_config.py` — logging centralizado con formato estandar
  - `src/pipeline/spark_session.py` — factory de SparkSession configurable por env
  - `src/pipeline/scripts/verify_pyspark.py` — smoke test del contenedor
  - `Dockerfile.pipeline` con python:3.11-slim + default-jre-headless + PySpark 3.5.1
  - `pyproject.toml` con configuracion de pytest (pythonpath, testpaths)
  - Servicio `pipeline` en docker-compose con depends_on condicionales
  - 9 tests unitarios pasando dentro del contenedor (5 logging + 4 Spark)
- **T3 (Generador de datos simulados):**
  - `src/pipeline/scripts/generate_data.py` con Faker (es_ES)
  - CSVs realistas: 5.000 pacientes + 10.000 ingresos, codigos ICD-10, departamentos hospitalarios
  - Casos borde intencionados: nulos (~5%), duplicados (~3%), fechas malformadas, huerfanos
  - Generacion determinista con seed para tests reproducibles
  - 7 tests unitarios anadidos (total 16 tests pasando)
- **T4 (Storage layer):**
  - `src/pipeline/storage/minio_client.py` — wrapper sobre minio-py (ensure_bucket, upload_file/bytes, download_file, exists, list_objects, remove_object)
  - `src/pipeline/storage/mongo_writer.py` — wrapper sobre pymongo (bulk_upsert_patients idempotente, add_radiography_to_patient, start/finish_pipeline_run, write_rejected)
  - Factories `get_minio_client_from_env` y `get_mongo_writer_from_env` que leen variables del entorno
  - 15 tests de integracion contra MongoDB y MinIO reales (total 31 tests pasando dentro del contenedor)
- **T5 (Ingesta de CSVs):**
  - `src/pipeline/ingesters/csv_ingester.py` — lee CSVs a DataFrames PySpark
  - Valida que existan las columnas requeridas (levanta `MissingColumnsError` en caso contrario)
  - Acepta columnas en cualquier orden, preserva todas las filas (incluidas las con casos borde — la validacion fila a fila queda para T7)
  - Anade columna `_source_file` para trazabilidad
  - 9 tests unitarios con CSVs temporales (total 40 tests pasando)
  - Smoke test con los 5.150 + 10.000 CSVs reales de T3 verificado
- **T6 (Ingesta de imagenes):**
  - `src/pipeline/ingesters/image_ingester.py` — lee PNGs, valida signature PNG, sube a MinIO con metadatos
  - Convencion de nombres `{patient_external_id}_{suffix}.png` (ej. `HOSP-000001_xray1.png`)
  - CB-2 cubierto: imagenes corruptas/invalidas se loguean y omiten sin crashear
  - Object key unico por imagen: `{patient_id}/{timestamp}_{filename}.png`
  - `src/pipeline/scripts/generate_dummy_images.py` para generar PNGs validos minimos para tests y demos
  - `docs/runbooks/download-radiography-dataset.md` con instrucciones para descargar el dataset real de Kaggle cuando se entrene el modelo
  - 7 tests de integracion contra MinIO real (total 47 tests pasando)
  - Smoke test con 17 PNGs dummy subidos a MinIO verificado
- **Arranque con un unico comando (`docker compose up`):**
  - `src/pipeline/scripts/bootstrap.py` corre al arrancar el servicio pipeline: verifica fixtures en `data/raw/`, sube radiografias a MinIO y comprueba conectividad con MongoDB (idempotente)
  - Dockerfile.pipeline con CMD `bootstrap` en lugar de `verify_pyspark`
  - Servicio `pipeline` en docker-compose con `restart: "no"`, `depends_on` condicional a `minio-init` completo y volumen `./data:/app/data:ro`
  - `data/raw/patients.csv`, `data/raw/admissions.csv` y 17 PNGs dummy committeados al repo (~1MB) para arranque offline, determinista y reproducible
- **Configuracion portable sin `.env`:**
  - Todas las variables del docker-compose con defaults (`${VAR:-default}`). Arranca en cualquier maquina sin crear `.env`
  - `.env.example` committeado como referencia opcional
- **Tests con skip limpio:**
  - `tests/pipeline/conftest.py` con hook que detecta disponibilidad de MongoDB/MinIO por TCP y hace skip de los tests de integracion cuando no estan accesibles (evita `KeyError` y errores de setup)
- **T7 (Validacion y limpieza PySpark):**
  - `src/pipeline/processors/data_validator.py` con `DataValidator`: separa filas validas de rechazadas con motivo (`rejection_reason`). Reglas first-failure-wins
  - Validacion de pacientes: external_id `HOSP-NNNNNN`, name no vacio, birth_date ISO, gender M/F/Other, blood_type en set valido
  - Validacion de ingresos: patient_external_id, admission_date ISO, department no vacio, status admitted/discharged/transferred
  - `src/pipeline/processors/data_cleaner.py` con `DataCleaner`: trim whitespace y dedup por external_id (pacientes) o por (patient_external_id, admission_date, department) (ingresos)
  - 13 tests unitarios con schemas PySpark explicitos (total 67 tests pasando)
  - Smoke test contra datos reales: 5.150 patients -> 4.957 validos + 193 rechazados (121 fecha mala, 72 nombre vacio), dedup a 4.813. 10.000 admissions -> 9.507 validos + 493 rechazados

### Changed
- PostgreSQL reemplazado por MongoDB (NoSQL) tras detectar texto oculto en el enunciado
- docker-compose y .env limpiados (variables sin consumidor eliminadas, redundancias eliminadas)

### Fixed
### Removed
- Variables `MONGO_USER` y `MONGO_PASSWORD` del `.env` (sin consumidor real)
- Variable `MONGO_INITDB_DATABASE` del compose (redundante con script de init)
