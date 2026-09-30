"""Verifica que la exportación no filtre material privado ni bases de trabajo."""

import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from opportunity_control.bootstrap import build_runtime
from opportunity_control.seed import create_seed_database
from scripts.package_delivery import ROOT, collect_files, package_delivery


class DeliveryTests(unittest.TestCase):
    """Pruebas de handoff y conservación de datos entre ejecuciones."""

    def test_export_excludes_private_instructions_and_runtime(self) -> None:
        files = [path.relative_to(ROOT).as_posix() for path in collect_files()]
        self.assertIn("web/index.html", files)
        self.assertIn("docs/ARQUITECTURA.svg", files)
        self.assertIn("deliverables/BridgeLytic_Vertical_Slice.html", files)
        for name in files:
            self.assertNotIn("AGENTS.md", name)
            self.assertNotIn("GUIA_DEMO.md", name)
            self.assertNotIn("__pycache__", name)
            self.assertFalse(name.startswith("runtime/"))
            self.assertFalse(name.endswith((".db", ".log", ".env")))

    def test_zip_manifest_matches_content(self) -> None:
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "delivery.zip"
            package_delivery(destination)
            with ZipFile(destination) as archive:
                prefix = "opportunity-control-layer/"
                for line in (
                    archive.read(prefix + "MANIFEST.sha256").decode().splitlines()
                ):
                    digest, filename = line.split("  ", 1)
                    self.assertEqual(
                        hashlib.sha256(archive.read(prefix + filename)).hexdigest(),
                        digest,
                    )

    def test_seed_never_overwrites_an_existing_database(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "test.db"
            create_seed_database(path)
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                create_seed_database(path, replace=True)
            self.assertEqual(path.read_bytes(), before)

    def test_restart_keeps_records_and_does_not_reseed(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "test.db"
            first = build_runtime(path)
            case = "OPPORTUNITY-UVA-AI-PILOT"
            response = first.api.handle(
                "POST",
                f"/api/opportunities/{case}/unknowns",
                {"id": "RESTART", "question": "Pregunta persistente", "actor": "test"},
            )
            self.assertEqual(response.status, 201)
            first.close()
            second = build_runtime(path)
            try:
                brief = second.api.handle(
                    "GET", f"/api/opportunities/{case}/brief"
                ).payload
                self.assertIn("RESTART", [item["id"] for item in brief["unknowns"]])
                self.assertEqual(
                    len(second.api.handle("GET", "/api/opportunities").payload), 3
                )
            finally:
                second.close()
