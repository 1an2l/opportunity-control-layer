"""Exportación por lista permitida; no incluye bases, secretos ni notas privadas."""

import argparse
import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = frozenset({"README.md", "pyproject.toml", ".gitignore"})
DIRECTORIES = frozenset(
    {"opportunity_control", "web", "data", "tests", "docs", "deliverables", "scripts"}
)
EXTENSIONS = frozenset({".py", ".js", ".css", ".html", ".md", ".svg", ".pdf", ".toml"})
EXCLUDED_PARTS = frozenset(
    {"__pycache__", ".git", "runtime", "complemento", "CONTEXTO_IA", ".venv"}
)
EXCLUDED_NAMES = frozenset({"AGENTS.md", "CLAUDE.md", "GUIA_DEMO.md", ".env"})


def collect_files(root: Path = ROOT) -> list[Path]:
    """Selecciona exclusivamente código, documentación técnica y entregables."""
    selected = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if not path.is_file() or path.is_symlink():
            continue
        if (
            any(part in EXCLUDED_PARTS for part in relative.parts)
            or path.name in EXCLUDED_NAMES
        ):
            continue
        if len(relative.parts) == 1:
            if path.name in ROOT_FILES:
                selected.append(path)
        elif (
            relative.parts[0] in DIRECTORIES
            and path.suffix in EXTENSIONS
            and not path.name.startswith(".")
        ):
            selected.append(path)
    return sorted(selected)


def package_delivery(destination: Path, root: Path = ROOT) -> int:
    """Crea un ZIP nuevo con manifiesto SHA-256; nunca sobrescribe un archivo."""
    destination = destination.resolve()
    if destination.is_relative_to(root.resolve()):
        raise ValueError("el paquete debe guardarse fuera del proyecto")
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = collect_files(root)
    manifest = []
    with ZipFile(destination, "x", compression=ZIP_DEFLATED) as archive:
        for path in files:
            name = path.relative_to(root).as_posix()
            data = path.read_bytes()
            archive.writestr(f"opportunity-control-layer/{name}", data)
            manifest.append(f"{hashlib.sha256(data).hexdigest()}  {name}")
        archive.writestr(
            "opportunity-control-layer/MANIFEST.sha256", "\n".join(manifest) + "\n"
        )
    return len(files)


def main() -> None:
    """Permite elegir una ruta externa para el paquete verificable."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT.parent / "entrega" / "BridgeLytic_Opportunity_Control_Layer.zip",
    )
    destination = parser.parse_args().output
    count = package_delivery(destination)
    print(f"Paquete creado: {destination.resolve()} ({count} archivos + manifiesto)")


if __name__ == "__main__":
    main()
