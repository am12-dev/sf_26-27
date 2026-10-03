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
PALEBLUE = RGBColor(0xdc, 0xe9, 0xf8)
GREEN = RGBColor(0x1b, 0x7f, 0x5a)
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


def table2(slide, rows, x, y, w, col_w=None, size=12, row_h=0.36, hi_rows=()):
    """Table with optional highlighted rows (used by the plain-English slides)."""
    nr, nc = len(rows), len(rows[0])
    t = slide.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(row_h * nr)).table
    if col_w:
        for i, cw in enumerate(col_w):
            t.columns[i].width = Inches(cw)
    for r in range(nr):
        t.rows[r].height = Inches(row_h)
        for c in range(nc):
            cell = t.cell(r, c)
            cell.margin_left = cell.margin_right = Inches(0.07)
            cell.margin_top = cell.margin_bottom = Inches(0.02)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame; tf.word_wrap = True
            if r == 0:
                _run(tf.paragraphs[0], str(rows[r][c]), size, True, WHITE)
                cell.fill.solid(); cell.fill.fore_color.rgb = NAVY
            else:
                _run(tf.paragraphs[0], str(rows[r][c]), size, r in hi_rows, INK)
                cell.fill.solid()
                cell.fill.fore_color.rgb = PALEBLUE if r in hi_rows else (WHITE if r % 2 else LIGHT)
    return t


def box(slide, text, x, y, w, h, fill=LIGHT, color=INK, size=15, bold=False, align=PP_ALIGN.LEFT,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    b = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        b.adjustments[0] = 0.08
    b.fill.solid(); b.fill.fore_color.rgb = fill; b.line.fill.background()
    tf = b.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.12)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, ln in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        _run(p, ln, size, bold, color)
    return b


def ci(v):
    return str(v).replace("-", "−")


def f3(v):
    return f"{v:.3f}"


# ---------------------------------------------------------------- data
nv = pd.read_csv(os.path.join(OUT, "nested_cv_verdict.csv"))
lb1 = pd.read_csv(os.path.join(OUT, "model_leaderboard_osteopenia.csv"))
lb2 = pd.read_csv(os.path.join(OUT, "model_leaderboard_osteoporosis.csv"))
arms = pd.read_csv(os.path.join(OUT, "prespecified_arms.csv"))
ref = pd.read_csv(os.path.join(OUT, "referral_table.csv"))
cpt = pd.read_csv(os.path.join(OUT, "clinical_predictor_table.csv"))


def vrow(target_prefix, comp_prefix):
    m = nv[nv["Target"].str.startswith(target_prefix) & nv["Comparator"].str.startswith(comp_prefix)]
    return m.iloc[0]


op_ost, op_w = vrow("Osteopenia", "OST"), vrow("Osteopenia", "Weight")
os_ost, os_w = vrow("Osteoporosis", "OST"), vrow("Osteoporosis", "Weight")
N, E1, E2 = 1111, int(op_ost["Events"]), int(os_ost["Events"])

# ================================================================ 1 title
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH)
bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
tb = s.shapes.add_textbox(Inches(0.9), Inches(2.0), Inches(11.5), Inches(3.5))
tf = tb.text_frame; tf.word_wrap = True
_run(tf.paragraphs[0], "Screening for Low Bone Mass Without a DXA Scan", 40, True, WHITE)
p = tf.add_paragraph(); _run(p, "An NHANES machine-learning pipeline: data, cohort, models and results", 22, False, WHITE)
p = tf.add_paragraph(); p.space_before = Pt(30)
_run(p, "Technical briefing for a Senior AI/ML Data Engineer  ·  sf_26-27 / OsteoporosisML.py", 16, False, RGBColor(0xb7, 0xd3, 0xf6))
p = tf.add_paragraph()
_run(p, "Postmenopausal women aged 50–65, NHANES 2005–2020, n = 1,111", 14, False, RGBColor(0xb7, 0xd3, 0xf6))
notes(s, "Title", """
Purpose of this session: walk a senior ML/data engineer through the whole project end to end — where the data comes from, how it is downloaded and cleaned, how the analysis cohort is built, which clinical decisions were made with the osteoporosis specialist, how the models are coded and evaluated, what the final results are, and where we want help.

Frame it up front: this is a research pipeline, not a production system. It is one Python file (OsteoporosisML.py, ~2,060 lines, blocks A–G), runs end to end in roughly 25–40 minutes, seed 42, fully reproducible.

The punchline, so nobody waits for it: the ML model is NOT statistically distinguishable from a two-input clinical formula (OST = 0.2 × (weight − age)). We will show how the models were built and tested, why we believe that result, and what we want to do next.

All numbers in this deck come from the outputs/ folder of OsteoporosisML.py.
""")

# ================================================================ 2 TL;DR
s = new_slide("The one-slide summary", section="Overview")
bullets(s, [
    (0, "Question:", "can routinely collected survey answers flag women likely to have low bone mass, so DXA is ordered for the right people?"),
    (0, "Data:", "NHANES, 5 survey cycles 2005–2020 → 1,111 postmenopausal non-Hispanic White women aged 50–65 with a hip DXA."),
    (0, "Target:", "T-score ≤ −1.0 (osteopenia or worse; 645 cases, 58%) and ≤ −2.5 (osteoporosis; 76 cases, 6.8%)."),
    (0, "Models:", "5 classifiers + 3 T-score regressors, 15 variables (16 columns), 5-fold stratified CV, nested CV for model choice, paired bootstrap CIs."),
    (0, "Result:", "nested-CV AUC 0.747 vs OST formula 0.739 → Δ +0.008 [−0.008, +0.025]. Not separable. Same story at T ≤ −2.5 (0.786 vs 0.780)."),
    (0, "Why:", "body weight carries nearly all the signal. Drop weight + BMI → AUC 0.603; drop any other block → no measurable change."),
    (0, "Engineering point:", "NHANES ships 2017–18 twice under different IDs; the pipeline uses one copy and asserts one row per woman."),
    (0, "Ask:", "help us decide whether this is a publishable null, and what data / design changes could move the needle."),
], size=17)
notes(s, "The one-slide summary", """
Read this slide slowly; everything after it is supporting detail.

Key framing for an ML audience:
- The comparator matters more than the AUC. A 0.75 AUC sounds respectable until you see that weight alone gets 0.737 and the two-input OST formula gets 0.739.
- The result is a null, and we are reporting it as one. The confidence interval on the improvement over OST crosses zero for both targets.
- The most interesting engineering point is a data trap: NHANES releases 2017–2018 twice (once on its own and again inside the pooled 2017–March 2020 'P_' files) with re-numbered respondent IDs, so ID-based de-duplication cannot see it. If both were loaded, the same women could sit in training and test folds — classic leakage through duplicated entities. The pipeline loads only the pooled file and asserts one row per woman.

Counts to remember: 1,111 women; 645 at T ≤ −1.0; 76 at T ≤ −2.5; 15 variables / 16 model columns; 8 models.
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

Why OST: it is the established, cheap screening tool that already uses only weight and age. If a model using 15 survey variables cannot beat a formula you can do in your head, it adds nothing clinically. So the estimand is the DIFFERENCE in AUC between the model and OST, measured on the same women, with a paired bootstrap confidence interval.

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
    ["RHQ", "periods, age at last period, estrogen"],
    ["OSQ", "prior fractures, steroids, family history"],
    ["MCQ / DIQ", "arthritis type, diabetes"],
    ["SMQ / ALQ", "smoking, alcohol"],
    ["PAQ / SLQ / DPQ", "activity, sleep, PHQ-9 depression"],
    ["DR1TOT / DR2TOT", "24-h dietary recall day 1 / day 2"],
    ["DSQTOT", "dietary supplements"],
    ["VID", "serum 25(OH) vitamin D (lab)"],
], 7.2, 1.5, 5.5, col_w=[1.8, 3.7], size=12, row_h=0.36)
callout(s, "Not used: 2011–12, 2015–16 and 2021–23 (no hip DXA was done);\n2017–18 standalone file (the same women are inside the pooled P_ file — see slide 6).", 0.6, 6.45, 12.1, 0.55, size=12)
notes(s, "Data source: NHANES", """
NHANES is run by the CDC's National Center for Health Statistics. Each two-year cycle is a fresh, nationally representative sample, released as many separate files (modules). Every file has the respondent ID, SEQN, and we left-join everything onto the demographics file (DEMO) within each cycle, then stack the cycles.

Cycle suffixes: D = 2005–06, E = 2007–08, F = 2009–10, H = 2013–14. The 2017–March 2020 release uses a 'P_' prefix instead of a suffix. COVID stopped field work in March 2020, so NCHS combined the partial 2019–2020 sample with the complete 2017–2018 cycle into these P_ files.

Modules used (from MODULE_COLS in block B): DEMO, BMX, DXXFEM, DR1TOT, VID, PAQ, DPQ, SMQ, ALQ, DIQ, MCQ, OSQ, RHQ, SLQ, plus the runtime downloads DSQTOT (supplements) and DR2TOT (day-2 diet). VID does not exist for the P_ cycle (declared as KNOWN_ABSENT).

Which cycles are in: five cycles, 1,111 women. Hip (femur) DXA was only done in 2005–2010, 2013–2014 and 2017–March 2020, so 2011–12, 2015–16 and 2021–23 cannot supply an outcome. The standalone 2017–2018 file is not loaded because the same women are already inside the pooled P_ files.

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
    (1, "Example: 99 is 'refused' for RHQ060 (age at last period) but a legitimate value for PAD680 (sedentary minutes). A single global sentinel list would delete real data (sleep of 7 or 9 h, weights of 77 or 99 kg)."),
    (0, "Denormal floats:", "NHANES encodes zero as 5.4e-79 in P_ and nutrient files; sanitise_denormals() snaps |v| < 1e-30 to 0.0 on every frame."),
], size=15)
notes(s, "Data acquisition", """
This slide is aimed squarely at a data engineer — these are the ingestion traps the loader is built to handle.

1. File discovery. Filenames are built explicitly from the CYCLES table (block A): {prefix}{module}.csv for P_ or {module}_{suffix}.csv otherwise. Globbing is deliberately avoided: OSQ_*.csv does not match P_OSQ.csv, so a glob would silently drop the most recent cycle from the fracture/steroid variables, and a stray 'P_DEMO (1).csv' in that folder would be picked up.

2. Runtime downloads. Two module families are fetched on demand: DSQTOT (total dietary supplement intake) for E, F, H and P_, and DR2TOT (day-2 24-hour dietary recall) for D, E, F, H and P_. Download is requests.get with a 90-second timeout, raise_for_status, write to a temporary .xpt, read with pandas.read_sas(format='xport'), keep only SEQN plus the nutrient columns, save as CSV, delete the temp file. The cache check is 'exists and larger than 2 KB'. Any exception prints '!! download failed' and returns an empty frame, so the pipeline still completes. With the committed caches, every download is a cache hit. There is no 2005–06 DSQTOT release in the URL table, so supplements are unobserved for that cycle.

3. Label-decoded vs numeric. The older CSVs were exported with value labels, so RIAGENDR is 'Female' not 2 and yes/no items are 'Yes'/'No'; the P_ files are numeric. decode() normalises strings (lower-case, strip, treat '', 'nan', '.', 'none' as missing, strip a trailing '.0'), then maps per the SPEC entry. Refused / don't-know words map to NaN.

4. SPEC (block B) is a dictionary declaring for each column: kind, sentinel codes, valid range, and category levels. Values outside the valid window become NaN. Examples: BMXWT 25–250 kg; DXXNKBMD 0.2–1.8 g/cm²; PAD680 sentinels 7777/9999, valid 0–1440 minutes; SLD012 sleep sentinels 77/99, valid 2–14 hours; ALQ130 sentinels 777/999/99, valid 1–30.

5. Denormals. Some NHANES SAS-exported files store zero as a tiny denormal float (5.397605346934028e-79). Without fixing it, nutrient columns appear to contain no zeros. sanitise_denormals runs on every loaded frame.
""")

