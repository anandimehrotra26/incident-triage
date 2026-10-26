"""Main evaluation: rules baseline vs TF-IDF/LogReg vs TF-IDF/LogReg + rule features.

Two test regimes (both reported, neither hidden):
  random   - stratified random split. Test phrasings also appear in training (optimistic).
  template - ~25% of message templates are held out entirely (pessimistic: novel phrasing).
Each regime is repeated over 5 seeds. Seed 42 gets the detailed artefacts (errors, latency, figures).

Run:  python -m triage.evaluate
"""
import json
import pickle
import time
from dataclasses import asdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

from .config import (ASSUMED_CPU_USD_PER_HOUR, ASSUMED_HUMAN_REVIEW_MINUTES, ASSUMED_HUMAN_USD_PER_HOUR,
                     BASE_CATEGORIES, BASE_COSTS, SEED)
from .costs import evaluate, is_abstained, manual_fifo_cost_per_100, manual_only_cost_per_100, report_cost
from .model import time_single
from .pipeline import bootstrap_ci, fit_tuned, load, prepare_oof, split
from .rules import RulesTriage

RESULTS = Path(__file__).resolve().parent.parent / "results"
SEEDS = [42, 43, 44, 45, 46]
RULE_WEIGHT = 3.0  # chosen with dev-only grouped CV (see docs/MODEL_SELECTION.md)

A_RULES = "A_rules_baseline"
B_ML = "B_tfidf_logreg"
C_MLR = "C_tfidf_logreg_plus_rule_features"
C_NET = "C+_with_urgent_safety_net"


def run_regime(df, mode, seed, cm):
    dev, test = split(df, mode, seed)
    texts = test["text"].tolist()
    out = {}
    rules = RulesTriage()
    out[A_RULES] = {"model": rules, "info": {}, "preds": rules.predict(texts)}
    oof_b = prepare_oof(dev, mode, seed, rule_weight=0.0)
    mb, ib = fit_tuned(dev, oof_b, cm, rule_weight=0.0)
    out[B_ML] = {"model": mb, "info": ib, "preds": mb.predict(texts)}
    oof_c = prepare_oof(dev, mode, seed, rule_weight=RULE_WEIGHT)
    mc, ic = fit_tuned(dev, oof_c, cm, rule_weight=RULE_WEIGHT)
    out[C_MLR] = {"model": mc, "info": ic, "preds": mc.predict(texts)}
    mn, inn = fit_tuned(dev, oof_c, cm, rule_weight=RULE_WEIGHT, safety_net=True)
    out[C_NET] = {"model": mn, "info": inn, "preds": mn.predict(texts)}
    for k, v in out.items():
        v["metrics"], v["costs"] = evaluate(v["preds"], test["category"], test["urgent"], cm)
    return dev, test, out


