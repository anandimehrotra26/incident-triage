"""Shared helpers: loading, splitting, fitting + tuning. Used by evaluate.py and change_request.py."""
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from .config import TEST_SIZE
from .model import MLTriage, oof_probabilities, tune_thresholds

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def load(name="incidents.csv"):
    df = pd.read_csv(DATA / name)
    df["urgent"] = df["urgent"].astype(int)
    return df


def random_split(df, seed):
    """Standard stratified split: test reports share templates with training reports (optimistic)."""
    dev, test = train_test_split(df, test_size=TEST_SIZE, stratify=df["category"], random_state=seed)
    return dev.reset_index(drop=True), test.reset_index(drop=True)


def template_split(df, seed, frac=0.25):
    """Hold out ~25% of the *templates* in every (category, urgency) group: the test set only
    contains phrasings the model has never seen the core of. Much harsher; closer to real novelty."""
    rng = random.Random(seed)
    groups = {}
    for tid in sorted(df["template_id"].unique()):
        cat, u, _ = tid.split("|")
        groups.setdefault((cat, u), []).append(tid)
    held = set()
    for key, tids in groups.items():
        if len(tids) >= 2:
            rng.shuffle(tids)
            held.update(tids[: max(1, math.ceil(frac * len(tids)))])
    mask = df["template_id"].isin(held)
    return df[~mask].reset_index(drop=True), df[mask].reset_index(drop=True)


def split(df, mode, seed):
    return random_split(df, seed) if mode == "random" else template_split(df, seed)


def prepare_oof(dev, mode, seed, rule_weight=0.0, C=10.0):
    groups = dev["template_id"].values if mode == "template" else None
    return oof_probabilities(dev["text"].values, dev["category"].values, dev["urgent"].values,
                             groups=groups, seed=seed, rule_weight=rule_weight, C=C)


def fit_tuned(dev, oof, cm, safety_net=False, tune=True, rule_weight=0.0, C=10.0):
    """Fit on all dev data; tune thresholds on the out-of-fold predictions."""
    P, pu, classes = oof
    model = MLTriage(safety_net=safety_net, rule_weight=rule_weight, C=C).fit(dev["text"].values, dev["category"].values, dev["urgent"].values)
    info = {"t_urgent": 0.5, "t_cat": 0.5}
    if tune:
        tu, tc, grid = tune_thresholds(dev["text"].values, P, pu, classes, dev["category"].values,
                                       dev["urgent"].values, cm, safety_net=safety_net)
        model.t_urgent, model.t_cat = tu, tc
        info = {"t_urgent": tu, "t_cat": tc}
        info["grid"] = grid
    return model, info


def bootstrap_ci(costs, n_boot=2000, seed=0):
    rng = np.random.default_rng(seed)
    costs = np.asarray(costs)
    means = [rng.choice(costs, size=len(costs), replace=True).mean() * 100 for _ in range(n_boot)]
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
