"""Regression cases for observed data errors, using synthetic fixtures."""
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "futbol_xg"))
from analysis_core import merge_sources, possession_dilimle, possession_statistics, reconstruct_game_states, summarize_states, reconcile_xg, audit_event_order


def fixtures():
    return pd.DataFrame([
        dict(league="L", season=2526, game_id=1, team="H", opponent="A", venue="Home", gol=1, xg=0.8),
        dict(league="L", season=2526, game_id=1, team="A", opponent="H", venue="Away", gol=1, xg=0.1),
    ])


def shots():
    return pd.DataFrame([
        dict(league="L", season=2526, game_id=1, shot_id=1, team="H", minute=10, xg=0.0, result="Own Goal"),
        dict(league="L", season=2526, game_id=1, shot_id=2, team="H", minute=20, xg=0.8, result="Goal"),
        dict(league="L", season=2526, game_id=1, shot_id=3, team="A", minute=40, xg=0.1, result="Missed Shot"),
    ])


class AnalysisTests(unittest.TestCase):
    def test_own_goal_changes_opponent_score_and_next_state(self):
        events, exposure, matches, missing = reconstruct_game_states(shots(), fixtures())
        self.assertEqual(events.durum.tolist(), ["drawing", "trailing", "drawing"])
        self.assertEqual(events.is_attacking_shot.tolist(), [False, True, True])
        self.assertTrue(matches.score_verified.all())
        self.assertEqual(missing, [])
        self.assertTrue((exposure.groupby("team").minutes.sum() == 90).all())

    def test_zero_shot_states_keep_time_and_season(self):
        events, exposure, _, _ = reconstruct_game_states(shots(), fixtures())
        summary = summarize_states(events, exposure)
        row = summary[(summary.team == "A") & (summary.durum == "leading")].iloc[0]
        self.assertEqual(row.toplam_dakika, 10)
        self.assertEqual(row.toplam_sut, 0)
        self.assertEqual(row.xg_90, 0)
        self.assertTrue(np.isnan(row.xg_sut_basina))
        self.assertIn("season", summary)

    def test_verified_duration_and_invalid_end(self):
        durations = pd.DataFrame([dict(league="L", season=2526, game_id=1, end_minute=95)])
        _, exposure, matches, _ = reconstruct_game_states(shots(), fixtures(), durations)
        self.assertEqual(matches.duration_source.iloc[0], "provided")
        self.assertTrue((exposure.groupby("team").minutes.sum() == 95).all())
        durations.end_minute = 39
        with self.assertRaisesRegex(ValueError, "precedes"):
            reconstruct_game_states(shots(), fixtures(), durations)

    def test_score_mismatch_is_rejected(self):
        f = fixtures()
        f.loc[f.team == "H", "gol"] = 2
        with self.assertRaisesRegex(ValueError, "score mismatch"):
            reconstruct_game_states(shots(), f)

    def test_fractional_fixture_goals_are_rejected_instead_of_truncated(self):
        f = fixtures().astype({"gol": float})
        f.loc[f.team == "H", "gol"] = 1.5
        with self.assertRaisesRegex(ValueError, "whole numbers"):
            reconstruct_game_states(shots(), f)

    def test_non_finite_metrics_and_fractional_shot_counts_are_rejected(self):
        f = fixtures().drop(columns=["gol", "xg", "game_id"]).assign(GF=[1, 1], possession=[50, 50], sut=[10., 10.])
        u = fixtures()
        u.loc[u.team == "H", "xg"] = np.inf
        with self.assertRaisesRegex(ValueError, "finite"):
            merge_sources(f, u)
        f.loc[f.team == "H", "sut"] = np.inf
        with self.assertRaisesRegex(ValueError, "finite"):
            merge_sources(f, fixtures())
        f.loc[f.team == "H", "sut"] = 10.5
        with self.assertRaisesRegex(ValueError, "whole numbers"):
            merge_sources(f, fixtures())

    def test_duplicate_event_is_rejected(self):
        s = pd.concat([shots(), shots().iloc[:1]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "duplicate keys"):
            reconstruct_game_states(s, fixtures())

    def test_inconsistent_match_is_quarantined_as_a_whole(self):
        bad = fixtures().assign(game_id=2)
        bad.loc[bad.team == "H", "gol"] = 2
        f = pd.concat([fixtures(), bad], ignore_index=True)
        s = pd.concat([shots(), shots().assign(game_id=2, shot_id=[4, 5, 6])], ignore_index=True)
        events, exposure, matches, _ = reconstruct_game_states(s, f, exclude_score_mismatches=True)
        self.assertEqual(set(events.game_id), {1})
        self.assertEqual(set(exposure.game_id), {1})
        self.assertEqual(matches.score_verified.tolist(), [True, False])
        self.assertEqual(matches.excluded_events.tolist(), [0, 3])

    def test_fixture_without_events_is_reported(self):
        f = pd.concat([fixtures(), fixtures().assign(game_id=2)], ignore_index=True)
        _, _, _, missing = reconstruct_game_states(shots(), f)
        self.assertEqual(missing, [dict(league="L", season=2526, game_id=2)])

    def test_possession_final_edge_included(self):
        d = possession_dilimle(pd.DataFrame({"possession": [24, 25, 74, 75, 76]}))
        self.assertEqual(d.possession.tolist(), [25, 74, 75])
        self.assertFalse(d.Possession_Bin.isna().any())
        self.assertEqual(str(d.Possession_Bin.iloc[-1]), "70-75%")

    def test_missing_shots_do_not_inflate_quality(self):
        d = pd.DataFrame(dict(league=["L"] * 2, season=[2526] * 2, game_id=[1, 2],
                              possession=[50, 50], xg=[2.0, 100.0], sut=[10.0, np.nan], gol=[1, 1]))
        quality = possession_statistics(d, "shot_quality", repetitions=0)
        self.assertAlmostEqual(quality.value.iloc[0], 0.2)
        self.assertEqual(quality.n.iloc[0], 1)
        volume = possession_statistics(d, "volume", repetitions=0)
        self.assertEqual(volume.n.iloc[0], 2)

    def test_duplicate_merge_key_is_rejected(self):
        f = fixtures().assign(GF=[1, 1], possession=[50, 50], sut=[10, 10])
        with self.assertRaisesRegex(ValueError, "duplicate keys"):
            merge_sources(pd.concat([f, f.iloc[:1]]), fixtures())

    def test_match_clusters_and_bootstrap_are_deterministic(self):
        d = pd.DataFrame(dict(league=["L"] * 4, season=[2526] * 4, game_id=[1, 1, 2, 2],
                              possession=[50] * 4, xg=[1., 2., 3., 4.], sut=[10] * 4, gol=[1] * 4))
        a = possession_statistics(d, "volume", repetitions=100)
        b = possession_statistics(d, "volume", repetitions=100)
        pd.testing.assert_frame_equal(a, b)
        self.assertEqual(a.match_clusters.iloc[0], 2)
        self.assertEqual(a.n.iloc[0], 4)

    def test_xg_reconciliation_reports_difference_without_editing_events(self):
        f = fixtures()
        f.loc[f.team == "H", "xg"] = 0.6
        events, _, _, _ = reconstruct_game_states(shots(), f)
        audit = reconcile_xg(events, f)
        row = audit.loc[audit.team == "H"].iloc[0]
        self.assertAlmostEqual(row.xg_difference, 0.2)
        self.assertFalse(row.within_tolerance)
        self.assertEqual(row.attacking_shots, 1)
        self.assertEqual(len(events), 3)

    def test_xg_reconciliation_keeps_zero_shot_team_and_excludes_missing_fixture(self):
        f = fixtures()
        f.loc[f.team == "A", "xg"] = 0.0
        f = pd.concat([f, fixtures().assign(game_id=2)], ignore_index=True)
        events, _, _, _ = reconstruct_game_states(shots().iloc[:2], f)
        audit = reconcile_xg(events, f)
        row = audit.loc[audit.team == "A"].iloc[0]
        self.assertEqual(row.event_xg, 0)
        self.assertEqual(row.attacking_shots, 0)
        self.assertTrue(row.within_tolerance)
        self.assertEqual(set(audit.game_id), {1})

    def test_order_diagnostic_reports_sensitivity_without_relabelling_events(self):
        s = shots().assign(shot_id=[2, 1, 3])
        events, _, _, _ = reconstruct_game_states(s, fixtures())
        audit = audit_event_order(events, fixtures()).iloc[0]
        self.assertEqual(audit.minute_decreases, 1)
        self.assertEqual(audit.scoring_minute_decreases, 1)
        self.assertEqual(audit.alternative_state_labels, 2)
        self.assertEqual(events.durum.tolist(), ["drawing", "trailing", "drawing"])


if __name__ == "__main__":
    unittest.main()
