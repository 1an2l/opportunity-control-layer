/** Cliente local: la clave vive sólo en memoria de esta pestaña. */
let token = "";
export function setToken(value) {
  token = value.trim();
}
export async function request(path, { method = "GET", body } = {}) {
  const headers = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body) headers["Content-Type"] = "application/json";
  const response = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  let payload;
  try {
    payload = JSON.parse(text);
  } catch {
    throw new Error(
      "La API no devolvió JSON. Inicie con python -m opportunity_control; no use Live Server.",
    );
  }
  if (!response.ok) {
    const error = new Error(
      `HTTP ${response.status}: ${payload.message || payload.error}`,
    );
    error.status = response.status;
    throw error;
  }
  return payload;
}
