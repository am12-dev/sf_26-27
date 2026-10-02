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

import sys

# Must run before pandas is imported. Progress output uses emoji and the default Windows
# console codepage (cp1252) raises UnicodeEncodeError without this. Not cosmetic.
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    pass

import os
import warnings
from functools import reduce

import numpy as np
import pandas as pd
import requests

warnings.filterwarnings('ignore')

# ================================================================================
# BLOCK A — CONFIGURATION
# ================================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'raw')
PROC_DIR = os.path.join(BASE_DIR, 'data', 'processed')
OUT_DIR  = os.path.join(BASE_DIR, 'outputs')

# 2017_2018 IS DELIBERATELY ABSENT. NHANES 2017-March 2020 field work stopped early, so
# NCHS pooled the partial 2019-2020 sample WITH the complete 2017-2018 cycle: the
# 2017_2018 respondents are physically inside the P_ files under re-numbered SEQNs.
# Running both cycles duplicated 176 cohort women (161 postmenopausal, 12.7%), and
# StratifiedKFold splits rows rather than people, so those duplicates straddled folds.
# SEQN dedup cannot find them (DEMO_J 93703-102956 vs P_DEMO 109263-124822 are disjoint);
# only dropping the cycle does. Do not re-add 2017_2018.
# 2015_2016 and 2021_2023 are also present in data/raw/ and also deliberately excluded —
# do not add them without checking with the user.
CYCLES = [
    {'name': '2005_2006', 'suffix': 'D', 'prefix': ''},
    {'name': '2007_2008', 'suffix': 'E', 'prefix': ''},
    {'name': '2009_2010', 'suffix': 'F', 'prefix': ''},
    {'name': '2013_2014', 'suffix': 'H', 'prefix': ''},
    {'name': '2017_2020', 'suffix': 'P', 'prefix': 'P_'},
]

