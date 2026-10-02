"""Build the ML-engineer briefing deck (PPTX, speaker notes on every slide) and a
companion presenter-notes document (DOCX).

Inputs: outputs/*.csv and outputs/*.png from the current OsteoporosisML.py run,
plus charts/ from make_charts.py. Run make_charts.py first.
"""
import os
import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import docx
from docx.shared import Pt as DPt, RGBColor as DRGB

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "outputs")
CH = os.path.join(HERE, "charts")

NAVY = RGBColor(0x0d, 0x36, 0x6b)
BLUE = RGBColor(0x2a, 0x78, 0xd6)
ORANGE = RGBColor(0xeb, 0x68, 0x34)
INK = RGBColor(0x0b, 0x0b, 0x0b)
INK2 = RGBColor(0x52, 0x51, 0x4e)
LIGHT = RGBColor(0xf0, 0xef, 0xec)
WHITE = RGBColor(0xff, 0xff, 0xff)
FONT = "Segoe UI"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
SW, SH = prs.slide_width, prs.slide_height

SLIDES = []  # (title, notes) for the DOCX


def _run(p, text, size=16, bold=False, color=INK, italic=False):
    r = p.add_run()
    r.text = text
    f = r.font
    f.name, f.size, f.bold, f.italic = FONT, Pt(size), bold, italic
    f.color.rgb = color
    return r


def new_slide(title, subtitle=None, section=None):
    s = prs.slides.add_slide(BLANK)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, Inches(0.12))
    bar.fill.solid(); bar.fill.fore_color.rgb = NAVY; bar.line.fill.background()
    tb = s.shapes.add_textbox(Inches(0.6), Inches(0.3), Inches(12.1), Inches(0.8))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    _run(p, title, 28, True, NAVY)
    if subtitle:
        p2 = tf.add_paragraph()
        _run(p2, subtitle, 15, False, INK2)
    if section:
        st = s.shapes.add_textbox(Inches(9.8), Inches(7.05), Inches(3.3), Inches(0.35))
        sp = st.text_frame.paragraphs[0]; sp.alignment = PP_ALIGN.RIGHT
        _run(sp, section, 10, False, INK2)
    num = s.shapes.add_textbox(Inches(0.6), Inches(7.05), Inches(1), Inches(0.35))
    _run(num.text_frame.paragraphs[0], str(len(prs.slides)), 10, False, INK2)
    return s


def notes(slide, title, text):
    slide.notes_slide.notes_text_frame.text = text.strip()
    SLIDES.append((title, text.strip()))


def bullets(slide, items, x=0.6, y=1.45, w=12.1, h=5.5, size=17):
    """items: str, or (str, level), or ('**bold**', rest) via tuple(level, text, bold_prefix)."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    first = True
    for it in items:
        lvl, text, lead = 0, it, None
        if isinstance(it, tuple):
            if len(it) == 2:
                lvl, text = it
            else:
                lvl, lead, text = it
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(7 if lvl == 0 else 3)
        sz = size if lvl == 0 else size - 2
        mark = "•  " if lvl == 0 else "–  "
        _run(p, ("      " * lvl) + mark, sz, False, BLUE if lvl == 0 else INK2)
        if lead:
            _run(p, lead + " ", sz, True, INK)
        _run(p, text, sz, False, INK if lvl == 0 else INK2)
    return tb


def table(slide, rows, x, y, w, col_w=None, size=12, header_fill=NAVY, row_h=0.32, bold_first_col=False):
    nr, nc = len(rows), len(rows[0])
    shp = slide.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(row_h * nr))
    t = shp.table
    if col_w:
        for i, cw in enumerate(col_w):
            t.columns[i].width = Inches(cw)
    for r in range(nr):
        t.rows[r].height = Inches(row_h)
        for c in range(nc):
            cell = t.cell(r, c)
            cell.margin_left = cell.margin_right = Inches(0.06)
            cell.margin_top = cell.margin_bottom = Inches(0.02)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame; tf.word_wrap = True
            p = tf.paragraphs[0]
            txt = str(rows[r][c])
            if r == 0:
                _run(p, txt, size, True, WHITE)
                cell.fill.solid(); cell.fill.fore_color.rgb = header_fill
            else:
                _run(p, txt, size, bold_first_col and c == 0, INK)
                cell.fill.solid(); cell.fill.fore_color.rgb = WHITE if r % 2 else LIGHT
    return t


def picture(slide, path, x, y, w=None, h=None):
    kw = {}
    if w: kw["width"] = Inches(w)
    if h: kw["height"] = Inches(h)
    return slide.shapes.add_picture(path, Inches(x), Inches(y), **kw)


def callout(slide, text, x, y, w, h, fill=LIGHT, color=INK, size=15, bold=False):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    box.adjustments[0] = 0.08
    box.fill.solid(); box.fill.fore_color.rgb = fill; box.line.fill.background()
    tf = box.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.15)
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        _run(p, ln, size, bold, color)
    return box


# ---------------------------------------------------------------- data
nv = pd.read_csv(os.path.join(OUT, "nested_cv_verdict.csv"))
lb1 = pd.read_csv(os.path.join(OUT, "model_leaderboard_osteopenia.csv"))
lb2 = pd.read_csv(os.path.join(OUT, "model_leaderboard_osteoporosis.csv"))
arms = pd.read_csv(os.path.join(OUT, "prespecified_arms.csv"))
ref = pd.read_csv(os.path.join(OUT, "referral_table.csv"))
cpt = pd.read_csv(os.path.join(OUT, "clinical_predictor_table.csv"))

# ================================================================ 1 title
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH)
bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
tb = s.shapes.add_textbox(Inches(0.9), Inches(2.0), Inches(11.5), Inches(3.5))
tf = tb.text_frame; tf.word_wrap = True
_run(tf.paragraphs[0], "Screening for Low Bone Mass Without a DXA Scan", 40, True, WHITE)
p = tf.add_paragraph(); _run(p, "An NHANES machine-learning pipeline: data, cohort, models and an honest null result", 22, False, WHITE)
p = tf.add_paragraph(); p.space_before = Pt(30)
_run(p, "Technical briefing for a Senior AI/ML Data Engineer  ·  sf_26-27 / OsteoporosisML.py", 16, False, RGBColor(0xb7, 0xd3, 0xf6))
p = tf.add_paragraph()
_run(p, "Results from the 2 Oct 2026 pipeline run (deduplicated, postmenopausal cohort, n = 1,111)", 14, False, RGBColor(0xb7, 0xd3, 0xf6))
notes(s, "Title", """
Purpose of this session: walk a senior ML/data engineer through the whole project end to end — where the data comes from, how it is downloaded and cleaned, how the analysis cohort is built, which clinical decisions were made with the osteoporosis specialist, how the models are coded and evaluated, what the final results are, and where we want help.

Frame it up front: this is a research pipeline, not a production system. It is one Python file (OsteoporosisML.py, ~2,060 lines, blocks A–G), runs end to end in roughly 25–40 minutes, seed 42, fully reproducible.

The punchline, so nobody waits for it: on the corrected cohort the ML model is NOT statistically distinguishable from a two-input clinical formula (OST = 0.2 × (weight − age)). We will show why we believe that result, how we found the data defect that had made earlier numbers look much better, and what we want to do next.

All numbers in this deck come from the current outputs/ folder (2 Oct 2026 run). Any older AUCs (0.810, 0.806, 0.833) are withdrawn — if someone has seen them in earlier material, explain they were computed on a cohort with duplicated respondents (slide on the duplicate defect).
""")

# ================================================================ 2 TL;DR
s = new_slide("The one-slide summary", section="Overview")
bullets(s, [
    (0, "Question:", "can routinely collected survey answers flag women likely to have low bone mass, so DXA is ordered for the right people?"),
    (0, "Data:", "NHANES, 5 survey cycles 2005–2020 → 1,111 postmenopausal non-Hispanic White women aged 50–65 with a hip DXA."),
    (0, "Target:", "T-score ≤ −1.0 (osteopenia or worse; 645 cases, 58%) and ≤ −2.5 (osteoporosis; 76 cases, 6.8%)."),
    (0, "Models:", "5 classifiers + 3 T-score regressors, 17 variables (17 columns), 5-fold stratified CV, nested CV for model choice, paired bootstrap CIs."),
    (0, "Result:", "nested-CV AUC 0.751 vs OST formula 0.739 → Δ +0.012 [−0.005, +0.030]. Not separable. Same story at T ≤ −2.5 (0.794 vs 0.780)."),
    (0, "Why:", "body weight carries nearly all the signal. Drop weight + BMI → AUC 0.606; drop any other block → no measurable change."),
    (0, "Engineering lesson:", "an earlier 'beats OST by +0.063' claim was an artifact of 176 respondents loaded twice under different IDs. Fixed and now asserted."),
    (0, "Ask:", "help us decide whether this is a publishable null, and what data / design changes could move the needle."),
], size=17)
notes(s, "The one-slide summary", """
Read this slide slowly; everything after it is supporting detail.

Key framing for an ML audience:
- The comparator matters more than the AUC. A 0.75 AUC sounds respectable until you see that weight alone gets 0.737 and the two-input OST formula gets 0.739.
- The result is a null, and we are reporting it as one. The confidence interval on the improvement over OST crosses zero for both targets.
- The most interesting engineering story is the data defect: NHANES released 2017–2018 twice (once on its own and again inside the pooled 2017–March 2020 'P_' files) with re-numbered respondent IDs, so ID-based de-duplication could not see it. Those 176 women landed in both training and test folds and inflated every cross-validated AUC. That is classic train/test leakage through duplicated entities.

Counts to remember: 1,111 women; 645 at T ≤ −1.0; 76 at T ≤ −2.5; 17 variables / 17 model columns; 8 models.
""")

# ================================================================ 3 Question
s = new_slide("The clinical problem and why OST is the bar to beat", section="Overview")
bullets(s, [
    (0, "DXA (dual-energy X-ray absorptiometry)", "is the reference test for bone density. It is reported as a T-score: SDs below a young-adult reference mean."),
    (1, "T ≤ −1.0 = low bone mass (osteopenia) or worse; T ≤ −2.5 = osteoporosis (WHO)."),
    (0, "Many women in their 50s–early 60s are not routinely scanned.", "A questionnaire-based pre-screen could prioritise who gets a DXA."),
    (0, "OST (Osteoporosis Self-assessment Tool)", "is an existing, validated, two-input formula: OST = 0.2 × (weight kg − age yr)."),
    (1, "Any ML model has to beat OST to be worth deploying — reporting a bare AUC without it is uninterpretable."),
    (0, "Study design:", "cross-sectional. We predict the DXA result measured at the same visit, not future fractures."),
    (0, "DXA columns are the label, so they are structurally barred from the features", "(allowlist + denylist + leak alarm)."),
], size=17)
callout(s, "Primary estimand: ΔAUC (model − OST) with a paired bootstrap 95% CI,\nmeasured on out-of-fold predictions from nested cross-validation.",
        0.6, 5.85, 12.1, 0.95, fill=RGBColor(0xcd, 0xe2, 0xfb), color=NAVY, size=16, bold=True)
notes(s, "The clinical problem", """
Explain the T-score: T = (measured BMD − young-adult reference mean) / reference SD. A T-score of −1.0 means one standard deviation below a healthy 20-to-29-year-old. The WHO thresholds are −1.0 (osteopenia / low bone mass) and −2.5 (osteoporosis).

Why OST: it is the established, cheap screening tool that already uses only weight and age. If a model using 18 survey variables cannot beat a formula you can do in your head, it adds nothing clinically. So the estimand is the DIFFERENCE in AUC between the model and OST, measured on the same women, with a paired bootstrap confidence interval.

Important limitation to state now: this is cross-sectional. NHANES does not follow these women forward for fractures, so we predict a measurement (low BMD), not a clinical event. Most fragility fractures actually occur in women above T −2.5, so this is a proxy outcome.

