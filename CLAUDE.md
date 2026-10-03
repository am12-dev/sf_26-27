# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Research project: early osteoporosis risk detection **without a DXA scan**, using NHANES survey data.
The cohort is intentionally narrow — **postmenopausal** non-Hispanic White women aged 50–65
(n = 1,111) — and the target `at_risk` is derived from DXA femoral-neck / total-hip BMD T-scores,
which are then structurally barred from the feature set (the DXA measurement is the thing being
predicted away).

`OsteoporosisML.py` is the **only** Python file in the repo. There is no package, no test suite, no
build step, and no dependency manifest. It was rewritten in full per
`Notes/rewrite_implementation_plan.html`; the file is internally organised into blocks A–G and the
module docstring lists the five structural changes. Two earlier scripts (`SF_new1.py`,
`NHANES_PipelineModel.py`) were removed in commit `0d87b3e` and can be recovered with
`git show 94bec2f:SF_new1.py`.

`Notes/project_walkthrough.html` is a full plain-language walkthrough of the study. Read it before
explaining this project to anyone; update it when results change. `Notes/statistician_brief.html` and
`Notes/specialist_answers_and_decisions.html` record the methodological rulings and why each was made.

## The five things that changed in the rewrite

These are the facts most likely to be got wrong by anyone working from older notes, older commits, or
the pre-rewrite walkthrough.

**1. 2017_2018 is gone from `CYCLES`, and must not come back.** NHANES stopped field work in March
2020, so NCHS pooled the partial 2019–2020 sample with the **complete** 2017–2018 cycle into the `P_`
files under re-numbered SEQNs. Loading both cycles loaded 176 cohort women twice with disjoint IDs
(`DEMO_J` 93703–102956 vs `P_DEMO` 109263–124822 never collide, so SEQN dedup cannot see it). Because
`StratifiedKFold` splits rows and not people, those pairs straddled train and test folds and inflated
every cross-validated AUC. `audit_duplicates` now asserts zero duplicates on a physical fingerprint
(`DXXNKBMD`, `DXXOFBMD`, `BMXWT`, `BMXHT`, `RIDAGEYR`) so the defect cannot return silently.

**2. The cohort is postmenopausal only.** `apply_menopause_gate` drops 156 still-cycling women and 41
whose status cannot be determined. Those two groups are **not the same thing** — the 41 are unknown,
not premenopausal, and must never be described as premenopausal.

**3. Feature selection is an allowlist.** `FEATURE_GROUPS` in block E names every variable that may
enter a model. The old design admitted every column not explicitly excluded, so any newly derived
column leaked the target unless somebody remembered to add it to `exclude`. `BMD_DENYLIST` asserts on
top of the allowlist as a second gate. **Adding a variable now means adding it to `FEATURE_GROUPS`** —
new columns are no longer picked up automatically, which is the point.

**4. Sentinel handling is per variable.** `SPEC` in block B declares kind and valid range for each
column. One global refused/don't-know list cannot be correct: 99 is a refusal for `RHQ060` and a
legitimate value for `PAD680`.

**5. Every pre-rewrite AUC is withdrawn.** 0.810 and 0.806 were computed on the duplicated cohort.
Nothing from the old run carries forward. **Do not quote 0.810, 0.806 or 0.833 from any older note,
commit message or walkthrough.**

## Running

```bash
python OsteoporosisML.py
```

Runs end to end and prints a model leaderboard plus the result tables to stdout. A full run takes
roughly 25–40 minutes — the bootstraps, permutation importance, the ablation grid and the nested CV
dominate. Dependencies (`pandas`, `numpy`, `matplotlib`, `scikit-learn`, `lightgbm`, `xgboost`,
`requests`) are installed in the system Python interpreter configured in `.vscode/settings.json` —
there is no venv or `requirements.txt`. If you add a dependency, note it in the module docstring since
nothing else tracks it.

`BASE_DIR` is derived from the script's own location (`os.path.dirname(os.path.abspath(__file__))`), so
the script survives being moved or renamed. Nothing needs editing if the repo moves — do not
reintroduce a hardcoded path.

