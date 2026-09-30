# Casos de uso y transacciones

`application/services.py` coordina contenido y etapas. `application/workflow.py`
coordina intake, propuestas, decisiones y seguimiento. Ambos usan el mismo puerto,
reloj y conexión transaccional.

| Operación | Validación principal | Efecto atómico |
|---|---|---|
| Crear oportunidad | Cuenta consistente, owner, etapa INTAKE | Cuenta si falta + oportunidad + evento |
| Capturar señal | Cuenta correcta, fuente, procedencia y fecha no futura | Señal + evento |
| Registrar evidencia | Campos, confianza válida y duplicado por afirmación/fuente | Evidencia + evento |
| Guardar propuesta | Opción y referencias del mismo caso | Nueva versión + evento |
| Solicitar gate | 2–3 opciones y propuesta | Etapa + evento |
| Decidir | Revisor HTTP, confirmación literal, opción, motivo y propuesta vigente | Aprobación + decisión + etapa + eventos |
| Simular tarea | Decisión aprobada y tarea pendiente del mismo caso | Estado SIMULATED + evento |
| Acción externa | Prohibida incluso aprobada | Evento de bloqueo; HTTP 403 |

`BEGIN IMMEDIATE` protege la lectura-validación-escritura de transiciones. Una transacción
anidada usa SAVEPOINT: si falla, revierte su propio trabajo; si falla la transacción exterior,
todo se revierte. Una falla de auditoría impide confirmar la decisión.

Las solicitudes rechazadas asociables a una oportunidad se registran después del rollback.
JSON ilegible, rutas inexistentes y rechazos de Host/Origin ocurren antes de conocer un
comando de dominio válido; no se presentan como eventos de una oportunidad.

No hay ejecución de instrucciones almacenadas en textos: son datos para revisión, nunca
comandos de correo, red o sistema.
