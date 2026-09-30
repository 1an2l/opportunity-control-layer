# Matriz de aceptación — Evidence-to-Decision Vertical Slice

Alcance: versión local evaluable con tres fixtures. Esta matriz no asigna una puntuación
propia ni sustituye la aceptación técnica del evaluador.

| Criterio de Jeff | Evidencia en la entrega | Verificación |
|---|---|---|
| Data model (15) | Cuenta, contacto, señal, oportunidad, conocimiento, propuesta, decisión, next action | test_domain; test_repository; test_vertical_slice |
| Backend/API (15) | HTTP JSON, validación, persistencia y errores estables | test_api; test_server |
| UI/workflow (10) | Intake, referencias, opciones, propuesta, aprobación, brief y seguimiento | tests/browser_check.py |
| AI/agent boundaries (15) | Simulador declarado, sin LLM ni herramientas; borrador persistido y sin autoridad | test_ai_draft_is_persisted_and_never_approves |
| Human approval + auditability (15) | Clave de revisor, confirmación explícita, motivo, opción, historial append-only | test_server; test_approval_requires_literal_true_and_reason |
| Tests/reliability (15) | Duplicados, incompletos, transiciones inválidas, permisos, rollback/reintento | test_vertical_slice; test_services; test_repository |
| Architecture (10) | Diagrama ampliado de componentes y ramas sí/no | ARQUITECTURA.svg y ARQUITECTURA.md |
| Clarity/documentation (5) | README, contrato API, fuentes, límites, decisiones técnicas y deck | docs/; deliverables/ |

## Pruebas de aceptación prioritarias

- `test_complete_slice_all_three_cases`: recorre los tres casos hasta decisión, simula una tarea y confirma bloqueo externo.
- `test_final_audit_failure_rolls_back_decision_approval_and_stage`: inyecta una falla final, comprueba rollback y reintento.
- `test_editor_cannot_approve_even_using_encoded_route`: un editor no eleva permisos por cuerpo ni ruta codificada.
- `test_identity_is_taken_from_credential_not_body`: la identidad no se obtiene de texto ingresado por el cliente.
- `test_proposal_requires_references_from_same_case`: no mezcla evidencia entre cuentas.
- `test_frozen_case_cannot_change_evidence`: exige pausa antes de corregir un expediente en revisión final.
- `test_direct_approved_transition_cannot_bypass_decision`: no hay atajo de estado que evite registrar la decisión.
- `tests/browser_check.py`: recorrido con navegador real, decisión distinta de la propuesta, auditoría y ancho móvil.

Ejecutar `python -m unittest discover -v`. Los resultados deben obtenerse de la copia que
se entregue; un test exitoso no equivale a certificación de seguridad productiva.

## Pendientes externos y de handoff

- Dataset sanitizado y canal/repositorio controlado, aún no entregados en la conversación disponible.
- Confirmación sobre alcance esperado de IA de sandbox. El producto actual no llama a un LLM.
- Demo de 5–10 minutos de esta nueva versión: debe grabarse o presentarse en vivo. El video del case inicial no demuestra esta implementación.
- Validación técnica del evaluador, revisión de dependencias y aceptación formal.

El deck acompaña la ejecución; no reemplaza una demo funcional ni el video pendiente.
La entrega debe describirse como **vertical slice local para revisión**, no como producto
con datos reales integrado a producción ni como sprint formalmente aceptado.