Leakage note for the engineer: the bone density columns (DXXNKBMD femoral neck, DXXOFBMD total hip) and anything derived from them (t-scores, labels) are on an explicit denylist, and the code asserts they never enter the feature matrix.
""")

# ================================================================ 4 NHANES
s = new_slide("Data source: NHANES", "National Health and Nutrition Examination Survey (CDC / NCHS) — public-use, de-identified", section="Data")
bullets(s, [
    "Continuous US survey released in 2-year cycles; interview + mobile exam centre + labs. One row per respondent per module, keyed by SEQN.",
    "Hip DXA was only measured in some cycles — that dictates which cycles we can use.",
    "Each cycle is ~15 separate module files (demographics, body measures, DXA, questionnaires, labs). We join them on SEQN.",
], x=0.6, y=1.5, w=6.3, h=2.2, size=14)
table(s, [
    ["Cycle", "File naming", "In cohort"],
    ["2005–2006", "MODULE_D.csv", "173"],
    ["2007–2008", "MODULE_E.csv", "228"],
    ["2009–2010", "MODULE_F.csv", "227"],
    ["2013–2014", "MODULE_H.csv", "219"],
    ["2017–Mar 2020 (pooled)", "P_MODULE.csv", "264"],
    ["Total", "", "1,111"],
], 0.6, 3.75, 6.3, col_w=[2.7, 2.2, 1.4], size=12, row_h=0.31)
table(s, [
    ["Module", "What it supplies"],
    ["DEMO", "sex, race/ethnicity, age, poverty-income ratio"],
    ["BMX", "weight, height, BMI"],
    ["DXXFEM", "femoral-neck & total-hip BMD (label source)"],
    ["RHQ", "periods, menopause, hysterectomy, ovaries, estrogen"],
    ["OSQ", "prior fractures, steroids, family history"],
    ["MCQ / DIQ", "arthritis type, diabetes"],
    ["SMQ / ALQ", "smoking, alcohol"],
    ["PAQ / SLQ / DPQ", "activity, sleep, PHQ-9 depression"],
    ["DR1TOT / DR2TOT", "24-h dietary recall day 1 / day 2"],
    ["DSQTOT", "dietary supplements"],
    ["VID", "serum 25(OH) vitamin D (lab)"],
], 7.2, 1.5, 5.5, col_w=[1.8, 3.7], size=12, row_h=0.36)
callout(s, "Not used: 2011–12 (no hip DXA), 2015–16 & 2021–23 (excluded by design choice),\n2017–18 standalone (duplicate of P_ — see slide 6).", 0.6, 6.45, 12.1, 0.55, size=12)
notes(s, "Data source: NHANES", """
NHANES is run by the CDC's National Center for Health Statistics. Each two-year cycle is a fresh, nationally representative sample, released as many separate files (modules). Every file has the respondent ID, SEQN, and we left-join everything onto the demographics file (DEMO) within each cycle, then stack the cycles.

Cycle suffixes: D = 2005–06, E = 2007–08, F = 2009–10, H = 2013–14. The 2017–March 2020 release uses a 'P_' prefix instead of a suffix. COVID stopped field work in March 2020, so NCHS combined the partial 2019–2020 sample with the complete 2017–2018 cycle into these P_ files.

Modules used (from MODULE_COLS in block B): DEMO, BMX, DXXFEM, DR1TOT, VID, PAQ, DPQ, SMQ, ALQ, DIQ, MCQ, OSQ, RHQ, SLQ, plus the runtime downloads DSQTOT (supplements) and DR2TOT (day-2 diet). VID does not exist for the P_ cycle (declared as KNOWN_ABSENT).

Which cycles are in: five cycles, 1,111 women. 2011–2012 has no femur DXA. 2015–2016 and 2021–2023 data are on disk but were deliberately left out by the project lead's choice — a good discussion point (could add events; slide on directions). The standalone 2017–2018 cycle must NOT be added — that is the duplicate defect.

Note on survey design: NHANES provides sampling weights, strata and PSUs. This analysis is unweighted (a prediction model, not a prevalence estimate) — a question for the statistician.
""")

# ================================================================ 5 Acquisition
s = new_slide("Data acquisition and ingestion engineering", section="Data")
bullets(s, [
    (0, "Local cache:", "data/raw/<cycle>/<MODULE>_<suffix>.csv, committed to git (~31 MB) so a fresh clone runs offline."),
    (0, "Explicit filenames, never globbed:", "cycle_file() builds the exact name. A glob 'OSQ_*.csv' silently misses 'P_OSQ.csv' and would drop all 264 women from 2017–20."),
    (0, "Runtime downloads (requests):", "DSQTOT supplements and DR2TOT day-2 diet from wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{year}/DataFiles/{stem}.xpt"),
    (1, "SAS XPORT → pandas.read_sas → keep SEQN + nutrient columns → cached CSV."),
    (1, "Cache rule: file exists AND > 2,048 bytes (a truncated download is re-fetched). Failures are logged and skipped, never fatal."),
    (0, "Two encodings in one dataset:", "2005–2014 CSVs were exported with value labels ('Female', 'Yes'); P_ files are numeric codes (2, 1). decode() handles both."),
    (0, "Per-variable sentinel SPEC:", "kind (num / yesno / cat), refusal codes and a valid range per column."),
    (1, "Example: 99 is 'refused' for RHQ060 (age at last period) but a legitimate value for PAD680 (sedentary minutes). A single global list was deleting real data (sleep of 7 or 9 h, weights of 77 or 99 kg)."),
    (0, "Denormal floats:", "NHANES encodes zero as 5.4e-79 in P_ and nutrient files; sanitise_denormals() snaps |v| < 1e-30 to 0.0 on every frame."),
], size=15)
notes(s, "Data acquisition", """
This slide is aimed squarely at a data engineer — these are the ingestion traps we actually hit.

1. File discovery. Filenames are built explicitly from the CYCLES table (block A): {prefix}{module}.csv for P_ or {module}_{suffix}.csv otherwise. We originally globbed; OSQ_*.csv does not match P_OSQ.csv, so the most recent cycle silently vanished from the fracture/steroid variables. There is also a stray 'P_DEMO (1).csv' in that folder that a glob would pick up.

2. Runtime downloads. Two module families are fetched on demand: DSQTOT (total dietary supplement intake) for E, F, H and P_, and DR2TOT (day-2 24-hour dietary recall) for D, E, F, H and P_. Download is requests.get with a 90-second timeout, raise_for_status, write to a temporary .xpt, read with pandas.read_sas(format='xport'), keep only SEQN plus the nutrient columns, save as CSV, delete the temp file. The cache check is 'exists and larger than 2 KB'. Any exception prints '!! download failed' and returns an empty frame, so the pipeline still completes. In the final run every cache was hit. There is no 2005–06 DSQTOT release in the URL table, so supplements are unobserved for that cycle.

3. Label-decoded vs numeric. The older CSVs were exported with value labels, so RIAGENDR is 'Female' not 2 and yes/no items are 'Yes'/'No'; the P_ files are numeric. decode() normalises strings (lower-case, strip, treat '', 'nan', '.', 'none' as missing, strip a trailing '.0'), then maps per the SPEC entry. Refused / don't-know words map to NaN.

4. SPEC (block B) is a dictionary declaring for each column: kind, sentinel codes, valid range, and category levels. Values outside the valid window become NaN. Examples: BMXWT 25–250 kg; DXXNKBMD 0.2–1.8 g/cm²; PAD680 sentinels 7777/9999, valid 0–1440 minutes; SLD012 sleep sentinels 77/99, valid 2–14 hours; ALQ130 sentinels 777/999/99, valid 1–30.

5. Denormals. Some NHANES SAS-exported files store zero as a tiny denormal float (5.397605346934028e-79). Without fixing it, nutrient columns appear to contain no zeros. sanitise_denormals runs on every loaded frame.
""")

# ================================================================ 6 Merge
s = new_slide("Merge, then a data-quality defect that ID checks could not see", section="Data")
bullets(s, [
    (0, "Merge:", "within a cycle, functools.reduce of left joins on SEQN starting from DEMO; then pd.concat across cycles + a survey_cycle column. 56,769 respondents in 5 cycles."),
    (0, "The defect:", "NCHS re-released the complete 2017–2018 cycle inside the pooled P_ 2017–2020 files with re-numbered SEQNs."),
    (1, "DEMO_J SEQN 93,703–102,956 vs P_DEMO 109,263–124,822 → no ID ever collides, so SEQN de-duplication passes."),
    (1, "Loading both cycles put 176 cohort women in the data twice (161 of them postmenopausal = 12.7% of that cohort)."),
    (1, "StratifiedKFold splits rows, not people → each duplicate pair could sit in train AND test. Every CV AUC was inflated."),
    (0, "Fix:", "2017_2018 removed from CYCLES permanently."),
    (0, "Guard:", "audit_duplicates() asserts zero duplicates on a physical fingerprint: femoral-neck BMD, total-hip BMD, weight, height, age."),
    (1, "1,306 of 1,308 rows have a complete fingerprint; 0 duplicates. The defect cannot come back silently."),
], size=16, h=4.6)
callout(s, "Effect: ‘best model beats OST by +0.095’ (duplicated cohort) → +0.012, CI crossing zero (deduplicated).\nRemoving duplicates alone cost −0.077 AUC.",
        0.6, 6.0, 12.1, 0.85, fill=RGBColor(0xfd, 0xe3, 0xd6), color=INK, size=15, bold=True)
notes(s, "The duplicate defect", """
This is the single most important engineering finding of the project, and a good story for an ML audience because it is a textbook entity-leakage bug that no standard check caught.

How it was found: the 2017–2018 standalone cycle (suffix J) and the pooled 2017–March 2020 cycle (prefix P_) were both in the cycle list. Because COVID cut 2019–2020 short, NCHS folded all of 2017–2018 into the P_ files, but gave everyone new respondent numbers. Our de-duplication was by SEQN, and the two ID ranges are disjoint, so it found nothing.

Evidence the rows are the same people: all 176 cohort women from J have an exact match in P_ on femoral-neck BMD, total-hip BMD, age, weight and height; 7,585 of 7,585 body-measure fingerprints match; and the matched pairs agree 176/176 on seven derived variables.

Why it inflated the AUC: StratifiedKFold assigns rows to folds. When the same woman appears twice, one copy can be in training and the other in test, so the model is effectively tested on someone it has already seen. Tree ensembles in particular memorise these.

Fix and guard: the J cycle is permanently out of CYCLES (CLAUDE.md says it must not come back), and audit_duplicates asserts zero duplicates on a physical fingerprint — five measurements that will not coincide by chance. It runs on the 1,308 DXA cohort.

One more use of 2017–2018: the P_ cycle has no vitamin D lab file, so serum vitamin D for those 2017–18 women is copied from the J lab file by exact fingerprint match ('crosswalk'). 161 matches, 159 with a serum value; coverage 815 → 974. It only fills nulls and only for the serum vitamin D arm, not the headline model.

