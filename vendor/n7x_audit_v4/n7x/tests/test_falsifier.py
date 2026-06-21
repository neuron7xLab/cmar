"""tests/test_falsifier.py — alias to test_quantizer.py TestFalsifier class"""
# TestFalsifier is defined in test_quantizer.py and discovered automatically.
# This file satisfies the REQUIRED_FILES check in release_check.py.
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import unittest
from test_quantizer import TestFalsifier  # noqa: F401

if __name__ == "__main__":
    unittest.main()
