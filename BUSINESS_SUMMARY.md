# Incident triage for a logistics operator - one-page business summary

**Problem.** Incident reports (accidents, spills, theft, damage, delays, breakdowns, customs, lost parcels) arrive as free text. Today someone reads each one, decides which team gets it, and hopes the urgent ones are noticed in time. The costly failures are not "wrong label" but (a) an urgent case sitting in a normal queue and (b) a safety incident reaching the wrong team.

**What was built.** A triage service that, per report, returns a team queue, an URGENT/STANDARD flag, and a "needs human" decision when it is not confident. It runs in ~1-2 ms per report on one CPU core. The URGENT flag is independent of the routing decision, so uncertain reports still jump the human queue if they look urgent. A web demo and CLI are included.

**Evidence (synthetic data - see caveat).** Cost = invented but explicit penalties: missed urgent 100, wrong team 8 (25 if safety-critical), human review 4. Lower is better; a human reading everything perfectly costs 400 per 100 reports (617 if urgent items wait in arrival order).

| | easy test (phrasing seen in training) | hard test (phrasing never seen) |
|---|---|---|
| Keyword rules | 726 | 880 |
| ML (TF-IDF + logistic regression) | **110** - 99% urgent recall, 11% sent to humans | 403 - sends almost everything to humans |
| ML + rule features + urgent safety net (demo model) | 117 - 99% urgent recall, 13% to humans | 417 - 94% urgent recall, 48% to humans, ~7 costly misroutes per 274 |

**Honest reading.** The simple rules baseline is worse than having a human read everything. The ML models are far better *if real reports resemble the training reports*, and no better than a human if they do not. The truth for the operator sits between the two columns and can only be measured on the operator's own reports. When the model is out of its depth it mostly fails safe (it abstains) but it still missed ~6% of urgent reports on unseen phrasing, so it is **not safe to run unattended**.

**Changed requirements.** *Stricter penalty for missed urgent (100 -> 300):* change one number and re-tune two thresholds (~10 s, no retraining). On hard data this cut cost 574 -> 429 and raised urgent recall 93.8% -> 95.1% by sending more to humans; on easy data nothing changed because urgent recall was already ~99%. It cannot fix cases where the model is confidently wrong. *New category (cold chain):* the existing system sent 80-99% of new-category reports to a human and silently misrouted 1-20%; about 40 labelled examples (5-6 s retrain) were enough when new reports resembled the examples, 80 gave only 58-67% auto-correct on genuinely new phrasing. Old categories were unaffected. Hand-written rules adapted faster here (two regexes -> 90% correct, 100% urgent recall) but they were written by the author of the test data, so treat that as best case.

**Money (assumptions: 2 min of human time at $30/h = $1 per review, so 1 cost unit = $0.25; compute ~$0.00002 per 1,000 reports).** Per 10,000 reports: human reads all, perfectly prioritised ~$10,000; demo model on easy data ~$2,900; on hard data ~$10,400 (no saving). Compute cost is negligible; human review and rare urgent misses dominate.

**Recommendation.** Do not launch on this evidence. Run a 4-6 week **shadow pilot** on real reports: the model suggests, humans decide, everything is logged. Go/no-go: >= 99% urgent recall on >= 200 real urgent cases, <= 1% costly misroutes among auto-routed reports, and a human re-labelled sample (>= 100) to replace the invented labels and penalties. Start by automating only the URGENT flag and the highest-confidence routes.

**Caveats.** All data is synthetic and template-based; labels and penalties are the author's assumptions; independent label review and user feedback are pending (see `FEEDBACK.md`, `data/review/`); an LLM-based option was not measured.
