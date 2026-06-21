# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared test helpers: locate the seed; make disposable repaired copies."""
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "examples" / "seed_14kb_intent"


class SeedCase(unittest.TestCase):
    def copy_seed(self) -> Path:
        d = Path(tempfile.mkdtemp(prefix="cmar_seed_"))
        dst = d / "repo"
        shutil.copytree(SEED, dst)
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        return dst
