from __future__ import annotations

import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from cmar.audit_stream import scan_audit_package, project_audit_to_cmar


def make_audit_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("n7x/src/n7x/pipeline/normalizer.py", "def normalize(): return {}\n")
        z.writestr("n7x/src/n7x/pipeline/quantizer.py", "def quantize(): return {}\n")
        z.writestr("n7x/src/n7x/pipeline/integrator.py", "def integrate(): return {}\n")
        z.writestr("n7x/src/n7x/pipeline/falsifier.py", "def falsify(): return {}\n")
        z.writestr("n7x/src/n7x/scorers/velocity.py", "def score(): return 1\n")
        z.writestr("n7x/src/n7x/collectors/repo.py", "def collect(): return {}\n")
        z.writestr("n7x/src/n7x/cli.py", "import argparse\np=argparse.ArgumentParser(); p.add_subparsers().add_parser('audit')\n")
        z.writestr("n7x/tests/test_pipeline.py", "def test_ok(): assert True\n")
        z.writestr("n7x/.github/workflows/audit.yml", "name: audit\n")


class AuditStreamTests(unittest.TestCase):
    def test_scan_and_project_audit_package(self) -> None:
        with TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "audit.zip"
            make_audit_zip(pkg)
            snap = scan_audit_package(pkg)
            self.assertGreaterEqual(snap.total_files, 9)
            self.assertGreaterEqual(snap.layer_files["pipeline"], 4)
            projection = project_audit_to_cmar(snap)
            self.assertEqual(projection.projection_verdict, "AUDIT_STREAM_ACCEPTED")
            self.assertIn("normalizer", projection.accepted_capabilities)


if __name__ == "__main__":
    unittest.main()
