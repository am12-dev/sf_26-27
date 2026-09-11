"""Missingness table + funnel figures for the statistician.

  missingness_by_variable.csv   one row per variable: counts, %, and whether the
                                missingness is associated with the outcome
  fig_missing_by_variable.png   how many participants are missing each variable
  fig_missing_funnel.png        complete-case sample size as variables are added
  fig_missing_per_patient.png   how many variables each participant is missing

The outcome-association column is the one that answers "what should be imputed":
missingness unrelated to the outcome is benign to impute, missingness that tracks
the outcome biases whatever is imputed into it.
"""
import importlib.util
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'Notes', 'figures')
os.makedirs(OUT, exist_ok=True)
spec = importlib.util.spec_from_file_location('m', os.path.join(ROOT, 'OsteoporosisML.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

d = pd.read_csv(os.path.join(ROOT, 'data', 'processed', 'option_b_v4_final.csv'), low_memory=False)
_, X, y = m.define_features(d)
N = len(X)

# --- palette (dataviz reference instance, light surface) -------------------
SURFACE, INK, INK2, MUTED, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#8a8880', '#e2e1dc'
GOOD, WARN, SERIOUS, CRIT = '#0ca30c', '#fab219', '#ec835a', '#d03b3b'
RAMP = ['#86b6ef', '#5598e7', '#2a78d6', '#256abf', '#104281']
S1 = '#2a78d6'
plt.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
    'font.family': 'DejaVu Sans', 'text.color': INK, 'axes.labelcolor': INK2,
    'axes.edgecolor': GRID, 'xtick.color': INK2, 'ytick.color': INK2, 'font.size': 10,
    'axes.titlesize': 12.5, 'axes.titlecolor': INK,
    'axes.spines.top': False, 'axes.spines.right': False,
})


def band(pc):
    if pc == 0:
        return GOOD, 'complete'
    if pc < 5:
        return GOOD, 'impute freely (<5%)'
    if pc < 20:
        return WARN, 'impute with care (5-20%)'
    if pc < 50:
        return SERIOUS, 'imputation dominates (20-50%)'
    return CRIT, 'mostly invented (>50%)'


# ==================================================================== table
rows = []
for c in X.columns:
    miss = X[c].isna()
    n_miss = int(miss.sum())
    pc = 100 * n_miss / N
    col, lab = band(pc)
    # is missingness associated with the outcome?
    if 0 < n_miss < N:
        tab = pd.crosstab(miss, y)
        chi2, p, _, _ = stats.chi2_contingency(tab)
        r_miss, r_obs = y[miss].mean(), y[~miss].mean()
        assoc = (f'{100*(r_miss-r_obs):+.1f}pp', f'{p:.3f}',
                 'YES - informative' if p < 0.05 else 'no')
    else:
        r_miss, r_obs = np.nan, y.mean()
        assoc = ('', '', 'n/a - nothing missing')
    vals = X[c].dropna()
    kind = 'binary' if set(np.unique(vals)) <= {0.0, 1.0} else 'continuous'
    rows.append({
        'Variable': c,
        'Type': kind,
        'Participants with a value': N - n_miss,
        'Participants MISSING': n_miss,
        'Missing %': round(pc, 1),
        'Imputation band': lab,
        'Low bone mass among MISSING': f'{r_miss:.1%}' if n_miss else '',
        'Low bone mass among OBSERVED': f'{r_obs:.1%}',
        'Difference': assoc[0],
        'Chi-square p': assoc[1],
        'Missingness informative?': assoc[2],
    })
tab = pd.DataFrame(rows).sort_values('Missing %', ascending=False)
p_tab = os.path.join(ROOT, 'Notes', 'missingness_by_variable.csv')
tab.to_csv(p_tab, index=False)
print(f'  missingness_by_variable.csv: {len(tab)} variables')
print()
print(tab[['Variable', 'Participants MISSING', 'Missing %', 'Imputation band',
           'Difference', 'Chi-square p', 'Missingness informative?']].to_string(index=False))

# ============================================ fig 1: missing per variable
srt = tab.sort_values('Missing %')
fig, ax = plt.subplots(figsize=(9.6, 6.4))
yy = np.arange(len(srt))
cols = [band(p)[0] for p in srt['Missing %']]
ax.barh(yy, srt['Missing %'], color=cols, height=0.68, zorder=3)
for i, (pc, nm) in enumerate(zip(srt['Missing %'], srt['Participants MISSING'])):
    ax.text(pc + 0.7, i, f'{int(nm)}  ({pc:.1f}%)', va='center', ha='left',
            fontsize=9.3, color=INK)
ax.set_yticks(yy)
ax.set_yticklabels(srt['Variable'], fontsize=9.4, family='monospace')
ax.set_xlim(0, 100)
ax.set_xlabel('Participants missing this variable (% of 1,484)')
ax.set_title('How many participants are missing each variable\n'
             'green < 5%   amber 5-20%   orange 20-50%   red > 50%')
ax.grid(axis='x', color=GRID, lw=0.7, zorder=0)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'fig_missing_by_variable.png'), dpi=200, bbox_inches='tight')
plt.close(fig)
print('\n  fig_missing_by_variable.png')

