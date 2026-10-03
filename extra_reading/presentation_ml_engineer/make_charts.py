"""Charts for the ML-engineer briefing deck. Reads only current outputs/ and the
analysis cohort; regenerate after any pipeline rerun."""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "outputs")
CH = os.path.join(HERE, "charts")

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#fcfcfb"
plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 12, "axes.edgecolor": GRID,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
})

def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(CH, name), dpi=200)
    plt.close(fig)

# 1. Attrition funnel
# counts from _run_final.log (apply_filters / apply_menopause_gate)
steps = [("All NHANES respondents, 5 cycles", 56769), ("Female", 28644),
         ("Non-Hispanic White", 10672), ("Aged 50-65", 1639),
         ("Femoral-neck DXA available", 1308), ("Postmenopausal (analysis cohort)", 1111)]
fig, ax = plt.subplots(figsize=(9, 4.6))
labels = [s[0] for s in steps][::-1]
vals = [s[1] for s in steps][::-1]
ax.barh(labels, vals, color=BLUE, height=0.6)
ax.set_xscale("log")
for y, v in enumerate(vals):
    ax.text(v * 1.08, y, f"{v:,}", va="center", color=INK, fontsize=12)
ax.set_xlim(500, 200000)
ax.set_xlabel("Respondents (log scale)")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.tick_params(axis="y", length=0)
save(fig, "attrition.png")

# 2. Nested-CV verdict: model vs comparators, both targets
nv = pd.read_csv(os.path.join(OUT, "nested_cv_verdict.csv"))
fig, axes = plt.subplots(1, 2, figsize=(11, 3.7), sharey=False)
for ax, tgt, title in zip(axes, ["Osteopenia+ (T<=-1.0)", "Osteoporosis (T<=-2.5)"],
                          ["Osteopenia or worse (T ≤ −1.0), 645 events",
                           "Osteoporosis (T ≤ −2.5), 76 events"]):
    sub = nv[nv.Target == tgt]
    w = sub[sub.Comparator == "Weight alone"].iloc[0]
    o = sub[sub.Comparator.str.startswith("OST")].iloc[0]
    names = ["Weight alone", "OST formula", "Full ML panel\n(nested CV)"]
    vals = [w["Comparator AUC"], o["Comparator AUC"], o["Nested AUC"]]
    cols = [AQUA, ORANGE, BLUE]
    ax.bar(names, vals, color=cols, width=0.55)
    for x, v in enumerate(vals):
        ax.text(x, v + 0.004, f"{v:.3f}", ha="center", color=INK, fontsize=13, fontweight="bold")
    ax.set_ylim(0.70, 0.81)
    ax.set_title(title, color=INK, fontsize=12.5, loc="left")
    ax.set_ylabel("Out-of-fold AUC (axis starts at 0.70)")
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
save(fig, "nested_verdict.png")

# 3. AUC decomposition
dec = pd.read_csv(os.path.join(OUT, "auc_decomposition.csv"))
fig, ax = plt.subplots(figsize=(9, 4.8))
import numpy as np
x = np.arange(len(dec)); bw = 0.36
ax.bar(x - bw/2 - 0.01, dec["Best AUC"], bw, color=BLUE, label="Best ML model")
ax.bar(x + bw/2 + 0.01, dec["OST AUC"], bw, color=ORANGE, label="OST formula")
for i, r in dec.iterrows():
    ax.text(i - bw/2, r["Best AUC"] + 0.004, f"{r['Best AUC']:.3f}", ha="center", fontsize=11, color=INK)
    ax.text(i + bw/2, r["OST AUC"] + 0.004, f"{r['OST AUC']:.3f}", ha="center", fontsize=11, color=INK)
short = ["A. 6 cycles, all DXA\n(duplicates present)  n=1,484",
         "B. 6 cycles, postmeno\n(duplicates present)  n=1,272",
         "C. 5 cycles, all DXA\n(deduplicated)  n=1,308",
         "D. 5 cycles, postmeno\n(shipped)  n=1,111"]
ax.set_xticks(x); ax.set_xticklabels(short, fontsize=9.5)
ax.set_ylim(0.70, 0.87); ax.set_ylabel("AUC, T ≤ −1.0 (axis starts at 0.70)")
ax.legend(frameon=False, loc="upper right", labelcolor=INK2)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
save(fig, "auc_decomposition.png")

# 4. Block ablation
ab = pd.read_csv(os.path.join(OUT, "model_block_ablation_osteopenia.csv"))
lab = {"drop body size (bmi + weight_kg)": "Drop body size (bmi + weight)",
       "drop all menopause/hormone vars": "Drop all menopause / hormone",
       "drop all lifestyle vars": "Drop all lifestyle",
       "drop all history/family vars": "Drop all history / family",
       "KEEP only age + weight (OST inputs)": "Keep ONLY age + weight",
       "KEEP only age + bmi": "Keep ONLY age + bmi"}
ab["L"] = ab.Test.map(lab)
ab = ab.iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 4.8))
cols = [ORANGE if "body" in t else BLUE for t in ab.Test]
ax.barh(ab.L, ab["Reduced AUC"], color=cols, height=0.6)
full = ab["Full panel AUC"].iloc[0]
ax.axvline(full, color=INK2, ls="--", lw=1.2)
ax.text(full - 0.002, len(ab) - 0.45, f"full 20-column panel {full:.3f}", color=INK2, fontsize=11, ha="right")
for y, (v, n) in enumerate(zip(ab["Reduced AUC"], ab["Variables in model"])):
    ax.text(v - 0.003, y, f"{v:.3f}  ({n} vars)", va="center", ha="right", color="white", fontsize=11, fontweight="bold")
ax.set_xlim(0.55, 0.80); ax.set_xlabel("AUC after refit, T ≤ −1.0 (axis starts at 0.55)")
ax.tick_params(axis="y", length=0)
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
save(fig, "block_ablation.png")

# 5. Missingness per model variable
t1 = pd.read_csv(os.path.join(OUT, "table_one.csv"))
t1 = t1[t1.Variable != "n"].copy()
t1["m"] = t1["Missing %"].astype(float)
t1 = t1.sort_values("m")
fig, ax = plt.subplots(figsize=(8, 6.8))
ax.barh(t1.Variable, t1.m, color=BLUE, height=0.65)
for y, v in enumerate(t1.m):
    n_obs = round(1111 * (1 - v / 100))
    ax.text(v + 0.25, y, f"{v:.1f}%  (n={n_obs:,})", va="center", fontsize=10, color=INK)
ax.set_xlim(0, 21); ax.set_xlabel("Missing % of 1,111 women (median-imputed in-fold)")
ax.tick_params(axis="y", length=0, labelsize=10.5)
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
save(fig, "missingness.png")

# 6. Referral table: scans per case
rt = pd.read_csv(os.path.join(OUT, "referral_table.csv"))
print("charts written to", CH)