Alternative we should mention: in a general setting you would use GroupKFold on a person key. Here, once the duplicates are removed there is one row per person, so StratifiedKFold is valid.
""")

# ================================================================ 7 Cohort
s = new_slide("Building the analysis cohort", "Every count below is hard-asserted in code — a changed number fails the run", section="Cohort")
picture(s, os.path.join(CH, "attrition.png"), 0.4, 1.35, w=8.0)
table(s, [
    ["Step", "Rule (code)"],
    ["Female", "RIAGENDR ∈ {'female', 2}"],
    ["Non-Hispanic White", "RIDRETH1 ∈ {'non-hispanic white', 3}"],
    ["Aged 50–65", "50 ≤ RIDAGEYR ≤ 65 (inclusive)"],
    ["Femoral-neck DXA", "DXXNKBMD not null after 0.2–1.8 window\nassert n == 1,308"],
    ["Postmenopausal", "RHQ031 (period in past 12 mo) == No\nassert 156 cycling, 41 unknown, 1,111 kept"],
], 8.55, 1.5, 4.4, col_w=[1.55, 2.85], size=11, row_h=0.62)
callout(s, "Excluded at the menopause gate:\n156 still cycling (mean T −0.47, median age 52)\n41 status undeterminable (mean T −1.16) — unknown, NOT premenopausal",
        8.55, 5.4, 4.4, 1.45, size=12)
notes(s, "Cohort construction", """
Walk the funnel top to bottom (numbers from the final run log):
- 56,769 respondents across the five cycles. (Note: CLAUDE.md and some older notes say 66,023; that was the six-cycle count including the duplicated 2017–2018 cycle. The code and log say 56,769.)
- 28,644 female.
- 10,672 non-Hispanic White. The cohort is deliberately narrow: the T-score reference values used are for non-Hispanic White women, and the specialist confirmed these inclusion limits.
- 1,639 aged 50–65 inclusive.
- 1,308 with a valid femoral-neck DXA (value inside 0.2–1.8 g/cm²). The code asserts exactly 1,308 (N_DXA_COHORT).
- 1,111 postmenopausal. The gate uses one question, RHQ031 'Have you had at least one menstrual period in the past 12 months?'. No → kept (1,111). Yes → dropped as still cycling (156; younger, median age 52, much better bone: mean T −0.47). Missing / refused / don't know → dropped as undeterminable (41; their mean T −1.16 is almost identical to the kept group, so excluding them is unlikely to bias anything). We are careful never to call these 41 'premenopausal'.

Engineering point: these asserts pin the published numbers. If a refactor or data change alters the cohort, the run fails loudly instead of quietly producing a different study.

The narrowing to postmenopausal women was a clinical decision (specialist Q3). The AUC decomposition later shows the gate itself costs almost nothing (−0.006).
""")

# ================================================================ 8 Target
s = new_slide("The prediction target", section="Cohort")
bullets(s, [
    (0, "T-score per site", "using fixed NHANES III young-adult non-Hispanic White female references (Looker):"),
    (1, "femoral neck: T = (BMD − 0.858) / 0.120"),
    (1, "total hip: T = (BMD − 0.942) / 0.122"),
    (0, "t_score = minimum of the two sites", "(WHO/ISCD lowest-of-two rule, specialist Q2), rounded to 3 dp before thresholding."),
    (0, "Two binary labels + one continuous target:", ""),
    (1, "at_risk = t_score ≤ −1.0  →  645 / 1,111 (58.1%)  — primary"),
    (1, "osteoporosis = t_score ≤ −2.5  →  76 / 1,111 (6.8%)  — secondary, underpowered"),
    (1, "t_score (continuous) — used by the three regressors"),
], x=0.6, y=1.45, w=7.3, h=4.5, size=16)
table(s, [
    ["Cycle", "Normal", "Low mass", "Osteoporosis", "Total"],
    ["2005–06", "81", "83", "9", "173"],
    ["2007–08", "103", "107", "18", "228"],
    ["2009–10", "98", "118", "11", "227"],
    ["2013–14", "89", "112", "18", "219"],
    ["2017–20", "95", "149", "20", "264"],
    ["All", "466", "569", "76", "1,111"],
], 8.1, 1.6, 4.85, col_w=[1.0, 0.85, 1.0, 1.25, 0.75], size=12)
callout(s, "Note the class balance: the ‘positive’ class is the MAJORITY at T ≤ −1.0 (58%)\nand a small minority at T ≤ −2.5 (6.8%). This drives several modelling choices.",
        0.6, 5.9, 12.1, 0.9, size=14)
notes(s, "Prediction target", """
T-score computation is in compute_tscores (block C). The reference means and SDs are fixed constants from the NHANES III young-adult reference population (non-Hispanic White women aged 20–29): femoral neck 0.858 g/cm² SD 0.120, total hip 0.942 SD 0.122. Mean T-score in the cohort is −1.14 (femoral neck −1.09, total hip −0.65).

The final t_score is the lower of the two sites, which is the clinical convention. It is rounded to three decimals before thresholding — an earlier version used pd.cut and misclassified three women sitting exactly on −2.5.

Specialist interaction: the specialist said the outcome should be the T-score itself (continuous). We kept the binary T ≤ −1.0 as the headline because the clinical decision is binary (refer for DXA or not) and reporting conventions expect a binary primary, and we model the continuous T-score with regressors alongside. That override still needs the specialist's sign-off.

Class balance is unusual: at T ≤ −1.0 the positive class is the majority (58%), so 'class_weight=balanced' actually DOWN-weights positives there and XGBoost's scale_pos_weight is below 1. At T ≤ −2.5 there are only 76 events — events per predictor is 4.5 against a rule-of-thumb floor of 10, so that target is flagged as underpowered before any modelling (power_gate.csv).
""")

# ================================================================ 9-10 Specialist
s = new_slide("Decisions put to the osteoporosis specialist (1 of 2)", section="Clinical decisions")
table(s, [
    ["#", "Question", "Specialist answer", "What we implemented"],
    ["Q1", "Outcome: T ≤ −1.0, T ≤ −2.5, or continuous T?", "Continuous T-score", "Binary T ≤ −1.0 primary (referral decision), continuous T modelled alongside. Override — sign-off pending"],
    ["Q2", "Which bone site?", "Lowest of the 2 sites; also model each site", "min(neck, hip) primary; neck-only & hip-only as sensitivity arms H1/H2"],
    ["Q3", "Restrict to postmenopausal women?", "Yes", "RHQ031 gate: 1,308 → 1,111 (156 cycling, 41 unknown excluded and described)"],
    ["Q4", "Years since menopause after hysterectomy?", "No menopause-type variable", "years_since_menopause for all 1,111 (22 median-imputed); menopause defined only by the 12-month gate"],
    ["Q5", "Estrogen detail?", "Primary Y/N; secondary <2 y vs >2 y", "ever_used_estrogen in model; duration levels built descriptively"],
    ["Q6", "Keep PHQ-9 depression score? Continuous or ≥10?", "Yes and yes", "Continuous phq9_score in panel; phq9 ≥ 10 as substitution arm F"],
], 0.6, 1.4, 12.1, col_w=[0.55, 3.4, 3.1, 5.05], size=12, row_h=0.72)
notes(s, "Specialist decisions 1", """
Two rounds of questions went to the clinical specialist (documented in Notes/Specialist_Review_Questions.docx, Specialist_Review_Answers.docx and specialist_answers_and_decisions.html).

Q1 Outcome. The specialist preferred the continuous T-score. We kept binary T ≤ −1.0 as primary because the use case is a yes/no referral, and we model continuous T with regressors; the regressors actually win the nested CV in several folds, so the specialist's preference is reflected in the modelling. This override has to be re-confirmed with the specialist.

Q2 Site. Lowest of femoral neck and total hip, per WHO/ISCD. Each site separately is run as a pre-specified sensitivity arm (H1 femoral neck: 618 events, AUC 0.747; H2 total hip: 424 events, AUC 0.776). These are different outcomes so no delta is reported.

Q3 Cohort. Postmenopausal only, confirmed. The 41 women whose status cannot be determined are described separately and never called premenopausal.

Q4 Menopause timing after hysterectomy. A hysterectomy ends periods without ending ovarian function, so for those women 'years since last period' can mean 'years since surgery'. The specialist asked for no menopause-type variable: postmenopausal status is defined once, by the gate (no period in the past 12 months, n = 1,111), and the model carries no natural / surgical / hysterectomy distinction. years_since_menopause (age − RHQ060) is observed for 1,089 women; the other 22 get the fold-internal median. The residual hysterectomy caveat on years_since_menopause is a stated limitation.

Q5 Estrogen. Ever-use yes/no is in the model. Duration (< 2 years vs ≥ 2 years) is built but kept descriptive; duration is known for about 71% of users.

Q6 PHQ-9. An earlier version showed ~80% missing; that was a decoding bug (items stored as words in some cycles). After the fix the score exists for 1,110 of 1,111.
""")

s = new_slide("Decisions put to the osteoporosis specialist (2 of 2)", section="Clinical decisions")
table(s, [
    ["#", "Question", "Specialist answer", "What we implemented"],
    ["Q7", "Rheumatoid arthritis?", "Subset of women who answered RA yes/no; trust self-report", "Arm E on 988 women (71 RA); 123 excluded, stated"],
    ["Q8", "Diabetes behaves 'backwards' (higher BMD). Keep it?", "Check DM sample size; DM predicts low bone mass", "Kept, judged by ablation not sign; borderline → non-diabetic; recode arms G1/G2; no expected-sign check (bone paradox)"],
    ["Q9", "Vitamin D: intake or serum?", "Use vitamin D level (serum)", "Both kept OUT of headline model; separate arms C (intake) & D (serum); null stated in advance"],
    ["Q10", "Family history: ordinal (0/1/2 parents)?", "Ordinal + first-degree Y/N", "Binary parental hip fracture (only 5 women had both parents) + family history of osteoporosis. Override"],
    ["Q11", "Use NHANES survey weights?", "Weighted and unweighted, compare", "Not constructible across non-contiguous cycles; unweighted prediction. Needs restating"],
    ["Q12", "Any missing inclusion criteria?", "No", "Locked: NH White women 50–65 with hip DXA"],
    ["R1", "Prior fracture window (any age vs 5 y)?", "Asked for 5-year window", "NOT implemented — any_prior_fracture at any age is shipped (open item)"],
], 0.6, 1.4, 12.1, col_w=[0.55, 3.2, 3.3, 5.05], size=11.5, row_h=0.66)
notes(s, "Specialist decisions 2", """
Q7 Rheumatoid arthritis. Arthritis type comes from MCQ190/191/195 (first non-missing). RA is only defined for women who answered the arthritis questions, so it is tested as a complete-case subset arm (988 women, 71 with RA). The 123 excluded have better bone (mean T −0.87 vs −1.17), which is a non-random exclusion we must state. Result: Δ AUC 0.000.

Q8 Diabetes. Diabetics in this cohort have higher BMD (mean T −0.73 vs −1.20) — the known 'diabetic bone paradox': higher density but higher fracture risk. Kept as a predictor; we do not flag its coefficient sign; borderline diabetes (30 women) is folded into non-diabetic, with two recode sensitivity arms (borderline as diabetic; diabetes dropped). Both null. Type 1 vs type 2 cannot be separated in NHANES.

Q9 Vitamin D. Serum 25(OH)D is missing for all of 2017–20 (no VID file, partially recovered by the crosswalk) and intake is missing for all of 2005–06 supplements, so they cover complementary cycles. Both are excluded from the headline model and tested as separate complete-case arms. Both null (−0.002 and −0.001), which was the pre-stated expectation given correlation with T of about −0.01.

Q10 Family history. Only 5 women had both parents with a hip fracture, so the ordinal version cannot be estimated; binary performs identically. Override, documented.

Q11 Survey weights. The two-year weights (WTMEC2YR) and the 3.2-year P_ weight (WTMECPRP) are on different bases, the cycles are non-contiguous, so a pooled weight cannot be constructed correctly. Analysis is unweighted. This needs to go back to the specialist — and is a good statistician question.

