"""Command-line triage.

  python -m triage.cli "driver is bleeding after a collision on the expressway"
  python -m triage.cli --file reports.csv --column text --out triaged.csv
"""
import argparse
import json

import joblib
import pandas as pd

from .model import route_of
from .train import MODEL_PATH


def load_model():
    if not MODEL_PATH.exists():
        raise SystemExit("No trained model. Run:  python -m triage.train")
    blob = joblib.load(MODEL_PATH)
    return blob["model"], blob["meta"]


def triage_text(model, text, t_urgent=None, t_cat=None):
    P, pu = model.proba([text])
    pred = model.decide([text], P, pu, t_cat=t_cat, t_urgent=t_urgent)[0]
    order = P[0].argsort()[::-1][:3]
    r = route_of(pred)
    return {"category": pred["category"], "p_category": round(pred["p_category"], 3), "urgent": pred["urgent"],
            "p_urgent": round(pred["p_urgent"], 3), **r,
            "top3": [(model.classes_[i], round(float(P[0, i]), 3)) for i in order]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?")
    ap.add_argument("--file")
    ap.add_argument("--column", default="text")
    ap.add_argument("--out")
    a = ap.parse_args()
    model, meta = load_model()
    if a.file:
        df = pd.read_csv(a.file)
        res = [triage_text(model, t) for t in df[a.column].astype(str)]
        out = pd.concat([df, pd.DataFrame(res)], axis=1)
        out.to_csv(a.out or "triaged.csv", index=False)
        print(f"wrote {a.out or 'triaged.csv'}: {int(out['needs_human'].sum())}/{len(out)} sent to human review, "
              f"{int((out['priority'] == 'URGENT').sum())} flagged URGENT")
    elif a.text:
        print(json.dumps(triage_text(model, a.text), indent=2))
    else:
        ap.error("give a text or --file")


if __name__ == "__main__":
    main()
