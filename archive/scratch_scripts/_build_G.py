
# ================================================================================
# BLOCK G — DIAGNOSTICS, HEADLINE EVALUATION, PRESPECIFIED ARMS, MAIN
# ================================================================================

def coefficient_diagnostics(X, y, label, filename='coefficient_diagnostics.csv'):
    """A leak detector and a sign-error detector. NOT a findings table.

    These are standardised coefficients from one unpenalised-in-spirit logistic fit.
    They are unstable across collinear predictors — bmi and weight_kg will trade
    magnitude run to run — so they must never be read as effect sizes. Two alarms:

      LEAK   any |coefficient| above LEAK_COEF_THRESHOLD is implausible for a survey
             predictor and usually means a BMD-derived column reached the feature set.
      SIGN   EXPECTED_SIGNS holds the direction each predictor must take if the data
             are wired up correctly. A flip is either a coding error or a real finding,
             and the table says which ones flipped so the question gets asked.
    """
    print_section(f'DIAGNOSTIC: COEFFICIENT SANITY CHECK — {label}')
    y = np.asarray(y)
    pw = (y == 0).sum() / max((y == 1).sum(), 1)
    pipe = _pipe(get_model_dictionary(pw)['Logistic Regression (L2)']).fit(X, y)
    coef = pipe.named_steps['model'].coef_[0]
    rows = []
    for f, c in zip(X.columns, coef):
        exp = EXPECTED_SIGNS.get(f)
        flag = []
        if abs(c) > LEAK_COEF_THRESHOLD:
            flag.append('LEAK?')
        if exp is not None and np.sign(c) != exp and abs(c) > 0.05:
            flag.append('SIGN')
        rows.append({'Predictor': f, 'Std coef': round(float(c), 4),
                     'Expected sign': {1: '+', -1: '-'}.get(exp, 'n/a'),
                     'Observed sign': '+' if c > 0 else '-',
                     'Flag': ' '.join(flag) or 'ok'})
    table = pd.DataFrame(rows).sort_values('Std coef', key=np.abs, ascending=False)
    print(table.to_string(index=False))
    leaks = table[table['Flag'].str.contains('LEAK')]
    signs = table[table['Flag'].str.contains('SIGN')]
    if len(leaks):
        print(f"\n  !! {len(leaks)} coefficient(s) exceed |{LEAK_COEF_THRESHOLD}| — check "
              "for a BMD-derived column in the feature set.")
    else:
        print(f"\n  No coefficient exceeds |{LEAK_COEF_THRESHOLD}|. No leak signature.")
    if len(signs):
        print(f"  {len(signs)} predictor(s) point the wrong way: "
              f"{', '.join(signs['Predictor'])}.")
        # A flip is either reverse causation, or one half of a collinear pair where the
        # partner absorbed the effect. Name the partner so the reader is not left to
        # guess which: a residual sign on the weaker member of a correlated pair carries
        # no clinical meaning at all.
        corr = X.corr().abs()
        for f in signs['Predictor']:
            other = corr[f].drop(f).idxmax()
            r = corr.loc[f, other]
            partner = table.loc[table['Predictor'] == other, 'Std coef'].iloc[0]
            note = ('partner absorbed the effect, so this is a residual with no '
                    'clinical reading' if r > 0.5 and abs(partner) > abs(
                        table.loc[table['Predictor'] == f, 'Std coef'].iloc[0])
                    else 'not explained by collinearity — investigate or report it')
            print(f"    {f:<22} strongest partner {other} (|r| {r:.2f}, "
                  f"coef {partner:+.3f}): {note}")
        print("  State the ones that survive this rather than hide them — a backwards")
        print("  vitamin D coefficient is reverse causation (low intake prompts")
        print("  supplementation), not a bug.")
    print("  This table is DIAGNOSTIC. Do not present it as a result.")
    save_csv(table, filename, 'DIAGNOSTIC')
    return table


