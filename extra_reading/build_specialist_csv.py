"""Build two CSVs for the osteoporosis specialist to inspect before advising.

  specialist_data_extract.csv     1,484 rows - one per woman, readable headers,
                                  RAW questionnaire values as downloaded
  specialist_variable_reference.csv  one row per variable - what it asks, which
                                  cycles carry it, cohort coverage, distribution

Values are read straight from data/raw/ and cleaned only by removing each
variable's OWN implausible sentinel codes. In particular 7 and 9 are kept where
they are real answers (7 hours of sleep, 7 drinks, 7 days a week) - the pipeline
currently deletes them, which is the bug this extract documents.
"""
import glob
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

d = pd.read_csv(os.path.join(ROOT, 'data', 'processed', 'option_b_v4_final.csv'),
                low_memory=False)
X = d[['SEQN', 'survey_cycle', 'age', 't_score', 'at_risk']].copy()


def gather(mod, cols):
    frames, cyc_seen = [], {}
    for cy in m.CYCLES:
        fn = f"{cy['prefix']}{mod}.csv" if cy['prefix'] else f"{mod}_{cy['suffix']}.csv"
        f = glob.glob(os.path.join(ROOT, 'data', 'raw', cy['name'], fn))
        if not f:
            continue
        t = pd.read_csv(f[0], low_memory=False)
        keep = [c for c in cols if c in t.columns]
        for c in keep:
            cyc_seen.setdefault(c, []).append(cy['name'][:4])
        if keep:
            frames.append(t[['SEQN'] + keep])
    got = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=['SEQN'])
    return got, cyc_seen


CYCLES_OF = {}


def pull(mod, cols):
    g, seen = gather(mod, cols)
    CYCLES_OF.update(seen)
    if g.empty:
        return pd.DataFrame({'SEQN': X.SEQN})
    return g.groupby('SEQN', as_index=False).first()


def numr(frame, col, lo, hi):
    """Numeric within a variable's OWN plausible range; underflow zero repaired."""
    if col not in frame.columns:
        return pd.Series(np.nan, index=frame.index)
    v = pd.to_numeric(frame[col], errors='coerce')
    v = v.mask(v.notna() & (v.abs() < 1e-30), 0.0)
    return v.where(v.between(lo, hi))


def ynum(frame, col):
    if col not in frame.columns:
        return pd.Series(np.nan, index=frame.index)
    s = frame[col].astype(str).str.strip().str.lower()
    return pd.Series(np.where(s.isin(['yes', '1', '1.0']), 1.0,
                     np.where(s.isin(['no', '2', '2.0']), 0.0, np.nan)), index=frame.index)


# ---------------------------------------------------------------- assemble
osq = pull('OSQ', ['OSQ010A', 'OSQ010B', 'OSQ010C', 'OSQ130', 'OSQ140Q', 'OSQ140U',
                   'OSQ170', 'OSQ150']
           + [f'OSD030{a}{b}' for a in 'ABC' for b in 'ABCDEFGHIJ'])
alq = pull('ALQ', ['ALQ101', 'ALQ110', 'ALQ111', 'ALQ120Q', 'ALQ120U', 'ALQ121', 'ALQ130'])
paq = pull('PAQ', ['PAQ650', 'PAQ655', 'PAD660', 'PAQ665', 'PAQ670', 'PAD675', 'PAD680'])
slq = pull('SLQ', ['SLD010H', 'SLD012', 'SLQ050'])
dsq = pull('DSQTOT', ['DSQTCALC', 'DSQTVD', 'DSDCOUNT', 'DSD010'])
dr1 = pull('DR1TOT', ['DR1TCALC', 'DR1TVD', 'DR1TKCAL', 'DR1DRSTZ'])
dr2 = pull('DR2TOT', ['DR2TCALC', 'DR2TVD'])
dem = pull('DEMO', ['INDFMPIR', 'INDFMINC', 'INDHHIN2', 'DMDEDUC2'])

