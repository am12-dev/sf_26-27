"""Per-variable coverage + distribution profile for the specialist, on the 1,272 cohort.

Runs the existing pipeline but MONKEYPATCHES recode_refused with a range-based
version, because the global [7,9,77,99,...] replace destroys real sleep/weight/
intake values. Writes Notes/specialist_variable_decisions.csv.
"""
import sys, importlib.util, os
import pandas as pd, numpy as np
sys.stdout.reconfigure(encoding='utf-8')

spec = importlib.util.spec_from_file_location('osteo', 'OsteoporosisML.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

# ---- range-based sentinel handling: a code is missing only if it is OUTSIDE
# ---- the variable's plausible range. Undeclared cols keep the old behaviour
# ---- (correct for the PHQ items, where 0-3 is valid and 7/9 really are codes).
VALID = {
    'SLD010H': (2, 12), 'SLD012': (2, 14), 'RIDAGEYR': (0, 80),
    'BMXWT': (20, 300), 'BMXHT': (100, 220), 'BMXBMI': (10, 80),
    'DR1TVD': (0, 500), 'DR1TCALC': (0, 20000), 'ALQ130': (1, 30),
    'LBXVIDMS': (5, 400), 'LBDVIDMS': (5, 400), 'PAD680': (0, 1380),
    'RHQ060': (20, 65), 'INDFMPIR': (0, 5),
}
_orig = m.recode_refused


def patched(df):
    num = [c for c in df.columns if df[c].dtype in ['float64', 'int64']]
    for c in num:
        if c in VALID:
            lo, hi = VALID[c]
            s = pd.to_numeric(df[c], errors='coerce')
            df[c] = s.where((s >= lo) & (s <= hi))
        else:
            df[c] = df[c].replace(m.REFUSED, np.nan)
    return df


m.recode_refused = patched

m.setup_directories()
supp_df = m.download_supplement_files()
day2_df = m.download_day2_dietary()
df = m.load_and_merge_cycles()
df = m.recode_refused(df)
df = m.apply_filters(df)
df = m.compute_tscores(df)
df = m.compute_derived_variables(df, supp_df, day2_df)
df = m.compute_menopause_variables(df)

CY = {'2005_2006': '_D', '2007_2008': '_E', '2009_2010': '_F',
      '2013_2014': '_H', '2017_2018': '_J', '2017_2020': 'P_'}


def load(mod, cols, ranges=None):
    fr = []
    for name, sfx in CY.items():
        fn = 'P_%s.csv' % mod if sfx == 'P_' else '%s%s.csv' % (mod, sfx)
        p = os.path.join('data/raw', name, fn)
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p, low_memory=False)
        d = d[['SEQN'] + [c for c in cols if c in d.columns]].copy()
        for c in d.columns:
            if pd.api.types.is_numeric_dtype(d[c]):
                d.loc[d[c].abs() < 1e-10, c] = 0.0          # P_ denormal -> 0
                if ranges and c in ranges:
                    lo, hi = ranges[c]
                    d[c] = d[c].where((d[c] >= lo) & (d[c] <= hi))
        fr.append(d)
    return pd.concat(fr, ignore_index=True).drop_duplicates('SEQN')


rhq = load('RHQ', ['RHQ031', 'RHQ060', 'RHD280', 'RHQ305', 'RHQ540'], {'RHQ060': (20, 65)})
d = df.merge(rhq, on='SEQN', how='left', suffixes=('', '_R'))
pick = lambda c: c if c in d.columns else c + '_R'
d = d[m.recode_yesno(d[pick('RHQ031')]) == 0].copy().reset_index(drop=True)
assert len(d) == 1272, len(d)
CYCLE = d['survey_cycle']

V, SRC, LBL = {}, {}, {}


def add(key, series, src, label):
    V[key] = pd.Series(np.asarray(series), index=d.index)
    SRC[key], LBL[key] = src, label


add('age', pd.to_numeric(d['RIDAGEYR'], errors='coerce'), 'DEMO.RIDAGEYR', 'Age, years')
add('bmi', pd.to_numeric(d['BMXBMI'], errors='coerce'), 'BMX.BMXBMI', 'BMI, kg/m2')
am = pd.to_numeric(d[pick('RHQ060')], errors='coerce')
add('years_since_menopause', pd.to_numeric(d['RIDAGEYR'], errors='coerce') - am,
    'RIDAGEYR - RHQ060', 'Years since menopause')
add('ever_estrogen', m.recode_yesno(d[pick('RHQ540')]), 'RHQ.RHQ540', 'Ever used estrogen')
add('poverty_income_ratio', pd.to_numeric(d['INDFMPIR'], errors='coerce'),
    'DEMO.INDFMPIR', 'Poverty income ratio')

