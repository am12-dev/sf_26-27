# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Research project: early osteoporosis risk detection **without a DXA scan**, using NHANES survey data.
Cohort is intentionally narrow — non-Hispanic White women aged 50–65 (n = 1,484) — and the target
`at_risk` is derived from DXA femoral-neck / total-hip BMD T-scores, which are then excluded from the
feature set (the DXA measurement is the thing being predicted away).

`OsteoporosisML.py` is the **only** Python file in the repo. There is no package, no test suite, no
build step, and no dependency manifest. Two earlier scripts (`SF_new1.py`, `NHANES_PipelineModel.py`)
were removed in commit `0d87b3e`; `SF_new1.py` is the only source of the SHAP and calibration-curve
code and can be recovered with `git show 94bec2f:SF_new1.py`.

`Notes/project_walkthrough.html` is a full plain-language walkthrough of the study — cohort derivation,
the 23 predictors, the leakage guards, current results, and which outputs are appropriate to present.
Read it before explaining this project to anyone; update it when results change.

## Running

```bash
python OsteoporosisML.py
```

Runs end to end (steps 0–13, seventeen banners including `1b`, `6b` and `11b`) and prints a model
leaderboard plus several result tables to stdout. A full run takes roughly 30 minutes — the bootstraps,
permutation importance and nested CV dominate. Dependencies (`pandas`, `numpy`, `matplotlib`,
`scikit-learn`, `lightgbm`, `xgboost`, `requests`) are installed in the system Python interpreter
configured in `.vscode/settings.json` — there is no venv or `requirements.txt`. If you add a dependency,
note it in the module docstring since nothing else tracks it.

`BASE_DIR` is derived from the script's own location
(`os.path.dirname(os.path.abspath(__file__))`), so the script survives being moved or renamed.
`data/` and `outputs/` live directly beneath it at the repo root. Nothing needs editing if the repo
moves — do not reintroduce a hardcoded path.

The script reconfigures `sys.stdout`/`sys.stderr` to UTF-8 before importing pandas — this is required,
not cosmetic, because the progress output uses emoji and the default Windows console codepage
(cp1252) raises `UnicodeEncodeError`.

Network: step 1 downloads dietary-supplement files (`DSQTOT_*`) and step 1b downloads day-2 dietary
recalls (`DR2TOT_*`, cached as a 3-column extract suffixed `_calcium_vitd`), both from `wwwn.cdc.gov`,
into the matching `data/raw/<cycle>/` folder. The cache check is "file exists AND is over a size floor",
so a truncated download is re-fetched. Failed downloads are logged and skipped, not fatal. The
`DSQTOT_*` caches are committed but the `DR2TOT_*` ones are not, so a fresh clone re-downloads six
files once and then runs offline.

## Pipeline architecture

`main()` is a linear chain of step functions, each taking and returning a DataFrame. Every step prints a
banner via `print_section`. To debug a single step, import the module and call the functions in sequence
rather than adding flags — they are pure enough to run piecewise:

```python
import importlib.util
spec = importlib.util.spec_from_file_location('osteo', 'OsteoporosisML.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
df = m.compute_tscores(m.apply_filters(m.recode_refused(m.load_and_merge_cycles())))
```

Key structural facts that are not obvious from any one function:

**Cycle configuration is the main knob.** `CYCLES` lists six survey cycles with a NHANES letter suffix
(`D`, `E`, `F`, `H`, `J`) or a prefix (`P_` for the combined 2017–2020 cycle). File naming is derived
from these, so a cycle is added by appending to `CYCLES` and dropping CSVs into
`data/raw/<name>/`. `data/raw/` also contains **2015_2016 and 2021_2023 data that is deliberately not
in `CYCLES`** — do not "fix" this by adding them without checking with the user.

**`apply_filters` hard-asserts the cohort size at 1,484.** Any change to cycles, inclusion criteria, or
the DXA non-null requirement will trip this assert. That is its purpose: it pins the published cohort.
Treat a failing assert as a signal the cohort definition changed, not as a bug in the assert. The
attrition chain is 66,023 respondents → 33,341 female → 12,239 non-Hispanic White → 1,863 aged 50–65 →
1,484 with a femoral-neck DXA result.

**Raw CSVs are label-decoded, not numeric-coded.** These were exported with value labels applied, so
`RIAGENDR` is `"Female"` (not `2`), `RIDRETH1` is `"Non-Hispanic White"` (not `3`), and yes/no items are
`"Yes"`/`"No"`. Cycles 2015_2016 and 2017_2018 also ship `.XPT` originals alongside the CSVs — the
script reads only the CSVs. Two consequences to keep in mind:

- Filters and recodes accept both forms (`isin([2, 2.0, 'Female'])`, `recode_yesno` matching on lowercase
  strings). Preserve that dual handling when touching them.
- `recode_refused` only maps refused/don't-know sentinels (7/9/77/99/…) on `float64`/`int64` columns, so
  it is a no-op for label-coded columns. Anything relying on it needs numeric input.
- Because `education` stays a string, `define_features` silently drops it (see below).

**Feature selection is exclusion-based and drops non-numerics.** `define_features` starts from all
columns, removes a hand-maintained `exclude` list (IDs, filter variables, raw BMD, T-scores, both
targets, raw PHQ items, raw reproductive items, raw day-2 dietary columns, and dietary/supplement
components superseded by `total_*`), then drops every remaining `object`/`category` column. New
engineered variables are therefore included automatically — which cuts both ways: **any new column
derived from BMD or the T-score must be added to `exclude` or it leaks the target.** 23 features
survive.

**Only `X_without` is trained on.** `define_features` returns `X_with` and `X_without` (the latter minus
`sleep_risk`), but everything downstream uses `X_without` exclusively — sleep data is sparse across
cycles and was dropped for data density. `X_with` is plumbed through and unused; don't assume both arms
get scored.

**Modeling setup.** Two arms. Five classifiers (logistic regression L2, elastic-net logistic, random
forest, LightGBM, XGBoost) trained on the binary label, and three regressors (`RidgeCV`, RF, LightGBM)
trained on the continuous `t_score` and never on any label — one regressor fit serves both clinical
cutoffs by thresholding the predicted T-score twice. All are wrapped in a `Pipeline` of median
imputation → standard scaling → estimator (`_pipe`), so imputation and scaling are always learned inside
the training fold. Evaluated with 5-fold `StratifiedKFold(random_state=42)`; the seed is 42 throughout
and the whole run reproduces exactly. Class imbalance is handled per-model (`class_weight='balanced'`,
or `scale_pos_weight` for XGBoost). Both boosters are aggressively regularized (`max_depth=2`,
`reg_lambda=50`) because n = 1,484 overfits trivially.

**Do not rank models by the train/test gap.** The forest's in-sample AUC is 1.000 by construction — on
shuffled labels it still reaches 0.997 — so `run_model` enables out-of-bag scoring and the leaderboard
reports **train, test and OOB AUC side by side**. OOB is the honest in-sample number for a bagged
ensemble. Relatedly, `RF_MIN_SAMPLES_LEAF = 1` was chosen by nested CV, not assumed: raising it to
shrink the gap *lowers* test AUC monotonically (0.810 → 0.762 across the grid). The gap is the price of
the performance, not a defect to regularize away.

**Tree importances were deliberately removed** from reporting. Gini importance and split counts are
unsigned and biased toward continuous features over binary ones, and here they inverted the real
ranking. `clinical_table` uses permutation importance (mean out-of-fold AUC lost when a column is
shuffled) instead — model-agnostic and comparable across families. Do not reintroduce
`feature_importances_` as a presented result.

**Derived-variable details worth knowing:** `sleep_hrs` coalesces `SLD012` (newer cycles) with `SLD010H`
(older); `phq9_score` sums the nine PHQ items clipped to 0–3 with `min_count=5`, so respondents with
fewer than five answered items get NaN (it ends up 80% missing); `serum_vitd_nmol` coalesces `LBXVIDMS`
and `LBDVIDMS`. `total_calcium_mg` / `total_vitd_mcg` add a **two-day** dietary average to supplement
intake using plain addition, so a missing component yields a missing total rather than a fabricated one.
The supplement 0-fill is **scoped to respondents who appear in a `DSQTOT` file** — absence from every
file means unobserved (left NaN, flagged by `supp_data_available`), whereas a NaN nutrient for someone
present in a file means "reported no supplement", because NHANES codes non-users as blank rather than 0.
T-scores use fixed NHANES III young-adult reference means/SDs; `t_score` is the **minimum** of
femoral-neck and total-hip, rounded to three decimals before thresholding; `at_risk` is
`t_score <= -1.0` (osteopenia or worse — not osteoporosis alone) and `osteoporosis` is `t_score <= -2.5`.

## Results and how to talk about them

**The nested-CV number is the defensible one**, not the leaderboard. Fitting eight models and reporting
the best is biased upward; `nested_cv_selection` moves model choice inside each outer training fold so
no test row helps pick the model scored on it. The comparator is **OST** (`0.2 × (weight_kg − age)`), a
validated two-input formula — reporting AUC without it is uninterpretable.

