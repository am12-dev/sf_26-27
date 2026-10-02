
# ================================================================================
# BLOCK F — MODEL LAYER
# ================================================================================

from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.ensemble import (RandomForestClassifier, RandomForestRegressor)
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.metrics import brier_score_loss, confusion_matrix, roc_auc_score
from sklearn.model_selection import (StratifiedKFold, cross_val_predict,
                                     cross_validate)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import xgboost as xgb


def save_csv(df, filename, tier):
    """Write one result table to outputs/ and label who it is for.

    Every file carries a tier so the folder stays self-explanatory without a README
    that can drift out of sync with the code.
      PRESENT    - for the clinical audience.
      METHODS    - backs up a methodological choice if it is challenged.
      DIAGNOSTIC - a bug detector. Standardised units, unstable across collinear
                   predictors, therefore NOT findings and not to be shown as results.
    """
    assert tier in ('PRESENT', 'METHODS', 'DIAGNOSTIC'), tier
    path = os.path.join(OUT_DIR, filename)
    df.to_csv(path, index=False)
    print(f"  [{tier:10s}] {filename}")
    return path


def _pipe(model):
    """Imputation and scaling are learned INSIDE the training fold, never before it."""
    return Pipeline([('imputer', SimpleImputer(strategy='median')),
                     ('scaler', StandardScaler()), ('model', model)])


def make_random_forest(min_samples_leaf=None, oob=True):
    """Random forest with out-of-bag scoring enabled.

    OOB scores each row using only the ~37% of trees whose bootstrap sample excluded it,
    which is the honest in-sample number for a bagged ensemble. Plain in-sample AUC is
    near 1.0 for any deep forest — on shuffled labels this configuration still reaches
    0.997 — because ~63% of the trees have memorised each training row.
    """
    return RandomForestClassifier(
        n_estimators=500,
        min_samples_leaf=RF_MIN_SAMPLES_LEAF if min_samples_leaf is None else min_samples_leaf,
        class_weight='balanced', random_state=SEED, n_jobs=-1,
        bootstrap=True, oob_score=oob)


def get_model_dictionary(pos_weight):
    """Five classifiers on the binary label. Both boosters are aggressively
    regularised (max_depth 2, reg_lambda 50) because n ~ 1,100 overfits trivially."""
    return {
        'Logistic Regression (L2)': LogisticRegression(
            max_iter=1000, random_state=SEED, class_weight='balanced'),
        'Elastic Net Logistic Regression': LogisticRegression(
            penalty='elasticnet', solver='saga', l1_ratio=0.5, max_iter=2000,
            random_state=SEED, class_weight='balanced'),
        'Random Forest': make_random_forest(),
        'LightGBM (Aggressive Reg)': lgb.LGBMClassifier(
            n_estimators=150, max_depth=2, num_leaves=4, min_child_samples=50,
            reg_lambda=50.0, class_weight='balanced', random_state=SEED,
            verbose=-1, n_jobs=-1),
        'XGBoost (Aggressive Reg)': xgb.XGBClassifier(
            n_estimators=150, max_depth=2, min_child_weight=15, reg_lambda=50.0,
            scale_pos_weight=pos_weight, random_state=SEED, eval_metric='logloss',
            n_jobs=-1),
    }


def get_regressor_dictionary():
    """Continuous t_score models, which never see either binary label.

    Dichotomising a continuous measurement discards information: a woman at T = -2.4 and
    one at T = +0.5 are otherwise the same 'negative'. Regressing t_score keeps the
    gradient, and ONE fit serves BOTH clinical cutoffs — the predicted T-score is simply
    thresholded twice.
    """
    return {
        'Ridge -> t_score': RidgeCV(alphas=np.logspace(-3, 3, 13)),
        'RF -> t_score': RandomForestRegressor(n_estimators=500, min_samples_leaf=5,
                                               random_state=SEED, n_jobs=-1),
        'LightGBM -> t_score': lgb.LGBMRegressor(n_estimators=150, max_depth=2,
                                                 num_leaves=4, min_child_samples=50,
                                                 reg_lambda=50.0, random_state=SEED,
                                                 verbose=-1, n_jobs=-1),
    }


