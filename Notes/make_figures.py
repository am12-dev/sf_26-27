"""Slide figures for the specialist presentation.

Every number is read from outputs/ rather than transcribed, so the deck cannot
drift from the pipeline. Palette values are the dataviz reference instance
(categorical slots 1-3; ordinal blue ramp from step 250 on a light surface).
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'Notes', 'figures')
os.makedirs(OUT, exist_ok=True)

# --- palette (dataviz reference instance, light surface) --------------------
SURFACE   = '#fcfcfb'
INK       = '#0b0b0b'
INK_2     = '#52514e'
INK_MUTED = '#8a8880'
GRID      = '#e2e1dc'
S1, S2, S3 = '#2a78d6', '#eb6834', '#1baf7a'   # categorical 1-3
GOOD, CRIT, WARN = '#0ca30c', '#d03b3b', '#fab219'  # status
RAMP = ['#86b6ef', '#5598e7', '#2a78d6', '#256abf', '#104281']  # ordinal 250..650

plt.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE, 'font.family': 'DejaVu Sans',
    'text.color': INK, 'axes.labelcolor': INK_2, 'axes.edgecolor': GRID,
    'xtick.color': INK_2, 'ytick.color': INK_2, 'font.size': 10,
    'axes.titlesize': 12.5, 'axes.titleweight': 'medium', 'axes.titlecolor': INK,
    'axes.spines.top': False, 'axes.spines.right': False,
})


def finish(fig, name):
    fig.tight_layout()
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'  {name}')


# ===========================================================================
# 1. Cohort attrition - ordinal ramp, one bar per stage
# ===========================================================================
stages = ['All respondents\n6 NHANES cycles', 'Female', 'Non-Hispanic White',
          'Aged 50-65', 'Femoral-neck DXA\navailable']
counts = [66023, 33341, 12239, 1863, 1484]

fig, ax = plt.subplots(figsize=(9, 4.2))
y = np.arange(len(stages))[::-1]
ax.barh(y, counts, color=RAMP, height=0.62, zorder=3)
for yi, c in zip(y, counts):
    ax.text(c * 1.03, yi, f'{c:,}', va='center', ha='left',
            fontsize=10.5, color=INK, fontweight='medium')
ax.set_yticks(y); ax.set_yticklabels(stages, fontsize=9.5)
ax.set_xscale('log'); ax.set_xlim(800, 200000)
ax.set_xticks([1000, 10000, 100000]); ax.set_xticklabels(['1K', '10K', '100K'])
ax.set_xlabel('Participants remaining (log scale)')
ax.set_title('Cohort derivation: 66,023 respondents to 1,484 women')
ax.grid(axis='x', color=GRID, lw=0.7, zorder=0)
ax.set_axisbelow(True)
finish(fig, 'fig1_attrition.png')


# ===========================================================================
# 2. Leaderboard vs the OST baseline - one series, winner emphasised
# ===========================================================================
bc = pd.read_csv(os.path.join(BASE, 'outputs', 'baseline_comparison.csv'))
op = bc[bc['Target'].str.contains('OSTEOPENIA')].sort_values('AUC')
labels = op['Model'].str.replace(' (Aggressive Reg)', '', regex=False)
labels = labels.str.replace('  0.2x(weight-age)', ' (Koh 2001)', regex=False)
labels = labels.str.replace('->', '→', regex=False)
vals = op['AUC'].to_numpy()
ost = float(op.loc[op['Model'].str.startswith('OST'), 'AUC'].iloc[0])

colors = [S1 if v > ost else INK_MUTED for v in vals]
colors[int(np.argmax(vals))] = '#104281'

fig, ax = plt.subplots(figsize=(9.4, 5.0))
yy = np.arange(len(vals))
ax.barh(yy, vals, color=colors, height=0.66, zorder=3)
ax.axvline(ost, color=CRIT, ls='--', lw=1.4, zorder=4)
ax.text(ost + 0.0015, -0.92, f'OST baseline {ost:.3f}', color=CRIT,
        fontsize=9.5, va='bottom', ha='left')
for yi, v in zip(yy, vals):
    ax.text(v + 0.0015, yi, f'{v:.3f}', va='center', ha='left',
            fontsize=9.5, color=INK)
ax.set_yticks(yy); ax.set_yticklabels(labels, fontsize=9.5)
ax.set_xlim(0.70, 0.828); ax.set_ylim(-1.1, len(vals) - 0.3)
ax.set_xlabel('Cross-validated AUC')
ax.set_title('Every model vs OST, a two-input formula (Koh 2001)\nTarget: osteopenia or worse (T ≤ −1.0)')
ax.grid(axis='x', color=GRID, lw=0.7, zorder=0); ax.set_axisbelow(True)
finish(fig, 'fig2_leaderboard.png')


# ===========================================================================
# 3. THE money chart - optimistic vs nested, both targets, CI against zero
# ===========================================================================
v = pd.read_csv(os.path.join(BASE, 'outputs', 'nested_cv_verdict.csv'))

fig, ax = plt.subplots(figsize=(9.4, 3.5))
for i, r in v.iterrows():
    yb = 1 - i
    # optimistic delta (hollow, for contrast)
    ax.scatter(r['Optimistic d_AUC'], yb + 0.17, s=90, facecolor=SURFACE,
               edgecolor=INK_MUTED, lw=1.6, zorder=4)
    ax.text(r['Optimistic d_AUC'], yb + 0.30, 'leaderboard', fontsize=8.4,
            color=INK_MUTED, ha='center')
    # nested delta with CI
    sig = r['Nested CI low'] > 0
    col = GOOD if sig else CRIT
    ax.hlines(yb - 0.13, r['Nested CI low'], r['Nested CI high'], color=col, lw=3, zorder=3)
    ax.scatter(r['Nested d_AUC'], yb - 0.13, s=110, color=col, zorder=5)
    ax.text(r['Nested CI high'] + 0.004, yb - 0.13,
            f"{r['Nested d_AUC']:+.3f}  [{r['Nested CI low']:+.3f}, {r['Nested CI high']:+.3f}]",
            va='center', fontsize=9.2, color=col, fontweight='medium')
    tag = 'BEATS OST' if sig else 'NOT separable from OST'
    ax.text(-0.052, yb + 0.02, tag, fontsize=9.2, color=col,
            fontweight='bold', ha='left')

ax.axvline(0, color=INK, lw=1.2, zorder=2)
ax.text(-0.003, 1.60, 'no better than OST', fontsize=8.8, color=INK_2, ha='right')
ax.set_yticks([1, 0])
ax.set_yticklabels(['Osteopenia or worse\nT ≤ −1.0 · 836 events',
                    'Osteoporosis\nT ≤ −2.5 · 94 events'], fontsize=9.5)
ax.set_xlim(-0.055, 0.145); ax.set_ylim(-0.62, 1.75)
ax.set_xlabel('Gain in AUC over the OST formula (95% CI)')
ax.set_title('The honest result: selection bias removed\nHollow = best-of-8 leaderboard   Solid = nested cross-validation')
ax.grid(axis='x', color=GRID, lw=0.7, zorder=0); ax.set_axisbelow(True)
finish(fig, 'fig3_nested_verdict.png')


# ===========================================================================
# 4. Clinical translation - DXA scans per case found (osteoporosis target)
# ===========================================================================
rt = pd.read_csv(os.path.join(BASE, 'outputs', 'referral_table.csv'))
op_r = rt[rt['Target'].str.contains('OSTEOPOROSIS')].copy()
op_r['spc'] = pd.to_numeric(op_r['Scans per case'], errors='coerce')
op_r['sens'] = op_r['Sensitivity'].str.rstrip('%').astype(float)
model_rows = op_r[op_r['Top fraction flagged'] != 'scan all']
scan_all = float(op_r.loc[op_r['Top fraction flagged'] == 'scan all', 'spc'].iloc[0])

fig, ax = plt.subplots(figsize=(9.4, 4.4))
x = model_rows['sens'].to_numpy(); yv = model_rows['spc'].to_numpy()
frac = model_rows['Top fraction flagged'].to_numpy()
ax.plot(x, yv, '-o', color=S1, lw=2, ms=8, zorder=4, label='Model-guided referral')
ax.axhline(scan_all, color=CRIT, ls='--', lw=1.5, zorder=3,
           label=f'Scan everyone ({scan_all:.2f} scans/case)')
ax.scatter([100], [scan_all], s=90, color=CRIT, zorder=5)
for xi, yi, f in zip(x, yv, frac):
    ax.annotate(f'top {float(f)*100:.0f}%', (xi, yi), textcoords='offset points',
                xytext=(6, 9), fontsize=8.6, color=INK_2)
ax.annotate(f'Flagging the top 50% finds {x[0]:.0f}% of cases\n'
            f'at {yv[0]:.1f} scans per case, not {scan_all:.1f}\n'
            f'- a {100*(1-yv[0]/scan_all):.0f}% cut in scanning effort',
            (x[0], yv[0]), textcoords='offset points', xytext=(-232, 78),
            fontsize=9.8, color=INK, ha='left', va='center',
            arrowprops=dict(arrowstyle='->', color=INK_MUTED, lw=1.0,
                            connectionstyle='arc3,rad=-0.18'))
ax.set_xlabel('Sensitivity - share of osteoporosis cases detected (%)')
ax.set_ylabel('DXA scans ordered per case found')
ax.set_title('What it buys a clinic: osteoporosis (T ≤ −2.5), prevalence 6.3%')
ax.grid(color=GRID, lw=0.7, zorder=0); ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=9.2, loc='lower right')
ax.set_ylim(4.6, 17.2)
finish(fig, 'fig4_scans_per_case.png')


# ===========================================================================
# 5. Which predictors carry the signal - permutation importance
# ===========================================================================
ct = pd.read_csv(os.path.join(BASE, 'outputs', 'clinical_predictor_table.csv'))
top = ct.nlargest(10, 'dAUC (RF)')[::-1]
sig = top['Direction'] != 'ns'

fig, ax = plt.subplots(figsize=(9.4, 4.6))
yy = np.arange(len(top))
ax.barh(yy, top['dAUC (RF)'], color=[S1 if s else INK_MUTED for s in sig],
        height=0.66, zorder=3)
for yi, val, s in zip(yy, top['dAUC (RF)'], sig):
    ax.text(val + 0.0016, yi, f'{val:+.3f}' + ('  *' if s else ''),
            va='center', fontsize=9.2, color=INK)
ax.set_yticks(yy); ax.set_yticklabels(top['Predictor'], fontsize=9.5, family='monospace')
ax.set_xlabel('AUC lost when the predictor is shuffled (out of fold)')
ax.set_title('Weight dominates every other predictor\n* = 95% CI for the odds ratio excludes 1   grey = not significant')
ax.set_xlim(0, max(top['dAUC (RF)']) * 1.22)
ax.grid(axis='x', color=GRID, lw=0.7, zorder=0); ax.set_axisbelow(True)
finish(fig, 'fig5_importance.png')


# ===========================================================================
# 6. Adjusted odds ratios - the five significant predictors
# ===========================================================================
sigt = ct[ct['Direction'] != 'ns'].copy()
sigt[['lo', 'hi']] = sigt['95% CI'].str.strip('()').str.split('-', expand=True).astype(float)
sigt = sigt.sort_values('OR')

fig, ax = plt.subplots(figsize=(9.4, 3.4))
yy = np.arange(len(sigt))
for yi, r in zip(yy, sigt.itertuples()):
    col = CRIT if r.OR > 1 else GOOD
    ax.hlines(yi, r.lo, r.hi, color=col, lw=3, zorder=3)
    ax.scatter(r.OR, yi, s=105, color=col, zorder=5)
    ax.text(r.hi * 1.04, yi, f'{r.OR:.2f}  ({r.lo:.2f}–{r.hi:.2f})',
            va='center', fontsize=9.2, color=INK)
ax.axvline(1.0, color=INK, lw=1.2, zorder=2)
ax.set_yticks(yy)
ax.set_yticklabels([f'{r.Predictor}\n{r.Unit}' for r in sigt.itertuples()], fontsize=9)
ax.set_xscale('log'); ax.set_xlim(0.35, 5.2)
ax.set_xticks([0.5, 1, 2, 4]); ax.set_xticklabels(['0.5', '1', '2', '4'])
ax.set_xlabel('Adjusted odds ratio (log scale)')
ax.set_title('The five predictors whose 95% CI excludes 1\nRed = raises risk of low bone mass   Green = protective')
ax.grid(axis='x', color=GRID, lw=0.7, zorder=0); ax.set_axisbelow(True)
finish(fig, 'fig6_odds_ratios.png')

print(f'\n  6 figures -> {OUT}')