def ece(conf, correct, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    e = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            e += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(e)


def error_table(test, preds, cm):
    rows = []
    for t, p in zip(test.itertuples(), preds):
        cost, ev = report_cost(t.category, t.urgent, p, cm)
        kind = "ok" if cost == 0 else (sorted(ev)[0] if ev else "other")
        if is_abstained(p) and kind == "review":
            kind = "abstained"
        rows.append({"id": t.id, "text": t.text, "true_category": t.category, "true_urgent": t.urgent,
                     "pred_category": p["category"], "pred_urgent": int(p["urgent"]),
                     "abstained": int(is_abstained(p)), "p_category": p["p_category"], "p_urgent": p["p_urgent"],
                     "cost": cost, "event": "+".join(sorted(ev)) if ev else "", "hard": t.hard,
                     "template_id": t.template_id, "label_noise_injected": t.label_noise_injected})
    return pd.DataFrame(rows)


def main():
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "figures").mkdir(exist_ok=True)
    df = load()
    cm = BASE_COSTS
    summary = {"cost_model": asdict(cm), "seeds": SEEDS, "regimes": {}}
    per_seed = {}
    detail = {}
    for mode in ("random", "template"):
        per_seed[mode] = {}
        for seed in SEEDS:
            t0 = time.time()
            dev, test, out = run_regime(df, mode, seed, cm)
            per_seed[mode][seed] = {k: v["metrics"] | {"thresholds": {x: v["info"].get(x) for x in ("t_urgent", "t_cat")}}
                                    for k, v in out.items()}
            per_seed[mode][seed]["_manual_only_cost_per_100"] = manual_only_cost_per_100(cm)
            per_seed[mode][seed]["_test_n"] = len(test)
            print(f"[{mode} seed {seed}] done in {time.time() - t0:.1f}s | " + " | ".join(
                f"{k.split('_')[0]}:{v['metrics']['cost_per_100']:.0f}" for k, v in out.items()))
            if seed == SEED:
                detail[mode] = (dev, test, out)
    summary["per_seed"] = {m: {str(s): v for s, v in d.items()} for m, d in per_seed.items()}

    # ---- aggregates
    agg = {}
    for mode in per_seed:
        agg[mode] = {}
        for a in (A_RULES, B_ML, C_MLR, C_NET):
            rows = [per_seed[mode][s][a] for s in SEEDS]
            agg[mode][a] = {k: {"mean": float(np.mean([r[k] for r in rows])), "sd": float(np.std([r[k] for r in rows]))}
                            for k in ("cost_per_100", "abstain_rate", "urgent_recall", "urgent_missed_total",
                                      "costly_misroutes", "auto_accuracy_on_accepted", "macro_f1_all")}
    summary["aggregate"] = agg

    # ---- detailed artefacts for primary seed
    summary["primary"] = {}
    for mode, (dev, test, out) in detail.items():
        block = {"n_dev": len(dev), "n_test": len(test), "n_urgent_test": int(test["urgent"].sum()), "approaches": {}}
        for a, v in out.items():
            lo, hi = bootstrap_ci(v["costs"])
            texts = test["text"].tolist()
            lat = time_single(v["model"], texts)
            entry = {"metrics": v["metrics"], "cost_per_100_ci95": [lo, hi], "latency": lat,
                     "thresholds": {x: v["info"].get(x) for x in ("t_urgent", "t_cat")}}
            entry["cpu_usd_per_1000_reports"] = lat["mean_ms"] / 3.6e6 * ASSUMED_CPU_USD_PER_HOUR * 1000
            if hasattr(v["model"], "feat"):
                t0 = time.perf_counter()
                v["model"].__class__(rule_weight=v["model"].rule_weight).fit(dev["text"].values, dev["category"].values, dev["urgent"].values)
                entry["fit_seconds"] = time.perf_counter() - t0
                entry["model_bytes"] = len(pickle.dumps(v["model"]))
            block["approaches"][a] = entry
            err = error_table(test, v["preds"], cm)
            err.to_csv(RESULTS / f"errors_{mode}_{a}.csv", index=False)
        summary["primary"][mode] = block

    # calibration + coverage-accuracy for approach C
    for mode, (dev, test, out) in detail.items():
        m = out[C_MLR]["model"]
        P, pu = m.proba(test["text"].tolist())
        conf = P.max(1)
        pred = np.array(m.classes_)[P.argmax(1)]
        correct = (pred == test["category"].values).astype(float)
        summary["primary"][mode]["calibration_ece_C"] = ece(conf, correct)
        curve = []
        for tc in np.round(np.arange(0.0, 0.96, 0.05), 2):
            preds = m.decide(test["text"].tolist(), P, pu, t_cat=tc)
            mm, _ = evaluate(preds, test["category"], test["urgent"], cm)
            curve.append({"t_cat": float(tc), "coverage": 1 - mm["abstain_rate"],
                          "accuracy_on_accepted": mm["auto_accuracy_on_accepted"], "cost_per_100": mm["cost_per_100"]})
        summary["primary"][mode]["coverage_curve_C"] = curve
        # label-noise ceiling: how many test rows carry an injected wrong recorded label
        summary["primary"][mode]["injected_label_noise_in_test"] = int(test["label_noise_injected"].sum())

    # ---- human-readable dollars (assumptions!)
    summary["assumptions"] = {"cpu_usd_per_hour": ASSUMED_CPU_USD_PER_HOUR,
                              "human_review_minutes": ASSUMED_HUMAN_REVIEW_MINUTES,
                              "human_usd_per_hour": ASSUMED_HUMAN_USD_PER_HOUR,
                              "human_usd_per_review": ASSUMED_HUMAN_REVIEW_MINUTES / 60 * ASSUMED_HUMAN_USD_PER_HOUR}

    with open(RESULTS / "results.json", "w") as f:
        json.dump(summary, f, indent=2, default=float)

    plot_all(summary, detail)
    write_markdown(summary)
    # persist the primary deployable model (template regime = the harsher, safer-to-trust estimate)
    print("wrote results/results.json, RESULTS.md, figures/")


