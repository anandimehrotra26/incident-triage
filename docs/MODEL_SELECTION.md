# How the models were chosen (and what was seen when)

This file exists so a reader can judge how much the reported numbers were shaped by looking at them.

## The three approaches

| id | approach | trained? | notes |
|---|---|---|---|
| A | Keyword/regex rules with simple negation (`triage/rules.py`) | no | Abstains (sends to human) only when no rule fires. No probabilities, so no threshold to tune. |
| B | TF-IDF (word 1-2 grams + char 3-5 grams) + two logistic-regression heads (category, urgent) | yes | Confidence-based abstention, thresholds tuned on cost. |
| C | B + negation-aware rule-hit counts as extra features | yes | Same heads and thresholds. |
| C+ | C + a "safety net": any strong urgent cue in the rules forces the URGENT flag | yes | Can only add urgent flags, never remove them. This is the variant deployed in the demo. |

Not measured: an LLM-based classifier. No API access was available in the build environment, so any claim about LLM accuracy, latency or cost would be invented. It is the obvious next comparison (see README).

## Protocol

- Splits: `random` (stratified 80/20) and `template` (about 25% of core sentences per category/urgency group held out entirely). Both are reported, 5 seeds each.
- Thresholds (urgent flag, category confidence for auto-routing) are chosen by grid search on **out-of-fold** predictions inside the development set, minimising the cost model in `triage/config.py`. The test set is touched once per seed for scoring.
- In the `template` regime the out-of-fold folds are grouped by template, so the thresholds are tuned on data that looks as novel as the test set will.

## Things that happened, in order (full disclosure)

1. First run of approach B on the unseen-template split showed ~33% category accuracy and abstention on 98% of reports. I had **seen test-split numbers** at this point.
2. Because of that, approach C (rule features) was added. Its feature weight (3.0) and C were chosen using **dev-only grouped cross-validation**, not the test set (weights tried: 0, 1, 3, 5, 8; C: 3, 10, 30). The idea of adding rule features was nevertheless motivated by seeing the test failure, so the test numbers for C are mildly optimistic.
3. The first draft of the rules baseline contained ~25 words taken from the generator's own templates (e.g. "ankle", "bollard", "padlock", "siphon", "claim form"). These made the baseline look much better than a plain keyword approach should. They were removed **before** any reported baseline number. Because rule features feed approach C, this affects A and C identically.
4. The urgent-threshold grid originally stopped at 0.05. The strict-penalty scenario showed that the theoretical optimum (cost_false / (cost_false + cost_miss) = 5/305 = 0.016) lay below the grid, so the grid was extended down to 0.005 and **everything was re-run**. Under the base costs the random-regime results were identical afterwards; a few unseen-template seeds moved slightly (e.g. approach C seed 44: 367 -> 388).
5. No hyper-parameter was tuned for approach B beyond C=10 (a default-ish value), so B is, if anything, under-tuned. Dev-only exploration showed char-only, word-only and C=1/10/100 all land at 27-38% grouped-CV category accuracy: the problem for B is data diversity, not regularisation.

## Known weaknesses of the evaluation

- Synthetic data (see `data/DATA_PROVENANCE.md`). The two splits bracket real performance rather than estimate it.
- 5 seeds over 180-274 test reports; a single missed urgent report moves cost per 100 by 35-55 points. Bootstrap CIs in `results/RESULTS.md` are wide for that reason.
- The cost model is invented. Change the numbers in `triage/config.py` and re-run `make evaluate`.
- Category confidence is only moderately calibrated (ECE 0.06 random split, 0.11 unseen-template split).