def compute_baselines(df):
    """Non-ML comparators, oriented so a HIGHER score means HIGHER risk.

    OST = 0.2 x (weight_kg - age) is a validated two-input screening formula needing
    only a scale and a birthdate. It is the bar any model here has to clear: an AUC
    reported without it is uninterpretable.
    """
    w = pd.to_numeric(df['weight_kg'], errors='coerce')
    a = pd.to_numeric(df['age'], errors='coerce')
    ost = 0.2 * (w - a)
    return {'OST  0.2x(weight-age)': -ost.fillna(ost.median()).to_numpy(),
            'Weight alone': -w.fillna(w.median()).to_numpy()}


def bootstrap_delta_auc(y, s_model, s_ref, n_boot=1000, seed=SEED):
    """Paired stratified bootstrap of AUC(model) - AUC(reference).

    Resampling cases and non-cases separately holds prevalence fixed across replicates.
    Both scores are evaluated on the same resampled rows, so the difference is paired.
    """
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    a = np.asarray(s_model, dtype=float)
    b = np.asarray(s_ref, dtype=float)
    pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    d = np.empty(n_boot)
    for i in range(n_boot):
        ix = np.concatenate([rng.choice(pos, pos.size, replace=True),
                             rng.choice(neg, neg.size, replace=True)])
        d[i] = roc_auc_score(y[ix], a[ix]) - roc_auc_score(y[ix], b[ix])
    return d.mean(), np.percentile(d, 2.5), np.percentile(d, 97.5), float((d <= 0).mean())


def holm(pvals):
    """Holm-Bonferroni adjusted p-values, order preserved."""
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    order = np.argsort(p)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def oof_scores(X, y, t_score, folds):
    """Out-of-fold scores for every classifier and regressor, on one fold structure."""
    y = np.asarray(y)
    pw = (y == 0).sum() / max((y == 1).sum(), 1)
    out = {}
    for name, model in get_model_dictionary(pw).items():
        out[name] = cross_val_predict(_pipe(model), X, y, cv=folds,
                                      method='predict_proba')[:, 1]
    for name, reg in get_regressor_dictionary().items():
        out[name] = -cross_val_predict(_pipe(reg), X, t_score, cv=folds)
    return out


# --- leaderboard -------------------------------------------------------------------

MIN_OOB_COVERAGE = 0.80


def _oob_auc(est, y, min_coverage=MIN_OOB_COVERAGE):
    """Out-of-bag AUC, or a refusal to report one, with the reason.

    scikit-learn >= 1.9 makes the bootstrap draw sample_weight-aware, and
    class_weight='balanced' is applied as a sample weight. On an imbalanced target the
    minority class is therefore oversampled into nearly every bootstrap, so most of its
    rows are never out-of-bag. Measured here: at T <= -2.5 only 27.6% of cases get an
    OOB estimate, against 100% of non-cases.

    sklearn returns those rows as an all-ZERO decision-function row rather than NaN, so
    an isnan guard silently keeps them and scores every uncovered case at 0.0 — the
    lowest possible rank. That produced an OOB AUC of 0.108 for the osteoporosis target:
    not a weak model but an inverted one, and it would have been printed in a
    PRESENT-tier leaderboard. Drop the uncovered rows, and if either class loses more
    than min_coverage of its rows the survivors are a biased subset, so report nothing.
    """
    odf = est.oob_decision_function_
    ok = (np.nansum(odf, axis=1) > 0) & ~np.isnan(odf).any(axis=1)
    y = np.asarray(y)
    cov = {c: ok[y == c].mean() for c in np.unique(y)}
    worst = min(cov.values())
    if worst < min_coverage:
        lo = min(cov, key=cov.get)
        return np.nan, (f'withheld: only {worst:.0%} of class {lo} rows are ever '
                        f'out-of-bag (class_weight oversamples them)')
    if ok.sum() == 0 or len(np.unique(y[ok])) < 2:
        return np.nan, 'withheld: no usable out-of-bag rows'
    return roc_auc_score(y[ok], odf[ok, 1]), f'coverage {worst:.0%}'


