/** Presentación escapada de expedientes; las reglas las decide el backend. */
export const $ = (id) => document.getElementById(id);
export const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const e = escapeHtml;
const labels = {
  INTAKE: "Intake",
  EVIDENCE_REVIEW: "Revisión de evidencia",
  OPTIONS_READY: "Opciones listas",
  PENDING_APPROVAL: "Pendiente de aprobación",
  APPROVED: "Aprobada",
  REJECTED: "Rechazada",
  PAUSED: "Pausada",
};
const record = (title, body) =>
  `<div class="record"><strong>${e(title)}</strong>${body}</div>`;
const paragraph = (value) => `<p>${e(value)}</p>`;
const small = (value) => `<small>${e(value)}</small>`;
const list = (id, values, renderer) => {
  $(id).innerHTML = values.length
    ? values.map(renderer).join("")
    : '<p class="empty">Sin registros todavía.</p>';
};
export function renderPortfolio(items, selected) {
  $("opportunity-list").innerHTML = items
    .map(
      (item) =>
        `<button class="case-button ${item.id === selected ? "selected" : ""}" data-case="${e(item.id)}">${e(item.title)}<small>${e(labels[item.stage])} · ${e(item.owner)}</small></button>`,
    )
    .join("");
}
function renderGuidance(brief) {
  const stage = brief.opportunity.stage;
  const instructions = {
    INTAKE: [
      "Revisar el origen de la señal",
      "Compruebe fuente y procedencia; después avance a revisión de evidencia.",
    ],
    EVIDENCE_REVIEW: [
      "Separar hechos, hipótesis e incógnitas",
      "Registre al menos una evidencia con fuente para pasar a opciones listas.",
    ],
    OPTIONS_READY: [
      "Comparar alternativas y redactar propuesta",
      "Debe haber 2–3 opciones y una propuesta con evidencia referenciada antes de pedir aprobación.",
    ],
    PENDING_APPROVAL: [
      "Revisión humana de la decisión",
      "El expediente está congelado. El revisor elige una opción y confirma con motivo; para corregir, pause el caso.",
    ],
    APPROVED: [
      "Planear y simular el siguiente paso interno",
      "La decisión ya está registrada. Puede simular una tarea pendiente; no se ejecuta nada fuera del sistema.",
    ],
    REJECTED: [
      "Decisión de no avanzar",
      "Caso cerrado. El historial se conserva; no hay ejecución externa.",
    ],
    PAUSED: [
      "Resolver lo pendiente y retomar la revisión",
      "Puede agregar información o versionar la propuesta. Luego vuelva a revisión de evidencia.",
    ],
  };
  const [title, detail] = instructions[stage];
  $("next-step").textContent = title;
  $("next-requirement").textContent = detail;
  const steps = [
    ["intake", "01 · Señal"],
    ["knowledge", "02 · Evidencia"],
    ["proposals", "03 · Propuesta"],
    ["decision", "04 · Decisión"],
    ["next-actions", "05 · Next action"],
    ["audit", "06 · Auditoría"],
  ];
  const active = {
    INTAKE: 0,
    EVIDENCE_REVIEW: 1,
    OPTIONS_READY: 2,
    PENDING_APPROVAL: 3,
    APPROVED: 4,
    REJECTED: 3,
    PAUSED: 1,
  }[stage];
  $("workflow").innerHTML = steps
    .map(
      ([id, title], i) =>
        `<a href="#${id}" class="${i === active ? "current" : ""}">${title}</a>`,
    )
    .join("");
  renderTransitionControls(brief);
}

