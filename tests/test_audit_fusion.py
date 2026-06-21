from __future__ import annotations

import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from cmar.audit_stream import integrate_audit_with_cmar


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


class AuditFusionTests(unittest.TestCase):
    def test_integrate_audit_with_cmar(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            (repo / "idea.py").write_text("def f(): return 1\n", encoding="utf-8")
            audit = root / "audit.zip"
            make_audit_zip(audit)
            report = integrate_audit_with_cmar(repo, audit, target_valid_mass=1)
            data = report.to_dict()
            self.assertTrue(data["stream_linkage"])
            self.assertEqual(data["audit_projection"]["projection_verdict"], "AUDIT_STREAM_ACCEPTED")
            self.assertIn(data["fused_verdict"]["gate"], {"PASS", "CONTINUE_INTEGRATION", "FAIL_AUDIT_STREAM"})


if __name__ == "__main__":
    unittest.main()