def run_model(pipe, X, y, cv):
    res = cross_validate(pipe, X, y, cv=cv, scoring=['roc_auc', 'recall', 'precision', 'f1'],
                         return_train_score=True)
    y_pred = cross_val_predict(pipe, X, y, cv=cv)
    tn, fp, fn, tp = confusion_matrix(y, y_pred).ravel()
    pipe.fit(X, y)
    oob_auc, oob_note = np.nan, 'n/a (not a bagged ensemble)'
    est = pipe.named_steps['model']
    if hasattr(est, 'oob_decision_function_'):
        oob_auc, oob_note = _oob_auc(est, y)
    return {'auc': res['test_roc_auc'].mean(), 'train_auc': res['train_roc_auc'].mean(),
            'oob_auc': oob_auc, 'oob_note': oob_note,
            'sens': tp / (tp + fn), 'spec': tn / (tn + fp),
            'tn': tn, 'fp': fp, 'fn': fn, 'tp': tp}


def train_models(X, y, label):
    print_section(f'STEP 9: MODEL LEADERBOARD — {label}')
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    pw = (np.asarray(y) == 0).sum() / max((np.asarray(y) == 1).sum(), 1)
    rows = []
    for name, model in get_model_dictionary(pw).items():
        m = run_model(_pipe(model), X, y, cv)
        m['Model'] = name
        rows.append(m)
        oob = (f" | OOB {m['oob_auc']:.3f}" if not np.isnan(m['oob_auc'])
               else (f" | OOB {m['oob_note']}" if m['oob_note'].startswith('withheld')
                     else ""))
        print(f"  {name:<34} test {m['auc']:.3f}  train {m['train_auc']:.3f}{oob}")
    print("  Train AUC is in-sample and inflated by design for the bagged forest, so OOB")
    print("  is its honest in-sample figure. Do NOT rank models by the train/test gap.")
    return pd.DataFrame(rows)


# --- importance --------------------------------------------------------------------

def permutation_importance_cv(model, X, y, n_repeats=5, seed=SEED):
    """Permutation importance as mean AUC lost, measured OUT OF FOLD.

    Model-agnostic and in the same units for every model, so unlike Gini importance or
    split counts it is comparable across model families and is not biased toward
    continuous features over binary ones. Tree importances were deliberately removed
    from reporting: here they inverted the real ranking.
    """
    y_arr = np.asarray(y)
    folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=seed).split(X, y_arr))
    acc = np.zeros(X.shape[1])
    for tr, te in folds:
        pipe = _pipe(clone(model))
        pipe.fit(X.iloc[tr], y_arr[tr])
        r = permutation_importance(pipe, X.iloc[te], y_arr[te], scoring='roc_auc',
                                   n_repeats=n_repeats, random_state=seed, n_jobs=1)
        acc += r.importances_mean
    return acc / len(folds)


def _clinical_increment(X, feature):
    if feature in CLINICAL_UNITS:
        return CLINICAL_UNITS[feature]
    v = X[feature].dropna()
    if set(v.unique()) <= {0.0, 1.0}:
        return 1, 'yes vs no'
    return 1, 'per 1 unit'


