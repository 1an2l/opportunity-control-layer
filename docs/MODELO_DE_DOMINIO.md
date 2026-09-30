# Modelo de dominio

| Pieza | Responsabilidad | Archivo |
|---|---|---|
| Account / Contact | Organización y rol sanitizado; no canal de contacto | `domain/accounts.py` |
| Signal / Opportunity | Movimiento observado y problema que se evaluará | `domain/opportunities.py` |
| Evidence | Afirmación, fuente, procedencia, confianza y fecha | `domain/knowledge.py` |
| Hypothesis / Unknown | Inferencia con fundamento / pregunta pendiente | `domain/knowledge.py` |
| DecisionOption | Alternativa, razón y riesgo | `domain/decisions.py` |
| Proposal | Versión de recomendación con IDs de evidencia, hipótesis e incógnitas | `domain/proposals.py` |
| Decision / Approval | Opción final, motivo, propuesta revisada, persona y fecha | `domain/decisions.py` |
| NextAction | Paso interno con owner, fecha y estado | `domain/actions.py` |
| AuditEvent | Quién, qué, cuándo, resultado y transición | `domain/audit.py` |

`Recommendation` es el valor básico de una sugerencia. La persistencia usa `Proposal`,
que agrega identidad, versión y referencias exigidas por el flujo auditable.

## Confianza

- `VERIFIED`: afirmación comprobada por una persona frente a la fuente indicada.
- `INFERRED`: interpretación, no hecho confirmado.
- `UNKNOWN`: información no comprobada, confianza numérica cero.
- Las hipótesis sólo son `INFERRED`; las incógnitas sólo `UNKNOWN`.

La media mostrada es `suma de confianza / cantidad de evidencias`. Se escogió como
resumen descriptivo transparente, no como fórmula de priorización. No permite aprobar,
no mide conversión comercial y no compensa evidencia faltante.

## Etapas

`INTAKE → EVIDENCE_REVIEW → OPTIONS_READY → PENDING_APPROVAL → APPROVED`.

Revisión y opciones también permiten `PAUSED`; pendiente de aprobación permite
`PAUSED` o `REJECTED`. Una pausa vuelve a revisión. Aprobado y rechazado son finales.

Preparar opciones requiere evidencia. Pedir aprobación requiere 2–3 alternativas y una
propuesta trazable. La aplicación congela señales/evidencia/hipótesis/incógnitas/opciones/
propuestas en pendiente y estados finales. Una corrección necesita pausa explícita.

La decisión puede elegir una alternativa distinta de la recomendada, pero debe registrar
su motivo. Aprobar no elimina riesgos ni incógnitas; éstos siguen visibles en el brief.