SUPP_URLS = [
    ('2007_2008', 'DSQTOT_E', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2007/DataFiles/DSQTOT_E.xpt'),
    ('2009_2010', 'DSQTOT_F', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2009/DataFiles/DSQTOT_F.xpt'),
    ('2013_2014', 'DSQTOT_H', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2013/DataFiles/DSQTOT_H.xpt'),
    ('2017_2020', 'P_DSQTOT', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_DSQTOT.xpt'),
]

DAY2_URLS = [
    ('2005_2006', 'DR2TOT_D', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/DR2TOT_D.xpt'),
    ('2007_2008', 'DR2TOT_E', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2007/DataFiles/DR2TOT_E.xpt'),
    ('2009_2010', 'DR2TOT_F', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2009/DataFiles/DR2TOT_F.xpt'),
    ('2013_2014', 'DR2TOT_H', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2013/DataFiles/DR2TOT_H.xpt'),
    ('2017_2020', 'P_DR2TOT', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_DR2TOT.xpt'),
]

# --- cohort checkpoints. These are asserts on purpose: they pin the published cohort. ---
N_DXA_COHORT      = 1308    # women 50-65, NH White, with a femoral-neck DXA result
N_POSTMENOPAUSAL  = 1111    # the analysis cohort (Q3)
N_STILL_CYCLING   = 156     # excluded: reported a period in the last 12 months
N_MENO_UNKNOWN    = 41      # excluded: menopausal status undeterminable

T_OSTEOPENIA   = -1.0
T_OSTEOPOROSIS = -2.5

# NHANES III young-adult non-Hispanic White female reference (Looker et al.)
FEMORAL_NECK_MEAN, FEMORAL_NECK_SD = 0.858, 0.120
TOTAL_HIP_MEAN,    TOTAL_HIP_SD    = 0.942, 0.122

SEED = 42
RF_MIN_SAMPLES_LEAF = 1
RF_LEAF_GRID = [1, 2, 5, 10, 20, 50]
LEAK_COEF_THRESHOLD = 2.0
RILEY_MIN_EPP = 10.0   # events per predictor below which a target is reported as underpowered

# No 'diabetes' entry, deliberately: the diabetic bone paradox (higher BMD, higher
# fracture risk) means a positive BMD coefficient is the expected finding, not a bug.
EXPECTED_SIGNS = {
    'weight_kg': -1, 'bmi': -1, 'height_cm': -1, 'age': +1,
    'years_since_menopause': +1, 'oophorectomy': +1,
    'ever_used_estrogen': -1, 'any_prior_fracture': +1, 'steroid_use': +1,
    'serum_vitd_nmol': -1, 'total_calcium_mg': -1, 'total_vitd_mcg': -1,
    'family_hx_osteoporosis': +1, 'parental_hip_fracture': +1,
}

CLINICAL_UNITS = {
    'weight_kg': (10, 'per 10 kg'), 'height_cm': (5, 'per 5 cm'), 'bmi': (5, 'per 5 kg/m2'),
    'age': (5, 'per 5 years'), 'years_since_menopause': (5, 'per 5 years'),
    'serum_vitd_nmol': (25, 'per 25 nmol/L'), 'total_calcium_mg': (500, 'per 500 mg'),
    'total_vitd_mcg': (10, 'per 10 mcg'), 'poverty_income_ratio': (1, 'per 1 unit'),
    'alcohol_drinks_day': (1, 'per 1 drink/day'), 'phq9_score': (5, 'per 5 points'),
    'sedentary_min_day': (60, 'per 1 hour/day'),
    'sleep_hrs': (1, 'per 1 hour'),
}

def print_section(title):
    print(f"\n{'=' * 78}\n  {title}\n{'=' * 78}")

# ================================================================================
# BLOCK B — DATA LAYER
# ================================================================================
#
# Three rules this block exists to enforce, each of which was a live defect:
#
#  1. EXPLICIT FILE MAP, NEVER A GLOB. OSQ_*.csv does not match P_OSQ.csv, so a glob
#     silently drops all 264 women of the 2017_2020 cycle and the run still "succeeds".
#     data/raw/2017_2020/ also contains a stray "P_DEMO (1).csv" that a glob would find.
#  2. PER-VARIABLE SENTINELS, NEVER A GLOBAL LIST. A global {7, 9, 77, 99, ...} blanks a
#     legitimate 9 hours of sleep and a legitimate 7 drinks/day, while missing 999 in
#     RHQ060. Each column declares its own.
#  3. ONE SHARED DUAL-FORM DECODER. The 2005-2014 CSVs were exported WITH value labels
#     applied ("Female", "Yes", "Menopause/Change of life"); the P_ files are raw numeric
#     codes. Any arithmetic that assumes one form silently NaNs the other four cycles —
#     that is how phq9_score ended up 80% missing.
#
# The P_ files also carry a denormal float, 5.397605346934028e-79, where the code 0
# belongs (e.g. DPQ010 "Not at all"). It is neither NaN nor 0, so it survives every
# na_values check and poisons any sum. sanitise_denormals() snaps it to 0.

DENORMAL_EPS = 1e-30

# --- the declarative variable specification --------------------------------------
# kind:      num | yesno | cat
# sentinels: numeric codes meaning refused / do-not-know FOR THIS COLUMN ONLY
# valid:     plausibility window applied after decoding (num only)
# levels:    canonical value -> accepted forms, lowercased. Numeric codes differ
#            between the labelled cycles and the P_ files, so both forms are listed.

SPEC = {
    # demographics
    'RIDAGEYR': {'kind': 'num', 'valid': (0, 120)},
    'INDFMPIR': {'kind': 'num', 'valid': (0, 5)},
    'DMDEDUC2': {'kind': 'cat'},
    'RIAGENDR': {'kind': 'cat'},
    'RIDRETH1': {'kind': 'cat'},
    'SDMVPSU':  {'kind': 'num'},
    'SDMVSTRA': {'kind': 'num'},
    'WTMEC2YR': {'kind': 'num'},
    'WTMECPRP': {'kind': 'num'},
    # body measures and DXA (measured; no sentinels, only plausibility windows)
    'BMXBMI': {'kind': 'num', 'valid': (10, 80)},
    'BMXWT':  {'kind': 'num', 'valid': (25, 250)},
    'BMXHT':  {'kind': 'num', 'valid': (120, 210)},
    'DXXNKBMD': {'kind': 'num', 'valid': (0.2, 1.8)},
    'DXXOFBMD': {'kind': 'num', 'valid': (0.2, 1.8)},
    # diet and lab
    'DR1TCALC': {'kind': 'num', 'valid': (0, 8000)},
    'DR1TVD':   {'kind': 'num', 'valid': (0, 400)},
    'DR2TCALC': {'kind': 'num', 'valid': (0, 8000)},
    'DR2TVD':   {'kind': 'num', 'valid': (0, 400)},
    'LBXVIDMS': {'kind': 'num', 'valid': (5, 400)},
    'LBDVIDMS': {'kind': 'num', 'valid': (5, 400)},
    # activity and behaviour
    'PAD680': {'kind': 'num', 'sentinels': [7777, 9999], 'valid': (0, 1440)},
    'PAQ650': {'kind': 'yesno'},
    'ALQ130': {'kind': 'num', 'sentinels': [777, 999, 99], 'valid': (1, 30)},
    # Ever-drinker gate. ALQ130 (drinks per drinking day) is asked only of people who
    # drink, so its 328 blanks are structurally zero, not missing. ALQ101 is the gate in
    # 2005-2014, ALQ111 in the P_ release; ALQ110 catches lifetime-abstainer follow-up.
    'ALQ101': {'kind': 'yesno'}, 'ALQ110': {'kind': 'yesno'}, 'ALQ111': {'kind': 'yesno'},
    'SMQ020': {'kind': 'yesno'},
    # sleep. SLD010H is whole hours (2005-2014); SLD012 allows half hours (2017-2020).
    'SLD010H': {'kind': 'num', 'sentinels': [77, 99], 'valid': (2, 14)},
    'SLD012':  {'kind': 'num', 'sentinels': [77, 99], 'valid': (2, 14)},
    # PHQ-9: four ordered response levels scored 0-3
    **{c: {'kind': 'cat', 'sentinels': [7, 9], 'levels': {
            0.0: ['not at all', '0'], 1.0: ['several days', '1'],
            2.0: ['more than half the days', '2'], 3.0: ['nearly every day', '3']}}
       for c in ['DPQ010', 'DPQ020', 'DPQ030', 'DPQ040', 'DPQ050',
                 'DPQ060', 'DPQ070', 'DPQ080', 'DPQ090']},
    # conditions
    'MCQ160A': {'kind': 'yesno'},
    'DIQ010':  {'kind': 'cat', 'sentinels': [7, 9], 'levels': {
                    1.0: ['yes', '1'], 0.0: ['no', '2'], 2.0: ['borderline', '3']}},
    # Arthritis type. The column NAME differs by cycle — MCQ190 (2005-2008),
    # MCQ191 (2009-2010), MCQ195 (2013 onward). An earlier note claiming 2009-2010 does
    # not ask arthritis type was wrong; MCQ191 asks it.
    **{c: {'kind': 'cat', 'sentinels': [7, 9], 'levels': {
            'osteoarthritis': ['osteoarthritis',
                               'osteoarthritis or degenerative arthritis', '1'],
            'rheumatoid':     ['rheumatoid arthritis', '2'],
            'psoriatic':      ['psoriatic arthritis', '3'],
            'other':          ['other', '4']}}
       for c in ['MCQ190', 'MCQ191', 'MCQ195']},
    # fracture history and family history
    'OSQ010A': {'kind': 'yesno'}, 'OSQ010B': {'kind': 'yesno'},
    'OSQ010C': {'kind': 'yesno'}, 'OSQ130': {'kind': 'yesno'},
    'OSQ150': {'kind': 'yesno'}, 'OSQ170': {'kind': 'yesno'},
    'OSQ200': {'kind': 'yesno'},
    'OSQ180': {'kind': 'num', 'sentinels': [999, 99999, 77777], 'valid': (10, 100)},
    # reproductive
    'RHQ031': {'kind': 'yesno'},
    'RHQ060': {'kind': 'num', 'sentinels': [999, 9999, 77777, 99999], 'valid': (20, 70)},
    'RHQ074': {'kind': 'yesno'},
    'RHD280': {'kind': 'yesno'},
    'RHQ305': {'kind': 'yesno'},
    'RHQ540': {'kind': 'yesno'},
    'RHQ554': {'kind': 'yesno'},
    'RHQ570': {'kind': 'yesno'},
    **{c: {'kind': 'num', 'sentinels': [777, 999, 7777, 9999, 77777, 99999],
           'valid': (0, 60)}
       for c in ['RHQ560Q', 'RHQ576Q', 'RHQ586Q']},
    **{c: {'kind': 'cat', 'sentinels': [7, 9],
           'levels': {'months': ['months', '1'], 'years': ['years', '2']}}
       for c in ['RHQ560U', 'RHQ576U', 'RHQ586U']},
    # Reason periods stopped. RHD042 (2005-2010) merges menopause and hysterectomy into
    # ONE category, which is why menopause type cannot be read off it and has to be
    # reconstructed from hysterectomy / oophorectomy status in block D.
    'RHD042': {'kind': 'cat', 'sentinels': [7, 9, 77, 99], 'levels': {
                   'pregnancy': ['pregnancy', '1'],
                   'breastfeeding': ['breast feeding', '2'],
                   'meno_or_hyst': ['menopause/hysterectomy', '3'],
                   'medical': ['medical conditions/treatments', '4'],
                   'other': ['other', '5']}},
    # RHD043 codes in P_RHQ are NOT sequential: 3 = Hysterectomy, 7 = Menopause.
    # Verified two ways against the labelled 2017_2018 file — frequency ratio 1.58,
    # matching the 1.60 overall pooling ratio, and 776 of the 779 code-3 rows report
    # RHD280 = Yes. Assuming the usual 1..7 order silently swaps the two categories.
    'RHD043': {'kind': 'cat', 'sentinels': [77, 99], 'levels': {
                   'pregnancy': ['pregnancy', '1'],
                   'breastfeeding': ['breast feeding', '2'],
                   'hysterectomy': ['hysterectomy', '3'],
                   'menopause': ['menopause/change of life', '7'],
                   'other': ['other', '9']}},
}

# module -> columns pulled from it
# Supplement and day-2 dietary nutrients. These arrive from the download path rather
# than MODULE_COLS, but they go through the same decoder so the guards actually run.
# Bounds are deliberately generous: a guard that is too tight silently deletes real
# intake, which is the worse error. DR2TCALC tops out at 11,830 mg in the raw files,
# which is not physiologically possible from food and is what the ceiling is for.
SPEC['DSQTCALC'] = {'kind': 'num', 'valid': (0, 5000)}     # supplement calcium, mg
SPEC['DSQTVD'] = {'kind': 'num', 'valid': (0, 3000)}       # supplement vitamin D, mcg

MODULE_COLS = {
    'DEMO':   ['RIAGENDR', 'RIDRETH1', 'RIDAGEYR', 'INDFMPIR', 'DMDEDUC2',
               'SDMVPSU', 'SDMVSTRA', 'WTMEC2YR', 'WTMECPRP'],
    'BMX':    ['BMXBMI', 'BMXWT', 'BMXHT'],
    'DXXFEM': ['DXXNKBMD', 'DXXOFBMD'],
    'DR1TOT': ['DR1TCALC', 'DR1TVD'],
    'VID':    ['LBXVIDMS', 'LBDVIDMS'],
    'PAQ':    ['PAD680', 'PAQ650'],
    'DPQ':    ['DPQ010', 'DPQ020', 'DPQ030', 'DPQ040', 'DPQ050',
               'DPQ060', 'DPQ070', 'DPQ080', 'DPQ090'],
    'SMQ':    ['SMQ020'],
    'ALQ':    ['ALQ101', 'ALQ110', 'ALQ111', 'ALQ130'],
    'DIQ':    ['DIQ010'],
    'MCQ':    ['MCQ160A', 'MCQ190', 'MCQ191', 'MCQ195'],
    'OSQ':    ['OSQ010A', 'OSQ010B', 'OSQ010C', 'OSQ130',
               'OSQ150', 'OSQ170', 'OSQ180', 'OSQ200'],
    'RHQ':    ['RHQ031', 'RHQ060', 'RHQ074', 'RHD042', 'RHD043', 'RHD280', 'RHQ305',
               'RHQ540', 'RHQ554', 'RHQ570',
               'RHQ560Q', 'RHQ560U', 'RHQ576Q', 'RHQ576U', 'RHQ586Q', 'RHQ586U'],
    'SLQ':    ['SLD010H', 'SLD012'],
}

# Modules legitimately absent for a cycle, so a missing file is expected, not a defect.
# The P_ release ships no vitamin D lab file at all; block D recovers serum 25(OH)D for
# part of that cycle through a physical-measurement crosswalk instead.
KNOWN_ABSENT = {('2017_2020', 'VID')}


def cycle_file(cycle, module):
    """Exact filename for a module in a cycle. Explicit construction, never a glob."""
    return f"{cycle['prefix']}{module}.csv" if cycle['prefix'] \
        else f"{module}_{cycle['suffix']}.csv"


def sanitise_denormals(df):
    """Snap denormal floats to 0. See the module note above."""
    for c in df.select_dtypes(include=['float64', 'float32']).columns:
        v = df[c].to_numpy(dtype='float64', copy=False)
        mask = (np.abs(v) < DENORMAL_EPS) & (v != 0) & ~np.isnan(v)
        if mask.any():
            df.loc[mask, c] = 0.0
    return df


def _norm(v):
    """Lowercased, whitespace-stripped string form of a raw cell, or None if missing."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    s = str(v).strip().lower()
    if s in ('', 'nan', '.', 'none'):
        return None
    # "2.0" and "2" are the same code
    if s.endswith('.0') and s[:-2].replace('-', '').isdigit():
        s = s[:-2]
    return s


_MISSING_WORDS = {'refused', "don't know", 'dont know', 'do not know',
                  'dk', 'unknown', 'missing'}


def decode(series, col):
    """Decode one raw column per its SPEC entry. Handles labels and codes alike."""
    spec = SPEC.get(col, {'kind': 'num'})
    kind = spec['kind']
    sent = set(float(s) for s in spec.get('sentinels', []))

    if kind == 'num':
        out = pd.to_numeric(series, errors='coerce')
        if sent:
            out = out.where(~out.isin(sent))
        lo, hi = spec.get('valid', (-np.inf, np.inf))
        return out.where((out >= lo) & (out <= hi))

    if kind == 'yesno':
        def f(v):
            s = _norm(v)
            if s is None or s in _MISSING_WORDS:
                return np.nan
            if s in ('yes', '1'):
                return 1.0
            if s in ('no', '2'):
                return 0.0
            return np.nan
        return series.map(f)

    # categorical
    levels = spec.get('levels')
    if levels is None:
        return series.map(lambda v: _norm(v)).where(
            lambda s: ~s.isin(_MISSING_WORDS))
    lookup = {}
    for canon, forms in levels.items():
        for form in forms:
            lookup[form] = canon

    def g(v):
        s = _norm(v)
        if s is None or s in _MISSING_WORDS:
            return np.nan
        try:
            if float(s) in sent:
                return np.nan
        except ValueError:
            pass
        return lookup.get(s, np.nan)
    return series.map(g)


def load_module(cycle, module):
    """Read one module for one cycle, keep the specified columns, decode them."""
    path = os.path.join(DATA_DIR, cycle['name'], cycle_file(cycle, module))
    if not os.path.exists(path):
        if (cycle['name'], module) not in KNOWN_ABSENT:
            print(f"    !! MISSING {cycle['name']}/{cycle_file(cycle, module)} "
                  f"— every column from {module} will be NaN for this cycle")
        return pd.DataFrame()
    raw = pd.read_csv(path, low_memory=False)
    raw = sanitise_denormals(raw)
    wanted = [c for c in MODULE_COLS[module] if c in raw.columns]
    out = pd.DataFrame({'SEQN': raw['SEQN']})
    for c in wanted:
        out[c] = decode(raw[c], c)
    return out


def load_and_merge_cycles():
    """Build one respondent-level frame across all cycles in CYCLES."""
    print_section('STEP 1: LOAD AND DECODE NHANES CYCLES')
    frames = []
    for cycle in CYCLES:
        parts = [load_module(cycle, m) for m in MODULE_COLS]
        parts = [p for p in parts if len(p) > 0]
        merged = reduce(lambda l, r: pd.merge(l, r, on='SEQN', how='left'), parts)
        merged['survey_cycle'] = cycle['name']
        frames.append(merged)
        print(f"  {cycle['name']}: {len(merged):>6,} respondents, "
              f"{merged.shape[1] - 2} decoded columns")
    df = pd.concat(frames, ignore_index=True, sort=False)
    print(f"  TOTAL   : {len(df):>6,} respondents across {len(CYCLES)} cycles")
    return df

# ================================================================================
# BLOCK C — COHORT CONSTRUCTION
# ================================================================================

def apply_filters(df):
    """Non-Hispanic White women aged 50-65 with a femoral-neck DXA result."""
    print_section('STEP 2: COHORT FILTERS')
    n0 = len(df)
    df = df[df['RIAGENDR'].astype(str).str.lower().isin(['female', '2'])].copy()
    n1 = len(df)
    df = df[df['RIDRETH1'].astype(str).str.lower().isin(['non-hispanic white', '3'])].copy()
    n2 = len(df)
    df = df[(df['RIDAGEYR'] >= 50) & (df['RIDAGEYR'] <= 65)].copy()
    n3 = len(df)
    df = df[df['DXXNKBMD'].notna()].copy()
    n4 = len(df)
    for label, n in [('respondents', n0), ('female', n1), ('non-Hispanic White', n2),
                     ('aged 50-65', n3), ('femoral-neck DXA result', n4)]:
        print(f"  {label:<28} {n:>7,}")
    assert n4 == N_DXA_COHORT, (
        f"Expected {N_DXA_COHORT:,} women with a femoral-neck DXA, got {n4:,}. "
        "This assert pins the published cohort: a change here means the cohort "
        "definition moved, not that the assert is wrong.")
    return df


# Fields that identify a person physically. Two rows agreeing on all five to full
# precision are the same woman measured once, not two women who happen to match.
FINGERPRINT = ['DXXNKBMD', 'DXXOFBMD', 'BMXWT', 'BMXHT', 'RIDAGEYR']


def audit_duplicates(df):
    """Assert that no respondent appears twice under two SEQNs.

    NHANES re-numbered SEQNs when it pooled 2017-2018 into the 2017-March 2020 release,
    so the same 176 cohort women appeared in both cycles with disjoint IDs (DEMO_J
    93703-102956 vs P_DEMO 109263-124822). ID-based dedup finds nothing. Because
    StratifiedKFold splits rows rather than people, those pairs straddled train and test
    folds and inflated every cross-validated AUC. Dropping 2017_2018 from CYCLES is the
    fix; this is the check that it stayed fixed.
    """
    print_section('STEP 2b: DUPLICATE-RESPONDENT AUDIT')
    complete = df.dropna(subset=FINGERPRINT)
    dup = complete.duplicated(subset=FINGERPRINT, keep=False)
    n_dup = int(dup.sum())
    print(f"  rows with a complete physical fingerprint : {len(complete):,}")
    print(f"  rows sharing a fingerprint with another   : {n_dup}")
    if n_dup:
        print(complete.loc[dup, ['SEQN', 'survey_cycle'] + FINGERPRINT]
              .sort_values(FINGERPRINT).head(20).to_string(index=False))
    assert n_dup == 0, (
        f"{n_dup} duplicate respondents across cycles. Check whether an overlapping "
        "cycle was added back to CYCLES (2017_2018 is inside the 2017_2020 P_ files).")
    print("  OK — no respondent appears twice.")
    return df


def compute_tscores(df):
    """T-scores against the NHANES III young-adult reference, and the two labels."""
    print_section('STEP 3: T-SCORES AND OUTCOME LABELS')
    df['femoral_neck_bmd'] = df['DXXNKBMD']
    df['total_hip_bmd'] = df['DXXOFBMD']
    df['t_femoral_neck'] = (df['DXXNKBMD'] - FEMORAL_NECK_MEAN) / FEMORAL_NECK_SD
    df['t_total_hip'] = (df['DXXOFBMD'] - TOTAL_HIP_MEAN) / TOTAL_HIP_SD
    # WHO/ISCD convention: the LOWEST of the measured sites defines the diagnosis.
    # Rounded to 3 dp BEFORE thresholding, or float error puts women who sit exactly on
    # a cutoff on either side of it depending on the machine.
    df['t_score'] = df[['t_femoral_neck', 't_total_hip']].min(axis=1).round(3)
    df['at_risk'] = (df['t_score'] <= T_OSTEOPENIA).astype(int)
    df['osteoporosis'] = (df['t_score'] <= T_OSTEOPOROSIS).astype(int)
    df['bone_status'] = np.select(
        [df['osteoporosis'] == 1, df['at_risk'] == 1],
        ['Osteoporosis', 'Low Bone Mass'], default='Normal')
    print(f"  mean T-score {df['t_score'].mean():.3f}   median age {df['RIDAGEYR'].median():.0f}")
    print(f"  T <= {T_OSTEOPENIA}: {int(df['at_risk'].sum()):,}   "
          f"T <= {T_OSTEOPOROSIS}: {int(df['osteoporosis'].sum()):,}")
    return df


def apply_menopause_gate(df):
    """Restrict to postmenopausal women (Q3 ruling), and say who was dropped and why.

    RHQ031 asks whether the respondent had a period in the past 12 months. A 'No' is the
    operational definition of postmenopausal used here. Two groups leave the cohort and
    they are NOT the same group:
      - still cycling (RHQ031 = Yes): premenopausal or perimenopausal, and much younger
        and denser than the analysis cohort, so keeping them would flatter the model.
      - undeterminable (RHQ031 missing / refused): status simply unknown. They are not
        premenopausal and must not be described as such.
    """
    print_section('STEP 4: MENOPAUSE GATE')
    status = df['RHQ031']                      # 1.0 = had a period, 0.0 = did not
    post = status == 0.0
    cycling = status == 1.0
    unknown = status.isna()
    for label, mask in [('postmenopausal (kept)', post),
                        ('still cycling (excluded)', cycling),
                        ('status undeterminable (excluded)', unknown)]:
        sub = df[mask]
        if len(sub):
            print(f"  {label:<34} {len(sub):>5,}   mean T {sub['t_score'].mean():+.3f}   "
                  f"median age {sub['RIDAGEYR'].median():.0f}")
    assert int(cycling.sum()) == N_STILL_CYCLING, int(cycling.sum())
    assert int(unknown.sum()) == N_MENO_UNKNOWN, int(unknown.sum())

    out = df[post].copy()
    out['postmenopausal'] = 1.0
    assert len(out) == N_POSTMENOPAUSAL, (
        f"Expected {N_POSTMENOPAUSAL:,} postmenopausal women, got {len(out):,}")
    print(f"\n  analysis cohort n = {len(out):,}   "
          f"T <= {T_OSTEOPENIA}: {int(out['at_risk'].sum()):,} "
          f"({out['at_risk'].mean():.1%})   "
          f"T <= {T_OSTEOPOROSIS}: {int(out['osteoporosis'].sum()):,} "
          f"({out['osteoporosis'].mean():.1%})")
    print("  by cycle: " + "  ".join(
        f"{c}={n}" for c, n in out['survey_cycle'].value_counts().sort_index().items()))
    return out

# ================================================================================
# BLOCK D — DERIVATIONS
# ================================================================================

def setup_directories():
    for d in (PROC_DIR, OUT_DIR):
        os.makedirs(d, exist_ok=True)
    for c in CYCLES:
        os.makedirs(os.path.join(DATA_DIR, c['name']), exist_ok=True)


def _download_xpt(url, dest_csv, keep=None, size_floor=2048):
    """Fetch an NHANES .xpt once and cache it as CSV.

    The cache test is "exists AND bigger than a floor", so a truncated download is
    refetched rather than trusted. A failure is logged and skipped, never fatal: every
    cache in this repo is committed, so a fresh clone runs fully offline.
    """
    if os.path.exists(dest_csv) and os.path.getsize(dest_csv) > size_floor:
        return pd.read_csv(dest_csv, low_memory=False)
    try:
        r = requests.get(url, timeout=90)
        r.raise_for_status()
        tmp = dest_csv + '.xpt'
        with open(tmp, 'wb') as fh:
            fh.write(r.content)
        d = pd.read_sas(tmp, format='xport')
        os.remove(tmp)
        if keep:
            d = d[[c for c in keep if c in d.columns]]
        d.to_csv(dest_csv, index=False)
        print(f"    downloaded {os.path.basename(dest_csv)}  ({len(d):,} rows)")
        return d
    except Exception as exc:
        print(f"    !! download failed for {os.path.basename(dest_csv)}: {exc}")
        return pd.DataFrame()


def load_supplements():
    """Total dietary-supplement calcium and vitamin D, pooled across cycles."""
    print_section('STEP 5: DIETARY SUPPLEMENT TOTALS (DSQTOT)')
    frames = []
    for cyc, stem, url in SUPP_URLS:
        dest = os.path.join(DATA_DIR, cyc, f'{stem}.csv')
        d = _download_xpt(url, dest, keep=['SEQN', 'DSQTCALC', 'DSQTVD'])
        if len(d):
            d = d[[c for c in ['SEQN', 'DSQTCALC', 'DSQTVD'] if c in d.columns]].copy()
            d = sanitise_denormals(d)
            for c in ('DSQTCALC', 'DSQTVD'):
                if c in d.columns:
                    d[c] = decode(d[c], c)
            d['survey_cycle'] = cyc
            frames.append(d)
            print(f"  {cyc}: {len(d):,} respondents in a supplement file")
    if not frames:
        return pd.DataFrame(columns=['SEQN', 'DSQTCALC', 'DSQTVD'])
    out = pd.concat(frames, ignore_index=True)
    print(f"  NOTE: 2005_2006 has no DSQTOT release, so supplement intake is "
          f"unobserved — not zero — for that cycle.")
    return out


def load_day2_dietary():
    """Day-2 24-hour recall calcium and vitamin D."""
    print_section('STEP 5b: DAY-2 DIETARY RECALL (DR2TOT)')
    frames = []
    for cyc, stem, url in DAY2_URLS:
        dest = os.path.join(DATA_DIR, cyc, f'{stem}_calcium_vitd.csv')
        d = _download_xpt(url, dest, keep=['SEQN', 'DR2TCALC', 'DR2TVD'])
        if len(d):
            d = sanitise_denormals(d[[c for c in ['SEQN', 'DR2TCALC', 'DR2TVD']
                                      if c in d.columns]].copy())
            for c in ('DR2TCALC', 'DR2TVD'):
                if c in d.columns:
                    d[c] = decode(d[c], c)
            frames.append(d)
            print(f"  {cyc}: {len(d):,} day-2 recalls"
                  + ("  (no DR2TVD in this release)" if 'DR2TVD' not in d.columns else ""))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=['SEQN'])


# --- vitamin D crosswalk ----------------------------------------------------------

CROSSWALK_KEY = ['femoral_neck_bmd', 'total_hip_bmd', 'RIDAGEYR', 'BMXWT', 'BMXHT']


def crosswalk_serum_vitd(df):
    """Recover serum 25(OH)D for the 2017_2020 cycle from the 2017_2018 release.

    The P_ (2017-March 2020) release ships no vitamin D lab file, so 264 women — a fifth
    of the cohort, and the whole of the most recent cycle — would have no serum value.
    But the 2017-2018 respondents are physically inside the P_ files under re-numbered
    SEQNs, and the 2017_2018 release DOES carry LBXVIDMS. Matching the two on five
    continuous physical measurements recovers the lab value for the women who are in
    both. The match key is the same fingerprint used by the duplicate audit: agreement
    on all five to full precision identifies the same woman.

    2017_2018 is used here ONLY as a lab-value donor. It is not a cohort cycle, none of
    its rows enter the analysis, and no outcome is read from it.
    """
    donor_dir = os.path.join(DATA_DIR, '2017_2018')
    if not os.path.isdir(donor_dir):
        print('  !! 2017_2018 donor files absent — crosswalk skipped')
        return df
    try:
        dem = pd.read_csv(os.path.join(donor_dir, 'DEMO_J.csv'), low_memory=False)
        bmx = pd.read_csv(os.path.join(donor_dir, 'BMX_J.csv'), low_memory=False)
        dxa = pd.read_csv(os.path.join(donor_dir, 'DXXFEM_J.csv'), low_memory=False)
        vid = pd.read_csv(os.path.join(donor_dir, 'VID_J.csv'), low_memory=False)
    except FileNotFoundError as exc:
        print(f'  !! crosswalk skipped: {exc}')
        return df

    donor = reduce(lambda l, r: pd.merge(l, r, on='SEQN', how='inner'),
                   [dem[['SEQN', 'RIDAGEYR']], bmx[['SEQN', 'BMXWT', 'BMXHT']],
                    dxa[['SEQN', 'DXXNKBMD', 'DXXOFBMD']],
                    vid[['SEQN'] + [c for c in ['LBXVIDMS', 'LBDVIDMS']
                                    if c in vid.columns]]])
    donor = donor.rename(columns={'DXXNKBMD': 'femoral_neck_bmd',
                                  'DXXOFBMD': 'total_hip_bmd'})
    donor['serum_donor'] = np.nan
    for c in ('LBXVIDMS', 'LBDVIDMS'):
        if c in donor.columns:
            donor['serum_donor'] = donor['serum_donor'].fillna(
                pd.to_numeric(donor[c], errors='coerce'))
    donor = donor.dropna(subset=CROSSWALK_KEY).drop_duplicates(subset=CROSSWALK_KEY)

    tgt = df[df['survey_cycle'] == '2017_2020'].dropna(subset=CROSSWALK_KEY)
    pairs = tgt[CROSSWALK_KEY + ['SEQN']].merge(
        donor[CROSSWALK_KEY + ['serum_donor']], on=CROSSWALK_KEY, how='inner')
    carried = pairs.dropna(subset=['serum_donor']).drop_duplicates('SEQN')
    lookup = carried.set_index('SEQN')['serum_donor']

    before = int(df['serum_vitd_nmol'].notna().sum())
    mask = df['survey_cycle'] == '2017_2020'
    df.loc[mask, 'serum_vitd_nmol'] = df.loc[mask, 'serum_vitd_nmol'].fillna(
        df.loc[mask, 'SEQN'].map(lookup))
    df['serum_vitd_crosswalked'] = 0.0
    df.loc[mask & df['SEQN'].isin(lookup.index), 'serum_vitd_crosswalked'] = 1.0
    after = int(df['serum_vitd_nmol'].notna().sum())
    print(f"  fingerprint matches 2017_2020 <-> 2017_2018 : {len(pairs)}")
    print(f"  of those carrying a serum value             : {len(carried)}")
    print(f"  serum 25(OH)D coverage {before} -> {after}  "
          f"(missing {len(df) - before} -> {len(df) - after})")
    return df


# --- derived variables -------------------------------------------------------------

def compute_menopause_variables(df):
    """Menopause timing and type.

    menopause_natural had to be rebuilt. The previous rule pattern-matched the reason
    text, which fails twice: RHD042 (2005-2010) merges menopause and hysterectomy into a
    SINGLE category called "Menopause/Hysterectomy", so every woman in those cycles was
    scored natural; and the P_ file is numeric-coded, so the whole 2017_2020 cycle
    matched nothing and went missing. Coverage was 831 of 1,111.

    The rebuild reads the unambiguous category where cycles provide one (RHD043) and
    disambiguates the merged RHD042 category with reported hysterectomy status.
    """
    print_section('STEP 6: MENOPAUSE VARIABLES')
    age_men = df['RHQ060']                       # already windowed to 20-70 by SPEC
    df['age_at_menopause'] = age_men
    ysm = df['RIDAGEYR'] - age_men
    df['years_since_menopause'] = ysm.where(ysm >= 0)
    df['hysterectomy'] = df['RHD280']
    df['oophorectomy'] = df['RHQ305']            # not collected in 2005_2006

    nat = pd.Series(np.nan, index=df.index, dtype=float)
    nat[df['RHD043'] == 'menopause'] = 1.0
    nat[df['RHD043'] == 'hysterectomy'] = 0.0
    ambiguous = df['RHD042'] == 'meno_or_hyst'
    nat[ambiguous & (df['hysterectomy'] == 0.0)] = 1.0
    nat[ambiguous & (df['hysterectomy'] == 1.0)] = 0.0
    df['menopause_natural'] = nat

    # Four-level type (Q4, option A). Surgical menopause with the ovaries removed is a
    # different exposure from a hysterectomy that left them in place: ovaries kept means
    # oestrogen continued, and in this cohort that group is 19.7 years post-menopause at
    # mean T -1.137 versus 9.0 years and -1.252 for natural menopause. Collapsing the two
    # would confound duration of oestrogen deficiency with the surgery itself.
    mtype = pd.Series('unknown', index=df.index, dtype=object)
    mtype[nat == 1.0] = 'natural'
    mtype[(nat == 0.0) & (df['oophorectomy'] == 1.0)] = 'surgical_oophorectomy'
    mtype[(nat == 0.0) & (df['oophorectomy'] == 0.0)] = 'hysterectomy_ovaries_kept'
    df['menopause_type'] = mtype

    print(f"  menopause_natural coverage {int(nat.notna().sum()):,} of {len(df):,} "
          f"(was 831 before the rebuild)")
    print("  menopause_type: " + "  ".join(
        f"{k}={v}" for k, v in df['menopause_type'].value_counts().items()))
    print(f"  years_since_menopause coverage {int(df['years_since_menopause'].notna().sum()):,}")
    print("  NOTE age = age_at_menopause + years_since_menopause exactly, so "
          "age_at_menopause is descriptive only and never enters the feature set.")
    return df


def compute_estrogen_variables(df):
    """Ever-use of oestrogen, and duration where any of the three routes recorded it."""
    ever = df['RHQ540']
    df['ever_used_estrogen'] = ever

    dur = pd.Series(np.nan, index=df.index, dtype=float)
    for qty, unit in [('RHQ560Q', 'RHQ560U'), ('RHQ576Q', 'RHQ576U'),
                      ('RHQ586Q', 'RHQ586U')]:
        v = pd.to_numeric(df.get(qty), errors='coerce')
        u = df.get(unit)
        if u is not None:
            v = pd.Series(np.where(u == 'months', v / 12.0, v), index=df.index)
        dur = dur.fillna(v)
    dur = dur.where(ever == 1.0)
    df['estrogen_years'] = dur

    # Four-level secondary exposure. 2 years is the conventional short/long split.
    lvl = pd.Series(np.nan, index=df.index, dtype=object)
    lvl[ever == 0.0] = 'never'
    lvl[(ever == 1.0) & dur.isna()] = 'ever_duration_unknown'
    lvl[(ever == 1.0) & (dur < 2)] = 'under_2y'
    lvl[(ever == 1.0) & (dur >= 2)] = 'two_years_or_more'
    df['estrogen_exposure'] = lvl

    n_ever = int((ever == 1.0).sum())
    n_dur = int(dur.notna().sum())
    print(f"  oestrogen ever-use {n_ever} / never {int((ever == 0.0).sum())} / "
          f"unknown {int(ever.isna().sum())}")
    print(f"  duration recorded for {n_dur} of {n_ever} ever-users "
          f"({n_dur / max(n_ever, 1):.0%}), median {dur.median():.1f} y. "
          f"2017_2020 records no duration quantity at all.")
    return df


def compute_derived_variables(df, supp, day2):
    """Everything else: PHQ-9, sleep, vitamin D, intake totals, fractures, comorbidity."""
    print_section('STEP 7: DERIVED VARIABLES')

    # PHQ-9. Previously computed by arithmetic straight over the label strings, which
    # produced NaN for five of six cycles and left the score 80% missing.
    phq_cols = [c for c in MODULE_COLS['DPQ'] if c in df.columns]
    df['phq9_score'] = df[phq_cols].sum(axis=1, min_count=5)
    df['phq9_ge10'] = (df['phq9_score'] >= 10).astype(float).where(
        df['phq9_score'].notna())
    print(f"  phq9_score coverage {int(df['phq9_score'].notna().sum()):,} of {len(df):,}"
          f"   median {df['phq9_score'].median():.0f}   mean {df['phq9_score'].mean():.2f}"
          f"   >= 10: {int((df['phq9_score'] >= 10).sum())} "
          f"({(df['phq9_score'] >= 10).mean():.1%})")

    # Sleep: SLD012 (2017-2020, half hours) coalesced with SLD010H (older, whole hours).
    df['sleep_hrs'] = df['SLD012'].fillna(df['SLD010H'])
    print(f"  sleep_hrs coverage {int(df['sleep_hrs'].notna().sum()):,}   "
          f"median {df['sleep_hrs'].median():.1f}")

    # Serum 25(OH)D before the crosswalk.
    serum = pd.Series(np.nan, index=df.index, dtype=float)
    for c in ('LBXVIDMS', 'LBDVIDMS'):
        if c in df.columns:
            serum = serum.fillna(df[c])
    df['serum_vitd_nmol'] = serum
    df = crosswalk_serum_vitd(df)

    # Dietary intake: mean of the available 24-hour recalls.
    if len(day2):
        d2 = day2.drop_duplicates('SEQN').set_index('SEQN')
        for src, dst in [('DR2TCALC', 'DR2TCALC'), ('DR2TVD', 'DR2TVD')]:
            df[dst] = df['SEQN'].map(d2[src]) if src in d2.columns else np.nan
    else:
        df['DR2TCALC'] = np.nan
        df['DR2TVD'] = np.nan
    diet_ca = df[['DR1TCALC', 'DR2TCALC']].mean(axis=1)
    diet_vd = df[['DR1TVD', 'DR2TVD']].mean(axis=1)
    df['n_recall_days'] = df[['DR1TCALC', 'DR2TCALC']].notna().sum(axis=1)

    # Supplements. NHANES codes a non-user as BLANK, not 0, so a NaN nutrient means
    # "reported no supplement" only for someone who appears in a DSQTOT file at all.
    # Absence from every file (the whole 2005_2006 cycle) means unobserved, and the
    # 0-fill is scoped accordingly — otherwise a missing cycle becomes 173 fake zeros.
    if len(supp):
        s = supp.drop_duplicates('SEQN').set_index('SEQN')
        observed = df['SEQN'].isin(s.index)
        df['supp_calcium_mg'] = df['SEQN'].map(s['DSQTCALC'])
        df['supp_vitd_mcg'] = df['SEQN'].map(s['DSQTVD'])
        df.loc[observed, ['supp_calcium_mg', 'supp_vitd_mcg']] = \
            df.loc[observed, ['supp_calcium_mg', 'supp_vitd_mcg']].fillna(0)
        df.loc[~observed, ['supp_calcium_mg', 'supp_vitd_mcg']] = np.nan
    else:
        observed = pd.Series(False, index=df.index)
        df['supp_calcium_mg'] = np.nan
        df['supp_vitd_mcg'] = np.nan
    df['supp_data_available'] = observed.astype(float)

    # Plain addition, so a missing component yields a missing total rather than a
    # fabricated one that silently treats "unobserved" as "none".
    df['total_calcium_mg'] = diet_ca + df['supp_calcium_mg']
    df['total_vitd_mcg'] = diet_vd + df['supp_vitd_mcg']
    print(f"  total_calcium_mg coverage {int(df['total_calcium_mg'].notna().sum()):,}   "
          f"total_vitd_mcg {int(df['total_vitd_mcg'].notna().sum()):,}")

    # Prior fracture. Hip (n=21) and wrist (n=46) are each too rare to model alone, so
    # the three sites are pooled; the site-specific columns stay out of the feature set.
    sites = df[['OSQ010A', 'OSQ010B', 'OSQ010C']]
    df['prior_hip_fracture'] = df['OSQ010A']
    df['prior_spine_fracture'] = df['OSQ010B']
    df['prior_wrist_fracture'] = df['OSQ010C']
    df['any_prior_fracture'] = np.where(
        (sites == 1).any(axis=1), 1.0,
        np.where(sites.notna().all(axis=1), 0.0, np.nan))

    # Family history (Q10): the ordinal parent count collapses to a binary because only
    # 5 women report two affected parents. Both features are kept; they are different
    # questions (any relative with osteoporosis vs a parent who fractured a hip).
    df['family_hx_osteoporosis'] = df['OSQ150']
    df['mother_hip_fracture'] = df['OSQ170']
    df['father_hip_fracture'] = df['OSQ200']
    par = df[['OSQ170', 'OSQ200']]
    df['parental_hip_fracture'] = np.where(
        (par == 1).any(axis=1), 1.0,
        np.where((par == 0).all(axis=1), 0.0, np.nan))

    # Rheumatoid arthritis (Q7). The type question is asked only of women who answered
    # yes to the arthritis gate, so an RA indicator is defined on a SUBSET, not the
    # cohort. Women who passed the gate but whose type is unknown cannot be scored
    # either way and are excluded from the RA arm rather than silently called non-RA.
    atype = pd.Series(np.nan, index=df.index, dtype=object)
    for c in ('MCQ190', 'MCQ191', 'MCQ195'):
        if c in df.columns:
            atype = atype.fillna(df[c])
    df['arthritis_type'] = atype
    df['any_arthritis'] = df['MCQ160A']
    gate_no = df['MCQ160A'] == 0.0
    df['rheumatoid_arthritis'] = np.where(
        atype == 'rheumatoid', 1.0, np.where(gate_no | atype.notna(), 0.0, np.nan))
    df['ra_arm_eligible'] = df['rheumatoid_arthritis'].notna().astype(float)

    # Diabetes (Q8). Borderline folds into non-diabetic for the primary definition; a
    # reclassification run moves it the other way. Diabetes stays a predictor and is
    # judged by ablation, with no EXPECTED_SIGNS entry: the diabetic bone paradox means
    # a HIGHER BMD alongside higher fracture risk, so a positive coefficient is the
    # expected finding here, not a sign error.
    df['diabetes'] = df['DIQ010'].replace({2.0: 0.0})
    df['diabetes_borderline_as_case'] = df['DIQ010'].replace({2.0: 1.0})

    df['ever_smoked'] = df['SMQ020']
    df['vigorous_activity'] = df['PAQ650']
    df['steroid_use'] = df['OSQ130']
    df['sedentary_min_day'] = df['PAD680']
    # Alcohol. Two different questions, and conflating them mislabels 62 women.
    #   ALQ101 (2005-2014) / ALQ111 (2017-2020): drank in the PAST 12 MONTHS.
    #   ALQ110: ever had 12+ drinks in a LIFETIME, asked only of those who said No above.
    # ALQ130 is average drinks per day over the past 12 months and is asked down both
    # branches, so a blank for a confirmed non-current-drinker is a true zero. Leaving it
    # missing would send those women through median imputation at 2 drinks a day, which
    # invents drinking in abstainers. The zero-fill therefore keys on CURRENT drinking,
    # while ever_drinker is a lifetime OR across all three items.
    current = pd.Series(np.nan, index=df.index, dtype=float)
    for c in ('ALQ101', 'ALQ111'):
        if c in df.columns:
            current = current.fillna(df[c])
    ever = current.copy()
    for c in ('ALQ110', 'ALQ111', 'ALQ101'):
        if c in df.columns:
            ever = np.fmax(ever, df[c])            # fmax ignores NaN: any Yes wins
    drinks = df['ALQ130'].copy()
    drinks = drinks.where(~((current == 0.0) & drinks.isna()), 0.0)
    df['current_drinker'] = current
    df['ever_drinker'] = ever
    df['alcohol_drinks_day'] = drinks
    print(f"  alcohol_drinks_day coverage {int(drinks.notna().sum()):,} "
          f"(non-drinkers set to 0, not imputed)")
    return df


RENAME = {'RIDAGEYR': 'age', 'INDFMPIR': 'poverty_income_ratio', 'DMDEDUC2': 'education',
          'BMXBMI': 'bmi', 'BMXWT': 'weight_kg', 'BMXHT': 'height_cm',
          'DR1TCALC': 'dietary_calcium_mg', 'DR1TVD': 'dietary_vitd_mcg'}


def rename_and_save(df):
    df = df.rename(columns=RENAME)
    # WTMEC2YR (2-year basis) and WTMECPRP (3.2-year basis) are NOT interchangeable, so
    # they stay in separate columns and are only ever used within a cycle.
    out = os.path.join(PROC_DIR, 'analysis_cohort_postmenopausal.csv')
    df.to_csv(out, index=False)
    print(f"  wrote {os.path.relpath(out, BASE_DIR)}  ({len(df):,} x {df.shape[1]})")
    return df

# ================================================================================
# BLOCK E — FEATURE ALLOWLIST, ANALYSIS COHORTS, POWER GATE, TABLE 1
# ================================================================================
#
# Feature selection is an ALLOWLIST, not an exclusion list. The previous pipeline took
# every column and removed a hand-maintained exclude list, which meant any newly derived
# column was included by default — so a column derived from BMD or the T-score leaked
# the target unless somebody remembered to add it. Here nothing enters the model unless
# it is named below, and a denylist assertion runs on top as a second gate.
#
# Groups, not columns, are the unit. A categorical variable expands to several indicator
# columns but is ONE variable clinically, so the ablation grid drops the whole group.

FEATURE_GROUPS = {
    'age':                    ['age'],
    'bmi':                    ['bmi'],
    'weight_kg':              ['weight_kg'],
    'years_since_menopause':  ['years_since_menopause'],
    # Reference level is natural menopause. Surgical menopause with the ovaries removed
    # is a different exposure from a hysterectomy that left them in place.
    'menopause_type':         ['meno_surgical_oophorectomy',
                               'meno_hysterectomy_ovaries_kept', 'meno_unknown'],
    'ever_used_estrogen':     ['ever_used_estrogen'],
    'diabetes':               ['diabetes'],
    'ever_smoked':            ['ever_smoked'],
    'alcohol_drinks_day':     ['alcohol_drinks_day'],
    'any_prior_fracture':     ['any_prior_fracture'],
    'steroid_use':            ['steroid_use'],
    'vigorous_activity':      ['vigorous_activity'],
    'sedentary_min_day':      ['sedentary_min_day'],
    'poverty_income_ratio':   ['poverty_income_ratio'],
    'parental_hip_fracture':  ['parental_hip_fracture'],
    'family_hx_osteoporosis': ['family_hx_osteoporosis'],
    'phq9_score':             ['phq9_score'],
    'sleep_hrs':              ['sleep_hrs'],
}

# Arm-specific additions. Vitamin D is never in the base set: intake and serum are
# measured on different subsets, so putting both in one model silently intersects them.
ARM_GROUPS = {
    'vitd_intake': {'total_calcium_mg': ['total_calcium_mg'],
                    'total_vitd_mcg':   ['total_vitd_mcg']},
    'vitd_serum':  {'serum_vitd_nmol':  ['serum_vitd_nmol']},
    'ra':          {'rheumatoid_arthritis': ['rheumatoid_arthritis']},
    'phq_binary':  {'phq9_ge10': ['phq9_ge10']},
}

# Anything computed from the DXA scan. Never a feature, under any arm. This is the
# structural guarantee that the model is not handed the thing it is predicting away.
BMD_DENYLIST = {
    'femoral_neck_bmd', 'total_hip_bmd', 'DXXNKBMD', 'DXXOFBMD',
    't_femoral_neck', 't_total_hip', 't_score', 'at_risk', 'osteoporosis', 'bone_status',
}


def encode_features(df):
    """Materialise every allowlisted column, including categorical indicators."""
    out = pd.DataFrame(index=df.index)
    for col in ['age', 'bmi', 'weight_kg', 'years_since_menopause',
                'ever_used_estrogen', 'diabetes', 'ever_smoked', 'alcohol_drinks_day',
                'any_prior_fracture', 'steroid_use', 'vigorous_activity',
                'sedentary_min_day', 'poverty_income_ratio', 'parental_hip_fracture',
                'family_hx_osteoporosis', 'phq9_score', 'sleep_hrs',
                'total_calcium_mg', 'total_vitd_mcg', 'serum_vitd_nmol',
                'rheumatoid_arthritis', 'phq9_ge10']:
        out[col] = pd.to_numeric(df[col], errors='coerce') if col in df.columns else np.nan
    mt = df['menopause_type']
    out['meno_surgical_oophorectomy'] = (mt == 'surgical_oophorectomy').astype(float)
    out['meno_hysterectomy_ovaries_kept'] = (mt == 'hysterectomy_ovaries_kept').astype(float)
    out['meno_unknown'] = (mt == 'unknown').astype(float)
    return out


def build_feature_matrix(encoded, groups):
    """Assemble X from an ordered group dict, with the leakage assertion."""
    cols = [c for g in groups.values() for c in g]
    bad = BMD_DENYLIST.intersection(cols)
    assert not bad, f"BMD-derived columns reached the feature set: {sorted(bad)}"
    return encoded[cols].copy()


def riley_gate(n_events, n_predictors, label):
    """Events per predictor, with an explicit underpowered verdict.

    Ten events per predictor is the conventional floor. Below it a model is not
    necessarily wrong, but the apparent performance is dominated by how the folds fell,
    and a difference against a comparator will not be separable from zero. Saying so up
    front is the point: it stops a collapsed nested estimate being read as a surprise.
    """
    epp = n_events / max(n_predictors, 1)
    ok = epp >= RILEY_MIN_EPP
    print(f"    {label:<44} events {n_events:>4}  predictors {n_predictors:>3}  "
          f"EPP {epp:>5.2f}  {'OK' if ok else 'UNDERPOWERED'}")
    return {'Cohort': label, 'Events': n_events, 'Predictors': n_predictors,
            'EPP': round(epp, 2), 'Powered': bool(ok)}


def build_cohorts(df, encoded):
    """The analysis cohorts. Each arm is a different set of women, never a merge.

    Serum 25(OH)D and dietary/supplement intake are measured on overlapping but
    different subsets. A model given both is silently fitted on the intersection, and
    its AUC is then not comparable with the base model on a different case mix. So each
    vitamin D exposure gets its own cohort and its own comparator, and the two are
    never cross-compared.
    """
    print_section('STEP 8: ANALYSIS COHORTS AND POWER GATE')
    base = FEATURE_GROUPS
    specs = {
        'C0 base': (base, []),
        'C1 + vitamin D intake': ({**base, **ARM_GROUPS['vitd_intake']},
                                  ['total_calcium_mg', 'total_vitd_mcg']),
        'C2 + serum 25(OH)D': ({**base, **ARM_GROUPS['vitd_serum']},
                               ['serum_vitd_nmol']),
        'C3 + both vitamin D': ({**base, **ARM_GROUPS['vitd_intake'],
                                 **ARM_GROUPS['vitd_serum']},
                                ['total_calcium_mg', 'total_vitd_mcg', 'serum_vitd_nmol']),
        'C4 + rheumatoid arthritis': ({**base, **ARM_GROUPS['ra']},
                                      ['rheumatoid_arthritis']),
    }
    cohorts, gate_rows = {}, []
    for name, (groups, required) in specs.items():
        mask = pd.Series(True, index=df.index)
        for c in required:
            mask &= encoded[c].notna()
        sub = df[mask]
        X = build_feature_matrix(encoded[mask], groups)
        cohorts[name] = {'X': X, 'df': sub, 'groups': groups}
        n1 = int(sub['at_risk'].sum())
        n2 = int(sub['osteoporosis'].sum())
        print(f"  {name:<28} n {len(sub):>5,}   T<=-1.0 {n1:>4}   T<=-2.5 {n2:>4}   "
              f"{X.shape[1]} columns / {len(groups)} variables")
        gate_rows.append(riley_gate(n2, X.shape[1], f"{name} @ T<=-2.5"))
        gate_rows.append(riley_gate(min(n1, len(sub) - n1), X.shape[1],
                                    f"{name} @ T<=-1.0"))
    print("\n  At T <= -1.0 the minority class is the NON-events, so that is what the")
    print("  events-per-predictor count uses. At T <= -2.5 every cohort is below the")
    print("  conventional floor of 10, which is stated here in advance rather than")
    print("  discovered afterwards when the nested estimate collapses.")
    save_csv(pd.DataFrame(gate_rows), 'power_gate.csv', 'METHODS')
    return cohorts


def table_one(df, X):
    """Descriptive table by bone status, the first thing a clinical reader asks for."""
    print_section('STEP 8b: TABLE 1 — COHORT DESCRIPTION BY BONE STATUS')
    rows = []
    groups = [('Normal (T > -1.0)', df['at_risk'] == 0),
              ('Low bone mass (-2.5 < T <= -1.0)',
               (df['at_risk'] == 1) & (df['osteoporosis'] == 0)),
              ('Osteoporosis (T <= -2.5)', df['osteoporosis'] == 1),
              ('All', pd.Series(True, index=df.index))]
    for col in X.columns:
        row = {'Variable': col, 'Missing %': round(100 * X[col].isna().mean(), 1)}
        binary = set(X[col].dropna().unique()) <= {0.0, 1.0}
        for label, mask in groups:
            v = X.loc[mask.to_numpy(), col].dropna()
            row[label] = (f"{v.mean():.1%}" if binary and len(v)
                          else (f"{v.mean():.1f} ({v.std():.1f})" if len(v) else "n/a"))
        rows.append(row)
    hdr = {'Variable': 'n', 'Missing %': ''}
    for label, mask in groups:
        hdr[label] = f"{int(mask.sum()):,}"
    table = pd.DataFrame([hdr] + rows)
    print(table.to_string(index=False))
    print("  Continuous variables as mean (SD); binary variables as percent positive.")
    save_csv(table, 'table_one.csv', 'PRESENT')
    return table

# ================================================================================
# BLOCK F — MODEL LAYER
# ================================================================================

from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.ensemble import (RandomForestClassifier, RandomForestRegressor)
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.metrics import brier_score_loss, confusion_matrix, roc_auc_score
from sklearn.model_selection import (StratifiedKFold, cross_val_predict,
                                     cross_validate)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import xgboost as xgb


def save_csv(df, filename, tier):
    """Write one result table to outputs/ and label who it is for.

    Every file carries a tier so the folder stays self-explanatory without a README
    that can drift out of sync with the code.
      PRESENT    - for the clinical audience.
      METHODS    - backs up a methodological choice if it is challenged.
      DIAGNOSTIC - a bug detector. Standardised units, unstable across collinear
                   predictors, therefore NOT findings and not to be shown as results.
    """
    assert tier in ('PRESENT', 'METHODS', 'DIAGNOSTIC'), tier
    path = os.path.join(OUT_DIR, filename)
    df.to_csv(path, index=False)
    print(f"  [{tier:10s}] {filename}")
    return path


def _pipe(model):
    """Imputation and scaling are learned INSIDE the training fold, never before it."""
    return Pipeline([('imputer', SimpleImputer(strategy='median')),
                     ('scaler', StandardScaler()), ('model', model)])


def make_random_forest(min_samples_leaf=None, oob=True):
    """Random forest with out-of-bag scoring enabled.

    OOB scores each row using only the ~37% of trees whose bootstrap sample excluded it,
    which is the honest in-sample number for a bagged ensemble. Plain in-sample AUC is
    near 1.0 for any deep forest — on shuffled labels this configuration still reaches
    0.997 — because ~63% of the trees have memorised each training row.
    """
    return RandomForestClassifier(
        n_estimators=500,
        min_samples_leaf=RF_MIN_SAMPLES_LEAF if min_samples_leaf is None else min_samples_leaf,
        class_weight='balanced', random_state=SEED, n_jobs=-1,
        bootstrap=True, oob_score=oob)


def get_model_dictionary(pos_weight):
    """Five classifiers on the binary label. Both boosters are aggressively
    regularised (max_depth 2, reg_lambda 50) because n ~ 1,100 overfits trivially."""
    return {
        'Logistic Regression (L2)': LogisticRegression(
            max_iter=1000, random_state=SEED, class_weight='balanced'),
        'Elastic Net Logistic Regression': LogisticRegression(
            penalty='elasticnet', solver='saga', l1_ratio=0.5, max_iter=2000,
            random_state=SEED, class_weight='balanced'),
        'Random Forest': make_random_forest(),
        'LightGBM (Aggressive Reg)': lgb.LGBMClassifier(
            n_estimators=150, max_depth=2, num_leaves=4, min_child_samples=50,
            reg_lambda=50.0, class_weight='balanced', random_state=SEED,
            verbose=-1, n_jobs=-1),
        'XGBoost (Aggressive Reg)': xgb.XGBClassifier(
            n_estimators=150, max_depth=2, min_child_weight=15, reg_lambda=50.0,
            scale_pos_weight=pos_weight, random_state=SEED, eval_metric='logloss',
            n_jobs=-1),
    }


def get_regressor_dictionary():
    """Continuous t_score models, which never see either binary label.

    Dichotomising a continuous measurement discards information: a woman at T = -2.4 and
    one at T = +0.5 are otherwise the same 'negative'. Regressing t_score keeps the
    gradient, and ONE fit serves BOTH clinical cutoffs — the predicted T-score is simply
    thresholded twice.
    """
    return {
        'Ridge -> t_score': RidgeCV(alphas=np.logspace(-3, 3, 13)),
        'RF -> t_score': RandomForestRegressor(n_estimators=500, min_samples_leaf=5,
                                               random_state=SEED, n_jobs=-1),
        'LightGBM -> t_score': lgb.LGBMRegressor(n_estimators=150, max_depth=2,
                                                 num_leaves=4, min_child_samples=50,
                                                 reg_lambda=50.0, random_state=SEED,
                                                 verbose=-1, n_jobs=-1),
    }


def compute_baselines(df):
    """Non-ML comparators, oriented so a HIGHER score means HIGHER risk.

    OST = 0.2 x (weight_kg - age) is a validated two-input screening formula needing
    only a scale and a birthdate. It is the bar any model here has to clear: an AUC
    reported without it is uninterpretable.
    """
    w = pd.to_numeric(df['weight_kg'], errors='coerce')
    a = pd.to_numeric(df['age'], errors='coerce')
    ost = 0.2 * (w - a)
    return {'OST  0.2x(weight-age)': -ost.fillna(ost.median()).to_numpy(),
            'Weight alone': -w.fillna(w.median()).to_numpy()}


def bootstrap_delta_auc(y, s_model, s_ref, n_boot=1000, seed=SEED):
    """Paired stratified bootstrap of AUC(model) - AUC(reference).

    Resampling cases and non-cases separately holds prevalence fixed across replicates.
    Both scores are evaluated on the same resampled rows, so the difference is paired.
    """
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    a = np.asarray(s_model, dtype=float)
    b = np.asarray(s_ref, dtype=float)
    pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    d = np.empty(n_boot)
    for i in range(n_boot):
        ix = np.concatenate([rng.choice(pos, pos.size, replace=True),
                             rng.choice(neg, neg.size, replace=True)])
        d[i] = roc_auc_score(y[ix], a[ix]) - roc_auc_score(y[ix], b[ix])
    return d.mean(), np.percentile(d, 2.5), np.percentile(d, 97.5), float((d <= 0).mean())


def holm(pvals):
    """Holm-Bonferroni adjusted p-values, order preserved."""
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    order = np.argsort(p)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def oof_scores(X, y, t_score, folds):
    """Out-of-fold scores for every classifier and regressor, on one fold structure."""
    y = np.asarray(y)
    pw = (y == 0).sum() / max((y == 1).sum(), 1)
    out = {}
    for name, model in get_model_dictionary(pw).items():
        out[name] = cross_val_predict(_pipe(model), X, y, cv=folds,
                                      method='predict_proba')[:, 1]
    for name, reg in get_regressor_dictionary().items():
        out[name] = -cross_val_predict(_pipe(reg), X, t_score, cv=folds)
    return out


# --- leaderboard -------------------------------------------------------------------

MIN_OOB_COVERAGE = 0.80


def _oob_auc(est, y, min_coverage=MIN_OOB_COVERAGE):
    """Out-of-bag AUC, or a refusal to report one, with the reason.

    scikit-learn >= 1.9 makes the bootstrap draw sample_weight-aware, and
    class_weight='balanced' is applied as a sample weight. On an imbalanced target the
    minority class is therefore oversampled into nearly every bootstrap, so most of its
    rows are never out-of-bag. Measured here: at T <= -2.5 only 27.6% of cases get an
    OOB estimate, against 100% of non-cases.

    sklearn returns those rows as an all-ZERO decision-function row rather than NaN, so
    an isnan guard silently keeps them and scores every uncovered case at 0.0 — the
    lowest possible rank. That produced an OOB AUC of 0.108 for the osteoporosis target:
    not a weak model but an inverted one, and it would have been printed in a
    PRESENT-tier leaderboard. Drop the uncovered rows, and if either class loses more
    than min_coverage of its rows the survivors are a biased subset, so report nothing.
    """
    odf = est.oob_decision_function_
    ok = (np.nansum(odf, axis=1) > 0) & ~np.isnan(odf).any(axis=1)
    y = np.asarray(y)
    cov = {c: ok[y == c].mean() for c in np.unique(y)}
    worst = min(cov.values())
    if worst < min_coverage:
        lo = min(cov, key=cov.get)
        return np.nan, (f'withheld: only {worst:.0%} of class {lo} rows are ever '
                        f'out-of-bag (class_weight oversamples them)')
    if ok.sum() == 0 or len(np.unique(y[ok])) < 2:
        return np.nan, 'withheld: no usable out-of-bag rows'
    return roc_auc_score(y[ok], odf[ok, 1]), f'coverage {worst:.0%}'


def run_model(pipe, X, y, cv):
    res = cross_validate(pipe, X, y, cv=cv, scoring=['roc_auc', 'recall', 'precision', 'f1'],
                         return_train_score=True)
    y_pred = cross_val_predict(pipe, X, y, cv=cv)
    tn, fp, fn, tp = confusion_matrix(y, y_pred).ravel()
    pipe.fit(X, y)
    oob_auc, oob_note = np.nan, 'n/a (not a bagged ensemble)'
    est = pipe.named_steps['model']
    if hasattr(est, 'oob_decision_function_'):
        oob_auc, oob_note = _oob_auc(est, y)
    return {'auc': res['test_roc_auc'].mean(), 'train_auc': res['train_roc_auc'].mean(),
            'oob_auc': oob_auc, 'oob_note': oob_note,
            'sens': tp / (tp + fn), 'spec': tn / (tn + fp),
            'tn': tn, 'fp': fp, 'fn': fn, 'tp': tp}


def train_models(X, y, label):
    print_section(f'STEP 9: MODEL LEADERBOARD — {label}')
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    pw = (np.asarray(y) == 0).sum() / max((np.asarray(y) == 1).sum(), 1)
    rows = []
    for name, model in get_model_dictionary(pw).items():
        m = run_model(_pipe(model), X, y, cv)
        m['Model'] = name
        rows.append(m)
        oob = (f" | OOB {m['oob_auc']:.3f}" if not np.isnan(m['oob_auc'])
               else (f" | OOB {m['oob_note']}" if m['oob_note'].startswith('withheld')
                     else ""))
        print(f"  {name:<34} test {m['auc']:.3f}  train {m['train_auc']:.3f}{oob}")
    print("  Train AUC is in-sample and inflated by design for the bagged forest, so OOB")
    print("  is its honest in-sample figure. Do NOT rank models by the train/test gap.")
    return pd.DataFrame(rows)


# --- importance --------------------------------------------------------------------

def permutation_importance_cv(model, X, y, n_repeats=5, seed=SEED):
    """Permutation importance as mean AUC lost, measured OUT OF FOLD.

    Model-agnostic and in the same units for every model, so unlike Gini importance or
    split counts it is comparable across model families and is not biased toward
    continuous features over binary ones. Tree importances were deliberately removed
    from reporting: here they inverted the real ranking.
    """
    y_arr = np.asarray(y)
    folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=seed).split(X, y_arr))
    acc = np.zeros(X.shape[1])
    for tr, te in folds:
        pipe = _pipe(clone(model))
        pipe.fit(X.iloc[tr], y_arr[tr])
        r = permutation_importance(pipe, X.iloc[te], y_arr[te], scoring='roc_auc',
                                   n_repeats=n_repeats, random_state=seed, n_jobs=1)
        acc += r.importances_mean
    return acc / len(folds)


def _clinical_increment(X, feature):
    if feature in CLINICAL_UNITS:
        return CLINICAL_UNITS[feature]
    v = X[feature].dropna()
    if set(v.unique()) <= {0.0, 1.0}:
        return 1, 'yes vs no'
    return 1, 'per 1 unit'


def bootstrap_odds_ratios(X, y, n_boot=500, seed=SEED):
    """Adjusted ORs per clinically meaningful unit, with stratified-bootstrap CIs."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    incs = np.array([_clinical_increment(X, f)[0] for f in X.columns], dtype=float)
    pw = (y == 0).sum() / max((y == 1).sum(), 1)
    base = _pipe(get_model_dictionary(pw)['Logistic Regression (L2)'])
    pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    draws = np.empty((n_boot, X.shape[1]))
    for i in range(n_boot):
        ix = np.concatenate([rng.choice(pos, pos.size, replace=True),
                             rng.choice(neg, neg.size, replace=True)])
        p = clone(base).fit(X.iloc[ix], y[ix])
        draws[i] = (p.named_steps['model'].coef_[0] / p.named_steps['scaler'].scale_) * incs
    pipe = clone(base).fit(X, y)
    point = (pipe.named_steps['model'].coef_[0] / pipe.named_steps['scaler'].scale_) * incs
    return (np.exp(point), np.exp(np.percentile(draws, 2.5, axis=0)),
            np.exp(np.percentile(draws, 97.5, axis=0)))


def clinical_table(X, y, target_label, filename='clinical_predictor_table.csv'):
    print_section(f'STEP 10: CLINICAL PREDICTOR TABLE — {target_label}')
    print('  Adjusted odds ratios from penalised logistic regression, per clinically')
    print('  meaningful unit, with stratified-bootstrap 95% CIs. Permutation importance')
    print('  is mean AUC lost when the predictor is shuffled, measured out of fold.\n')
    or_pt, or_lo, or_hi = bootstrap_odds_ratios(X, y)
    pw = (np.asarray(y) == 0).sum() / max((np.asarray(y) == 1).sum(), 1)
    perm_lr = permutation_importance_cv(
        get_model_dictionary(pw)['Logistic Regression (L2)'], X, y)
    perm_rf = permutation_importance_cv(make_random_forest(oob=False), X, y)
    rows = []
    for i, f in enumerate(X.columns):
        _, unit = _clinical_increment(X, f)
        signif = not (or_lo[i] <= 1.0 <= or_hi[i])
        rows.append({'Predictor': f, 'Unit': unit, 'OR': or_pt[i],
                     '95% CI': f"({or_lo[i]:.2f}-{or_hi[i]:.2f})",
                     'Direction': ('risk' if or_pt[i] > 1 else 'protective') if signif else 'ns',
                     'dAUC (LR)': perm_lr[i], 'dAUC (RF)': perm_rf[i],
                     'Missing %': 100 * X[f].isna().mean()})
    table = pd.DataFrame(rows).sort_values('dAUC (RF)', ascending=False)
    print(table.to_string(index=False, formatters={
        'OR': '{:.2f}'.format, 'dAUC (LR)': '{:+.4f}'.format,
        'dAUC (RF)': '{:+.4f}'.format, 'Missing %': '{:.1f}'.format}))
    n_sig = int((table['Direction'] != 'ns').sum())
    print(f"\n  {n_sig} of {len(table)} predictors have a 95% CI excluding OR = 1.")
    print("  'ns' means the interval includes 1; do not interpret the point estimate.")
    save_csv(table, filename, 'PRESENT')
    return table


def plot_forest(table, target_label, filename='forest_plot_odds_ratios.png'):
    d = table.copy()
    d[['lo', 'hi']] = d['95% CI'].str.strip('()').str.split('-', expand=True).astype(float)
    d = d.sort_values('OR')
    fig, ax = plt.subplots(figsize=(9, 0.34 * len(d) + 1.6))
    ypos = np.arange(len(d))
    sig = d['Direction'] != 'ns'
    ax.hlines(ypos, d['lo'], d['hi'], color=np.where(sig, '#1f4e79', '#b0b0b0'), lw=2)
    ax.scatter(d['OR'], ypos, s=34, color=np.where(sig, '#1f4e79', '#b0b0b0'), zorder=3)
    ax.axvline(1.0, color='#c0392b', ls='--', lw=1)
    ax.set_yticks(ypos)
    ax.set_yticklabels([f"{r.Predictor}  ({r.Unit})" for r in d.itertuples()], fontsize=8)
    ax.set_xscale('log')
    ax.set_xlabel('Adjusted odds ratio (log scale)')
    ax.set_title(f'Adjusted odds ratios — {target_label}\nsolid = 95% CI excludes 1', fontsize=10)
    ax.grid(axis='x', alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, filename), dpi=150)
    plt.close(fig)
    print(f"  [PRESENT   ] {filename}")


def ablation_grid(X, y, t_score, groups, label):
    """Drop one variable at a time and measure what the model loses.

    Permutation importance shuffles a column inside a model that was TRAINED with it,
    so a variable with a close substitute looks unimportant even when the pair matters.
    Ablation refits without the variable entirely, which is the question a clinician is
    actually asking: if this were not collected, would the model be worse? The two
    disagree exactly where collinearity lives, and both are reported.

    No multiplicity correction is applied to the per-model columns. Holm-adjusted
    p-values are given for the primary model only, and the grid is exploratory: with
    18 variables the smallest few deltas are not distinguishable from noise.
    """
    print_section(f'STEP 11: VARIABLE ABLATION GRID — {label}')
    y = np.asarray(y)
    folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED).split(X, y))
    full = oof_scores(X, y, t_score, folds)
    full_auc = {k: roc_auc_score(y, v) for k, v in full.items()}
    primary = max(full_auc, key=full_auc.get)
    # Two models share a first word (LightGBM classifier vs LightGBM regressor, and
    # likewise the forests), so tag the t_score regressors explicitly.
    def short(k):
        return (k.split(' ->')[0] + '->T') if '->' in k else k.split()[0]
    print("  full-model AUCs: " + "   ".join(f"{short(k)} {v:.3f}"
                                             for k, v in full_auc.items()))
    print(f"  primary model for the CI column: {primary} (AUC {full_auc[primary]:.3f})\n")

    rows, pvals = [], []
    for gname, cols in groups.items():
        keep = [c for c in X.columns if c not in cols]
        red = oof_scores(X[keep], y, t_score, folds)
        row = {'Variable': gname, 'Columns dropped': len(cols)}
        for m in full_auc:
            row[f'dAUC {m}'] = full_auc[m] - roc_auc_score(y, red[m])
        d, lo, hi, p_le = bootstrap_delta_auc(y, full[primary], red[primary], n_boot=500)
        row['dAUC primary'] = d
        row['95% CI'] = f"[{lo:+.3f}, {hi:+.3f}]"
        row['p (one-sided)'] = p_le
        row['mean dAUC across models'] = np.mean([row[f'dAUC {m}'] for m in full_auc])
        rows.append(row)
        pvals.append(p_le)
        print(f"  {gname:<24} dAUC(primary) {d:+.4f}  [{lo:+.3f}, {hi:+.3f}]  "
              f"mean across models {row['mean dAUC across models']:+.4f}")

    table = pd.DataFrame(rows)
    table['p (Holm)'] = holm(pvals)
    table = table.sort_values('mean dAUC across models', ascending=False)
    table.insert(0, 'Rank', range(1, len(table) + 1))
    print(f"\n  Positive dAUC = the model is WORSE without the variable, i.e. it carries")
    print(f"  signal the rest of the panel does not. Primary model: {primary}.")
    save_csv(table, f'model_variable_ablation_{label}.csv', 'PRESENT')
    return table, primary


def block_ablation(X, y, t_score, groups, label):
    """Joint ablations, because single-variable ablation cannot see a collinear pair.

    Dropping bmi alone costs nothing when weight_kg is still there to carry adiposity,
    and vice versa — so a one-at-a-time grid scores both near zero and hides the fact
    that body size is the dominant signal. These drop whole blocks, and the last two
    rows ask the question the single-variable grid provokes: does the full panel add
    anything at all to the two inputs OST already uses?
    """
    print_section(f'STEP 11b: BLOCK AND RESTRICTED-PANEL ABLATION — {label}')
    y = np.asarray(y)
    folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED).split(X, y))
    full = oof_scores(X, y, t_score, folds)
    full_auc = {k: roc_auc_score(y, v) for k, v in full.items()}
    primary = max(full_auc, key=full_auc.get)

    tests = [
        ('drop body size (bmi + weight_kg)', 'drop', ['bmi', 'weight_kg']),
        ('drop all menopause/hormone vars', 'drop',
         ['years_since_menopause', 'menopause_type', 'ever_used_estrogen']),
        ('drop all lifestyle vars', 'drop',
         ['ever_smoked', 'alcohol_drinks_day', 'vigorous_activity', 'sedentary_min_day']),
        ('drop all history/family vars', 'drop',
         ['any_prior_fracture', 'steroid_use', 'parental_hip_fracture',
          'family_hx_osteoporosis']),
        ('KEEP only age + weight (OST inputs)', 'keep', ['age', 'weight_kg']),
        ('KEEP only age + bmi', 'keep', ['age', 'bmi']),
    ]
    rows = []
    for name, mode, gs in tests:
        sel = ({g: c for g, c in groups.items() if g not in gs} if mode == 'drop'
               else {g: groups[g] for g in gs})
        Xr = X[[c for cols in sel.values() for c in cols]]
        red = oof_scores(Xr, y, t_score, folds)
        d, lo, hi, p = bootstrap_delta_auc(y, full[primary], red[primary], n_boot=500)
        rows.append({'Test': name, 'Variables in model': len(sel),
                     'Full panel AUC': round(full_auc[primary], 3),
                     'Reduced AUC': round(roc_auc_score(y, red[primary]), 3),
                     'Delta AUC': round(d, 3), '95% CI': f"[{lo:+.3f}, {hi:+.3f}]",
                     'p (one-sided)': round(p, 4), 'Primary model': primary,
                     'Full panel better': bool(lo > 0)})
        print(f"  {name:<38} {len(sel):>2} vars  AUC {rows[-1]['Reduced AUC']:.3f}   "
              f"delta {d:+.3f} [{lo:+.3f}, {hi:+.3f}]   "
              f"{'full panel wins' if lo > 0 else 'no detectable difference'}")

    ost_row = next(r for r in rows if r['Test'].startswith('KEEP only age + weight'))
    if not ost_row['Full panel better']:
        print()
        print("  The full 18-variable panel is NOT distinguishable from a two-variable")
        print("  model on age and weight. That is the same conclusion the OST comparison")
        print("  reaches, arrived at independently, and it is the finding — not a")
        print("  shortfall to be tuned away.")
    save_csv(pd.DataFrame(rows), f'model_block_ablation_{label}.csv', 'PRESENT')
    return pd.DataFrame(rows)


# --- nested CV ----------------------------------------------------------------------

def rank_within_folds(score, folds, n):
    """Map scores to within-fold percentile ranks.

    Different outer folds can select different winners, and a classifier probability
    (0-1) is not on the same scale as a regressor negated T-score (about -1 to 4).
    Pooling raw values corrupts the global ranking. AUC uses order only, so ranking
    within fold makes folds commensurable without changing any within-fold comparison.
    """
    out = np.empty(n, dtype=float)
    s = np.asarray(score, dtype=float)
    for _, te in folds:
        out[te] = pd.Series(s[te]).rank(pct=True).to_numpy()
    return out


def nested_cv_selection(X, y, t_score, n_outer=5, n_inner=3, seed=SEED):
    """Unbiased evaluation of the whole 'fit eight models, keep the best' procedure.

    Picking the winner on the same rows that score it is optimistic: the leaderboard
    best is an upper bound, not an estimate. Here model choice happens strictly inside
    each outer TRAINING fold, and the winner is scored on the untouched outer test fold.
    Candidates span both arms, so the inner CV also decides which arm wins per fold.
    """
    y = np.asarray(y)
    t_score = np.asarray(t_score)
    outer = list(StratifiedKFold(n_splits=n_outer, shuffle=True,
                                 random_state=seed).split(X, y))
    oof = np.zeros(len(y), dtype=float)
    chosen = []
    for tr, te in outer:
        X_tr, y_tr, t_tr = X.iloc[tr], y[tr], t_score[tr]
        pw = (y_tr == 0).sum() / max((y_tr == 1).sum(), 1)
        inner = list(StratifiedKFold(n_splits=n_inner, shuffle=True,
                                     random_state=seed).split(X_tr, y_tr))
        best = (None, -np.inf, None, None)
        for name, model in get_model_dictionary(pw).items():
            p = cross_val_predict(_pipe(model), X_tr, y_tr, cv=inner,
                                  method='predict_proba')[:, 1]
            a = roc_auc_score(y_tr, p)
            if a > best[1]:
                best = (name, a, model, 'clf')
        for name, reg in get_regressor_dictionary().items():
            p = -cross_val_predict(_pipe(reg), X_tr, t_tr, cv=inner)
            a = roc_auc_score(y_tr, p)
            if a > best[1]:
                best = (name, a, reg, 'reg')
        pipe = _pipe(best[2])
        if best[3] == 'clf':
            pipe.fit(X_tr, y_tr)
            oof[te] = pipe.predict_proba(X.iloc[te])[:, 1]
        else:
            pipe.fit(X_tr, t_tr)
            oof[te] = -pipe.predict(X.iloc[te])
        chosen.append(best[0])
    return oof, chosen, outer


# --- calibration (the figure that was missing) ---------------------------------------

def calibration_figure(X, y, label, filename='calibration_curve.png'):
    """Reliability curve for the calibrated forest, plus its Brier score.

    Step 13 thresholds probabilities to decide who gets a DXA referral, which is only
    meaningful if a predicted 0.30 really means about 30%. Discrimination (AUC) says
    nothing about that. This figure was the one known reporting gap: the only
    calibration plotting code left the repo with SF_new1.py.
    """
    y = np.asarray(y)
    folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED).split(X, y))
    cal = CalibratedClassifierCV(_pipe(make_random_forest(oob=False)),
                                 method='sigmoid', cv=3)
    p_cal = cross_val_predict(cal, X, y, cv=folds, method='predict_proba')[:, 1]
    p_raw = cross_val_predict(_pipe(make_random_forest(oob=False)), X, y, cv=folds,
                              method='predict_proba')[:, 1]
    fig, ax = plt.subplots(figsize=(5.6, 5.4))
    ax.plot([0, 1], [0, 1], ls='--', lw=1, color='#888', label='perfect calibration')
    for p, name, colour in [(p_raw, 'Random forest (uncalibrated)', '#9a3412'),
                            (p_cal, 'Random forest (sigmoid-calibrated)', '#0e6b78')]:
        frac, mean_pred = calibration_curve(y, p, n_bins=10, strategy='quantile')
        ax.plot(mean_pred, frac, 'o-', color=colour, lw=1.8, ms=5,
                label=f"{name}  Brier {brier_score_loss(y, p):.3f}  "
                      f"AUC {roc_auc_score(y, p):.3f}")
    ax.set_xlabel('Mean predicted probability (out of fold)')
    ax.set_ylabel('Observed fraction of cases')
    ax.set_title(f'Calibration — {label}', fontsize=10)
    ax.legend(fontsize=7, loc='upper left')
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, filename), dpi=150)
    plt.close(fig)
    print(f"  [PRESENT   ] {filename}   calibrated Brier "
          f"{brier_score_loss(y, p_cal):.3f} vs raw {brier_score_loss(y, p_raw):.3f}")
    return p_cal


