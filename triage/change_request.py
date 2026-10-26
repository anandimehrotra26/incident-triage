"""Changed-requirement experiments.

Scenario 1 - STRICTER PENALTY for missing urgent cases (miss_urgent 100 -> 300).
   Compare: (a) do nothing (old thresholds), (b) re-tune thresholds only (no retraining, seconds).
Scenario 2 - NEW CATEGORY `cold_chain_excursion`.
   (a) What does the existing system do with the new reports? (does it fail safe or fail silent?)
   (b) How many labelled examples does it take to learn the category, and does it hurt the old categories?
   (c) How fast can the rules baseline adapt (one regex)?

Run:  python -m triage.change_request
"""
import time
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import BASE_COSTS, NEW_CATEGORY, ROUTE_TABLE, STRICT_COSTS
from .costs import evaluate, is_abstained
from .model import MLTriage, tune_thresholds
from .pipeline import load, prepare_oof, random_split, template_split
from .rules import RulesTriage

warnings.filterwarnings("ignore", message="The least populated class")
RESULTS = Path(__file__).resolve().parent.parent / "results"
RULE_WEIGHT = 3.0
SEEDS = [42, 43, 44]
KS = [0, 5, 10, 20, 40, 80]
COLD_RULE = {NEW_CATEGORY: r"\b(reefer|temperatures?|refrigerat\w*|chiller|freezer|cold chain|cold room|logger)\b"}
COLD_URGENT = r"\b(vaccines?|insulin|rising|failed|failure|alarm|frozen)\b"  # second hand-written rule: urgency cue


# --------------------------------------------------------------------- scenario 1
def scenario_strict_penalty():
    df = load()
    rows = []
    for mode, splitter in (("random", random_split), ("template", template_split)):
        for seed in (42, 43, 44, 45, 46):
            dev, test = splitter(df, seed)
            texts = test["text"].tolist()
            for name, rw, net in (("B_tfidf_logreg", 0.0, False), ("C_plus_rule_features", RULE_WEIGHT, False),
                                  ("C+_with_safety_net", RULE_WEIGHT, True)):
                oof = prepare_oof(dev, mode, seed, rule_weight=rw)
                P, pu, classes = oof
                model = MLTriage(rule_weight=rw, safety_net=net).fit(dev["text"].values, dev["category"].values, dev["urgent"].values)
                P_t, pu_t = model.proba(texts)
                t0 = time.perf_counter()
                tu0, tc0, _ = tune_thresholds(dev["text"].values, P, pu, classes, dev["category"].values, dev["urgent"].values, BASE_COSTS, safety_net=net)
                tu1, tc1, _ = tune_thresholds(dev["text"].values, P, pu, classes, dev["category"].values, dev["urgent"].values, STRICT_COSTS, safety_net=net)
                retune_s = time.perf_counter() - t0
                for label, (tu, tc) in (("old thresholds (do nothing)", (tu0, tc0)), ("re-tuned thresholds", (tu1, tc1))):
                    preds = model.decide(texts, P_t, pu_t, t_cat=tc, t_urgent=tu)
                    m, _ = evaluate(preds, test["category"], test["urgent"], STRICT_COSTS)
                    rows.append({"mode": mode, "seed": seed, "approach": name, "policy": label, "t_urgent": tu, "t_cat": tc,
                                 "cost_per_100_strict": m["cost_per_100"], "urgent_recall": m["urgent_recall"],
                                 "urgent_missed": m["urgent_missed_total"], "abstain_rate": m["abstain_rate"],
                                 "costly_misroutes": m["costly_misroutes"], "retune_seconds_both": retune_s})
            # rules baseline: no knob to turn
            preds = RulesTriage().predict(texts)
            m, _ = evaluate(preds, test["category"], test["urgent"], STRICT_COSTS)
            rows.append({"mode": mode, "seed": seed, "approach": "A_rules_baseline", "policy": "no tunable threshold",
                         "t_urgent": None, "t_cat": None, "cost_per_100_strict": m["cost_per_100"],
                         "urgent_recall": m["urgent_recall"], "urgent_missed": m["urgent_missed_total"],
                         "abstain_rate": m["abstain_rate"], "costly_misroutes": m["costly_misroutes"], "retune_seconds_both": 0})
        print(f"scenario 1 [{mode}] done")
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "change_strict_penalty_raw.csv", index=False)
    return out


