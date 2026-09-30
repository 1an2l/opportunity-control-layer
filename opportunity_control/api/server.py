"""Servidor HTTP estándar que publica API y archivos de la interfaz."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

from .access import LocalAccess
from .app import ApiApplication, ApiResponse

WEB_ROOT = Path(__file__).resolve().parents[2] / "web"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}
for module in ("api-client.js", "render.js", "forms.js"):
    STATIC_FILES[f"/{module}"] = (module, "text/javascript; charset=utf-8")


def make_handler(
    application: ApiApplication, access: LocalAccess | None = None
) -> type[BaseHTTPRequestHandler]:
    """Crea un handler ligado a una instancia de aplicación."""

    access = access or LocalAccess()

    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            """Sirve recursos estáticos o una consulta de API."""

            if self.path.split("?", 1)[0] in STATIC_FILES:
                self._serve_static()
                return
            self._serve_api("GET")

        def do_POST(self) -> None:
            """Procesa una solicitud JSON de escritura."""

            self._serve_api("POST")

        def _serve_static(self) -> None:
            path = self.path.split("?", 1)[0]
            filename, content_type = STATIC_FILES[path]
            file_path = WEB_ROOT / filename
            if not file_path.is_file():
                self.send_error(404)
                return
            content = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def _serve_api(self, method: str) -> None:
            # Restringir Host también impide que un DNS externo apunte al servidor local.
            host = self.headers.get("Host", "").split(":")[0]
            if host not in {"127.0.0.1", "localhost"}:
                self._write_response(
                    ApiResponse(
                        403, {"error": "invalid_host", "message": "Sólo localhost"}
                    )
                )
                return
            try:
                body = self._read_json() if method == "POST" else None
            except (json.JSONDecodeError, ValueError, TypeError):
                self._write_response(
                    ApiResponse(
                        400,
                        {
                            "error": "invalid_json",
                            "message": "El cuerpo debe ser un objeto JSON válido.",
                        },
                    )
                )
                return
            path = urlparse(self.path).path.rstrip("/")
            principal = access.resolve(self.headers.get("Authorization", ""))
            if method == "GET" and path == "/api/session":
                self._write_response(
                    ApiResponse(
                        200,
                        {
                            "actor": principal.actor if principal else "lector-local",
                            "role": principal.role if principal else "reader",
                        },
                    )
                )
                return
            if method == "POST":
                origin = self.headers.get("Origin")
                if origin and origin != f"http://{self.headers.get('Host')}":
                    self._write_response(
                        ApiResponse(
                            403,
                            {
                                "error": "invalid_origin",
                                "message": "Origen no permitido",
                            },
                        )
                    )
                    return
                if principal is None:
                    application._audit_rejection(
                        method,
                        path,
                        {"actor": "unauthenticated-local-request"},
                        "credencial ausente o inválida",
                    )
                    self._write_response(
                        ApiResponse(
                            401,
                            {
                                "error": "unauthorized",
                                "message": "Ingrese una clave local de edición o revisión",
                            },
                        )
                    )
                    return
                body["actor"] = principal.actor
                if not access.can_write(principal, path, body):
                    application._audit_rejection(
                        method, path, body, "el rol editor no puede decidir"
                    )
                    self._write_response(
                        ApiResponse(
                            403,
                            {
                                "error": "forbidden",
                                "message": "La decisión requiere clave de revisor",
                            },
                        )
                    )
                    return
            self._write_response(application.handle(method, self.path, body))

        def _read_json(self) -> dict[str, object]:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 262144:
                raise ValueError("tamaño JSON fuera de límites")
            if self.headers.get_content_type() != "application/json":
                raise ValueError("se requiere application/json")
            if length <= 0:
                return {}
            value = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(value, dict):
                raise TypeError("JSON must be an object")
            return cast(dict[str, object], value)

        def _write_response(self, response: ApiResponse) -> None:
            content = json.dumps(
                response.payload,
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(response.status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, format: str, *args: object) -> None:
            """Conserva una línea simple de diagnóstico HTTP local."""

            print(f"HTTP {self.address_string()} - {format % args}")

    return RequestHandler


def run_server(
    application: ApiApplication,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    access: LocalAccess | None = None,
) -> None:
    """Inicia un servidor local de un solo proceso sin efectos externos."""

    access = access or LocalAccess()
    server = HTTPServer((host, port), make_handler(application, access))
    print(f"Opportunity Control Layer disponible en http://{host}:{port}")
    print(f"Clave EDITOR (sólo sesión local): {access.editor_token}")
    print(f"Clave REVISOR (aprobación humana): {access.reviewer_token}")
    print("No comparta estas claves ni las incluya en capturas. Caducan al reiniciar.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