mcq = load('MCQ', ['MCQ160A', 'MCQ190', 'MCQ195'])
q = d[['SEQN']].merge(mcq, on='SEQN', how='left')
arth = m.recode_yesno(q['MCQ160A'])
is_ra = lambda s: (s == 2) if pd.api.types.is_numeric_dtype(s) else \
    s.astype(str).str.strip().str.lower().str.startswith('rheumatoid')
ra_flag = is_ra(q['MCQ190']) | is_ra(q['MCQ195'])
typ_known = q['MCQ190'].notna() | q['MCQ195'].notna()
ra = pd.Series(np.nan, index=q.index)
ra[arth == 0] = 0.0
ra[(arth == 1) & typ_known] = 0.0
ra[ra_flag] = 1.0
add('rheumatoid_arthritis', ra, 'MCQ160A + MCQ190/MCQ195', 'Rheumatoid arthritis')

diq = load('DIQ', ['DIQ010'])
add('diabetes', m.recode_yesno(d[['SEQN']].merge(diq, on='SEQN', how='left')['DIQ010']),
    'DIQ.DIQ010', 'Diabetes')
smq = load('SMQ', ['SMQ020'])
add('ever_smoked', m.recode_yesno(d[['SEQN']].merge(smq, on='SEQN', how='left')['SMQ020']),
    'SMQ.SMQ020', 'Ever smoked 100 cigarettes')

alq = load('ALQ', ['ALQ101', 'ALQ111', 'ALQ120Q', 'ALQ130'], {'ALQ130': (1, 30)})
a = d[['SEQN']].merge(alq, on='SEQN', how='left')
ever = m.recode_yesno(a['ALQ101']).fillna(m.recode_yesno(a['ALQ111']))
dpd = pd.to_numeric(a['ALQ130'], errors='coerce')
ac = pd.Series(np.nan, index=a.index, dtype=object)
ac[ever == 0] = 'zero'
ac[(dpd > 0) & (dpd < 3)] = '<3/day'
ac[dpd >= 3] = '3+/day'
ac[ac.isna() & (pd.to_numeric(a['ALQ120Q'], errors='coerce') == 0)] = 'zero'
add('alcohol_cat', ac, 'ALQ101|ALQ111 + ALQ130', 'Alcohol: zero / <3 / 3+ per day')

osq = load('OSQ', ['OSQ010A', 'OSQ010B', 'OSQ010C', 'OSQ130', 'OSQ170', 'OSQ200'])
o = d[['SEQN']].merge(osq, on='SEQN', how='left')
fx = pd.concat([m.recode_yesno(o[c]) for c in ['OSQ010A', 'OSQ010B', 'OSQ010C']], axis=1)
add('prior_fracture', np.where(fx.max(axis=1) == 1, 1.0,
                               np.where(fx.notna().all(axis=1), 0.0, np.nan)),
    'OSQ010A/B/C', 'Prior fracture (hip/spine/wrist)')
add('steroid_use', m.recode_yesno(o['OSQ130']), 'OSQ.OSQ130', 'Ever daily steroids')
add('mother_hip_fx', m.recode_yesno(o['OSQ170']), 'OSQ.OSQ170', 'Mother hip fracture')
add('father_hip_fx', m.recode_yesno(o['OSQ200']), 'OSQ.OSQ200', 'Father hip fracture')

PR = {'PAQ610': (1, 7), 'PAQ625': (1, 7), 'PAQ640': (1, 7), 'PAQ655': (1, 7), 'PAQ670': (1, 7),
      'PAD615': (0, 840), 'PAD630': (0, 840), 'PAD645': (0, 840), 'PAD660': (0, 840),
      'PAD675': (0, 840), 'PAD680': (0, 1380)}
paq = load('PAQ', list(PR) + ['PAQ605', 'PAQ620', 'PAQ635', 'PAQ650', 'PAQ665'], PR)
p = d[['SEQN']].merge(paq, on='SEQN', how='left')


def dom(g, dy, mi):
    G = m.recode_yesno(p[g])
    wk = pd.to_numeric(p[dy], errors='coerce') * pd.to_numeric(p[mi], errors='coerce')
    return wk.where(G == 1, other=pd.Series(np.where(G == 0, 0.0, np.nan), index=p.index))


vw, mw = dom('PAQ605', 'PAQ610', 'PAD615'), dom('PAQ620', 'PAQ625', 'PAD630')
tr = dom('PAQ635', 'PAQ640', 'PAD645')
vr, mr = dom('PAQ650', 'PAQ655', 'PAD660'), dom('PAQ665', 'PAQ670', 'PAD675')
add('met_min_week', 8 * vw + 4 * mw + 4 * tr + 8 * vr + 4 * mr, 'PAQ605-PAD675', 'Total activity, MET-min/wk')
add('moderate_min_wk', mw + tr + mr, 'PAQ620-PAD675', 'Moderate activity, min/wk')
add('vigorous_min_wk', vw + vr, 'PAQ605/PAQ650', 'Vigorous activity, min/wk')
add('sitting_hrs_day', pd.to_numeric(p['PAD680'], errors='coerce') / 60, 'PAQ.PAD680', 'Sitting, hours/day')

