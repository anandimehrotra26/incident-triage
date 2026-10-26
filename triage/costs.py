"""Cost-weighted evaluation of routing decisions."""
from collections import Counter

import numpy as np
from sklearn.metrics import f1_score

from .config import HUMAN_REVIEW, SAFETY_CRITICAL, CostModel


def is_abstained(pred):
    return bool(pred["abstain"]) or pred["category"] == HUMAN_REVIEW


def report_cost(true_cat, true_urgent, pred, cm: CostModel):
    """Return (total_cost, Counter of event types) for one report."""
    ev = Counter()
    cost = 0.0
    missed = bool(true_urgent) and not pred["urgent"]
    if is_abstained(pred):
        ev["review"] += 1
        cost += cm.human_review
        if missed:  # urgent report waits in the normal review queue
            ev["abstain_urgent_delay"] += 1
            cost += cm.abstain_urgent_delay
        return cost, ev
    if missed:
        ev["missed_urgent"] += 1
        cost += cm.miss_urgent
    if (not true_urgent) and pred["urgent"]:
        ev["false_urgent"] += 1
        cost += cm.false_urgent
    if pred["category"] != true_cat:
        if true_cat in SAFETY_CRITICAL:
            ev["wrong_team_critical"] += 1
            cost += cm.wrong_team_critical
        else:
            ev["wrong_team"] += 1
            cost += cm.wrong_team
    return cost, ev


def evaluate(preds, true_cats, true_urgs, cm: CostModel):
    n = len(preds)
    costs = np.zeros(n)
    events = Counter()
    for i, (p, c, u) in enumerate(zip(preds, true_cats, true_urgs)):
        costs[i], ev = report_cost(c, u, p, cm)
        events.update(ev)
    abst = np.array([is_abstained(p) for p in preds])
    pred_cat = np.array([p["category"] for p in preds])
    pred_urg = np.array([bool(p["urgent"]) for p in preds])
    true_cat = np.array(true_cats)
    true_urg = np.array(true_urgs).astype(bool)

    auto = ~abst
    correct_auto = (pred_cat == true_cat) & auto
    urg_pos = true_urg.sum()
    m = {
        "n": n,
        "cost_total": float(costs.sum()),
        "cost_per_100": float(costs.mean() * 100),
        "events": dict(events),
        "abstain_rate": float(abst.mean()),
        "auto_accuracy_on_accepted": float(correct_auto.sum() / max(auto.sum(), 1)),
        "auto_correct_share_of_all": float(correct_auto.sum() / n),
        "macro_f1_all": float(f1_score(true_cat, pred_cat, average="macro", zero_division=0)),
        "urgent_recall": float((pred_urg & true_urg).sum() / max(urg_pos, 1)),
        "urgent_precision": float((pred_urg & true_urg).sum() / max(pred_urg.sum(), 1)),
        "urgent_missed_total": int((true_urg & ~pred_urg).sum()),  # regardless of abstention
        "urgent_n": int(urg_pos),
        "costly_misroutes": int(events.get("missed_urgent", 0) + events.get("wrong_team_critical", 0)),
    }
    return m, costs


def manual_only_cost_per_100(cm: CostModel):
    """Reference: a human reads every report (assumed perfect). Optimistic for the human."""
    return cm.human_review * 100.0


def manual_fifo_cost_per_100(cm: CostModel, urgent_rate):
    """Reference: a human reads every report in arrival order (no urgent flag), so every urgent report pays the
    queue-delay penalty. Perfect-prioritisation reference is `manual_only_cost_per_100`."""
    return (cm.human_review + cm.abstain_urgent_delay * urgent_rate) * 100.0