for f in (osq, alq, paq, slq, dsq, dr1, dr2, dem):
    X = X.merge(f, on='SEQN', how='left')

out = pd.DataFrame()
out['Participant ID'] = X.SEQN
out['Survey cycle'] = X.survey_cycle
out['Age (years)'] = X.age
out['DXA T-score (lowest of 2 hip sites)'] = X.t_score
out['Low bone mass (T <= -1.0)'] = X.at_risk.map({1: 'Yes', 0: 'No'})

# ---- alcohol -------------------------------------------------------------
ever = pd.Series(np.nan, index=X.index)
for col in ('ALQ101', 'ALQ111'):
    ever = ever.fillna(ynum(X, col))
per_occ = numr(X, 'ALQ130', 1, 40)
q = numr(X, 'ALQ120Q', 0, 400)
u = X['ALQ120U'].astype(str).str.strip().str.lower() if 'ALQ120U' in X else pd.Series('', index=X.index)
days = pd.Series(np.nan, index=X.index)
days[u.str.startswith('week')] = q * 52
days[u.str.startswith('month')] = q * 12
days[u.str.startswith('year')] = q
days[q == 0] = 0.0
FREQ = {0: 0, 1: 365, 2: 300, 3: 200, 4: 130, 5: 90, 6: 50, 7: 30, 8: 10, 9: 4, 10: 1.5}
days = days.fillna(numr(X, 'ALQ121', 0, 99).map(FREQ))
out['Alcohol: ever drank'] = ever.map({1.0: 'Yes', 0.0: 'No'})
out['Number of alcohol drinks per drinking day'] = per_occ
out['Alcohol: drinking days per year'] = days.round(0)
out['Alcohol: average drinks per day'] = ((per_occ * days) / 365).round(3)

# ---- prior fracture ------------------------------------------------------
for site, code, pref in [('hip', 'OSQ010A', 'OSD030A'), ('spine', 'OSQ010B', 'OSD030B'),
                         ('wrist', 'OSQ010C', 'OSD030C')]:
    cols = [c for c in X.columns if c.startswith(pref)]
    out[f'Prior fracture: ever {site}'] = ynum(X, code).map({1.0: 'Yes', 0.0: 'No'})
    if cols:
        a = X[cols].apply(pd.to_numeric, errors='coerce')
        a = a.where((a >= 1) & (a <= 95))          # DataFrame has no .between
        out[f'Prior fracture: age at first {site}'] = a.min(axis=1)
        out[f'Prior fracture: age at most recent {site}'] = a.max(axis=1)
    else:
        out[f'Prior fracture: age at first {site}'] = np.nan
        out[f'Prior fracture: age at most recent {site}'] = np.nan

allages = X[[c for c in X.columns if c.startswith('OSD030')]] \
    .apply(pd.to_numeric, errors='coerce')
allages = allages.where((allages >= 1) & (allages <= 95))
recent = allages.max(axis=1)
out['Prior fracture: age at most recent (any site)'] = recent
out['Prior fracture: years since most recent'] = (X.age - recent).round(0)
out['Prior fracture: within last 5 years'] = np.where(
    allages.ge(X.age - 5, axis=0).any(axis=1), 'Yes', 'No')
out['Prior fracture: within last 10 years'] = np.where(
    allages.ge(X.age - 10, axis=0).any(axis=1), 'Yes', 'No')
out['Family history: mother fractured hip'] = ynum(X, 'OSQ170').map({1.0: 'Yes', 0.0: 'No'})

# ---- steroids ------------------------------------------------------------
sq = numr(X, 'OSQ140Q', 0, 500)
su = X['OSQ140U'].astype(str).str.strip().str.lower() if 'OSQ140U' in X else pd.Series('', index=X.index)
mon = pd.Series(np.nan, index=X.index)
mon[su.str.startswith('day')] = sq / 30
mon[su.str.startswith('week')] = sq / 4.345
mon[su.str.startswith('month')] = sq
mon[su.str.startswith('year')] = sq * 12
out['Steroids: ever daily for a month or more'] = ynum(X, 'OSQ130').map({1.0: 'Yes', 0.0: 'No'})
out['Steroids: total months taken'] = mon.round(1)