def referral_table(y, score, cutoffs=(0.50, 0.40, 0.35, 0.30, 0.25), as_quantile=False):
    """Screening cost in the unit a clinician decides on: DXA scans per case found."""
    y = np.asarray(y)
    P, N = int(y.sum()), len(y)
    rows = []
    for c in cutoffs:
        thr = np.quantile(score, 1 - c) if as_quantile else c
        pred = (score >= thr).astype(int)
        tp = int(((pred == 1) & (y == 1)).sum())
        flagged = int(pred.sum())
        rows.append({'Cutoff': f"{c:.2f}", 'Sensitivity': f"{tp / P:.1%}" if P else 'n/a',
                     'DXAs ordered': flagged, 'Cases found': tp, 'Missed': P - tp,
                     'PPV': f"{tp / flagged:.1%}" if flagged else 'n/a',
                     'Scans per case': f"{flagged / tp:.2f}" if tp else 'inf'})
    rows.append({'Cutoff': 'scan all', 'Sensitivity': '100.0%', 'DXAs ordered': N,
                 'Cases found': P, 'Missed': 0, 'PPV': f"{P / N:.1%}",
                 'Scans per case': f"{N / P:.2f}" if P else 'inf'})
    return pd.DataFrame(rows)

# ================================================================================
# BLOCK G — DIAGNOSTICS, HEADLINE EVALUATION, PRESPECIFIED ARMS, MAIN
# ================================================================================