# ================================================================ 6 Merge
s = new_slide("Merging cycles, and keeping one row per woman", section="Data")
bullets(s, [
    (0, "Merge:", "within a cycle, functools.reduce of left joins on SEQN starting from DEMO; then pd.concat across cycles + a survey_cycle column. 56,769 respondents in 5 cycles."),
    (0, "The trap:", "NCHS re-released the complete 2017–2018 cycle inside the pooled P_ 2017–2020 files with re-numbered SEQNs."),
    (1, "DEMO_J SEQN 93,703–102,956 vs P_DEMO 109,263–124,822 → IDs never collide, so SEQN de-duplication cannot see repeats."),
    (1, "Loading both would put 176 cohort women in the data twice, and StratifiedKFold could place the two copies in train AND test."),
    (0, "Design:", "only the pooled P_ file is loaded; the standalone 2017_2018 cycle is not in CYCLES."),
    (0, "Guard:", "audit_duplicates() asserts zero duplicates on a physical fingerprint: femoral-neck BMD, total-hip BMD, weight, height, age."),
    (1, "1,306 of 1,308 rows have a complete fingerprint; 0 duplicates. A repeat cannot enter silently."),
], size=16, h=4.6)
callout(s, "One row per woman is what makes ordinary stratified cross-validation valid here.",
        0.6, 6.0, 12.1, 0.75, fill=RGBColor(0xcd, 0xe2, 0xfb), color=NAVY, size=16, bold=True)