# ---- activity ------------------------------------------------------------
vd, vm = numr(X, 'PAQ655', 1, 7), numr(X, 'PAD660', 1, 1200)
md, mm = numr(X, 'PAQ670', 1, 7), numr(X, 'PAD675', 1, 1200)
out['Vigorous activity: any in a typical week'] = ynum(X, 'PAQ650').map({1.0: 'Yes', 0.0: 'No'})
out['Vigorous activity: days per week'] = vd
out['Vigorous activity: minutes per session'] = vm
out['Vigorous activity: total minutes per week'] = (vd * vm)
out['Moderate activity: any in a typical week'] = ynum(X, 'PAQ665').map({1.0: 'Yes', 0.0: 'No'})
out['Moderate activity: days per week'] = md
out['Moderate activity: minutes per session'] = mm
out['Moderate activity: total minutes per week'] = (md * mm)
out['Sedentary time: minutes per day'] = numr(X, 'PAD680', 0, 1320)

# ---- sleep ---------------------------------------------------------------
sleep = numr(X, 'SLD010H', 1, 20).fillna(numr(X, 'SLD012', 1, 20))
out['Sleep: hours per night'] = sleep
out['Sleep: told a doctor about trouble sleeping'] = ynum(X, 'SLQ050').map({1.0: 'Yes', 0.0: 'No'})

# ---- calcium / vitamin D -------------------------------------------------
out['Supplements: took any in past 30 days'] = ynum(X, 'DSD010').map({1.0: 'Yes', 0.0: 'No'})
out['Supplements: number taken'] = numr(X, 'DSDCOUNT', 0, 60)
out['Supplement calcium (mg/day)'] = numr(X, 'DSQTCALC', 0, 9000)
out['Supplement vitamin D (mcg/day)'] = numr(X, 'DSQTVD', 0, 3000)
out['Dietary calcium day 1 (mg)'] = numr(X, 'DR1TCALC', 0, 9000)
out['Dietary calcium day 2 (mg)'] = numr(X, 'DR2TCALC', 0, 9000)
out['Dietary vitamin D day 1 (mcg)'] = numr(X, 'DR1TVD', 0, 500)
out['Dietary vitamin D day 2 (mcg)'] = numr(X, 'DR2TVD', 0, 500)
out['Dietary recall day 1 reliable'] = X['DR1DRSTZ'].astype(str).str.slice(0, 34) \
    if 'DR1DRSTZ' in X else np.nan
out['Total energy intake day 1 (kcal)'] = numr(X, 'DR1TKCAL', 0, 12000)

# ---- socioeconomic -------------------------------------------------------
out['Poverty income ratio (0 = at poverty line, 5 = capped)'] = numr(X, 'INDFMPIR', 0, 5)
inc = pd.Series(np.nan, index=X.index, dtype=object)
for col in ('INDHHIN2', 'INDFMINC'):
    if col in X.columns:
        inc = inc.fillna(X[col].astype(object))
out['Annual family income (band)'] = inc
out['Education level'] = X['DMDEDUC2'] if 'DMDEDUC2' in X else np.nan

p1 = os.path.join(ROOT, 'extra_reading', 'specialist_data_extract.csv')
out.to_csv(p1, index=False)
print(f'  {os.path.basename(p1)}: {len(out)} rows x {out.shape[1]} columns')