def tune_rf_leaf_nested(X, y, seed=SEED):
    """Choose min_samples_leaf inside each outer training fold, never on the test fold."""
    y = np.asarray(y)
    outer = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=seed).split(X, y))
    rows, picks = [], []
    for leaf in RF_LEAF_GRID:
        aucs = []
        for tr, te in outer:
            pipe = _pipe(make_random_forest(min_samples_leaf=leaf, oob=False))
            pipe.fit(X.iloc[tr], y[tr])
            aucs.append(roc_auc_score(y[te], pipe.predict_proba(X.iloc[te])[:, 1]))
        rows.append({'min_samples_leaf': leaf, 'Test AUC': np.mean(aucs),
                     'SD across folds': np.std(aucs)})
    for tr, te in outer:
        inner = list(StratifiedKFold(n_splits=3, shuffle=True,
                                     random_state=seed).split(X.iloc[tr], y[tr]))
        best, best_a = None, -np.inf
        for leaf in RF_LEAF_GRID:
            p = cross_val_predict(_pipe(make_random_forest(min_samples_leaf=leaf, oob=False)),
                                  X.iloc[tr], y[tr], cv=inner, method='predict_proba')[:, 1]
            a = roc_auc_score(y[tr], p)
            if a > best_a:
                best, best_a = leaf, a
        picks.append(best)
    return pd.DataFrame(rows), picks


def report_rf_tuning(X, y, label):
    """Evidence that RF_MIN_SAMPLES_LEAF was measured, not assumed.

    The forest's train/test gap is large and the reflex is to regularise it away by
    growing shallower leaves. That reflex is wrong here: raising min_samples_leaf lowers
    TEST AUC monotonically. The gap is the price of the performance, not a defect.
    """
    print_section(f'METHODS: RANDOM FOREST LEAF TUNING — {label}')
    table, picks = tune_rf_leaf_nested(X, y)
    print(table.to_string(index=False, formatters={'Test AUC': '{:.4f}'.format,
                                                   'SD across folds': '{:.4f}'.format}))
    print(f"\n  min_samples_leaf chosen by inner CV per outer fold: {picks}")
    print(f"  shipped value: RF_MIN_SAMPLES_LEAF = {RF_MIN_SAMPLES_LEAF}")
    best = table.loc[table['Test AUC'].idxmax(), 'min_samples_leaf']
    print(f"  best on the grid: {best}. Test AUC falls from "
          f"{table['Test AUC'].iloc[0]:.3f} to {table['Test AUC'].iloc[-1]:.3f} across "
          "the grid, so shrinking the gap costs real discrimination.")
    save_csv(table, 'rf_leaf_tuning.csv', 'METHODS')
    return table


def evaluate_target(X, df, target, target_label, n_events, tag):
    """The headline evaluation for one clinical cutoff.

    Reports the leaderboard (biased upward by design), the nested estimate (the
    defensible one), and the gap between them, all against OST. Fitting eight models and
    quoting the best is selection on the test fold; the nested figure moves that choice
    inside each outer training fold so no test row helps pick the model scored on it.
    When the two diverge, the divergence IS the finding.
    """
    y = df[target].to_numpy()
    t = df['t_score'].to_numpy()

    lb = train_models(X, y, target_label)
    lb.insert(0, 'Target', target_label)
    save_csv(lb, f'model_leaderboard_{tag}.csv', 'PRESENT')
    best_lb = lb.loc[lb['auc'].idxmax()]

    print_section(f'STEP 12: NESTED CROSS-VALIDATION — {target_label}')
    oof, chosen, outer = nested_cv_selection(X, y, t)
    oof_r = rank_within_folds(oof, outer, len(y))
    nested_auc = roc_auc_score(y, oof_r)
    print(f"  model chosen per outer fold: {chosen}")
    print(f"  leaderboard best  {best_lb['Model']}  AUC {best_lb['auc']:.3f}")
    print(f"  nested estimate                    AUC {nested_auc:.3f}   "
          f"(optimism {best_lb['auc'] - nested_auc:+.3f})")

    base = compute_baselines(df)
    rows = []
    for ref_name, ref in base.items():
        ref_auc = roc_auc_score(y, ref)
        d, lo, hi, p = bootstrap_delta_auc(y, oof_r, ref)
        beats = lo > 0
        rows.append({'Target': target_label, 'Events': int(n_events),
                     'Comparator': ref_name, 'Comparator AUC': round(ref_auc, 3),
                     'Leaderboard AUC': round(float(best_lb['auc']), 3),
                     'Nested AUC': round(nested_auc, 3),
                     'Optimism': round(float(best_lb['auc']) - nested_auc, 3),
                     'Delta vs comparator': round(d, 3),
                     '95% CI': f"[{lo:+.3f}, {hi:+.3f}]",
                     'p (one-sided)': round(p, 4),
                     'Verdict': 'Beats comparator' if beats else 'Not separable'})
        print(f"  vs {ref_name:<24} {ref_auc:.3f}   delta {d:+.3f} "
              f"[{lo:+.3f}, {hi:+.3f}]   {'BEATS' if beats else 'not separable'}")

    verdict = pd.DataFrame(rows)
    ost = verdict[verdict['Comparator'].str.startswith('OST')].iloc[0]
    if ost['Verdict'] == 'Not separable':
        print(f"\n  The advantage over OST spans zero at {n_events} events. Report this as")
        print(f"  not separable. Do NOT quote the leaderboard figure "
              f"({best_lb['auc']:.3f}) as a result for this target.")
    return verdict, oof_r, chosen