# ============================================ fig 2: the funnel
order = X.isna().mean().sort_values().index.tolist()
steps, kept = [], []
for i in range(1, len(order) + 1):
    n = int(X[order[:i]].notna().all(axis=1).sum())
    steps.append(i)
    kept.append(n)

fig, (ax, axt) = plt.subplots(1, 2, figsize=(13.2, 5.4),
                              gridspec_kw={'width_ratios': [2.35, 1]})
axt.axis('off')
ax.plot(steps, kept, '-o', color=S1, lw=2.2, ms=6, zorder=4)
ax.fill_between(steps, kept, color=S1, alpha=0.10, zorder=2)
ax.axhline(N, color=MUTED, ls=':', lw=1.2, zorder=1)
ax.text(0.6, N + 24, f'full cohort {N:,}', fontsize=9.3, color=INK2)
# The steepest drops are listed in a side panel rather than annotated in place -
# in-plot labels for 22 closely spaced points collide with each other and the
# title no matter how the offsets are tuned. At step s the variable just added
# is order[s-1]. Each listed point is marked on the curve.
drops = sorted(range(1, len(kept)), key=lambda i: kept[i - 1] - kept[i], reverse=True)[:6]
ax.scatter([steps[i] for i in drops], [kept[i] for i in drops],
           s=64, facecolor=SURFACE, edgecolor=CRIT, lw=1.8, zorder=5)
ax.scatter([steps[-1]], [kept[-1]], s=130, color=CRIT, zorder=6)

axt.text(0, 0.97, 'THE SIX BIGGEST DROPS', fontsize=10, color=CRIT,
         family='monospace', va='top', weight='bold')
axt.text(0, 0.90, 'requiring this variable costs:', fontsize=9.3, color=INK2, va='top')
for j, i in enumerate(sorted(drops, key=lambda i: kept[i - 1] - kept[i], reverse=True)):
    s, lost = steps[i], kept[i - 1] - kept[i]
    axt.text(0, 0.80 - j * 0.085, f'−{lost:>4}', fontsize=11.5, color=CRIT,
             family='monospace', va='top', weight='bold')
    axt.text(0.20, 0.80 - j * 0.085, order[s - 1], fontsize=10, color=INK,
             family='monospace', va='top')
    axt.text(0.20, 0.755 - j * 0.085, f'{kept[i]:,} participants left',
             fontsize=8.8, color=INK2, va='top')
axt.text(0, 0.235, f'All {len(order)} required: {kept[-1]} remain',
         fontsize=11, color=CRIT, va='top', weight='bold')
axt.text(0, 0.175, 'Every participant is missing at\nleast one variable, so there is\n'
                   'no complete-case sample at all.',
         fontsize=9.3, color=INK2, va='top')
axt.text(0, 0.045, 'Circled points are marked on\nthe curve.', fontsize=8.8,
         color=MUTED, va='top')
ax.set_xlabel('Number of variables required to be non-missing (added most-complete first)')
ax.set_ylabel('Participants retained')
ax.set_title('Complete-case funnel: the cost of requiring every variable')
ax.set_xticks(range(0, len(order) + 1, 2))
ax.set_ylim(-60, N + 130)
ax.grid(color=GRID, lw=0.7, zorder=0)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'fig_missing_funnel.png'), dpi=200, bbox_inches='tight')
plt.close(fig)
print('  fig_missing_funnel.png')

# ============================================ fig 3: per-patient burden
per = X.isna().sum(axis=1)
vc = per.value_counts().sort_index()
fig, ax = plt.subplots(figsize=(9.2, 4.4))
cols3 = [RAMP[min(int(k), len(RAMP) - 1)] if k <= 2 else RAMP[-1] for k in vc.index]
ax.bar(vc.index, vc.values, color=cols3, width=0.72, zorder=3)
for k, v in vc.items():
    ax.text(k, v + 12, f'{v}', ha='center', fontsize=9.3, color=INK)
ax.set_xlabel('Number of the 22 variables this participant is missing')
ax.set_ylabel('Participants')
ax.set_title(f'Missing-data burden per participant\n'
             f'{int((per == 0).sum())} of {N} are missing nothing; median {int(per.median())}, max {int(per.max())}')
ax.set_xticks(range(0, int(per.max()) + 1))
ax.grid(axis='y', color=GRID, lw=0.7, zorder=0)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'fig_missing_per_patient.png'), dpi=200, bbox_inches='tight')
plt.close(fig)
print('  fig_missing_per_patient.png')

print()
print(f'  participants missing nothing        : {int((per == 0).sum())}')
print(f'  participants missing exactly one    : {int((per == 1).sum())}')
print(f'  participants missing two or more    : {int((per >= 2).sum())}')
print(f'  median variables missing per patient: {per.median():.0f}   max {per.max()}')
print()
inf = tab[tab['Missingness informative?'] == 'YES - informative']
print(f'  variables whose MISSINGNESS tracks the outcome (p < 0.05): {len(inf)}')
for _, r in inf.iterrows():
    print(f'    {r.Variable:24s} {r["Missing %"]:5.1f}% missing   '
          f'outcome differs by {r.Difference}  (p = {r["Chi-square p"]})')