/** Un cierre final conduce a seguimiento o auditoría, no a un selector vacío. */
function renderTransitionControls(brief) {
  const transitions = brief.allowed_transitions.filter((v) => v !== "APPROVED");
  const hasTransitions = transitions.length > 0;
  $("next-stage").innerHTML = transitions
    .map((v) => `<option value="${v}">${e(labels[v])}</option>`)
    .join("");
  $("transition-form").hidden = !hasTransitions;
  $("transition-form")
    .querySelectorAll("input, select, button")
    .forEach((control) => {
      control.disabled = !hasTransitions;
    });
  $("transition-complete").hidden = hasTransitions;
  if (hasTransitions) return;

  const approved = brief.opportunity.stage === "APPROVED";
  const rejected = brief.opportunity.stage === "REJECTED";
  $("transition-complete-title").textContent = approved
    ? "Decisión aprobada: continúa con el seguimiento interno"
    : rejected
      ? "Caso rechazado: decisión finalizada"
      : "Sin cambios de etapa disponibles";
  $("transition-complete-detail").textContent = approved
    ? "Ya no necesitas cambiar de etapa. Registra una siguiente acción con responsable y fecha, o simula una tarea pendiente. No se ejecuta nada externo."
    : "No hay otra transición disponible en este estado. Puedes consultar la decisión y su historial de auditoría.";
  $("transition-complete-link").href = approved ? "#next-actions" : "#audit";
  $("transition-complete-link").textContent = approved
    ? "Ir a las siguientes acciones internas →"
    : "Ver historial de auditoría →";
}
function references(id, items, name, field) {
  $(id).innerHTML =
    items
      .map(
        (item) =>
          `<label class="check"><input type="checkbox" name="${name}" value="${e(item.id)}">${e(item[field])} <small>${e(item.id)}</small></label>`,
      )
      .join("") || "<small>Sin registros.</small>";
}
export function renderBrief(brief, events, role) {
  $("opportunity-view").hidden = false;
  $("account-name").textContent = brief.account.name;
  $("opportunity-title").textContent = brief.opportunity.title;
  $("opportunity-owner").textContent =
    `Responsable: ${brief.opportunity.owner} · ID: ${brief.opportunity.id}`;
  $("stage-badge").textContent = labels[brief.opportunity.stage];
  $("last-movement").textContent = brief.last_movement
    ? `Último evento: ${brief.last_movement.event_type} · ${brief.last_movement.occurred_at}`
    : "Sin movimientos";
  $("confidence-badge").textContent =
    `Confianza media de evidencia: ${brief.confidence_summary.average} / 1 · informativa, no un score comercial`;
  renderGuidance(brief);
  list("signal-list", brief.signals, (s) =>
    record(
      s.title,
      small(`${s.id} · ${s.observed_at}`) +
        paragraph(s.source) +
        small(s.provenance),
    ),
  );
  list("contact-list", brief.contacts, (c) =>
    record(c.role, paragraph(c.display_name) + small(c.id)),
  );
  list("evidence-list", brief.evidence, (x) =>
    record(
      x.statement,
      `<span class="pill">${e(x.confidence_state)} · ${e(x.confidence)}</span>` +
        small(x.id) +
        paragraph(`Fuente: ${x.source}`) +
        small(x.provenance),
    ),
  );
  list("hypothesis-list", brief.hypotheses, (x) =>
    record(
      x.statement,
      paragraph(x.rationale) + small(`${x.id} · confianza ${x.confidence}`),
    ),
  );
  list("unknown-list", brief.unknowns, (x) =>
    record(x.question, small(`${x.id} · sin respuesta · confianza 0`)),
  );
  list("option-list", brief.options, (x) =>
    record(
      x.title,
      small(x.id) + paragraph(x.rationale) + small(`Riesgo: ${x.risk}`),
    ),
  );
  document.querySelectorAll(".option-select").forEach((select) => {
    select.innerHTML =
      '<option value="">Seleccione una alternativa</option>' +
      brief.options
        .map((o) => `<option value="${e(o.id)}">${e(o.title)}</option>`)
        .join("");
  });
  references(
    "evidence-references",
    brief.evidence,
    "evidence_ids",
    "statement",
  );
  references(
    "hypothesis-references",
    brief.hypotheses,
    "hypothesis_ids",
    "statement",
  );
  references("unknown-references", brief.unknowns, "unknown_ids", "question");
  const proposal = brief.proposal;
  $("proposal-result").innerHTML = proposal
    ? record(
        proposal.id,
        paragraph(proposal.rationale) +
          small(`Opción: ${proposal.option_id}`) +
          small(`Evidencia: ${proposal.evidence_ids.join(", ")}`) +
          small(
            `Hipótesis: ${proposal.hypothesis_ids.join(", ") || "Ninguna referenciada"}`,
          ) +
          small(
            `Incógnitas: ${proposal.unknown_ids.join(", ") || "Ninguna referenciada"}`,
          ) +
          small(
            `Autor: ${proposal.actor} · ${proposal.created_at} · versiones: ${brief.proposals.length}`,
          ),
      )
    : '<p class="empty">Aún no existe una propuesta revisable.</p>';
  $("decision-proposal").value = proposal?.id || "";
  // La confirmación no se hereda de una vista anterior o de otra revisión.
  $("decision-form").querySelector('[name="confirmed"]').checked = false;
  const decision = brief.decision;
  $("decision-result").innerHTML = decision
    ? record(
        "Aprobación humana persistida",
        paragraph(decision.rationale) +
          small(`Opción: ${decision.selected_option_id}`) +
          small(
            `Aprobador: ${decision.approval.actor} · ${decision.approval.approved_at}`,
          ) +
          small(`Propuesta revisada: ${decision.proposal_id}`),
      )
    : '<p class="empty">No hay decisión aprobada. Ningún borrador equivale a autorización.</p>';
  $("decision-form").querySelector("button").disabled =
    brief.opportunity.stage !== "PENDING_APPROVAL" || role !== "reviewer";
  list("action-list", brief.next_actions, (x) =>
    record(
      x.description,
      small(`${x.owner} · fecha: ${x.due_date} · ${x.status}`) +
        (x.status === "PENDING"
          ? `<div class="action-buttons"><button data-action-id="${e(x.id)}" data-status="SIMULATED">Simular</button><button data-action-id="${e(x.id)}" data-status="CANCELLED">Cancelar</button><button data-action-id="${e(x.id)}" data-status="BLOCKED">Bloquear</button></div>`
          : ""),
    ),
  );
  const draft = brief.ai_drafts.at(-1);
  $("ai-result").innerHTML = draft
    ? record(
        "Borrador local · no es una decisión",
        paragraph(draft.summary) +
          paragraph(draft.rationale) +
          small(
            `ID: ${draft.id} · opción sugerida: ${draft.recommended_option_id || "ninguna"}`,
          ) +
          small(draft.limitations.join(" ")),
      )
    : "";
  $("event-count").textContent = `${events.length} eventos`;
  $("audit-list").innerHTML = [...events]
    .reverse()
    .map(
      (ev) =>
        `<div class="audit-event ${ev.outcome === "REJECTED" ? "rejected" : ""}"><div><span class="pill">${e(ev.outcome)}</span>${small(ev.occurred_at)}${small(ev.actor)}</div><div><strong>${e(ev.event_type)}</strong>${paragraph(ev.detail)}${ev.previous_stage ? small(`${ev.previous_stage} → ${ev.next_stage}`) : ""}${small(ev.id)}</div></div>`,
    )
    .join("");
}
