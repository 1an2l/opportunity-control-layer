"""Exporta presentación y arquitectura a PDF con un navegador local opcional."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Renderiza fuentes versionables; no accede a servicios externos."""
    from playwright.sync_api import sync_playwright

    output = ROOT / "deliverables"
    previews = ROOT / "runtime" / "qa"
    previews.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 780})
        page.goto((output / "BridgeLytic_Vertical_Slice.html").as_uri())
        # El PDF es autocontenido; no incrustar enlaces file:// del equipo local.
        page.locator("a").evaluate_all(
            "links => links.forEach(link => link.removeAttribute('href'))"
        )
        page.pdf(
            path=str(output / "BridgeLytic_Vertical_Slice.pdf"),
            print_background=True,
            prefer_css_page_size=True,
        )
        for number in (0, 2, 4, 6, 7):
            page.locator(".slide").nth(number).screenshot(
                path=str(previews / f"slide-{number + 1}.png")
            )
        svg = (ROOT / "docs" / "ARQUITECTURA.svg").read_text(encoding="utf-8")
        page.set_viewport_size({"width": 1600, "height": 1920})
        page.set_content(
            "<html><head><style>body{margin:0}@page{size:A3 portrait;margin:10mm}"
            "@media print{svg{width:100%;height:395mm;display:block}}</style></head>"
            "<body>" + svg + "</body></html>"
        )
        page.screenshot(path=str(previews / "architecture.png"), full_page=True)
        page.pdf(
            path=str(output / "BridgeLytic_Arquitectura.pdf"),
            print_background=True,
            prefer_css_page_size=True,
        )
        browser.close()
    print("PDFs generados desde HTML/SVG locales en deliverables/.")


if __name__ == "__main__":
    main()
