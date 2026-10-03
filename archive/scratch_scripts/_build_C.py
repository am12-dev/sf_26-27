
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