# ==========================================================================
# reference sheet
# ==========================================================================
DESC = [
 ('Number of alcohol drinks per drinking day', 'ALQ130',
  'Average number of drinks on the days she drank, past 12 months',
  'drinks', 'NOT average daily intake - 4 monthly and 4 daily both record as 4'),
 ('Alcohol: drinking days per year', 'ALQ120Q+ALQ120U / ALQ121',
  'How often she drank in the past 12 months', 'days/year',
  'Currently UNUSED. Needed to turn drinks-per-occasion into daily intake'),
 ('Alcohol: average drinks per day', 'derived',
  'Drinks per drinking day x drinking days per year / 365', 'drinks/day',
  'Derived here for review. 20 women reach 3/day (the FRAX threshold)'),
 ('Prior fracture: ever hip / spine / wrist', 'OSQ010A/B/C',
  'Has a hip / spine / wrist ever been fractured', 'yes-no',
  'What the model uses now. No age restriction, so childhood fractures count'),
 ('Prior fracture: age at first / most recent', 'OSD030AA..CJ',
  'Age at each individual fracture, up to 5 hip and 10 each spine and wrist',
  'years', 'Currently UNUSED. Makes any recency rule computable'),
 ('Family history: mother fractured hip', 'OSQ170',
  'Did her mother ever fracture her hip', 'yes-no',
  'Currently UNUSED. A core FRAX risk factor'),
 ('Steroids: ever daily for a month or more', 'OSQ130',
  'Ever taken prednisone or cortisone daily for a month or longer', 'yes-no',
  'What the model uses now'),
 ('Steroids: total months taken', 'OSQ140Q+OSQ140U',
  'How long they were taken', 'months',
  'Duration only - NHANES never records WHEN, so a 5-year rule is impossible'),
 ('Vigorous activity: any in a typical week', 'PAQ650',
  'Any vigorous-intensity recreational activity in a typical week', 'yes-no',
  'What the model uses now - a bare yes/no with NO dose'),
 ('Vigorous activity: days per week', 'PAQ655',
  'Days per week of vigorous recreational activity', 'days',
  'Currently UNUSED - this is the missing dose'),
 ('Vigorous activity: minutes per session', 'PAD660',
  'Minutes of vigorous recreational activity on those days', 'minutes',
  'Currently UNUSED - this is the missing dose'),
 ('Vigorous activity: total minutes per week', 'derived',
  'Days per week x minutes per session', 'minutes/week',
  'Derived here so intensity can be compared against guideline thresholds'),
 ('Moderate activity: total minutes per week', 'PAQ665/670 + PAD675',
  'Same three questions for moderate-intensity activity', 'minutes/week',
  'Entirely UNUSED. Weight-bearing moderate activity may matter more for bone'),
 ('Sedentary time: minutes per day', 'PAD680',
  'Minutes spent sitting on a typical day', 'minutes/day',
  'Collected then excluded from the model'),
 ('Sleep: hours per night', 'SLD010H (2005-2014) / SLD012 (2017-2020)',
  'Hours of sleep on a usual weeknight', 'hours',
  'RECORDED FOR 1,479 of 1,484. The pipeline currently keeps only 990 - see note'),
 ('Sleep: told a doctor about trouble sleeping', 'SLQ050',
  'Ever told a doctor she had trouble sleeping', 'yes-no',
  'Available in all six cycles. Currently UNUSED'),
 ('Supplements: took any in past 30 days', 'DSD010',
  'Took any vitamin, mineral or other supplement in the past 30 days', 'yes-no',
  'Currently UNUSED. This is the gate that identifies true non-users'),
 ('Supplements: number taken', 'DSDCOUNT',
  'How many different supplements were reported', 'count',
  'Currently UNUSED'),
 ('Supplement calcium (mg/day)', 'DSQTCALC',
  'Total elemental calcium from all reported supplements', 'mg/day',
  'In use. Absent for 2005-2006 - the DSQTOT file starts in 2007-2008'),
 ('Supplement vitamin D (mcg/day)', 'DSQTVD',
  'Total vitamin D from all reported supplements', 'mcg/day',
  'In use. Same 2005-2006 gap'),
 ('Dietary calcium day 1 / day 2 (mg)', 'DR1TCALC / DR2TCALC',
  'Calcium from food and drink, from two separate 24-hour recalls', 'mg/day',
  'In use, averaged across the two days'),
 ('Dietary vitamin D day 1 / day 2 (mcg)', 'DR1TVD / DR2TVD',
  'Vitamin D from food and drink, two 24-hour recalls', 'mcg/day',
  'In use. Day-1 vitamin D is ABSENT for 2005-2006'),
 ('Dietary recall day 1 reliable', 'DR1DRSTZ',
  'Interviewer flag - did the recall meet minimum reliability criteria', 'category',
  'Currently UNUSED. Unreliable recalls are being averaged in as though valid'),
 ('Total energy intake day 1 (kcal)', 'DR1TKCAL',
  'Total calories from the day-1 recall', 'kcal/day',
  'Currently UNUSED. Nutrient intake is normally energy-adjusted'),
 ('Poverty income ratio', 'INDFMPIR',
  'Family income divided by the federal poverty threshold for that family size and year',
  'ratio', '0 = at or below the poverty line. CAPPED AT 5, so 5 means "5 or more"'),
 ('Annual family income (band)', 'INDHHIN2 / INDFMINC',
  'Household income as a banded category', 'category',
  'Currently UNUSED. The banded form the ratio is derived from'),
 ('Education level', 'DMDEDUC2',
  'Highest level of education completed', 'category',
  'Collected but silently dropped - it stays text and the model keeps numbers only'),
]

