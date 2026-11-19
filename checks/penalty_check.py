"""Penalty check (added after submission, 20 Nov 2026).

The cost model charges nothing for a false URGENT flag on a report that is sent to a person,
and only 4 + 10 for an urgent report that waits unflagged in that person's queue. Both numbers
are assumptions. This script re-runs approaches B and C+ on the same five splits as
`python -m triage.evaluate` and re-scores them two other ways, to see which conclusions survive.

Run from the repository root:  python checks/penalty_check.py   (about 2-3 minutes)
"""
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402

from triage.config import BASE_COSTS  # noqa: E402
from triage.costs import evaluate, is_abstained  # noqa: E402
from triage.pipeline import fit_tuned, load, prepare_oof, split  # noqa: E402

SEEDS = (42, 43, 44, 45, 46)


def main():
    df = load()
    print("cost per 100 reports, mean of 5 runs (people reading everything = 400)")
    print(f"{'test':10s} {'model':4s} {'as built':>9s} {'false alarm in queue = 5':>26s} {'+ queue miss = 100':>20s}")
    for mode in ("template", "random"):
        res = {"B": [], "C+": []}
        for seed in SEEDS:
            dev, test = split(df, mode, seed)
            texts, urg, n = test["text"].tolist(), test["urgent"].tolist(), len(test)
            mb, _ = fit_tuned(dev, prepare_oof(dev, mode, seed, rule_weight=0.0), BASE_COSTS, rule_weight=0.0)
            mn, _ = fit_tuned(dev, prepare_oof(dev, mode, seed, rule_weight=3.0), BASE_COSTS, rule_weight=3.0, safety_net=True)
            for name, m in (("B", mb), ("C+", mn)):
                preds = m.predict(texts)
                met, costs = evaluate(preds, test["category"], test["urgent"], BASE_COSTS)
                fa_q = sum(1 for p, u in zip(preds, urg) if is_abstained(p) and p["urgent"] and not u)
                miss_q = sum(1 for p, u in zip(preds, urg) if is_abstained(p) and not p["urgent"] and u)
                base = costs.sum()
                res[name].append((met["cost_per_100"], (base + 5 * fa_q) / n * 100, (base + 5 * fa_q + 86 * miss_q) / n * 100))
        label = "unseen" if mode == "template" else "seen"
        for name, rows in res.items():
            a = np.array(rows).mean(axis=0)
            print(f"{label:10s} {name:4s} {a[0]:9.1f} {a[1]:26.1f} {a[2]:20.1f}")


if __name__ == "__main__":
    main()
