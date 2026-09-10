"""Build the specialist decision sheet + the complete-case trade-off table.

  specialist_decision_sheet.csv        every variable - currently used or
                                       candidate - with coverage, distribution,
                                       caution, and an empty decision column
  specialist_completecase_tradeoff.csv how many women survive as more variables
                                       are required to be non-missing
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
IN_MODEL = set(X.columns)
ex = pd.read_csv(os.path.join(ROOT, 'Notes', 'specialist_data_extract.csv'), low_memory=False)

# group, readable, model column (or None), NHANES source, question, unit, caution
V = [
 ('Body measurement', 'Weight', 'weight_kg', 'BMXWT', 'Measured body weight', 'kg',
  'Most predictive single variable in the study - shuffling it costs 0.098 AUC'),
 ('Body measurement', 'Height', 'height_cm', 'BMXHT', 'Measured standing height', 'cm', ''),
 ('Body measurement', 'BMI', 'bmi', 'BMXBMI', 'Body mass index', 'kg/m2',
  'Shares most of its information with weight and height'),
 ('Demographic', 'Age', 'age', 'RIDAGEYR', 'Age at screening', 'years',
  'Complete. One of only five significant predictors (OR 1.30 per 5 years)'),

 ('Reproductive', 'Postmenopausal', 'postmenopausal', 'RHQ031',
  'Derived: no menstrual period in the last 12 months', 'yes-no',
  'Significant - OR 2.13. One of the five'),
 ('Reproductive', 'Years since menopause', 'years_since_menopause', 'RHQ060 + age',
  'Derived: current age minus age at last menstrual period', 'years',
  'Corrupted for hysterectomy patients, who report surgery age as their last period'),
 ('Reproductive', 'Bilateral oophorectomy', 'oophorectomy', 'RHQ305',
  'Both ovaries surgically removed', 'yes-no',
  'OR 1.30 but not significant. 200 of 206 also had a hysterectomy'),
 ('Reproductive', 'Natural menopause', 'menopause_natural', 'RHD042 / RHD043',
  'Derived from the stated reason periods stopped', 'yes-no',
  'Derived from the same item as hysterectomy, so partly redundant'),
 ('Reproductive', 'Ever used oestrogen / HRT', 'ever_used_estrogen', 'RHQ540',
  'Ever taken female hormones', 'yes-no',
  'Significant and protective - OR 0.58. Crude ever/never; duration is available unused'),
 ('Reproductive', 'Hysterectomy', None, 'RHD280', 'Uterus surgically removed', 'yes-no',
  'REMOVED on your advice - no mechanism without oophorectomy, and OR was 0.96'),
 ('Reproductive', 'Age at oophorectomy', None, 'RHQ332',
  'Age when both ovaries were removed', 'years',
  'CANDIDATE, 5 of 6 cycles. Would give years of oestrogen deficiency'),
 ('Reproductive', 'Duration of HRT use', None, 'RHQ560Q + RHQ560U',
  'How long female hormones were taken', 'years',
  'CANDIDATE, 5 of 6 cycles. Would sharpen the strongest protective predictor'),

 ('Fracture history', 'Any prior fracture', 'any_prior_fracture', 'OSQ010A/B/C',
  'Ever fractured hip, spine or wrist - at ANY age', 'yes-no',
  'Significant - OR 1.72. Includes childhood fractures; you asked for a 5-year window'),
 ('Fracture history', 'Age at each fracture', None, 'OSD030AA..CJ',
  'Age at every individual fracture, all sites', 'years',
  'CANDIDATE, all 6 cycles. Makes the 5-year window computable. Currently unused'),
 ('Fracture history', 'Fracture mechanism', None, 'OSQ040AA..',
  'Per-fracture follow-up, possibly trauma vs low-trauma', 'code',
  'CANDIDATE - would isolate fragility fractures. Wording needs codebook confirmation'),
 ('Fracture history', 'Mother fractured her hip', None, 'OSQ170',
  'Did her mother ever fracture her hip', 'yes-no',
  'CANDIDATE, all 6 cycles. A core FRAX risk factor. Currently unused'),
 ('Fracture history', 'Relative had osteoporosis', None, 'OSQ150',
  'Any close biological relative told they had osteoporosis', 'yes-no',
  'CANDIDATE, all 6 cycles. Currently unused'),

 ('Medication / comorbidity', 'Long-term steroid use', 'steroid_use', 'OSQ130',
  'Ever taken prednisone or cortisone daily for a month or longer', 'yes-no',
  'QUEUED FOR REMOVAL - no recency in NHANES, and >3 months gives only +1.8pp'),
 ('Medication / comorbidity', 'Steroid duration', None, 'OSQ140Q + OSQ140U',
  'How long steroids were taken', 'months',
  'Duration only. NHANES never records WHEN, so your 5-year rule cannot apply'),
 ('Medication / comorbidity', 'Arthritis (any type)', 'any_arthritis', 'MCQ160A',
  'Ever told by a doctor she had arthritis of any type', 'yes-no',
  'QUEUED FOR REPLACEMENT - 45.8% prevalence, not the FRAX risk factor'),
 ('Medication / comorbidity', 'Rheumatoid arthritis', None, 'MCQ190 / MCQ195',
  'Which type of arthritis - isolates rheumatoid', 'yes-no',
  'CANDIDATE, 5 of 6 cycles. 54 women (3.6%), +8.8pp. This IS the FRAX factor'),
 ('Medication / comorbidity', 'Diabetes', 'diabetes', 'DIQ010',
  'Ever told by a doctor she had diabetes', 'yes-no', ''),

 ('Lifestyle', 'Ever smoked', 'ever_smoked', 'SMQ020',
  'Smoked at least 100 cigarettes in her life', 'yes-no',
  'Ever/never only - no intensity or recency, and OR is 1.03'),
 ('Lifestyle', 'Alcohol drinks per drinking day', 'alcohol_drinks_day', 'ALQ130',
  'Average drinks on the days she drank, past 12 months', 'drinks',
  'NOT daily intake. 384 of the 470 blanks are non-drinkers imputed as drinkers'),
 ('Lifestyle', 'Alcohol drinking frequency', None, 'ALQ120Q+U / ALQ121',
  'How often she drank in the past 12 months', 'days/year',
  'CANDIDATE, all 6 cycles. Needed to compute true daily intake. Unused'),
 ('Lifestyle', 'Heavy drinking (>= 3/day)', None, 'derived',
  'Average daily intake at or above the FRAX threshold', 'yes-no',
  'CANDIDATE. Only 20 women, but +24.9pp - the largest crude gap in the study'),
 ('Lifestyle', 'Vigorous activity (any)', 'vigorous_activity', 'PAQ650',
  'Any vigorous recreational activity in a typical week', 'yes-no',
  'Bare yes/no with NO dose. Absent for all of 2005-2006'),
 ('Lifestyle', 'Vigorous activity dose', None, 'PAQ655 + PAD660',
  'Days per week and minutes per session', 'minutes/week',
  'CANDIDATE, 5 of 6 cycles. Median is 3 days x 60 min = 180 min/week. Unused'),
 ('Lifestyle', 'Moderate activity dose', None, 'PAQ665/670 + PAD675',
  'Same three questions for moderate-intensity activity', 'minutes/week',
  'CANDIDATE, 5 of 6 cycles. 577 women, median 140 min/week. Entirely unused'),
 ('Lifestyle', 'Sedentary time', None, 'PAD680', 'Minutes sitting on a typical day',
  'minutes/day', 'Collected then excluded. Median 360 min/day'),
 ('Lifestyle', 'Sleep hours per night', None, 'SLD010H / SLD012',
  'Hours of sleep on a usual weeknight', 'hours',
  'CANDIDATE. Recorded for 1,478 of 1,484 - NOT sparse. Excluded on a false premise'),
 ('Lifestyle', 'Trouble sleeping (told a doctor)', None, 'SLQ050',
  'Ever told a doctor she had trouble sleeping', 'yes-no',
  'CANDIDATE, all 6 cycles, complete. Unused'),

 ('Diet and supplements', 'Total calcium', 'total_calcium_mg', 'DR1/DR2TCALC + DSQTCALC',
  'Two-day dietary average plus supplement intake', 'mg/day',
  'No association - OR 1.01 (0.90-1.11)'),
 ('Diet and supplements', 'Total vitamin D', 'total_vitd_mcg', 'DR1/DR2TVD + DSQTVD',
  'Two-day dietary average plus supplement intake', 'mcg/day',
  'No association, and trips the sign check - likely reverse causation'),
 ('Diet and supplements', 'Supplement data available', 'supp_data_available', 'derived',
  'Whether her survey cycle shipped a supplement file at all', 'yes-no',
  'NOT a patient characteristic - a dataset provenance flag. Recommend removal'),
 ('Diet and supplements', 'Took any supplement', None, 'DSD010',
  'Any supplement in the past 30 days', 'yes-no',
  'CANDIDATE. The gate that identifies TRUE non-users. Unused'),
 ('Diet and supplements', 'Number of supplements', None, 'DSDCOUNT',
  'How many different supplements reported', 'count', 'CANDIDATE. Unused'),
 ('Diet and supplements', 'Dietary recall reliable', None, 'DR1DRSTZ',
  'Interviewer flag - did the recall meet reliability criteria', 'category',
  'CANDIDATE as an EXCLUSION filter. Unreliable recalls are currently averaged in'),
 ('Diet and supplements', 'Total energy intake', None, 'DR1TKCAL',
  'Total calories from the day-1 recall', 'kcal/day',
  'CANDIDATE. Nutrient intake is normally energy-adjusted'),

 ('Laboratory', 'Serum 25(OH) vitamin D', 'serum_vitd_nmol', 'LBXVIDMS / LBDVIDMS',
  'Measured blood 25-hydroxyvitamin D', 'nmol/L',
  'Measured, not reported. No association - OR 0.94. Absent for 2017-2020'),

 ('Social', 'Poverty income ratio', 'poverty_income_ratio', 'INDFMPIR',
  'Family income divided by the federal poverty threshold', 'ratio',
  'Significant and protective - OR 0.91. CAPPED AT 5, so 5 means "5 or more"'),
 ('Social', 'Family income band', None, 'INDHHIN2 / INDFMINC',
  'Household income as a banded category', 'category', 'CANDIDATE. Unused'),
 ('Social', 'Education level', None, 'DMDEDUC2', 'Highest education completed', 'category',
  'Collected but SILENTLY DROPPED - stays text, and the model keeps numbers only'),

 ('Mood', 'PHQ-9 depression score', 'phq9_score', 'DPQ010-DPQ090',
  'Nine-item depression screen, summed', 'score 0-27',
  '80.4% MISSING. Contributes negatively. Alone it makes complete-case analysis impossible'),
]

EXTRACT_COL = {
 'Sleep hours per night': 'Sleep: hours per night',
 'Trouble sleeping (told a doctor)': 'Sleep: told a doctor about trouble sleeping',
 'Vigorous activity dose': 'Vigorous activity: total minutes per week',
 'Moderate activity dose': 'Moderate activity: total minutes per week',
 'Sedentary time': 'Sedentary time: minutes per day',
 'Mother fractured her hip': 'Family history: mother fractured hip',
 'Age at each fracture': 'Prior fracture: age at most recent (any site)',
 'Alcohol drinking frequency': 'Alcohol: drinking days per year',
 'Took any supplement': 'Supplements: took any in past 30 days',
 'Number of supplements': 'Supplements: number taken',
 'Total energy intake': 'Total energy intake day 1 (kcal)',
 'Dietary recall reliable': 'Dietary recall day 1 reliable',
 'Family income band': 'Annual family income (band)',
 'Education level': 'Education level',
 'Steroid duration': 'Steroids: total months taken',
 'Hysterectomy': None,
}


def summarise(series):
    n = int(series.notna().sum())
    if n == 0:
        return n, ''
    num = pd.to_numeric(series, errors='coerce')
    if num.notna().sum() > 0.6 * n:
        if set(np.unique(num.dropna())) <= {0.0, 1.0}:
            return n, f'{int((num == 1).sum())} yes / {int((num == 0).sum())} no'
        return n, (f'min {num.min():g} / median {num.median():g} / '
                   f'p90 {num.quantile(.9):g} / max {num.max():g}')
    vc = series.dropna().astype(str).value_counts().head(3)
    return n, '; '.join(f'{k}={v}' for k, v in vc.items())


rows = []
for grp, name, col, src, question, unit, caution in V:
    if col and col in X.columns:
        status = 'YES - in the model now'
        n, dist = summarise(X[col])
    else:
        status = ('REMOVED' if 'REMOVED' in caution
                  else 'QUEUED' if 'QUEUED' in caution
                  else 'no - candidate')
        ecol = EXTRACT_COL.get(name)
        if ecol and ecol in ex.columns:
            n, dist = summarise(ex[ecol])
        elif col and col in d.columns:
            n, dist = summarise(d[col])
        else:
            n, dist = '', 'see data extract'
    pc = f'{100*(1-n/len(d)):.1f}%' if isinstance(n, int) and n else ''
    rows.append({
        'Group': grp,
        'Variable': name,
        'Currently used for modelling': status,
        'NHANES source': src,
        'What the question asks': question,
        'Unit': unit,
        'Women with a value (of 1,484)': n,
        'Missing': pc,
        'Distribution in the cohort': dist,
        'Caution / note': caution,
        'SPECIALIST DECISION (include / exclude / redefine)': '',
        'Specialist comments': '',
    })
sheet = pd.DataFrame(rows)
p1 = os.path.join(ROOT, 'Notes', 'specialist_decision_sheet.csv')
sheet.to_csv(p1, index=False)
print(f'  specialist_decision_sheet.csv: {len(sheet)} variables '
      f'({int((sheet["Currently used for modelling"] == "YES - in the model now").sum())} '
      f'currently used, {int((sheet["Currently used for modelling"] == "no - candidate").sum())} candidates)')

# ------------------------------------------------------- complete-case curve
order = X.isna().mean().sort_values(ascending=False)
rows2, kept = [], list(X.columns)
for i, var in enumerate(order.index):
    n = int(X[kept].notna().all(axis=1).sum())
    sub = X[kept].notna().all(axis=1)
    rows2.append({
        'Variables required to be complete': len(kept),
        'Most-missing variable still required': var,
        'Its missing %': round(order[var] * 100, 1),
        'Women retained': n,
        '% of 1,484 retained': round(100 * n / len(X), 1),
        'Low bone mass in that subset': f'{y[sub].mean():.1%}' if n else '',
        'Prevalence shift vs full cohort': (f'{100*(y[sub].mean()-y.mean()):+.1f}pp'
                                            if n else ''),
    })
    kept.remove(var)
    if len(kept) < 6:
        break
cc = pd.DataFrame(rows2)
p2 = os.path.join(ROOT, 'Notes', 'specialist_completecase_tradeoff.csv')
cc.to_csv(p2, index=False)
print(f'  specialist_completecase_tradeoff.csv: {len(cc)} rows')
print()
print(cc.to_string(index=False))
