"""
================================================================================
NHANES OSTEOPOROSIS STUDY — COMPLETE PIPELINE WITH ELASTIC NET & FEATURE WEIGHTS
================================================================================
Study:      Early osteoporosis risk detection without DXA scan
Population: Non-Hispanic White women aged 50–65
Cycles:     2005-06, 2007-08, 2009-10, 2013-14, 2017-18, 2017-20
Models:     Logistic Regression (L2), Elastic Net, Random Forest, LightGBM, XGBoost
================================================================================
"""

import os
import io
import sys
import warnings

# Progress output below uses emoji, which raise UnicodeEncodeError on the default
# Windows console codepage (cp1252). Must run before pandas is imported.
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    pass

import requests
from functools import reduce

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Core Machine Learning Dependencies
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import StratifiedKFold, cross_validate, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import confusion_matrix, roc_auc_score, average_precision_score
from sklearn.calibration import CalibratedClassifierCV
from sklearn.inspection import permutation_importance
from sklearn.base import clone

# Boosting Engines
import lightgbm as lgb
import xgboost as xgb

warnings.filterwarnings('ignore')

# ================================================================================
# CONFIGURATION
# ================================================================================
# Repo root, resolved from this file's location so the script survives a move.
# data/ and outputs/ live directly beneath it.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = f"{BASE_DIR}/data/raw"
PROC_DIR = f"{BASE_DIR}/data/processed"
OUT_DIR  = f"{BASE_DIR}/outputs"

CYCLES = [
    {'name': '2005_2006', 'suffix': 'D', 'prefix': ''},
    {'name': '2007_2008', 'suffix': 'E', 'prefix': ''},
    {'name': '2009_2010', 'suffix': 'F', 'prefix': ''},
    {'name': '2013_2014', 'suffix': 'H', 'prefix': ''},
    {'name': '2017_2018', 'suffix': 'J', 'prefix': ''},
    {'name': '2017_2020', 'suffix': 'P', 'prefix': 'P_'},
]