def coefficient_diagnostics(X, y, label, filename='coefficient_diagnostics.csv'):
    """A leak detector and a sign-error detector. NOT a findings table.

    These are standardised coefficients from one unpenalised-in-spirit logistic fit.
    They are unstable across collinear predictors — bmi and weight_kg will trade
    magnitude run to run — so they must never be read as effect sizes. Two alarms:

      LEAK   any |coefficient| above LEAK_COEF_THRESHOLD is implausible for a survey
             predictor and usually means a BMD-derived column reached the feature set.
      SIGN   EXPECTED_SIGNS holds the direction each predictor must take if the data
             are wired up correctly. A flip is either a coding error or a real finding,
             and the table says which ones flipped so the question gets asked.
    """
    print_section(f'DIAGNOSTIC: COEFFICIENT SANITY CHECK — {label}')
    y = np.asarray(y)
    pw = (y == 0).sum() / max((y == 1).sum(), 1)
    pipe = _pipe(get_model_dictionary(pw)['Logistic Regression (L2)']).fit(X, y)
    coef = pipe.named_steps['model'].coef_[0]
    rows = []
    for f, c in zip(X.columns, coef):
        exp = EXPECTED_SIGNS.get(f)
        flag = []
        if abs(c) > LEAK_COEF_THRESHOLD:
            flag.append('LEAK?')
        if exp is not None and np.sign(c) != exp and abs(c) > 0.05:
            flag.append('SIGN')
        rows.append({'Predictor': f, 'Std coef': round(float(c), 4),
                     'Expected sign': {1: '+', -1: '-'}.get(exp, 'n/a'),
                     'Observed sign': '+' if c > 0 else '-',
                     'Flag': ' '.join(flag) or 'ok'})
    table = pd.DataFrame(rows).sort_values('Std coef', key=np.abs, ascending=False)
    print(table.to_string(index=False))
    leaks = table[table['Flag'].str.contains('LEAK')]
    signs = table[table['Flag'].str.contains('SIGN')]
    if len(leaks):
        print(f"\n  !! {len(leaks)} coefficient(s) exceed |{LEAK_COEF_THRESHOLD}| — check "
              "for a BMD-derived column in the feature set.")
    else:
        print(f"\n  No coefficient exceeds |{LEAK_COEF_THRESHOLD}|. No leak signature.")
    if len(signs):
        print(f"  {len(signs)} predictor(s) point the wrong way: "
              f"{', '.join(signs['Predictor'])}.")
        # A flip is either reverse causation, or one half of a collinear pair where the
        # partner absorbed the effect. Name the partner so the reader is not left to
        # guess which: a residual sign on the weaker member of a correlated pair carries
        # no clinical meaning at all.
        corr = X.corr().abs()
        for f in signs['Predictor']:
            other = corr[f].drop(f).idxmax()
            r = corr.loc[f, other]
            partner = table.loc[table['Predictor'] == other, 'Std coef'].iloc[0]
            note = ('partner absorbed the effect, so this is a residual with no '
                    'clinical reading' if r > 0.5 and abs(partner) > abs(
                        table.loc[table['Predictor'] == f, 'Std coef'].iloc[0])
                    else 'not explained by collinearity — investigate or report it')
            print(f"    {f:<22} strongest partner {other} (|r| {r:.2f}, "
                  f"coef {partner:+.3f}): {note}")
        print("  State the ones that survive this rather than hide them — a backwards")
        print("  vitamin D coefficient is reverse causation (low intake prompts")
        print("  supplementation), not a bug.")
    print("  This table is DIAGNOSTIC. Do not present it as a result.")
    save_csv(table, filename, 'DIAGNOSTIC')
    return table