def compare_arm(df, encoded, base_groups, arm_name, arm_groups, target, label):
    """One prespecified arm, evaluated on ITS OWN rows against ITS OWN base model.

    An arm variable is measured on a subset, so the honest question is not 'does the
    augmented model beat the full-cohort base model' — that compares two different case
    mixes. It is 'on exactly these women, does adding this variable help'. Both models
    are therefore refit on the arm's complete-case rows and compared pairwise.
    """
    cols = [c for g in arm_groups.values() for c in g]
    mask = pd.Series(True, index=df.index)
    for c in cols:
        mask &= encoded[c].notna()
    sub, enc_sub = df[mask], encoded[mask]
    y = sub[target].to_numpy()
    t = sub['t_score'].to_numpy()
    X_base = build_feature_matrix(enc_sub, base_groups)
    X_arm = build_feature_matrix(enc_sub, {**base_groups, **arm_groups})
    folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED).split(X_base, y))

    s_base = oof_scores(X_base, y, t, folds)
    s_arm = oof_scores(X_arm, y, t, folds)
    a_base = {k: roc_auc_score(y, v) for k, v in s_base.items()}
    a_arm = {k: roc_auc_score(y, v) for k, v in s_arm.items()}
    primary = max(a_base, key=a_base.get)
    d, lo, hi, p = bootstrap_delta_auc(y, s_arm[primary], s_base[primary], n_boot=500)
    print(f"  {arm_name:<30} n {len(sub):>5,}  events {int(y.sum()):>4}  "
          f"base {a_base[primary]:.3f} -> arm {a_arm[primary]:.3f}  "
          f"delta {d:+.3f} [{lo:+.3f}, {hi:+.3f}]  "
          f"{'adds signal' if lo > 0 else 'no detectable gain'}")
    return {'Arm': arm_name, 'Target': label, 'n': len(sub), 'Events': int(y.sum()),
            'Variables added': ', '.join(arm_groups),
            'Primary model': primary,
            'Base AUC': round(a_base[primary], 3), 'Arm AUC': round(a_arm[primary], 3),
            'Delta AUC': round(d, 3), '95% CI': f"[{lo:+.3f}, {hi:+.3f}]",
            'p (one-sided)': round(p, 4),
            'Verdict': 'Adds signal' if lo > 0 else 'No detectable gain'}