# --------------------------------------------------------------------- scenario 2
def ext_split(ext, seed, variant):
    rng = np.random.default_rng(seed)
    if variant == "same_template":
        idx = rng.permutation(len(ext))
        n_test = 40
        test_idx = set(idx[:n_test])
        mask = ext.index.isin(test_idx) if False else np.array([i in test_idx for i in range(len(ext))])
    else:  # new_template: hold out 2 of the non-urgent and 1 of the urgent templates
        held = set()
        for u, k in (("N", 2), ("U", 1)):
            tids = sorted(t for t in ext["template_id"].unique() if t.split("|")[1] == u)
            held.update(rng.choice(tids, size=k, replace=False))
        mask = ext["template_id"].isin(held).values
    return ext[~mask].reset_index(drop=True), ext[mask].reset_index(drop=True)


def new_cat_metrics(preds, ext_test, cm):
    true_cats = ext_test["category"].tolist()
    m, _ = evaluate(preds, true_cats, ext_test["urgent"].tolist(), cm)
    n = len(preds)
    cats = np.array([p["category"] for p in preds])
    abst = np.array([is_abstained(p) for p in preds])
    correct = (cats == np.array(true_cats)) & ~abst
    silent = (cats != np.array(true_cats)) & ~abst
    return {"n": n, "recall_auto_correct": float(correct.mean()), "abstain_rate": float(abst.mean()),
            "silent_misroute_rate": float(silent.mean()), "urgent_recall": m["urgent_recall"],
            "cost_per_100": m["cost_per_100"], "where_routed": pd.Series(cats[silent]).value_counts().to_dict()}


def scenario_new_category():
    base = load()
    ext = load("incidents_coldchain_ext.csv")
    cm = BASE_COSTS
    rows = []
    zero_shot_dest = []
    for variant in ("same_template", "new_template"):
        for seed in SEEDS:
            dev, test = random_split(base, seed)
            pool, ext_test = ext_split(ext, seed, variant)
            # --- rules baseline + one regex
            r0 = RulesTriage()
            r1 = RulesTriage(extra_patterns=COLD_RULE)
            r2 = RulesTriage(extra_patterns=COLD_RULE, extra_urgent=COLD_URGENT)
            for lab, r in (("A_rules_baseline (before)", r0), ("A_rules_baseline + category regex", r1),
                           ("A_rules_baseline + category regex + urgency regex", r2)):
                nm = new_cat_metrics(r.predict(ext_test["text"].tolist()), ext_test, cm)
                bm, _ = evaluate(r.predict(test["text"].tolist()), test["category"], test["urgent"], cm)
                rows.append({"variant": variant, "seed": seed, "approach": lab, "k": 0, **{f"new_{k}": v for k, v in nm.items() if k != "where_routed"},
                             "base_cost_per_100": bm["cost_per_100"], "base_acc_auto": bm["auto_accuracy_on_accepted"],
                             "base_costly": bm["costly_misroutes"], "base_abstain": bm["abstain_rate"], "train_seconds": 0.0})
            for name, rw in (("B_tfidf_logreg", 0.0), ("C_plus_rule_features", RULE_WEIGHT)):
                for k in KS:
                    k_eff = min(k, len(pool))
                    add = pool.sample(n=k_eff, random_state=seed) if k_eff else pool.iloc[0:0]
                    dev_k = pd.concat([dev, add], ignore_index=True)
                    t0 = time.perf_counter()
                    oof = prepare_oof(dev_k, "random", seed, rule_weight=rw)
                    model = MLTriage(rule_weight=rw).fit(dev_k["text"].values, dev_k["category"].values, dev_k["urgent"].values)
                    P, pu, classes = oof
                    tu, tc, _ = tune_thresholds(dev_k["text"].values, P, pu, classes, dev_k["category"].values, dev_k["urgent"].values, cm)
                    model.t_urgent, model.t_cat = tu, tc
                    secs = time.perf_counter() - t0
                    nm = new_cat_metrics(model.predict(ext_test["text"].tolist()), ext_test, cm)
                    bm, _ = evaluate(model.predict(test["text"].tolist()), test["category"], test["urgent"], cm)
                    rows.append({"variant": variant, "seed": seed, "approach": name, "k": k, "k_eff": k_eff,
                                 **{f"new_{kk}": v for kk, v in nm.items() if kk != "where_routed"},
                                 "base_cost_per_100": bm["cost_per_100"], "base_acc_auto": bm["auto_accuracy_on_accepted"],
                                 "base_costly": bm["costly_misroutes"], "base_abstain": bm["abstain_rate"], "train_seconds": secs})
                    if k == 0:
                        zero_shot_dest.append({"variant": variant, "seed": seed, "approach": name, **nm["where_routed"]})
        print(f"scenario 2 [{variant}] done")
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "change_new_category_raw.csv", index=False)
    pd.DataFrame(zero_shot_dest).fillna(0).to_csv(RESULTS / "change_new_category_zero_shot_destinations.csv", index=False)
    return out, pd.DataFrame(zero_shot_dest).fillna(0)