def tune_rf_leaf_nested(X, y, seed=SEED):
    """Choose min_samples_leaf inside each outer training fold, never on the test fold."""
    y = np.asarray(y)
    outer = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=seed).split(X, y))
    rows, picks = [], []
    for leaf in RF_LEAF_GRID:
        aucs = []
        for tr, te in outer:
            pipe = _pipe(make_random_forest(min_samples_leaf=leaf, oob=False))
            pipe.fit(X.iloc[tr], y[tr])
            aucs.append(roc_auc_score(y[te], pipe.predict_proba(X.iloc[te])[:, 1]))
        rows.append({'min_samples_leaf': leaf, 'Test AUC': np.mean(aucs),
                     'SD across folds': np.std(aucs)})
    for tr, te in outer:
        inner = list(StratifiedKFold(n_splits=3, shuffle=True,
                                     random_state=seed).split(X.iloc[tr], y[tr]))
        best, best_a = None, -np.inf
        for leaf in RF_LEAF_GRID:
            p = cross_val_predict(_pipe(make_random_forest(min_samples_leaf=leaf, oob=False)),
                                  X.iloc[tr], y[tr], cv=inner, method='predict_proba')[:, 1]
            a = roc_auc_score(y[tr], p)
            if a > best_a:
                best, best_a = leaf, a
        picks.append(best)
    return pd.DataFrame(rows), picks


