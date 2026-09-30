/** Orquestación de pantalla; ninguna operación escribe fuera de la API local. */
import { request, setToken } from "./api-client.js";
import { $, renderBrief, renderPortfolio } from "./render.js";
import { formPayload } from "./forms.js";
let selected = null,
  brief = null,
  role = "reader",
  generation = 0,
  busy = false;
const notice = (message, error = false) => {
  $("notice").textContent = message;
  $("notice").classList.toggle("error", error);
};
async function refresh() {
  const turn = ++generation;
  const items = await request("/api/opportunities");
  if (turn !== generation) return;
  if (!selected || !items.some((item) => item.id === selected))
    selected = items[0]?.id;
  renderPortfolio(items, selected);
  if (!selected) {
    $("opportunity-view").hidden = true;
    return;
  }
  const id = selected;
  const [next, events] = await Promise.all([
    request(`/api/opportunities/${encodeURIComponent(id)}/brief`),
    request(`/api/opportunities/${encodeURIComponent(id)}/events`),
  ]);
  if (turn !== generation || id !== selected) return;
  brief = next;
  renderBrief(next, events, role);
}
async function mutate(endpoint, body, form = null, global = false) {
  if (busy) return;
  busy = true;
  const id = selected;
  notice("Validando y guardando la operación…");
  try {
    const path = global
      ? "/api/opportunities"
      : `/api/opportunities/${encodeURIComponent(id)}/${endpoint}`;
    const result = await request(path, { method: "POST", body });
    if (global) selected = result.opportunity.id;
    if (form) form.reset();
    await refresh();
    notice("Operación registrada. El historial y el brief están actualizados.");
  } catch (error) {
    try {
      await refresh();
    } catch {
      /* Conservar el error original si también falla la lectura. */
    }
    notice(error.message, true);
  } finally {
    busy = false;
  }
}
$("opportunity-list").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-case]");
  if (!button || busy) return;
  selected = button.dataset.case;
  // No transportar un motivo de decisión escrito para otra cuenta.
  document
    .querySelectorAll("#opportunity-view form")
    .forEach((form) => form.reset());
  try {
    await refresh();
    notice("Expediente cargado.");
  } catch (error) {
    notice(error.message, true);
  }
});
$("session-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  setToken($("session-key").value);
  try {
    const session = await request("/api/session");
    role = session.role;
    $("session-label").textContent = `${session.actor} · ${session.role}`;
    $("session-key").value = "";
    await refresh();
    notice(
      role === "reader"
        ? "Clave no válida: permanece en modo lectura."
        : "Permisos locales activados.",
      role === "reader",
    );
  } catch (error) {
    notice(error.message, true);
  }
});
document.querySelectorAll("form[data-endpoint]").forEach((form) =>
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const payload = formPayload(form);
    mutate(
      form.dataset.endpoint,
      payload,
      form,
      form.dataset.global === "true",
    );
  }),
);
$("transition-form").addEventListener("submit", (event) => {
  event.preventDefault();
  if ($("next-stage").disabled || !$("next-stage").value) return;
  mutate("transitions", formPayload(event.currentTarget));
});
$("decision-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  mutate("decisions", formPayload(form), form);
});
$("action-list").addEventListener("click", (event) => {
  const button = event.target.closest("[data-action-id]");
  if (button)
    mutate("action-status", {
      id: button.dataset.actionId,
      status: button.dataset.status,
    });
});
$("ai-button").addEventListener("click", () => mutate("ai-draft", {}));
$("external-action-button").addEventListener("click", () =>
  mutate("external-action", {
    description: "Comprobación local del bloqueo: no hay llamada externa",
  }),
);
$("refresh-button").addEventListener("click", () =>
  refresh()
    .then(() => notice("Datos actualizados."))
    .catch((error) => notice(error.message, true)),
);
$("export-button").addEventListener("click", () => {
  if (!brief) return;
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(brief, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = `brief-${brief.opportunity.id}.json`;
  link.click();
  URL.revokeObjectURL(url);
});
refresh()
  .then(() =>
    notice(
      "Seleccione un caso. Para editar, active una clave local desde la terminal.",
    ),
  )
  .catch((error) => notice(error.message, true));
