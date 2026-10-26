"""Approach B - TF-IDF (word + char n-grams) + logistic regression, with calibrated-ish
probabilities, a cost-tuned urgent threshold and a confidence-based abstention policy.
Approach C - the same model plus a rules "safety net" that can only ADD urgent flags.
"""
import time
from itertools import product

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, StratifiedKFold

from .config import HUMAN_REVIEW, ROUTE_TABLE, CostModel
from .costs import evaluate
from .rules import rule_features, strong_urgent_cue


class Featurizer:
    def __init__(self, rule_weight=0.0):
        self.rule_weight = rule_weight  # 0 = pure text model; >0 adds negation-aware rule-hit features
        self.word = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, lowercase=True, min_df=1)
        self.char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, lowercase=True, min_df=2)

    def fit(self, texts):
        self.word.fit(texts)
        self.char.fit(texts)
        return self

    def transform(self, texts):
        blocks = [self.word.transform(texts), self.char.transform(texts)]
        if self.rule_weight > 0:
            blocks.append(csr_matrix(rule_features(list(texts), self.rule_weight)))
        return hstack(blocks).tocsr()


class MLTriage:
    """Two logistic-regression heads (category, urgent) on shared TF-IDF features."""

    def __init__(self, t_urgent=0.5, t_cat=0.5, C=10.0, safety_net=False, rule_weight=0.0, name=None):
        self.t_urgent, self.t_cat, self.C, self.safety_net = t_urgent, t_cat, C, safety_net
        self.rule_weight = rule_weight
        base = "tfidf_logreg" if rule_weight == 0 else "tfidf_logreg_rulefeats"
        self.name = name or (base + ("+safety_net" if safety_net else ""))

    # -------- training
    def fit(self, texts, cats, urgs):
        self.feat = Featurizer(self.rule_weight).fit(texts)
        X = self.feat.transform(texts)
        self.cat_clf = LogisticRegression(C=self.C, max_iter=3000, class_weight="balanced").fit(X, cats)
        self.urg_clf = LogisticRegression(C=self.C, max_iter=3000, class_weight="balanced").fit(X, np.asarray(urgs).astype(int))
        self.classes_ = list(self.cat_clf.classes_)
        return self

    # -------- inference
    def proba(self, texts):
        X = self.feat.transform(texts)
        return self.cat_clf.predict_proba(X), self.urg_clf.predict_proba(X)[:, 1]

    def decide(self, texts, P_cat, p_urg, t_cat=None, t_urgent=None):
        t_cat = self.t_cat if t_cat is None else t_cat
        t_urgent = self.t_urgent if t_urgent is None else t_urgent
        out = []
        idx = P_cat.argmax(axis=1)
        for i, t in enumerate(texts):
            label = self.classes_[idx[i]]
            pmax = float(P_cat[i, idx[i]])
            urgent = bool(p_urg[i] >= t_urgent)
            if self.safety_net and strong_urgent_cue(t):
                urgent = True
            out.append({"category": label, "p_category": pmax, "urgent": urgent, "p_urgent": float(p_urg[i]),
                        "abstain": pmax < t_cat or label == HUMAN_REVIEW})
        return out

    def explain(self, text, top=5):
        """Top word n-grams pushing the predicted category, and the rule hits that fed the model (for the demo)."""
        X = self.feat.transform([text])
        j = int(self.cat_clf.predict_proba(X).argmax())
        n_word = len(self.feat.word.vocabulary_)
        w = X[:, :n_word].multiply(self.cat_clf.coef_[j, :n_word]).toarray()[0]
        names = self.feat.word.get_feature_names_out()
        order = np.argsort(-w)[:top]
        terms = [(str(names[i]), round(float(w[i]), 3)) for i in order if w[i] > 0]
        from .rules import RULE_CATS
        hits = {}
        if self.rule_weight > 0:
            r = rule_features([text], 3.0)[0]  # unscaled 0..3
            hits = {c: round(float(v / 3.0 * 3), 1) for c, v in zip(RULE_CATS + ["urgent_strong", "urgent_weak"], r) if v > 0}
        return {"top_terms": terms, "rule_hits": hits}

    def predict(self, texts):
        texts = list(texts)
        P, pu = self.proba(texts)
        return self.decide(texts, P, pu)

    def predict_one(self, text):
        return self.predict([text])[0]


def route_of(pred):
    """Turn a prediction into the operational routing decision."""
    abstain = bool(pred["abstain"]) or pred["category"] == HUMAN_REVIEW
    return {
        "queue": "human_review" if abstain else ROUTE_TABLE.get(pred["category"], "human_review"),
        "priority": "URGENT" if pred["urgent"] else "STANDARD",
        "needs_human": abstain,
    }


# ------------------------------------------------------------------ threshold tuning
def oof_probabilities(texts, cats, urgs, groups=None, n_splits=5, seed=0, C=10.0, rule_weight=0.0):
    """Out-of-fold probabilities so thresholds are tuned on data the model did not train on."""
    texts = np.asarray(texts, dtype=object)
    cats = np.asarray(cats)
    urgs = np.asarray(urgs).astype(int)
    classes = sorted(set(cats))
    P = np.zeros((len(texts), len(classes)))
    pu = np.zeros(len(texts))
    if groups is None:
        # stratify on category; urgent is then roughly balanced too
        splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed).split(texts, cats)
    else:
        splitter = GroupKFold(n_splits=n_splits).split(texts, cats, groups)
    for tr, te in splitter:
        m = MLTriage(C=C, rule_weight=rule_weight).fit(texts[tr], cats[tr], urgs[tr])
        Pt, put = m.proba(texts[te])
        # classes may be missing from a fold; align columns
        for j, c in enumerate(m.classes_):
            P[te, classes.index(c)] = Pt[:, j]
        pu[te] = put
    return P, pu, classes


# For a calibrated p_urgent the cost-optimal flag threshold is C_false / (C_false + C_miss):
# 5/105 = 0.048 under the base costs and 5/305 = 0.016 under the strict ones, so the grid must reach below 0.05.
T_URGENT_GRID = np.array([0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.075] + list(np.round(np.arange(0.10, 0.96, 0.05), 2)))
T_CAT_GRID = np.round(np.arange(0.15, 0.96, 0.05), 2)


def tune_thresholds(texts, P, pu, classes, cats, urgs, cm: CostModel, safety_net=False):
    """Grid-search (t_urgent, t_cat) minimising total cost on the supplied (out-of-fold) predictions."""
    shell = MLTriage(safety_net=safety_net)
    shell.classes_ = classes
    best = None
    grid = []
    for tu, tc in product(T_URGENT_GRID, T_CAT_GRID):
        preds = shell.decide(texts, P, pu, t_cat=tc, t_urgent=tu)
        m, _ = evaluate(preds, cats, urgs, cm)
        grid.append((float(tu), float(tc), m["cost_total"], m["abstain_rate"], m["urgent_recall"]))
        key = (m["cost_total"], m["abstain_rate"])
        if best is None or key < best[0]:
            best = (key, float(tu), float(tc))
    return best[1], best[2], grid


def time_single(model, texts, warmup=20):
    """Per-report latency in milliseconds (one call per report, includes featurisation)."""
    for t in texts[:warmup]:
        model.predict_one(t)
    lat = []
    for t in texts:
        t0 = time.perf_counter()
        model.predict_one(t)
        lat.append((time.perf_counter() - t0) * 1000)
    lat = np.array(lat)
    return {"median_ms": float(np.median(lat)), "p95_ms": float(np.percentile(lat, 95)), "mean_ms": float(lat.mean())}
