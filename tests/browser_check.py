"""Verificación opcional de UI con Playwright y Edge, sin red externa."""

from http.server import HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

from opportunity_control.api.access import LocalAccess
from opportunity_control.api.server import make_handler
from opportunity_control.bootstrap import build_runtime


def main() -> None:
    """Ejecuta un recorrido humano real y comprueba el diseño responsivo."""
    from playwright.sync_api import sync_playwright

    with TemporaryDirectory(prefix="ocl-browser-") as directory:
        runtime = build_runtime(Path(directory) / "test.db")
        access = LocalAccess("editor-browser-test", "reviewer-browser-test")
        server = HTTPServer(("127.0.0.1", 0), make_handler(runtime.api, access))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="msedge", headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}")
                page.locator("#opportunity-view").wait_for(state="visible")
                assert page.locator("#transition-form").is_visible()
                assert page.locator("#next-stage").is_enabled()
                assert page.locator("#next-stage option").count() == 1
                assert page.locator("#transition-complete").is_hidden()
                page.locator("#session-key").fill(access.reviewer_token)
                page.locator("#session-form button").click()
                page.wait_for_function(
                    "document.querySelector('#session-label').textContent.includes('reviewer-browser-test')"
                )
                for stage in ("EVIDENCE_REVIEW", "OPTIONS_READY"):
                    page.locator("#next-stage").select_option(stage)
                    page.locator("#transition-form button").click()
                    page.wait_for_function(
                        "document.querySelector('#notice').textContent.includes('Operación registrada')"
                    )
                    page.wait_for_timeout(80)
                page.locator("#proposal-form").locator("..").locator("summary").click()
                page.locator("#proposal-form select").select_option(index=1)
                page.locator("#proposal-form textarea").fill(
                    "Preparar evaluación interna con evidencia sintética"
                )
                page.locator("#evidence-references input").first.check()
                page.locator("#hypothesis-references input").first.check()
                page.locator("#unknown-references input").first.check()
                page.locator("#proposal-form button").click()
                page.wait_for_function(
                    "document.querySelector('#decision-proposal').value.length > 0"
                )
                page.locator("#next-stage").select_option("PENDING_APPROVAL")
                page.locator("#transition-form button").click()
                page.wait_for_function(
                    "!document.querySelector('#decision-form button').disabled"
                )
                page.locator("#decision-form select").select_option(index=2)
                page.locator("#decision-form textarea").fill(
                    "Prefiero esperar los datos sanitizados para evitar conclusiones prematuras"
                )
                page.locator("#decision-form input[type=checkbox]").check()
                page.locator("#decision-form button").click()
                page.wait_for_function(
                    "document.querySelector('#stage-badge').textContent === 'Aprobada'"
                )
                assert page.locator("#transition-form").is_hidden()
                assert page.locator("#next-stage").is_disabled()
                assert page.locator("#transition-complete").is_visible()
                assert (
                    "Decisión aprobada"
                    in page.locator("#transition-complete-title").inner_text()
                )
                page.locator("#transition-complete-link").click()
                assert page.url.endswith("#next-actions")
                page.locator("[data-status=SIMULATED]").first.click()
                page.wait_for_function(
                    "document.querySelector('#action-list').textContent.includes('SIMULATED')"
                )
                page.locator("#external-action-button").click()
                page.wait_for_function(
                    "document.querySelector('#notice').textContent.includes('HTTP 403')"
                )
                assert (
                    page.locator("#audit-list")
                    .inner_text()
                    .count("EXTERNAL_ACTION_BLOCKED")
                    >= 1
                )
                output = Path("runtime/qa")
                output.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(output / "desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                page.screenshot(path=str(output / "mobile.png"), full_page=True)
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth"
                ), "Desbordamiento horizontal móvil"
                # Recargar un caso cerrado no debe volver a mostrar el selector vacío.
                page.reload()
                page.locator("#transition-complete").wait_for(state="visible")
                assert page.locator("#transition-form").is_hidden()
                page.set_viewport_size({"width": 1440, "height": 1000})
                page.locator(".next-panel").screenshot(
                    path=str(output / "terminal-stage.png")
                )
                # Cambiar a un caso abierto debe recuperar los controles normales.
                page.locator('[data-case="OPPORTUNITY-UVA-AI-PILOT"]').click()
                page.locator("#transition-form").wait_for(state="visible")
                assert page.locator("#next-stage").is_enabled()
                assert page.locator("#transition-complete").is_hidden()
                # El otro cierre final debe conducir a auditoría, no a simulación.
                case_url = f"http://127.0.0.1:{server.server_port}/api/opportunities/OPPORTUNITY-UVA-AI-PILOT"
                commands = [
                    ("transitions", {"next_stage": "EVIDENCE_REVIEW"}),
                    ("transitions", {"next_stage": "OPTIONS_READY"}),
                    (
                        "proposals",
                        {
                            "id": "PROPOSAL-REJECTION-UI",
                            "option_id": "OPTION-SEED-001-1",
                            "rationale": "Revisión sintética",
                            "evidence_ids": ["EVIDENCE-SEED-001"],
                        },
                    ),
                    ("transitions", {"next_stage": "PENDING_APPROVAL"}),
                    (
                        "transitions",
                        {
                            "next_stage": "REJECTED",
                            "rationale": "Respaldo insuficiente para avanzar",
                        },
                    ),
                ]
                for endpoint, body in commands:
                    response = page.request.post(
                        f"{case_url}/{endpoint}",
                        data=body,
                        headers={"Authorization": f"Bearer {access.reviewer_token}"},
                    )
                    assert response.ok, response.text()
                page.locator("#refresh-button").click()
                page.wait_for_function(
                    "document.querySelector('#stage-badge').textContent === 'Rechazada'"
                )
                assert page.locator("#transition-form").is_hidden()
                assert (
                    "Caso rechazado"
                    in page.locator("#transition-complete-title").inner_text()
                )
                page.locator("#transition-complete-link").click()
                assert page.url.endswith("#audit")
                page.set_viewport_size({"width": 1600, "height": 1920})
                page.set_content(
                    '<html><body style="margin:0">'
                    + Path("docs/ARQUITECTURA.svg").read_text(encoding="utf-8")
                    + "</body></html>"
                )
                page.screenshot(path=str(output / "architecture.png"), full_page=True)
                assert not errors, errors
                browser.close()
                print(
                    "UI OK: propuesta, decisión, simulación, bloqueo, auditoría y ancho móvil."
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
            runtime.close()


if __name__ == "__main__":
    main()
