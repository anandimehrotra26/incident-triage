# Attribution

## People

| role | name | what they did |
|---|---|---|
| Project owner / submitter | **Anandi Mehrotra** (anandimehrotra26) | Gave Claude the brief and directed it throughout, deployed the demo, publishes the repository, and organised the checks done after submission. Did not write the code by hand; did not verify the results before submitting. |
| Independent label reviewers | **Dhruv** (30 reports) and **Pranav** (30 reports), 15-16 Nov 2026 | Relabelled 60 reports from `data/review/` without seeing the recorded labels. Neither had any part in building the project. |
| Demo testers | **Dhruv** (14 Nov) and **Pranav** (16 Nov) | Tried the live demo; answers and screenshots in `FEEDBACK.md`. |

## AI tools

- **Claude (Anthropic), model Claude Sonnet 5.5, used through Claude's file/shell tools in a single working session on 2026-10-26.** Claude wrote essentially all code in `triage/`, `demo/`, `tests/`, the dataset generator and its text fragments, the cost model proposal, and the first drafts of every document in this repository. It also ran the experiments in its sandbox and reported the numbers. The project owner is responsible for what is submitted; the numbers in `results/` are the unedited output of the scripts.
- **After submission (13-20 Nov 2026), Claude (Anthropic)** was used again in a separate session as a tutor, to make the blind review sheets, to run the penalty check in `checks/` with me, and to draft the README and documentation updates that record the checks.
- No other AI tool was used. No real or confidential data was given to any AI tool.

## Libraries

numpy, pandas, scikit-learn, scipy, matplotlib, joblib, tabulate (all open source; see `requirements.txt`). The demo uses only the Python standard library plus one HTML file.

## What is NOT claimed

- The label review and demo feedback were done after submission (14-16 Nov 2026), not before.
- No real incident data was used.
