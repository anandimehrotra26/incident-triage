# Error analysis and when to abstain

All counts are for the seed-42 test sets (random: 180 reports, 39 urgent; unseen-template: 274 reports, 51 urgent) and come from `results/ERROR_SUMMARY.md` and `results/errors_*.csv`, which list every mistake with its text. Small counts: treat each as an anecdote with a number attached, not a rate.

## 1. Where the rules baseline (A) fails

- **Urgency is the big hole.** It misses 8 of 39 urgent reports (random split) and 11 of 51 (unseen split). The misses are urgent-by-context reports with no alarm vocabulary: vaccines running late, "grounded aircraft", a production line that halts, "steering locked up ... on the hard shoulder", "ammonia smell ... workers feeling dizzy". Rules only know words someone thought to list.
- **Single keywords hijack the category.** `cargo_damage -> hazmat_spill` x6 in the random split: "roof leak above dock" fires the *leak* rule. Under the unseen split, `accident_injury -> cargo_damage` x5 and `theft_security -> hazmat_spill` x5 ("fuel siphoning" fires *fuel*).
- It abstains on 27% of reports (no rule fired), but 16 of those are the genuinely unclear ones, so most of its abstentions are the system working as intended; the cost is in the 17 *confident* wrong routes it makes anyway.

## 2. Where the ML models fail

**Random split (approach C+).** 23 reports go to a human: all 16 genuinely unclear ones plus 7 routable ones. Of those 7, 3 would have been routed wrongly (abstaining paid off) and 4 would have been right (abstaining cost 4 units each). Two reports are auto-routed to the wrong team, and one of those is the model being *right* about a deliberately mislabeled report (recorded `theft_security`, text is about wet cartons). No urgent report missed. Pure TF-IDF (B) missed one: "pallet of pesticide ruptured, vapour cloud near the loading bay", auto-routed with the urgent probability below threshold.

**Unseen-template split.** The honest picture:
- **B (no rule features) cannot categorise unseen phrasing.** It abstains on 270 of 274 reports (and flags 55 reports urgent, mostly false). Its urgent head still generalises (99.6% recall at that threshold), so B degenerates into "urgent detector + send everything to humans", which costs the same as a human reading everything (403 vs 400 per 100).
- **C+ auto-routes 139 reports and gets 11 wrong**, 8 of them safety-critical categories. Recurring confusions: `accident_injury -> cargo_damage` x3 ("scraped a bollard while reversing, bumper cracked": it hears *cracked*, not *scraped/driver*), `accident_injury -> vehicle_breakdown` x2 (stalled on a level crossing - ambiguous by our own labeling guide, and one of the two is an injected label error), `theft_security -> cargo_damage` x2 ("seal broken ... cartons missing").
- **It still misses urgent reports on novel phrasing**: 5 of 51 not flagged (2 auto-routed). Examples: "truck broke down in the middle lane of the expressway, hazard lights on" (urgent probability 0.05-0.07: in training, most breakdowns are routine), "driver reports being followed by a car trying to force him off the road" (sent to a human but not flagged), "sealed legal documents ... needed in court this afternoon". The first is exactly what a one-line domain rule ("lane", "expressway", "hard shoulder") would catch. I did **not** add it, because that would be tuning on the test errors; it is listed under next steps.
- **Label noise is a visible share of "errors":** 4 of the 11 auto-routed errors are cases where the recorded label is the injected wrong one.

## 3. When should the system abstain? What the data says

1. **Always, for text with no identifiable incident** (`unclear_other`). All 16 (random) and 17 (unseen) of them were sent to a human by every approach. This is the easy 6-9% of volume.
2. **When the top category's probability is below ~0.6-0.85** (tuned thresholds: 0.35-0.60 on the random split, 0.55-0.85 on the unseen split). Abstentions concentrate in `delay_late`, `misdelivery_lost` and `cargo_damage` - the categories whose wording overlaps most (35 / 25 / 29 of 135 abstentions on the unseen split).
3. **Never abstain without also flagging urgency.** The system emits the URGENT flag independently of the category decision, so a report that goes to the human queue can still jump to its front. That is why abstention is cheap for urgent reports in the cost model (the 10-unit delay applies only if the flag is missed). Of the 5 unflagged urgent reports on the unseen split, 3 were abstentions that lost this protection.
4. **Abstention is not free and is not very selective.** On the unseen split, 27 of the 118 abstentions on routable reports were cases where the model's top guess was in fact right. The coverage/accuracy curve for approach C (`results/figures/coverage_accuracy_C_*.png`) shows the trade-off: on the unseen split accuracy on auto-routed reports is 80% at 71% coverage, 89% at 57% and 95% at 45%; on the random split it is 97% at 91% coverage and 99% at 78%. Confidence from this model is only moderately calibrated (ECE 0.06 random, 0.11 unseen).

## 4. What would reduce errors (not done; honest list)

- Real incident text for training and for a real held-out set. Nothing here replaces it.
- A few dozen operator-written road-position / personal-safety urgency rules (`lane`, `hard shoulder`, `followed`, `court today`) as a second safety net.
- Per-category abstention thresholds from the cost model (misrouting safety-critical categories costs 25, others 8) instead of a single global threshold.
- A pretrained sentence-embedding or LLM classifier for generalisation to new phrasing; it was not measured here (no model/API access in the build environment).
- Fixing the labeling guide's ambiguous rules (level crossing, "late and damaged") before collecting more labels; some "errors" are label disagreement.
