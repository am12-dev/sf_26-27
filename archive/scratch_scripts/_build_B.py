
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
