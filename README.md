# Early osteoporosis risk detection without a DXA scan — NHANES 2005–March 2020

Can routinely collected survey, exam and lab variables identify low bone mass in
postmenopausal women **without** a DXA scan — and do they do better than the two-variable
OST formula, `0.2 × (weight_kg − age)`, that a clinic can already compute?

**Short answer from the current run: no, not separably.** The models perform about as well as
OST, but the gain over it is within noise at both clinical cutoffs (see [Results](#results)).

---

## Quick start

```bash
pip install -r requirements.txt     # Python 3.12
python OsteoporosisML.py            # no arguments; ~25-40 min
```

- Runs fully **offline**: every NHANES input file is committed under `data/raw/`.
- Seeded (`SEED = 42`), so a rerun reproduces `outputs/` exactly.
- The script **asserts** the cohort sizes (1,308 → 1,111). If an assert fires, the input data
  differ from the committed files — it is a check, not a bug.
- Start reading the results at **`outputs/nested_cv_verdict.csv`**.

## Repository layout

```
OsteoporosisML.py      the entire pipeline (one file, blocks A–G, see below)
requirements.txt       pinned package versions
data/raw/<cycle>/      NHANES source files, one folder per survey cycle (inputs)
data/processed/        analysis_cohort_postmenopausal.csv = the cohort the models see
outputs/               every result table and figure, plus run_log.txt (console output)
extra_reading/         walkthrough, specialist Q&A, slides, notes, NHANES data dictionary
archive/               superseded scratch scripts and old logs — not needed, kept for history
```

Only `OsteoporosisML.py` and `outputs/` are needed to understand the study.

## The study in one page

**Cohort** (`apply_filters`, `apply_menopause_gate`)

| Step | n |
|---|---|
| Women 50–65, non-Hispanic White, with a femoral-neck DXA, 5 NHANES cycles | 1,308 |
| Excluded: still menstruating (period in last 12 months) | −156 |
| Excluded: menopausal status unknown | −41 |
| **Analysis cohort (postmenopausal)** | **1,111** |

Cycles: 2005–06, 2007–08, 2009–10, 2013–14, 2017–March 2020. The 2017–18 cycle is
**deliberately left out**: NHANES folded those women into the 2017–2020 `P_` files under new IDs,
so loading both counted 176 women twice (see the docstring at the top of the script).
`data/raw/` also holds 2015–16, 2017–18 and 2021–23 files that the pipeline does not use.

**Outcome** — computed from the DXA scan, never given to the models (`compute_tscores`)

- T-score = the lower of femoral-neck and total-hip, against the NHANES III young-adult
  reference (Looker et al.).
- Two labels: **T ≤ −1.0** (osteopenia or worse, 645 women, 58%) and
  **T ≤ −2.5** (osteoporosis, 76 women, 6.8%).

**Predictors** — an explicit allowlist, `FEATURE_GROUPS` (15 variables, 16 columns)

| Group | Variables |
|---|---|
| Body / demographic | age, BMI, weight, poverty-income ratio |
| Reproductive | years since menopause, ever used estrogen |
| Clinical history | prior fracture (any site), steroid use, diabetes |
| Family history | parental hip fracture, family history of osteoporosis |
| Lifestyle | ever smoked, alcohol (none / <3 / 3+ per day), sleep hours, PHQ-9 depression score |

Vitamin D (intake or serum), rheumatoid arthritis and physical activity are tested as
**separate pre-specified arms** (`ARM_GROUPS`, `run_arms`), each on the women who have that
measurement. `BMD_DENYLIST` asserts that nothing derived from the DXA scan can enter any model.

The raw NHANES column behind each predictor, and how it is decoded, is in `SPEC` and
`MODULE_COLS` (block B). Per-variable provenance is in
`extra_reading/specialist_variable_provenance.csv`.

**Models** (`get_model_dictionary`, `get_regressor_dictionary`)

- Classifiers on the yes/no label: logistic regression (L2), elastic-net logistic, random
  forest, LightGBM, XGBoost (both boosters heavily regularised).
- Regressors on the continuous T-score: ridge, random forest, LightGBM.
- Comparators: **OST** and **weight alone**.
- Every model is a pipeline of median imputation → scaling → model, fitted inside each
  training fold, so nothing is learned from the test rows.

**Evaluation**

- 5-fold stratified cross-validation, scored by ROC AUC.
- **Nested CV** (5 outer × 3 inner): the "best model" is chosen inside each training fold, then
  scored on the untouched test fold. This is the honest estimate. The leaderboard, which picks
  the best of eight after seeing every fold, is optimistic by construction.
- Paired bootstrap 95% CI for each model's AUC difference vs OST.

## Results

From `outputs/nested_cv_verdict.csv`:

| Target | Events | OST AUC | Nested model AUC | Δ vs OST (95% CI) | Verdict |
|---|---|---|---|---|---|
| T ≤ −1.0 | 645 | 0.739 | 0.747 | +0.008 (−0.008, +0.025) | not separable |
| T ≤ −2.5 | 76 | 0.780 | 0.786 | +0.007 (−0.016, +0.030) | not separable |

At T ≤ −2.5 there are only 76 events, below the usual 10-events-per-predictor floor
(`outputs/power_gate.csv`), so that target is underpowered and the analysis says so up front.

**Earlier figures of AUC 0.810 / 0.806 are withdrawn.** They were computed on the cohort
that counted the duplicated women twice.

## Outputs

Each file is tagged when written (see `save_csv`):
**PRESENT** = a result for the clinical audience,
**METHODS** = backs up a method choice,
**DIAGNOSTIC** = a bug detector, not a finding.

| File | Tier | What it answers |
|---|---|---|
| `nested_cv_verdict.csv` | PRESENT | **The bottom line**: does the model beat OST? |
| `table_one.csv`, `table_one_categories.csv` | PRESENT | Who is in the cohort, by bone status |
| `model_leaderboard_osteopenia.csv`, `…_osteoporosis.csv` | PRESENT | Every model's cross-validated AUC (optimistic; see nested) |
| `clinical_predictor_table.csv`, `forest_plot_odds_ratios.png` | PRESENT | Adjusted odds ratio per clinical unit with 95% CI, plus permutation importance |
| `model_variable_ablation_osteopenia.csv`, `model_block_ablation_osteopenia.csv` | PRESENT | AUC lost when a variable / block is removed and the model refitted |
| `prespecified_arms.csv` | PRESENT | Does adding vitamin D, RA or activity help? |
| `calibration_curve.png` | PRESENT | Do predicted probabilities match observed rates? |
| `referral_table.csv`, `threshold_sweep.csv` | PRESENT | Screening cost: DXA scans ordered per case found, sensitivity/specificity by cutoff |
| `power_gate.csv`, `rf_leaf_tuning.csv`, `auc_decomposition.csv` | METHODS | Events per predictor; forest tuning; why the AUC fell after the fixes (written by `_decompose.py`, since removed; recover with `git show 239c2a7:_decompose.py`) |
| `coefficient_diagnostics.csv` | DIAGNOSTIC | Leakage and sign-error check — **do not present** |
| `run_log.txt`, `auc_decomposition_log.txt` | — | Console output of the run that produced these files |

`clinical_predictor_table.csv` (variable shuffled inside a trained model) and
`model_variable_ablation_osteopenia.csv` (model refitted without the variable) answer different
questions. Where they disagree, collinearity between predictors is the reason.

## Reading the code

`OsteoporosisML.py` is ordered top to bottom as the pipeline runs; `main()` at the bottom is the
table of contents.

| Block | What it does | Key names |
|---|---|---|
| A | Configuration: cycles, cutoffs, cohort checkpoints | `CYCLES`, `T_OSTEOPENIA`, `N_POSTMENOPAUSAL` |
| B | Loads NHANES files and decodes each variable's own missing-value codes | `SPEC`, `MODULE_COLS`, `decode` |
| C | Cohort filters, duplicate audit, T-scores, menopause gate | `apply_filters`, `audit_duplicates`, `compute_tscores` |
| D | Derived variables: years since menopause, calcium/vitamin D, PHQ-9 and more | `compute_derived_variables` |
| E | Feature allowlist, analysis cohorts, power gate, Table 1 | `FEATURE_GROUPS`, `build_cohorts` |
| F | Models, cross-validation, bootstrap, odds ratios, ablation, nested CV | `get_model_dictionary`, `nested_cv_selection` |
| G | Pre-specified arms, screening tables, `main()` | `run_arms`, `screening_tables` |

The module docstring at the top lists the methodological rules that must not be broken (for
example, never rank models by the train/test gap, and never present Gini importance).

## Extra reading

All in `extra_reading/`:

- `project_walkthrough.html` — plain-language walkthrough of the whole study. **Start here.**
- `specialist_answers_and_decisions.html`, `Specialist_Review_Questions.docx`,
  `Specialist_Review_Answers.docx`, `SpecialistUpdate.docx` — the specialist's variable rulings.
- `statistician_brief.html` — methodological decisions and the reasons for them.
- `variable_definition_note.html`, `reproductive_variables_note.html`, `missing_data_note.html` — how
  individual variables were defined, and how missing data were handled.
- `specialist_variable_*.csv` — variable reference, provenance and decisions.
- `literature_ml_vs_ost.md` — published ML-vs-OST studies.
- `*.pptx` and `presentation_ml_engineer/` — slide decks.
- `nhanes_data_dictionary _allCycles.doc` — NHANES variable definitions.
- `build_*.py`, `make_figures.py` — scripts that generate the decks and notes. They are not part
  of the analysis.

Some older notes predate the cohort fixes. Where any document disagrees with `outputs/`,
**`outputs/` is current.**

## Data source

NHANES (CDC/NCHS), public-domain survey data: https://wwwn.cdc.gov/nchs/nhanes/. The files are
CSV conversions of the CDC `.xpt` downloads, named `<MODULE>_<suffix>.csv`
(`P_<MODULE>.csv` for 2017–March 2020).
