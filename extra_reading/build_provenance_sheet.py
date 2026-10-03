"""Build the raw-vs-computed variable provenance sheet for the specialist.

Every variable the pipeline touches, split by where it comes from:
  A  RAW, used directly        - taken from NHANES, renamed only
  B  RAW, recoded to 1/0       - a yes/no NHANES item mapped to a binary
  C  COMPUTED                  - derived by the pipeline from one or more raw items
  D  OUTCOME                   - derived from the DXA scan; never a predictor

No model is run. Coverage and distributions come from the saved analysis file.
"""
import importlib.util
import os
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('m', os.path.join(ROOT, 'OsteoporosisML.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

d = pd.read_csv(os.path.join(ROOT, 'data', 'processed', 'option_b_v4_final.csv'), low_memory=False)
_, X, y = m.define_features(d)
IN = set(X.columns)
N = len(d)

# (category, model name, NHANES source, derivation, unit, note)
ROWS = [
 # ---------------- A. raw, used directly -------------------------------
 ('A  RAW - used directly', 'age', 'RIDAGEYR', 'Used as-is (renamed only)', 'years', ''),
 ('A  RAW - used directly', 'weight_kg', 'BMXWT', 'Used as-is (renamed only)', 'kg',
  'Measured, not reported'),
 ('A  RAW - used directly', 'height_cm', 'BMXHT', 'Used as-is (renamed only)', 'cm',
  'Measured, not reported'),
 ('A  RAW - used directly', 'bmi', 'BMXBMI', 'Used as-is (renamed only)', 'kg/m2',
  'NHANES computes this; overlaps weight and height'),
 ('A  RAW - used directly', 'poverty_income_ratio', 'INDFMPIR', 'Used as-is (renamed only)',
  'ratio', 'CAPPED AT 5 by NHANES, so 5 means "5 or more"'),
 ('A  RAW - used directly', 'alcohol_drinks_day', 'ALQ130', 'Used as-is (renamed only)',
  'drinks', 'Drinks per DRINKING day, not per day. Under review'),
 ('A  RAW - used directly', 'education', 'DMDEDUC2', 'Renamed, then silently dropped',
  'category', 'Stays text, and the feature builder keeps numeric columns only'),
 ('A  RAW - used directly', 'sedentary_min_day', 'PAD680', 'Renamed, then excluded',
  'minutes/day', 'Collected then excluded from the feature set'),
 ('A  RAW - used directly', 'dietary_calcium_mg', 'DR1TCALC', 'Renamed, then excluded',
  'mg/day', 'Superseded by total_calcium_mg'),
 ('A  RAW - used directly', 'dietary_vitd_mcg', 'DR1TVD', 'Renamed, then excluded',
  'mcg/day', 'Superseded by total_vitd_mcg'),

 # ---------------- B. raw, recoded to 1/0 ------------------------------
 ('B  RAW - recoded to 1/0', 'ever_smoked', 'SMQ020',
  'recode_yesno: Yes/1 -> 1, No/2 -> 0, else missing', 'yes-no',
  'Ever/never only. No intensity or recency'),
 ('B  RAW - recoded to 1/0', 'diabetes', 'DIQ010',
  'recode_yesno on "ever told you had diabetes"', 'yes-no', ''),
 ('B  RAW - recoded to 1/0', 'any_arthritis', 'MCQ160A',
  'recode_yesno on "ever told you had arthritis"', 'yes-no',
  'ANY arthritis, not rheumatoid. QUEUED FOR REPLACEMENT'),
 ('B  RAW - recoded to 1/0', 'steroid_use', 'OSQ130',
  'recode_yesno on "ever taken steroids daily for a month or longer"', 'yes-no',
  'QUEUED FOR REMOVAL - no recency recorded anywhere in NHANES'),
 ('B  RAW - recoded to 1/0', 'ever_used_estrogen', 'RHQ540',
  'recode_yesno on "ever taken female hormones"', 'yes-no',
  'Ever/never. Duration exists unused in RHQ560Q/U'),
 ('B  RAW - recoded to 1/0', 'vigorous_activity', 'PAQ650',
  'recode_yesno on "any vigorous recreational activity in a typical week"', 'yes-no',
  'No dose. PAQ655 days and PAD660 minutes exist unused'),
 ('B  RAW - recoded to 1/0', 'prior_hip_fracture', 'OSQ010A',
  'recode_yesno on "ever fractured your hip"', 'yes-no',
  'Component of any_prior_fracture; excluded on its own (21 positives)'),
 ('B  RAW - recoded to 1/0', 'prior_spine_fracture', 'OSQ010B',
  'recode_yesno on "ever fractured your spine"', 'yes-no',
  'Component of any_prior_fracture; excluded on its own'),
 ('B  RAW - recoded to 1/0', 'prior_wrist_fracture', 'OSQ010C',
  'recode_yesno on "ever fractured your wrist"', 'yes-no',
  'Component of any_prior_fracture; excluded on its own (46 positives)'),
 ('B  RAW - recoded to 1/0', 'hysterectomy', 'RHD280',
  'recode_yesno on "had a hysterectomy"', 'yes-no',
  'REMOVED from the model on your advice'),
 ('B  RAW - recoded to 1/0', 'oophorectomy', 'RHQ305',
  'recode_yesno on "had both ovaries removed"', 'yes-no',
  'Age at surgery exists unused in RHQ332'),

 # ---------------- C. computed -----------------------------------------
 ('C  COMPUTED', 'postmenopausal', 'RHQ031',
  '1 minus recode_yesno(any period in the last 12 months) - so 1 = no period in 12 months',
  'yes-no', 'This IS the simple binary menopause variable'),
 ('C  COMPUTED', 'age_at_menopause', 'RHQ060',
  'Age at last menstrual period, kept only if between 20 and 70', 'years',
  'EXCLUDED from features: age = age_at_menopause + years_since_menopause exactly'),
 ('C  COMPUTED', 'years_since_menopause', 'RHQ060 + RIDAGEYR',
  'Current age minus age at last period; negative values set to missing', 'years',
  'Corrupted for hysterectomy patients, who report surgery age as their last period'),
 ('C  COMPUTED', 'menopause_natural', 'RHD042 (2005-2010) + RHD043 (2013+)',
  'Text of "reason periods stopped" parsed: contains menopause/change of life -> 1, '
  'contains hysterectomy -> 0', 'yes-no',
  'Same source item as hysterectomy, so partly redundant'),
 ('C  COMPUTED', 'any_prior_fracture', 'OSQ010A + OSQ010B + OSQ010C',
  '1 if ANY site reported yes; 0 only if ALL three answered no; otherwise missing',
  'yes-no', 'No age restriction, so childhood fractures count. UNDER REVIEW'),
 ('C  COMPUTED', 'phq9_score', 'DPQ010 - DPQ090',
  'Nine items clipped to 0-3 and summed, min_count=5 so under five answers gives missing',
  'score 0-27', '80.4% missing'),
 ('C  COMPUTED', 'serum_vitd_nmol', 'LBXVIDMS + LBDVIDMS',
  'LBXVIDMS where present, otherwise LBDVIDMS (NHANES renamed it mid-study)', 'nmol/L',
  'Measured lab value. Absent for 2017-2020'),
 ('C  COMPUTED', 'sleep_hrs', 'SLD012 + SLD010H',
  'SLD012 where present, otherwise SLD010H', 'hours',
  'EXCLUDED. Recorded for 1,478 of 1,484 - excluded on a false sparsity premise'),
 ('C  COMPUTED', 'sleep_risk', 'sleep_hrs',
  '1 if sleep_hrs < 7, else 0; missing if sleep_hrs missing', 'yes-no',
  'EXCLUDED. Built but never trained on'),
 ('C  COMPUTED', 'supp_calcium_mg', 'DSQTCALC',
  'Supplement calcium; 0-filled ONLY for women present in a DSQTOT file, else missing',
  'mg/day', 'EXCLUDED as a component; feeds total_calcium_mg'),
 ('C  COMPUTED', 'supp_vitd_mcg', 'DSQTVD',
  'Supplement vitamin D; same scoped 0-fill', 'mcg/day',
  'EXCLUDED as a component; feeds total_vitd_mcg'),
 ('C  COMPUTED', 'supp_data_available', 'DSQTOT file presence',
  '1 if her survey cycle shipped a supplement file at all, else 0', 'yes-no',
  'NOT a patient characteristic - a dataset provenance flag. Recommend removal'),
 ('C  COMPUTED', 'dietary_calcium_mg_2day', 'DR1TCALC + DR2TCALC',
  'Mean of the two 24-hour recalls', 'mg/day', 'EXCLUDED; feeds total_calcium_mg'),
 ('C  COMPUTED', 'dietary_vitd_mcg_2day', 'DR1TVD + DR2TVD',
  'Mean of the two 24-hour recalls', 'mcg/day', 'EXCLUDED; feeds total_vitd_mcg'),
 ('C  COMPUTED', 'n_recall_days', 'DR1TCALC + DR2TCALC',
  'Count of non-missing recall days (0, 1 or 2)', 'count',
  'EXCLUDED - describes survey response, not the woman'),
 ('C  COMPUTED', 'total_calcium_mg', 'dietary 2-day mean + supplement',
  'Plain addition, so a missing component gives a missing total (never a fabricated one)',
  'mg/day', 'No association with the outcome'),
 ('C  COMPUTED', 'total_vitd_mcg', 'dietary 2-day mean + supplement',
  'Plain addition, same rule', 'mcg/day',
  'No association, and trips the clinical sign check'),

 # ---------------- D. outcome ------------------------------------------
 ('D  OUTCOME - never a predictor', 'femoral_neck_bmd', 'DXXNKBMD',
  'Used as-is (renamed only)', 'g/cm2', 'Source of the outcome. Excluded from features'),
 ('D  OUTCOME - never a predictor', 'total_hip_bmd', 'DXXOFBMD',
  'Used as-is (renamed only)', 'g/cm2', 'Source of the outcome. Excluded from features'),
 ('D  OUTCOME - never a predictor', 't_femoral_neck', 'DXXNKBMD',
  '(BMD - 0.858) / 0.120, NHANES III young-adult reference', 'SD', 'Excluded'),
 ('D  OUTCOME - never a predictor', 't_total_hip', 'DXXOFBMD',
  '(BMD - 0.942) / 0.122, NHANES III young-adult reference', 'SD', 'Excluded'),
 ('D  OUTCOME - never a predictor', 't_score', 't_femoral_neck + t_total_hip',
  'The LOWER of the two sites, rounded to 3 decimals', 'SD',
  'Clinical convention classifies by the worst site'),
 ('D  OUTCOME - never a predictor', 'at_risk', 't_score',
  '1 if t_score <= -1.0 (osteopenia or worse)', 'yes-no',
  'THE PRIMARY TARGET the models are trained to predict'),
 ('D  OUTCOME - never a predictor', 'osteoporosis', 't_score',
  '1 if t_score <= -2.5 (WHO threshold)', 'yes-no', 'Secondary target'),
 ('D  OUTCOME - never a predictor', 'bone_status', 't_score',
  'Three-level label: Normal / Low Bone Mass / Osteoporosis', 'category',
  'Descriptive only'),
]


def summarise(col):
    if col not in d.columns:
        return '', '', 'not in the saved file'
    s = d[col]
    n = int(s.notna().sum())
    if n == 0:
        return 0, '100.0%', ''
    num = pd.to_numeric(s, errors='coerce')
    if num.notna().sum() > 0.6 * n:
        u = set(np.unique(num.dropna()))
        if u <= {0.0, 1.0}:
            dist = f'{int((num == 1).sum())} yes / {int((num == 0).sum())} no'
        else:
            dist = (f'min {num.min():g} / median {num.median():g} / '
                    f'p90 {num.quantile(.9):g} / max {num.max():g}')
    else:
        vc = s.dropna().astype(str).value_counts().head(3)
        dist = '; '.join(f'{k}={v}' for k, v in vc.items())
    return n, f'{100*(1-n/N):.1f}%', dist


rows = []
for cat, name, src, deriv, unit, note in ROWS:
    n, missing, dist = summarise(name)
    if name in IN:
        status = 'YES - trained on'
    elif cat.startswith('D'):
        status = 'no - this is the outcome'
    else:
        status = 'no - built but excluded'
    rows.append({
        'Source type': cat,
        'Variable name in the model': name,
        'Raw NHANES variable(s)': src,
        'How it is derived': deriv,
        'Unit': unit,
        'Used to train the models?': status,
        'Women with a value (of 1,484)': n,
        'Missing': missing,
        'Distribution in the cohort': dist,
        'Note': note,
        'SPECIALIST DECISION (use / drop / redefine)': '',
        'Specialist comments': '',
    })
sheet = pd.DataFrame(rows)
p = os.path.join(ROOT, 'extra_reading', 'specialist_variable_provenance.csv')
sheet.to_csv(p, index=False)

print(f'  specialist_variable_provenance.csv: {len(sheet)} variables\n')
print(sheet.groupby('Source type')['Variable name in the model'].count().to_string())
print()
print('  used to train the models:')
print(sheet['Used to train the models?'].value_counts().to_string())
print()
trained = sheet[sheet['Used to train the models?'] == 'YES - trained on']
print(f'  the {len(trained)} trained-on variables, by provenance:')
for cat, grp in trained.groupby('Source type'):
    print(f'    {cat}: {", ".join(sorted(grp["Variable name in the model"]))}')
