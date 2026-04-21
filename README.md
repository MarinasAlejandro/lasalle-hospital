# Sistema Inteligente de Soporte Hospitalario

Sistema de IA para el hospital **laSalle Health Center** que clasifica radiografias de torax, procesa datos clinicos a escala y automatiza procesos hospitalarios.

Proyecto final del Master en AI & Big Data.

## Equipo

- Alejandro Marinas
- Yago

## Stack

| Componente | Tecnologia |
|-----------|-----------|
| Pipeline de datos | PySpark 3.5.1 |
| BBDD NoSQL | MongoDB 7 |
| Almacenamiento de objetos | MinIO (S3-compatible) |
| Deep Learning | PyTorch *(en construccion)* |
| API | FastAPI *(en construccion)* |
| Dashboard | Streamlit *(en construccion)* |
| Infraestructura | Docker + Docker Compose |

## Requisitos previos

- Docker Desktop (o Docker Engine + Docker Compose v2)
- Puertos libres: `27017` (MongoDB), `9000` y `9001` (MinIO)

## Arranque

Clona el repositorio y ejecuta:

```bash
docker compose up
```

Con ese unico comando:

1. Se levantan **MongoDB** y **MinIO** con sus volumenes persistentes.
2. Se inicializa automaticamente la base de datos `hospital` (colecciones e indices).
3. Se crean los buckets de MinIO (`radiographies`, `raw-backups`).
4. El servicio `pipeline` ejecuta un bootstrap que **sube las radiografias de ejemplo** (incluidas en `data/raw/`) al bucket `radiographies` y verifica la conectividad con MongoDB.
5. Al terminar el bootstrap, `hospital-mongodb` y `hospital-minio` quedan corriendo y listos para usarse.

Cuando veas la linea `=== Bootstrap complete. System is ready. ===` el sistema esta listo.

### Como acceder al sistema

| Servicio | URL | Credenciales |
|---|---|---|
| MongoDB | `mongodb://localhost:27017` (BD: `hospital`) | sin auth (dev) |
| MinIO API | `http://localhost:9000` | `minioadmin` / `minioadmin123` |
| MinIO consola web | `http://localhost:9001` | `minioadmin` / `minioadmin123` |

## Ejecutar los tests

```bash
docker compose run --rm --entrypoint "" pipeline pytest tests/pipeline -v
```

## Detener el sistema

```bash
docker compose down        # Para los contenedores (conserva datos)
docker compose down -v     # Para y borra todos los datos
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
│   ├── api/            # FastAPI (pendiente)
│   ├── pipeline/       # Ingesta, limpieza, transformacion (PySpark)
│   ├── ml/             # Modelo clasificacion radiografias (pendiente)
│   ├── dashboard/      # Visualizacion (pendiente)
│   └── automation/     # Alertas e informes (pendiente)
├── tests/          # Tests por modulo
├── data/raw/       # Fixtures sinteticos (CSVs + PNGs de radiografias)
├── docker/         # Scripts de inicializacion de servicios
├── docker-compose.yml
└── Dockerfile.pipeline
```

## Datos incluidos en el repositorio

El directorio `data/raw/` contiene datos sinteticos generados con [Faker](https://faker.readthedocs.io) y commiteados al repo para que el arranque sea completamente reproducible y offline:

- `patients.csv`: 5.000 pacientes (con ~5% de casos borde: nulos, duplicados, fechas malformadas)
- `admissions.csv`: 10.000 ingresos (con referencias huerfanas intencionadas)
- `images/`: 17 PNGs dummy con la convencion `HOSP-NNNNNN_xrayN.png`

Para regenerar los datos:

```bash
docker compose run --rm --entrypoint "" pipeline python -m src.pipeline.scripts.generate_data --seed 42
docker compose run --rm --entrypoint "" pipeline python -m src.pipeline.scripts.generate_dummy_images --seed 42
```

El **dataset real** de radiografias (para entrenar el modelo ML) no esta en el repo por tamano. Ver `docs/runbooks/download-radiography-dataset.md`.

## Metodologia

Desarrollo dirigido por especificacion (SDD). Cada feature pasa por: `spec → design → tasks → implementacion → validacion`. Artefactos en `specs/` y `design/`. Backlog en `tasks/backlog.md`.

## Estado del proyecto

Progreso pipeline: **6/12 tareas completadas** (T1-T6). Ver `tasks/pipeline-datos.md`.
