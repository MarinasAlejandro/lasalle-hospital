# ADR-002: MongoDB como base de datos principal en lugar de PostgreSQL

> Estado: accepted
> Fecha: 2026-04-14

## Contexto
El enunciado incluye texto oculto en la seccion de Entregables que indica "(NoSQL sobre todo)" junto a "Base de datos". Esto sugiere que el profesor espera una base de datos NoSQL como componente principal. Ademas, la seccion de pipeline mencionaba MongoDB como alternativa valida.

Los datos clinicos del hospital (pacientes, ingresos, radiografias metadata) tienen estructura semi-variable que encaja bien con documentos JSON.

## Decision
Usar **MongoDB** como base de datos principal para datos clinicos en lugar de PostgreSQL. MinIO se mantiene para almacenamiento de imagenes.

## Alternativas consideradas

| Opcion | Pros | Contras |
|--------|------|---------|
| MongoDB (elegida) | NoSQL como pide el enunciado, flexible para datos clinicos semi-estructurados, JSON nativo | Menos familiar para el equipo, no tiene joins nativos |
| PostgreSQL (descartada) | Familiar, ACID completo, SQL estandar | El enunciado sugiere NoSQL como preferencia |
| PostgreSQL + MongoDB (ambas) | Cubre ambos mundos | Complejidad innecesaria, dos BBDD que mantener |

## Consecuencias
- (+) Cumple con la preferencia del profesor (NoSQL)
- (+) Documentos JSON encajan bien con datos clinicos de estructura variable
- (+) Mas sencillo: una sola BBDD en vez de dos para datos estructurados
- (+) Mas facil de demostrar en la presentacion (datos consultables directamente como JSON)
- (-) Sin transacciones ACID tan robustas como PostgreSQL (aceptable para datos simulados)

## Requisitos relacionados
- RF-5: Persistencia de datos procesados
- Pipeline de datos a escala (almacenamiento)
