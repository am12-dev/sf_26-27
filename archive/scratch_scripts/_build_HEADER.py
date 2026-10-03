"""Early osteoporosis risk detection without a DXA scan — NHANES 2005-March 2020.

Predicts low bone mass in postmenopausal non-Hispanic White women aged 50-65 from
routinely available survey, examination and laboratory variables, with the DXA-derived
measurements the model is meant to replace held strictly out of the feature set.

Run with:  python OsteoporosisML.py      (no arguments, no flags)

WHAT CHANGED IN THIS REWRITE, AND WHY IT MATTERS
------------------------------------------------
1. 2017_2018 was removed from CYCLES. NHANES stopped field work in March 2020 and
   pooled the partial 2019-2020 sample with the COMPLETE 2017-2018 cycle into the
   `P_` files under re-numbered SEQNs. Loading both cycles therefore loaded 176 of
   these women twice with disjoint IDs, which SEQN-based dedup cannot see. Because
   StratifiedKFold splits rows and not people, those pairs straddled train and test
   folds and inflated every cross-validated AUC. `audit_duplicates` now asserts on a
   physical fingerprint so the defect cannot come back silently.
   Cohort consequence: 1,484 -> 1,308 with a femoral-neck DXA.

2. The cohort is now postmenopausal only (n = 1,111). 156 still-cycling women and 41
   whose status cannot be determined are excluded, and they are NOT the same group —
   the 41 are unknown, not premenopausal, and must never be described as such.

3. Feature selection is an ALLOWLIST (`FEATURE_GROUPS`), not an exclusion list. The
   old design included every column not explicitly excluded, so any newly derived
   column leaked the target unless somebody remembered to exclude it. `BMD_DENYLIST`
   asserts on top of that as a second gate.

4. Sentinel handling is PER VARIABLE (`SPEC`), not one global refused/don't-know list.
   A global list cannot be right: 99 is a refusal for RHQ060 and a legitimate value
   for PAD680.

5. Every prior published AUC is withdrawn. 0.810 and 0.806 were computed on the
   duplicated cohort. Nothing from the old run carries forward.

METHODOLOGICAL COMMITMENTS THAT ARE NOT NEGOTIABLE
--------------------------------------------------
- The NESTED-CV number is the defensible one, not the leaderboard. Fitting eight models
  and reporting the best selects on the test fold.
- OST = 0.2 x (weight_kg - age) is the comparator. An AUC without it is uninterpretable.
- Do NOT rank models by the train/test gap. The forest reaches AUC 0.997 on shuffled
  labels in-sample; OOB is its honest in-sample figure and is reported alongside.
- Do NOT reintroduce `feature_importances_` as a presented result. Gini importance is
  unsigned and biased toward continuous features, and here it inverted the real
  ranking. Permutation importance and ablation are what get reported.
- `coefficient_diagnostics.csv` is a bug detector, not a findings table.

DEPENDENCIES (nothing else tracks them — there is no requirements.txt)
  pandas, numpy, matplotlib, scikit-learn, lightgbm, xgboost, requests

NETWORK  Supplement (`DSQTOT_*`) and day-2 dietary (`DR2TOT_*`) extracts download from
  wwwn.cdc.gov into data/raw/<cycle>/. All caches are committed, so a fresh clone runs
  fully offline. A failed download is logged and skipped, never fatal.

RUNTIME  Roughly 25-40 minutes. The bootstraps, permutation importance, the ablation
  grid and the nested CV dominate. Seeded at SEED = 42 throughout; the run reproduces
  exactly.

LAYOUT   Block A configuration · B data layer · C cohort · D derivations ·
         E allowlist and power gate · F model layer · G arms, reporting, main().
"""
