
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
