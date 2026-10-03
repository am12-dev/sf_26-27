
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
