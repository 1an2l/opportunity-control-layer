/** Traducción de formularios a comandos JSON; sin reglas de negocio. */
export function formPayload(form) {
  const data = new FormData(form);
  const payload = Object.fromEntries(data.entries());
  if (data.has("confidence"))
    payload.confidence = Number(data.get("confidence"));
  if (form.id === "proposal-form")
    for (const key of ["evidence_ids", "hypothesis_ids", "unknown_ids"])
      payload[key] = data.getAll(key);
  if (form.id === "decision-form")
    payload.confirmed = data.get("confirmed") === "on";
  if (form.dataset.endpoint && !payload.id)
    payload.id = `${form.dataset.endpoint.toUpperCase()}-${crypto.randomUUID()}`;
  return payload;
}
