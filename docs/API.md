# Contrato HTTP local

Base: `http://127.0.0.1:8000`. Escrituras con `Content-Type: application/json` y
`Authorization: Bearer <clave-local>`. El servidor asigna el actor; no enviarlo desde el cliente.

| Método | Ruta | Función |
|---|---|---|
| GET | /api/health | Estado y bloqueo externo |
| GET | /api/session | Identidad/rol actual, nunca tokens |
| GET / POST | /api/opportunities | Listar / crear intake |
| GET | /api/opportunities/{id}/brief | Expediente completo y transiciones disponibles |
| GET | /api/opportunities/{id}/events | Eventos ordenados por inserción |
| POST | /api/opportunities/{id}/signals | Señal con fuente/procedencia/fecha |
| POST | /api/opportunities/{id}/contacts | Rol sanitizado de la cuenta |
| POST | /api/opportunities/{id}/evidence | Evidencia y confianza |
| POST | /api/opportunities/{id}/hypotheses | Inferencia separada |
| POST | /api/opportunities/{id}/unknowns | Pregunta pendiente |
| POST | /api/opportunities/{id}/options | Alternativa, razón y riesgo |
| POST | /api/opportunities/{id}/proposals | Nueva versión de recomendación |
| POST | /api/opportunities/{id}/transitions | Transición no aprobatoria |
| POST | /api/opportunities/{id}/decisions | Decisión final explícita; sólo revisor |
| POST | /api/opportunities/{id}/next-actions | Plan interno con responsable/fecha |
| POST | /api/opportunities/{id}/action-status | Simular, cancelar o bloquear una tarea |
| POST | /api/opportunities/{id}/ai-draft | Borrador local persistido |
| POST | /api/opportunities/{id}/external-action | Bloqueo auditable, nunca ejecución |

## Ejemplos de cuerpos

Crear oportunidad:
```json
{"id":"OPP-LOCAL","account_id":"ACCOUNT-LOCAL","account_name":"Cuenta sanitizada","title":"Problema de prueba","owner":"analista"}
```

Evidencia (el servidor asigna fecha UTC si se omite):
```json
{"id":"EV-LOCAL","statement":"El fixture exige operación local","source":"data/SEED_SOURCES.md","provenance":"Lectura manual del fixture; no hecho comercial","confidence_state":"VERIFIED","confidence":1}
```

Propuesta: usar IDs existentes del mismo caso, no estos ejemplos si aún no se crearon.
```json
{"id":"PROP-LOCAL","option_id":"OPTION-1","rationale":"Evaluar internamente, sin contacto","evidence_ids":["EV-LOCAL"],"hypothesis_ids":[],"unknown_ids":[]}
```

Cambio de etapa:
```json
{"next_stage":"PENDING_APPROVAL"}
```

Rechazar requiere rol de revisor y `rationale` con el motivo; pausar permite incluirlo
de forma opcional. El motivo queda en el evento de transición.

Decisión después del gate:
```json
{"proposal_id":"PROP-LOCAL","option_id":"OPTION-1","rationale":"Fuentes y riesgos revisados; sólo trabajo interno","confirmed":true}
```

Next action y seguimiento:
```json
{"id":"ACTION-LOCAL","description":"Revisar supuestos con el fixture","owner":"analista","due_date":"2026-09-30"}
```
```json
{"id":"ACTION-LOCAL","status":"SIMULATED"}
```

## Respuestas

200 consulta/transición; 201 registro; 400 JSON/campos inválidos; 401 falta credencial;
403 permiso insuficiente o acción externa bloqueada; 404 ruta/objeto ausente; 405 método;
409 duplicado; 422 regla de dominio; 500 fallo interno sin detalles sensibles.
`APPROVED` por `transitions` devuelve 422: debe usarse `decisions`.