# --------------------------------------------------------------------- report
def write_report(s1, s2, dest):
    L = ["# Changed-requirement experiments (auto-generated by `python -m triage.change_request`)\n"]
    L.append("## Scenario 1 - missing an urgent case now costs 300 instead of 100\n")
    L.append("All numbers are evaluated under the NEW (strict) cost model. 'Old thresholds' = the thresholds tuned under the old penalty. "
             "'Re-tuned' = thresholds re-chosen under the new penalty on out-of-fold data; no retraining, no code change except one number in `triage/config.py`.\n")
    g = s1.groupby(["mode", "approach", "policy"]).agg(cost=("cost_per_100_strict", "mean"), cost_sd=("cost_per_100_strict", "std"),
                                                         recall=("urgent_recall", "mean"), missed=("urgent_missed", "mean"),
                                                         abst=("abstain_rate", "mean"), t_urg=("t_urgent", "mean"),
                                                         secs=("retune_seconds_both", "mean")).reset_index()
    for mode in ("random", "template"):
        L.append(f"\n### {mode} regime (mean over 5 seeds)\n")
        L.append("| approach | policy | cost/100 (strict) | urgent recall | urgent missed / seed | abstain rate | mean t_urgent |")
        L.append("|---|---|---|---|---|---|---|")
        for r in g[g["mode"] == mode].itertuples():
            tu = "-" if pd.isna(r.t_urg) else f"{r.t_urg:.2f}"
            L.append(f"| {r.approach} | {r.policy} | {r.cost:.1f} ± {0 if pd.isna(r.cost_sd) else r.cost_sd:.1f} | {r.recall * 100:.1f}% | {r.missed:.1f} | {r.abst * 100:.1f}% | {tu} |")
    L.append(f"\nRe-tuning both cost models (grid of {19 * 17} threshold pairs x 2) took ~{s1['retune_seconds_both'].max():.1f}s at most.\n")

    L.append("\n## Scenario 2 - new category `cold_chain_excursion`\n")
    L.append(f"Config change needed: `ROUTE_TABLE['{NEW_CATEGORY}'] = '{ROUTE_TABLE[NEW_CATEGORY]}'` (already in `triage/config.py`). "
             "The models below are re-trained from labelled examples only.\n")
    L.append("`same_template`: new-category test reports share phrasing with the labelled new-category examples (optimistic). "
             "`new_template`: whole templates held out (harsh).\n")
    L.append("### What the existing system does with the new reports (k = 0 labelled examples)\n")
    z = s2[(s2["k"] == 0)].groupby(["variant", "approach"]).agg(abst=("new_abstain_rate", "mean"), silent=("new_silent_misroute_rate", "mean"),
                                                                 urg=("new_urgent_recall", "mean"), cost=("new_cost_per_100", "mean")).reset_index()
    L.append("| variant | approach | abstained to a human | SILENTLY routed to a wrong team | urgent recall | cost/100 |")
    L.append("|---|---|---|---|---|---|")
    for r in z.itertuples():
        L.append(f"| {r.variant} | {r.approach} | {r.abst * 100:.0f}% | {r.silent * 100:.0f}% | {r.urg * 100:.0f}% | {r.cost:.0f} |")
    L.append("\nWhere the silently misrouted ones went (mean count per seed):\n")
    L.append(dest.groupby(["variant", "approach"]).mean(numeric_only=True).drop(columns=["seed"], errors="ignore").round(1).to_markdown())
    L.append("\n### Learning curve: labelled new-category examples added -> new-category quality and old-category regression\n")
    c = s2[s2["approach"].isin(["B_tfidf_logreg", "C_plus_rule_features"])].groupby(["variant", "approach", "k"]).agg(
        recall=("new_recall_auto_correct", "mean"), silent=("new_silent_misroute_rate", "mean"), abst=("new_abstain_rate", "mean"),
        urg=("new_urgent_recall", "mean"), newcost=("new_cost_per_100", "mean"), baseacc=("base_acc_auto", "mean"),
        basecostly=("base_costly", "mean"), secs=("train_seconds", "mean")).reset_index()
    L.append("| variant | approach | k | new-cat auto-correct | new-cat silent misroute | new-cat abstain | new-cat urgent recall | new-cat cost/100 | OLD categories: accuracy on auto-routed | OLD categories: costly misroutes per seed | retrain s |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in c.itertuples():
        L.append(f"| {r.variant} | {r.approach} | {r.k} | {r.recall * 100:.0f}% | {r.silent * 100:.0f}% | {r.abst * 100:.0f}% | {r.urg * 100:.0f}% | {r.newcost:.0f} | {r.baseacc * 100:.1f}% | {r.basecostly:.1f} | {r.secs:.1f} |")
    a = s2[s2["approach"].str.startswith("A_")].groupby(["variant", "approach"]).agg(
        recall=("new_recall_auto_correct", "mean"), silent=("new_silent_misroute_rate", "mean"), abst=("new_abstain_rate", "mean"),
        urg=("new_urgent_recall", "mean"), newcost=("new_cost_per_100", "mean"), baseacc=("base_acc_auto", "mean"),
        basecostly=("base_costly", "mean")).reset_index()
    L.append("\n### Rules baseline before/after hand-written rules (no labelled data, no training)\n")
    L.append("The category regex and the urgency regex were written by the same author who wrote the generator's cold-chain templates, so this is an upper bound for what rules adaptation achieves.\n")
    L.append("| variant | approach | new-cat auto-correct | silent misroute | abstain | urgent recall | new-cat cost/100 | OLD categories: accuracy on auto-routed | OLD categories: costly misroutes per seed |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in a.itertuples():
        L.append(f"| {r.variant} | {r.approach} | {r.recall * 100:.0f}% | {r.silent * 100:.0f}% | {r.abst * 100:.0f}% | {r.urg * 100:.0f}% | {r.newcost:.0f} | {r.baseacc * 100:.1f}% | {r.basecostly:.1f} |")
    (RESULTS / "CHANGE_REQUEST.md").write_text("\n".join(L) + "\n")

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), sharey=True)
    for ax, variant in zip(axes, ("same_template", "new_template")):
        for name, col in (("B_tfidf_logreg", "#5b8def"), ("C_plus_rule_features", "#2a9d8f")):
            d = c[(c["variant"] == variant) & (c["approach"] == name)]
            ax.plot(d["k"], d["recall"] * 100, marker="o", color=col, label=f"{name}: auto-correct")
            ax.plot(d["k"], d["silent"] * 100, marker="x", ls="--", color=col, label=f"{name}: silent misroute")
        ax.set_title(variant, fontsize=10)
        ax.set_xlabel("labelled new-category examples added")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("% of new-category test reports")
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(RESULTS / "figures" / "new_category_learning_curve.png", dpi=140)
    plt.close(fig)


def main():
    RESULTS.mkdir(exist_ok=True)
    s1 = scenario_strict_penalty()
    s2, dest = scenario_new_category()
    write_report(s1, s2, dest)
    print("wrote results/CHANGE_REQUEST.md and figures/new_category_learning_curve.png")


if __name__ == "__main__":
    main()
