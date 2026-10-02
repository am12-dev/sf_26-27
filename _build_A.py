"""
NHANES early-osteoporosis-risk pipeline — rewrite per Notes/rewrite_implementation_plan.html.

Cohort: non-Hispanic White women aged 50-65, POSTMENOPAUSAL, five NHANES cycles.
Target: DXA hip BMD T-score (lowest of femoral neck / total hip); the DXA scan is the
thing being predicted away, so every BMD-derived column is structurally barred from the
feature set by an ALLOWLIST (block E) rather than an exclusion list.

Dependencies (nothing else tracks them): pandas, numpy, matplotlib, scikit-learn,
lightgbm, xgboost, requests.

Structure:
  BLOCK A  configuration and the declarative variable specification
  BLOCK B  data layer: explicit per-cycle file map, per-variable sentinels, decoders
  BLOCK C  cohort construction: filters, duplicate audit, T-scores, menopause gate
  BLOCK D  derivations
  BLOCK E  feature allowlist, analysis cohorts, Riley gate, Table 1
  BLOCK F  model panel, nested CV, permutation importance, ablation grid
  BLOCK G  arms, reporting, main
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
