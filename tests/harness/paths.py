"""Repository paths used by the harness."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TESTS = REPO / "tests"
HARNESS = TESTS / "harness"
RESULTS = TESTS / "results"
TARGETS = HARNESS / "targets.json"
STATIC_CHECKS = TESTS / "static_checks.py"
