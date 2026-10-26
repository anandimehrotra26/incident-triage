"""Independent label review tooling.

  python -m triage.review make                         # build a blind 60-report review sheet
  python -m triage.review score <completed_sheet.csv>  # agreement stats + disagreement list
  python -m triage.review apply <completed_sheet.csv>  # write data/incidents_reviewed.csv (adjudicated labels)

The sheet NEVER contains the recorded labels, so the reviewer is blind to them. The reviewer must be a person who
did not write the generator or the labels (see data/review/REVIEWER_INSTRUCTIONS.md). As shipped, the review
is PENDING: no completed sheet exists in this repo until a human fills one in.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from .config import BASE_CATEGORIES

ROOT = Path(__file__).resolve().parent.parent
REVIEW_DIR = ROOT / "data" / "review"
N_REVIEW = 60


def make(seed=7):
    df = pd.read_csv(ROOT / "data" / "incidents.csv")
    rng = np.random.default_rng(seed)
    picks = []
    for c in BASE_CATEGORIES:  # 4 per recorded category so rare classes are covered
        ids = df[df["category"] == c]["id"].values
        picks += list(rng.choice(ids, size=min(4, len(ids)), replace=False))
    rest = df[~df["id"].isin(picks)]["id"].values
    picks += list(rng.choice(rest, size=N_REVIEW - len(picks), replace=False))
    rng.shuffle(picks)
    sheet = df.set_index("id").loc[picks, ["text"]].reset_index()
    sheet["reviewer_category"] = ""
    sheet["reviewer_urgent_0or1"] = ""
    sheet["reviewer_notes"] = ""
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    sheet.to_csv(REVIEW_DIR / "review_sheet_blank.csv", index=False)
    print(f"wrote {REVIEW_DIR / 'review_sheet_blank.csv'} with {len(sheet)} reports (labels hidden)")


def _load_completed(path):
    r = pd.read_csv(path, dtype=str).fillna("")
    r = r[(r["reviewer_category"] != "") & (r["reviewer_urgent_0or1"] != "")]
    if len(r) < 50:
        print(f"WARNING: only {len(r)} completed rows; the brief asks for at least 50")
    gold = pd.read_csv(ROOT / "data" / "incidents.csv").set_index("id")
    r = r.join(gold[["category", "urgent", "category_true", "label_noise_injected"]], on="id")
    r["reviewer_urgent"] = r["reviewer_urgent_0or1"].astype(int)
    return r


def score(path, out_dir=None):
    r = _load_completed(path)
    bad = set(r["reviewer_category"]) - set(BASE_CATEGORIES)
    if bad:
        sys.exit(f"unknown category labels in sheet: {bad}")
    cat_agree = (r["reviewer_category"] == r["category"]).mean()
    urg_agree = (r["reviewer_urgent"] == r["urgent"].astype(int)).mean()
    k_cat = cohen_kappa_score(r["reviewer_category"], r["category"])
    k_urg = cohen_kappa_score(r["reviewer_urgent"], r["urgent"].astype(int))
    dis = r[(r["reviewer_category"] != r["category"]) | (r["reviewer_urgent"] != r["urgent"].astype(int))]
    L = [f"# Label review report (n={len(r)})\n",
         f"- category agreement: {cat_agree:.1%}, Cohen's kappa {k_cat:.3f}",
         f"- urgent agreement:   {urg_agree:.1%}, Cohen's kappa {k_urg:.3f}",
         f"- disagreements: {len(dis)}\n",
         "## Disagreements (adjudicate each: fill final_category / final_urgent in the sheet, then run `apply`)\n",
         "| id | text | recorded | reviewer | notes |", "|---|---|---|---|---|"]
    for t in dis.itertuples():
        L.append(f"| {t.id} | {t.text} | {t.category}/{t.urgent} | {t.reviewer_category}/{t.reviewer_urgent} | {t.reviewer_notes} |")
    # simulation-only diagnostic: did the reviewer catch the deliberately injected noise?
    inj = r[r["label_noise_injected"].astype(int) == 1]
    caught = int((inj["reviewer_category"] == inj["category_true"]).sum())
    L.append(f"\n## Simulation-only diagnostic\nInjected label-noise rows in the sample: {len(inj)}; of those the reviewer's label equals the "
             f"generator's true category in {caught}. (A real dataset has no such column.)")
    out = Path(out_dir or REVIEW_DIR) / "review_report.md"
    out.write_text("\n".join(L))
    print("\n".join(L[:4]))
    print(f"full report: {out}")


def apply(path):
    r = _load_completed(path)
    df = pd.read_csv(ROOT / "data" / "incidents.csv")
    fc = r.set_index("id")
    n_changed = 0
    for i, row in df.iterrows():
        if row["id"] in fc.index:
            f = fc.loc[row["id"]]
            new_c = f.get("final_category", "") or f["reviewer_category"]
            new_u = int(f.get("final_urgent", "") or f["reviewer_urgent"])
            if new_c != row["category"] or new_u != row["urgent"]:
                n_changed += 1
                df.loc[i, "category"], df.loc[i, "urgent"] = new_c, new_u
    df.to_csv(ROOT / "data" / "incidents_reviewed.csv", index=False)
    print(f"wrote data/incidents_reviewed.csv ({n_changed} labels changed). Re-run evaluation on it by pointing triage.pipeline.load() at that file.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "make"
    if cmd == "make":
        make()
    elif cmd == "score":
        score(sys.argv[2])
    elif cmd == "apply":
        apply(sys.argv[2])
    else:
        sys.exit(__doc__)