add('total_calcium_mg', pd.to_numeric(d['total_calcium_mg'], errors='coerce'),
    'DR1TCALC+DR2TCALC+DSQTCAL', 'Calcium, diet+supplement, mg/day')
add('vitd_intake_IU', pd.to_numeric(d['total_vitd_mcg'], errors='coerce') * 40,
    '(DR1TVD+DR2TVD+DSQTVD)x40', 'Vitamin D intake, IU/day')
vidc = [c for c in ['LBXVIDMS', 'LBDVIDMS'] if c in d.columns]
sv = pd.to_numeric(d[vidc[0]], errors='coerce')
for c in vidc[1:]:
    sv = sv.fillna(pd.to_numeric(d[c], errors='coerce'))
add('serum_vitd_ngml', sv / 2.496, 'VID.LBXVIDMS/LBDVIDMS', 'Serum 25(OH)D, ng/mL')
add('sleep_hrs', pd.to_numeric(d['sleep_hrs'], errors='coerce'), 'SLQ.SLD012|SLD010H', 'Sleep, hours/night')
add('phq9_score', pd.to_numeric(d['phq9_score'], errors='coerce'), 'DPQ010-090', 'PHQ-9 score')

CORE = ['age', 'bmi', 'years_since_menopause', 'ever_estrogen', 'rheumatoid_arthritis',
        'diabetes', 'ever_smoked', 'alcohol_cat', 'prior_fracture', 'steroid_use',
        'met_min_week', 'total_calcium_mg', 'poverty_income_ratio', 'mother_hip_fx',
        'father_hip_fx', 'sleep_hrs']

N = len(d)
rows = []
for k, s in V.items():
    s = pd.Series(s)
    n = int(s.notna().sum()); miss = N - n
    miss_cy = CYCLE[s.isna()].value_counts()
    conc = '' if miss == 0 else '%s (%d of %d)' % (miss_cy.index[0], miss_cy.iloc[0], miss)
    cat = s.dtype == object or s.dropna().nunique() <= 4
    if cat:
        vc = s.dropna().value_counts()
        summ = '; '.join('%s=%d (%.0f%%)' % (a, b, b / n * 100) for a, b in vc.items())
        rows.append(dict(variable=k, label=LBL[k], source=SRC[k], type='categorical',
                         n_available=n, n_missing=miss, pct_missing=round(miss / N * 100, 1),
                         mean='', median='', iqr='', skew='', pct_zero='',
                         levels=summ, missing_concentrated_in=conc,
                         suggested='mode' if miss else 'none needed',
                         core='yes' if k in CORE else 'no'))
    else:
        x = pd.to_numeric(s, errors='coerce').dropna()
        sk = x.skew()
        sug = ('none needed' if miss == 0 else
               'median (skew %+.1f)' % sk if abs(sk) > 1 else 'mean or median (near-normal)')
        rows.append(dict(variable=k, label=LBL[k], source=SRC[k], type='continuous',
                         n_available=n, n_missing=miss, pct_missing=round(miss / N * 100, 1),
                         mean=round(x.mean(), 2), median=round(x.median(), 2),
                         iqr='%.1f-%.1f' % (x.quantile(.25), x.quantile(.75)),
                         skew=round(sk, 2), pct_zero=round((x == 0).mean() * 100, 1),
                         levels='', missing_concentrated_in=conc, suggested=sug,
                         core='yes' if k in CORE else 'no'))

t = pd.DataFrame(rows).sort_values(['core', 'pct_missing'], ascending=[False, True])
out = 'Notes/specialist_variable_decisions.csv'
t.to_csv(out, index=False)

pd.set_option('display.width', 250, 'display.max_colwidth', 46)
print('\n' + '=' * 110)
print('  PER-VARIABLE COVERAGE IN THE 1,272 COHORT  (recode_refused bug fixed)')
print('=' * 110)
print(t[['variable', 'type', 'n_available', 'n_missing', 'pct_missing',
         'mean', 'median', 'skew', 'missing_concentrated_in', 'suggested']].to_string(index=False))
print('\n--- CATEGORICAL LEVELS ---')
for _, r in t[t.type == 'categorical'].iterrows():
    print('  %-24s %s' % (r.variable, r.levels))
print('\n--- wrote %s ---' % out)
