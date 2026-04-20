# Lessons Learned - Sistema Inteligente de Soporte Hospitalario

## Patrones a evitar

| Fecha | Error | Causa raiz | Regla |
|-------|-------|-----------|-------|
| 2026-04-20 | Variables en `.env` que no se aplican en `docker-compose` (MONGO_USER/PASSWORD definidas pero MongoDB sin auth) | Generar configuracion sin verificar que cada variable tiene consumidor real | Regla: cada variable de `.env` debe tener al menos un consumidor en compose o codigo. Si no, o se usa o se elimina |
| 2026-04-20 | Redundancia entre `MONGO_INITDB_DATABASE` en compose y `db.getSiblingDB('hospital')` en script de init | Configuracion defensiva duplicando la misma informacion en dos sitios | Regla: una sola fuente de verdad. Si el script crea la DB, el compose no necesita declararla |
| 2026-04-20 | IA anadio entrada nueva al diario rompiendo el orden cronologico (sesion 7 encima de sesion 6) | La IA inserta contenido nuevo en la posicion que le parece relevante, no por fecha | Regla: al editar documentos cronologicos (diario, changelog, ADRs), verificar explicitamente que la nueva entrada va al final o en su posicion cronologica correcta |
| 2026-04-20 | IA uso tipo `refactor` en un commit que en realidad era limpieza de configuracion + documentacion | La IA no distingue con precision entre tipos de Conventional Commits cuando hay un mix de cambios | Regla: refactor = reestructurar codigo sin cambiar comportamiento. Limpieza de config o deps = `chore`. Cambios en docs/diarios/lecciones = `docs`. Si hay mix, priorizar el cambio dominante |
| 2026-04-20 | IA uso `refactor:` en el commit de migracion PostgreSQL → MongoDB cuando solo cambiaban archivos de documentacion (no habia codigo todavia) | Sin codigo implementado no puede haber refactor. Uso del tipo por inercia del lenguaje coloquial ("refactorizar la decision") | Regla: `refactor:` SOLO aplica cuando hay codigo que se reestructura sin cambiar comportamiento. Si solo cambian specs/design/decisions/README → `docs:` |

## Decisiones tomadas

| Fecha | Decision | Alternativas | Por que |
|-------|----------|-------------|---------|

## Cosas que funcionan
<!-- Patrones, librerias o enfoques que han dado buen resultado -->
