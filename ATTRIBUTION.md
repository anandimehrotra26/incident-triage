# Attribution

## People

| role | name | what they did |
|---|---|---|
| Project owner / submitter | **[FILL IN: your name]** | Set the brief, directed the work, reviewed outputs, publishes the repository. |
| Independent label reviewer | **[FILL IN: name or role, or "not yet done"]** | Completes `data/review/review_sheet_blank.csv` (>= 50 reports). Must not be the submitter. |
| Demo tester(s) | **[FILL IN, or "none yet"]** | See `FEEDBACK.md`. |

## AI tools

- **Claude (Anthropic), model Claude Sonnet 5.5, used through Claude's file/shell tools in a single working session on 2026-10-26.** Claude wrote essentially all code in `triage/`, `demo/`, `tests/`, the dataset generator and its text fragments, the cost model proposal, and the first drafts of every document in this repository. It also ran the experiments in its sandbox and reported the numbers. The project owner is responsible for what is submitted; the numbers in `results/` are the unedited output of the scripts.
- No other AI tool was used. No real or confidential data was given to any AI tool.

## Libraries

numpy, pandas, scikit-learn, scipy, matplotlib, joblib, tabulate (all open source; see `requirements.txt`). The demo uses only the Python standard library plus one HTML file.

## What is NOT claimed

- No human has independently reviewed the labels yet (pending; tooling is included).
- No external person has tried the demo yet (pending; feedback buttons and a template are included).
- No real incident data was used.
