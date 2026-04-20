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

### Changed
- PostgreSQL reemplazado por MongoDB (NoSQL) tras detectar texto oculto en el enunciado
- docker-compose y .env limpiados (variables sin consumidor eliminadas, redundancias eliminadas)

### Fixed
### Removed
- Variables `MONGO_USER` y `MONGO_PASSWORD` del `.env` (sin consumidor real)
- Variable `MONGO_INITDB_DATABASE` del compose (redundante con script de init)