notes(s, "One row per woman", """
This is a good story for an ML audience because it is a textbook entity-leakage trap that no standard ID check catches.

The trap: NHANES publishes a standalone 2017–2018 cycle (suffix J) and a pooled 2017–March 2020 cycle (prefix P_). Because COVID cut 2019–2020 short, NCHS folded all of 2017–2018 into the P_ files, but gave everyone new respondent numbers. De-duplicating by SEQN finds nothing, because the two ID ranges are disjoint.

Evidence the rows are the same people: all 176 cohort women from J have an exact match in P_ on femoral-neck BMD, total-hip BMD, age, weight and height; 7,585 of 7,585 body-measure fingerprints match; and the matched pairs agree 176/176 on seven derived variables.

Why it matters: StratifiedKFold assigns rows to folds. If the same woman appeared twice, one copy could be in training and the other in test, so the model would be tested on someone it has already seen. Tree ensembles in particular memorise such rows.

Design and guard: J is not in CYCLES (CLAUDE.md says it must not be added), and audit_duplicates asserts zero duplicates on a physical fingerprint — five measurements that will not coincide by chance. It runs on the 1,308 DXA cohort.

One legitimate use of 2017–2018: the P_ cycle has no vitamin D lab file, so serum vitamin D for those 2017–18 women is copied from the J lab file by exact fingerprint match ('crosswalk'). 161 matches, 159 with a serum value; coverage 815 → 974. It only fills missing values and only for the serum vitamin D arm, not the headline model.

Alternative we should mention: in a general setting you would use GroupKFold on a person key. Here there is one row per person, so StratifiedKFold is valid.
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
- 56,769 respondents across the five cycles.
- 28,644 female.
- 10,672 non-Hispanic White. The cohort is deliberately narrow: the T-score reference values used are for non-Hispanic White women, and the specialist confirmed these inclusion limits.
- 1,639 aged 50–65 inclusive.
- 1,308 with a valid femoral-neck DXA (value inside 0.2–1.8 g/cm²). The code asserts exactly 1,308 (N_DXA_COHORT).
- 1,111 postmenopausal. The gate uses one question, RHQ031 'Have you had at least one menstrual period in the past 12 months?'. No → kept (1,111). Yes → dropped as still cycling (156; younger, median age 52, much better bone: mean T −0.47). Missing / refused / don't know → dropped as undeterminable (41; their mean T −1.16 is almost identical to the kept group, so excluding them is unlikely to bias anything). We are careful never to call these 41 'premenopausal'.

Engineering point: these asserts pin the cohort counts. If a refactor or data change alters the cohort, the run fails loudly instead of quietly producing a different study.

The narrowing to postmenopausal women was a clinical decision (specialist Q3).
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

The final t_score is the lower of the two sites, which is the clinical convention. It is rounded to three decimals before thresholding, so women sitting exactly on −2.5 are classified consistently.

Specialist interaction: the specialist said the outcome should be the T-score itself (continuous). We kept the binary T ≤ −1.0 as the headline because the clinical decision is binary (refer for DXA or not) and reporting conventions expect a binary primary, and we model the continuous T-score with regressors alongside. That override still needs the specialist's sign-off.

Class balance is unusual: at T ≤ −1.0 the positive class is the majority (58%), so 'class_weight=balanced' actually DOWN-weights positives there and XGBoost's scale_pos_weight is below 1. At T ≤ −2.5 there are only 76 events — events per predictor is 4.75 against a rule-of-thumb floor of 10, so that target is flagged as underpowered before any modelling (power_gate.csv).
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

Q6 PHQ-9. The nine items are stored as words in some cycles and as codes in others; decode() handles both, so the score exists for 1,110 of 1,111.
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

# ================================================================ Specialist traceability
def arm_delta(code):
    r = arms[arms["Arm"].str.startswith(code + ":")]
    if r.empty:
        return "see arms slide"
    r = r.iloc[0]
    return f"{r['Delta AUC']:+.3f} {ci(r['95% CI'])}"


SPEC_HDR = ["#", "Specialist's instruction", "How the model uses it", "Status"]
spec_rows_1 = [
    SPEC_HDR,
    ["1", "Age — continuous", "Main model, continuous (years)", "As specified"],
    ["2", "BMI — continuous; 6 bands for the demographic table", "Main model, continuous; 6 WHO bands in Table 1", "As specified"],
    ["3", "Years since menopause — continuous; exclude anyone with a period in the last 12 months",
     "Main model, continuous; cohort keeps only women with no period in 12 months (1,111)", "As specified"],
    ["4", "Ever used estrogen — yes/no (when was it used?)", "Main model, yes/no; duration < 2 y vs ≥ 2 y built for description", "As specified"],
    ["5", "Rheumatoid arthritis — yes/no", "Arm E: tested on the 988 women whose arthritis type is recorded", "Used (arm)"],
    ["6", "Diabetes — yes/no", "Main model, yes/no (borderline = no); arms G1/G2 check the coding", "As specified"],
    ["7", "Smoking — yes/no", "Main model, yes/no (≥ 100 cigarettes in life)", "As specified"],
]
spec_rows_2 = [
    SPEC_HDR,
    ["8", "Current alcohol — categorical: zero, < 3, ≥ 3 drinks/day", "Main model, 3 categories (< 3/day is the reference)", "As specified"],
    ["9", "Prior fracture — yes/no", "Main model, yes/no (hip, spine or wrist)", "As specified"],
    ["10", "Steroid use — yes/no", "Main model, yes/no", "As specified"],
    ["11", "Activity → MET-min/week (primary); moderate & vigorous min/week, sitting h/day (secondary)",
     f"Arm I: MET-min/week + sitting ({arm_delta('I')}); arm I2: moderate + vigorous min/week + sitting ({arm_delta('I2')})", "Used (arm)*"],
    ["12", "Calcium (diet + supplements) — continuous; 4 bands for the table",
     f"Arm C, continuous ({arm_delta('C')}); 4 bands in Table 1", "Used (arm)*"],
    ["13–14", "Vitamin D: intake in IU/day OR serum level, never both; serum preferred",
     f"Separate arms, never together: C intake, D serum ({arm_delta('D')}); intake shown in IU/day in Table 1", "As specified"],
    ["15", "Poverty income ratio — continuous; bands < 1, 1–< 3, ≥ 3 for the table", "Main model, continuous; 3 bands in Table 1", "As specified"],
]
spec_rows_3 = [
    SPEC_HDR,
    ["16", "Mother hip fracture — yes/no; search for father", "Father found in all cycles; main model uses mother OR father (only 5 women had both)", "As specified"],
    ["17", "PHQ-9 — subset analysis only (≈ 20% data), continuous",
     "Score is 99.9% complete, so it is in the main model, continuous; arm F tests the ≥ 10 cut-off", "Adapted ↑"],
    ["18", "Search for antidepressant data", "Found in the prescription file (RXQ_RX); needs a drug-class mapping — not yet used", "Open"],
    ["19", "Search for falls / fall-risk data", "No falls or balance questions in any cycle used", "Not available"],
    ["20", "Sleep — continuous (primary); 5 bands (secondary)",
     f"Main model, continuous; arm J swaps in the 5 bands, 7–8 h reference ({arm_delta('J')})", "As specified"],
    ["Rule", "Keep variables continuous to preserve power", "All numeric inputs continuous; categories only where specified (alcohol) or for Table 1", "As specified"],
    ["Rule", "Check each variable's distribution first", "Done and sent to you; skewed inputs (activity) modelled on a log scale", "As specified"],
    ["Rule", "For each variable, see how the model behaves without it", "Single-variable ablation: every variable removed in turn and the model refit", "As specified"],
]
for i, rows in enumerate([spec_rows_1, spec_rows_2, spec_rows_3], 1):
    s = new_slide(f"Your variable list, and how each item is used ({i} of 3)",
                  "From the specialist's variable notes — every item mapped to the model", section="Clinical decisions")
    hi = tuple(r for r in range(1, len(rows)) if rows[r][3] in ("Open", "Not available", "Adapted ↑"))
    table2(s, rows, 0.6, 1.45, 12.1, col_w=[0.75, 4.1, 5.65, 1.6], size=12, row_h=0.62 if i < 3 else 0.6, hi_rows=hi)
    if i == 2:
        tb = s.shapes.add_textbox(Inches(0.6), Inches(6.55), Inches(12.1), Inches(0.45))
        tb.text_frame.word_wrap = True
        _run(tb.text_frame.paragraphs[0], "* Arm because 2005–06 did not ask these questions: the arm uses the women who were asked "
             "and compares with the main model refit on the same women, so nothing is made up.", 12, False, INK2)
    notes(s, f"Specialist variable list {i}", {
        1: """
This slide and the next two walk through the specialist's written variable list item by item, so they can see that every input was taken into account.

'Main model' means the variable is in the headline model for all 1,111 women. 'Arm' means it is tested in its own side-experiment, on the women who have it, against the main model refit on those same women.

- Items 1–3: age, BMI and years since menopause are continuous, as asked. The cohort rule in item 3 (no period in the last 12 months) defines the 1,111 women.
- Item 4: estrogen is yes/no. The specialist asked when it was used: duration is recorded for about 71% of users and is built for description; timing is not consistently available.
- Item 5: rheumatoid arthritis can only be defined for women who answered the arthritis-type question, so it is an arm on those 988 women.
- Items 6–7: diabetes and smoking are yes/no as asked. Borderline diabetes counts as no; two arms check that choice.
""",
        2: """
- Item 8: alcohol is used exactly as specified — three categories (none, under 3, 3 or more drinks a day), with 'under 3' as the reference group because it is the largest. Note the NHANES question is drinks per drinking day.
- Items 9–10: prior fracture and steroid use are yes/no.
- Item 11: physical activity is calculated as MET-min/week from the specialist's references (8 METs for vigorous, 4 for moderate and walking/cycling). The secondary measures — moderate and vigorous minutes per week, and sitting time — are also built. Because the 2005–06 survey did not ask these questions, activity is tested in two arms (I: MET + sitting; I2: moderate + vigorous + sitting) on the women from 2007 onward. This avoids inventing values for 173 women.
- Item 12: calcium (diet plus supplements) is continuous, in arm C, because supplements were not recorded in 2005–06. The four bands appear in Table 1.
- Items 13–14: vitamin D intake and serum level are never put in the same model, as instructed. Each has its own arm. Intake is shown in IU/day in Table 1 (the model's unit does not matter, because inputs are rescaled).
- Item 15: income ratio is continuous in the model; the three bands are in Table 1.
""",
        3: """
- Item 16: father's hip fracture was found in every cycle. Because only 5 women had both parents with a hip fracture, the model uses 'mother or father'.
- Item 17: the specialist expected PHQ-9 to be available for only about 20% of women. It turned out to be 99.9% complete, so it is in the main model as a continuous score; arm F tests the ≥ 10 cut-off.
- Item 18: antidepressant use is in the NHANES prescription file but needs each drug name mapped to a drug class. Not yet used — an open item to agree with the specialist.
- Item 19: there are no falls or balance questions in the cycles used, so this is a stated limitation.
- Item 20: sleep is continuous in the main model, and arm J swaps in the specialist's five bands (≤ 5, 6, 7–8 reference, 9, ≥ 10 hours).

General rules: inputs are kept continuous; distributions were checked and sent to the specialist; and 'how does the model behave without each variable' is answered by the single-variable ablation, which refits the model with each variable removed in turn.

Also from the later question rounds (slides 9–10): the 5-year prior-fracture window (R1) is not built yet.
""",
    }[i])

s = new_slide("With every input in place, the model still sits at AUC ≈ 0.75",
              "Main model built to the specialist's specification; arms add each remaining item", section="Clinical decisions")
fin = [["Target", "Model (nested AUC)", "OST formula", "Model − OST [95% CI]", "Verdict"]]
for lab, o in [("Low bone mass (T ≤ −1.0)", op_ost), ("Osteoporosis (T ≤ −2.5)", os_ost)]:
    fin.append([lab, f3(o["Nested AUC"]), f3(o["Comparator AUC"]),
                f"{o['Delta vs comparator']:+.3f} {ci(o['95% CI'])}", o["Verdict"]])
table2(s, fin, 0.6, 1.5, 12.1, col_w=[3.0, 2.0, 1.7, 3.2, 2.2], size=14, row_h=0.6)
bullets(s, [
    (0, "Every item on the list is used —", "in the main model, or in its own arm where the data only exist for some women."),
    (0, "No arm adds measurable signal:", "activity, calcium, vitamin D, rheumatoid arthritis, sleep bands, depression cut-off."),
    (0, "What drives the model is body weight,", "which OST already uses — so the model cannot pull away from OST."),
    (0, "To move beyond 0.75 needs a different kind of information,", "e.g. blood tests (alkaline phosphatase), weight history, imaging."),
], x=0.6, y=3.6, w=12.1, h=3.2, size=17)
notes(s, "All inputs in place", f"""
The point of this slide for the specialist: the model was built to their specification, and the ceiling is not because something they asked for was left out.

Every item on their list is either in the main model or tested in its own arm. The main model includes alcohol in their three categories, sleep and income as continuous values, and the cohort rule they set. The arms cover activity (MET-min/week and the secondary measures), calcium, vitamin D (intake and serum kept apart), rheumatoid arthritis, sleep in their five bands, and the depression cut-off. None of the arms improves the model.

Headline: low bone mass {f3(op_ost['Nested AUC'])} vs OST {f3(op_ost['Comparator AUC'])}, difference {op_ost['Delta vs comparator']:+.3f} {ci(op_ost['95% CI'])}; osteoporosis {f3(os_ost['Nested AUC'])} vs {f3(os_ost['Comparator AUC'])}, difference {os_ost['Delta vs comparator']:+.3f} {ci(os_ost['95% CI'])}.

Why it stays near 0.75: removing weight and BMI drops the AUC to about 0.6; removing anything else changes almost nothing. OST already uses weight and age. The questionnaire items describe lifestyle and history, which explain only a small part of why bone density differs between women.

What could move it: information of a different kind — blood tests such as alkaline phosphatase, weight history (weight lost since peak), medications (including the antidepressant item still open), or imaging. Good discussion point with the specialist.
""")

# ================================================================ 11 Features
s = new_slide("The model feature panel: 15 variables, 16 columns", "Allowlist (FEATURE_GROUPS, block E): nothing enters a model unless it is named here", section="Features")
fv = [
    ["Variable", "NHANES source", "Type", "n observed", "Missing"],
    ["age", "RIDAGEYR", "cont.", "1,111", "0%"],
    ["weight_kg", "BMXWT", "cont.", "1,111", "0%"],
    ["bmi", "BMXBMI", "cont.", "1,110", "0.1%"],
    ["years_since_menopause", "age − RHQ060", "cont.", "1,089", "2.0%"],
    ["ever_used_estrogen", "RHQ540", "bin.", "1,109", "0.2%"],
    ["diabetes", "DIQ010 (borderline→0)", "bin.", "1,111", "0%"],
    ["ever_smoked", "SMQ020", "bin.", "1,111", "0%"],
    ["alcohol (zero / <3 / 3+ per day)", "ALQ130 (+0 non-drinkers)", "cat.", "960", "13.6%"],
    ["any_prior_fracture", "OSQ010A/B/C", "bin.", "1,111", "0%"],
    ["steroid_use", "OSQ130", "bin.", "1,106", "0.5%"],
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
    (1, "physical activity: MET-min/week + sitting (arm I); moderate + vigorous min/week + sitting (arm I2) — 2007 onward"),
    (1, "sleep in five bands (arm J, replaces hours)"),
    (0, "Denylist", "(asserted): BMD, site T-scores, t_score, labels, bone_status."),
    (0, "Benched:", "height (enters via BMI), age at menopause (= age − years since), education, supplement-availability flag, vigorous-activity yes/no (MET-min/week is used instead, in arm I)."),
], x=9.05, y=1.45, w=3.9, h=5.5, size=13)
notes(s, "Feature panel", """
This is the complete headline feature set: 15 variables, 16 model columns — alcohol enters as the specialist's three categories (two indicator columns, '< 3 per day' as reference). There is no menopause-type variable — per the specialist, menopause is defined only by the 12-month gate.

The n observed column answers 'how many of the cohort have each variable' — out of 1,111. Most variables are near-complete. Only alcohol (960) is notably incomplete. Physical activity is not in the headline panel: the 2005–06 cycle used a different activity questionnaire, so activity is missing for that entire cycle (173 women). Rather than impute a whole cycle, activity has its own arm (I) on the 2007+ women.

Derivation details worth mentioning to an engineer:
- years_since_menopause = age − age at last period (RHQ060), kept only if ≥ 0.
- alcohol: ALQ130 is drinks per drinking day. Blank for a confirmed non-current drinker (ALQ101/ALQ111 = No) is set to 0 — a true zero, not missing. Current vs lifetime drinking are separate questions; conflating them mislabels 62 women.
- phq9_score: sum of nine items mapped to 0–3; requires at least 5 answered items, otherwise NaN.
- sleep_hrs: SLD012 (newer cycles) coalesced with SLD010H (older cycles).
- any_prior_fracture: yes if any of hip / spine / wrist fracture questions is yes; no only if all three are answered no.
- parental_hip_fracture: mother (OSQ170) or father (OSQ200).
- met_min_week (arm I only): the specialist's references (PMC9858810, PMC12851727; WHO GPAQ): 8 METs × days × minutes for vigorous work and vigorous recreation, 4 METs for moderate work, moderate recreation and walking/cycling, summed. A domain answered 'No' counts as 0. Minutes valid 10–960/day, days 1–7. Modelled as log(1 + MET-min/week) because it is heavily skewed (median 720, max 43,680 = 728 MET-h/week).

Why an allowlist: if a pipeline admits every column not explicitly excluded, every new derived column is a potential target leak unless someone remembers to exclude it. Here adding a variable means adding it to FEATURE_GROUPS on purpose. The BMD denylist is asserted on top as a second gate.

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
    (0, "Complete-case:", "only in the arms (vit D, RA, physical activity)."),
    (0, "OST / weight baselines:", "median fill (0 rows affected)."),
], x=7.9, y=1.35, w=5.1, h=5.6, size=13)
notes(s, "Missing data and imputation", """
Directly answering 'was any mean/median/imputation done?':

1. Yes — median imputation, and only inside the cross-validation folds. Every model is a scikit-learn Pipeline: SimpleImputer(strategy='median') → StandardScaler → estimator. Because the pipeline is fitted on the training fold, the median is learned from training rows only and applied to the test fold; there is no leakage of test-fold statistics. This also applies to tree models (they are wrapped in the same pipeline). For binary columns the median is effectively the mode.

2. No mean imputation anywhere. The only 'mean' is averaging the two 24-hour dietary recall days for calcium and vitamin D intake (and if only one day exists, that day is used).

3. Logical zero-fills that are not imputation but correct coding: alcohol drinks/day = 0 for women who said they did not drink in the past 12 months (ALQ130 is skipped for them); supplement calcium/vitamin D = 0 for women who are in a supplement file but report no supplement (NHANES codes non-users as blank).

4. Complete-case analysis is used only in the arms: vitamin D intake (930), serum vitamin D (974), RA (988), physical activity (932).

Structural missingness is not imputed: the activity variables are missing for the whole 2005–06 cycle because that survey used a different questionnaire. Median-filling them would code all 173 of those women as 'no vigorous activity'. So activity is kept out of the headline model and tested only in arm I (log MET-min/week + sedentary minutes) on the 932 women from 2007 onward, with nothing imputed.

Also no multiple imputation (MICE); with < 6% missing on most variables single imputation is defensible, but alcohol (13.6%) is where MI would matter most.
""")