The script reconfigures `sys.stdout`/`sys.stderr` to UTF-8 before importing pandas — this is required,
not cosmetic, because the progress output uses emoji and the default Windows console codepage (cp1252)
raises `UnicodeEncodeError`.

Network: step 5 downloads dietary-supplement files (`DSQTOT_*`) and step 5b downloads day-2 dietary
recalls (`DR2TOT_*`), both from `wwwn.cdc.gov`, into the matching `data/raw/<cycle>/` folder. The cache
check is "file exists AND is over a size floor", so a truncated download is re-fetched. Failed
downloads are logged and skipped, not fatal. The download caches are committed, so a fresh clone runs
fully offline.

To debug one step, import the module and call the functions in sequence rather than adding flags:

```python
import importlib.util
spec = importlib.util.spec_from_file_location('osteo', 'OsteoporosisML.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
df = m.apply_menopause_gate(m.compute_tscores(m.apply_filters(m.load_and_merge_cycles())))
```

## Pipeline architecture

`main()` is a linear chain of step functions, each taking and returning a DataFrame. Every step prints
a banner via `print_section`. Key structural facts that are not obvious from any one function:

**Cycle configuration is the main knob.** `CYCLES` lists five survey cycles with a NHANES letter suffix
(`D`, `E`, `F`, `H`) or a prefix (`P_` for the combined 2017–2020 cycle). `data/raw/` also contains
**2015_2016, 2017_2018 and 2021_2023 data that is deliberately not in `CYCLES`** — 2017_2018 for the
duplication reason above, the others by the user's choice. Do not "fix" this by adding them.

**The cohort asserts pin the published numbers.** `apply_filters` hard-asserts `N_DXA_COHORT = 1308`;
`apply_menopause_gate` asserts 156 still-cycling, 41 unknown and `N_POSTMENOPAUSAL = 1111`;
`audit_duplicates` asserts zero fingerprint duplicates. Treat a failing assert as a signal that the
cohort definition changed, not as a bug in the assert. Attrition: 66,023 respondents → female →
non-Hispanic White → aged 50–65 → **1,308** with a femoral-neck DXA → **1,111** postmenopausal.

**Raw CSVs are label-decoded, not numeric-coded.** These were exported with value labels applied, so
`RIAGENDR` is `"Female"` (not `2`), `RIDRETH1` is `"Non-Hispanic White"` (not `3`), and yes/no items
are `"Yes"`/`"No"`. `decode` in block B handles both forms per `SPEC`; preserve that dual handling when
touching it. Cycles 2015_2016 and 2017_2018 also ship `.XPT` originals alongside the CSVs — the script
reads only the CSVs.

**Denormal floats are NHANES's encoding of zero.** `P_*` and nutrient files carry values like
`5.397605346934028e-79`. `sanitise_denormals` maps anything under `DENORMAL_EPS = 1e-30` to 0.0 and
runs on every loaded frame, including the supplement and day-2 nutrient extracts. Without it those
columns look like they contain no zeros at all.

**Modeling setup.** Eight models on one fold structure. Five classifiers (logistic regression L2,
elastic-net logistic, random forest, LightGBM, XGBoost) trained on the binary label, and three
regressors (`RidgeCV`, RF, LightGBM) trained on the continuous `t_score` and never on any label — one
regressor fit serves both clinical cutoffs by thresholding the predicted T-score twice. All are wrapped
in a `Pipeline` of median imputation → standard scaling → estimator (`_pipe`), so imputation and
scaling are always learned inside the training fold. Evaluated with 5-fold
`StratifiedKFold(random_state=42)`; the seed is 42 throughout and the whole run reproduces exactly.
Class imbalance is handled per-model (`class_weight='balanced'`, or `scale_pos_weight` for XGBoost).
Both boosters are aggressively regularized (`max_depth=2`, `reg_lambda=50`) because this n overfits
trivially. `rank_within_folds` makes classifier probabilities and negated regressor T-scores
commensurable before they are pooled.

