# Sistema Inteligente de Soporte Hospitalario

Sistema de IA para el hospital **laSalle Health Center** que clasifica radiografias de torax, procesa datos clinicos a escala y automatiza procesos hospitalarios.

Proyecto final del Master en AI & Big Data.

## Equipo

- Alejandro Marinas
- Yago

## Stack

| Componente | Tecnologia |
|-----------|-----------|
| API | FastAPI |
| Pipeline de datos | PySpark 3.5.1 |
| Deep Learning | PyTorch |
| BBDD NoSQL | MongoDB 7 |
| Almacenamiento objetos | MinIO (S3-compatible) |
| Infraestructura | Docker + Docker Compose |

## Requisitos previos

- **Docker Desktop** (o Docker Engine + Docker Compose v2)
- **~8 GB RAM** libres para los contenedores (PySpark necesita JVM)
- Puertos libres: `27017` (MongoDB), `9000` y `9001` (MinIO), `8000` (API — futura)

## Arranque rapido

Clonar el repositorio y arrancar todo con un solo comando:

```bash
git clone https://github.com/MarinasAlejandro/lasalle-hospital.git
cd lasalle-hospital
docker compose up -d
```

Esto levanta:
- **MongoDB** en `localhost:27017` (BD `hospital` inicializada con colecciones e indices)
- **MinIO** en `localhost:9000` (API S3) y `localhost:9001` (consola web — user `minioadmin` / pass `minioadmin123`)
- **MinIO init**: job one-shot que crea los buckets `radiographies` y `raw-backups`
- **Pipeline worker**: imagen con PySpark + Python 3.11 lista para ejecutar scripts

Verificar que los servicios estan healthy:

```bash
docker compose ps
```

## Ejecutar el pipeline (estado actual)

El pipeline esta en construccion. Lo implementado hasta ahora:

### 1. Generar datos sinteticos

```bash
# 5.000 pacientes + 10.000 ingresos (CSVs en data/raw/)
docker compose run --rm --entrypoint "" \
  -v "$(pwd)/data:/app/data" \
  pipeline python -m src.pipeline.scripts.generate_data --seed 42

# 20 pacientes con PNGs dummy (imagenes en data/raw/images/)
docker compose run --rm --entrypoint "" \
  -v "$(pwd)/data:/app/data" \
  pipeline python -m src.pipeline.scripts.generate_dummy_images --seed 42
```

### 2. Ejecutar los tests

```bash
docker compose run --rm --entrypoint "" pipeline pytest tests/pipeline -v
```

Los 47 tests (unitarios + integracion contra MongoDB y MinIO reales) deben pasar.

### 3. Dataset real de radiografias

Para entrenar el modelo de clasificacion se usa el [COVID-19 Radiography Database de Kaggle](https://www.kaggle.com/datasets/tawsifurrahman/covid19-radiography-database). Ver instrucciones en:

```
docs/runbooks/download-radiography-dataset.md
```

## Detener el sistema

```bash
docker compose down          # Para los contenedores (conserva datos)
docker compose down -v       # Para y BORRA todos los datos
```

## Estructura del repositorio

```
├── specs/          # Especificaciones por feature (SDD)
├── design/         # Arquitectura por feature
├── decisions/      # ADRs (decisiones tecnicas)
├── tasks/          # Backlog y tareas
├── docs/
│   ├── diario-ia.md    # Diario de desarrollo con IA (entregable obligatorio)
│   └── runbooks/       # Guias operativas
├── src/
│   ├── api/            # FastAPI — endpoints REST (pendiente)
│   ├── pipeline/       # Ingesta, limpieza, transformacion (PySpark)
│   ├── ml/             # Modelo clasificacion radiografias (pendiente)
│   ├── dashboard/      # Visualizacion de resultados (pendiente)
│   └── automation/     # Alertas e informes automaticos (pendiente)
├── tests/          # Tests por modulo
├── data/           # Datos (no versionados)
├── docker/         # Scripts de inicializacion de servicios
├── docker-compose.yml
├── Dockerfile.pipeline
└── requirements-pipeline.txt
```

## Estado del proyecto

Ver `tasks/backlog.md` para el roadmap completo y `tasks/pipeline-datos.md` para el detalle del pipeline.

**Progreso pipeline:** 6/12 tareas completadas (T1-T6).

## Metodologia

Desarrollo dirigido por especificacion (SDD). Cada feature pasa por: spec → design → tasks → implementacion → validacion. Ver `specs/` y `design/` para los artefactos aprobados.

## Configuracion

Las variables de entorno estan en `.env` (incluido en el repo con credenciales de desarrollo):

| Variable | Descripcion | Default |
|---|---|---|
| `MONGO_HOST` | Host de MongoDB | `mongodb` |
| `MONGO_PORT` | Puerto de MongoDB | `27017` |
| `MONGO_DB` | Nombre de la base de datos | `hospital` |
| `MINIO_HOST` | Host de MinIO | `minio` |
| `MINIO_PORT` | Puerto de la API S3 | `9000` |
| `MINIO_CONSOLE_PORT` | Puerto de la consola web | `9001` |
| `MINIO_ROOT_USER` | Usuario admin de MinIO | `minioadmin` |
| `MINIO_ROOT_PASSWORD` | Password admin de MinIO | `minioadmin123` |
| `MINIO_BUCKET_RADIOGRAPHIES` | Bucket para radiografias | `radiographies` |
| `MINIO_BUCKET_RAW_BACKUPS` | Bucket para backups raw | `raw-backups` |
