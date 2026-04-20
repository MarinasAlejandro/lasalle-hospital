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

### Changed
- PostgreSQL reemplazado por MongoDB (NoSQL) tras detectar texto oculto en el enunciado
- docker-compose y .env limpiados (variables sin consumidor eliminadas, redundancias eliminadas)

### Fixed
### Removed
- Variables `MONGO_USER` y `MONGO_PASSWORD` del `.env` (sin consumidor real)
- Variable `MONGO_INITDB_DATABASE` del compose (redundante con script de init)
