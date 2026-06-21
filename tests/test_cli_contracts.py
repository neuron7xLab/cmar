from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CliContractTests(unittest.TestCase):
    def run_cmd(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)

    def test_doctor_default_root_runs(self) -> None:
        result = self.run_cmd([sys.executable, "-m", "cmar.cli", "doctor", "--out", "artifacts/test_doctor_default.json"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((ROOT / "artifacts/test_doctor_default.json").exists())

    def test_corpus_eval_uses_runtime_corpus(self) -> None:
        corpus = ROOT / "benchmark_corpus/runtime_v13/artifact_state_stress.jsonl"
        result = self.run_cmd([sys.executable, "-m", "cmar.cli", "corpus-eval", str(corpus), "--limit", "64", "--out", "artifacts/test_corpus_eval.json"])
        self.assertEqual(result.returncode, 0, result.stderr)
        data = (ROOT / "artifacts/test_corpus_eval.json").read_text(encoding="utf-8")
        self.assertIn('"records": 64', data)


if __name__ == "__main__":
    unittest.main()