def bootstrap_odds_ratios(X, y, n_boot=500, seed=SEED):
    """Adjusted ORs per clinically meaningful unit, with stratified-bootstrap CIs."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    incs = np.array([_clinical_increment(X, f)[0] for f in X.columns], dtype=float)
    pw = (y == 0).sum() / max((y == 1).sum(), 1)
    base = _pipe(get_model_dictionary(pw)['Logistic Regression (L2)'])
    pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    draws = np.empty((n_boot, X.shape[1]))
    for i in range(n_boot):
        ix = np.concatenate([rng.choice(pos, pos.size, replace=True),
                             rng.choice(neg, neg.size, replace=True)])
        p = clone(base).fit(X.iloc[ix], y[ix])
        draws[i] = (p.named_steps['model'].coef_[0] / p.named_steps['scaler'].scale_) * incs
    pipe = clone(base).fit(X, y)
    point = (pipe.named_steps['model'].coef_[0] / pipe.named_steps['scaler'].scale_) * incs
    return (np.exp(point), np.exp(np.percentile(draws, 2.5, axis=0)),
            np.exp(np.percentile(draws, 97.5, axis=0)))


def clinical_table(X, y, target_label, filename='clinical_predictor_table.csv'):
    print_section(f'STEP 10: CLINICAL PREDICTOR TABLE — {target_label}')
    print('  Adjusted odds ratios from penalised logistic regression, per clinically')
    print('  meaningful unit, with stratified-bootstrap 95% CIs. Permutation importance')
    print('  is mean AUC lost when the predictor is shuffled, measured out of fold.\n')
    or_pt, or_lo, or_hi = bootstrap_odds_ratios(X, y)
    pw = (np.asarray(y) == 0).sum() / max((np.asarray(y) == 1).sum(), 1)
    perm_lr = permutation_importance_cv(
        get_model_dictionary(pw)['Logistic Regression (L2)'], X, y)
    perm_rf = permutation_importance_cv(make_random_forest(oob=False), X, y)
    rows = []
    for i, f in enumerate(X.columns):
        _, unit = _clinical_increment(X, f)
        signif = not (or_lo[i] <= 1.0 <= or_hi[i])
        rows.append({'Predictor': f, 'Unit': unit, 'OR': or_pt[i],
                     '95% CI': f"({or_lo[i]:.2f}-{or_hi[i]:.2f})",
                     'Direction': ('risk' if or_pt[i] > 1 else 'protective') if signif else 'ns',
                     'dAUC (LR)': perm_lr[i], 'dAUC (RF)': perm_rf[i],
                     'Missing %': 100 * X[f].isna().mean()})
    table = pd.DataFrame(rows).sort_values('dAUC (RF)', ascending=False)
    print(table.to_string(index=False, formatters={
        'OR': '{:.2f}'.format, 'dAUC (LR)': '{:+.4f}'.format,
        'dAUC (RF)': '{:+.4f}'.format, 'Missing %': '{:.1f}'.format}))
    n_sig = int((table['Direction'] != 'ns').sum())
    print(f"\n  {n_sig} of {len(table)} predictors have a 95% CI excluding OR = 1.")
    print("  'ns' means the interval includes 1; do not interpret the point estimate.")
    save_csv(table, filename, 'PRESENT')
    return table


def plot_forest(table, target_label, filename='forest_plot_odds_ratios.png'):
    d = table.copy()
    d[['lo', 'hi']] = d['95% CI'].str.strip('()').str.split('-', expand=True).astype(float)
    d = d.sort_values('OR')
    fig, ax = plt.subplots(figsize=(9, 0.34 * len(d) + 1.6))
    ypos = np.arange(len(d))
    sig = d['Direction'] != 'ns'
    ax.hlines(ypos, d['lo'], d['hi'], color=np.where(sig, '#1f4e79', '#b0b0b0'), lw=2)
    ax.scatter(d['OR'], ypos, s=34, color=np.where(sig, '#1f4e79', '#b0b0b0'), zorder=3)
    ax.axvline(1.0, color='#c0392b', ls='--', lw=1)
    ax.set_yticks(ypos)
    ax.set_yticklabels([f"{r.Predictor}  ({r.Unit})" for r in d.itertuples()], fontsize=8)
    ax.set_xscale('log')
    ax.set_xlabel('Adjusted odds ratio (log scale)')
    ax.set_title(f'Adjusted odds ratios — {target_label}\nsolid = 95% CI excludes 1', fontsize=10)
    ax.grid(axis='x', alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, filename), dpi=150)
    plt.close(fig)
    print(f"  [PRESENT   ] {filename}")


def ablation_grid(X, y, t_score, groups, label):
    """Drop one variable at a time and measure what the model loses.

    Permutation importance shuffles a column inside a model that was TRAINED with it,
    so a variable with a close substitute looks unimportant even when the pair matters.
    Ablation refits without the variable entirely, which is the question a clinician is
    actually asking: if this were not collected, would the model be worse? The two
    disagree exactly where collinearity lives, and both are reported.

    No multiplicity correction is applied to the per-model columns. Holm-adjusted
    p-values are given for the primary model only, and the grid is exploratory: with
    18 variables the smallest few deltas are not distinguishable from noise.
    """
    print_section(f'STEP 11: VARIABLE ABLATION GRID — {label}')
    y = np.asarray(y)
    folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED).split(X, y))
    full = oof_scores(X, y, t_score, folds)
    full_auc = {k: roc_auc_score(y, v) for k, v in full.items()}
    primary = max(full_auc, key=full_auc.get)
    # Two models share a first word (LightGBM classifier vs LightGBM regressor, and
    # likewise the forests), so tag the t_score regressors explicitly.
    def short(k):
        return (k.split(' ->')[0] + '->T') if '->' in k else k.split()[0]
    print("  full-model AUCs: " + "   ".join(f"{short(k)} {v:.3f}"
                                             for k, v in full_auc.items()))
    print(f"  primary model for the CI column: {primary} (AUC {full_auc[primary]:.3f})\n")

    rows, pvals = [], []
    for gname, cols in groups.items():
        keep = [c for c in X.columns if c not in cols]
        red = oof_scores(X[keep], y, t_score, folds)
        row = {'Variable': gname, 'Columns dropped': len(cols)}
        for m in full_auc:
            row[f'dAUC {m}'] = full_auc[m] - roc_auc_score(y, red[m])
        d, lo, hi, p_le = bootstrap_delta_auc(y, full[primary], red[primary], n_boot=500)
        row['dAUC primary'] = d
        row['95% CI'] = f"[{lo:+.3f}, {hi:+.3f}]"
        row['p (one-sided)'] = p_le
        row['mean dAUC across models'] = np.mean([row[f'dAUC {m}'] for m in full_auc])
        rows.append(row)
        pvals.append(p_le)
        print(f"  {gname:<24} dAUC(primary) {d:+.4f}  [{lo:+.3f}, {hi:+.3f}]  "
              f"mean across models {row['mean dAUC across models']:+.4f}")

    table = pd.DataFrame(rows)
    table['p (Holm)'] = holm(pvals)
    table = table.sort_values('mean dAUC across models', ascending=False)
    table.insert(0, 'Rank', range(1, len(table) + 1))
    print(f"\n  Positive dAUC = the model is WORSE without the variable, i.e. it carries")
    print(f"  signal the rest of the panel does not. Primary model: {primary}.")
    save_csv(table, f'model_variable_ablation_{label}.csv', 'PRESENT')
    return table, primary


def block_ablation(X, y, t_score, groups, label):
    """Joint ablations, because single-variable ablation cannot see a collinear pair.

    Dropping bmi alone costs nothing when weight_kg is still there to carry adiposity,
    and vice versa — so a one-at-a-time grid scores both near zero and hides the fact
    that body size is the dominant signal. These drop whole blocks, and the last two
    rows ask the question the single-variable grid provokes: does the full panel add
    anything at all to the two inputs OST already uses?
    """
    print_section(f'STEP 11b: BLOCK AND RESTRICTED-PANEL ABLATION — {label}')
    y = np.asarray(y)
    folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED).split(X, y))
    full = oof_scores(X, y, t_score, folds)
    full_auc = {k: roc_auc_score(y, v) for k, v in full.items()}
    primary = max(full_auc, key=full_auc.get)

    tests = [
        ('drop body size (bmi + weight_kg)', 'drop', ['bmi', 'weight_kg']),
        ('drop all menopause/hormone vars', 'drop',
         ['years_since_menopause', 'menopause_type', 'ever_used_estrogen']),
        ('drop all lifestyle vars', 'drop',
         ['ever_smoked', 'alcohol_drinks_day', 'vigorous_activity', 'sedentary_min_day']),
        ('drop all history/family vars', 'drop',
         ['any_prior_fracture', 'steroid_use', 'parental_hip_fracture',
          'family_hx_osteoporosis']),
        ('KEEP only age + weight (OST inputs)', 'keep', ['age', 'weight_kg']),
        ('KEEP only age + bmi', 'keep', ['age', 'bmi']),
    ]
    rows = []
    for name, mode, gs in tests:
        sel = ({g: c for g, c in groups.items() if g not in gs} if mode == 'drop'
               else {g: groups[g] for g in gs})
        Xr = X[[c for cols in sel.values() for c in cols]]
        red = oof_scores(Xr, y, t_score, folds)
        d, lo, hi, p = bootstrap_delta_auc(y, full[primary], red[primary], n_boot=500)
        rows.append({'Test': name, 'Variables in model': len(sel),
                     'Full panel AUC': round(full_auc[primary], 3),
                     'Reduced AUC': round(roc_auc_score(y, red[primary]), 3),
                     'Delta AUC': round(d, 3), '95% CI': f"[{lo:+.3f}, {hi:+.3f}]",
                     'p (one-sided)': round(p, 4), 'Primary model': primary,
                     'Full panel better': bool(lo > 0)})
        print(f"  {name:<38} {len(sel):>2} vars  AUC {rows[-1]['Reduced AUC']:.3f}   "
              f"delta {d:+.3f} [{lo:+.3f}, {hi:+.3f}]   "
              f"{'full panel wins' if lo > 0 else 'no detectable difference'}")

    ost_row = next(r for r in rows if r['Test'].startswith('KEEP only age + weight'))
    if not ost_row['Full panel better']:
        print()
        print("  The full 18-variable panel is NOT distinguishable from a two-variable")
        print("  model on age and weight. That is the same conclusion the OST comparison")
        print("  reaches, arrived at independently, and it is the finding — not a")
        print("  shortfall to be tuned away.")
    save_csv(pd.DataFrame(rows), f'model_block_ablation_{label}.csv', 'PRESENT')
    return pd.DataFrame(rows)


# --- nested CV ----------------------------------------------------------------------

def rank_within_folds(score, folds, n):
    """Map scores to within-fold percentile ranks.

    Different outer folds can select different winners, and a classifier probability
    (0-1) is not on the same scale as a regressor negated T-score (about -1 to 4).
    Pooling raw values corrupts the global ranking. AUC uses order only, so ranking
    within fold makes folds commensurable without changing any within-fold comparison.
    """
    out = np.empty(n, dtype=float)
    s = np.asarray(score, dtype=float)
    for _, te in folds:
        out[te] = pd.Series(s[te]).rank(pct=True).to_numpy()
    return out


def nested_cv_selection(X, y, t_score, n_outer=5, n_inner=3, seed=SEED):
    """Unbiased evaluation of the whole 'fit eight models, keep the best' procedure.

    Picking the winner on the same rows that score it is optimistic: the leaderboard
    best is an upper bound, not an estimate. Here model choice happens strictly inside
    each outer TRAINING fold, and the winner is scored on the untouched outer test fold.
    Candidates span both arms, so the inner CV also decides which arm wins per fold.
    """
    y = np.asarray(y)
    t_score = np.asarray(t_score)
    outer = list(StratifiedKFold(n_splits=n_outer, shuffle=True,
                                 random_state=seed).split(X, y))
    oof = np.zeros(len(y), dtype=float)
    chosen = []
    for tr, te in outer:
        X_tr, y_tr, t_tr = X.iloc[tr], y[tr], t_score[tr]
        pw = (y_tr == 0).sum() / max((y_tr == 1).sum(), 1)
        inner = list(StratifiedKFold(n_splits=n_inner, shuffle=True,
                                     random_state=seed).split(X_tr, y_tr))
        best = (None, -np.inf, None, None)
        for name, model in get_model_dictionary(pw).items():
            p = cross_val_predict(_pipe(model), X_tr, y_tr, cv=inner,
                                  method='predict_proba')[:, 1]
            a = roc_auc_score(y_tr, p)
            if a > best[1]:
                best = (name, a, model, 'clf')
        for name, reg in get_regressor_dictionary().items():
            p = -cross_val_predict(_pipe(reg), X_tr, t_tr, cv=inner)
            a = roc_auc_score(y_tr, p)
            if a > best[1]:
                best = (name, a, reg, 'reg')
        pipe = _pipe(best[2])
        if best[3] == 'clf':
            pipe.fit(X_tr, y_tr)
            oof[te] = pipe.predict_proba(X.iloc[te])[:, 1]
        else:
            pipe.fit(X_tr, t_tr)
            oof[te] = -pipe.predict(X.iloc[te])
        chosen.append(best[0])
    return oof, chosen, outer


# --- calibration (the figure that was missing) ---------------------------------------

def calibration_figure(X, y, label, filename='calibration_curve.png'):
    """Reliability curve for the calibrated forest, plus its Brier score.

    Step 13 thresholds probabilities to decide who gets a DXA referral, which is only
    meaningful if a predicted 0.30 really means about 30%. Discrimination (AUC) says
    nothing about that. This figure was the one known reporting gap: the only
    calibration plotting code left the repo with SF_new1.py.
    """
    y = np.asarray(y)
    folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED).split(X, y))
    cal = CalibratedClassifierCV(_pipe(make_random_forest(oob=False)),
                                 method='sigmoid', cv=3)
    p_cal = cross_val_predict(cal, X, y, cv=folds, method='predict_proba')[:, 1]
    p_raw = cross_val_predict(_pipe(make_random_forest(oob=False)), X, y, cv=folds,
                              method='predict_proba')[:, 1]
    fig, ax = plt.subplots(figsize=(5.6, 5.4))
    ax.plot([0, 1], [0, 1], ls='--', lw=1, color='#888', label='perfect calibration')
    for p, name, colour in [(p_raw, 'Random forest (uncalibrated)', '#9a3412'),
                            (p_cal, 'Random forest (sigmoid-calibrated)', '#0e6b78')]:
        frac, mean_pred = calibration_curve(y, p, n_bins=10, strategy='quantile')
        ax.plot(mean_pred, frac, 'o-', color=colour, lw=1.8, ms=5,
                label=f"{name}  Brier {brier_score_loss(y, p):.3f}  "
                      f"AUC {roc_auc_score(y, p):.3f}")
    ax.set_xlabel('Mean predicted probability (out of fold)')
    ax.set_ylabel('Observed fraction of cases')
    ax.set_title(f'Calibration — {label}', fontsize=10)
    ax.legend(fontsize=7, loc='upper left')
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, filename), dpi=150)
    plt.close(fig)
    print(f"  [PRESENT   ] {filename}   calibrated Brier "
          f"{brier_score_loss(y, p_cal):.3f} vs raw {brier_score_loss(y, p_raw):.3f}")
    return p_cal


def referral_table(y, score, cutoffs=(0.50, 0.40, 0.35, 0.30, 0.25), as_quantile=False):
    """Screening cost in the unit a clinician decides on: DXA scans per case found."""
    y = np.asarray(y)
    P, N = int(y.sum()), len(y)
    rows = []
    for c in cutoffs:
        thr = np.quantile(score, 1 - c) if as_quantile else c
        pred = (score >= thr).astype(int)
        tp = int(((pred == 1) & (y == 1)).sum())
        flagged = int(pred.sum())
        rows.append({'Cutoff': f"{c:.2f}", 'Sensitivity': f"{tp / P:.1%}" if P else 'n/a',
                     'DXAs ordered': flagged, 'Cases found': tp, 'Missed': P - tp,
                     'PPV': f"{tp / flagged:.1%}" if flagged else 'n/a',
                     'Scans per case': f"{flagged / tp:.2f}" if tp else 'inf'})
    rows.append({'Cutoff': 'scan all', 'Sensitivity': '100.0%', 'DXAs ordered': N,
                 'Cases found': P, 'Missed': 0, 'PPV': f"{P / N:.1%}",
                 'Scans per case': f"{N / P:.2f}" if P else 'inf'})
    return pd.DataFrame(rows)
