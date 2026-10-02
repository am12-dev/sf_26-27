"""Why did the headline AUC fall from 0.810 to ~0.751?

Two things changed at once, and a reviewer will want them separated:
  1. 2017_2018 left CYCLES, removing 176 duplicated respondents that straddled
     train and test folds.
  2. The cohort became postmenopausal only, dropping 156 still-cycling women who
     were younger and much denser (mean T -0.473 vs -1.140) and therefore easy
     negatives that flatter any model.

Only the first is a bug fix. The second is a deliberate narrowing that SHOULD cost
discrimination, because it removes variance the model was being rewarded for
explaining. Holding the feature panel and the model set fixed across all four stages
is what makes the two separable.

Run after OsteoporosisML.py exists:  python _decompose.py
"""
import importlib.util
import os
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = next(p for p in ('OsteoporosisML.py', '_stage.py')
              if os.path.exists(os.path.join(HERE, p)))
spec = importlib.util.spec_from_file_location('osteo', os.path.join(HERE, TARGET))
m = importlib.util.module_from_spec(spec)
sys.modules['osteo'] = m
spec.loader.exec_module(m)

SIX_CYCLES = m.CYCLES + [{'name': '2017_2018', 'suffix': 'J', 'prefix': ''}]


def evaluate(df, encoded, label, note):
    """Out-of-fold AUC of the whole panel, plus OST, on one cohort definition."""
    X = m.build_feature_matrix(encoded, m.FEATURE_GROUPS)
    y = df['at_risk'].to_numpy()
    t = df['t_score'].to_numpy()
    folds = list(StratifiedKFold(n_splits=5, shuffle=True,
                                 random_state=m.SEED).split(X, y))
    scores = m.oof_scores(X, y, t, folds)
    aucs = {k: roc_auc_score(y, v) for k, v in scores.items()}
    best = max(aucs, key=aucs.get)
    ost = m.compute_baselines(df)['OST  0.2x(weight-age)']
    ost_auc = roc_auc_score(y, ost)
    d, lo, hi, _ = m.bootstrap_delta_auc(y, scores[best], ost, n_boot=500)
    print(f"  {label:<44} n {len(df):>5,}  events {int(y.sum()):>4}   "
          f"best {aucs[best]:.3f} ({best})   OST {ost_auc:.3f}   "
          f"delta {d:+.3f} [{lo:+.3f}, {hi:+.3f}]")
    return {'Stage': label, 'What changed': note, 'n': len(df),
            'Events (T<=-1.0)': int(y.sum()), 'Best model': best,
            'Best AUC': round(aucs[best], 3), 'OST AUC': round(ost_auc, 3),
            'Delta vs OST': round(d, 3), '95% CI': f"[{lo:+.3f}, {hi:+.3f}]",
            'Beats OST': bool(lo > 0)}


def prepare(cycles, n_expect):
    """Load and derive under a given cycle list, with the cohort assert relaxed."""
    m.CYCLES = cycles
    m.N_DXA_COHORT = n_expect
    df = m.load_and_merge_cycles()
    df = m.apply_filters(df)
    df = m.compute_tscores(df)
    df = m.compute_menopause_variables(df)
    df = m.compute_estrogen_variables(df)
    df = m.compute_derived_variables(df, SUPP, DAY2)
    return df.rename(columns=m.RENAME)


if __name__ == '__main__':
    m.setup_directories()
    SUPP = m.load_supplements()
    DAY2 = m.load_day2_dietary()
    rows = []

    m.print_section('DECOMPOSITION: WHERE THE AUC WENT')

    six = prepare(SIX_CYCLES, 1484)   # the published count: 6 cycles, duplicates included
    rows.append(evaluate(six, m.encode_features(six),
                         'A. 6 cycles, all DXA (as published)',
                         'baseline: contains 176 duplicated respondents'))

    post6 = six[six['RHQ031'] == 0.0]
    rows.append(evaluate(post6, m.encode_features(post6),
                         'B. 6 cycles, postmenopausal only',
                         'cohort narrowed; duplicates still present'))

    five = prepare([c for c in SIX_CYCLES if c['name'] != '2017_2018'], 1308)
    rows.append(evaluate(five, m.encode_features(five),
                         'C. 5 cycles, all DXA',
                         'duplicates removed; cohort still unrestricted'))

    post5 = five[five['RHQ031'] == 0.0]
    rows.append(evaluate(post5, m.encode_features(post5),
                         'D. 5 cycles, postmenopausal (shipped)',
                         'both changes applied — this is the analysis cohort'))

    table = pd.DataFrame(rows)
    a, b, c, d = (r['Best AUC'] for r in rows)
    print(f"\n  duplicate fix alone      (A -> C): {c - a:+.3f}")
    print(f"  menopause gate alone     (A -> B): {b - a:+.3f}")
    print(f"  both, as shipped         (A -> D): {d - a:+.3f}")
    print("\n  The duplicate component is a bug fix: that discrimination was never real.")
    print("  The menopause component is a deliberate narrowing — removing younger,")
    print("  denser, still-cycling women takes away easy negatives, so a lower AUC on a")
    print("  harder and more clinically relevant cohort is the expected cost, not a loss.")
    m.save_csv(table, 'auc_decomposition.csv', 'METHODS')