def report_rf_tuning(X, y, label):
    """Evidence that RF_MIN_SAMPLES_LEAF was measured, not assumed.

    The forest's train/test gap is large and the reflex is to regularise it away by
    growing shallower leaves. That reflex is wrong here: raising min_samples_leaf lowers
    TEST AUC monotonically. The gap is the price of the performance, not a defect.
    """
    print_section(f'METHODS: RANDOM FOREST LEAF TUNING — {label}')
    table, picks = tune_rf_leaf_nested(X, y)
    print(table.to_string(index=False, formatters={'Test AUC': '{:.4f}'.format,
                                                   'SD across folds': '{:.4f}'.format}))
    print(f"\n  min_samples_leaf chosen by inner CV per outer fold: {picks}")
    print(f"  shipped value: RF_MIN_SAMPLES_LEAF = {RF_MIN_SAMPLES_LEAF}")
    best = table.loc[table['Test AUC'].idxmax(), 'min_samples_leaf']
    print(f"  best on the grid: {best}. Test AUC falls from "
          f"{table['Test AUC'].iloc[0]:.3f} to {table['Test AUC'].iloc[-1]:.3f} across "
          "the grid, so shrinking the gap costs real discrimination.")
    save_csv(table, 'rf_leaf_tuning.csv', 'METHODS')
    return table