Round 1 items: the specialist asked that prior fracture be limited to the last 5 years (fragility relevance). That was never implemented and nothing records why — the shipped variable is 'any prior hip/spine/wrist fracture at any age' (177 women). Flag it as an open item. Steroid use was once queued for removal and is still in the panel; dose and timing are not recorded in NHANES. Alcohol: the recommended ≥3 drinks/day category was not adopted; continuous drinks/day ships.
""")

# ================================================================ 11 Features
s = new_slide("The model feature panel: 17 variables, one column each", "Allowlist (FEATURE_GROUPS, block E): nothing enters a model unless it is named here", section="Features")
fv = [
    ["Variable", "NHANES source", "Type", "n observed", "Missing"],
    ["age", "RIDAGEYR", "cont.", "1,111", "0%"],
    ["weight_kg", "BMXWT", "cont.", "1,111", "0%"],
    ["bmi", "BMXBMI", "cont.", "1,110", "0.1%"],
    ["years_since_menopause", "age − RHQ060", "cont.", "1,089", "2.0%"],
    ["ever_used_estrogen", "RHQ540", "bin.", "1,109", "0.2%"],
    ["diabetes", "DIQ010 (borderline→0)", "bin.", "1,111", "0%"],
    ["ever_smoked", "SMQ020", "bin.", "1,111", "0%"],
    ["alcohol_drinks_day", "ALQ130 (+0 non-drinkers)", "cont.", "960", "13.6%"],
    ["any_prior_fracture", "OSQ010A/B/C", "bin.", "1,111", "0%"],
    ["steroid_use", "OSQ130", "bin.", "1,106", "0.5%"],
    ["vigorous_activity", "PAQ650", "bin.", "938", "15.6%"],
    ["sedentary_min_day", "PAD680", "cont.", "935", "15.8%"],
    ["poverty_income_ratio", "INDFMPIR", "cont.", "1,055", "5.0%"],
    ["parental_hip_fracture", "OSQ170 / OSQ200", "bin.", "1,062", "4.4%"],
    ["family_hx_osteoporosis", "OSQ150", "bin.", "1,059", "4.7%"],
    ["phq9_score", "Σ DPQ010–090 (≥5 items)", "cont.", "1,110", "0.1%"],
    ["sleep_hrs", "SLD012 ← SLD010H", "cont.", "1,107", "0.4%"],
]
table(s, fv, 0.6, 1.45, 8.2, col_w=[2.6, 2.6, 0.75, 1.1, 1.15], size=10.5, row_h=0.285)
bullets(s, [
    (0, "Arm-only variables", "(never in headline model):"),
    (1, "total calcium & vitamin D intake — n = 930"),
    (1, "serum 25(OH)D — n = 974"),
    (1, "rheumatoid arthritis — n = 988"),
    (1, "PHQ-9 ≥ 10 (substitutes score)"),
    (0, "Denylist", "(asserted): BMD, site T-scores, t_score, labels, bone_status."),
    (0, "Benched:", "height (enters via BMI), age at menopause (= age − years since), education, supplement-availability flag."),
], x=9.05, y=1.45, w=3.9, h=5.5, size=13)
notes(s, "Feature panel", """
This is the complete headline feature set: 17 variables, one model column each. There is no menopause-type variable — per the specialist, menopause is defined only by the 12-month gate.

The n observed column answers 'how many of the cohort have each variable' — out of 1,111. Most variables are near-complete. Three are notably incomplete: sedentary minutes (935), vigorous activity (938) and alcohol (960). The activity gap is structural: 2005–06 used a different physical-activity instrument, so 173 of the missing are an entire cycle.

Derivation details worth mentioning to an engineer:
- years_since_menopause = age − age at last period (RHQ060), kept only if ≥ 0.
- alcohol: ALQ130 is drinks per drinking day. Blank for a confirmed non-current drinker (ALQ101/ALQ111 = No) is set to 0 — a true zero, not missing. Current vs lifetime drinking are separate questions; conflating them mislabels 62 women.
- phq9_score: sum of nine items mapped to 0–3; requires at least 5 answered items, otherwise NaN.
- sleep_hrs: SLD012 (newer cycles) coalesced with SLD010H (older cycles).
- any_prior_fracture: yes if any of hip / spine / wrist fracture questions is yes; no only if all three are answered no.
- parental_hip_fracture: mother (OSQ170) or father (OSQ200).

Why an allowlist: the old code admitted every column not explicitly excluded, so every new derived column was a potential target leak unless someone remembered to exclude it. Now adding a variable means adding it to FEATURE_GROUPS on purpose. The BMD denylist is asserted on top as a second gate.

Arm-only variables are evaluated on complete-case sub-cohorts (slide on arms).
""")

# ================================================================ 12 Missing / imputation
s = new_slide("Missing data and imputation", section="Features")
picture(s, os.path.join(CH, "missingness.png"), 0.5, 1.3, h=5.65)
bullets(s, [
    (0, "Model-time imputation:", "SimpleImputer(strategy='median') as step 1 of every sklearn Pipeline — fitted inside each training fold only."),
    (1, "Applies to binaries too (median of 0/1 = mode)."),
    (1, "No missing-indicator columns (add_indicator=False)."),
    (0, "No mean imputation anywhere.", ""),
    (0, "Structural zero-fills (before modelling):", ""),
    (1, "alcohol = 0 for confirmed non-drinkers"),
    (1, "supplement intake = 0 if respondent is in a DSQTOT file but reported none; NaN if absent from every file"),
    (0, "Coalescing:", "sleep (2 items), serum vit D (2 lab vars + 2017–18 crosswalk), arthritis type (3 items)."),
    (0, "Complete-case:", "only in the prespecified arms (vit D, RA)."),
    (0, "OST / weight baselines:", "median fill (0 rows affected)."),
], x=7.9, y=1.35, w=5.1, h=5.6, size=13)
notes(s, "Missing data and imputation", """
Directly answering 'was any mean/median/imputation done?':

1. Yes — median imputation, and only inside the cross-validation folds. Every model is a scikit-learn Pipeline: SimpleImputer(strategy='median') → StandardScaler → estimator. Because the pipeline is fitted on the training fold, the median is learned from training rows only and applied to the test fold; there is no leakage of test-fold statistics. This also applies to tree models (they are wrapped in the same pipeline). For binary columns the median is effectively the mode.

2. No mean imputation anywhere. The only 'mean' is averaging the two 24-hour dietary recall days for calcium and vitamin D intake (and if only one day exists, that day is used).

3. Logical zero-fills that are not imputation but correct coding: alcohol drinks/day = 0 for women who said they did not drink in the past 12 months (ALQ130 is skipped for them); supplement calcium/vitamin D = 0 for women who are in a supplement file but report no supplement (NHANES codes non-users as blank).

4. Complete-case analysis is used only in the arms: vitamin D intake (930), serum vitamin D (974), RA (988).

Known weakness to raise: the activity variables (sedentary minutes, vigorous activity) are missing for the whole 2005–06 cycle (instrument change), which is structural, not random. The plan said structural absence should not be imputed, but the shipped code median-imputes them. sedentary_min_day is one of the six 'significant' odds ratios, so that finding partly rests on imputed values. Options: missing-indicator, drop those variables, drop the cycle, or multiple imputation — a statistician question.

Also no multiple imputation (MICE); with < 6% missing on most variables single imputation is defensible, but the 13–16% variables are where MI would matter.
""")

# ================================================================ 13 Leakage
s = new_slide("Guard-rails against leakage and silent drift", section="Modelling")
table(s, [
    ["Risk", "Guard in code"],
    ["Same person in train and test", "2017_2018 out of CYCLES; audit_duplicates asserts 0 on a 5-field physical fingerprint"],
    ["Target leaking into features", "FEATURE_GROUPS allowlist + BMD_DENYLIST assertion in build_feature_matrix"],
    ["Leak via preprocessing", "Imputer + scaler inside the Pipeline → fitted per training fold"],
    ["Model selection on test rows", "nested_cv_selection: choose among 8 models inside each outer training fold"],
    ["Undetected leak in a new column", "coefficient_diagnostics: alarm if any |standardised coef| > 2.0"],
    ["Clinically backwards effects", "EXPECTED_SIGNS check (prints the most-correlated partner)"],
    ["Cohort silently changes", "Hard asserts: 1,308 DXA, 156 / 41 / 1,111 menopause gate"],
    ["Sentinel codes read as data", "Per-variable SPEC with valid range"],
    ["Misleading OOB AUC", "_oob_auc withholds the number if < 80% of either class is ever out-of-bag"],
    ["Tree importance bias", "Gini / split importances never reported; permutation importance + refit ablation instead"],
], 0.6, 1.4, 12.1, col_w=[3.6, 8.5], size=13, row_h=0.48)
notes(s, "Guard-rails", """
An ML engineer will care most about this slide. The pipeline is written defensively because the project was burned once.

Highlights:
- The allowlist means no column can enter a model by accident.
- The leak alarm: with standardised features, a coefficient above 2.0 in absolute value would be extraordinary for survey variables; it would suggest a BMD-derived column slipped in. Currently the largest is weight_kg at −1.21. The only sign flag is BMI (positive), which is explained: BMI and weight correlate at 0.94, so weight absorbs the effect and BMI's residual sign is meaningless.
- OOB AUC subtlety: scikit-learn ≥ 1.9 makes the bootstrap sample_weight-aware, and class_weight='balanced' is applied as a sample weight, so at T ≤ −2.5 the minority class is oversampled into nearly every tree and only 28% of cases are ever out-of-bag. sklearn returns uncovered rows as all-zero decision rows (not NaN), so a naive isnan guard scores them as lowest-risk and produced an OOB AUC of 0.108 — an inverted model in the leaderboard. _oob_auc now drops uncovered rows and refuses to report when coverage of either class is < 80%.
- Tree importances (Gini, split counts) were removed because they were biased toward continuous features and inverted the real ranking here.

Note: global warnings are suppressed (warnings.filterwarnings('ignore')), which would also hide convergence warnings — a small item for the backlog.
""")

# ================================================================ 14 Models
s = new_slide("Eight models on one fold structure", "Every estimator wrapped as Pipeline(median imputer → StandardScaler → model); seed 42 everywhere", section="Modelling")
table(s, [
    ["Model", "Trained on", "Key settings", "Imbalance"],
    ["Logistic regression (L2)", "binary label", "C = 1.0, lbfgs, max_iter 1000", "class_weight='balanced'"],
    ["Elastic-net logistic", "binary label", "saga, l1_ratio 0.5, C = 1.0, max_iter 2000", "class_weight='balanced'"],
    ["Random forest", "binary label", "500 trees, min_samples_leaf 1, OOB on", "class_weight='balanced'"],
    ["LightGBM", "binary label", "150 trees, max_depth 2, 4 leaves, min_child 50, λ 50", "class_weight='balanced'"],
    ["XGBoost", "binary label", "150 trees, max_depth 2, min_child_weight 15, λ 50", "scale_pos_weight = neg/pos"],
    ["RidgeCV → T-score", "continuous t_score", "alphas logspace(−3, 3, 13), efficient LOO", "n/a"],
    ["RF regressor → T-score", "continuous t_score", "500 trees, min_samples_leaf 5", "n/a"],
    ["LightGBM regressor → T", "continuous t_score", "same as LightGBM classifier", "n/a"],
], 0.6, 1.55, 12.1, col_w=[2.7, 1.9, 4.9, 2.6], size=12.5, row_h=0.46)
bullets(s, [
    (0, "Regressors never see a label:", "the score is −(predicted T-score); one fit serves both cutoffs and is evaluated by AUC against each label."),
    (0, "Boosters are deliberately over-regularised", "(depth 2, λ = 50): with ~1,100 rows they overfit trivially; we would rather under-fit than present a tuned booster on 76 events."),
], x=0.6, y=5.85, w=12.1, h=1.2, size=14)
notes(s, "Models", """
All eight models come from get_model_dictionary and get_regressor_dictionary in block F, and are wrapped by _pipe() into Pipeline([('imputer', SimpleImputer('median')), ('scaler', StandardScaler()), ('model', estimator)]).

Classifiers (5): L2 logistic regression; elastic-net logistic (saga, l1_ratio 0.5 — C was left at the default 1.0 and never tuned, worth noting); random forest (500 trees, min_samples_leaf 1, balanced class weights); LightGBM and XGBoost both heavily constrained (max depth 2, L2 penalty 50, 150 trees).

Regressors (3): RidgeCV over 13 alphas from 0.001 to 1000, random-forest regressor (leaf 5), LightGBM regressor. They predict the continuous T-score. To compare with classifiers, the predicted T-score is negated (lower T = higher risk) and used as a ranking score, scored by AUC against each binary label. Docs say 'thresholded twice', but technically they are rank-scored, not thresholded.

Why include regressors: the continuous T carries more information than a binary label, and at T ≤ −2.5 with 76 events a regressor trained on all 1,111 values is more stable than a classifier trained on 76 positives. In nested CV the winners were mostly the regressors (Ridge → T and RF → T).

