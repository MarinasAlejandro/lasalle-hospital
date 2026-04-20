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
| Pipeline de datos | PySpark |
| Deep Learning | PyTorch |
| BBDD NoSQL | MongoDB |
| Almacenamiento objetos | MinIO |
| Infraestructura | Docker + Docker Compose |

## Estructura del repositorio

```
├── specs/          # Especificaciones por feature (SDD)
├── design/         # Arquitectura por feature
├── decisions/      # ADRs (decisiones tecnicas)
├── tasks/          # Backlog y tareas
├── src/
│   ├── api/        # FastAPI — endpoints REST
│   ├── pipeline/   # Ingesta, limpieza, transformacion (PySpark)
│   ├── ml/         # Modelo clasificacion radiografias (PyTorch)
│   ├── dashboard/  # Visualizacion de resultados
│   └── automation/ # Alertas e informes automaticos
├── tests/          # Tests por modulo
├── data/           # Datos (no versionados)
├── notebooks/      # Exploracion y prototipado
└── docs/           # Diario de desarrollo con IA, runbooks
```

## Como ejecutar

> **TODO:** Instrucciones de ejecucion pendientes de implementar la infraestructura Docker.

## Metodologia

Desarrollo dirigido por especificacion (SDD). Cada feature pasa por: spec → design → tasks → implementacion → validacion.