**Do not rank models by the train/test gap.** The forest's in-sample AUC is 1.000 by construction — on
shuffled labels it still reaches 0.997 — so the leaderboard reports train, test and OOB AUC side by
side. OOB is the honest in-sample number for a bagged ensemble. Relatedly, `RF_MIN_SAMPLES_LEAF = 1`
was chosen by nested CV, not assumed. The gap is the price of the performance, not a defect to
regularize away.

**OOB AUC is withheld rather than reported when coverage is poor — do not "fix" this.** scikit-learn
≥ 1.9 makes the bootstrap `sample_weight`-aware, and `class_weight='balanced'` is applied as a sample
weight, so on an imbalanced target the minority class is oversampled into nearly every tree and rarely
lands out-of-bag. At T ≤ −2.5 only ~28% of cases get an OOB estimate. Worse, sklearn returns uncovered
rows as an all-**zero** decision-function row rather than NaN, so an `isnan` guard silently keeps them
and scores every uncovered case at 0.0 — the lowest possible rank. That produced an OOB AUC of
**0.108**: not a weak model but an inverted one, in a PRESENT-tier leaderboard. `_oob_auc` drops
uncovered rows and refuses to report at all when either class falls below `MIN_OOB_COVERAGE = 0.80`,
printing the reason instead of a number.

**Tree importances are deliberately absent** from reporting. Gini importance and split counts are
unsigned and biased toward continuous features over binary ones, and here they inverted the real
ranking. Do not reintroduce `feature_importances_` as a presented result.

**Derived-variable details worth knowing:** `sleep_hrs` coalesces `SLD012` (newer cycles) with
`SLD010H` (older); `phq9_score` sums the nine PHQ items clipped to 0–3 with `min_count=5`, so
respondents with fewer than five answered items get NaN; `serum_vitd_nmol` coalesces `LBXVIDMS` and
`LBDVIDMS`. `total_calcium_mg` / `total_vitd_mcg` add a **two-day** dietary average to supplement
intake using plain addition, so a missing component yields a missing total rather than a fabricated
one. The supplement 0-fill is **scoped to respondents who appear in a `DSQTOT` file** — absence from
every file means unobserved (left NaN, flagged by `supp_data_available`), whereas a NaN nutrient for
someone present in a file means "reported no supplement", because NHANES codes non-users as blank
rather than 0.

**Alcohol: current and lifetime drinking are different questions.** `ALQ101`/`ALQ111` ask about the
past 12 months; `ALQ110` asks about ever having had 12+ drinks in a lifetime and is asked only of those
who said no. `ALQ130` (drinks/day) is asked down both branches, so a blank for a confirmed
non-**current** drinker is a true zero. The zero-fill therefore keys on `current_drinker`, while
`ever_drinker` is a lifetime OR across all three items via `np.fmax`. Conflating them mislabels 62
women as non-drinkers.

**T-scores** use fixed NHANES III young-adult reference means/SDs; `t_score` is the **minimum** of
femoral-neck and total-hip (the WHO/ISCD lowest-of-two rule), rounded to three decimals before
thresholding; `at_risk` is `t_score <= -1.0` (osteopenia or worse — **not** osteoporosis alone) and
`osteoporosis` is `t_score <= -2.5`.

## Results and how to talk about them

**The nested-CV number is the defensible one**, not the leaderboard. Fitting eight models and reporting
the best is biased upward; `nested_cv_selection` moves model choice inside each outer training fold so
no test row helps pick the model scored on it. The comparator is **OST** (`0.2 × (weight_kg − age)`), a
validated two-input formula — reporting AUC without it is uninterpretable.

| Target | Events | OST | Weight alone | Leaderboard | Nested | Δ vs OST | Verdict |
|---|---|---|---|---|---|---|---|
| Osteopenia+ (T ≤ −1.0) | 645 | 0.739 | 0.737 | 0.752 | **0.747** | +0.008 [−0.008, +0.025] | **Not separable** |
| Osteoporosis (T ≤ −2.5) | 76 | 0.780 | 0.766 | 0.793 | **0.786** | +0.007 [−0.016, +0.030] | **Not separable**, and underpowered |

