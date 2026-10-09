from pathlib import Path
import csv
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_upload import ROOT, publication_files


class UploadTests(unittest.TestCase):
    def test_publication_manifest_excludes_local_inputs_and_environment(self):
        names = {p.relative_to(ROOT).as_posix() for p in publication_files()}
        self.assertIn("README.md", names)
        self.assertIn("examples/synthetic/understat_team_match.csv", names)
        self.assertIn("results/validation_report.json", names)
        self.assertFalse(any(n.startswith(("futbol_xg/data/", ".venv/", "demo-results/")) for n in names))
        self.assertFalse(any(n.endswith((".dll", ".pyc", ".lock", "_possession_data_full.csv")) for n in names))
        self.assertFalse(any("xg_reconciliation_detail" in n for n in names))

    def test_public_xg_diagnostics_exclude_source_values(self):
        with (ROOT / "results" / "xg_reconciliation.csv").open(encoding="utf-8", newline="") as handle:
            columns = next(csv.reader(handle))
        self.assertEqual(columns, ["league", "season", "game_id", "team", "xg_difference", "within_tolerance"])


if __name__ == "__main__":
    unittest.main()