# ------------------------------------------------------------------ plots
def plot_all(summary, detail):
    agg = summary["aggregate"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    names = [A_RULES, B_ML, C_MLR, C_NET]
    short = ["A rules", "B tfidf-LR", "C +rule feats", "C + safety net"]
    for ax, mode, title in zip(axes, ("random", "template"), ("Random split (optimistic)", "Unseen-template split (harsh)")):
        means = [agg[mode][a]["cost_per_100"]["mean"] for a in names]
        sds = [agg[mode][a]["cost_per_100"]["sd"] for a in names]
        ax.bar(short, means, yerr=sds, capsize=4, color=["#9aa5b1", "#5b8def", "#2a9d8f", "#e9a23b"])
        ax.axhline(manual_only_cost_per_100(BASE_COSTS), color="crimson", ls="--", lw=1)
        ax.text(0.02, manual_only_cost_per_100(BASE_COSTS) + 6, "human reads everything", color="crimson", fontsize=8)
        ax.set_title(title, fontsize=10)
        ax.tick_params(axis="x", rotation=20)
    axes[0].set_ylabel("expected cost per 100 reports (lower is better)")
    fig.suptitle("Cost per 100 reports, mean ± sd over 5 seeds")
    fig.tight_layout()
    fig.savefig(RESULTS / "figures" / "cost_comparison.png", dpi=140)
    plt.close(fig)

    for mode, (dev, test, out) in detail.items():
        m = out[C_MLR]["model"]
        preds = out[C_MLR]["preds"]
        labels = list(m.classes_)
        y = test["category"].values
        yp = np.array([p["category"] for p in preds])
        cmx = confusion_matrix(y, yp, labels=labels)
        fig, ax = plt.subplots(figsize=(6.5, 5.5))
        ax.imshow(cmx, cmap="Blues")
        ax.set_xticks(range(len(labels)), labels, rotation=60, ha="right", fontsize=7)
        ax.set_yticks(range(len(labels)), labels, fontsize=7)
        for i in range(len(labels)):
            for j in range(len(labels)):
                if cmx[i, j]:
                    ax.text(j, i, cmx[i, j], ha="center", va="center", fontsize=7,
                            color="white" if cmx[i, j] > cmx.max() / 2 else "black")
        ax.set_xlabel("predicted (argmax, before abstention)")
        ax.set_ylabel("recorded label")
        ax.set_title(f"Approach C confusion matrix - {mode} split, seed {SEED}", fontsize=9)
        fig.tight_layout()
        fig.savefig(RESULTS / "figures" / f"confusion_C_{mode}.png", dpi=140)
        plt.close(fig)

        curve = summary["primary"][mode]["coverage_curve_C"]
        fig, ax = plt.subplots(figsize=(5.5, 4))
        ax.plot([c["coverage"] for c in curve], [c["accuracy_on_accepted"] for c in curve], marker="o", ms=3)
        ax.set_xlabel("coverage (share auto-routed)")
        ax.set_ylabel("category accuracy on auto-routed")
        ax.set_title(f"Abstention trade-off, approach C, {mode} split", fontsize=9)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(RESULTS / "figures" / f"coverage_accuracy_C_{mode}.png", dpi=140)
        plt.close(fig)


# ------------------------------------------------------------------ markdown
def fmt(x, d=1):
    return f"{x:.{d}f}"


def write_markdown(s):
    L = []
    cm = s["cost_model"]
    L.append("# Results (auto-generated by `python -m triage.evaluate` - do not edit by hand)\n")
    L.append("Cost units are ASSUMPTIONS, see `triage/config.py`: " + ", ".join(f"{k}={v}" for k, v in cm.items()) + ".\n")
    ur = s["primary"]["random"]["n_urgent_test"] / s["primary"]["random"]["n_test"]
    L.append(f"Human-reads-everything references: **{manual_only_cost_per_100(BASE_COSTS):.0f} per 100 reports** if the queue is perfectly "
             f"prioritised and the human is always right (best case for the human), or **{manual_fifo_cost_per_100(BASE_COSTS, ur):.0f}** "
             f"if reports are read first-in-first-out so urgent ones wait (urgent share {ur:.1%}).\n")
    for mode, title in (("random", "Random stratified split (optimistic: test phrasings also seen in training)"),
                        ("template", "Unseen-template split (harsh: core phrasing of test reports never seen in training)")):
        L.append(f"\n## {title}\n")
        L.append("Mean ± sd over 5 seeds; count columns are the mean per seed (test sets have ~180 / ~270 reports). "
                 "`urgent missed` = truly urgent reports NOT flagged urgent (including ones sent to a human). "
                 "`costly misroutes` = urgent reports auto-routed as standard + safety-critical reports auto-routed to the wrong team.\n")
        L.append("| approach | cost / 100 | abstain rate | urgent recall | urgent missed (count/seed) | costly misroutes (count/seed) | accuracy on auto-routed |")
        L.append("|---|---|---|---|---|---|---|")
        for a, v in s["aggregate"][mode].items():
            L.append(f"| {a} | {fmt(v['cost_per_100']['mean'])} ± {fmt(v['cost_per_100']['sd'])} | "
                     f"{fmt(v['abstain_rate']['mean'] * 100)}% | {fmt(v['urgent_recall']['mean'] * 100)}% | "
                     f"{fmt(v['urgent_missed_total']['mean'])} | {fmt(v['costly_misroutes']['mean'])} | "
                     f"{fmt(v['auto_accuracy_on_accepted']['mean'] * 100)}% |")
        p = s["primary"][mode]
        L.append(f"\n### Seed {SEED} detail ({mode}): n_test={p['n_test']}, urgent in test={p['n_urgent_test']}, "
                 f"injected label noise in test={p['injected_label_noise_in_test']}\n")
        L.append("| approach | cost / 100 [95% bootstrap CI] | thresholds (urgent, category) | median / p95 latency ms | CPU $ per 1,000 reports | fit s | model KB |")
        L.append("|---|---|---|---|---|---|---|")
        for a, e in p["approaches"].items():
            th = e["thresholds"]
            ths = "-" if th["t_urgent"] is None else f"{th['t_urgent']:.2f}, {th['t_cat']:.2f}"
            L.append(f"| {a} | {fmt(e['metrics']['cost_per_100'])} [{fmt(e['cost_per_100_ci95'][0])}, {fmt(e['cost_per_100_ci95'][1])}] | "
                     f"{ths} | {e['latency']['median_ms']:.2f} / {e['latency']['p95_ms']:.2f} | "
                     f"{e['cpu_usd_per_1000_reports']:.6f} | {e.get('fit_seconds', 0):.2f} | {e.get('model_bytes', 0) / 1024:.0f} |")
        L.append(f"\nCategory-confidence calibration (ECE) of approach C: {p['calibration_ece_C']:.3f}\n")
        ev = {a: e["metrics"]["events"] for a, e in p["approaches"].items()}
        L.append("Event counts on the test set (seed 42): ")
        for a, e in ev.items():
            L.append(f"- {a}: {json.dumps(e)}")
    L.append("\n![cost](figures/cost_comparison.png)\n")
    (RESULTS / "RESULTS.md").write_text("\n".join(L))


if __name__ == "__main__":
    main()
