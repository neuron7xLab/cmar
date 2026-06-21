from __future__ import annotations
import unittest
from pathlib import Path
from cmar.normalizer import normalize_payload, normalize_repository
from cmar.quantizer import quantize_normalized_report
from cmar.falsifier import falsify_payload
from cmar.autofill import autofill_repository
from cmar.integrator import integrate_artifact_streams
from cmar.runtime import run_runtime_pipeline

class CMARRuntimeSuite(unittest.TestCase):
    def test_normalize_payload(self):
        r = normalize_payload({
            'scan': {'artifact_hash': 'x', 'total_bytes': 1000, 'layer_bytes': {'source': 200, 'test': 100}, 'missing_surface': []},
            'mass_ledger': {'valid_mass_bytes': 500, 'target_valid_mass_bytes': 1000, 'voids_detected': 1, 'blocking_voids': 0},
            'protocol_report': {'valid': True},
        })
        self.assertIn('source_mass_ratio', r.vector)
        self.assertGreaterEqual(r.release_readiness, 0)
        self.assertLessEqual(r.release_readiness, 1)

    def test_quantizer_visible_thresholds(self):
        r = quantize_normalized_report({'vector': {'a': 0.1, 'b': 0.9}})
        self.assertTrue(r.thresholds)
        self.assertEqual(r.state_vector['a'], 'VOID')
        self.assertEqual(r.state_vector['b'], 'RELEASE')

    def test_falsify_missing(self):
        r = falsify_payload({
            'scan': {'missing_surface': ['tests', 'ci', 'entrypoint'], 'total_bytes': 100, 'layer_bytes': {'docs': 90}, 'artifact_hash': 'a'},
            'mass_ledger': {'artifact_hash': 'a', 'valid_mass_bytes': 10, 'total_bytes': 100, 'status': 'BLOCKED', 'blocking_voids': 3},
            'protocol_report': {'valid': True},
            'quantization_report': {'verdict': 'VOID'},
        })
        self.assertEqual(r.verdict, 'FALSIFIED')

    def test_falsify_clean(self):
        r = falsify_payload({
            'scan': {'missing_surface': [], 'total_bytes': 100, 'layer_bytes': {'source': 40, 'test': 20}, 'artifact_hash': 'a'},
            'mass_ledger': {'artifact_hash': 'a', 'valid_mass_bytes': 80, 'total_bytes': 100, 'status': 'PASS', 'blocking_voids': 0},
            'protocol_report': {'valid': True},
            'quantization_report': {'verdict': 'RELEASE'},
        })
        self.assertEqual(r.verdict, 'NOT_FALSIFIED')

    def test_autofill(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / 'idea.py').write_text('def f(): return 1\n')
            r = autofill_repository(p, 1)
            self.assertTrue(r.success)
            self.assertTrue((p / 'SECURITY.md').exists())
            self.assertTrue((p / '.github/workflows/ci.yml').exists())

    def test_integrator(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / 'idea.py').write_text('def f(): return 1\n')
            s = integrate_artifact_streams(p, 1).to_dict()
            self.assertEqual(s['flow'][0], 'scan')
            self.assertIn('integrated_verdict', s)

    def test_runtime(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / 'idea.py').write_text('def f(): return 1\n')
            r = run_runtime_pipeline(p, 1)
            self.assertIn(r.final_status, {'PASS', 'PARTIAL', 'FAIL'})
            self.assertTrue(r.normalized_state)
            self.assertTrue(r.quantized_state)
            self.assertTrue(r.integrated_state)

if __name__ == '__main__':
    unittest.main()