# explicit extract column(s) per reference row - the heuristic matcher silently
# summarised the wrong column (e.g. only the hip half of a three-site question)
COLS = {
 'Number of alcohol drinks per drinking day': ['Number of alcohol drinks per drinking day'],
 'Alcohol: drinking days per year': ['Alcohol: drinking days per year'],
 'Alcohol: average drinks per day': ['Alcohol: average drinks per day'],
 'Prior fracture: ever hip / spine / wrist': ['Prior fracture: ever hip',
     'Prior fracture: ever spine', 'Prior fracture: ever wrist'],
 'Prior fracture: age at first / most recent': ['Prior fracture: age at most recent (any site)'],
 'Family history: mother fractured hip': ['Family history: mother fractured hip'],
 'Steroids: ever daily for a month or more': ['Steroids: ever daily for a month or more'],
 'Steroids: total months taken': ['Steroids: total months taken'],
 'Vigorous activity: any in a typical week': ['Vigorous activity: any in a typical week'],
 'Vigorous activity: days per week': ['Vigorous activity: days per week'],
 'Vigorous activity: minutes per session': ['Vigorous activity: minutes per session'],
 'Vigorous activity: total minutes per week': ['Vigorous activity: total minutes per week'],
 'Moderate activity: total minutes per week': ['Moderate activity: total minutes per week'],
 'Sedentary time: minutes per day': ['Sedentary time: minutes per day'],
 'Sleep: hours per night': ['Sleep: hours per night'],
 'Sleep: told a doctor about trouble sleeping': ['Sleep: told a doctor about trouble sleeping'],
 'Supplements: took any in past 30 days': ['Supplements: took any in past 30 days'],
 'Supplements: number taken': ['Supplements: number taken'],
 'Supplement calcium (mg/day)': ['Supplement calcium (mg/day)'],
 'Supplement vitamin D (mcg/day)': ['Supplement vitamin D (mcg/day)'],
 'Dietary calcium day 1 / day 2 (mg)': ['Dietary calcium day 1 (mg)', 'Dietary calcium day 2 (mg)'],
 'Dietary vitamin D day 1 / day 2 (mcg)': ['Dietary vitamin D day 1 (mcg)',
     'Dietary vitamin D day 2 (mcg)'],
 'Dietary recall day 1 reliable': ['Dietary recall day 1 reliable'],
 'Total energy intake day 1 (kcal)': ['Total energy intake day 1 (kcal)'],
 'Poverty income ratio': ['Poverty income ratio (0 = at poverty line, 5 = capped)'],
 'Annual family income (band)': ['Annual family income (band)'],
 'Education level': ['Education level'],
}
# cycle lists for rows whose NHANES field names several variables
CYC_OVERRIDE = {
 'Sleep: hours per night': '2005, 2007, 2009, 2013, 2017, 2017 (name changes mid-study)',
 'Alcohol: drinking days per year': '2005, 2007, 2009, 2013, 2017, 2017 (name changes 2017)',
 'Alcohol: average drinks per day': 'derived from the two rows above',
 'Prior fracture: age at first / most recent': '2005, 2007, 2009, 2013, 2017, 2017',
 'Steroids: total months taken': '2005, 2007, 2009, 2013, 2017, 2017',
 'Vigorous activity: total minutes per week': 'derived from the two rows above',
 'Moderate activity: total minutes per week': '2007, 2009, 2013, 2017, 2017',
 'Dietary calcium day 1 / day 2 (mg)': '2005, 2007, 2009, 2013, 2017, 2017',
 'Dietary vitamin D day 1 / day 2 (mcg)': '2007, 2009, 2013, 2017, 2017 (absent 2005-2006)',
 'Annual family income (band)': '2005, 2007, 2009, 2013, 2017',
 'Prior fracture: ever hip / spine / wrist': '2005, 2007, 2009, 2013, 2017, 2017',
}

