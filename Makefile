# Credit risk cut-off pipeline. Run `make all` from raw CSVs to website JSON.
# Windows without make: use `python tasks.py <target>` (same targets).

ifeq ($(OS),Windows_NT)
PY := .venv/Scripts/python
else
PY := .venv/bin/python
endif
export PYTHONIOENCODING := utf-8

.PHONY: setup data-check ingest clean segments features split binning model scorecard cutoff final-test claims validate powerbi export-web readme all test lint web

setup:
	python3.11 -m venv .venv || py -3.11 -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

data-check:
	$(PY) -m src.data_check
ingest: data-check
	$(PY) -m src.ingest
clean:
	$(PY) -m src.clean
segments:
	$(PY) -m src.segments
features:
	$(PY) -m src.features
split:
	$(PY) -m src.split
binning:
	$(PY) -m src.binning
model:
	$(PY) -m src.model
scorecard:
	$(PY) -m src.scorecard
cutoff:
	$(PY) -m src.cutoff
# The test split is opened here, once, after the cut-off is frozen.
final-test:
	$(PY) -m src.final_test
claims:
	$(PY) -m src.claims
validate:
	$(PY) -m src.validate
powerbi:
	$(PY) -m src.powerbi
export-web:
	$(PY) -m src.export_web
readme:
	$(PY) -m src.readme

# claims and export-web run a second time so the resume bullets and the site pick up
# the validation report.
all: ingest clean segments features split binning model scorecard cutoff final-test claims powerbi export-web validate
	$(PY) -m src.claims
	$(PY) -m src.export_web
	$(PY) -m src.readme

test:
	$(PY) -m pytest -q
	cd web && npm run lint && npm run typecheck && npm run test && npm run check-data

lint:
	$(PY) -m ruff check src tests
	cd web && npm run lint

web:
	cd web && npm install && npm run build
