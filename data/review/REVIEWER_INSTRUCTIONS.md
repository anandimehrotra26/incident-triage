# Instructions for the independent reviewer

**Status: PENDING.** No completed review exists in this repository yet. Whoever reviews must not be the person who wrote the generator or the labelling guide.

1. Read `docs/LABELING_GUIDE.md` (5 minutes).
2. Open `review_sheet_blank.csv` (60 reports, labels hidden). Do **not** open `data/incidents.csv`.
3. For each row fill:
   - `reviewer_category` - one of: accident_injury, hazmat_spill, theft_security, cargo_damage, delay_late, vehicle_breakdown, customs_documentation, misdelivery_lost, unclear_other
   - `reviewer_urgent_0or1` - 1 or 0 following the guide
   - `reviewer_notes` - anything ambiguous (optional)
4. Save as `review_sheet_completed.csv` in this folder. At least 50 rows must be filled (all 60 preferred).
5. Run:
   ```
   python -m triage.review score data/review/review_sheet_completed.csv
   ```
   This writes `review_report.md` (agreement, Cohen's kappa, and the list of disagreements).
6. Adjudicate each disagreement: add columns `final_category` and `final_urgent` to the completed sheet for those rows, then
   ```
   python -m triage.review apply data/review/review_sheet_completed.csv
   ```
   to produce `data/incidents_reviewed.csv`.
7. Record in `ATTRIBUTION.md` who reviewed (name or role) and how long it took.

Expected result for context: ~3% of recorded category labels were deliberately flipped (about 2 of 60 sampled), and the labelling guide has a handful of genuinely ambiguous rules, so a careful reviewer should disagree on a few rows. Zero disagreements would be suspicious.