rows = []
for label, code, question, unit, note in DESC:
    cols_here = [c for c in COLS.get(label, []) if c in out.columns]
    n, dist = '', ''
    if cols_here:
        if len(cols_here) > 1:
            parts = []
            for cc in cols_here:
                s = out[cc]
                num = pd.to_numeric(s, errors='coerce')
                if num.notna().sum() > 0.6 * max(int(s.notna().sum()), 1):
                    parts.append(f'{cc.split(":")[-1].strip()}: median {num.median():g}')
                else:
                    yes = int((s.astype(str) == 'Yes').sum())
                    parts.append(f'{cc.split(":")[-1].strip()}: {yes} Yes')
            dist = '; '.join(parts)
            n = int(out[cols_here].notna().any(axis=1).sum())
        else:
            s = out[cols_here[0]]
            n = int(s.notna().sum())
            num = pd.to_numeric(s, errors='coerce')
            if num.notna().sum() > 0.6 * max(n, 1):
                dist = (f'min {num.min():g} / median {num.median():g} / '
                        f'p90 {num.quantile(.9):g} / max {num.max():g}')
            else:
                vc = s.dropna().astype(str).value_counts().head(3)
                dist = '; '.join(f'{k}={v}' for k, v in vc.items())
    first = code.split()[0].split('/')[0].strip()
    rows.append({
        'Readable name': label,
        'NHANES variable': code,
        'What the question asks': question,
        'Unit': unit,
        'Cycles carrying it': CYC_OVERRIDE.get(
            label, ', '.join(CYCLES_OF.get(first, [])) or 'see note'),
        'Cohort with a value (of 1,484)': n,
        'Distribution in the cohort': dist,
        'Status / caution': note,
    })
ref = pd.DataFrame(rows)
p2 = os.path.join(ROOT, 'extra_reading', 'specialist_variable_reference.csv')
ref.to_csv(p2, index=False)
print(f'  {os.path.basename(p2)}: {len(ref)} variables documented')

print('\n  coverage check (raw, before any pipeline damage):')
for c in ['Sleep: hours per night', 'Number of alcohol drinks per drinking day',
          'Vigorous activity: total minutes per week', 'Supplement calcium (mg/day)',
          'Poverty income ratio (0 = at poverty line, 5 = capped)',
          'Prior fracture: age at most recent (any site)']:
    print(f'    {c:56s} {int(out[c].notna().sum()):5d} / 1484')
