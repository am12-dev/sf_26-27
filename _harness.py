

if __name__ == '__main__':
    import time
    t0 = time.time()
    setup_directories()
    supp = load_supplements()
    day2 = load_day2_dietary()
    d = load_and_merge_cycles()
    d = apply_filters(d); d = audit_duplicates(d); d = compute_tscores(d)
    d = apply_menopause_gate(d)
    d = compute_menopause_variables(d)
    d = compute_estrogen_variables(d)
    d = compute_derived_variables(d, supp, day2)
    d = rename_and_save(d)
    d.to_pickle('_stage_derived.pkl')

    print_section('ALCOHOL PATCH CHECK')
    print('  ever_drinker      ', dict(d.ever_drinker.value_counts(dropna=False)))
    print('  alcohol coverage  ', int(d.alcohol_drinks_day.notna().sum()), 'of', len(d))
    print('  zeros (non-drinker)', int((d.alcohol_drinks_day == 0).sum()))

    enc = encode_features(d)
    cohorts = build_cohorts(d, enc)
    table_one(cohorts['C0 base']['df'], cohorts['C0 base']['X'])
    print('\n  elapsed %.1fs' % (time.time() - t0))