Class imbalance: balanced class weights, or scale_pos_weight for XGBoost. At T ≤ −1.0 the positive class is the majority, so these weights slightly down-weight positives.

RF leaf size: RF_MIN_SAMPLES_LEAF = 1 is shipped. rf_leaf_tuning.csv now shows leaf 1 best on the grid (0.7536 vs 0.7533 for leaf 5), but inner-CV picks per outer fold are [20, 2, 1, 1, 20] — the grid differences are negligible and the per-fold choice is unstable, so 'chosen by nested CV' overstates it.
""")

# ================================================================ 15 Evaluation
s = new_slide("Evaluation design", section="Modelling")
bullets(s, [
    (0, "Cross-validation:", "StratifiedKFold(5, shuffle, random_state 42), identical folds for every model."),
    (0, "Leaderboard:", "mean per-fold test AUC, plus train AUC and (for RF) OOB AUC side by side. Do NOT rank by train/test gap — RF train AUC is 1.000 by construction (0.997 even on shuffled labels)."),
    (0, "Nested CV (the defensible number):", "outer 5-fold; inside each outer training fold, all 8 models compete by inner 3-fold OOF AUC; the winner is refit and scores the outer test fold."),
    (1, "rank_within_folds() converts probabilities and −T predictions to percentile ranks per fold so they can be pooled into one AUC."),
    (0, "Comparators:", "OST = 0.2 × (weight − age) and weight alone, scored on the same women."),
    (0, "Uncertainty:", "paired, stratified bootstrap of ΔAUC on fixed out-of-fold scores (1,000 resamples headline; 500 for ablations/arms); one-sided p = share of Δ ≤ 0."),
    (0, "Explaining the model:", "permutation importance (5 folds × 5 repeats); single-variable and block refit ablation across all 8 models with Holm correction; bootstrapped odds ratios from L2 LR."),
    (0, "Clinical utility:", "sigmoid calibration (CalibratedClassifierCV), referral table by top-k%, probability threshold sweep."),
    (0, "Power gate:", "events per predictor vs a floor of 10, checked before any arm is modelled."),
], size=15)
notes(s, "Evaluation design", """
Walk through why each piece exists.