def evaluate_target(X, df, target, target_label, n_events, tag):
    """The headline evaluation for one clinical cutoff.

    Reports the leaderboard (biased upward by design), the nested estimate (the
    defensible one), and the gap between them, all against OST. Fitting eight models and
    quoting the best is selection on the test fold; the nested figure moves that choice
    inside each outer training fold so no test row helps pick the model scored on it.
    When the two diverge, the divergence IS the finding.
    """
    y = df[target].to_numpy()
    t = df['t_score'].to_numpy()

    lb = train_models(X, y, target_label)
    lb.insert(0, 'Target', target_label)
    save_csv(lb, f'model_leaderboard_{tag}.csv', 'PRESENT')
    best_lb = lb.loc[lb['auc'].idxmax()]

    print_section(f'STEP 12: NESTED CROSS-VALIDATION — {target_label}')
    oof, chosen, outer = nested_cv_selection(X, y, t)
    oof_r = rank_within_folds(oof, outer, len(y))
    nested_auc = roc_auc_score(y, oof_r)
    print(f"  model chosen per outer fold: {chosen}")
    print(f"  leaderboard best  {best_lb['Model']}  AUC {best_lb['auc']:.3f}")
    print(f"  nested estimate                    AUC {nested_auc:.3f}   "
          f"(optimism {best_lb['auc'] - nested_auc:+.3f})")

    base = compute_baselines(df)
    rows = []
    for ref_name, ref in base.items():
        ref_auc = roc_auc_score(y, ref)
        d, lo, hi, p = bootstrap_delta_auc(y, oof_r, ref)
        beats = lo > 0
        rows.append({'Target': target_label, 'Events': int(n_events),
                     'Comparator': ref_name, 'Comparator AUC': round(ref_auc, 3),
                     'Leaderboard AUC': round(float(best_lb['auc']), 3),
                     'Nested AUC': round(nested_auc, 3),
                     'Optimism': round(float(best_lb['auc']) - nested_auc, 3),
                     'Delta vs comparator': round(d, 3),
                     '95% CI': f"[{lo:+.3f}, {hi:+.3f}]",
                     'p (one-sided)': round(p, 4),
                     'Verdict': 'Beats comparator' if beats else 'Not separable'})
        print(f"  vs {ref_name:<24} {ref_auc:.3f}   delta {d:+.3f} "
              f"[{lo:+.3f}, {hi:+.3f}]   {'BEATS' if beats else 'not separable'}")

    verdict = pd.DataFrame(rows)
    ost = verdict[verdict['Comparator'].str.startswith('OST')].iloc[0]
    if ost['Verdict'] == 'Not separable':
        print(f"\n  The advantage over OST spans zero at {n_events} events. Report this as")
        print(f"  not separable. Do NOT quote the leaderboard figure "
              f"({best_lb['auc']:.3f}) as a result for this target.")
    return verdict, oof_r, chosen