def run_arms(df, encoded, cohorts):
    """Arms C-H, all prespecified. Nulls are reported, not buried.

    Every one of these was written down before it was run, with the expected answer
    stated in advance. That is what makes a null here informative rather than a failed
    attempt: 'serum vitamin D adds nothing' is a result when it was predicted, and a
    fishing expedition when it was not.
    """
    print_section('STEP 13: PRESPECIFIED ARMS')
    base = FEATURE_GROUPS
    rows = []

    print('\n  Arms C/D — vitamin D. Intake and serum are measured on DIFFERENT subsets,')
    print('  so they get separate arms and are never cross-compared. Vitamin D is out of')
    print('  the headline model entirely and the null was stated in advance.')
    rows.append(compare_arm(df, encoded, base, 'C: vitamin D + calcium intake',
                            ARM_GROUPS['vitd_intake'], 'at_risk', 'T<=-1.0'))
    rows.append(compare_arm(df, encoded, base, 'D: serum 25(OH)D',
                            ARM_GROUPS['vitd_serum'], 'at_risk', 'T<=-1.0'))

    print('\n  Arm E — rheumatoid arthritis. Descriptive only at T<=-2.5, and the 123')
    print('  women whose arthritis type is unrecorded are EXCLUDED, not coded as no RA.')
    rows.append(compare_arm(df, encoded, base, 'E: rheumatoid arthritis',
                            ARM_GROUPS['ra'], 'at_risk', 'T<=-1.0'))
    ra = cohorts['C4 + rheumatoid arthritis']['df']
    for v, name in [(1, 'rheumatoid arthritis'), (0, 'no rheumatoid arthritis')]:
        s = ra[ra['rheumatoid_arthritis'] == v]
        print(f"    {name:<24} n {len(s):>4}   mean T {s['t_score'].mean():+.3f}   "
              f"T<=-2.5 {int(s['osteoporosis'].sum()):>3} ({s['osteoporosis'].mean():.1%})")
    print(f"    excluded for unrecorded arthritis type: "
          f"{int((df['ra_arm_eligible'] == 0).sum())}")

    print('\n  Arm F — PHQ-9 as a binary. A SUBSTITUTION for the continuous score, never')
    print('  an addition: the two are the same information and would collide.')
    sub_groups = {k: v for k, v in base.items() if k != 'phq9_score'}
    rows.append(compare_arm(df, encoded, sub_groups, 'F: PHQ-9 >= 10 (substitution)',
                            ARM_GROUPS['phq_binary'], 'at_risk', 'T<=-1.0'))

    print('\n  Arm G — diabetes. The diabetic bone paradox means type 2 diabetes raises')
    print('  measured BMD while also raising fracture risk, so a protective coefficient')
    print('  here is expected and is NOT evidence the model is wrong. There is')
    print('  deliberately no EXPECTED_SIGNS entry for it. Two reclassifications:')
    enc_g = encoded.copy()
    X0 = build_feature_matrix(encoded, base)
    y0 = df['at_risk'].to_numpy()
    t0 = df['t_score'].to_numpy()
    folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED).split(X0, y0))
    a0 = {k: roc_auc_score(y0, v) for k, v in oof_scores(X0, y0, t0, folds).items()}
    primary = max(a0, key=a0.get)
    for variant, series in [
            ('G1: borderline coded as diabetic',
             pd.to_numeric(df['diabetes_borderline_as_case'], errors='coerce')),
            ('G2: diabetes dropped entirely', None)]:
        if series is None:
            Xg = build_feature_matrix(encoded, {k: v for k, v in base.items()
                                                if k != 'diabetes'})
        else:
            enc_g['diabetes'] = series
            Xg = build_feature_matrix(enc_g, base)
        ag = roc_auc_score(y0, oof_scores(Xg, y0, t0, folds)[primary])
        print(f"    {variant:<38} AUC {ag:.3f}  (shipped {a0[primary]:.3f}, "
              f"delta {ag - a0[primary]:+.3f})")
        rows.append({'Arm': variant, 'Target': 'T<=-1.0', 'n': len(df),
                     'Events': int(y0.sum()), 'Variables added': 'diabetes recoded',
                     'Primary model': primary, 'Base AUC': round(a0[primary], 3),
                     'Arm AUC': round(ag, 3), 'Delta AUC': round(ag - a0[primary], 3),
                     '95% CI': 'n/a', 'p (one-sided)': np.nan,
                     'Verdict': 'Sensitivity only'})

    print('\n  Arm H — site sensitivity. The headline uses the WHO/ISCD lowest-of-two')
    print('  rule. These refit on each site alone to show the rule is not driving the')
    print('  result. Reported for the headline target only, and never re-ablated.')
    for site, col in [('H1: femoral neck only', 't_femoral_neck'),
                      ('H2: total hip only', 't_total_hip')]:
        ok = df[col].notna()
        ys = (df.loc[ok, col].round(3) <= T_OSTEOPENIA).astype(int).to_numpy()
        ts = df.loc[ok, col].round(3).to_numpy()
        Xs = build_feature_matrix(encoded[ok.to_numpy()], base)
        fs = list(StratifiedKFold(n_splits=5, shuffle=True,
                                  random_state=SEED).split(Xs, ys))
        asite = {k: roc_auc_score(ys, v) for k, v in oof_scores(Xs, ys, ts, fs).items()}
        pm = max(asite, key=asite.get)
        print(f"    {site:<26} n {int(ok.sum()):>5,}  events {int(ys.sum()):>4}  "
              f"AUC {asite[pm]:.3f}  ({pm})")
        # No delta here. These arms respecify the OUTCOME, so they are computed on a
        # different label and a different set of rows than the headline; subtracting
        # the two AUCs would compare two different questions.
        rows.append({'Arm': site, 'Target': 'T<=-1.0 at this site', 'n': int(ok.sum()),
                     'Events': int(ys.sum()), 'Variables added': 'none (outcome respecified)',
                     'Primary model': pm, 'Base AUC': round(a0[primary], 3),
                     'Arm AUC': round(asite[pm], 3), 'Delta AUC': np.nan,
                     '95% CI': 'n/a (different outcome, not comparable)',
                     'p (one-sided)': np.nan, 'Verdict': 'Sensitivity only'})

    table = pd.DataFrame(rows)
    save_csv(table, 'prespecified_arms.csv', 'PRESENT')
    return table