**The headline finding is a null, and it must be reported as one.** On the deduplicated postmenopausal
cohort the full panel — 15 variables, 16 model columns (alcohol enters as the specialist's three
categories) — is not statistically separable from OST, and not from **weight alone** either
(T ≤ −1.0: +0.010 [−0.007, +0.027]; T ≤ −2.5: +0.021 [−0.005, +0.048]). There is no
`menopause_type` (the specialist ruled it out; menopause is defined only by the no-period-in-12-months
gate) and no activity variable (arm-only, see below). The pre-rewrite claim of +0.063 [+0.046, +0.082]
over OST was an artifact of the duplicated respondents.

**The panel follows the specialist's written variable list (`Notes/SpecialistUpdate.docx`).** Items are
continuous unless the specialist specified otherwise. Alcohol (item 8) is zero / < 3 / 3+ drinks per
day, with < 3 as reference (`alcohol_zero`, `alcohol_3plus`; missing answers fall to the reference via
in-fold median imputation). Sleep (item 20) is continuous in the headline and in five bands in arm J.
Activity (item 11) is MET-min/week in arm I and moderate + vigorous min/week + sitting in arm I2. The
specialist's descriptive bands (BMI ×6, calcium ×4, income ×3, sleep ×5, alcohol ×3, vitamin D intake in
IU/day) are in `table_one_categories.csv`. Open: antidepressants (item 18, needs an RXQ_RX drug-class
mapping) and the 5-year prior-fracture window (round-2 R1). Not available: falls (item 19).

`auc_decomposition.csv` separates the two things that changed at once, holding the feature panel and
the model set fixed and varying only the cycle list and the cohort gate:

| Stage | n | Best AUC | OST | Δ vs OST |
|---|---|---|---|---|
| A. 6 cycles, all DXA (as published) | 1,484 | 0.836 | 0.747 | +0.089 [+0.070, +0.107] |
| B. 6 cycles, postmenopausal | 1,272 | 0.831 | 0.733 | +0.098 [+0.077, +0.120] |
| C. 5 cycles, all DXA | 1,308 | 0.763 | 0.753 | +0.010 [−0.005, +0.024] |
| D. 5 cycles, postmenopausal (shipped) | 1,111 | 0.755 | 0.739 | +0.016 [−0.001, +0.030] |

**Duplicate fix alone (A→C): −0.073. Menopause gate alone (A→B): −0.005.** Do not attribute any
material part of the drop to narrowing the cohort — it costs essentially nothing, and the "beats OST"
claim already dies at stage C, before the menopause gate is applied. Stage A scores 0.836 rather than
the published 0.810 because it runs the *rebuilt* panel on the *old* duplicated cohort; the rebuilt
variables and the fingerprint-filled serum vitamin D gave the duplicate pairs even more to exploit.
Stage A vs C is the valid subtraction because only the cycle list differs.

One-sided p and the percentile CI can look inconsistent on these rows (e.g. p = 0.028 with a CI of
[−0.000, +0.031] for age + weight below). They are not: p is the fraction of bootstrap deltas at or
below zero, so any p above 0.025 puts the 2.5th percentile below zero. The `Verdict` column keys on the
CI, which is the conservative choice — do not restate a row as positive because its p is under 0.05.

**Optimism** (leaderboard − nested) is +0.005 at T ≤ −1.0 and +0.007 at T ≤ −2.5; it can come out
negative at 76 events, which is noise, not evidence that nesting improves a model.

**Body size is very nearly the whole model.** From `model_block_ablation_osteopenia.csv`:

| Block dropped | Vars | AUC | Δ vs full panel |
|---|---|---|---|
| body size (`bmi` + `weight_kg`) | 13 | **0.603** | **+0.151 [+0.115, +0.187]** |
| all menopause / hormone vars | 13 | 0.749 | +0.006 [−0.000, +0.013] |
| all lifestyle vars (smoking, alcohol) | 13 | 0.756 | −0.001 [−0.004, +0.003] |
| all history / family vars | 11 | 0.751 | +0.004 [−0.003, +0.011] |
| *keep only* age + weight (OST inputs) | 2 | 0.739 | +0.016 [−0.000, +0.031] |
| *keep only* age + bmi | 2 | 0.718 | +0.037 [+0.016, +0.057] |