# ================================================================ 13 Leakage
s = new_slide("Guard-rails against leakage and silent drift", section="Modelling")
table(s, [
    ["Risk", "Guard in code"],
    ["Same person in train and test", "standalone 2017_2018 not loaded; audit_duplicates asserts 0 on a 5-field physical fingerprint"],
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
An ML engineer will care most about this slide. The pipeline is written defensively.

Highlights:
- The allowlist means no column can enter a model by accident.
- The leak alarm: with standardised features, a coefficient above 2.0 in absolute value would be extraordinary for survey variables; it would suggest a BMD-derived column slipped in. The largest is weight_kg at −1.18. The only sign flag is BMI (positive), which is explained: BMI and weight correlate at 0.94, so weight absorbs the effect and BMI's residual sign is meaningless.
- OOB AUC subtlety: scikit-learn ≥ 1.9 makes the bootstrap sample_weight-aware, and class_weight='balanced' is applied as a sample weight, so at T ≤ −2.5 the minority class is oversampled into nearly every tree and only 28% of cases are ever out-of-bag. sklearn returns uncovered rows as all-zero decision rows (not NaN), so a naive isnan guard would score them as lowest-risk and report an inverted OOB AUC. _oob_auc drops uncovered rows and refuses to report when coverage of either class is < 80%.
- Tree importances (Gini, split counts) are not reported because they are biased toward continuous features; permutation importance and refit ablation are used instead.

Note: global warnings are suppressed (warnings.filterwarnings('ignore')), which would also hide convergence warnings — a small item for the backlog.
""")

# ================================================================ 4 AUC
s = new_slide("How we score a model: AUC", "One number for 'how well does the score sort women by risk?'",
              section="Modelling")
box(s, "Pick one woman WITH low bone density and one WITHOUT, at random.\n"
       "AUC = how often the model gives the first woman the higher risk score.",
    0.6, 1.6, 12.1, 1.1, PALEBLUE, INK, 18, True, PP_ALIGN.CENTER)
table2(s, [["AUC", "What it means"],
          ["0.50", "coin flip — the score is useless"],
          ["0.70 – 0.80", "useful but imperfect — typical for screening questionnaires"],
          ["0.80 – 0.90", "good"],
          ["1.00", "perfect — always ranks the right woman higher"]],
      0.6, 3.0, 7.0, col_w=[1.6, 5.4], size=14, row_h=0.5, hi_rows=(2,))
bullets(s, [
    "AUC only cares about ORDER, not the exact number. That is why a risk probability, a predicted T-score and the OST formula can all be compared on the same scale.",
    "A difference of 0.01 in AUC means the model sorts 1 more pair in 100 correctly.",
], x=7.9, y=3.0, w=4.9, h=3.8, size=15)
notes(s, "AUC", """
AUC stands for 'area under the ROC curve', but the plain-English meaning is more useful: take every possible pair of one woman who has low bone density and one who does not. AUC is the fraction of those pairs where the model gives the higher risk score to the woman who actually has low bone density.

0.5 is a coin flip. 1.0 is perfect. Screening questionnaires in osteoporosis usually land between 0.70 and 0.80 — that is where OST and our models are.

Because AUC only looks at order, we can compare very different kinds of score fairly: a probability from a classifier, a predicted T-score from a regressor, or the OST formula itself.

Scale of differences: +0.01 AUC means one more correctly ordered pair per hundred. That is small; it matters only if we are confident it is real, which is what the later slides test.
""")

# ================================================================ 5 Eight models
s = new_slide("The 8 models, in two families",
              "Same 15 inputs for all eight; they differ only in HOW they turn inputs into a score", section="Modelling")
box(s, "FAMILY 1 — five 'yes / no' models\nlearn the label directly: low bone density, yes or no",
    0.6, 1.55, 6.0, 0.95, NAVY, WHITE, 14, True)
table2(s, [["Model", "In plain English"],
          ["Logistic regression", "Adds up the inputs, each with a weight. The classic medical-statistics model."],
          ["Elastic net", "Logistic regression that may shrink weak inputs to zero."],
          ["Random forest", "500 decision trees, each on a resampled set of women; they vote."],
          ["LightGBM", "Small trees built one after another, each fixing the last one's mistakes."],
          ["XGBoost", "Same idea as LightGBM, a different implementation."]],
      0.6, 2.6, 6.0, col_w=[1.8, 4.2], size=12, row_h=0.62)
box(s, "FAMILY 2 — three 'predict the T-score' models\npredict the actual bone-density number, then compare it to the cutoff",
    6.85, 1.55, 5.9, 0.95, ORANGE, WHITE, 14, True)
table2(s, [["Model", "In plain English"],
          ["Ridge → T-score", "A straight-line formula for the T-score, kept modest so it does not over-fit."],
          ["Random forest → T-score", "500 trees that each guess the T-score; the guesses are averaged."],
          ["LightGBM → T-score", "Small trees in sequence, predicting the T-score."]],
      6.85, 2.6, 5.9, col_w=[2.0, 3.9], size=12, row_h=0.62)
box(s, "Why family 2? A woman at T = −0.9 and one at T = +1.5 are both 'no' to a yes/no model, "
       "but the T-score model sees that the first is close to the line. One T-score model also serves BOTH cutoffs.",
    6.85, 5.25, 5.9, 1.4, LIGHT, INK, 13)
notes(s, "Eight models", """
All eight models get exactly the same 15 inputs and the same women. The only difference is the method.

Family 1, five classifiers, learn the yes/no label directly.
- Logistic regression: each input gets a weight, the weighted inputs are added up, and the total is turned into a probability. It is the standard model in medical research and the easiest to explain.
- Elastic net: logistic regression with a built-in penalty that can push a weak input's weight all the way to zero, so it does its own variable selection.
- Random forest: 500 decision trees. Each tree is a flowchart of yes/no questions ('weight under 65 kg? age over 60?'), grown on a different random resample of the women. The forest averages their votes. It can capture interactions a straight-line model cannot.
- LightGBM and XGBoost: 'gradient boosting'. Very small trees are built one at a time, each one trying to correct the errors of the ones before. We kept them deliberately small and heavily restrained (depth 2, strong penalty), because with about 1,100 women they otherwise memorise the data.

Family 2, three regressors, predict the T-score itself as a number, then we use the predicted number as the risk score (lower predicted T = higher risk).
- Why bother: turning bone density into yes/no throws information away. A woman just above the line and a woman far above it look identical to a yes/no model. Predicting the number keeps that detail, and one model answers both questions (T ≤ −1.0 and T ≤ −2.5) at once.
- Ridge is a straight-line formula with a penalty; the random forest and LightGBM versions are the tree methods applied to the number.

Why eight at all: different methods suit different data. Trying a range — simple to flexible — tells us whether the limit is the method or the information in the inputs. (Spoiler: it is the information.)

Shared settings: missing values are filled with the median and inputs are put on a common scale; the yes/no models give extra weight to the less common class so they do not ignore it.
""")

# ================================================================ 6 Cross-validation
s = new_slide("Testing fairly, step 1: 5-fold cross-validation",
              "A model is only ever scored on women it has never seen", section="Modelling")
labels = ["Round 1", "Round 2", "Round 3", "Round 4", "Round 5"]
for r in range(5):
    y0 = 1.75 + r * 0.72
    tb = s.shapes.add_textbox(Inches(0.6), Inches(y0), Inches(1.2), Inches(0.55))
    _run(tb.text_frame.paragraphs[0], labels[r], 14, True, INK2)
    for c in range(5):
        test = (c == r)
        box(s, "TEST" if test else "train", 1.85 + c * 1.12, y0, 1.05, 0.55,
            ORANGE if test else PALEBLUE, WHITE if test else INK, 12, test, PP_ALIGN.CENTER,
            MSO_SHAPE.RECTANGLE)
tb = s.shapes.add_textbox(Inches(1.85), Inches(5.4), Inches(5.6), Inches(0.5))
_run(tb.text_frame.paragraphs[0], "each block = one-fifth of the 1,111 women (≈ 222)", 12, False, INK2)
bullets(s, [
    "Split the women into 5 equal groups, keeping the share of cases the same in each.",
    "Train on 4 groups, score the 5th. Repeat until every group has been the test group once.",
    "Result: every woman gets ONE score from a model that never saw her.",
    "AUC is computed on those 'unseen' scores.",
    (0, "Inside each round:", "filling in missing values and scaling are learned from the training groups only — the test group never leaks in."),
], x=7.7, y=1.6, w=5.2, h=5.2, size=15)
notes(s, "Cross-validation", """
The single most important rule in evaluating a prediction model: never score it on the data it learned from. A model can memorise the women it trained on and look perfect, then fail on new women.

5-fold cross-validation solves this without needing a separate dataset:
1. Split the 1,111 women into five groups of about 222. 'Stratified' means each group has the same share of low-bone-density cases as the whole.
2. Train the model on four groups, then score the fifth group, which it has never seen.
3. Rotate so each group takes a turn as the test group.
Every woman ends up with exactly one 'out-of-fold' score, produced by a model that did not see her. AUC is calculated on those scores.

A subtle but important detail: steps like filling in missing values (with the median) and putting inputs on a common scale are part of the model. They are learned from the four training groups only and then applied to the test group. If we computed the median using all 1,111 women first, a little information about the test women would leak into training.

Everything uses the same random seed (42), so the splits — and every number in this deck — are reproducible.
""")

# ================================================================ 7 Nested CV
s = new_slide("Testing fairly, step 2: nested cross-validation",
              "The honest score for 'try 8 models and keep the best'", section="Modelling")
box(s, "THE TRAP\nIf we try 8 models and report the best score, part of that 'best' is luck — "
       "we picked whichever model happened to suit these particular women.",
    0.6, 1.6, 5.6, 1.6, LIGHT, INK, 15)
box(s, "THE FIX\nMake 'pick the best model' part of the training, and score the pick on women "
       "that were not used for picking.", 0.6, 3.4, 5.6, 1.4, PALEBLUE, INK, 15)
# diagram
box(s, "Outer round (×5): hold out one-fifth of the women", 6.6, 1.6, 6.15, 0.6, NAVY, WHITE, 14, True)
box(s, "Inner contest on the other four-fifths:\nall 8 models compete in a 3-fold cross-validation\n→ the winner is chosen",
    6.9, 2.35, 5.85, 1.25, ORANGE, WHITE, 14, False)
box(s, "Winner is refit and scores the held-out fifth\n(women it has never seen, and who played no part in choosing it)",
    6.9, 3.75, 5.85, 1.05, PALEBLUE, INK, 14)
box(s, "Combine the 5 held-out fifths → NESTED AUC", 6.6, 4.95, 6.15, 0.6, NAVY, WHITE, 14, True)
bullets(s, [
    (0, "Leaderboard AUC:", "best of the 8 on ordinary cross-validation — slightly optimistic."),
    (0, "Nested AUC:", "the number we report as the result."),
    (0, "Optimism:", "leaderboard minus nested — how much the pick flattered itself."),
], x=0.6, y=5.05, w=5.8, h=1.9, size=14)
notes(s, "Nested cross-validation", """
Cross-validation gives each model an honest score. But we have eight models, and we want to report 'the best one'. Choosing the best and then quoting its score is a little dishonest: some of its lead is luck — it happened to fit these particular women well.

Nested cross-validation moves the choosing inside the training:
- Outer loop: split the women into five fifths. Hold one fifth out completely.
- Inner loop: using only the other four-fifths, run all eight models through their own 3-fold cross-validation and pick the winner.
- Refit the winner on those four-fifths and score the held-out fifth — women who neither trained the model nor helped choose it.
- Repeat for all five fifths and combine the scores into one AUC.

So the nested AUC is not the score of one particular model. It is the honest score of the whole recipe: 'try eight models, keep the best'. That is exactly what we would do in practice, so it is the right number to report.

Different outer rounds can pick different winners; the run log lists which model won each round. The winners vary between the forest, logistic-style and T-score models, which itself says the models are close to interchangeable.

'Optimism' is the leaderboard best minus the nested AUC. Small optimism means picking the winner did not inflate the result much.
""")

# ================================================================ 8 Comparing to OST
s = new_slide("Testing fairly, step 3: is the model really better than OST?",
              "A difference only counts if it survives the play of chance", section="Modelling")
bullets(s, [
    (0, "Same women, same comparison.", "The model's nested scores and OST are compared on the identical 1,111 women ('paired')."),
    (0, "Bootstrap:", "re-draw the 1,111 women at random with replacement, 1,000 times, and recompute model AUC − OST AUC each time."),
    (0, "95% confidence interval:", "the middle 95% of those 1,000 differences — the range the true difference plausibly lies in."),
    (0, "The rule:", "if the whole interval is above zero → 'beats OST'. If it includes zero → 'not separable'."),
], x=0.6, y=1.6, w=7.2, h=4.4, size=16)
# number line illustration
box(s, "Reading an interval", 8.2, 1.6, 4.6, 0.55, NAVY, WHITE, 14, True)
line = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(8.4), Inches(3.35), Inches(4.2), Inches(0.04))
line.fill.solid(); line.fill.fore_color.rgb = INK2; line.line.fill.background()
zero = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(9.6), Inches(2.4), Inches(0.03), Inches(2.6))
zero.fill.solid(); zero.fill.fore_color.rgb = INK; zero.line.fill.background()
tb = s.shapes.add_textbox(Inches(9.35), Inches(5.0), Inches(0.6), Inches(0.4))
_run(tb.text_frame.paragraphs[0], "0", 13, True, INK)
box(s, "", 10.0, 2.55, 2.3, 0.3, GREEN, WHITE, 10, shape=MSO_SHAPE.RECTANGLE)
tb = s.shapes.add_textbox(Inches(10.0), Inches(2.85), Inches(2.8), Inches(0.4))
_run(tb.text_frame.paragraphs[0], "all above 0 → beats OST", 12, True, GREEN)
box(s, "", 9.1, 3.75, 2.2, 0.3, ORANGE, WHITE, 10, shape=MSO_SHAPE.RECTANGLE)
tb = s.shapes.add_textbox(Inches(9.1), Inches(4.05), Inches(3.4), Inches(0.4))
_run(tb.text_frame.paragraphs[0], "crosses 0 → not separable", 12, True, ORANGE)
box(s, "'Not separable' does not mean 'equal'. It means we cannot tell them apart with this many women.",
    0.6, 6.1, 12.1, 0.65, LIGHT, INK, 15, True)
notes(s, "Bootstrap comparison", """
Suppose the model's AUC is 0.01 higher than OST's. Is that a real advantage, or just luck in which 1,111 women happened to be surveyed? The bootstrap answers that.

How it works:
- Draw 1,111 women at random from our 1,111, with replacement (some women appear twice, some not at all). Keep the number of cases and non-cases fixed.
- On that resampled group, compute the model's AUC and OST's AUC, and take the difference.
- Do this 1,000 times. We now have 1,000 plausible values of the difference.
- The 95% confidence interval is the range covering the middle 950 of them.

It is 'paired' because the model and OST are always scored on the same resampled women, so the comparison is like-for-like.

The decision rule: if the entire interval sits above zero, the model beats OST. If the interval includes zero, the difference could plausibly be nothing, and we call it 'not separable'.

Be careful with wording. 'Not separable' is not proof that the two are equal; it means this study is not big enough to tell them apart. A one-sided p-value is also reported (the share of bootstrap differences at or below zero), but the verdict is based on the interval.
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

The script writes data/processed/analysis_cohort_postmenopausal.csv (1,111 rows × 131 columns) — the analysis input — and everything else goes to outputs/ through save_csv, which stamps a tier: PRESENT (for clinicians), METHODS (defends choices), DIAGNOSTIC (leak/sign detectors, not findings).

Dependencies: pandas, numpy, matplotlib, scikit-learn, lightgbm, xgboost, requests — installed in the system Python, no requirements file. stdout is reconfigured to UTF-8 before imports because the progress output uses emoji and the Windows cp1252 console would raise.

What an engineer will notice is missing, and where they could help: no unit tests (the asserts act as integration tests), no dependency lockfile, no CI, no experiment tracking, no data versioning beyond git. There are also ~20 scratch scripts (_build_*.py, _edit_wt*.py, _stage.py) in the repo root that should be cleaned up.
""")

# ================================================================ 9 Leaderboard
s = new_slide("Results 1: all 8 models land in the same place",
              "Ordinary 5-fold cross-validation AUC for the five yes/no models", section="Results")


def lb_rows(lb):
    out = []
    for _, r in lb.iterrows():
        out.append([r["Model"].replace(" (Aggressive Reg)", "").replace("Elastic Net Logistic Regression", "Elastic net")
                    .replace("Logistic Regression (L2)", "Logistic regression"), f3(r["auc"])])
    return out


rows = [["Model", "Low bone mass\n(T ≤ −1.0)", "Osteoporosis\n(T ≤ −2.5)"]]
for a, b in zip(lb_rows(lb1), lb_rows(lb2)):
    rows.append([a[0], a[1], b[1]])
rows.append(["OST formula (for reference)", f3(op_ost["Comparator AUC"]), f3(os_ost["Comparator AUC"])])
table2(s, rows, 0.6, 1.6, 7.0, col_w=[3.4, 1.8, 1.8], size=14, row_h=0.6, hi_rows=(len(rows) - 1,))
spread1 = lb1["auc"].max() - lb1["auc"].min()
bullets(s, [
    f"For low bone mass, all five sit within {spread1:.3f} of each other.",
    "Simple logistic regression does as well as the complex tree models.",
    "When very different methods agree, the limit is the information in the inputs, not the method.",
    "The three T-score models are judged inside the nested test (next slide), where they often win a round.",
], x=7.9, y=1.6, w=4.9, h=5.0, size=15)
notes(s, "Leaderboard", f"""
This table is the 'leaderboard': each yes/no model's AUC from ordinary 5-fold cross-validation.

For low bone mass (T ≤ −1.0), the five models range from {lb1['auc'].min():.3f} to {lb1['auc'].max():.3f}. Logistic regression, the simplest, is at the top with elastic net; the boosted-tree models are slightly lower. For osteoporosis the spread is wider ({lb2['auc'].min():.3f} to {lb2['auc'].max():.3f}), but with only {E2} cases those numbers bounce around a lot.

The important reading: methods that work in completely different ways all hit the same ceiling, and that ceiling is barely above OST. That tells us more modelling cleverness is unlikely to help — the inputs simply do not contain much more information about bone density than weight and age already do.

The three T-score models are not in this table because this leaderboard is for yes/no models; they compete in the nested cross-validation, where they won several rounds.

Reminder: the leaderboard best is slightly optimistic (we picked it after seeing the scores). The result we report is the nested AUC on the next slide.
""")

# ================================================================ 10 Headline
s = new_slide("Results 2: the headline — model vs OST",
              "Nested AUC (the honest score) against the two simple rules", section="Results")
vt = [["Target", "Model\n(nested)", "OST", "Model − OST\n[95% CI]", "Verdict"]]
for lab, o in [("Low bone mass (T ≤ −1.0)", op_ost), ("Osteoporosis (T ≤ −2.5)", os_ost)]:
    vt.append([lab, f3(o["Nested AUC"]), f3(o["Comparator AUC"]),
               f"{o['Delta vs comparator']:+.3f}\n{ci(o['95% CI'])}", o["Verdict"].replace("Beats comparator", "Beats OST")])
table2(s, vt, 0.6, 1.6, 7.6, col_w=[2.5, 1.1, 0.9, 1.7, 1.4], size=13, row_h=0.8)
wt = [["Target", "Weight alone", "Model − weight [95% CI]", "Verdict"]]
for lab, o in [("Low bone mass", op_w), ("Osteoporosis", os_w)]:
    wt.append([lab, f3(o["Comparator AUC"]), f"{o['Delta vs comparator']:+.3f} {ci(o['95% CI'])}",
               o["Verdict"].replace("Beats comparator", "Beats weight*")])
table2(s, wt, 0.6, 4.3, 7.6, col_w=[2.0, 1.3, 2.8, 1.5], size=12, row_h=0.5)
tb = s.shapes.add_textbox(Inches(0.6), Inches(5.85), Inches(7.6), Inches(0.9))
tf = tb.text_frame; tf.word_wrap = True
_run(tf.paragraphs[0], (f"* Osteoporosis has only {E2} cases; the interval only just clears zero, so treat this as fragile."
                        if os_w["Verdict"].startswith("Beats") else
                        f"Osteoporosis has only {E2} cases, so its intervals are wide."), 12, False, INK2)
box(s, "IN PLAIN ENGLISH\n\nThe model is about 0.01 AUC ahead of OST on both targets, "
       "but the uncertainty is larger than the gap.\n\nWe cannot say the model is better than "
       "a formula that uses only weight and age.", 8.5, 1.6, 4.25, 4.2, NAVY, WHITE, 16)
notes(s, "Headline result", f"""
This is the main result.

Low bone mass (T ≤ −1.0, {E1} cases): nested AUC {f3(op_ost['Nested AUC'])} versus OST {f3(op_ost['Comparator AUC'])}. The model is {op_ost['Delta vs comparator']:+.3f} ahead, but the 95% interval is {ci(op_ost['95% CI'])} — it includes zero. Verdict: not separable from OST.

Osteoporosis (T ≤ −2.5, {E2} cases): nested AUC {f3(os_ost['Nested AUC'])} versus OST {f3(os_ost['Comparator AUC'])}, difference {os_ost['Delta vs comparator']:+.3f}, interval {ci(os_ost['95% CI'])}. Also not separable.

Against weight alone: for low bone mass the model is also not separable from weight alone ({op_w['Delta vs comparator']:+.3f}, {ci(op_w['95% CI'])}). For osteoporosis the difference against weight alone is {os_w['Delta vs comparator']:+.3f}, interval {ci(os_w['95% CI'])} — {'it only just clears zero; do not over-read that with ' + str(E2) + ' cases' if os_w['Verdict'].startswith('Beats') else 'also not separable'}. The comparison that matters clinically is OST.

How to say it: 'With careful methods, machine learning on 15 routinely available inputs matches, but does not exceed, the two-input OST formula.' That is a legitimate finding, consistent with the published literature (simple tools like OST usually perform as well as complex ones).
""")

# ================================================================ 20 Ablation
s = new_slide("Results 3: what the model actually uses — body size", "Refit ablation, primary model Ridge → T-score, T ≤ −1.0, paired bootstrap 500", section="Results")
picture(s, os.path.join(CH, "block_ablation.png"), 0.45, 1.35, w=8.6)
bullets(s, [
    (0, "Drop weight + BMI → 0.603", "(Δ +0.151 [+0.115, +0.187])."),
    (0, "Drop any other block entirely → no measurable change", "(≤ 0.006, CIs cross 0)."),
    (0, "Age + weight alone = 0.739", "= OST's AUC. The other 14 columns add +0.016 [−0.000, +0.031] — not measurable."),
    (0, "Single-variable ablation:", "only weight_kg survives Holm (+0.018 [+0.007, +0.030])."),
    (0, "Permutation importance:", "weight +0.240 (LR) / +0.152 (RF); next best 0.024."),
    (0, "BMI paradox:", "≈0 in single ablation but 2nd in RF permutation — weight substitutes for it (r = 0.94). Quote the block result."),
], x=9.2, y=1.4, w=3.85, h=5.6, size=12.5)
notes(s, "Body size dominates", """
From model_block_ablation_osteopenia.csv. Each row refits all models without the listed variables (or with only them), on the same folds.

- Drop body size (BMI + weight): AUC 0.755 → 0.603. Δ +0.151 [+0.115, +0.187]. This block is nearly the whole model.
- Drop all menopause/hormone variables (years since menopause, estrogen): 0.749, Δ +0.006 [−0.000, +0.013].
- Drop all lifestyle variables (smoking, alcohol categories): 0.756, Δ −0.001.
- Drop all history/family variables (prior fracture, steroids, parental hip fracture, family history): 0.751, Δ +0.004.
- Keep only age + weight (OST's inputs): 0.739 — reproduces OST to three decimals. The full panel's +0.016 over it has a CI of [−0.000, +0.031], so the other 14 columns do not measurably add to OST's two inputs.
- Keep only age + BMI: 0.718.

Why single-variable ablation and permutation importance disagree on BMI: BMI and weight are 0.94 correlated. Remove BMI alone and weight covers it (Δ ≈ 0). Shuffle BMI inside a forest that also has weight and the forest loses a little (permutation rank 2 for RF). Only removing both shows the block's real value. Tell clinicians the block number.

Interpretation for the engineer: the signal is low-dimensional and largely captured by body mass. That is physiologically sensible — mechanical loading and adipose-derived estrogen both raise bone density. To improve, we need a genuinely new kind of information, not more questionnaire items of the same type.
""")

# ================================================================ 21 ORs
s = new_slide("Results 4: per-predictor effects (adjusted odds ratios)", "L2 logistic regression, all 16 columns together, bootstrap 500 refits; solid = 95% CI excludes 1", section="Results")
picture(s, os.path.join(OUT, "forest_plot_odds_ratios.png"), 0.4, 1.3, h=5.65)
table(s, [
    ["Predictor (unit)", "OR (95% CI)", "Dir."],
    ["weight (per 10 kg)", "0.51 (0.39–0.65)", "protective"],
    ["ever used estrogen", "0.59 (0.43–0.76)", "protective"],
    ["poverty-income ratio (per 1)", "0.90 (0.82–0.98)", "protective"],
    ["age (per 5 y)", "1.27 (1.07–1.52)", "risk"],
    ["any prior fracture", "1.76 (1.20–2.74)", "risk"],
    ["steroid use", "1.49 (0.98–2.39)", "ns"],
    ["alcohol 3+/day vs <3", "0.71 (0.43–1.07)", "ns"],
], 6.75, 1.45, 6.2, col_w=[2.8, 1.9, 1.5], size=12, row_h=0.42)
callout(s, "Caveats: ORs come from a penalised (C = 1), class-weighted sklearn model, so they are shrunk and not classical inference.\nActivity is not in this table: it is tested only in arm I (2005–06 not asked).",
        6.75, 5.0, 6.2, 1.6, size=12)
notes(s, "Odds ratios", """
Five of the 16 columns have a confidence interval excluding 1:
- Protective: weight 0.51 per 10 kg (the dominant effect), ever used estrogen 0.59, poverty-income ratio 0.90 per unit (higher income, better bone).
- Risk: age 1.27 per 5 years, any prior fracture 1.76.
- Steroid use 1.49 (0.98–2.39) is not significant. Alcohol, in the specialist's categories: none vs < 3/day 0.90 (0.59–1.31), 3+ vs < 3/day 0.71 (0.43–1.07) — neither significant.

Everything else (BMI, years since menopause, family history, parental hip fracture, smoking, alcohol, PHQ-9, sleep, diabetes) has a CI spanning 1. Activity is arm-only, so it is not in this table.

Method caveats a statistician will ask about: these are not statsmodels maximum-likelihood ORs. They come from scikit-learn's L2-penalised logistic regression with balanced class weights, coefficients back-transformed from standardised units to clinical units, with a 500-replicate stratified bootstrap that refits imputation and model each time. Penalisation shrinks ORs toward 1, and class weighting changes the intercept. Directions and relative sizes are reliable; exact values are not textbook ORs. A useful follow-up: refit with an unpenalised GLM (and possibly survey design) for the clinical table.

Associations are not causal and the study is cross-sectional (e.g., estrogen users may differ systematically).
""")

# ================================================================ 22 Arms
s = new_slide("Results 5: arms and power — no arm adds signal", section="Results")
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
    ["C0 base (16 cols)", "4.8", "29.1"],
    ["C1 + vit D intake", "3.7", "21.2"],
    ["C2 + serum 25(OH)D", "4.0", "24.0"],
    ["C3 + both vit D", "3.1", "17.1"],
    ["C4 + RA", "4.2", "23.8"],
    ["C5 + activity", "3.7", "21.2"],
], 9.25, 1.4, 3.7, col_w=[1.7, 1.0, 1.0], size=11, row_h=0.4)
callout(s, "Events per predictor floor = 10.\nEvery T ≤ −2.5 cohort is under-powered → reported as ‘underpowered’, not as a negative finding.",
        9.25, 4.45, 3.7, 1.7, size=12)
notes(s, "Prespecified arms", """
What an arm is: a planned side-experiment. Take the base model (the 15-variable panel), change exactly one thing, refit, and compare against the base model fitted on the same women and the same folds. The term comes from clinical trials, where each arm is one version of the treatment. 'Prespecified' means the list of arms and the expected result for each were written down before anything ran, which is what makes a null reportable rather than fishing. Arms C–H were prespecified; arm I (activity) comes from the analysis plan and was added when the MET calculation was built.

Each arm adds or substitutes one clinical idea and refits on the same rows and folds as its base model (complete cases for the arm variable).

- C. Calcium + vitamin D intake (diet two-day average + supplements), n 930: −0.002 [−0.006, +0.001].
- D. Serum 25(OH)D, n 974: −0.001 [−0.008, +0.005].
- E. Rheumatoid arthritis, n 988 (71 RA): 0.000.
- I. Physical activity (log MET-min/week + sitting time), n 932 women from 2007 on (2005–06 did not ask the questions): +0.004 [−0.002, +0.009].
- I2. The specialist's secondary activity measures (moderate and vigorous minutes per week + sitting), same 932 women: +0.003 [−0.002, +0.009].
- J. Sleep in the specialist's five bands instead of hours (7–8 h reference), n 1,107: −0.001 [−0.007, +0.006].
- F. PHQ-9 ≥ 10 instead of the continuous score: −0.001 [−0.002, +0.000] — a negligible loss.
- G1/G2. Diabetes recoded (borderline as diabetic) or dropped: +0.001 / 0.000. Sensitivity only.
- H1/H2. Outcome re-specified to femoral neck only (618 events, 0.747) or total hip only (424 events, 0.776). Different outcome, so no delta.

The C–H nulls were written down before the run, which is what makes them reportable rather than fishing.

Power gate: events per predictor (EPP) = min(events, non-events) / number of model columns. At T ≤ −1.0 the binding class is the 466 non-events → 466 / 16 = 29.1. At T ≤ −2.5, 76 / 16 = 4.75. The gate is named after Riley et al. but is really the classic 10-events-per-variable rule; Riley's sample-size criteria (shrinkage, optimism, precision of intercept) would be a better formal check — a statistician item.
""")

# ================================================================ 23 Calibration & referral
s = new_slide("Results 6: calibration and what a referral rule would look like", "Osteopenia+ target; prevalence in this cohort is 58% — PPV will not transfer to a clinic", section="Results")
picture(s, os.path.join(OUT, "calibration_curve.png"), 0.4, 1.3, h=5.0)
rr = [["Flag top", "Sensitivity", "DXAs", "Cases found", "PPV", "Scans/case"]]
for _, r in ref.iterrows():
    rr.append([("all" if r["Top fraction flagged"] == "scan all" else f"{float(r['Top fraction flagged']):.0%}"),
               r.Sensitivity, f"{int(r['DXAs ordered']):,}", r["Cases found"], r.PPV, f"{float(r['Scans per case']):.2f}"])
table(s, rr, 6.35, 1.45, 6.6, col_w=[1.0, 1.2, 0.85, 1.25, 1.0, 1.3], size=12, row_h=0.4)
bullets(s, [
    "Sigmoid-calibrated RF: Brier 0.200 vs 0.201 raw (always guessing the 58% average scores ≈ 0.24).",
    "Flag the top 30% → find 44% of cases at 1.19 scans per case (vs 1.72 scanning everyone).",
    "Referral table uses nested-CV ranks (quantiles), the threshold sweep uses calibrated probabilities — never merge them.",
    "The cutoff choice is clinical; no referral table is given for osteoporosis (76 cases — underpowered).",
], x=6.35, y=4.45, w=6.6, h=2.5, size=13)
notes(s, "Calibration and referral", """
Calibration: the random forest out-of-fold probabilities, raw and sigmoid-calibrated (CalibratedClassifierCV, 3-fold, inside the outer 5-fold), 10 quantile bins. Both track the diagonal; Brier 0.201 raw, 0.200 calibrated.

Referral table (referral_table.csv): flag the top X% of women by nested-CV out-of-fold rank. For example, flagging the top 30% orders 335 scans, finds 281 of 645 cases (44% sensitivity), PPV 84%, 1.19 scans per case found. Scanning everyone finds all 645 at 1.72 scans per case.

Threshold sweep (threshold_sweep.csv) is a different object: literal probability cutoffs on the calibrated forest (e.g., cutoff 0.30 → 97.8% sensitivity, 1,030 scans). Same-looking numbers, different meaning; they are kept separate on purpose.

Big caveat: 58% of this cohort is positive at T ≤ −1.0, so PPV and scans-per-case are inflated relative to a real clinic population. And OST would give almost the same table — the referral table illustrates utility, it does not show ML beats OST.

A useful extension: decision-curve analysis (net benefit) of model vs OST vs scan-all vs scan-none.
""")

# ================================================================ 24 Caveats
s = new_slide("Known caveats from code review (our backlog)", "Found while preparing this briefing — none changes the headline null, all are worth fixing or disclosing", section="Critique")
table(s, [
    ["Item", "Detail", "Impact"],
    ["Prior-fracture window", "Specialist asked for a 5-year window; any-age fracture shipped", "Clinical validity"],
    ["No survey design", "Weights / strata / PSU unused; results not nationally representative", "Generalisability"],
    ["Bootstrap scope", "Resamples fixed OOF scores; no refit variance; reports mean Δ", "CIs somewhat too narrow"],
    ["Optimism metric", "Leaderboard = mean of fold AUCs; nested = pooled OOF AUC", "Small, mixes aggregations"],
    ["Odds ratios", "Penalised (C = 1), class-weighted LR — shrunk, not MLE", "Labelling"],
    ["RF leaf size", "Shipped 1; grid best 5 (0.7523 vs 0.7478); inner-CV picks [20, 1, 20, 2, 20]; docs say ‘nested-CV chosen’", "Negligible"],
    ["Power gate naming", "10-EPV rule labelled ‘Riley’", "Labelling"],
    ["Hygiene", "Warnings globally suppressed; ~20 scratch scripts in repo root; no tests / lockfile", "Maintainability"],
], 0.6, 1.5, 12.1, col_w=[2.6, 6.0, 3.5], size=12, row_h=0.47)
notes(s, "Known caveats", """
Being upfront here builds credibility with an engineer. None of these would turn the null into a positive result — if anything, wider (refit) bootstrap intervals make the null more robust.

Most substantive:
1. The specialist's request for a 5-year prior-fracture window was never implemented and nothing records why. NHANES asks age at each fracture (OSQ020x / OSQ040), so it is constructible.
2. No survey weights or design — fine for internal prediction, but any prevalence or 'representative' claim is off the table.

Statistical scope: the bootstrap resamples the out-of-fold predictions, so it captures sampling variability of the test set but not refitting variability; repeated cross-validation with several seeds would give a fuller picture.

Hygiene: warnings.filterwarnings('ignore') hides solver convergence warnings (saga on elastic net could be affected); ~20 scratch scripts clutter the repo root; no tests, lockfile or CI.
""")

# ================================================================ 25 Statistician questions
s = new_slide("Questions to take to a statistician", section="Next steps")
bullets(s, [
    (0, "Framing the null:", "should we test equivalence / non-inferiority to OST (e.g., TOST with a ±0.02 margin) instead of ‘not separable’? What margin is clinically meaningful?"),
    (0, "Power:", "what n / events would detect ΔAUC = 0.02 over OST with 80% power, given model–OST correlation?"),
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

1. The headline is a null. A null from a confidence interval is 'absence of evidence'. The stronger, more publishable statement is equivalence: 'the ML model is within ±δ of OST'. That needs a pre-declared margin (δ = 0.02 or 0.03 AUC?) and a TOST-style test. With the current CI [−0.008, +0.025], we could already claim non-inferiority at a margin of 0.01 but not equivalence at 0.02 — worth a statistician's view.

2. Power. With roughly 1,100 women and model–OST score correlation around 0.9, what is the minimum detectable ΔAUC? If even double the data could not detect a clinically meaningful gain, that is a decision to stop rather than add cycles. The T ≤ −2.5 target especially would benefit from more events.

3. Uncertainty estimation. Our bootstrap resamples fixed predictions. Repeated CV (different seeds), or a bootstrap that refits, would include model-fitting variance. DeLong's test for correlated AUCs is a standard cross-check.

4. Missing data. Is single median imputation acceptable at < 6%? For whole-cycle gaps (activity in 2005–06), is it better to drop the variable, the cycle, or use MI with cycle as a predictor?

5. Survey weights. Specialist asked for weighted vs unweighted; pooled weights are not constructible across non-contiguous cycles with different bases. Is unweighted prediction acceptable, with per-cycle weighted descriptives?

6. The T ≤ −2.5 target has 76 events. Options: Firth logistic, regression on continuous T then threshold (current approach), or descriptive only. Should we apply Riley et al. (2020) sample-size criteria formally?

7. Outcome: should the continuous T-score be primary, as the specialist wanted, evaluated with R², MAE, calibration slope?

8. Clinical utility: decision curve analysis (net benefit across thresholds) and net reclassification vs OST often say more than ΔAUC.

9. Inference details: unpenalised GLM for the ORs; is Holm over 15 ablations the right family; is matching vitamin D across releases on BMD (which is in the outcome) acceptable?
""")

# ================================================================ 26 Directions
s = new_slide("Suggested directions", section="Next steps")
bullets(s, [
    (0, "1. Report the null properly.", "Pre-register an equivalence margin; add decision-curve analysis vs OST; publish ‘OST is near the ceiling for questionnaire data’."),
    (0, "2. Get more events, carefully.", "NHANES has no further hip-DXA cycles; consider broadening age or race/ethnicity with appropriate T-score references and interaction terms."),
    (0, "3. Bring in new kinds of signal, not more of the same.", "Height loss / height vs self-reported max height, weight change since age 25/40, grip strength (MGX, limited cycles), medications via RXQ_RX (PPIs, SSRIs, glucocorticoid detail, aromatase inhibitors), lab markers."),
    (0, "4. Change the target.", "Model continuous T-score as primary; long term, fracture outcomes need a prospective cohort (e.g., SOF, MrOS, UK Biobank) — also enables external validation."),
    (0, "5. External / temporal validation.", "Train on 2005–2014, test on 2017–2020 as a temporal hold-out."),
    (0, "6. Engineering hardening.", "Implement the 5-year fracture window; repeated-seed CV; pin deps (requirements.txt); unit tests for decode / SPEC / cohort asserts; remove scratch scripts; experiment tracking (e.g., MLflow)."),
], size=15)
notes(s, "Suggested directions", """
Directions, ordered by expected value.

1. Treat the null as the result. The finding that a two-input formula is at the ceiling for questionnaire data is useful to clinicians — it says don't bother with a longer questionnaire. Strengthen it with an equivalence framing and decision-curve analysis.

2. More events. The binding constraint is the 76 osteoporosis cases. NHANES has no other cycles with hip DXA (2011–12, 2015–16 and 2021–23 did not scan the hip). Broadening race/ethnicity needs race-appropriate reference values or a single reference with race as a covariate — a clinical decision.

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
callout(s, "Bottom line: a careful pipeline and an honest null —\nOST (weight & age) is essentially as good as a 15-variable ML panel on NHANES data.",
        0.6, 5.7, 12.1, 1.05, fill=NAVY, color=WHITE, size=17, bold=True)
notes(s, "Asks", """
Close by turning the session into a working discussion. Specific asks for a senior ML/data engineer:

- Sanity-check the leakage defences. In particular: is a 5-field physical fingerprint a sufficient cross-release duplicate check? Would they use GroupKFold on a fingerprint hash as belt-and-braces?
- Advise on validation compute: repeated nested CV (e.g., 10 seeds) multiplies a 25–40 minute run; could the expensive parts (permutation importance, ablation grid) be parallelised or cached?
- Advise on structure: the single-file design is easy to audit for a clinical audience, but hard to test. A middle path: keep the step functions, move them into a small package, add pytest for decode/SPEC/cohort counts.
- NHANES ingestion is reusable: cycle registry, label-vs-code decoding, denormal handling, cross-release duplicate detection.

Final message: we built a defensible pipeline, guarded against a subtle duplicated-entity leakage trap in NHANES, and the honest conclusion is that a two-variable clinical formula is as good as our machine-learning panel. The next gains come from new data, not new models.
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
                "OsteoporosisML.py (outputs/ folder).")
d.add_heading("Suggested timing (≈ 50 min + discussion)", 1)
for t in ["Overview & data (slides 1–6): 10 min", "Cohort, target, specialist decisions (7–10): 8 min",
          "The specialist's variable list, item by item, and the result with every input in place (11–14): 10 min",
          "Features, missing data, guard-rails (15–17): 6 min",
          "AUC, the 8 models, evaluation design, code (18–23): 14 min",
          "Results (24–29): 12 min", "Caveats, statistician questions, directions, asks (30–33): 8 min + discussion"]:
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
    ("Why not GroupKFold?", "With only the pooled 2017–2020 file loaded there is exactly one row per woman, so StratifiedKFold on rows equals grouping by person. The fingerprint audit asserts this. GroupKFold on a fingerprint hash would be a cheap extra safeguard."),
    ("Why median imputation rather than MICE or native NaN handling in LightGBM/XGBoost?", "Most variables are < 6% missing, and imputation is inside the fold so it does not leak. Using one pipeline for all models keeps comparisons fair. The largest gap is alcohol (13.6%); activity, missing for a whole cycle, is kept out of the headline model. MICE or missing indicators are on the list for the statistician."),
    ("Why such heavily regularised boosters? Did you tune them?", "With ~1,100 rows and 76 rare events, boosters overfit easily (train AUC 0.93–0.98 at T ≤ −2.5 even when constrained). We chose to under-fit rather than report a tuned booster. The near-identical AUCs across all model families indicate a feature ceiling, so tuning is unlikely to close the gap to a meaningful level — but it has not been systematically searched."),
    ("Why AUC and not PR-AUC or log-loss?", "AUC is the clinical-literature convention and the comparator (OST) is a score without probabilities. Calibration is assessed separately (Brier, calibration curve). PR-AUC would be informative for the 6.8%-prevalence target."),
    ("Is the bootstrap CI valid?", "It is a paired, stratified bootstrap of out-of-fold scores; it captures test-sample variability but not model-refit variability, so intervals are somewhat narrow. That would only strengthen the null. Repeated CV is the planned upgrade."),
    ("Could deep learning or AutoML help?", "Unlikely: n ≈ 1,100, tabular, signal dominated by one variable. Linear models already match the forest. Gains would need new information."),
    ("Why ignore survey weights?", "Pooled weights cannot be constructed consistently across non-contiguous cycles with different weight bases (2-year vs 3.2-year P_). For prediction, unweighted fitting is common; the cost is that prevalence and PPV are not nationally representative."),
    ("How do you know there are no other leaks?", "Allowlist + denylist assert, in-fold preprocessing, nested model selection, the |coef| > 2 leak alarm (largest is weight at −1.18), and the fact that OST — which cannot leak — scores within 0.012 of the model."),
    ("How long does it take to run and can it be parallelised?", "≈ 25–40 minutes; dominated by bootstraps, permutation importance, the ablation grid (15 variables × 8 models) and nested CV. Folds and ablation variables are embarrassingly parallel."),
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
    "Panel: 15 variables, 16 columns (alcohol in 3 categories). Arms: intake n 930, serum n 974, RA n 988, activity n 932, sleep bands n 1,107.",
    "Nested AUC T ≤ −1.0: 0.747 vs OST 0.739 (Δ +0.008 [−0.008, +0.025]) vs weight 0.737 (Δ +0.010 [−0.007, +0.027]).",
    "Nested AUC T ≤ −2.5: 0.786 vs OST 0.780 (Δ +0.007 [−0.016, +0.030]) vs weight 0.766 (Δ +0.021 [−0.005, +0.048]).",
    "Block ablation: drop body size 0.603; keep only age + weight 0.739; full 0.755 (Ridge → T).",
    "Significant ORs: weight 0.51/10 kg; estrogen 0.59; PIR 0.90; age 1.27/5 y; prior fracture 1.76.",
    "Calibration Brier 0.201 raw / 0.200 sigmoid. Top 30% flagged → 44% sensitivity, PPV 84%, 1.19 scans per case.",
]:
    d.add_paragraph(t, style="List Bullet")

d.add_heading("Source files", 1)
for t in ["OsteoporosisML.py (pipeline, blocks A–G)", "outputs/*.csv, *.png (results, 2 Oct 2026 run)", "_run_specialist.log (counts and verdicts)",
          "Notes/specialist_answers_and_decisions.html, Specialist_Review_Questions/Answers.docx (clinical decisions)",
          "Notes/statistician_brief.html (methodological rulings and open questions)",
          "Notes/presentation_ml_engineer/make_charts.py and build_deck.py (regenerate this deck)"]:
    d.add_paragraph(t, style="List Bullet")

notes_path = os.path.join(HERE, "Presenter_Notes_Osteoporosis_ML_Briefing.docx")
d.save(notes_path)
print("wrote", deck_path)
print("wrote", notes_path)
print("slides:", len(prs.slides))
