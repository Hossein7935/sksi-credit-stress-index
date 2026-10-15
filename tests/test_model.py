import unittest
from datetime import datetime
from pathlib import Path

from sksi.fetch import last_on_or_before, parse_fred_csv
from sksi.model import combine, load_calibration, regime_from_raw, score_from_raw

ROOT = Path(__file__).resolve().parents[1]


class FetchTests(unittest.TestCase):
    def test_parse_skips_blanks(self):
        text = "observation_date,DBAA\n2020-01-02,3.5\n2020-01-03,\n2020-01-06,.\n2020-01-07,3.7\n"
        parsed = parse_fred_csv(text)
        self.assertEqual(parsed[datetime(2020, 1, 2)], 3.5)
        self.assertEqual(parsed[datetime(2020, 1, 7)], 3.7)
        self.assertEqual(len(parsed), 2)

    def test_last_observation_within_a_week(self):
        series = {
            datetime(2020, 1, 2): 1.0,
            datetime(2020, 1, 3): 2.0,
        }
        dates = sorted(series)
        self.assertEqual(last_on_or_before(dates, series, datetime(2020, 1, 6), 6), 2.0)
        self.assertIsNone(last_on_or_before(dates, series, datetime(2020, 1, 20), 6))


class IndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cal = load_calibration(ROOT / "sksi" / "calibration.json")

    def test_thresholds_land_on_round_scores(self):
        cuts = self.cal["thresholds"]
        self.assertAlmostEqual(score_from_raw(cuts["watch"], self.cal), 48.0, places=6)
        self.assertAlmostEqual(score_from_raw(cuts["stress"], self.cal), 68.0, places=6)
        self.assertAlmostEqual(score_from_raw(cuts["severe"], self.cal), 84.0, places=6)
        self.assertEqual(regime_from_raw(cuts["watch"], self.cal), "watch")
        self.assertEqual(regime_from_raw(cuts["watch"] - 1e-9, self.cal), "normal")

    def test_gfc_peak_is_severe_quorum(self):
        # Week of 21 Nov 2008, acceleration ignored. Levels are the public record
        # of that week, not a redistributed series.
        result = combine(
            {"hy": 19.92, "ig": 6.36, "def": 3.26, "nfci": 3.06},
            calibration=self.cal,
        )
        self.assertEqual(result["regime"], "severe")
        self.assertTrue(result["quorum"])
        self.assertGreater(result["score"], 95)

    def test_current_calm_is_not_an_alarm(self):
        result = combine(
            {"hy": 3.10, "ig": 0.85, "def": 0.47, "nfci": -0.494},
            calibration=self.cal,
        )
        self.assertEqual(result["regime"], "normal")
        self.assertFalse(result["quorum"])
        self.assertLess(result["score"], 40)

    def test_one_calm_leg_blocks_quorum(self):
        result = combine(
            {"hy": 11.0, "ig": 3.0, "def": 1.6, "nfci": -0.56},
            calibration=self.cal,
        )
        self.assertFalse(result["quorum"])
        self.assertLess(result["sync"], 0.75)

    def test_higher_spreads_raise_the_index(self):
        base = {"hy": 4.7, "ig": 1.1, "def": 0.8, "nfci": -0.4}
        hotter = dict(base, hy=base["hy"] + 1.0)
        self.assertGreater(combine(hotter, calibration=self.cal)["raw"], combine(base, calibration=self.cal)["raw"])


if __name__ == "__main__":
    unittest.main()
