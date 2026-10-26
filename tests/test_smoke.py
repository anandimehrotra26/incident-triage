"""Fast checks (about 20 s). Run: python -m unittest discover -s tests -v"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from triage import data_gen, review  # noqa: E402
from triage.config import BASE_CATEGORIES, BASE_COSTS, STRICT_COSTS  # noqa: E402
from triage.costs import evaluate, report_cost  # noqa: E402
from triage.model import MLTriage, route_of  # noqa: E402
from triage.rules import RulesTriage  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


class DataTests(unittest.TestCase):
    def test_dataset_size_and_labels(self):
        df = pd.read_csv(ROOT / "data" / "incidents.csv")
        self.assertGreaterEqual(len(df), 300)
        self.assertTrue(set(df["category"]) <= set(BASE_CATEGORIES))
        self.assertTrue(set(df["urgent"]) <= {0, 1})

    def test_generator_is_deterministic(self):
        a = data_gen.generate(60, data_gen.CLASS_MIX, 1)
        b = data_gen.generate(60, data_gen.CLASS_MIX, 1)
        self.assertEqual([r["text"] for r in a], [r["text"] for r in b])

    def test_review_sheet_hides_labels(self):
        sheet = pd.read_csv(ROOT / "data" / "review" / "review_sheet_blank.csv")
        self.assertGreaterEqual(len(sheet), 50)
        self.assertFalse({"category", "urgent", "category_true"} & set(sheet.columns))


class RulesTests(unittest.TestCase):
    def test_negation(self):
        r = RulesTriage()
        self.assertFalse(r.predict_one("minor scrape, no injuries, drivable")["urgent"])
        self.assertTrue(r.predict_one("driver is bleeding, ambulance called")["urgent"])


class CostTests(unittest.TestCase):
    def pred(self, cat, urgent, abstain=False):
        return {"category": cat, "urgent": urgent, "abstain": abstain}

    def test_costs(self):
        c, _ = report_cost("delay_late", True, self.pred("delay_late", False), BASE_COSTS)
        self.assertEqual(c, BASE_COSTS.miss_urgent)
        c, _ = report_cost("hazmat_spill", False, self.pred("cargo_damage", False), BASE_COSTS)
        self.assertEqual(c, BASE_COSTS.wrong_team_critical)
        c, _ = report_cost("delay_late", True, self.pred("delay_late", False, abstain=True), BASE_COSTS)
        self.assertEqual(c, BASE_COSTS.human_review + BASE_COSTS.abstain_urgent_delay)
        c, _ = report_cost("delay_late", True, self.pred("delay_late", False), STRICT_COSTS)
        self.assertEqual(c, 300.0)


class ModelTests(unittest.TestCase):
    def test_train_predict_route(self):
        df = pd.read_csv(ROOT / "data" / "incidents.csv").head(300)
        m = MLTriage(rule_weight=3.0, t_cat=0.3, t_urgent=0.3).fit(df["text"].values, df["category"].values, df["urgent"].values)
        p = m.predict_one("Armed men stopped our truck and the driver is being held")
        self.assertTrue(p["urgent"])
        self.assertIn(route_of(p)["priority"], ("URGENT",))
        metrics, _ = evaluate(m.predict(df["text"].tolist()[:50]), df["category"][:50], df["urgent"][:50], BASE_COSTS)
        self.assertLess(metrics["cost_per_100"], 400)  # training-set sanity only, NOT a generalisation claim


class ReviewTests(unittest.TestCase):
    def test_score_with_simulated_reviewer(self):
        sheet = pd.read_csv(ROOT / "data" / "review" / "review_sheet_blank.csv")
        gold = pd.read_csv(ROOT / "data" / "incidents.csv").set_index("id")
        sheet["reviewer_category"] = gold.loc[sheet["id"], "category_true"].values
        sheet["reviewer_urgent_0or1"] = gold.loc[sheet["id"], "urgent"].values
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "completed.csv"
            sheet.to_csv(f, index=False)
            review.score(f, out_dir=d)
            self.assertTrue((Path(d) / "review_report.md").exists())


if __name__ == "__main__":
    unittest.main()
