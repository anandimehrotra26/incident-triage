PY ?= python3

.PHONY: all install data review-sheet evaluate change train demo test clean

all: data evaluate change train test   ## full reproducible run (about 12 minutes on 2 CPU cores)

install:
	$(PY) -m pip install -r requirements.txt

data:            ## regenerate the synthetic datasets (deterministic)
	$(PY) -m triage.data_gen

review-sheet:    ## build the blind 60-report sheet for the independent reviewer
	$(PY) -m triage.review make

evaluate:        ## baseline vs ML comparison -> results/RESULTS.md, results.json, figures, error CSVs
	$(PY) -m triage.evaluate

change:          ## stricter urgent-miss penalty + new category experiments -> results/CHANGE_REQUEST.md
	$(PY) -m triage.change_request

train:           ## train the deployable model -> models/triage_model.joblib
	$(PY) -m triage.train

demo: train      ## web demo on http://localhost:8000
	$(PY) demo/server.py 8000

test:
	$(PY) -m unittest discover -s tests -v

clean:
	rm -rf models/*.joblib results/*.csv results/*.json results/figures/*.png