Remove body size and the model falls to 0.603. Remove any other block *in its entirety* and nothing
measurable happens. Age plus weight alone reproduces OST's AUC to three decimals, and the remaining 14
columns buy +0.016 on top of it — an interval that touches zero, so they do not measurably add to
OST's two inputs.

Single-variable ablation puts `bmi` at ≈0 while permutation importance ranks it second. That is not a
contradiction and neither number is wrong — `weight_kg` substitutes for it, so shuffling `bmi` inside a
model that still has weight costs little, and dropping `bmi` alone costs nothing because weight covers
it. Only dropping the pair together shows the block's true worth. **Quote the block ablation, not the
single-variable row, when asked how much body size matters.**

In the per-predictor table, five of the 16 columns have a 95% CI excluding OR = 1: `weight_kg` 0.51
(0.39–0.65) per 10 kg, `ever_used_estrogen` 0.59 (0.43–0.76), `poverty_income_ratio` 0.90 (0.82–0.98)
— protective; and `age` 1.27 (1.07–1.52) per 5 y, `any_prior_fracture` 1.76 (1.20–2.74) — risk.
`steroid_use` 1.49 (0.98–2.39) and both alcohol categories (none 0.90, 3+ 0.71 vs < 3/day) are `ns`.
`weight_kg` leads permutation importance by an order of magnitude (+0.2395 LR / +0.1517 RF against
+0.0239 for the next).

**The `osteoporosis` target is underpowered and `power_gate.csv` says so in advance.** Every analysis
cohort sits at ~3.1–4.8 events per predictor against the Riley floor of 10 (`RILEY_MIN_EPP`), so it is
reported as underpowered rather than as a negative finding.

**Physical activity is arm-only.** Both activity items are absent for all of 2005–06 (pre-GPAQ
instrument), so in the headline model they could only enter by imputing a whole cycle — which an
earlier version did, coding all 173 of those women as "no vigorous activity". `met_min_week`
implements the specialist's references (PMC9858810, PMC12851727; WHO GPAQ): 8 METs × days × minutes
for vigorous work and recreation, 4 for moderate work, moderate recreation and walk/bicycle transport,
summed; a domain answered No is a true zero; days 1–7, minutes 10–960. It is modelled as
`log_met_min_week` (skew ≈ +4; median 720, max 43,680 MET-min/wk = 728 MET-h/wk). Arm I adds it plus
`sedentary_min_day`, and arm I2 adds `log_moderate_min_wk` + `log_vigorous_min_wk` + sitting, both on
the 932 women from 2007 on. Arms I, I2 and J were specified from the rewrite plan and the specialist's
list and added when implemented, after arms C–H had been run.

**All arms (C–J) show no detectable gain.** Vitamin D intake (−0.002), serum 25(OH)D (−0.001),
rheumatoid arthritis (0.000), PHQ-9 as a binary (−0.001), physical activity (I +0.004 [−0.002, +0.009];
I2 +0.003 [−0.002, +0.009]), sleep in five bands (J −0.001 [−0.007, +0.006]) and both diabetes
reclassifications. The C–H nulls were stated in advance, which is what makes them reportable. Arm H
(site sensitivity) carries **no delta** — it respecifies the outcome, so its AUC is computed on a
different label and a different set of rows than the headline, and subtracting the two would compare
two different questions.

**Variable importance lives in two places and they answer different questions.**
`clinical_predictor_table.csv` is permutation importance — shuffle a column inside a model that was
*trained with it*, so a variable with a close substitute looks unimportant even when the pair matters.
`model_variable_ablation_*.csv` refits *without* the variable entirely, which is the question a
clinician is actually asking. Where the two disagree, collinearity is the reason, and
`model_block_ablation_*.csv` exists to resolve it by dropping correlated variables as a group.

## Outputs and the tiering convention

Every result table goes through `save_csv(df, filename, tier)`, which writes to `outputs/` and prints
the tier as it writes. Keep using it — the folder is self-describing at the point of creation, which is
why there is no README in `outputs/` to drift out of sync. Tiers:

- **PRESENT** — for the clinical audience: `nested_cv_verdict.csv` (the bottom line, open this first),
  `table_one.csv`, `clinical_predictor_table.csv`, `forest_plot_odds_ratios*.png`,
  `model_variable_ablation_*.csv`, `model_block_ablation_*.csv`, `calibration_*.png`,
  `referral_table.csv`, `threshold_sweep.csv`, `model_leaderboard_*.csv`, `prespecified_arms.csv`.
- **METHODS** — defends a methodological choice if challenged: `power_gate.csv`, `rf_leaf_tuning.csv`,
  `auc_decomposition.csv`.
- **DIAGNOSTIC** — `coefficient_diagnostics.csv`. A leak and sign-error detector, in standardised units
  and unstable across collinear predictors. **Not a findings table**; the script says so in its own
  output. Two standing alarms live here: any `|standardised coef| > LEAK_COEF_THRESHOLD` (2.0) suggests
  a BMD-derived column entered the features, and `EXPECTED_SIGNS` flags clinically backwards
  coefficients. Each flagged sign is printed with the name of its most correlated partner, because a
  residual sign on the weaker member of a collinear pair carries no clinical meaning — `bmi` flips
  precisely because `weight_kg` absorbs the adiposity effect. There is deliberately **no
  `EXPECTED_SIGNS` entry for diabetes**: the diabetic bone paradox (higher BMD, higher fracture risk)
  makes a positive BMD coefficient the expected finding.

**Two cutoff tables mean different things by the same numbers.** `referral_table.csv` leads with
`Top fraction flagged` — a quantile of out-of-fold nested-CV ranks. `threshold_sweep.csv` keeps
`Probability Cutoff` — a real probability from a *sigmoid-calibrated* forest, and carries `Model` and
its AUC on every row. Never merge them or share an axis.

**The calibration gap is closed.** `calibration_figure` plots the raw against the sigmoid-calibrated
forest with Brier scores for both. This was the long-standing known gap; the old plotting code had gone
with `SF_new1.py`.

## Data layout and lineage

```
sf_26-27/
  OsteoporosisML.py                        # the entire pipeline, blocks A-G
  data/raw/<cycle>/<MODULE>_<suffix>.csv   # NHANES source, one folder per cycle
  data/processed/                          # option_b_v4_final.csv + legacy files
  outputs/                                 # regenerated every run; see tiering above
  Notes/project_walkthrough.html           # the project explainer
  Notes/statistician_brief.html            # methodological rulings and rationale
```

`data/processed/analysis_cohort_postmenopausal.csv` (1,111 × 119) is the only file the script writes
outside `outputs/` and the download caches, and it is the current analysis input. **Every other file in
`data/processed/` is pre-rewrite and scored on the duplicated cohort** — `option_b_v4_final.csv` (the
old preferred input), `nhanes_osteoporosis_cleaned.csv`, `option_b_v3_allcycles.csv`,
`option_b_v4_with_new_vars.csv` and the `osteoporosis_train_set` / `osteoporosis_test_set` pair are
artifacts of **earlier scripts no longer in the repo** — don't assume they can be regenerated, and don't
use them for new analysis. The train/test CSVs in particular carry legacy defects: duplicated `at_risk`
columns and duplicate one-hot education columns differing only in capitalization, from the
label-vs-code inconsistency across cycles. **They also predate the duplicate-respondent fix, so any
model scored on them is scored on the inflated cohort.**

`outputs/run_log.txt`, if present, is a manual stdout capture by the user, not a script artifact — it
will silently go stale.

**Git:** `.gitignore` lists `data/` and `outputs/`, but `data/` was committed before that and stays
tracked (~31 MB history) — deliberately, since several processed files cannot be regenerated and the
repo is their only copy. Nothing in `outputs/` is tracked, so a fresh clone has no results until the
pipeline runs. Do not `git rm --cached` the data directory.

Reference document (not code, but authoritative for variable definitions):
`nhanes_data_dictionary _allCycles.doc` at the repo root. `Notes/osteoporosis project.docx` holds
study write-up material. Earlier versions of this file cited a research-paper PDF and three ER-diagram
PDFs — **no PDFs exist in the repo**; ask the user for them if the study design spec is needed.
