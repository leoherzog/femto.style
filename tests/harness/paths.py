"""Repository paths used by the harness."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TESTS = REPO / "tests"
HARNESS = TESTS / "harness"
DIVERGENCES = TESTS / "divergences"
FIXTURES = TESTS / "fixtures"
RESULTS = TESTS / "results"
MATRIX = HARNESS / "matrix.json"
MASKS = HARNESS / "masks.json"
TARGETS = HARNESS / "targets.json"
STATIC_CHECKS = TESTS / "static_checks.py"
# Files the proxy serves at /__harness/<name> (never anything else from this folder).
HARNESS_FILES = ("host.html", "differ.js", "probe.html")
HARNESS_PREFIX = "/__harness/"