| Target | OST | Leaderboard | Nested | Δ vs OST | Verdict |
|---|---|---|---|---|---|
| Osteopenia+ (T ≤ −1.0), 836 events | 0.747 | 0.810 | 0.810 | +0.063 [+0.046, +0.082] | Beats OST |
| Osteoporosis (T ≤ −2.5), 94 events | 0.773 | 0.833 | 0.806 | +0.031 [−0.013, +0.077] | Not separable |

The osteoporosis row is the selection bias being caught: 0.833 collapses to 0.806, and the remaining
advantage spans zero at 4.1 events per predictor. **Never quote 0.833 as an osteoporosis result.**

## Outputs and the tiering convention

Every result table goes through `save_csv(df, filename, tier)`, which writes to `outputs/` and prints
the tier as it writes. Keep using it — the folder is self-describing at the point of creation, which is
why there is no README in `outputs/` to drift out of sync. Tiers:

- **PRESENT** — for the clinical audience: `nested_cv_verdict.csv` (the two-row bottom line, open this
  first), `clinical_predictor_table.csv`, `forest_plot_odds_ratios.png`, `referral_table.csv`,
  `threshold_sweep.csv`, `model_leaderboard.csv`.
- **METHODS** — defends a methodological choice if challenged: `baseline_comparison.csv`,
  `rf_leaf_tuning.csv`.
- **DIAGNOSTIC** — `coefficient_diagnostics.csv`. A leak and sign-error detector, in standardised units
  and unstable across collinear predictors. **Not a findings table**; the script says so in its own
  output. Two standing alarms live here: any `|standardised coef| > LEAK_COEF_THRESHOLD` (2.0) suggests
  a BMD-derived column entered the features, and `EXPECTED_SIGNS` flags clinically backwards
  coefficients. `total_vitd_mcg` currently trips the sign check — reverse causation, worth stating
  rather than hiding.

**Two cutoff tables mean different things by the same numbers.** `referral_table.csv` leads with
`Top fraction flagged` — a quantile of the leaderboard forest's scores (AUC 0.810). `threshold_sweep.csv`
keeps `Probability Cutoff` — a real probability from a *different*, sigmoid-calibrated forest
(AUC 0.764), and carries `Model` and both AUCs on every row. Never merge them or share an axis.

**Known gap:** there is no calibration figure. Step 13 depends on its probabilities being trustworthy
(hence `CalibratedClassifierCV`), but the only calibration plotting code went with `SF_new1.py`.
Regenerating a calibration curve from this script is the obvious next addition.

## Data layout and lineage

```
sf_26-27/
  OsteoporosisML.py                        # the entire pipeline
  data/raw/<cycle>/<MODULE>_<suffix>.csv   # NHANES source, one folder per cycle
  data/processed/                          # option_b_v4_final.csv + legacy files
  outputs/                                 # regenerated every run; see tiering above
  Notes/project_walkthrough.html           # the project explainer
```

`data/processed/option_b_v4_final.csv` is the only file the script writes outside `outputs/` and the
download caches, and it is the **preferred analysis input**. The other processed files
(`nhanes_osteoporosis_cleaned.csv`, `option_b_v3_allcycles.csv`, `option_b_v4_with_new_vars.csv`, the
`osteoporosis_train_set` / `osteoporosis_test_set` pair) are artifacts of **earlier scripts no longer in
the repo** — don't assume they can be regenerated. The train/test CSVs in particular carry legacy
defects: duplicated `at_risk` columns and duplicate one-hot education columns differing only in
capitalization, from the label-vs-code inconsistency across cycles.

Everything in `outputs/` is now current and traceable to a line in this script. `outputs/run_log.txt`,
if present, is a manual stdout capture by the user, not a script artifact — it will silently go stale.

**Git:** `.gitignore` lists `data/` and `outputs/`, but `data/` was committed before that and stays
tracked (158 files, ~31 MB history) — deliberately, since several processed files cannot be regenerated
and the repo is their only copy. Nothing in `outputs/` is tracked, so a fresh clone has no results until
the pipeline runs. Do not `git rm --cached` the data directory.

Reference document (not code, but authoritative for variable definitions):
`nhanes_data_dictionary _allCycles.doc` at the repo root. `Notes/osteoporosis project.docx` holds
study write-up material. Earlier versions of this file cited a research-paper PDF and three ER-diagram
PDFs — **no PDFs exist in the repo**; ask the user for them if the study design spec is needed.