def screening_tables(X, df, p_cal, oof_r):
    """Two cutoff tables that mean different things by the same numbers.

    referral_table leads with 'Top fraction flagged' — a QUANTILE of the nested model's
    scores, which are ranks and not probabilities. threshold_sweep keeps 'Probability
    Cutoff' — a real probability from a DIFFERENT, sigmoid-calibrated forest. They are
    not on the same axis and must never be merged or plotted together.
    """
    y = df['at_risk'].to_numpy()
    print_section('STEP 14: SCREENING YIELD — T<=-1.0')
    print('  How many DXA scans does each referral rule cost per case found?\n')
    ref = referral_table(y, oof_r, as_quantile=True)
    ref = ref.rename(columns={'Cutoff': 'Top fraction flagged'})
    ref.insert(0, 'Score', 'Nested CV out-of-fold rank (not a probability)')
    print(ref.to_string(index=False))
    save_csv(ref, 'referral_table.csv', 'PRESENT')

    sweep = referral_table(y, p_cal, as_quantile=False)
    sweep = sweep.rename(columns={'Cutoff': 'Probability Cutoff'})
    sweep.insert(0, 'Model', 'Random forest, sigmoid-calibrated')
    sweep.insert(1, 'AUC', round(roc_auc_score(y, p_cal), 3))
    print('\n  Calibrated-probability version — a different model, a different axis:')
    print(sweep.to_string(index=False))
    save_csv(sweep, 'threshold_sweep.csv', 'PRESENT')
    return ref, sweep


def main():
    setup_directories()
    supp = load_supplements()
    day2 = load_day2_dietary()

    df = load_and_merge_cycles()
    df = apply_filters(df)
    df = audit_duplicates(df)
    df = compute_tscores(df)
    df = apply_menopause_gate(df)
    df = compute_menopause_variables(df)
    df = compute_estrogen_variables(df)
    df = compute_derived_variables(df, supp, day2)
    df = rename_and_save(df)

    encoded = encode_features(df)
    cohorts = build_cohorts(df, encoded)
    X = cohorts['C0 base']['X']
    table_one(df, X)

    coefficient_diagnostics(X, df['at_risk'], 'T<=-1.0')

    verdicts = []
    for target, label, tag in [('at_risk', 'Osteopenia+ (T<=-1.0)', 'osteopenia'),
                               ('osteoporosis', 'Osteoporosis (T<=-2.5)', 'osteoporosis')]:
        v, oof_r, _ = evaluate_target(X, df, target, label, df[target].sum(), tag)
        verdicts.append(v)
        if target == 'at_risk':
            headline_oof = oof_r

    verdict = pd.concat(verdicts, ignore_index=True)
    save_csv(verdict, 'nested_cv_verdict.csv', 'PRESENT')

    clin = clinical_table(X, df['at_risk'], 'Osteopenia+ (T<=-1.0)')
    plot_forest(clin, 'Osteopenia+ (T<=-1.0)')
    ablation_grid(X, df['at_risk'], df['t_score'], FEATURE_GROUPS, 'osteopenia')
    block_ablation(X, df['at_risk'], df['t_score'], FEATURE_GROUPS, 'osteopenia')

    p_cal = calibration_figure(X, df['at_risk'], 'Osteopenia+ (T<=-1.0)')
    screening_tables(X, df, p_cal, headline_oof)

    report_rf_tuning(X, df['at_risk'], 'Osteopenia+ (T<=-1.0)')
    run_arms(df, encoded, cohorts)

    print_section('DONE')
    print('  Open outputs/nested_cv_verdict.csv first — it is the bottom line.')
    print('  Variable importance lives in two places and they answer different')
    print('  questions: clinical_predictor_table.csv (shuffle a column inside a model')
    print('  trained with it) and model_variable_ablation_osteopenia.csv (refit without')
    print('  the variable at all). Where they disagree, collinearity is the reason.')


if __name__ == '__main__':
    main()
