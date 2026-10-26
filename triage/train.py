"""Train the deployable model and save it to models/triage_model.joblib.

  python -m triage.train                    # conservative thresholds (tuned on unseen-template out-of-fold data)
  python -m triage.train --regime random    # thresholds tuned on random folds (more automation, optimistic)
  python -m triage.train --data incidents_reviewed.csv

Deployed variant = approach C+ (TF-IDF logistic regression + rule features + urgent safety net).
"""
import argparse
import hashlib
import time
from pathlib import Path

import joblib

from .config import BASE_COSTS, STRICT_COSTS
from .model import MLTriage, tune_thresholds
from .pipeline import DATA, load, prepare_oof

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "triage_model.joblib"
RULE_WEIGHT = 3.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="incidents.csv")
    ap.add_argument("--regime", choices=["template", "random"], default="template")
    ap.add_argument("--strict", action="store_true", help="tune thresholds under the strict urgent-miss penalty (300)")
    ap.add_argument("--extra", default=None, help="optional extra labelled CSV (e.g. incidents_coldchain_ext.csv) to add new categories")
    a = ap.parse_args()
    import pandas as pd
    df = load(a.data)
    if a.extra:
        df = pd.concat([df, load(a.extra)], ignore_index=True)
    cm = STRICT_COSTS if a.strict else BASE_COSTS
    t0 = time.time()
    oof = prepare_oof(df, a.regime, seed=42, rule_weight=RULE_WEIGHT)
    model = MLTriage(rule_weight=RULE_WEIGHT, safety_net=True).fit(df["text"].values, df["category"].values, df["urgent"].values)
    P, pu, classes = oof
    tu, tc, _ = tune_thresholds(df["text"].values, P, pu, classes, df["category"].values, df["urgent"].values, cm, safety_net=True)
    model.t_urgent, model.t_cat = tu, tc
    meta = {"data": a.data, "extra": a.extra, "n_train": len(df), "regime": a.regime, "strict": a.strict, "t_urgent": tu, "t_cat": tc,
            "classes": model.classes_, "data_sha256": hashlib.sha256((DATA / a.data).read_bytes()).hexdigest()[:16],
            "trained_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump({"model": model, "meta": meta}, MODEL_PATH)
    print(f"trained on {len(df)} reports in {time.time() - t0:.1f}s -> {MODEL_PATH}\n{meta}")


if __name__ == "__main__":
    main()
