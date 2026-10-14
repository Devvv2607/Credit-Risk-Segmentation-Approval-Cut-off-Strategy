# Credit Risk Scorecard & Cut-off Strategy

An end-to-end, reproducible credit-risk analysis of the public **Home Credit Default Risk** dataset: SQL segmentation of payment-difficulty risk, a WoE/IV logistic **points scorecard**, and an **approval cut-off strategy** with an interactive simulator, published as a static Next.js site. Every figure below is rendered from the pipeline outputs by `src/readme.py`, not typed.

**Live site:** {{site_link}}

> Generated file — edit `docs/README.template.md`, then run `make readme` (or `python tasks.py readme`).

| Home | Simulator | Scorecard |
|---|---|---|
| ![Home](docs/screenshots/home.png) | ![Simulator](docs/screenshots/simulator.png) | ![Scorecard](docs/screenshots/scorecard.png) |

## Business question

Whom should a lender approve, and where should the approval cut-off sit? The study answers it in three parts: which borrower segments carry elevated payment difficulty, how well an explainable scorecard ranks applicants, and what every possible cut-off would mean for approvals, payment difficulty and an illustrative profit.

## Data and TARGET definition

Kaggle's Home Credit Default Risk competition data: `application_train.csv` ({{applications}} applications), `bureau.csv` ({{bureau_rows}} records) and `previous_application.csv` ({{prev_rows}} records). File hashes are in `outputs/data_manifest.json`.

**TARGET** = 1 for a client with payment difficulties (a late payment beyond a threshold on at least one of the first instalments), 0 otherwise. The share with TARGET = 1 is called the **payment-difficulty rate** throughout; it is not a full default definition.

## Method

1. **Segmentation (DuckDB SQL)** — payment-difficulty rate, lift vs the baseline, portfolio share, risk rank and a 95% Wilson interval per segment; segments under {{min_segment}} applicants excluded.
2. **Split** — stratified 60/20/20 train / validation / test, seed 42. Train fits everything; validation selects the cut-off; test is opened once at the end.
3. **WoE/IV binning (optbinning, train only)** — monotonic bins, missing values as their own bin, WoE = ln(%good/%bad). IV ≥ 0.02, leak flag above 0.5, correlation filter at 0.7, protected attributes (`CODE_GENDER`, `NAME_FAMILY_STATUS`) excluded.
4. **Logistic regression** on WoE features, with coefficient-sign diagnostics (`outputs/coefficient_diagnostics.md`).
5. **Points scorecard** — 600 points at 50:1 odds, 20 points to double the odds, implemented by hand and cross-checked against optbinning.
6. **Cut-off strategy** — approval rate, payment-difficulty rate and illustrative profit at every 5-point cut-off on validation; a recommendation rule declared in config before computing; a 27-scenario sensitivity grid; one final check on test.

## Results

{{claims}}

| Split | AUC | Gini | KS |
|---|---|---|---|
{{metrics_rows}}

## Recommendation

**Cut-off {{cutoff}}** — the result under the illustrative assumptions in `config/assumptions.yaml`, not a lending decision. Rule: *{{rule}}*.

| | Validation | Test (once) |
|---|---|---|
| Approval rate | {{val_approval}} | {{test_approval}} |
| Payment-difficulty rate among approved | {{val_rate}} | {{test_rate}} |
| Baseline (approve everyone) | {{val_base}} | {{test_base}} |

## Limitations

- **Reject inference:** only booked loans have outcomes; declined applicants are absent.
- **No application dates:** no out-of-time validation is possible.
- **Not Indian lending data:** the scorecard would need recalibration before use elsewhere.
- **Illustrative profit:** labelled assumptions; excludes funding and operating cost, fees, recovery timing and loan term.

## How to reproduce

```bash
# 1. Accept the competition rules on Kaggle, then:
kaggle competitions download -c home-credit-default-risk
# unzip application_train.csv, bureau.csv and previous_application.csv into data/raw/

make setup        # Python 3.11 venv + requirements
make data-check   # confirms the three CSVs are present
make all          # raw CSVs -> outputs/ -> web/public/data/ (+ this README)
make test         # pytest + web lint, typecheck, vitest, data check
make web          # npm install + static build to web/out/
```

On Windows without `make`, use `python tasks.py <target>` (e.g. `python tasks.py all`). The pipeline is deterministic: two full runs produce byte-identical outputs. Validation: {{checks}} cross-stage checks pass (`outputs/validation_report.json`).

## Project structure

```
config/          settings.yaml, assumptions.yaml, site.yaml
sql/             01_baseline … 05_model_table (DuckDB)
src/             ingest, clean, segments, features, split, binning, model, scorecard,
                 cutoff, final_test, claims, validate, powerbi, export_web, readme
outputs/         aggregated CSV/JSON results, claims registry, diagnostics (committed)
tests/           pytest suite (data, leakage, segments, model, scorecard, cut-off, claims)
powerbi/         CSVs + POWERBI_GUIDE.md (no .pbix yet)
web/             Next.js static site (deploy with root directory web/)
data/            raw CSVs, DuckDB file, applicant-level tables — gitignored, never published
```

## Licence and data use

Code: MIT. Data: Home Credit Default Risk is Kaggle competition data, subject to the competition rules; raw data, applicant IDs, split assignments and applicant-level scores are **not** redistributed. `outputs/` and the site contain aggregated results only. This is an independent analysis, not affiliated with Home Credit or any lender.