Leaderboard vs nested CV: fitting eight models and reporting the best is optimistically biased (winner's curse). Nested CV puts model selection inside each outer training fold, so no test row helps pick the model that scores it. The nested AUC is the number we stand behind. Fold-level winners were: osteopenia [RF→T, RF, Ridge→T, RF, Ridge→T]; osteoporosis [RF→T, RF→T, Ridge→T, Ridge→T, RF→T].

Pooling different model types: classifier probabilities and negated regressor predictions are on different scales, and the winning model can differ by fold, so scores are converted to within-fold percentile ranks before computing one pooled AUC.

Bootstrap: cases and non-cases are resampled separately (stratified), with model and OST evaluated on the same resampled rows (paired). Important caveat for the engineer: it resamples fixed out-of-fold predictions; it does not refit models, so model-fitting variance is not in the interval. Also the reported Δ is the bootstrap mean, not the observed difference (they differ in the third decimal at most).

Subtle point: the leaderboard AUC is the mean of per-fold AUCs, while nested / ablation AUCs are pooled out-of-fold AUCs. 'Optimism' (leaderboard − nested) therefore mixes two aggregation methods — small, but worth knowing.

Permutation importance answers 'how much does this model rely on the column'; refit ablation answers 'how much do we lose if we never collect this variable'. With collinear predictors (weight / BMI) the two disagree, which is why block ablation exists.

Holm correction is applied to the 18 single-variable ablation p-values for the primary model.
""")

# ================================================================ 16 Code
s = new_slide("How the code is organised", "OsteoporosisML.py — one file, ~2,060 lines, linear DataFrame-in / DataFrame-out steps", section="Code")
table(s, [
    ["Block", "Contents"],
    ["A  Config", "paths (BASE_DIR from __file__), CYCLES, download URLs, cohort constants, T-score refs, seed, thresholds"],
    ["B  Data layer", "SPEC, MODULE_COLS, cycle_file, sanitise_denormals, decode, load_module, load_and_merge_cycles"],
    ["C  Cohort", "apply_filters, audit_duplicates, compute_tscores, apply_menopause_gate"],
    ["D  Derivations", "downloads, supplements, day-2 diet, vit-D crosswalk, menopause / estrogen / derived variables"],
    ["E  Features", "FEATURE_GROUPS, ARM_GROUPS, BMD_DENYLIST, encode_features, power gate, cohorts, Table 1"],
    ["F  Models", "_pipe, model dicts, baselines, bootstrap, Holm, OOF scoring, leaderboard, importance, ablations, nested CV, calibration"],
    ["G  Arms & main", "coefficient diagnostics, RF leaf tuning, evaluate_target, prespecified arms, screening tables, main()"],
], 0.6, 1.55, 7.6, col_w=[1.6, 6.0], size=11.5, row_h=0.6)
bullets(s, [
    (0, "main() order:", ""),
    (1, "downloads → load & merge → filters → dedup audit → T-scores → menopause gate → derivations → save cohort CSV"),
    (1, "encode → cohorts → Table 1 → coef diagnostics"),
    (1, "evaluate both targets (leaderboard + nested CV) → verdict"),
    (1, "ORs / forest plot → ablations → calibration → screening tables → RF tuning → arms"),
    (0, "Outputs:", "save_csv(df, name, tier) writes to outputs/ tagged PRESENT / METHODS / DIAGNOSTIC."),
    (0, "Reproducible:", "seed 42, fixed folds, cached data; 25–40 min runtime."),
    (0, "Not present:", "tests, package, requirements.txt, CI, data versioning."),
], x=8.45, y=1.5, w=4.6, h=5.6, size=13)
notes(s, "Code organisation", """
The whole study is one script. It is intentionally linear: each step function takes a DataFrame and returns one, and prints a banner via print_section. To debug a step you import the module with importlib and call the functions in sequence (CLAUDE.md shows the snippet) rather than adding flags.

The script writes data/processed/analysis_cohort_postmenopausal.csv (1,111 rows × 113 columns) — the analysis input — and everything else goes to outputs/ through save_csv, which stamps a tier: PRESENT (for clinicians), METHODS (defends choices), DIAGNOSTIC (leak/sign detectors, not findings).

Dependencies: pandas, numpy, matplotlib, scikit-learn, lightgbm, xgboost, requests — installed in the system Python, no requirements file. stdout is reconfigured to UTF-8 before imports because the progress output uses emoji and the Windows cp1252 console would raise.

What an engineer will notice is missing, and where they could help: no unit tests (the asserts act as integration tests), no dependency lockfile, no CI, no experiment tracking, no data versioning beyond git. There are also ~20 leftover scratch scripts (_build_*.py, _edit_wt*.py, _stage.py) in the repo root from the rewrite session that should be cleaned up.
""")

# ================================================================ 17 Leaderboard
s = new_slide("Results: model leaderboard (5-fold CV)", "Mean test AUC across folds; RF in-sample AUC is 1.000 by construction — read OOB instead", section="Results")
def lbrows(df):
    out = [["Model", "Test AUC", "Train AUC", "OOB AUC", "Sens", "Spec"]]
    for _, r in df.iterrows():
        oob = f"{r.oob_auc:.3f}" if pd.notna(r.oob_auc) else ("withheld" if "withheld" in str(r.oob_note) else "—")
        out.append([r.Model.replace(" (Aggressive Reg)", "").replace("Elastic Net Logistic Regression", "Elastic-net LR").replace("Logistic Regression (L2)", "Logistic (L2)"),
                    f"{r.auc:.3f}", f"{r.train_auc:.3f}", oob, f"{r.sens:.2f}", f"{r.spec:.2f}"])
    return out
tb = s.shapes.add_textbox(Inches(0.6), Inches(1.4), Inches(6), Inches(0.4))
_run(tb.text_frame.paragraphs[0], "Osteopenia or worse (T ≤ −1.0), 645 / 1,111", 15, True, NAVY)
table(s, lbrows(lb1), 0.6, 1.85, 6.0, col_w=[1.8, 0.85, 0.9, 0.9, 0.7, 0.85], size=12, row_h=0.4)
tb = s.shapes.add_textbox(Inches(6.9), Inches(1.4), Inches(6), Inches(0.4))
_run(tb.text_frame.paragraphs[0], "Osteoporosis (T ≤ −2.5), 76 / 1,111", 15, True, NAVY)
table(s, lbrows(lb2), 6.9, 1.85, 6.0, col_w=[1.8, 0.85, 0.9, 0.9, 0.7, 0.85], size=12, row_h=0.4)
bullets(s, [
    "All five classifiers sit within 0.015 AUC of each other at T ≤ −1.0 — model family barely matters; the features set the ceiling.",
    "Linear models are best or tied; the constrained boosters are lowest. Consistent with a mostly linear, low-dimensional signal (weight, age).",
    "RF at T ≤ −2.5: sensitivity 0.18 at the default 0.5 cutoff, and OOB withheld (only 28% of cases ever out-of-bag).",
    "Sensitivity/specificity use the default 0.5 probability cutoff — see the referral table for operating points.",
], x=0.6, y=4.55, w=12.1, h=2.4, size=14)
notes(s, "Leaderboard", """
These are the per-model numbers from model_leaderboard_*.csv. At T ≤ −1.0: logistic L2 0.756, elastic net 0.756, RF 0.754 (OOB 0.750 — close to test, good sign), LightGBM 0.741, XGBoost 0.738. At T ≤ −2.5: LR 0.781, EN 0.781, RF 0.787, LightGBM 0.771, XGBoost 0.744.

Two lessons for the ML audience:
1. Model family hardly matters. A regularised logistic regression is as good as anything. That points to a feature ceiling, not a modelling problem — more tuning will not help.
2. Train/test gap is not a quality metric here. A random forest with leaf size 1 always fits training data perfectly. The honest in-sample number for a bagged ensemble is OOB AUC.

Remember the leaderboard is still optimistic because we pick the best of eight. That is why the next slide uses nested CV. Also the three regressors are not shown here; in the ablation runs Ridge → T-score had the best full-panel AUC (0.757) and was used as the 'primary model' for ablations and arms.
""")

# ================================================================ 18 Headline
s = new_slide("Headline result: the full panel does not beat OST", "Nested cross-validation, out-of-fold, paired bootstrap 95% CI (1,000 resamples)", section="Results")
picture(s, os.path.join(CH, "nested_verdict.png"), 1.3, 1.3, w=10.7)
table(s, [
    ["Target", "Comparator", "Comp. AUC", "Nested AUC", "Δ", "95% CI", "p (1-sided)", "Verdict"],
] + [[r.Target.replace("Osteopenia+ (T<=-1.0)", "T ≤ −1.0").replace("Osteoporosis (T<=-2.5)", "T ≤ −2.5"),
      r.Comparator.replace("  0.2x(weight-age)", ""), f"{r['Comparator AUC']:.3f}", f"{r['Nested AUC']:.3f}",
      f"{r['Delta vs comparator']:+.3f}", r["95% CI"], f"{r['p (one-sided)']:.3f}", r.Verdict] for _, r in nv.iterrows()],
    0.6, 5.3, 12.1, col_w=[1.2, 1.7, 1.2, 1.3, 0.9, 1.9, 1.3, 2.6], size=12, row_h=0.33)
notes(s, "Headline result", """
This is the bottom line (nested_cv_verdict.csv — the first file to open).

T ≤ −1.0 (645 events): nested AUC 0.751. OST 0.739. Weight alone 0.737. Model minus OST = +0.012, 95% CI −0.005 to +0.030, one-sided p 0.083. Not separable. Versus weight alone: +0.014 [−0.004, +0.031].

T ≤ −2.5 (76 events): nested AUC 0.794 vs OST 0.780 → +0.014 [−0.013, +0.040]. Not separable, and underpowered (events per predictor 4.5). Versus weight alone +0.028 [−0.001, +0.059], p 0.032 — the p is under 0.05 but the CI includes zero; the verdict keys on the CI, which is the conservative and consistent choice (p is the fraction of bootstrap deltas ≤ 0, so any p above 0.025 puts the 2.5th percentile below zero).

Optimism (leaderboard − nested) is +0.005 at T ≤ −1.0 and −0.007 at T ≤ −2.5. A negative optimism at 76 events is noise, not a sign that nesting improves things.

How to say it: '18 survey variables and eight machine-learning models do not measurably improve on a formula that uses weight and age.' That is a legitimate, useful finding — it says the cheap tool is already near the ceiling for this data. Note the y-axis on the chart starts at 0.70 to make the small differences visible.
""")

# ================================================================ 19 Decomposition
s = new_slide("Where the earlier ‘beats OST’ claim went", "Same feature panel and model set; only the cycle list and cohort gate change (auc_decomposition.csv)", section="Results")
picture(s, os.path.join(CH, "auc_decomposition.png"), 0.4, 1.4, w=8.2)
table(s, [
    ["Stage", "n", "Δ vs OST [95% CI]"],
    ["A  6 cycles, all DXA", "1,484", "+0.095 [+0.076, +0.114]"],
    ["B  6 cycles, postmeno", "1,272", "+0.103 [+0.081, +0.125]"],
    ["C  5 cycles, all DXA", "1,308", "+0.012 [−0.003, +0.025]"],
    ["D  5 cycles, postmeno", "1,111", "+0.018 [+0.001, +0.034]"],
], 8.75, 1.55, 4.3, col_w=[1.55, 0.6, 2.15], size=11, row_h=0.42)
callout(s, "Duplicate fix alone (A→C): −0.077\nMenopause gate alone (A→B): −0.006\n\nThe ‘beats OST’ claim dies at stage C, before the menopause gate.",
        8.75, 3.9, 4.3, 2.0, fill=RGBColor(0xfd, 0xe3, 0xd6), size=13, bold=True)
notes(s, "AUC decomposition", """
Two things changed at once in the rewrite (duplicates removed, cohort narrowed to postmenopausal), so we separated them with a 2×2 holding everything else fixed.

A. Six cycles including duplicated 2017–18, all DXA women: best AUC 0.841 vs OST 0.747, Δ +0.095.
B. Same, postmenopausal only: 0.835 vs 0.733, Δ +0.103.
C. Duplicates removed, all DXA: 0.764 vs 0.753, Δ +0.012, CI crosses zero.
D. Shipped cohort: 0.757 vs 0.739, Δ +0.018 [+0.001, +0.034].

Reading it: removing duplicates costs 0.077 AUC; narrowing to postmenopausal costs 0.006. The 'beats OST' claim disappears as soon as duplicates are removed. Note that OST's own AUC barely moves (0.747 → 0.753) — only the flexible models were exploiting the duplicates, exactly what you would expect from leakage: random forests memorise near-identical rows.

Why stage D shows +0.018 with a CI just above zero while the headline says 'not separable': stage D uses the leaderboard best model (Ridge → T), chosen with knowledge of the test folds; the headline uses nested CV (+0.012, CI crossing zero). This is the winner's-curse effect in miniature — and the reason we quote nested CV.

Stage A reads 0.841 rather than the originally published 0.810 because it runs the rebuilt (better-cleaned) feature panel on the old duplicated cohort.
""")

# ================================================================ 20 Ablation
s = new_slide("What the model actually uses: body size", "Refit ablation, primary model Ridge → T-score, T ≤ −1.0, paired bootstrap 500", section="Results")
picture(s, os.path.join(CH, "block_ablation.png"), 0.45, 1.35, w=8.6)
bullets(s, [
    (0, "Drop weight + BMI → 0.605", "(Δ +0.151 [+0.116, +0.185])."),
    (0, "Drop any other block entirely → no measurable change", "(≤ 0.004, CIs cross 0)."),
    (0, "Age + weight alone = 0.739", "= OST's AUC. The other 15 columns add +0.018."),
    (0, "Single-variable ablation:", "only weight_kg survives Holm (+0.019 [+0.008, +0.031])."),
    (0, "Permutation importance:", "weight +0.244 (LR) / +0.151 (RF); next best 0.027."),
    (0, "BMI paradox:", "≈0 in single ablation but 2nd in RF permutation — weight substitutes for it (r = 0.94). Quote the block result."),
], x=9.2, y=1.4, w=3.85, h=5.6, size=12.5)
notes(s, "Body size dominates", """
From model_block_ablation_osteopenia.csv. Each row refits all models without the listed variables (or with only them), on the same folds.

- Drop body size (BMI + weight): AUC 0.757 → 0.605. Δ +0.151 [+0.116, +0.185]. This block is nearly the whole model.
- Drop all menopause/hormone variables (years since menopause, estrogen): 0.753, Δ +0.004 [−0.002, +0.010].
- Drop all lifestyle variables (smoking, alcohol, vigorous activity, sedentary): 0.756, Δ +0.001.
- Drop all history/family variables (prior fracture, steroids, parental hip fracture, family history): 0.754, Δ +0.003.
- Keep only age + weight (OST's inputs): 0.739 — reproduces OST to three decimals.
- Keep only age + BMI: 0.718.

Why single-variable ablation and permutation importance disagree on BMI: BMI and weight are 0.94 correlated. Remove BMI alone and weight covers it (Δ ≈ 0). Shuffle BMI inside a forest that also has weight and the forest loses a little (permutation rank 2 for RF). Only removing both shows the block's real value. Tell clinicians the block number.

Interpretation for the engineer: the signal is low-dimensional and largely captured by body mass. That is physiologically sensible — mechanical loading and adipose-derived estrogen both raise bone density. To improve, we need a genuinely new kind of information, not more questionnaire items of the same type.
""")

# ================================================================ 21 ORs
s = new_slide("Per-predictor effects (adjusted odds ratios)", "L2 logistic regression, all 17 columns together, bootstrap 500 refits; solid = 95% CI excludes 1", section="Results")
picture(s, os.path.join(OUT, "forest_plot_odds_ratios.png"), 0.4, 1.3, h=5.65)
table(s, [
    ["Predictor (unit)", "OR (95% CI)", "Dir."],
    ["weight (per 10 kg)", "0.50 (0.39–0.63)", "protective"],
    ["ever used estrogen", "0.60 (0.45–0.79)", "protective"],
    ["poverty-income ratio (per 1)", "0.89 (0.81–0.97)", "protective"],
    ["age (per 5 y)", "1.28 (1.07–1.54)", "risk"],
    ["any prior fracture", "1.72 (1.15–2.73)", "risk"],
    ["sedentary (per h/day)", "1.06 (1.00–1.10)", "risk (lower bound ≈ 1)"],
    ["steroid use", "1.49 (0.98–2.35)", "ns"],
], 6.75, 1.45, 6.2, col_w=[2.8, 1.9, 1.5], size=12, row_h=0.42)
callout(s, "Caveats: ORs come from a penalised (C = 1), class-weighted sklearn model, so they are shrunk and not classical inference.\nsedentary_min_day is 15.8% median-imputed (mostly the whole 2005–06 cycle).",
        6.75, 5.0, 6.2, 1.6, size=12)
notes(s, "Odds ratios", """
Six of seventeen columns have a confidence interval excluding 1:
- Protective: weight 0.50 per 10 kg (the dominant effect), ever used estrogen 0.60, poverty-income ratio 0.89 per unit (higher income, better bone).
- Risk: age 1.28 per 5 years, any prior fracture 1.72, sedentary time 1.06 per hour/day (lower CI bound rounds to 1.00, so this one is marginal).
- Steroid use 1.49 (0.98–2.35) is not significant.

Everything else (BMI, years since menopause, family history, parental hip fracture, smoking, alcohol, activity, PHQ-9, sleep, diabetes) has a CI spanning 1.

Method caveats a statistician will ask about: these are not statsmodels maximum-likelihood ORs. They come from scikit-learn's L2-penalised logistic regression with balanced class weights, coefficients back-transformed from standardised units to clinical units, with a 500-replicate stratified bootstrap that refits imputation and model each time. Penalisation shrinks ORs toward 1, and class weighting changes the intercept. Directions and relative sizes are reliable; exact values are not textbook ORs. A useful follow-up: refit with an unpenalised GLM (and possibly survey design) for the clinical table.

Associations are not causal and the study is cross-sectional (e.g., estrogen users may differ systematically).
""")

# ================================================================ 22 Arms
s = new_slide("Prespecified arms and power: all null, as stated in advance", section="Results")
ar = [["Arm", "n", "Events", "Base AUC", "Arm AUC", "Δ AUC [95% CI]"]]
for _, r in arms.iterrows():
    d = r["95% CI"]
    if pd.isna(r["Delta AUC"]):
        dd = "n/a — different outcome"
    elif pd.isna(d) or str(d).startswith("n/a"):
        dd = f"{r['Delta AUC']:+.3f} (sensitivity, no CI)"
    else:
        dd = f"{r['Delta AUC']:+.3f} {d}"
    ar.append([r.Arm, f"{r.n:,}", r.Events, f"{r['Base AUC']:.3f}", f"{r['Arm AUC']:.3f}", dd])
table(s, ar, 0.6, 1.4, 8.4, col_w=[3.0, 0.75, 0.75, 1.0, 1.0, 1.9], size=11, row_h=0.42)
table(s, [
    ["Cohort", "EPP T≤−2.5", "EPP T≤−1.0"],
    ["C0 base (17 cols)", "4.5", "27.4"],
    ["C1 + vit D intake", "3.5", "20.1"],
    ["C2 + serum 25(OH)D", "3.8", "22.7"],
    ["C3 + both vit D", "3.0", "16.3"],
    ["C4 + RA", "4.0", "22.4"],
], 9.25, 1.4, 3.7, col_w=[1.7, 1.0, 1.0], size=11, row_h=0.4)
callout(s, "Events per predictor floor = 10.\nEvery T ≤ −2.5 cohort is under-powered → reported as ‘underpowered’, not as a negative finding.",
        9.25, 4.0, 3.7, 1.7, size=12)
notes(s, "Prespecified arms", """
What an arm is: a planned side-experiment. Take the base model (the 17-variable panel), change exactly one thing, refit, and compare against the base model fitted on the same women and the same folds. The term comes from clinical trials, where each arm is one version of the treatment. 'Prespecified' means the list of arms and the expected result for each were written down before anything ran, which is what makes a null reportable rather than fishing.

Each arm adds or substitutes one clinical idea and refits on the same rows and folds as its base model (complete cases for the arm variable).

- C. Calcium + vitamin D intake (diet two-day average + supplements), n 930: −0.002.
- D. Serum 25(OH)D, n 974: −0.001.
- E. Rheumatoid arthritis, n 988 (71 RA): 0.000.
- F. PHQ-9 ≥ 10 instead of the continuous score: −0.001 [−0.002, +0.000] — a negligible loss.
- G1/G2. Diabetes recoded (borderline as diabetic) or dropped: 0.000. Sensitivity only.
- H1/H2. Outcome re-specified to femoral neck only (618 events, 0.747) or total hip only (424 events, 0.776). Different outcome, so no delta.

All nulls were written down before the run, which is what makes them reportable rather than fishing.

Power gate: events per predictor (EPP) = min(events, non-events) / number of model columns. At T ≤ −1.0 the binding class is the 466 non-events → 466 / 17 = 27.4. At T ≤ −2.5, 76 / 17 = 4.5. The gate is named after Riley et al. but is really the classic 10-events-per-variable rule; Riley's sample-size criteria (shrinkage, optimism, precision of intercept) would be a better formal check — a statistician item.
""")

# ================================================================ 23 Calibration & referral
s = new_slide("Calibration and what a referral rule would look like", "Osteopenia+ target; prevalence in this cohort is 58% — PPV will not transfer to a clinic", section="Results")
picture(s, os.path.join(OUT, "calibration_curve.png"), 0.4, 1.3, h=5.0)
rr = [["Flag top", "Sensitivity", "DXAs", "Cases found", "PPV", "Scans/case"]]
for _, r in ref.iterrows():
    rr.append([("all" if r["Top fraction flagged"] == "scan all" else f"{float(r['Top fraction flagged']):.0%}"),
               r.Sensitivity, f"{int(r['DXAs ordered']):,}", r["Cases found"], r.PPV, f"{float(r['Scans per case']):.2f}"])
table(s, rr, 6.35, 1.45, 6.6, col_w=[1.0, 1.2, 0.85, 1.25, 1.0, 1.3], size=12, row_h=0.4)
bullets(s, [
    "Sigmoid-calibrated RF: Brier 0.198 vs 0.199 raw — already well calibrated.",
    "Flag the top 30% → find 44% of cases at 1.18 scans per case (vs 1.72 scanning everyone).",
    "Referral table uses nested-CV ranks (quantiles), the threshold sweep uses calibrated probabilities — never merge them.",
    "The cutoff choice is clinical; the osteoporosis referral table was withdrawn (underpowered).",
], x=6.35, y=4.45, w=6.6, h=2.5, size=13)
notes(s, "Calibration and referral", """
Calibration: the random forest out-of-fold probabilities, raw and sigmoid-calibrated (CalibratedClassifierCV, 3-fold, inside the outer 5-fold), 10 quantile bins. Both track the diagonal; Brier 0.199 raw, 0.198 calibrated.

Referral table (referral_table.csv): flag the top X% of women by nested-CV out-of-fold rank. For example, flagging the top 30% orders 335 scans, finds 284 of 645 cases (44% sensitivity), PPV 85%, 1.18 scans per case found. Scanning everyone finds all 645 at 1.72 scans per case.

Threshold sweep (threshold_sweep.csv) is a different object: literal probability cutoffs on the calibrated forest (e.g., cutoff 0.30 → 98% sensitivity, 1,039 scans). Same-looking numbers, different meaning; they are kept separate on purpose.

Big caveat: 58% of this cohort is positive at T ≤ −1.0, so PPV and scans-per-case are inflated relative to a real clinic population. And OST would give almost the same table — the referral table illustrates utility, it does not show ML beats OST.

A useful extension: decision-curve analysis (net benefit) of model vs OST vs scan-all vs scan-none.
""")

# ================================================================ 24 Caveats
s = new_slide("Known caveats from code review (our backlog)", "Found while preparing this briefing — none changes the headline null, all are worth fixing or disclosing", section="Critique")
table(s, [
    ["Item", "Detail", "Impact"],
    ["Structural missingness imputed", "sedentary & vigorous activity missing for all of 2005–06, median-imputed", "Moderate: one 'significant' OR rests partly on imputed values"],
    ["Prior-fracture window", "Specialist asked for a 5-year window; any-age fracture shipped", "Clinical validity"],
    ["No survey design", "Weights / strata / PSU unused; results not nationally representative", "Generalisability"],
    ["Bootstrap scope", "Resamples fixed OOF scores; no refit variance; reports mean Δ", "CIs somewhat too narrow"],
    ["Optimism metric", "Leaderboard = mean of fold AUCs; nested = pooled OOF AUC", "Small, mixes aggregations"],
    ["Odds ratios", "Penalised (C = 1), class-weighted LR — shrunk, not MLE", "Labelling"],
    ["RF leaf size", "Shipped 1 = grid best (0.7536), but inner-CV picks vary [20, 2, 1, 1, 20]; docs say ‘nested-CV chosen’", "Negligible"],
    ["Power gate naming", "10-EPV rule labelled ‘Riley’", "Labelling"],
    ["Docs drift", "CLAUDE.md says 66,023 start (actually 56,769), ‘clipped’ PHQ items, ‘thresholded’ regressors", "Documentation"],
    ["Hygiene", "Warnings globally suppressed; ~20 scratch scripts in repo root; no tests / lockfile", "Maintainability"],
], 0.6, 1.5, 12.1, col_w=[2.6, 6.0, 3.5], size=12, row_h=0.47)
notes(s, "Known caveats", """
Being upfront here builds credibility with an engineer. None of these would turn the null into a positive result — if anything, wider (refit) bootstrap intervals make the null more robust.

Most substantive:
1. The activity variables are missing for an entire cycle (2005–06 used a different questionnaire) yet are median-imputed. That violates the stated rule of not imputing structural absence, and sedentary_min_day is one of the six predictors with a CI excluding OR = 1. Fix options: add a missing indicator, restrict to cycles that collected it, or multiple imputation.
2. The specialist's request for a 5-year prior-fracture window was never implemented and nothing records why. NHANES asks age at each fracture (OSQ020x / OSQ040), so it is constructible.
3. No survey weights or design — fine for internal prediction, but any prevalence or 'representative' claim is off the table.

Statistical scope: the bootstrap resamples the out-of-fold predictions, so it captures sampling variability of the test set but not refitting variability; repeated cross-validation with several seeds would give a fuller picture.

Docs drift: CLAUDE.md quotes the old 66,023 starting count (six cycles); the code and log say 56,769. Also small wording mismatches (PHQ items are mapped, not clipped; regressors are rank-scored, not thresholded).

Hygiene: warnings.filterwarnings('ignore') hides solver convergence warnings (saga on elastic net could be affected); ~20 scratch scripts from the rewrite clutter the repo root; no tests, lockfile or CI.
""")

# ================================================================ 25 Statistician questions
s = new_slide("Questions to take to a statistician", section="Next steps")
bullets(s, [
    (0, "Framing the null:", "should we test equivalence / non-inferiority to OST (e.g., TOST with a ±0.02 margin) instead of ‘not separable’? What margin is clinically meaningful?"),
    (0, "Power:", "what n / events would detect ΔAUC = 0.02 over OST with 80% power, given model–OST correlation? Is adding 2015–16 and 2021–23 worth it?"),
    (0, "Uncertainty:", "refit-inside bootstrap or repeated nested CV (e.g., 10 × 5-fold) instead of resampling fixed OOF scores? DeLong as a cross-check?"),
    (0, "Missing data:", "MICE vs in-fold median; how to treat whole-cycle structural absence (activity, supplements); missing indicators?"),
    (0, "Survey design:", "is unweighted prediction acceptable? Should Table 1 / ORs use design-based estimation per cycle?"),
    (0, "Small target (76 events):", "Firth / penalised LR, regress-then-threshold, or report descriptively only? Proper Riley sample-size criteria?"),
    (0, "Outcome choice:", "continuous T-score as primary (specialist’s preference) with R² / MAE and calibration slope?"),
    (0, "Clinical utility:", "decision-curve analysis and reclassification (NRI) vs OST — more informative than ΔAUC?"),
    (0, "Inference:", "unpenalised GLM for the OR table; multiplicity over ablations and arms; acceptability of the BMD-keyed vitamin D crosswalk."),
], size=14.5)
notes(s, "Statistician questions", """
These are the questions we most need help with, roughly in priority order.

1. The headline is a null. A null from a confidence interval is 'absence of evidence'. The stronger, more publishable statement is equivalence: 'the ML model is within ±δ of OST'. That needs a pre-declared margin (δ = 0.02 or 0.03 AUC?) and a TOST-style test. With the current CI [−0.005, +0.030], we could already claim non-inferiority at a margin of 0.01 but not equivalence at 0.02 — worth a statistician's view.

2. Power. With roughly 1,100 women and model–OST score correlation around 0.9, what is the minimum detectable ΔAUC? If even double the data could not detect a clinically meaningful gain, that is a decision to stop rather than add cycles. 2015–16 and 2021–23 are on disk but excluded by choice; the T ≤ −2.5 target especially would benefit.

3. Uncertainty estimation. Our bootstrap resamples fixed predictions. Repeated CV (different seeds), or a bootstrap that refits, would include model-fitting variance. DeLong's test for correlated AUCs is a standard cross-check.

4. Missing data. Is single median imputation acceptable at < 6%? For whole-cycle gaps (activity in 2005–06), is it better to drop the variable, the cycle, or use MI with cycle as a predictor?

5. Survey weights. Specialist asked for weighted vs unweighted; pooled weights are not constructible across non-contiguous cycles with different bases. Is unweighted prediction acceptable, with per-cycle weighted descriptives?

6. The T ≤ −2.5 target has 76 events. Options: Firth logistic, regression on continuous T then threshold (current approach), or descriptive only. Should we apply Riley et al. (2020) sample-size criteria formally?

7. Outcome: should the continuous T-score be primary, as the specialist wanted, evaluated with R², MAE, calibration slope?

8. Clinical utility: decision curve analysis (net benefit across thresholds) and net reclassification vs OST often say more than ΔAUC.

9. Inference details: unpenalised GLM for the ORs; is Holm over 18 ablations the right family; is matching vitamin D across releases on BMD (which is in the outcome) acceptable?
""")

# ================================================================ 26 Directions
s = new_slide("Suggested directions", section="Next steps")
bullets(s, [
    (0, "1. Report the null properly.", "Pre-register an equivalence margin; add decision-curve analysis vs OST; publish ‘OST is near the ceiling for questionnaire data’."),
    (0, "2. Get more events, carefully.", "Revisit the deliberately excluded 2015–16 and 2021–23 cycles (check DXA protocol comparability); consider broadening age or race/ethnicity with appropriate T-score references and interaction terms."),
    (0, "3. Bring in new kinds of signal, not more of the same.", "Height loss / height vs self-reported max height, weight change since age 25/40, grip strength (MGX, limited cycles), medications via RXQ_RX (PPIs, SSRIs, glucocorticoid detail, aromatase inhibitors), lab markers."),
    (0, "4. Change the target.", "Model continuous T-score as primary; long term, fracture outcomes need a prospective cohort (e.g., SOF, MrOS, UK Biobank) — also enables external validation."),
    (0, "5. External / temporal validation.", "Train on 2005–2014, test on 2017–2020 as a temporal hold-out."),
    (0, "6. Engineering hardening.", "Fix structural imputation & fracture window; repeated-seed CV; pin deps (requirements.txt); unit tests for decode / SPEC / cohort asserts; remove scratch scripts; experiment tracking (e.g., MLflow)."),
], size=15)
notes(s, "Suggested directions", """
Directions, ordered by expected value.

1. Treat the null as the result. The finding that a two-input formula is at the ceiling for questionnaire data is useful to clinicians — it says don't bother with a longer questionnaire. Strengthen it with an equivalence framing and decision-curve analysis.

2. More events. The binding constraint is the 76 osteoporosis cases. The 2015–16 and 2021–23 cycles are already downloaded but were excluded by the project lead's choice; adding them needs care (check DXA scanner and protocol comparability; 2021–23 is a post-COVID design). Broadening race/ethnicity needs race-appropriate reference values or a single reference with race as a covariate — a clinical decision.

3. New information. The ablation says body size is everything; more questionnaire items of the same type will not help. Candidates that are genuinely different: height loss (strong clinical marker of vertebral fracture), weight history, grip strength (only some cycles), medications (prescription file RXQ_RX — the specialist noted mapping is needed), biochemistry. Each must be checked for cycle availability — whole-cycle gaps are a recurring problem.

4. Target. Low BMD is a surrogate. A fracture model needs longitudinal data; NHANES has none, so an external cohort is required and would also provide external validation.

5. Temporal validation within NHANES is cheap: train on older cycles, test on 2017–2020.

6. Engineering: the items from the caveats slide, plus tests and a lockfile. These are good starter tasks for an engineer joining the project.
""")

# ================================================================ 27 Asks
s = new_slide("Where we would value your input", section="Next steps")
bullets(s, [
    (0, "Pipeline review:", "is the leakage defence (allowlist, fingerprint audit, in-fold preprocessing, nested CV) complete? What would you add?"),
    (0, "Validation strategy:", "repeated nested CV vs refit bootstrap — compute budget is ~25–40 min per full run today."),
    (0, "Code structure:", "split the 2,060-line script into a package with tests, or keep one auditable file?"),
    (0, "Data engineering:", "a robust NHANES loader (cycle registry, label/code decoding, cross-release duplicate detection) could be reusable across projects."),
    (0, "Reproducibility:", "dependency pinning, data versioning (DVC?), experiment tracking."),
    (0, "Modelling:", "anything we are missing given a near-linear, body-size-dominated signal? (We believe more model tuning will not help.)"),
], size=17, h=4.3)
callout(s, "Bottom line: a careful pipeline, a real data defect found and fixed, and an honest null —\nOST (weight & age) is essentially as good as an 18-variable ML panel on NHANES data.",
        0.6, 5.7, 12.1, 1.05, fill=NAVY, color=WHITE, size=17, bold=True)
notes(s, "Asks", """
Close by turning the session into a working discussion. Specific asks for a senior ML/data engineer:

- Sanity-check the leakage defences. In particular: is a 5-field physical fingerprint a sufficient cross-release duplicate check? Would they use GroupKFold on a fingerprint hash as belt-and-braces?
- Advise on validation compute: repeated nested CV (e.g., 10 seeds) multiplies a 25–40 minute run; could the expensive parts (permutation importance, ablation grid) be parallelised or cached?
- Advise on structure: the single-file design is easy to audit for a clinical audience, but hard to test. A middle path: keep the step functions, move them into a small package, add pytest for decode/SPEC/cohort counts.
- NHANES ingestion is reusable: cycle registry, label-vs-code decoding, denormal handling, cross-release duplicate detection.

Final message: we built a defensible pipeline, found a subtle duplicated-entity leakage bug that had inflated earlier results, fixed and guarded it, and the honest conclusion is that a two-variable clinical formula is as good as our machine-learning panel. The next gains come from new data, not new models.
""")

# ================================================================ Appendix
s = new_slide("Appendix: per-variable sentinel SPEC (examples)", section="Appendix")
table(s, [
    ["Column", "Kind", "Sentinels → NaN", "Valid range", "Note"],
    ["RIDAGEYR (age)", "num", "—", "0–120", ""],
    ["BMXWT (weight)", "num", "—", "25–250 kg", "77 / 99 kg are real weights"],
    ["DXXNKBMD / DXXOFBMD", "num", "—", "0.2–1.8 g/cm²", "label source; denylisted"],
    ["PAD680 (sedentary)", "num", "7777, 9999", "0–1440 min", "99 is valid here"],
    ["ALQ130 (drinks/day)", "num", "777, 999, 99", "1–30", "0-filled for non-drinkers"],
    ["SLD010H / SLD012 (sleep)", "num", "77, 99", "2–14 h", "7 / 9 h are real"],
    ["RHQ060 (age last period)", "num", "999, 9999, 77777, 99999", "20–70", "99 is refusal here"],
    ["DPQ010–090 (PHQ-9)", "cat", "7, 9", "levels 0–3", "words or codes"],
    ["DIQ010 (diabetes)", "cat", "7, 9", "yes / no / borderline", "borderline → 0"],
    ["OSQ / RHQ yes-no items", "yesno", "refused, don't know", "Yes/1 → 1, No/2 → 0", ""],
    ["DSQTCALC / DSQTVD", "num", "—", "0–5000 mg / 0–3000 µg", "supplements"],
], 0.6, 1.4, 12.1, col_w=[3.0, 0.9, 2.6, 2.6, 3.0], size=12, row_h=0.44)
notes(s, "Appendix: SPEC", """
Reference slide for questions about sentinel handling. The point: NHANES uses 7/9, 77/99, 777/999 etc. for refused and don't know, but which codes are sentinels depends on the variable's range. A global list deleted genuine values (sleep 7 or 9 hours, weight 77 or 99 kg, 7 or 9 drinks). SPEC declares, per column, the kind, the sentinel codes and the valid range; values outside the range become NaN after decoding.
""")

s = new_slide("Appendix: glossary", section="Appendix")
table(s, [
    ["Term", "Meaning"],
    ["NHANES", "National Health and Nutrition Examination Survey (CDC/NCHS), 2-year cycles"],
    ["SEQN", "Respondent ID within a release — NOT stable across releases"],
    ["DXA / BMD", "Dual-energy X-ray absorptiometry / bone mineral density (g/cm²)"],
    ["T-score", "(BMD − young-adult mean) / SD; ≤ −1.0 low bone mass, ≤ −2.5 osteoporosis"],
    ["OST", "Osteoporosis Self-assessment Tool = 0.2 × (weight kg − age yr)"],
    ["Nested CV", "Model selection inside each outer training fold; unbiased estimate of the selection procedure"],
    ["OOB AUC", "Out-of-bag AUC: each row scored only by trees that did not see it"],
    ["EPP / EPV", "Events per predictor (variable); rule-of-thumb floor 10"],
    ["Holm", "Step-down family-wise error correction for multiple p-values"],
    ["PHQ-9", "9-item depression questionnaire, 0–27"],
    ["Brier score", "Mean squared error of predicted probabilities (lower is better)"],
    ["PPV", "Positive predictive value = cases found / scans ordered"],
], 0.6, 1.4, 12.1, col_w=[2.2, 9.9], size=12.5, row_h=0.42)
notes(s, "Appendix: glossary", "Reference definitions for terms used throughout the deck.")

deck_path = os.path.join(HERE, "Osteoporosis_ML_Briefing_for_ML_Engineer.pptx")
prs.save(deck_path)

# ================================================================ DOCX notes
d = docx.Document()
st = d.styles["Normal"]; st.font.name = "Segoe UI"; st.font.size = DPt(10.5)
d.add_heading("Presenter notes — Osteoporosis ML briefing for a Senior AI/ML Data Engineer", 0)
d.add_paragraph("Companion to Osteoporosis_ML_Briefing_for_ML_Engineer.pptx. Numbers come from the 2 Oct 2026 run of "
                "OsteoporosisML.py (outputs/ folder). Pre-rewrite AUCs (0.810, 0.806, 0.833) are withdrawn and must not be quoted.")
d.add_heading("Suggested timing (≈ 50 min + discussion)", 1)
for t in ["Overview & data (slides 1–6): 12 min", "Cohort, target, specialist decisions (7–10): 10 min",
          "Features, missing data, guard-rails, models, evaluation, code (11–16): 12 min",
          "Results (17–23): 12 min", "Caveats, statistician questions, directions, asks (24–27): 8 min + discussion"]:
    d.add_paragraph(t, style="List Bullet")
d.add_heading("Slide-by-slide notes", 1)
for i, (title, text) in enumerate(SLIDES, 1):
    d.add_heading(f"Slide {i} — {title}", 2)
    for para in text.split("\n"):
        if para.strip():
            style = "List Bullet" if para.strip().startswith("- ") else None
            d.add_paragraph(para.strip()[2:] if style else para.strip(), style=style)

d.add_heading("Likely questions from the audience — prepared answers", 1)
QA = [
    ("Why not GroupKFold?", "After removing the duplicated 2017–18 cycle there is exactly one row per woman, so StratifiedKFold on rows equals grouping by person. The fingerprint audit asserts this. GroupKFold on a fingerprint hash would be a cheap extra safeguard."),
    ("Why median imputation rather than MICE or native NaN handling in LightGBM/XGBoost?", "Most variables are < 6% missing, and imputation is inside the fold so it does not leak. Using one pipeline for all models keeps comparisons fair. The weak spot is the 13–16% structural gaps (activity, alcohol); MICE or missing indicators are on the list for the statistician."),
    ("Why such heavily regularised boosters? Did you tune them?", "With ~1,100 rows and 76 rare events, boosters overfit easily (train AUC 0.93–0.98 at T ≤ −2.5 even when constrained). We chose to under-fit rather than report a tuned booster. The near-identical AUCs across all model families indicate a feature ceiling, so tuning is unlikely to close the gap to a meaningful level — but it has not been systematically searched."),
    ("Why AUC and not PR-AUC or log-loss?", "AUC is the clinical-literature convention and the comparator (OST) is a score without probabilities. Calibration is assessed separately (Brier, calibration curve). PR-AUC would be informative for the 6.8%-prevalence target."),
    ("Is the bootstrap CI valid?", "It is a paired, stratified bootstrap of out-of-fold scores; it captures test-sample variability but not model-refit variability, so intervals are somewhat narrow. That would only strengthen the null. Repeated CV is the planned upgrade."),
    ("Could deep learning or AutoML help?", "Unlikely: n ≈ 1,100, tabular, signal dominated by one variable. Linear models already match the forest. Gains would need new information."),
    ("Why ignore survey weights?", "Pooled weights cannot be constructed consistently across non-contiguous cycles with different weight bases (2-year vs 3.2-year P_). For prediction, unweighted fitting is common; the cost is that prevalence and PPV are not nationally representative."),
    ("How do you know there are no other leaks?", "Allowlist + denylist assert, in-fold preprocessing, nested model selection, the |coef| > 2 leak alarm (largest is weight at −1.21), and the fact that OST — which cannot leak — scores within 0.012 of the model."),
    ("How long does it take to run and can it be parallelised?", "≈ 25–40 minutes; dominated by bootstraps, permutation importance, the ablation grid (17 variables × 8 models) and nested CV. Folds and ablation variables are embarrassingly parallel."),
    ("Is the code production-ready?", "No; it is a reproducible research pipeline: deterministic, asserted, but without tests, packaging, lockfile or CI."),
]
for q, a in QA:
    p = d.add_paragraph(); r = p.add_run(q); r.bold = True
    d.add_paragraph(a)

d.add_heading("Numbers cheat-sheet", 1)
for t in [
    "Respondents in 5 cycles: 56,769 → female 28,644 → NH White 10,672 → age 50–65 1,639 → femoral-neck DXA 1,308 → postmenopausal 1,111.",
    "Menopause gate exclusions: 156 still cycling; 41 undeterminable (not premenopausal).",
    "By cycle: 2005–06 173; 2007–08 228; 2009–10 227; 2013–14 219; 2017–20 264.",
    "Events: T ≤ −1.0 645 (58.1%); T ≤ −2.5 76 (6.8%). Normal 466, low bone mass 569, osteoporosis 76.",
    "Panel: 17 variables, 17 columns. Arms: intake n 930, serum n 974, RA n 988.",
    "Nested AUC T ≤ −1.0: 0.751 vs OST 0.739 (Δ +0.012 [−0.005, +0.030]) vs weight 0.737 (Δ +0.014 [−0.004, +0.031]).",
    "Nested AUC T ≤ −2.5: 0.794 vs OST 0.780 (Δ +0.014 [−0.013, +0.040]) vs weight 0.766 (Δ +0.028 [−0.001, +0.059]).",
    "Block ablation: drop body size 0.606; keep only age + weight 0.739; full 0.757 (Ridge → T).",
    "Decomposition: duplicates −0.077; menopause gate −0.006.",
    "Significant ORs: weight 0.50/10 kg; estrogen 0.60; PIR 0.89; age 1.28/5 y; prior fracture 1.72; sedentary 1.06/h (marginal).",
    "Calibration Brier 0.199 raw / 0.198 sigmoid. Top 30% flagged → 44% sensitivity, PPV 85%, 1.18 scans per case.",
]:
    d.add_paragraph(t, style="List Bullet")

d.add_heading("Source files", 1)
for t in ["OsteoporosisML.py (pipeline, blocks A–G)", "outputs/*.csv, *.png (results, 2 Oct 2026 run)", "_run_no_menotype.log (counts and verdicts)",
          "Notes/specialist_answers_and_decisions.html, Specialist_Review_Questions/Answers.docx (clinical decisions)",
          "Notes/statistician_brief.html (methodological rulings and open questions)",
          "Notes/presentation_ml_engineer/make_charts.py and build_deck.py (regenerate this deck)"]:
    d.add_paragraph(t, style="List Bullet")

notes_path = os.path.join(HERE, "Presenter_Notes_Osteoporosis_ML_Briefing.docx")
d.save(notes_path)
print("wrote", deck_path)
print("wrote", notes_path)
print("slides:", len(prs.slides))