SUPP_URLS = [
    ('2007_2008', 'DSQTOT_E', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2007/DataFiles/DSQTOT_E.xpt'),
    ('2009_2010', 'DSQTOT_F', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2009/DataFiles/DSQTOT_F.xpt'),
    ('2013_2014', 'DSQTOT_H', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2013/DataFiles/DSQTOT_H.xpt'),
    ('2017_2018', 'DSQTOT_J', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DSQTOT_J.xpt'),
    ('2017_2020', 'P_DSQTOT', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_DSQTOT.xpt'),
]

# Day-2 24-hour dietary recall. A single day's recall carries large within-person
# variance, which attenuates nutrient-outcome associations toward zero (regression
# dilution); averaging two days raises the reliability ratio substantially.
DAY2_URLS = [
    ('2005_2006', 'DR2TOT_D', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/DR2TOT_D.xpt'),
    ('2007_2008', 'DR2TOT_E', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2007/DataFiles/DR2TOT_E.xpt'),
    ('2009_2010', 'DR2TOT_F', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2009/DataFiles/DR2TOT_F.xpt'),
    ('2013_2014', 'DR2TOT_H', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2013/DataFiles/DR2TOT_H.xpt'),
    ('2017_2018', 'DR2TOT_J', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DR2TOT_J.xpt'),
    ('2017_2020', 'P_DR2TOT', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_DR2TOT.xpt'),
]

PHQ_COLS = ['DPQ010', 'DPQ020', 'DPQ030', 'DPQ040', 'DPQ050', 'DPQ060', 'DPQ070', 'DPQ080', 'DPQ090']
REFUSED = [7, 9, 77, 99, 777, 999, 7777, 9999]

# Osteoporosis (WHO): T <= -2.5. Osteopenia-or-worse: T <= -1.0. BMD is reported to
# three decimals, so T-scores are rounded to three before thresholding — without it,
# women sitting exactly on a cutoff land on either side depending on float error.
T_OSTEOPENIA   = -1.0
T_OSTEOPOROSIS = -2.5

# Random-forest leaf size. Nested-CV tuned (see tune_rf_leaf_nested) rather than assumed:
# shrinking the train/test gap by raising this value monotonically LOWERS test AUC, so the
# gap is the price of the performance, not a defect to regularize away.
# Nested inner CV selected leaf=1 in 5/5 folds at T<=-1.0 and 3/5 (leaf=2 otherwise) at
# T<=-2.5, lifting test AUC 0.784 -> 0.810 and 0.829 -> 0.835 respectively. leaf=1 is also
# sklearn's own default; the previous value of 5 was an unnecessary constraint.
RF_MIN_SAMPLES_LEAF = 1
RF_LEAF_GRID = [1, 2, 5, 10, 20, 50]

# Leakage alarm for the coefficient diagnostic. The largest legitimate standardised
# coefficient observed is ~0.99 (weight_kg); a BMD- or T-score-derived column entering the
# feature set would dominate at several times that.
LEAK_COEF_THRESHOLD = 2.0

# Directions established in the osteoporosis literature, used only to flag sign errors.
# +1 = raises risk of low BMD, -1 = protective.
EXPECTED_SIGNS = {
    'weight_kg': -1, 'bmi': -1, 'height_cm': -1, 'age': +1,
    'years_since_menopause': +1, 'postmenopausal': +1, 'oophorectomy': +1,
    'ever_used_estrogen': -1, 'any_prior_fracture': +1, 'steroid_use': +1,
    'serum_vitd_nmol': -1, 'total_calcium_mg': -1, 'total_vitd_mcg': -1,
}

# Clinically meaningful increments for reporting odds ratios. Binary features are reported
# as "yes vs no" regardless of what appears here.
CLINICAL_UNITS = {
    'weight_kg': (10, 'per 10 kg'), 'height_cm': (5, 'per 5 cm'), 'bmi': (5, 'per 5 kg/m2'),
    'age': (5, 'per 5 years'), 'years_since_menopause': (5, 'per 5 years'),
    'serum_vitd_nmol': (25, 'per 25 nmol/L'), 'total_calcium_mg': (500, 'per 500 mg'),
    'total_vitd_mcg': (10, 'per 10 mcg'), 'poverty_income_ratio': (1, 'per 1 unit'),
    'alcohol_drinks_day': (1, 'per 1 drink/day'), 'phq9_score': (5, 'per 5 points'),
}

FEMORAL_NECK_MEAN = 0.858
FEMORAL_NECK_SD   = 0.120
TOTAL_HIP_MEAN    = 0.942
TOTAL_HIP_SD      = 0.122

# ================================================================================
# DATA PIPELINE HARVESTING FUNCTIONS
# ================================================================================

def load_file(cycle_name, filename):
    path = os.path.join(DATA_DIR, cycle_name, filename)
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)

def keep_cols(df, cols):
    if len(df) == 0:
        return pd.DataFrame()
    existing = ['SEQN'] + [c for c in cols if c in df.columns]
    return df[existing].copy()

def merge_files(dfs):
    dfs = [d for d in dfs if len(d) > 0 and 'SEQN' in d.columns]
    if not dfs:
        return pd.DataFrame()
    return reduce(lambda l, r: pd.merge(l, r, on='SEQN', how='left'), dfs)

def recode_yesno(series):
    def _r(x):
        if pd.isna(x): return np.nan
        x = str(x).strip().lower()
        if x in ['yes', '1', '1.0']: return 1.0
        if x in ['no',  '2', '2.0']: return 0.0
        return np.nan
    return series.apply(_r)

def print_section(title):
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")

def setup_directories():
    print_section("STEP 0: SETUP")
    for d in [PROC_DIR, OUT_DIR]:
        os.makedirs(d, exist_ok=True)
        print(f"  ✅ {d}")

def download_supplement_files():
    print_section("STEP 1: SUPPLEMENT FILES")
    all_supp = []
    for cycle, name, url in SUPP_URLS:
        folder   = os.path.join(DATA_DIR, cycle)
        csv_path = os.path.join(folder, f"{name}.csv")
        os.makedirs(folder, exist_ok=True)

        if os.path.exists(csv_path) and os.path.getsize(csv_path) > 10000:
            tmp = pd.read_csv(csv_path, low_memory=False)
            print(f"  📁 {name:15s} (cached) {len(tmp):>6,} rows")
        else:
            print(f"  ⬇️  Downloading {name}...", end=' ', flush=True)
            try:
                resp = requests.get(url, timeout=60)
                if resp.status_code == 200 and len(resp.content) > 10000:
                    tmp = pd.read_sas(io.BytesIO(resp.content), format='xport', encoding='utf-8')
                    tmp.to_csv(csv_path, index=False)
                    print(f"✅ {len(tmp):,} rows")
                else:
                    print(f"❌ HTTP {resp.status_code}")
                    continue
            except Exception as e:
                print(f"❌ {str(e)[:60]}")
                continue

        if 'DSQTCALC' in tmp.columns:
            sub = tmp[['SEQN', 'DSQTCALC', 'DSQTVD']].copy()
            sub.columns = ['SEQN', 'supp_calcium_mg', 'supp_vitd_mcg']
            all_supp.append(sub)

    if all_supp:
        supp_all = pd.concat(all_supp, ignore_index=True)
        return supp_all.groupby('SEQN').first().reset_index()
    return pd.DataFrame()

def download_day2_dietary():
    """Day-2 calcium / vitamin D, for the 2-day intake average.

    Only SEQN + the two nutrients are cached (suffix '_calcium_vitd' marks the file as
    a 3-column extract, NOT the full NHANES DR2TOT file) to keep the cache small.
    """
    print_section("STEP 1b: DAY-2 DIETARY RECALL (2-DAY INTAKE AVERAGE)")
    frames = []
    for cycle, name, url in DAY2_URLS:
        folder   = os.path.join(DATA_DIR, cycle)
        csv_path = os.path.join(folder, f"{name}_calcium_vitd.csv")
        os.makedirs(folder, exist_ok=True)

        if os.path.exists(csv_path) and os.path.getsize(csv_path) > 1000:
            tmp = pd.read_csv(csv_path, low_memory=False)
            print(f"  📁 {name:15s} (cached) {len(tmp):>6,} rows")
        else:
            print(f"  ⬇️  Downloading {name}...", end=' ', flush=True)
            try:
                resp = requests.get(url, timeout=180)
                if resp.status_code == 200 and len(resp.content) > 10000:
                    full = pd.read_sas(io.BytesIO(resp.content), format='xport', encoding='utf-8')
                    cols = ['SEQN'] + [c for c in ('DR2TCALC', 'DR2TVD') if c in full.columns]
                    tmp  = full[cols].copy()
                    tmp.to_csv(csv_path, index=False)
                    print(f"✅ {len(tmp):,} rows, cols={cols[1:]}")
                else:
                    print(f"❌ HTTP {resp.status_code}")
                    continue
            except Exception as e:
                print(f"❌ {str(e)[:60]}")
                continue
        frames.append(tmp)

    if not frames:
        print("  ⚠️  no day-2 data available — intake stays single-day")
        return pd.DataFrame()
    day2 = pd.concat(frames, ignore_index=True).groupby('SEQN').first().reset_index()
    print(f"  ✅ day-2 records: {len(day2):,}")
    return day2

def load_and_merge_cycles():
    print_section("STEP 2: LOAD AND MERGE ALL 6 CYCLES")
    all_cycles = []
    for cy in CYCLES:
        name, sfx, pre = cy['name'], cy['suffix'], cy['prefix']
        def fn(mod, _pre=pre, _sfx=sfx): return f"{_pre}{mod}.csv" if _pre else f"{mod}_{_sfx}.csv"

        demo = load_file(name, fn('DEMO'))
        bmx  = load_file(name, fn('BMX'))
        dxa  = load_file(name, fn('DXXFEM'))
        slq  = load_file(name, fn('SLQ'))
        dr1  = load_file(name, fn('DR1TOT'))
        vid  = load_file(name, fn('VID'))
        paq  = load_file(name, fn('PAQ'))
        dpq  = load_file(name, fn('DPQ'))
        smq  = load_file(name, fn('SMQ'))
        alq  = load_file(name, fn('ALQ'))
        mcq  = load_file(name, fn('MCQ'))
        osq  = load_file(name, fn('OSQ'))
        rhq  = load_file(name, fn('RHQ'))
        diq  = load_file(name, fn('DIQ'))

        demo_c = keep_cols(demo, ['RIAGENDR','RIDRETH1','RIDAGEYR','INDFMPIR','DMDEDUC2'])
        bmx_c  = keep_cols(bmx,  ['BMXBMI','BMXWT','BMXHT'])
        dxa_c  = keep_cols(dxa,  ['DXXNKBMD','DXXOFBMD'])
        dr1_c  = keep_cols(dr1,  ['DR1TCALC','DR1TVD'])
        # Serum 25(OH)D. VIDOXBLD (the name previously requested here) exists in no cycle,
        # so this silently contributed nothing. The real columns are LBXVIDMS (2007-2018,
        # LC-MS/MS) and LBDVIDMS (2005-06, regression-adjusted to LC-MS/MS equivalents).
        # 2017-2020 ships no VID file at all.
        vid_c  = keep_cols(vid,  ['LBXVIDMS', 'LBDVIDMS'])
        paq_c  = keep_cols(paq,  ['PAD680','PAQ650'])
        dpq_c  = keep_cols(dpq,  PHQ_COLS)
        smq_c  = keep_cols(smq,  ['SMQ020'])
        alq_c  = keep_cols(alq,  ['ALQ130'])
        mcq_c  = keep_cols(mcq,  ['MCQ160A'])
        osq_c  = keep_cols(osq,  ['OSQ010A','OSQ010B','OSQ010C','OSQ130'])
        # RHQ060 = age at last menstrual period (numeric, present in all six cycles).
        # RHD042 (2005-2010) / RHD043 (2013+) = reason periods stopped, which separates
        # natural menopause from hysterectomy. RHQ031 = any period in the last 12 months.
        rhq_c  = keep_cols(rhq,  ['RHQ074','RHQ540','RHQ060','RHD042','RHD043',
                                  'RHQ031','RHD280','RHQ305'])
        diq_c  = keep_cols(diq,  ['DIQ010'])

        slq_keep = [c for c in ['SLD012','SLD010H'] if c in (slq.columns if len(slq) > 0 else [])]
        slq_c = keep_cols(slq, slq_keep) if slq_keep else pd.DataFrame()

        merged = merge_files([demo_c, bmx_c, dxa_c, slq_c, dr1_c, vid_c, paq_c, dpq_c, smq_c, alq_c, mcq_c, osq_c, rhq_c, diq_c])
        merged['survey_cycle'] = name
        all_cycles.append(merged)

    return pd.concat(all_cycles, ignore_index=True)

def recode_refused(df):
    print_section("STEP 3: RECODE REFUSED/DON'T KNOW TO NaN")
    numeric_cols = [c for c in df.columns if df[c].dtype in ['float64','int64']]
    for col in numeric_cols:
        df[col] = df[col].replace(REFUSED, np.nan)
    return df

def apply_filters(df):
    print_section("STEP 4: INCLUSION FILTERS — ATTRITION TABLE")
    df = df[df['RIAGENDR'].isin([2, 2.0, 'Female'])].copy()
    df = df[df['RIDRETH1'].isin([3, 3.0, 'Non-Hispanic White'])].copy()
    df = df[(df['RIDAGEYR'] >= 50) & (df['RIDAGEYR'] <= 65)].copy()
    df = df[df['DXXNKBMD'].notna()].copy()
    assert len(df) == 1484, f"Expected 1,484 women, got {len(df)}"
    print(f"  ✅ Verified final cohort sample: {len(df):,} women")
    return df

def compute_tscores(df):
    print_section("STEP 5: T-SCORES AND TARGET VARIABLE")
    df['t_femoral_neck'] = (df['DXXNKBMD'] - FEMORAL_NECK_MEAN) / FEMORAL_NECK_SD
    df['t_total_hip']    = (df['DXXOFBMD'] - TOTAL_HIP_MEAN)    / TOTAL_HIP_SD
    df['t_score'] = df[['t_femoral_neck', 't_total_hip']].min(axis=1).round(3)

    # Both targets and bone_status derive from the same rounded comparisons, so the three
    # can never disagree. pd.cut previously put women sitting exactly on -2.5 in a
    # different class than a direct `t_score <= -2.5` test (3 women, a float artifact).
    df['at_risk']      = (df['t_score'] <= T_OSTEOPENIA).astype(int)
    df['osteoporosis'] = (df['t_score'] <= T_OSTEOPOROSIS).astype(int)
    df['bone_status']  = np.select(
        [df['osteoporosis'] == 1, df['at_risk'] == 1],
        ['Osteoporosis', 'Low Bone Mass'], default='Normal')

    n = len(df)
    print(f"  osteopenia or worse (T <= {T_OSTEOPENIA})  : {df['at_risk'].sum():4d} / {n}  ({df['at_risk'].mean():.1%})")
    print(f"  osteoporosis        (T <= {T_OSTEOPOROSIS}) : {df['osteoporosis'].sum():4d} / {n}  ({df['osteoporosis'].mean():.1%})")
    print(f"  t_score mean={df['t_score'].mean():.2f}  sd={df['t_score'].std():.2f}")
    return df

def compute_menopause_variables(df):
    """Reproductive-ageing features.

    Bone loss accelerates through the menopausal transition and the first years after it,
    then slows, so chronological age is a weak surrogate in a 50-65 cohort where menopause
    timing varies widely. Surgical menopause (hysterectomy/oophorectomy) removes ovarian
    oestrogen abruptly rather than gradually and is kept separate for that reason.
    """
    print_section("STEP 6b: REPRODUCTIVE AGEING (YEARS SINCE MENOPAUSE)")

    age_men = pd.to_numeric(df.get('RHQ060'), errors='coerce')
    # RHQ060 is an age in years; anything outside a plausible range is a sentinel.
    age_men = age_men.where((age_men >= 20) & (age_men <= 70))
    df['age_at_menopause'] = age_men

    # Runs before rename_and_save so the derived columns reach the saved CSV, hence the
    # tolerance for either the raw or the renamed age column.
    age_col = 'age' if 'age' in df.columns else 'RIDAGEYR'
    ysm = pd.to_numeric(df[age_col], errors='coerce') - age_men
    df['years_since_menopause'] = ysm.where(ysm >= 0)

    # Two distinct surgical routes, kept separate rather than pooled into one
    # "surgical_menopause" flag: hysterectomy alone leaves the ovaries producing
    # oestrogen, whereas bilateral oophorectomy removes it abruptly. Conflating them
    # buries the variable that should carry the signal.
    df['hysterectomy'] = recode_yesno(df['RHD280']) if 'RHD280' in df.columns else np.nan
    df['oophorectomy'] = recode_yesno(df['RHQ305']) if 'RHQ305' in df.columns else np.nan

    # Reason periods stopped: RHD042 in 2005-2010, RHD043 from 2013 on.
    reason = pd.Series(np.nan, index=df.index, dtype=object)
    for col in ('RHD042', 'RHD043'):
        if col in df.columns:
            reason = reason.fillna(df[col].astype(object))
    r = reason.astype(str).str.strip().str.lower()
    natural = pd.Series(np.nan, index=df.index, dtype=float)
    natural[r.str.contains('menopause|change of life', na=False)] = 1.0
    natural[r.str.contains('hysterectomy', na=False)] = 0.0
    df['menopause_natural'] = natural

    # RHQ031: at least one period in the past 12 months -> still cycling.
    if 'RHQ031' in df.columns:
        recent_period = recode_yesno(df['RHQ031'])
        df['postmenopausal'] = (1.0 - recent_period)
    else:
        df['postmenopausal'] = np.nan

    for c, lab in [('age_at_menopause', 'age at menopause (descriptive only)'),
                   ('years_since_menopause', 'years since menopause'),
                   ('hysterectomy', 'hysterectomy'),
                   ('oophorectomy', 'bilateral oophorectomy'),
                   ('menopause_natural', 'natural menopause'),
                   ('postmenopausal', 'postmenopausal')]:
        s = df[c]
        extra = (f" mean={s.mean():.1f}" if c.startswith(('age', 'years'))
                 else f" positives={int((s == 1).sum())}")
        print(f"  {lab:36s} non-null={s.notna().sum():5d} / {len(df)}{extra}")

    # age = age_at_menopause + years_since_menopause exactly, so all three together make
    # the design rank-deficient and split one effect across arbitrary coefficients.
    # age_at_menopause is dropped from the FEATURE set (it stays in the saved CSV for
    # descriptive tables) and recovered as age - years_since_menopause when needed.
    print("  ⚠️  age_at_menopause excluded from features: exactly collinear with "
          "age - years_since_menopause")
    return df

def compute_derived_variables(df, supp_df, day2_df=None):
    print_section("STEP 6: DERIVED VARIABLES")
    if 'SLD012' in df.columns and 'SLD010H' in df.columns:
        df['sleep_hrs'] = df['SLD012'].fillna(df['SLD010H'])
    else:
        df['sleep_hrs'] = df['SLD012'] if 'SLD012' in df.columns else (df['SLD010H'] if 'SLD010H' in df.columns else np.nan)
    
    df['sleep_hrs']  = pd.to_numeric(df['sleep_hrs'], errors='coerce')
    df['sleep_risk'] = (df['sleep_hrs'] < 7).astype(float)
    df.loc[df['sleep_hrs'].isna(), 'sleep_risk'] = np.nan

    avail_phq = [c for c in PHQ_COLS if c in df.columns]
    df['phq9_score'] = df[avail_phq].apply(pd.to_numeric, errors='coerce').clip(0, 3).sum(axis=1, min_count=5)

    # Serum 25(OH)D, coalesced across the two column names NHANES used.
    serum = pd.Series(np.nan, index=df.index, dtype=float)
    for col in ('LBXVIDMS', 'LBDVIDMS'):
        if col in df.columns:
            serum = serum.fillna(pd.to_numeric(df[col], errors='coerce'))
    df['serum_vitd_nmol'] = serum
    print(f"  ℹ️  serum_vitd_nmol non-null: {serum.notna().sum():,} / {len(df):,}"
          f"  mean={serum.mean():.1f} nmol/L")

    # Supplement totals exist only for cycles that ship a DSQTOT file (2005-06 has none:
    # DSQTOT starts in 2007-08). Absence from every file means "unobserved", whereas a NaN
    # nutrient value for someone present in a file means "no calcium / vitamin-D supplement
    # reported" — NHANES codes non-users as NaN, not 0. So the 0-fill is scoped to
    # respondents who actually appear in a supplement file; the rest stay NaN.
    if len(supp_df) > 0:
        df = df.merge(supp_df, on='SEQN', how='left')
        observed = df['SEQN'].isin(set(supp_df['SEQN']))
    else:
        df['supp_calcium_mg'] = np.nan
        df['supp_vitd_mcg']   = np.nan
        observed = pd.Series(False, index=df.index)

    df['supp_data_available'] = observed.astype(float)

    for col in ['supp_calcium_mg', 'supp_vitd_mcg']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df.loc[observed, col]  = df.loc[observed, col].fillna(0)
        df.loc[~observed, col] = np.nan

    # Average the two 24-hour recalls where day 2 exists. A single day estimates that
    # day's intake, not habitual intake; two days materially reduce that error.
    if day2_df is not None and len(day2_df) > 0:
        df = df.merge(day2_df, on='SEQN', how='left')

    def mean_of_days(day1_col, day2_col):
        d1 = pd.to_numeric(df[day1_col], errors='coerce') if day1_col in df.columns else pd.Series(np.nan, index=df.index)
        d2 = pd.to_numeric(df[day2_col], errors='coerce') if day2_col in df.columns else pd.Series(np.nan, index=df.index)
        return pd.concat([d1, d2], axis=1).mean(axis=1), d1, d2

    diet_ca, ca1, ca2 = mean_of_days('DR1TCALC', 'DR2TCALC')
    diet_vd, _,   _   = mean_of_days('DR1TVD',   'DR2TVD')
    df['dietary_calcium_mg_2day'] = diet_ca
    df['dietary_vitd_mcg_2day']   = diet_vd
    df['n_recall_days'] = ca1.notna().astype(int) + ca2.notna().astype(int)
    print(f"  ℹ️  dietary recall days used: "
          f"{(df['n_recall_days'] == 2).sum():,} women on 2 days, "
          f"{(df['n_recall_days'] == 1).sum():,} on 1 day, "
          f"{(df['n_recall_days'] == 0).sum():,} none")

    # Plain addition, not .add(fill_value=0): a missing dietary or supplement component
    # must yield a missing total rather than a fabricated one.
    df['total_calcium_mg'] = diet_ca + df['supp_calcium_mg']
    df['total_vitd_mcg']   = diet_vd + df['supp_vitd_mcg']

    n_unobs = int((~observed).sum())
    print(f"  ℹ️  supplement data unobserved for {n_unobs:,} women -> total_* left NaN, flagged via supp_data_available")
    print(f"  ℹ️  total_calcium_mg missing: {df['total_calcium_mg'].isna().sum():,} / {len(df):,}")
    return df

def recode_binary_variables(df):
    print_section("STEP 7: RECODE BINARY CLINICAL VARIABLES")
    binary_sources = []
    for cy in CYCLES:
        n, sfx, pre = cy['name'], cy['suffix'], cy['prefix']
        def fn2(mod, _pre=pre, _sfx=sfx): return f"{_pre}{mod}.csv" if _pre else f"{mod}_{_sfx}.csv"

        for module, col, new_name in [
            # MCQ160A asks whether a doctor ever said you had ARTHRITIS, of any type — it
            # is not rheumatoid-specific. It was previously named rheumatoid_arthritis,
            # which put a 45.8%-prevalence variable into the model under the name of a
            # 1-2%-prevalence FRAX risk factor.
            ('MCQ', 'MCQ160A', 'any_arthritis'),        ('OSQ', 'OSQ010A', 'prior_hip_fracture'),
            ('OSQ', 'OSQ010B', 'prior_spine_fracture'), ('OSQ', 'OSQ010C', 'prior_wrist_fracture'),
            ('OSQ', 'OSQ130',  'steroid_use'),           ('SMQ', 'SMQ020',  'ever_smoked'),
            ('RHQ', 'RHQ540',  'ever_used_estrogen'),    ('PAQ', 'PAQ650',  'vigorous_activity'),
            ('DIQ', 'DIQ010',  'diabetes'),
        ]:
            tmp = load_file(n, fn2(module))
            if len(tmp) > 0 and col in tmp.columns:
                sub = tmp[['SEQN', col]].copy()
                sub[new_name] = recode_yesno(sub[col])
                binary_sources.append(sub[['SEQN', new_name]])

    if binary_sources:
        binary_all = pd.concat(binary_sources).groupby('SEQN').first().reset_index()
        df = df.merge(binary_all, on='SEQN', how='left')

    # Hip (21 positives) and wrist (46) are too rare to estimate separately at this n —
    # every tree model assigned them exactly zero importance while the linear models
    # fitted noise. Pooled, "any prior fracture" is both estimable and the clinically
    # meaningful construct. The three components stay in the CSV for descriptive tables.
    parts = [c for c in ('prior_hip_fracture', 'prior_spine_fracture', 'prior_wrist_fracture')
             if c in df.columns]
    if parts:
        sub = df[parts]
        # 1 if any site reported, 0 only if every site was answered "no", else NaN.
        df['any_prior_fracture'] = np.where(
            (sub == 1).any(axis=1), 1.0,
            np.where(sub.notna().all(axis=1), 0.0, np.nan))
        n_pos = int((df['any_prior_fracture'] == 1).sum())
        print(f"  ℹ️  any_prior_fracture: {n_pos} positives "
              f"({100 * n_pos / len(df):.1f}%) from {', '.join(parts)}")
    return df

def rename_and_save(df):
    print_section("STEP 8: RENAME AND SAVE")
    rename = {
        'RIDAGEYR': 'age', 'INDFMPIR': 'poverty_income_ratio', 'DMDEDUC2': 'education',
        'BMXBMI': 'bmi', 'BMXWT': 'weight_kg', 'BMXHT': 'height_cm', 'DR1TCALC': 'dietary_calcium_mg',
        'DR1TVD': 'dietary_vitd_mcg', 'PAD680': 'sedentary_min_day',
        'ALQ130': 'alcohol_drinks_day', 'DXXNKBMD': 'femoral_neck_bmd', 'DXXOFBMD': 'total_hip_bmd',
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    df.to_csv(os.path.join(PROC_DIR, 'option_b_v4_final.csv'), index=False)
    return df

def define_features(df):
    print_section("STEP 9: DEFINE FEATURE SETS")
    exclude = [
        'SEQN', 'RIAGENDR', 'RIDRETH1', 'survey_cycle', 'age_group',
        'femoral_neck_bmd', 'total_hip_bmd', 't_femoral_neck', 't_total_hip', 't_score', 'bone_status',
        'at_risk', 'DPQ010', 'DPQ020', 'DPQ030', 'DPQ040', 'DPQ050', 'DPQ060', 'DPQ070', 'DPQ080', 'DPQ090',
        'cigarettes_per_day', 'menopause_confirmed', 'dietary_calcium_mg', 'dietary_vitd_mcg',
        'supp_calcium_mg', 'supp_vitd_mcg', 'sleep_hrs', 'SLD012', 'SLD010H', 'sedentary_min_day',
        # Second target — excluding it is mandatory, it is derived from the T-score.
        'osteoporosis',
        # Raw reproductive items, superseded by the derived menopause variables. RHQ060 in
        # particular is numeric and would otherwise duplicate age_at_menopause.
        'RHQ060', 'RHD042', 'RHD043', 'RHQ031', 'RHD280', 'RHQ305', 'RHQ074',
        # Raw day-2 dietary columns and the recall-day counter: DR2* are never renamed, so
        # without this they enter the model as duplicates of the 2-day averages, and
        # n_recall_days encodes day-2 response rather than anything about the respondent.
        'DR2TCALC', 'DR2TVD', 'n_recall_days',
        'dietary_calcium_mg_2day', 'dietary_vitd_mcg_2day',
        # age == age_at_menopause + years_since_menopause exactly. Keeping all three makes
        # the design rank-deficient, so age_at_menopause is descriptive-only.
        'age_at_menopause',
        # Superseded by any_prior_fracture (hip 21 / wrist 46 positives are unestimable).
        'prior_hip_fracture', 'prior_spine_fracture', 'prior_wrist_fracture',
        # Raw serum 25(OH)D columns, superseded by the coalesced serum_vitd_nmol.
        'LBXVIDMS', 'LBDVIDMS',
    ]
    feat_with = [c for c in df.columns if c not in exclude]
    X_with = df[feat_with].copy()
    y = df['at_risk'].copy()
    X_with = X_with.drop(columns=X_with.select_dtypes(include=['object', 'category']).columns.tolist())
    X_without = X_with.drop(columns=['sleep_risk'], errors='ignore')
    return X_with, X_without, y

# ================================================================================
# STEP 10: MODEL DEFINITION & CROSS-VALIDATION
# ================================================================================

def make_random_forest(min_samples_leaf=None, oob=True):
    """Random forest with out-of-bag scoring enabled.

    OOB scores each row using only the ~37% of trees whose bootstrap sample excluded it,
    which is the honest in-sample number for a bagged ensemble. The plain in-sample AUC
    is near 1.0 for any deep forest — on shuffled labels this configuration still reaches
    0.997 — because ~63% of the trees have memorized each training row.
    """
    return RandomForestClassifier(
        n_estimators=500,
        min_samples_leaf=RF_MIN_SAMPLES_LEAF if min_samples_leaf is None else min_samples_leaf,
        class_weight='balanced', random_state=42, n_jobs=-1,
        bootstrap=True, oob_score=oob)

def get_model_dictionary(pos_weight):
    return {
        'Logistic Regression (L2)': LogisticRegression(
            max_iter=1000, 
            random_state=42, 
            class_weight='balanced'
        ),
        'Elastic Net Logistic Regression': LogisticRegression(
            penalty='elasticnet',
            solver='saga',
            l1_ratio=0.5,
            max_iter=2000,
            random_state=42,
            class_weight='balanced'
        ),
        'Random Forest': make_random_forest(),
        'LightGBM (Aggressive Reg)': lgb.LGBMClassifier(
            n_estimators=150, max_depth=2, num_leaves=4, min_child_samples=50, reg_lambda=50.0,
            class_weight='balanced', random_state=42, verbose=-1, n_jobs=-1
        ),
        'XGBoost (Aggressive Reg)': xgb.XGBClassifier(
            n_estimators=150, max_depth=2, min_child_weight=15, reg_lambda=50.0,
            scale_pos_weight=pos_weight, random_state=42, eval_metric='logloss', n_jobs=-1
        )
    }

def run_model(pipe, X, y, cv):
    res = cross_validate(pipe, X, y, cv=cv, scoring=['roc_auc', 'recall', 'precision', 'f1'], return_train_score=True)
    y_pred = cross_val_predict(pipe, X, y, cv=cv)
    tn, fp, fn, tp = confusion_matrix(y, y_pred).ravel()

    # This full-data fit was previously discarded; it now yields the OOB estimate.
    pipe.fit(X, y)
    oob_auc = np.nan
    est = pipe.named_steps['model']
    if hasattr(est, 'oob_decision_function_'):
        oob_p = est.oob_decision_function_[:, 1]
        ok = ~np.isnan(oob_p)          # a row in every bootstrap has no OOB estimate
        if ok.sum() > 0:
            oob_auc = roc_auc_score(np.asarray(y)[ok], oob_p[ok])

    return {
        'auc': res['test_roc_auc'].mean(),
        'train_auc': res['train_roc_auc'].mean(),
        'oob_auc': oob_auc,
        'sens': tp / (tp + fn),
        'spec': tn / (tn + fp),
        'tn': tn, 'fp': fp, 'fn': fn, 'tp': tp
    }

def train_models(X_without, y):
    print_section("STEP 10: TRAIN AND AUDIT ALL MODALITY ARCHITECTURES")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    pos_weight = (y == 0).sum() / (y == 1).sum() if (y == 1).sum() > 0 else 1.0
    
    models = get_model_dictionary(pos_weight)

    results = []
    for name, model in models.items():
        pipe = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler()),
            ('model', model)
        ])
        metrics = run_model(pipe, X_without, y, cv)
        metrics['Model'] = name
        results.append(metrics)
        oob = f" | OOB AUC: {metrics['oob_auc']:.3f}" if not np.isnan(metrics['oob_auc']) else ""
        print(f"  ✅ Evaluated: {name:<32} | Test AUC: {metrics['auc']:.3f} "
              f"| Train AUC: {metrics['train_auc']:.3f}{oob}")

    return pd.DataFrame(results)

# ================================================================================
# STEP 11: FEATURE WEIGHTAGE & IMPORTANCE ANALYSIS
# ================================================================================

def audit_feature_weights(X, y):
    print_section("STEP 11: FEATURE WEIGHTS & IMPORTANCE AUDIT")
    
    pos_weight = (y == 0).sum() / (y == 1).sum() if (y == 1).sum() > 0 else 1.0
    # Tree importances were removed from this audit. Gini importance and split counts are
    # unsigned and biased toward continuous features over binary ones, which inverted the
    # real ranking: total_calcium_mg placed 7th despite a flat outcome gradient (57.8 /
    # 55.0 / 57.6 / 58.5% by quartile) while oophorectomy placed last despite OR 1.28.
    # Permutation importance in clinical_table() replaces them on a comparable AUC-drop
    # scale. The signed coefficients stay because they are the leak and sign-error detector.
    models = {k: v for k, v in get_model_dictionary(pos_weight).items()
              if k in ('Logistic Regression (L2)', 'Elastic Net Logistic Regression')}

    imputer = SimpleImputer(strategy='median')
    scaler = StandardScaler()
    
    X_proc = scaler.fit_transform(imputer.fit_transform(X))
    feature_names = X.columns.tolist()
    
    importance_dict = {'Feature': feature_names}
    
    for name, model in models.items():
        model.fit(X_proc, y)
        
        if hasattr(model, 'coef_'):
            # Linear model coefficients (Log Odds weights)
            weights = model.coef_[0]
        elif hasattr(model, 'feature_importances_'):
            # Tree-based feature importances
            weights = model.feature_importances_
        else:
            weights = np.zeros(len(feature_names))
            
        importance_dict[name] = weights

    importance_df = pd.DataFrame(importance_dict)
    
    # Sort by absolute weight in Elastic Net for clean ranking
    importance_df['abs_ref'] = importance_df['Elastic Net Logistic Regression'].abs()
    importance_df = importance_df.sort_values(by='abs_ref', ascending=False).drop(columns=['abs_ref'])

    # Internal diagnostic only — not a presentation artifact. Its job is to catch two
    # classes of bug, both of which it has caught before:
    #   1. Target leakage. Feature selection is exclusion-based, so any new BMD- or
    #      T-score-derived column silently enters the model and shows up here as a
    #      coefficient far larger than any legitimate predictor.
    #   2. Sign errors. A clinically backwards coefficient revealed the age /
    #      age_at_menopause / years_since_menopause collinearity, and a near-zero one
    #      revealed that hysterectomy and oophorectomy had been conflated.
    ref = 'Elastic Net Logistic Regression'
    top = importance_df.reindex(importance_df[ref].abs().sort_values(ascending=False).index)
    worst = top.iloc[0]
    print(f"  coefficient diagnostic: largest |standardised coef| = {abs(worst[ref]):.3f} "
          f"({worst['Feature']})")
    if abs(worst[ref]) > LEAK_COEF_THRESHOLD:
        print(f"  🚨 EXCEEDS {LEAK_COEF_THRESHOLD} — suspect target leakage. Check whether a new "
              f"column derived from BMD or the T-score entered the feature set.")
    else:
        print(f"  ✅ below the {LEAK_COEF_THRESHOLD} leakage threshold; no feature dominates implausibly")

    flipped = [f for f, v in zip(top['Feature'], top[ref])
               if f in EXPECTED_SIGNS and np.sign(v) != EXPECTED_SIGNS[f] and abs(v) > 0.02]
    if flipped:
        print(f"  ⚠️  coefficients against the expected clinical direction: {', '.join(flipped)}")
    else:
        print("  ✅ all coefficients with a known clinical direction have the expected sign")

    save_csv(top, "coefficient_diagnostics.csv", 'DIAGNOSTIC')
    print("     standardised units, unstable across collinear predictors — a leak and")
    print("     sign-error detector, NOT a findings table. Present clinical_predictor_table.csv.")

    return importance_df

# ================================================================================
# STEP 13: SENSITIVITY OPTIMIZATION & THRESHOLD SWEEP
# ================================================================================

def optimize_for_early_detection(X, y):
    print_section("STEP 13: OPTIMIZE FOR HIGH SENSITIVITY & EARLY DETECTION")
    
    cv_opt = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    base_rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=15,
        max_features="sqrt",
        class_weight={0: 1, 1: 3},
        random_state=42,
        n_jobs=-1
    )
    
    calibrated_rf = CalibratedClassifierCV(estimator=base_rf, method="sigmoid", cv=cv_opt)
    
    y_true_all, y_probs_all = [], []
    
    for train_idx, test_idx in cv_opt.split(X, y):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        
        imputer = SimpleImputer(strategy='median')
        scaler = StandardScaler()
        
        X_train_proc = scaler.fit_transform(imputer.fit_transform(X_train))
        X_test_proc = scaler.transform(imputer.transform(X_test))
        
        calibrated_rf.fit(X_train_proc, y_train)
        probs = calibrated_rf.predict_proba(X_test_proc)[:, 1]
        
        y_true_all.extend(y_test)
        y_probs_all.extend(probs)
        
    y_true_all = np.array(y_true_all)
    y_probs_all = np.array(y_probs_all)
    
    pr_auc = average_precision_score(y_true_all, y_probs_all)
    roc_auc = roc_auc_score(y_true_all, y_probs_all)
    
    print(f"  ✅ Calibrated RF PR-AUC Score : {pr_auc:.3f}")
    print(f"  ✅ Calibrated RF ROC-AUC Score: {roc_auc:.3f}\n")
    
    thresholds = [0.50, 0.40, 0.35, 0.30, 0.25]
    threshold_results = []
    
    for t in thresholds:
        preds = (y_probs_all >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true_all, preds).ravel()
        
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
        
        threshold_results.append({
            "Probability Cutoff": f"≥ {t:.2f}",
            "Sensitivity (Recall)": f"{sensitivity:.1%}",
            "Specificity": f"{specificity:.1%}",
            "Precision (PPV)": f"{ppv:.1%}",
            "Missed Cases (FN)": fn,
            "Flagged for DXA (TP + FP)": tp + fp
        })
        
    results_df = pd.DataFrame(threshold_results)
    
    print("=" * 95)
    print("🎯 CLINICAL DECISION THRESHOLD TUNING SWEEP (TARGETING ≥80% SENSITIVITY)")
    print("=" * 95)
    print(results_df.to_string(index=False))
    print("=" * 95)

    # A DIFFERENT forest from the leaderboard's: shallower, larger leaves, 3:1 class
    # weight, sigmoid-calibrated. Its ranking is weaker but its probabilities mean what
    # they say, which is what makes choosing a probability cutoff legitimate at all.
    # Both AUCs are recorded on every row so this table can never be mistaken for the
    # leaderboard model disagreeing with itself.
    save_csv(results_df.assign(**{'Model': 'Calibrated RF (depth 6, leaf 15, 3:1 weight)',
                                  'Model ROC-AUC': round(roc_auc, 4),
                                  'Model PR-AUC': round(pr_auc, 4)}),
             'threshold_sweep.csv', 'PRESENT')

# ================================================================================
# STEP 11b: CLINICAL PREDICTOR TABLE (for the specialist, not the modeller)
# ================================================================================

def _clinical_increment(X, feature):
    """Reporting increment for one predictor: (size in raw units, label)."""
    vals = X[feature].dropna().unique()
    if set(np.unique(vals)).issubset({0.0, 1.0}):
        return 1.0, 'yes vs no'
    return CLINICAL_UNITS.get(feature, (float(X[feature].std()), 'per 1 SD'))

def bootstrap_odds_ratios(X, y, n_boot=500, seed=42):
    """Stratified bootstrap CIs for adjusted odds ratios, per clinical unit.

    Each replicate refits the whole pipeline — imputation, scaling, and the penalised
    logistic fit — so imputation variability is carried into the interval rather than
    being treated as if the imputed values were observed. The scaler's own scale_ is used
    to convert each replicate's standardised coefficient back to raw units, which keeps
    the conversion correct even though the SD differs between replicates.
    """
    rng = np.random.default_rng(seed)
    y_arr = np.asarray(y)
    pos, neg = np.flatnonzero(y_arr == 1), np.flatnonzero(y_arr == 0)
    incs = np.array([_clinical_increment(X, f)[0] for f in X.columns], dtype=float)

    base_model = LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced')
    draws = np.empty((n_boot, X.shape[1]))
    for b in range(n_boot):
        ix = np.concatenate([rng.choice(pos, pos.size, replace=True),
                             rng.choice(neg, neg.size, replace=True)])
        pipe = _pipe(clone(base_model))
        pipe.fit(X.iloc[ix], y_arr[ix])
        coef_std = pipe.named_steps['model'].coef_[0]
        scale = pipe.named_steps['scaler'].scale_
        draws[b] = (coef_std / scale) * incs           # log-odds per clinical unit

    pipe = _pipe(clone(base_model))
    pipe.fit(X, y_arr)
    point = (pipe.named_steps['model'].coef_[0] / pipe.named_steps['scaler'].scale_) * incs
    return (np.exp(point), np.exp(np.percentile(draws, 2.5, axis=0)),
            np.exp(np.percentile(draws, 97.5, axis=0)))

def permutation_importance_cv(model, X, y, n_repeats=5, seed=42):
    """Permutation importance as mean AUC lost, measured out of fold.

    Model-agnostic and in the same units for every model, so unlike Gini importance or
    split counts it is comparable across model families and is not biased toward
    continuous features over binary ones.
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

def clinical_table(X, y, target_label):
    print_section(f"STEP 11b: CLINICAL PREDICTOR TABLE — {target_label}")
    print("  Adjusted odds ratios from penalised logistic regression, per clinically")
    print("  meaningful unit, with stratified-bootstrap 95% CIs. Permutation importance is")
    print("  mean AUC lost when the predictor is shuffled, measured out of fold.\n")

    or_pt, or_lo, or_hi = bootstrap_odds_ratios(X, y)
    pos_weight = (np.asarray(y) == 0).sum() / max((np.asarray(y) == 1).sum(), 1)
    perm_lr = permutation_importance_cv(
        get_model_dictionary(pos_weight)['Logistic Regression (L2)'], X, y)
    perm_rf = permutation_importance_cv(make_random_forest(oob=False), X, y)

    rows = []
    for i, f in enumerate(X.columns):
        _, unit_label = _clinical_increment(X, f)
        signif = not (or_lo[i] <= 1.0 <= or_hi[i])
        rows.append({
            'Predictor': f, 'Unit': unit_label,
            'OR': or_pt[i], '95% CI': f"({or_lo[i]:.2f}-{or_hi[i]:.2f})",
            'Direction': ('risk' if or_pt[i] > 1 else 'protective') if signif else 'ns',
            'dAUC (LR)': perm_lr[i], 'dAUC (RF)': perm_rf[i],
            'Missing %': 100 * X[f].isna().mean(),
        })
    table = pd.DataFrame(rows).sort_values('dAUC (RF)', ascending=False)

    print(table.to_string(index=False, formatters={
        'OR': '{:.2f}'.format, 'dAUC (LR)': '{:+.4f}'.format,
        'dAUC (RF)': '{:+.4f}'.format, 'Missing %': '{:.1f}'.format}))
    n_sig = int((table['Direction'] != 'ns').sum())
    print(f"\n  {n_sig} of {len(table)} predictors have a 95% CI excluding OR = 1.")
    print("  'ns' = interval includes 1; the point estimate should not be interpreted.")

    save_csv(table, "clinical_predictor_table.csv", 'PRESENT')
    plot_forest(table, target_label)
    return table

def plot_forest(table, target_label):
    """Forest plot of adjusted ORs on a log scale — the figure a clinical audience expects."""
    plt.switch_backend('Agg')
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
    out = os.path.join(OUT_DIR, 'forest_plot_odds_ratios.png')
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  📁 [PRESENT   ] {os.path.basename(out)}")

# ================================================================================
# STEP 12: BASELINE COMPARATORS, DUAL TARGETS, CONTINUOUS T-SCORE ARM
# ================================================================================

def compute_baselines(df):
    """Non-ML comparators, oriented so that a HIGHER score means HIGHER risk.

    OST = 0.2 * (weight_kg - age), a validated two-input screening formula that needs
    only a scale and a birthdate. It is the bar any model here has to clear: reporting
    AUC without it makes the numbers uninterpretable.
    """
    w = pd.to_numeric(df['weight_kg'], errors='coerce')
    a = pd.to_numeric(df['age'], errors='coerce')
    ost = 0.2 * (w - a)
    return {
        'OST  0.2x(weight-age)': -ost.fillna(ost.median()).to_numpy(),
        'Weight alone':          -w.fillna(w.median()).to_numpy(),
    }

def bootstrap_delta_auc(y, s_model, s_ref, n_boot=1000, seed=42):
    """Paired stratified bootstrap of AUC(model) - AUC(reference).

    Resampling cases and non-cases separately holds prevalence fixed across replicates.
    Both scores are evaluated on the same resampled rows, so the difference is paired.
    """
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    a = np.asarray(s_model, dtype=float)
    b = np.asarray(s_ref,   dtype=float)
    pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    d = np.empty(n_boot)
    for i in range(n_boot):
        ix = np.concatenate([rng.choice(pos, pos.size, replace=True),
                             rng.choice(neg, neg.size, replace=True)])
        d[i] = roc_auc_score(y[ix], a[ix]) - roc_auc_score(y[ix], b[ix])
    return d.mean(), np.percentile(d, 2.5), np.percentile(d, 97.5), float((d <= 0).mean())

def get_regressor_dictionary():
    """Continuous t_score models.

    Dichotomising a continuous measurement discards information — a woman at T=-2.4 and
    one at T=+0.5 are currently the same 'negative'. Regressing t_score keeps the
    gradient, and one fit serves BOTH clinical cutoffs: the predicted T-score is simply
    thresholded twice. These models never see either binary label.
    """
    return {
        'Ridge -> t_score':    RidgeCV(alphas=np.logspace(-3, 3, 13)),
        'RF -> t_score':       RandomForestRegressor(n_estimators=500, min_samples_leaf=5,
                                                     random_state=42, n_jobs=-1),
        'LightGBM -> t_score': lgb.LGBMRegressor(n_estimators=150, max_depth=2, num_leaves=4,
                                                 min_child_samples=50, reg_lambda=50.0,
                                                 random_state=42, verbose=-1, n_jobs=-1),
    }

def _pipe(model):
    return Pipeline([('imputer', SimpleImputer(strategy='median')),
                     ('scaler', StandardScaler()), ('model', model)])

def save_csv(df, filename, tier):
    """Write one result table to outputs/ and label who it is for.

    Every file this pipeline writes carries a tier, so that a folder of CSVs stays
    self-explanatory without a README that can drift out of sync with the code:
      PRESENT    - for the clinical audience.
      METHODS    - backs up a methodological choice if it is challenged.
      DIAGNOSTIC - a bug detector. Its numbers are in standardised units and are
                   unstable across collinear predictors, so they are NOT findings
                   and must not be shown as results.
    """
    assert tier in ('PRESENT', 'METHODS', 'DIAGNOSTIC'), tier
    path = os.path.join(OUT_DIR, filename)
    df.to_csv(path, index=False)
    print(f"  📁 [{tier:10s}] {filename}")
    return path

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
        rows.append({
            'Cutoff': f"{c:.2f}", 'Sensitivity': f"{tp / P:.1%}" if P else "n/a",
            'DXAs ordered': flagged, 'Cases found': tp, 'Missed': P - tp,
            'PPV': f"{tp / flagged:.1%}" if flagged else "n/a",
            'Scans per case': f"{flagged / tp:.2f}" if tp else "inf",
        })
    rows.append({'Cutoff': 'scan all', 'Sensitivity': '100.0%', 'DXAs ordered': N,
                 'Cases found': P, 'Missed': 0, 'PPV': f"{P / N:.1%}",
                 'Scans per case': f"{N / P:.2f}" if P else "inf"})
    return pd.DataFrame(rows)

def nested_cv_selection(X, y, t_score, n_outer=5, n_inner=3, seed=42):
    """Unbiased evaluation of the whole 'fit ten models, keep the best' procedure.

    Picking the winner on the same rows that score it is optimistic: the leaderboard's
    best delta-vs-OST is an upper bound, not an estimate. Here model choice happens
    strictly inside each outer TRAINING fold (via inner CV), and the winner is scored on
    the untouched outer test fold. The pooled out-of-fold predictions therefore estimate
    what the selection procedure actually generalises to.

    Candidates span both arms: classifiers see the binary label, regressors see only the
    continuous t_score, so the inner CV also decides which arm wins per fold.
    """
    y = np.asarray(y)
    t_score = np.asarray(t_score)
    outer = list(StratifiedKFold(n_splits=n_outer, shuffle=True, random_state=seed).split(X, y))
    oof = np.zeros(len(y), dtype=float)
    chosen = []

    for tr, te in outer:
        X_tr, y_tr, t_tr = X.iloc[tr], y[tr], t_score[tr]
        pw = (y_tr == 0).sum() / max((y_tr == 1).sum(), 1)
        inner = list(StratifiedKFold(n_splits=n_inner, shuffle=True,
                                     random_state=seed).split(X_tr, y_tr))

        best_name, best_auc, best_est, best_kind = None, -np.inf, None, None
        for name, model in get_model_dictionary(pw).items():
            p = cross_val_predict(_pipe(model), X_tr, y_tr, cv=inner, method='predict_proba')[:, 1]
            a = roc_auc_score(y_tr, p)
            if a > best_auc:
                best_name, best_auc, best_est, best_kind = name, a, model, 'clf'
        for name, reg in get_regressor_dictionary().items():
            p = -cross_val_predict(_pipe(reg), X_tr, t_tr, cv=inner)
            a = roc_auc_score(y_tr, p)
            if a > best_auc:
                best_name, best_auc, best_est, best_kind = name, a, reg, 'reg'

        pipe = _pipe(best_est)
        if best_kind == 'clf':
            pipe.fit(X_tr, y_tr)
            oof[te] = pipe.predict_proba(X.iloc[te])[:, 1]
        else:
            pipe.fit(X_tr, t_tr)
            oof[te] = -pipe.predict(X.iloc[te])
        chosen.append(best_name)

    return oof, chosen, outer

def rank_within_folds(score, folds, n):
    """Map scores to within-fold percentile ranks.

    Different outer folds can select different winners, and a classifier's probabilities
    (0-1) are not on the same scale as a regressor's negated T-scores (about -1 to 4).
    Pooling those raw values into one AUC corrupts the global ranking and deflates it.
    AUC only uses order, so converting to within-fold ranks makes folds commensurable
    without changing any within-fold comparison. Applied identically to every score being
    compared, so the contrast stays paired.
    """
    out = np.empty(n, dtype=float)
    s = np.asarray(score, dtype=float)
    for _, te in folds:
        out[te] = pd.Series(s[te]).rank(pct=True).to_numpy()
    return out

def tune_rf_leaf_nested(X, y, grid=RF_LEAF_GRID, n_outer=5, n_inner=3, seed=42):
    """Nested-CV tuning of min_samples_leaf, plus fixed-value comparators.

    The leaf value is chosen by inner CV inside each outer training fold and scored on the
    untouched outer test fold, so the result carries no bias from having read the test AUC
    across the grid. Fixed settings are evaluated on the SAME outer folds so the comparison
    is paired. All candidates are RF classifiers, so every score is a probability and the
    pooled AUC needs no rank correction.
    """
    y = np.asarray(y)
    outer = list(StratifiedKFold(n_splits=n_outer, shuffle=True, random_state=seed).split(X, y))

    tuned = np.zeros(len(y), dtype=float)
    picks = []
    for tr, te in outer:
        X_tr, y_tr = X.iloc[tr], y[tr]
        inner = list(StratifiedKFold(n_splits=n_inner, shuffle=True,
                                     random_state=seed).split(X_tr, y_tr))
        best_leaf, best_auc = None, -np.inf
        for leaf in grid:
            p = cross_val_predict(_pipe(make_random_forest(leaf, oob=False)),
                                  X_tr, y_tr, cv=inner, method='predict_proba')[:, 1]
            a = roc_auc_score(y_tr, p)
            if a > best_auc:
                best_leaf, best_auc = leaf, a
        pipe = _pipe(make_random_forest(best_leaf, oob=False))
        pipe.fit(X_tr, y_tr)
        tuned[te] = pipe.predict_proba(X.iloc[te])[:, 1]
        picks.append(best_leaf)

    fixed = {}
    for leaf in grid:
        oof = np.zeros(len(y), dtype=float)
        for tr, te in outer:
            pipe = _pipe(make_random_forest(leaf, oob=False))
            pipe.fit(X.iloc[tr], y[tr])
            oof[te] = pipe.predict_proba(X.iloc[te])[:, 1]
        fixed[leaf] = oof

    return tuned, picks, fixed, outer

def report_rf_tuning(X, y, label, ref=None):
    print(f"\n  RF min_samples_leaf — nested tuning ({label}):")
    tuned, picks, fixed, outer = tune_rf_leaf_nested(X, y)
    y_arr = np.asarray(y)

    def fold_mean(score):
        return np.mean([roc_auc_score(y_arr[te], score[te]) for _, te in outer])

    rows = [{'setting': f"nested-tuned {picks}", 'per-fold AUC': fold_mean(tuned),
             'pooled AUC': roc_auc_score(y_arr, tuned)}]
    for leaf, oof in fixed.items():
        tag = f"fixed leaf={leaf}" + ("  <- current default" if leaf == RF_MIN_SAMPLES_LEAF else "")
        rows.append({'setting': tag, 'per-fold AUC': fold_mean(oof),
                     'pooled AUC': roc_auc_score(y_arr, oof)})
    table = pd.DataFrame(rows)
    print(table.to_string(index=False, formatters={'per-fold AUC': '{:.3f}'.format,
                                                   'pooled AUC': '{:.3f}'.format}))
    if ref is not None:
        d, lo, hi, p = bootstrap_delta_auc(y_arr, tuned, ref)
        print(f"    nested-tuned vs OST: {d:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]  P(<= OST) {p:.3f}")
    best_fixed = max(fixed, key=lambda k: fold_mean(fixed[k]))
    print(f"    best fixed leaf by per-fold AUC: {best_fixed}   "
          f"(inner CV picked {picks})")
    return table

def evaluate_dual_target(X, df):
    print_section("STEP 12: BASELINES vs MODELS, AT BOTH CLINICAL THRESHOLDS")
    baselines = compute_baselines(df)
    t_score   = df['t_score'].to_numpy()
    targets = {
        f'OSTEOPENIA OR WORSE  (T <= {T_OSTEOPENIA})': df['at_risk'].to_numpy(),
        f'OSTEOPOROSIS         (T <= {T_OSTEOPOROSIS})': df['osteoporosis'].to_numpy(),
    }
    summary = {}
    # Both clinical thresholds share one file per result type, separated by a Target
    # column, so neither can be quoted without the reader seeing which threshold it is.
    all_compare, all_referral, all_verdict, all_tuning = [], [], [], []

    for tname, y in targets.items():
        n_pos = int(y.sum())
        print(f"\n{'-' * 102}\n  {tname}   prevalence {y.mean():.1%}  ({n_pos} events, "
              f"{n_pos / X.shape[1]:.1f} events per predictor)\n{'-' * 102}")

        folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=42).split(X, y))
        scores = dict(baselines)

        pos_weight = (y == 0).sum() / max(n_pos, 1)
        for name, model in get_model_dictionary(pos_weight).items():
            scores[name] = cross_val_predict(_pipe(model), X, y, cv=folds,
                                             method='predict_proba')[:, 1]

        # Regression arm: trained on continuous t_score, never on this binary label.
        for name, reg in get_regressor_dictionary().items():
            scores[name] = -cross_val_predict(_pipe(reg), X, t_score, cv=folds)

        ref_name = 'OST  0.2x(weight-age)'
        ref = scores[ref_name]
        rows = []
        for name, s in scores.items():
            auc = roc_auc_score(y, s)
            if name == ref_name:
                rows.append({'Model': name, 'AUC': auc, 'd_AUC vs OST': 0.0,
                             'ci_lo': np.nan, 'ci_hi': np.nan, '95% CI': '(reference)',
                             'P(<= OST)': ''})
            else:
                mean_d, lo, hi, p_le = bootstrap_delta_auc(y, s, ref)
                rows.append({'Model': name, 'AUC': auc, 'd_AUC vs OST': mean_d,
                             'ci_lo': lo, 'ci_hi': hi, '95% CI': f"[{lo:+.3f}, {hi:+.3f}]",
                             'P(<= OST)': f"{p_le:.3f}"})

        table = pd.DataFrame(rows).sort_values('AUC', ascending=False)
        print(table.drop(columns=['ci_lo', 'ci_hi']).to_string(
            index=False, formatters={'AUC': '{:.3f}'.format, 'd_AUC vs OST': '{:+.3f}'.format}))
        best = table.iloc[0]
        summary[tname] = best
        all_compare.append(table.assign(Target=tname.strip(), Events=n_pos,
                                        Prevalence=round(float(y.mean()), 4)))

        print(f"\n  Screening cost for {best['Model']} — top-fraction cutoffs:")
        ref_tbl = referral_table(y, scores[best['Model']], as_quantile=True)
        print(ref_tbl.to_string(index=False))
        # 'Cutoff' here is a TOP FRACTION of the score distribution (as_quantile=True),
        # not a probability. Renamed on the way out because step 13 saves a column
        # literally called 'Probability Cutoff' for a different model, and the two
        # columns are not comparable despite carrying the same numbers.
        all_referral.append(ref_tbl.rename(columns={'Cutoff': 'Top fraction flagged'})
                                   .assign(Target=tname.strip(), Model=best['Model']))

        # Nested CV: the same selection procedure, scored without seeing its own answer.
        nested_score, chosen, outer = nested_cv_selection(X, y, t_score)

        # Primary: mean of per-fold AUCs (each fold internally consistent, no scale issue).
        fold_nested = [roc_auc_score(y[te], nested_score[te]) for _, te in outer]
        fold_ost    = [roc_auc_score(y[te], ref[te])          for _, te in outer]
        fold_delta  = np.array(fold_nested) - np.array(fold_ost)

        # For a pooled CI, rank both scores within the same folds so they are comparable.
        n_obs = len(y)
        nested_r = rank_within_folds(nested_score, outer, n_obs)
        ost_r    = rank_within_folds(ref,          outer, n_obs)
        nested_auc = roc_auc_score(y, nested_r)
        n_d, n_lo, n_hi, n_p = bootstrap_delta_auc(y, nested_r, ost_r)

        print(f"\n  NESTED CV (selection inside each training fold, 5 outer x 3 inner):")
        print(f"    picked per fold : {', '.join(chosen)}")
        print(f"    per-fold AUC    : nested {np.mean(fold_nested):.3f} (sd {np.std(fold_nested):.3f})"
              f"   vs OST {np.mean(fold_ost):.3f} (sd {np.std(fold_ost):.3f})")
        print(f"    per-fold d_AUC  : {fold_delta.mean():+.3f}  (folds: "
              f"{', '.join(f'{d:+.3f}' for d in fold_delta)})")
        print(f"    pooled (ranked) : nested AUC {nested_auc:.3f}   "
              f"optimistic leaderboard best {best['AUC']:.3f}")
        print(f"    d_AUC vs OST    : {n_d:+.3f}  95% CI [{n_lo:+.3f}, {n_hi:+.3f}]   P(<= OST) {n_p:.3f}")
        summary[tname] = pd.concat([best, pd.Series(
            {'nested_auc': nested_auc, 'nested_d': n_d, 'nested_lo': n_lo, 'nested_hi': n_hi,
             'fold_d': fold_delta.mean()})])

        all_verdict.append({
            'Target': tname.strip(), 'Events': n_pos,
            'Prevalence': round(float(y.mean()), 4),
            'OST AUC': float(table.loc[table['Model'] == ref_name, 'AUC'].iloc[0]),
            'Optimistic best model': best['Model'],
            'Optimistic AUC': best['AUC'], 'Optimistic d_AUC': best['d_AUC vs OST'],
            'Nested AUC': nested_auc, 'Nested d_AUC': n_d,
            'Nested CI low': n_lo, 'Nested CI high': n_hi, 'P(<= OST)': n_p,
            'Nested per-fold d_AUC': fold_delta.mean(),
            'Model selected per fold': ' | '.join(chosen),
            'Verdict': ('BEATS OST' if n_lo > 0 else 'NOT separable from OST'),
        })

        all_tuning.append(report_rf_tuning(X, y, tname.strip(), ref=ref)
                          .assign(Target=tname.strip()))

    print(f"\n{'=' * 102}\n  BOTTOM LINE — incremental value over a two-variable 1985 formula\n{'=' * 102}")
    for tname, b in summary.items():
        if b['nested_lo'] > 0:
            verdict = "BEATS OST (nested 95% CI excludes zero)"
        else:
            verdict = "NOT separable from OST (nested 95% CI includes zero)"
        print(f"  {tname}")
        print(f"    optimistic best : {b['Model']}  AUC {b['AUC']:.3f}  delta {b['d_AUC vs OST']:+.3f} {b['95% CI']}")
        print(f"    nested estimate : AUC {b['nested_auc']:.3f}  delta {b['nested_d']:+.3f} "
              f"[{b['nested_lo']:+.3f}, {b['nested_hi']:+.3f}]")
        print(f"    verdict         : {verdict}")
    print(f"{'=' * 102}")
    print("  The nested row is the defensible number: model choice happened inside each")
    print("  training fold, so it carries no best-of-N selection bias.\n")

    save_csv(pd.DataFrame(all_verdict), 'nested_cv_verdict.csv', 'PRESENT')
    save_csv(pd.concat(all_referral, ignore_index=True), 'referral_table.csv', 'PRESENT')
    save_csv(pd.concat(all_compare, ignore_index=True).drop(columns=['ci_lo', 'ci_hi']),
             'baseline_comparison.csv', 'METHODS')
    save_csv(pd.concat(all_tuning, ignore_index=True), 'rf_leaf_tuning.csv', 'METHODS')
    return summary

# ================================================================================
# MAIN EXECUTION ROUTINE
# ================================================================================

def main():
    print("\n" + "=" * 60)
    print("  NHANES OSTEOPOROSIS PIPELINE — COMPLETE AUDIT")
    print("=" * 60)

    setup_directories()
    supp_df      = download_supplement_files()
    day2_df      = download_day2_dietary()
    full         = load_and_merge_cycles()
    full         = recode_refused(full)
    df           = apply_filters(full)
    df           = compute_tscores(df)
    df           = compute_derived_variables(df, supp_df, day2_df)
    df           = compute_menopause_variables(df)
    df           = recode_binary_variables(df)
    df           = rename_and_save(df)
    X_with, X_without, y = define_features(df)
    print(f"  features used: {X_without.shape[1]}  ->  {sorted(X_without.columns)}")
    
    leaderboard = train_models(X_without, y)
    
    leaderboard = leaderboard.rename(columns={
        'Model': 'Model Architecture',
        'auc': 'Test AUC-ROC',
        'train_auc': 'Train AUC-ROC',
        'oob_auc': 'OOB AUC-ROC',
        'sens': 'Sensitivity (Recall)',
        'spec': 'Specificity'
    })

    print("\n" + "="*110)
    print("🏆 FINAL COMPARATIVE STUDY LEADERBOARD")
    print("="*110)
    print(leaderboard[['Model Architecture', 'Test AUC-ROC', 'Train AUC-ROC', 'OOB AUC-ROC',
                       'Sensitivity (Recall)', 'Specificity']].to_string(index=False, na_rep='n/a', formatters={
        'Test AUC-ROC': '{:,.3f}'.format,
        'Train AUC-ROC': '{:,.3f}'.format,
        'OOB AUC-ROC': '{:,.3f}'.format,
        'Sensitivity (Recall)': '{:.1%}'.format,
        'Specificity': '{:.1%}'.format
    }))
    print("="*110)
    print("  Train AUC-ROC is in-sample. For the bagged forest it is inflated by design —")
    print("  ~63% of trees memorized each training row — so OOB AUC-ROC is its honest")
    print("  in-sample figure. Do not rank models by the train/test gap.")
    print("="*110 + "\n")

    save_csv(leaderboard[['Model Architecture', 'Test AUC-ROC', 'Train AUC-ROC', 'OOB AUC-ROC',
                          'Sensitivity (Recall)', 'Specificity', 'tn', 'fp', 'fn', 'tp']],
             'model_leaderboard.csv', 'PRESENT')

    # Step 11: coefficient diagnostic (leak + sign check; internal, not presented)
    audit_feature_weights(X_without, y)

    # Step 11b: the table and figure for the clinical collaborator
    clinical_table(X_without, y, f"osteopenia or worse (T <= {T_OSTEOPENIA})")

    # Step 12: Baselines (OST), both clinical thresholds, continuous t_score arm
    evaluate_dual_target(X_without, df)

    # Step 13: Run Threshold Optimization Experiment
    optimize_for_early_detection(X_without, y)


if __name__ == '__main__':
    main()