def compare_arm(df, encoded, base_groups, arm_name, arm_groups, target, label):
    """One prespecified arm, evaluated on ITS OWN rows against ITS OWN base model.

    An arm variable is measured on a subset, so the honest question is not 'does the
    augmented model beat the full-cohort base model' — that compares two different case
    mixes. It is 'on exactly these women, does adding this variable help'. Both models
    are therefore refit on the arm's complete-case rows and compared pairwise.
    """
    cols = [c for g in arm_groups.values() for c in g]
    mask = pd.Series(True, index=df.index)
    for c in cols:
        mask &= encoded[c].notna()
    sub, enc_sub = df[mask], encoded[mask]
    y = sub[target].to_numpy()
    t = sub['t_score'].to_numpy()
    X_base = build_feature_matrix(enc_sub, base_groups)
    X_arm = build_feature_matrix(enc_sub, {**base_groups, **arm_groups})
    folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED).split(X_base, y))

    s_base = oof_scores(X_base, y, t, folds)
    s_arm = oof_scores(X_arm, y, t, folds)
    a_base = {k: roc_auc_score(y, v) for k, v in s_base.items()}
    a_arm = {k: roc_auc_score(y, v) for k, v in s_arm.items()}
    primary = max(a_base, key=a_base.get)
    d, lo, hi, p = bootstrap_delta_auc(y, s_arm[primary], s_base[primary], n_boot=500)
    print(f"  {arm_name:<30} n {len(sub):>5,}  events {int(y.sum()):>4}  "
          f"base {a_base[primary]:.3f} -> arm {a_arm[primary]:.3f}  "
          f"delta {d:+.3f} [{lo:+.3f}, {hi:+.3f}]  "
          f"{'adds signal' if lo > 0 else 'no detectable gain'}")
    return {'Arm': arm_name, 'Target': label, 'n': len(sub), 'Events': int(y.sum()),
            'Variables added': ', '.join(arm_groups),
            'Primary model': primary,
            'Base AUC': round(a_base[primary], 3), 'Arm AUC': round(a_arm[primary], 3),
            'Delta AUC': round(d, 3), '95% CI': f"[{lo:+.3f}, {hi:+.3f}]",
            'p (one-sided)': round(p, 4),
            'Verdict': 'Adds signal' if lo > 0 else 'No detectable gain'}


def run_arms(df, encoded, cohorts):
    """Arms C-H, all prespecified. Nulls are reported, not buried.

    Every one of these was written down before it was run, with the expected answer
    stated in advance. That is what makes a null here informative rather than a failed
    attempt: 'serum vitamin D adds nothing' is a result when it was predicted, and a
    fishing expedition when it was not.
    """
    print_section('STEP 13: PRESPECIFIED ARMS')
    base = FEATURE_GROUPS
    rows = []

    print('\n  Arms C/D — vitamin D. Intake and serum are measured on DIFFERENT subsets,')
    print('  so they get separate arms and are never cross-compared. Vitamin D is out of')
    print('  the headline model entirely and the null was stated in advance.')
    rows.append(compare_arm(df, encoded, base, 'C: vitamin D + calcium intake',
                            ARM_GROUPS['vitd_intake'], 'at_risk', 'T<=-1.0'))
    rows.append(compare_arm(df, encoded, base, 'D: serum 25(OH)D',
                            ARM_GROUPS['vitd_serum'], 'at_risk', 'T<=-1.0'))

    print('\n  Arm E — rheumatoid arthritis. Descriptive only at T<=-2.5, and the 123')
    print('  women whose arthritis type is unrecorded are EXCLUDED, not coded as no RA.')
    rows.append(compare_arm(df, encoded, base, 'E: rheumatoid arthritis',
                            ARM_GROUPS['ra'], 'at_risk', 'T<=-1.0'))
    ra = cohorts['C4 + rheumatoid arthritis']['df']
    for v, name in [(1, 'rheumatoid arthritis'), (0, 'no rheumatoid arthritis')]:
        s = ra[ra['rheumatoid_arthritis'] == v]
        print(f"    {name:<24} n {len(s):>4}   mean T {s['t_score'].mean():+.3f}   "
              f"T<=-2.5 {int(s['osteoporosis'].sum()):>3} ({s['osteoporosis'].mean():.1%})")
    print(f"    excluded for unrecorded arthritis type: "
          f"{int((df['ra_arm_eligible'] == 0).sum())}")

    print('\n  Arm F — PHQ-9 as a binary. A SUBSTITUTION for the continuous score, never')
    print('  an addition: the two are the same information and would collide.')
    sub_groups = {k: v for k, v in base.items() if k != 'phq9_score'}
    rows.append(compare_arm(df, encoded, sub_groups, 'F: PHQ-9 >= 10 (substitution)',
                            ARM_GROUPS['phq_binary'], 'at_risk', 'T<=-1.0'))

    print('\n  Arm G — diabetes. The diabetic bone paradox means type 2 diabetes raises')
    print('  measured BMD while also raising fracture risk, so a protective coefficient')
    print('  here is expected and is NOT evidence the model is wrong. There is')
    print('  deliberately no EXPECTED_SIGNS entry for it. Two reclassifications:')
    enc_g = encoded.copy()
    X0 = build_feature_matrix(encoded, base)
    y0 = df['at_risk'].to_numpy()
    t0 = df['t_score'].to_numpy()
    folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED).split(X0, y0))
    a0 = {k: roc_auc_score(y0, v) for k, v in oof_scores(X0, y0, t0, folds).items()}
    primary = max(a0, key=a0.get)
    for variant, series in [
            ('G1: borderline coded as diabetic',
             pd.to_numeric(df['diabetes_borderline_as_case'], errors='coerce')),
            ('G2: diabetes dropped entirely', None)]:
        if series is None:
            Xg = build_feature_matrix(encoded, {k: v for k, v in base.items()
                                                if k != 'diabetes'})
        else:
            enc_g['diabetes'] = series
            Xg = build_feature_matrix(enc_g, base)
        ag = roc_auc_score(y0, oof_scores(Xg, y0, t0, folds)[primary])
        print(f"    {variant:<38} AUC {ag:.3f}  (shipped {a0[primary]:.3f}, "
              f"delta {ag - a0[primary]:+.3f})")
        rows.append({'Arm': variant, 'Target': 'T<=-1.0', 'n': len(df),
                     'Events': int(y0.sum()), 'Variables added': 'diabetes recoded',
                     'Primary model': primary, 'Base AUC': round(a0[primary], 3),
                     'Arm AUC': round(ag, 3), 'Delta AUC': round(ag - a0[primary], 3),
                     '95% CI': 'n/a', 'p (one-sided)': np.nan,
                     'Verdict': 'Sensitivity only'})

    print('\n  Arm H — site sensitivity. The headline uses the WHO/ISCD lowest-of-two')
    print('  rule. These refit on each site alone to show the rule is not driving the')
    print('  result. Reported for the headline target only, and never re-ablated.')
    for site, col in [('H1: femoral neck only', 't_femoral_neck'),
                      ('H2: total hip only', 't_total_hip')]:
        ok = df[col].notna()
        ys = (df.loc[ok, col].round(3) <= T_OSTEOPENIA).astype(int).to_numpy()
        ts = df.loc[ok, col].round(3).to_numpy()
        Xs = build_feature_matrix(encoded[ok.to_numpy()], base)
        fs = list(StratifiedKFold(n_splits=5, shuffle=True,
                                  random_state=SEED).split(Xs, ys))
        asite = {k: roc_auc_score(ys, v) for k, v in oof_scores(Xs, ys, ts, fs).items()}
        pm = max(asite, key=asite.get)
        print(f"    {site:<26} n {int(ok.sum()):>5,}  events {int(ys.sum()):>4}  "
              f"AUC {asite[pm]:.3f}  ({pm})")
        # No delta here. These arms respecify the OUTCOME, so they are computed on a
        # different label and a different set of rows than the headline; subtracting
        # the two AUCs would compare two different questions.
        rows.append({'Arm': site, 'Target': 'T<=-1.0 at this site', 'n': int(ok.sum()),
                     'Events': int(ys.sum()), 'Variables added': 'none (outcome respecified)',
                     'Primary model': pm, 'Base AUC': round(a0[primary], 3),
                     'Arm AUC': round(asite[pm], 3), 'Delta AUC': np.nan,
                     '95% CI': 'n/a (different outcome, not comparable)',
                     'p (one-sided)': np.nan, 'Verdict': 'Sensitivity only'})

    table = pd.DataFrame(rows)
    save_csv(table, 'prespecified_arms.csv', 'PRESENT')
    return table


def screening_tables(X, df, p_cal, oof_r):
    """Two cutoff tables that mean different things by the same numbers.

    referral_table leads with 'Top fraction flagged' — a QUANTILE of the nested model's
    scores, which are ranks and not probabilities. threshold_sweep keeps 'Probability
    Cutoff' — a real probability from a DIFFERENT, sigmoid-calibrated forest. They are
    not on the same axis and must never be merged or plotted together.
    """
    y = df['at_risk'].to_numpy()
    print_section('STEP 14: SCREENING YIELD — T<=-1.0')
    print('  How many DXA scans does each referral rule cost per case found?\n')
    ref = referral_table(y, oof_r, as_quantile=True)
    ref = ref.rename(columns={'Cutoff': 'Top fraction flagged'})
    ref.insert(0, 'Score', 'Nested CV out-of-fold rank (not a probability)')
    print(ref.to_string(index=False))
    save_csv(ref, 'referral_table.csv', 'PRESENT')

    sweep = referral_table(y, p_cal, as_quantile=False)
    sweep = sweep.rename(columns={'Cutoff': 'Probability Cutoff'})
    sweep.insert(0, 'Model', 'Random forest, sigmoid-calibrated')
    sweep.insert(1, 'AUC', round(roc_auc_score(y, p_cal), 3))
    print('\n  Calibrated-probability version — a different model, a different axis:')
    print(sweep.to_string(index=False))
    save_csv(sweep, 'threshold_sweep.csv', 'PRESENT')
    return ref, sweep


def main():
    setup_directories()
    supp = load_supplements()
    day2 = load_day2_dietary()

    df = load_and_merge_cycles()
    df = apply_filters(df)
    df = audit_duplicates(df)
    df = compute_tscores(df)
    df = apply_menopause_gate(df)
    df = compute_menopause_variables(df)
    df = compute_estrogen_variables(df)
    df = compute_derived_variables(df, supp, day2)
    df = rename_and_save(df)

    encoded = encode_features(df)
    cohorts = build_cohorts(df, encoded)
    X = cohorts['C0 base']['X']
    table_one(df, X)

    coefficient_diagnostics(X, df['at_risk'], 'T<=-1.0')

    verdicts = []
    for target, label, tag in [('at_risk', 'Osteopenia+ (T<=-1.0)', 'osteopenia'),
                               ('osteoporosis', 'Osteoporosis (T<=-2.5)', 'osteoporosis')]:
        v, oof_r, _ = evaluate_target(X, df, target, label, df[target].sum(), tag)
        verdicts.append(v)
        if target == 'at_risk':
            headline_oof = oof_r

    verdict = pd.concat(verdicts, ignore_index=True)
    save_csv(verdict, 'nested_cv_verdict.csv', 'PRESENT')

    clin = clinical_table(X, df['at_risk'], 'Osteopenia+ (T<=-1.0)')
    plot_forest(clin, 'Osteopenia+ (T<=-1.0)')
    ablation_grid(X, df['at_risk'], df['t_score'], FEATURE_GROUPS, 'osteopenia')
    block_ablation(X, df['at_risk'], df['t_score'], FEATURE_GROUPS, 'osteopenia')

    p_cal = calibration_figure(X, df['at_risk'], 'Osteopenia+ (T<=-1.0)')
    screening_tables(X, df, p_cal, headline_oof)

    report_rf_tuning(X, df['at_risk'], 'Osteopenia+ (T<=-1.0)')
    run_arms(df, encoded, cohorts)

    print_section('DONE')
    print('  Open outputs/nested_cv_verdict.csv first — it is the bottom line.')
    print('  Variable importance lives in two places and they answer different')
    print('  questions: clinical_predictor_table.csv (shuffle a column inside a model')
    print('  trained with it) and model_variable_ablation_osteopenia.csv (refit without')
    print('  the variable at all). Where they disagree, collinearity is the reason.')


if __name__ == '__main__':
    main()
