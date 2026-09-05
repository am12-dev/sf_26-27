"""Build the specialist presentation deck.

Numbers come from outputs/ where possible so the deck cannot drift from the
pipeline. Palette is the dataviz reference instance (light surface).

Dependency: python-pptx (pip install python-pptx) - NOT used by the pipeline
itself, only by this script. Run Notes/make_figures.py first; this reads the
PNGs it writes into Notes/figures/.
"""
import os
import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(BASE, 'Notes', 'figures')
OUTP = os.path.join(BASE, 'Notes', 'Osteoporosis_ML_Specialist_Briefing.pptx')

# palette
NAVY   = RGBColor(0x10, 0x42, 0x81)
BLUE   = RGBColor(0x2a, 0x78, 0xd6)
INK    = RGBColor(0x0b, 0x0b, 0x0b)
INK2   = RGBColor(0x52, 0x51, 0x4e)
MUTED  = RGBColor(0x8a, 0x88, 0x80)
SURF   = RGBColor(0xfc, 0xfc, 0xfb)
BAND   = RGBColor(0xf1, 0xf2, 0xef)
GOOD   = RGBColor(0x0c, 0x7a, 0x0c)
CRIT   = RGBColor(0xd0, 0x3b, 0x3b)
WARNC  = RGBColor(0x8a, 0x6a, 0x15)
WHITE  = RGBColor(0xff, 0xff, 0xff)

HEAD_FONT = 'Calibri Light'
BODY_FONT = 'Calibri'
MONO_FONT = 'Consolas'

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
W, H = 13.333, 7.5


def bg(slide, color=SURF):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color


def tb(slide, x, y, w, h, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.paragraphs[0].alignment = align
    return tf


def line(tf, text, size=16, bold=False, color=INK, font=BODY_FONT,
         space_after=6, first=False, italic=False, indent=0, bullet=None):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.space_after = Pt(space_after)
    p.level = indent
    if bullet:
        r0 = p.add_run()
        r0.text = bullet + '  '
        r0.font.size, r0.font.bold = Pt(size), True
        r0.font.color.rgb = BLUE
        r0.font.name = font
    r = p.add_run()
    r.text = text
    r.font.size, r.font.bold, r.font.italic = Pt(size), bold, italic
    r.font.color.rgb = color
    r.font.name = font
    return p


def header(slide, title, eyebrow=None, rule=True):
    if eyebrow:
        t = tb(slide, 0.62, 0.34, 11.5, 0.34)
        line(t, eyebrow.upper(), size=11.5, bold=True, color=BLUE,
             font=BODY_FONT, first=True)
    t = tb(slide, 0.62, 0.66 if eyebrow else 0.5, 12.1, 0.95)
    line(t, title, size=29, color=NAVY, font=HEAD_FONT, first=True)
    if rule:
        ln = slide.shapes.add_shape(1, Inches(0.62), Inches(1.62), Inches(12.1), Emu(11430))
        ln.fill.solid(); ln.fill.fore_color.rgb = NAVY
        ln.line.fill.background(); ln.shadow.inherit = False


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def new(title=None, eyebrow=None):
    s = prs.slides.add_slide(BLANK)
    bg(s)
    if title:
        header(s, title, eyebrow)
    return s


def figure(slide, name, x, y, w):
    slide.shapes.add_picture(os.path.join(FIG, name), Inches(x), Inches(y), width=Inches(w))


def takeaway(slide, text, y=6.42, color=NAVY):
    y = min(y, H - 0.72 - 0.14)   # never let the band run off the bottom edge
    box = slide.shapes.add_shape(1, Inches(0.62), Inches(y), Inches(12.1), Inches(0.72))
    box.fill.solid(); box.fill.fore_color.rgb = BAND
    box.line.fill.background(); box.shadow.inherit = False
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left, tf.margin_right = Inches(0.18), Inches(0.18)
    tf.margin_top = tf.margin_bottom = Inches(0.06)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    line(tf, text, size=14.5, color=color, bold=True, first=True, space_after=0)


def table(slide, rows, x, y, w, col_w=None, size=12, head_size=11,
          h=None, head_color=NAVY):
    nr, nc = len(rows), len(rows[0])
    h = h or min(0.34 * nr, 4.9)
    shp = slide.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(h))
    t = shp.table
    if col_w:
        for i, cw in enumerate(col_w):
            t.columns[i].width = Inches(cw)
    for ci, val in enumerate(rows[0]):
        c = t.cell(0, ci)
        c.text = str(val)
        c.fill.solid(); c.fill.fore_color.rgb = head_color
        pr = c.text_frame.paragraphs[0]
        pr.runs[0].font.size = Pt(head_size)
        pr.runs[0].font.bold = True
        pr.runs[0].font.color.rgb = WHITE
        pr.runs[0].font.name = BODY_FONT
        c.margin_left = c.margin_right = Inches(0.07)
    for ri in range(1, nr):
        for ci in range(nc):
            c = t.cell(ri, ci)
            raw = rows[ri][ci]
            mono = isinstance(raw, str) and raw.startswith('`')
            # strip EVERY backtick, not just the outer pair - cells naming two
            # variables ("`a` / `b`") otherwise render the inner marks literally
            c.text = raw.replace('`', '') if isinstance(raw, str) else str(raw)
            c.fill.solid()
            c.fill.fore_color.rgb = WHITE if ri % 2 else BAND
            pr = c.text_frame.paragraphs[0]
            for r in pr.runs:
                r.font.size = Pt(size)
                r.font.color.rgb = INK
                r.font.name = MONO_FONT if mono else BODY_FONT
            c.margin_left = c.margin_right = Inches(0.07)
            c.margin_top = c.margin_bottom = Inches(0.02)
    return t


# ===========================================================================
# 1. TITLE
# ===========================================================================
s = prs.slides.add_slide(BLANK)
bg(s, NAVY)
tf = tb(s, 1.0, 1.75, 11.3, 2.6)
line(tf, 'Screening Before the Scan', size=52, color=WHITE, font=HEAD_FONT, first=True)
line(tf, 'Can routine primary-care data predict what a DXA scan would say?',
     size=21, color=RGBColor(0xb7, 0xd3, 0xf6), font=HEAD_FONT, space_after=0)
tf2 = tb(s, 1.0, 4.75, 11.3, 1.9)
line(tf2, '1,484 non-Hispanic White women aged 50–65  ·  six NHANES cycles  ·  23 predictors  ·  8 models',
     size=15, color=RGBColor(0x9e, 0xc5, 0xf4), first=True)
line(tf2, 'Briefing prepared for review by an osteoporosis specialist', size=15,
     color=RGBColor(0x9e, 0xc5, 0xf4))
line(tf2, 'All results reproduce from a single script, fixed random seed', size=13,
     color=RGBColor(0x86, 0xb6, 0xef), italic=True)
notes(s, "Goal of this meeting: get clinical review of the design, the variable set, and the "
         "referral threshold. I am NOT claiming a DXA replacement - this is a triage question.")

# ===========================================================================
# 2. THE PROBLEM
# ===========================================================================
s = new('Bone loss is silent until it breaks something', 'The clinical problem')
tf = tb(s, 0.62, 1.95, 6.1, 4.3)
for b, t in [('1', 'No symptoms. Nothing a patient notices until a hip or wrist fractures after a minor fall.'),
             ('2', 'DXA is accurate but not universally reachable: a fixed, costly machine, an appointment to order and travel to.'),
             ('3', 'Routine screening often begins at 65 — yet loss accelerates fastest in the decade right after menopause.'),
             ('4', 'So the women in the 50–65 window are largely unscanned unless something else flags them.')]:
    line(tf, t, size=16.5, color=INK, bullet=b, space_after=15)

box = s.shapes.add_shape(1, Inches(7.05), Inches(1.95), Inches(5.65), Inches(3.15))
box.fill.solid(); box.fill.fore_color.rgb = BAND
box.line.fill.background(); box.shadow.inherit = False
tf = box.text_frame; tf.word_wrap = True
tf.margin_left = tf.margin_right = Inches(0.28); tf.margin_top = Inches(0.24)
line(tf, 'The question is triage, not replacement', size=17, bold=True, color=NAVY, first=True)
line(tf, 'Given a room of 55-year-olds and a limited number of scanner slots, can cheap '
         'information rank them well enough that the slots go to the right women?', size=15, color=INK)
line(tf, 'A triage tool does not have to be right about individuals. It has to order '
         'people better than what is used today.', size=15, color=INK2, italic=True)
takeaway(s, 'This project predicts a test result, not a fracture. It is a referral aid — never a diagnosis.')

# ===========================================================================
# 3. THE CENTRAL DESIGN
# ===========================================================================
s = new('Build the answer key from DXA — then hide it', 'Study design')
tf = tb(s, 0.62, 1.9, 12.1, 1.1)
line(tf, 'NHANES did both halves on the same people: it interviewed and examined participants '
         'AND scanned many of them. So the scan can be used twice, in two opposite roles.',
     size=16, color=INK, first=True)

for i, (t, body, col) in enumerate([
    ('ROLE 1 — the answer key',
     'Femoral-neck and total-hip BMD become a T-score, which becomes the yes/no label '
     'the model is graded against. Research use only.', NAVY),
    ('ROLE 2 — forbidden input',
     'Every column carrying the scan (BMD, T-scores, both labels, bone_status) is '
     'excluded from the feature set. Using them would predict the scan from the scan.', CRIT)]):
    box = s.shapes.add_shape(1, Inches(0.62 + i * 6.2), Inches(3.15), Inches(5.9), Inches(2.0))
    box.fill.solid(); box.fill.fore_color.rgb = BAND
    box.line.fill.background(); box.shadow.inherit = False
    tf = box.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.26); tf.margin_top = Inches(0.2)
    line(tf, t, size=15, bold=True, color=col, first=True)
    line(tf, body, size=14.5, color=INK)

tf = tb(s, 0.62, 5.35, 12.1, 0.9)
line(tf, 'Remove role 1 and what remains is a screening tool that needs no scanner. '
         'Feature selection here works by exclusion, so a standing alarm watches for any new '
         'BMD-derived column silently re-entering the model.', size=15, color=INK2, first=True)
takeaway(s, 'Leakage check every run: largest standardised coefficient 0.990 (weight) against an alarm threshold of 2.0. Clean.')
notes(s, "This is the slide to linger on. If a specialist understands only one thing, it should be "
         "that the DXA is the grading key and is walled off from the inputs.")

# ===========================================================================
# 4. DATA SOURCE
# ===========================================================================
s = new('NHANES: fourteen source files per cycle', 'Data')
tf = tb(s, 0.62, 1.9, 12.1, 0.75)
line(tf, 'A continuous CDC survey. Every participant carries one ID (SEQN) and every file keys on it — '
         'which is what makes the assembly possible. Six cycles: 2005-06, 07-08, 09-10, 13-14, 17-18, 17-20.',
     size=15, color=INK, first=True)
rows = [['File', 'Contents', 'Contributes'],
        ['DEMO', 'Demographics', 'Age, sex, ethnicity (cohort selection); income-to-poverty ratio'],
        ['BMX', 'Body measurements', 'Weight, height, BMI'],
        ['DXXFEM', 'Hip DXA scan', 'THE ANSWER KEY ONLY — femoral-neck + total-hip BMD'],
        ['RHQ', 'Reproductive health', 'Menopause age & cause, hysterectomy, oophorectomy, oestrogen use'],
        ['OSQ', 'Osteoporosis module', 'Prior hip / spine / wrist fracture, long-term steroid use'],
        ['VID', 'Vitamin D lab', 'Serum 25(OH)D (measured, not reported)'],
        ['DR1TOT + DR2TOT', 'Two 24-h diet recalls', 'Two-day average calcium and vitamin D'],
        ['DSQTOT', 'Supplements', 'Calcium and vitamin D from pills'],
        ['MCQ / SMQ / ALQ', 'Conditions, smoking, alcohol', 'Arthritis, ever-smoked, drinks per day'],
        ['PAQ / DIQ / DPQ', 'Activity, diabetes, PHQ-9', 'Vigorous activity, diabetes, depression score'],
        ['SLQ', 'Sleep', 'Collected, then dropped — too sparse across cycles']]
table(s, rows, 0.62, 2.78, 12.1, col_w=[1.85, 2.5, 7.75], size=11.5, h=3.8)
takeaway(s, 'All eleven download caches are committed, so the whole pipeline reproduces offline.', y=6.85)

# ===========================================================================
# 5. COHORT
# ===========================================================================
s = new('Four filters, each one deliberate', 'Cohort derivation')
figure(s, 'fig1_attrition.png', 0.72, 1.85, 7.5)
tf = tb(s, 8.5, 1.95, 4.25, 4.4)
line(tf, 'Why so narrow?', size=16, bold=True, color=NAVY, first=True)
line(tf, 'Holding sex, ancestry and age band fixed means the model does not spend limited '
         'statistical power learning those effects — and the T-score reference values are the '
         'right ones for this group.', size=13.5, color=INK)
line(tf, 'The cost', size=16, bold=True, color=NAVY, space_after=4)
line(tf, 'Nothing here generalises outside this group. The pipeline would have to be re-run '
         'and re-validated for any other population.', size=13.5, color=INK)
line(tf, 'The last filter', size=16, bold=True, color=NAVY, space_after=4)
line(tf, '379 otherwise-eligible women had no valid scan. No answer key means nothing to '
         'train or grade against.', size=13.5, color=INK)
takeaway(s, 'The script hard-asserts n = 1,484, so any change to cycles or criteria stops the run instead of quietly reporting different numbers.')

# ===========================================================================
# 6. THE TARGET
# ===========================================================================
s = new('From bone density to a yes/no label', 'The outcome')
tf = tb(s, 0.62, 1.9, 12.1, 0.6)
line(tf, 'A raw density of 0.72 g/cm² means nothing alone. The T-score expresses it as standard '
         'deviations from a healthy young-adult mean, using fixed NHANES III reference values.',
     size=15, color=INK, first=True)
rows = [['Step', 'What happens'],
        ['Femoral neck', 'T = (BMD − 0.858) / 0.120'],
        ['Total hip', 'T = (BMD − 0.942) / 0.122'],
        ['Combine', 'Take the LOWER of the two sites — clinical practice classifies by the worst site'],
        ['Round', 'To three decimals before thresholding, so women exactly on a cutoff do not '
                  'land on either side by floating-point noise'],
        ['Label', 'at_risk = T ≤ −1.0   ·   osteoporosis = T ≤ −2.5']]
table(s, rows, 0.62, 2.62, 12.1, col_w=[2.2, 9.9], size=13, h=2.1)

for i, (lab, val, sub, col) in enumerate([
        ('at_risk  (T ≤ −1.0)', '836 / 1,484', 'osteopenia or worse — 56.3%. PRIMARY target.', NAVY),
        ('osteoporosis  (T ≤ −2.5)', '94 / 1,484', 'the WHO threshold — 6.3%. Only 4.1 events per predictor.', CRIT),
        ('T-score distribution', 'mean −1.08', 'SD 1.02 — the cohort average sits on the osteopenia line.', INK2)]):
    box = s.shapes.add_shape(1, Inches(0.62 + i * 4.12), Inches(4.95), Inches(3.86), Inches(1.35))
    box.fill.solid(); box.fill.fore_color.rgb = BAND
    box.line.fill.background(); box.shadow.inherit = False
    tf = box.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.16); tf.margin_top = Inches(0.12)
    line(tf, lab, size=12, bold=True, color=col, first=True, space_after=2)
    line(tf, val, size=21, color=INK, font=HEAD_FONT, space_after=2)
    line(tf, sub, size=11.5, color=INK2)
takeaway(s, 'The primary target is NOT osteoporosis — it is any measurable bone loss, in over half this cohort. Quote it that way.')
notes(s, "Be explicit about this. If you say 'we detect osteoporosis with AUC 0.81' that is wrong on "
         "two counts: wrong target and wrong (optimistic) number.")

# ===========================================================================
# 7. VARIABLES USED
# ===========================================================================
s = new('The 23 inputs the model may look at', 'Variables used')
tf = tb(s, 0.62, 1.9, 12.1, 0.5)
line(tf, 'Grouped by where a real clinic would get them. If a variable here is not obtainable in a '
         'primary-care visit, the premise fails.', size=15, color=INK, first=True)
rows = [['Available from', 'Variables', 'Missing'],
        ['Measured in the room\nscale, stadiometer, DOB', '`weight_kg  height_cm  bmi  age`', '≤ 0.5%'],
        ['Reproductive history\ninterview', '`postmenopausal  years_since_menopause  hysterectomy\noophorectomy  menopause_natural  ever_used_estrogen`', '2.8 – 33.6%'],
        ['Chart / medication list', '`any_prior_fracture  steroid_use  any_arthritis  diabetes\never_smoked  alcohol_drinks_day  vigorous_activity`', '0 – 31.7%'],
        ['Routine labs', '`serum_vitd_nmol`', '23.0%'],
        ['Diet & supplements', '`total_calcium_mg  total_vitd_mcg  supp_data_available`', '15.4%'],
        ['Social', '`poverty_income_ratio`', '5.5%'],
        ['Mood screen', '`phq9_score`', '80.4%']]
table(s, rows, 0.62, 2.5, 12.1, col_w=[3.0, 7.55, 1.55], size=11.5, h=3.7)
takeaway(s, 'Two I would flag myself: phq9_score is 80% missing and contributes nothing; supp_data_available is a dataset-provenance flag, not a patient characteristic.', y=6.5)

# ===========================================================================
# 8. VARIABLES COMPUTED
# ===========================================================================
s = new('Variables computed, not collected', 'Feature engineering')
rows = [['Computed variable', 'How', 'Why it exists'],
        ['`t_score`', 'min of two site T-scores, rounded to 3 dp',
         'The grading key. Clinical convention classifies by the worst site.'],
        ['`years_since_menopause`', 'age − age at last period (RHQ060), implausible ages screened out',
         'Loss accelerates through the transition then slows. In a 50–65 cohort where timing varies by a decade, age is a weak surrogate.'],
        ['`postmenopausal`', '1 − (any period in last 12 months)',
         'Directly separates still-cycling from post-transition.'],
        ['`hysterectomy` / `oophorectomy`', 'kept as two separate flags, never pooled',
         'Uterus-only leaves ovaries producing oestrogen; bilateral oophorectomy cuts it off abruptly. Pooling buries the signal.'],
        ['`menopause_natural`', 'RHD042 (2005-10) / RHD043 (2013+) coalesced, text parsed',
         'Separates natural from surgical menopause across a mid-study variable rename.'],
        ['`any_prior_fracture`', '1 if any site reported; 0 only if all sites answered no; else NaN',
         'Hip (21) and wrist (46) events are too rare to estimate separately. Pooled = 233 positives, and the clinically meaningful construct.'],
        ['`total_calcium_mg` / `total_vitd_mcg`', 'two-day dietary mean + supplement intake, plain addition',
         'Intake is food plus pills. Plain addition means a missing component yields a missing total, never a fabricated one.'],
        ['`serum_vitd_nmol`', 'LBXVIDMS coalesced with LBDVIDMS',
         'NHANES changed the column name mid-study; one is regression-adjusted to the other.'],
        ['`phq9_score`', 'nine PHQ items clipped 0–3, summed with min_count=5',
         'Fewer than five answered items yields NaN rather than a falsely low score.']]
table(s, rows, 0.62, 1.85, 12.1, col_w=[2.75, 3.85, 5.5], size=10.5, h=4.55)
takeaway(s, 'The reproductive variables are where the domain thinking lives — they reflect how bone loss actually works, not what was easiest to code.', y=6.9)

# ===========================================================================
# 9. VARIABLES DROPPED
# ===========================================================================
s = new('Variables dropped, and exactly why', 'Exclusions')
rows = [['Dropped', 'Reason', 'Category'],
        ['`femoral_neck_bmd  total_hip_bmd  t_femoral_neck\nt_total_hip  t_score  bone_status  at_risk  osteoporosis`',
         'Every column carrying the scan. Using any of them predicts the scan from the scan.', 'TARGET LEAKAGE'],
        ['`prior_hip_fracture  prior_spine_fracture\nprior_wrist_fracture`',
         'Only 21 hip and 46 wrist events. Every tree gave them zero importance while linear models fitted noise. Pooled instead.', 'TOO RARE'],
        ['`age_at_menopause`',
         'age = age_at_menopause + years_since_menopause exactly. All three makes the design rank-deficient.', 'COLLINEAR'],
        ['`dietary_calcium_mg  supp_calcium_mg  DR2TCALC\ndietary_vitd_mcg  supp_vitd_mcg  DR2TVD`',
         'Components superseded by the total_* variables; left in they enter as near-duplicates.', 'SUPERSEDED'],
        ['`n_recall_days`',
         'Encodes whether the person answered a second diet survey — a property of the survey, not the woman.', 'SURVEY ARTEFACT'],
        ['`DPQ010 … DPQ090`', 'The nine raw PHQ items, superseded by their sum.', 'SUPERSEDED'],
        ['`sleep_hrs  sleep_risk`', 'Sparse and inconsistent across cycles. Both feature sets are built; only the without-sleep arm is trained.', 'DATA DENSITY'],
        ['`education`', 'Not an explicit exclusion — survives as text, then swept up by the blanket drop of non-numeric columns. An accidental omission.', 'ACCIDENTAL'],
        ['`SEQN  RIAGENDR  RIDRETH1  survey_cycle`', 'IDs and the filter variables, constant by construction.', 'NOT A PREDICTOR']]
table(s, rows, 0.62, 1.85, 12.1, col_w=[4.35, 5.9, 1.85], size=10.5, h=4.5)
takeaway(s, 'I am flagging education as a genuine oversight rather than a decision — it is collected but never modelled.', y=6.85)
notes(s, "If asked 'what would you add next': education is already collected and silently dropped; "
         "recovering it is the cheapest improvement available.")

# ===========================================================================
# 10. GUARDS
# ===========================================================================
s = new('Six ways this could have been wrong', 'Validity guards')
tf = tb(s, 0.62, 1.85, 12.1, 0.45)
line(tf, 'Most of these were not hypothetical — they were found and fixed, which is a different '
         'and stronger claim than "we were careful".', size=15, color=INK, first=True)
rows = [['#', 'Risk', 'Guard, and what it caught'],
        ['1', 'Target leakage', 'Alarm on any standardised coefficient > 2.0. Largest legitimate is 0.990 (weight). Clean every run.'],
        ['2', 'Clinically backwards effects', 'EXPECTED_SIGNS dictionary flags wrong-direction coefficients. This surfaced the age / menopause collinearity. Currently flags vitamin-D intake — reverse causation.'],
        ['3', 'Fabricated nutrient totals', 'Plain addition, not fill-value zero. Separately distinguishes "cycle shipped no supplement file" (206 women, unobserved) from "reported no supplements".'],
        ['4', 'A variable under a false name', 'MCQ160A was named rheumatoid_arthritis. It asks about ANY arthritis — 45.8% prevalence masquerading as a 1–2% FRAX risk factor. Renamed any_arthritis.'],
        ['5', 'Importance measures that lie', 'Gini importance ranked calcium 7th despite a flat outcome gradient. Replaced entirely with permutation importance (AUC lost when shuffled).'],
        ['6', 'A flattered in-sample score', 'The forest scores 1.000 in-sample by construction — 0.997 even on shuffled labels. Out-of-bag scoring (0.825) is reported instead.']]
table(s, rows, 0.62, 2.45, 12.1, col_w=[0.5, 3.0, 8.6], size=11, h=3.9)
takeaway(s, 'Leaf size was tuned by nested CV, not by eye: raising it to shrink the train/test gap LOWERS test AUC monotonically, 0.810 → 0.762.', y=6.55)

# ===========================================================================
# 11. MODELS
# ===========================================================================
s = new('Eight models across two arms', 'Models used')
tf = tb(s, 0.62, 1.85, 12.1, 0.45)
line(tf, 'All wrapped in the same pipeline — median imputation → standardisation → estimator — '
         'so preprocessing is always learned inside the training fold, never from the test rows.',
     size=15, color=INK, first=True)
rows = [['Model', 'What it actually does', 'Why it is in the set'],
        ['Logistic regression (L2)', 'One weight per variable, added up; penalty discourages large weights', 'The interpretable baseline — its coefficients become the odds ratios a clinician reads'],
        ['Elastic-net logistic', 'Same, with a penalty that can push weights to exactly zero', 'Automatic variable selection. It zeroed phq9_score entirely'],
        ['Random forest', '500 trees on different bootstrap samples, votes averaged', 'Captures non-linearity and interactions no additive model can. Wins here'],
        ['LightGBM', 'Trees built in sequence, each correcting the last', 'Usually strongest on tabular data — deliberately constrained here'],
        ['XGBoost', 'Same idea, different implementation', 'Independent check on LightGBM'],
        ['Ridge → T-score', 'Predicts the continuous T-score, never a label', 'Dichotomising discards information: T = −2.4 and T = +0.5 are both "negative"'],
        ['RF → T-score', 'Same, non-linear', 'One fit serves BOTH cutoffs — threshold the predicted T-score twice'],
        ['LightGBM → T-score', 'Same, boosted', 'Third check on the regression arm']]
table(s, rows, 0.62, 2.45, 12.1, col_w=[2.7, 4.35, 5.05], size=11, h=3.85)
takeaway(s, 'Both boosters are deliberately crippled (max_depth 2, reg_lambda 50): at n = 1,484 an unconstrained booster memorises the data and reports a fantasy.', y=6.5)

# ===========================================================================
# 12. VALIDATION DESIGN
# ===========================================================================
s = new('How the numbers were earned', 'Validation design')
for i, (t, body) in enumerate([
    ('5-fold cross-validation',
     'Split the 1,484 women into five groups holding case proportion equal. Train on four, test on the fifth, '
     'rotate five times. Every woman is tested exactly once, on a model that never saw her. Seed fixed at 42 throughout.'),
    ('The OST baseline — the bar to clear',
     'OST = 0.2 × (weight_kg − age). A validated 1985 formula needing only a scale and a birthdate. '
     'Reporting AUC without a cheap comparator is uninterpretable. Our OST scores 0.747 / 0.773 — inside the published 0.71–0.79 range, '
     'which independently validates the implementation.'),
    ('Nested cross-validation — the honest number',
     'Fitting eight models and reporting the best is biased upward: it was chosen BECAUSE it scored well on those rows. '
     'Nested CV moves model selection inside each training fold, so no test row helps pick the model scored on it.')]):
    y = 1.95 + i * 1.52
    box = s.shapes.add_shape(1, Inches(0.62), Inches(y), Inches(12.1), Inches(1.32))
    box.fill.solid(); box.fill.fore_color.rgb = BAND
    box.line.fill.background(); box.shadow.inherit = False
    tf = box.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.24); tf.margin_top = Inches(0.14)
    line(tf, t, size=15.5, bold=True, color=NAVY, first=True, space_after=3)
    line(tf, body, size=13.5, color=INK)
takeaway(s, 'Reported both ways on purpose. Where the two agree, the leaderboard was not flattering itself. Where they diverge, the nested number is the real one.')

# ===========================================================================
# 13. LEADERBOARD
# ===========================================================================
s = new('Every model against the 1985 formula', 'Results — leaderboard')
figure(s, 'fig2_leaderboard.png', 1.15, 1.8, 8.1)
tf = tb(s, 9.5, 2.0, 3.3, 4.3)
line(tf, 'Reading it', size=15.5, bold=True, color=NAVY, first=True)
line(tf, 'The forest wins clearly — 0.810 vs 0.753 for linear models. That gap says real '
         'non-linear structure exists.', size=13, color=INK)
line(tf, 'The boosters LOSE to the forest, unusual on tabular data and a direct consequence of '
         'how hard they were regularised.', size=13, color=INK)
line(tf, 'L2 and elastic net are identical to three decimals — with 23 chosen predictors there is '
         'little for sparsity to remove.', size=13, color=INK)
line(tf, 'Weight alone (0.735) sits BELOW OST, so the age term earns its place.', size=13, color=INK)
takeaway(s, 'All 23 variables, the bloodwork, the diet surveys and 500 trees buy +0.063 AUC over a formula you can do in your head.')

# ===========================================================================
# 14. THE HONEST RESULT
# ===========================================================================
s = new('The result that matters, and it splits by target', 'Results — headline')
figure(s, 'fig3_nested_verdict.png', 0.85, 1.78, 11.6)
tf = tb(s, 0.62, 4.95, 12.1, 1.35)
line(tf, 'Osteopenia or worse: the nested estimate EQUALS the leaderboard (0.810 both ways) and the gain is '
         'positive in all five folds (+0.070, +0.063, +0.052, +0.055, +0.074). Nothing to strip out — the same '
         'model won everywhere. A solid, reproducible result.', size=14, color=INK, first=True)
line(tf, 'Osteoporosis: 0.833 collapses to 0.806. That 0.027 drop IS the selection bias, caught in the act. The '
         'remaining +0.031 spans zero and one fold came out negative. With 94 events, we cannot show the model '
         'beats a two-variable formula.', size=14, color=INK)
takeaway(s, 'Bringing you "this half works, this half we cannot yet claim" is the whole point of building the machinery.')
notes(s, "This is the centrepiece slide. A judge or reviewer who has seen many ML posters will recognise "
         "immediately that almost nobody does this. Do not rush it.")

# ===========================================================================
# 15. IMPORTANCE
# ===========================================================================
s = new('Weight dominates everything else', 'Results — predictors')
figure(s, 'fig5_importance.png', 0.85, 1.8, 8.0)
tf = tb(s, 9.1, 2.0, 3.7, 4.3)
line(tf, 'The most instructive row', size=15.5, bold=True, color=NAVY, first=True)
line(tf, 'weight_kg is by far the most predictive single variable — shuffling it costs 0.145 AUC in '
         'the linear model, five to ten times anything else.', size=13, color=INK)
line(tf, 'Yet its odds ratio is NOT significant (0.41–1.05).', size=13, bold=True, color=CRIT)
line(tf, 'Both are true. Weight, BMI and height measure largely the same physical fact, so the model '
         'shifts credit freely between them and each interval is wide. Collectively they carry the '
         'signal; shuffling weight alone breaks the arrangement.', size=13, color=INK)
takeaway(s, 'A wide interval means "we cannot separate this from its neighbours" — not "this does not matter". That is why both columns are reported.')

# ===========================================================================
# 16. ODDS RATIOS
# ===========================================================================
s = new('Five of 23 predictors reach significance', 'Results — effect sizes')
figure(s, 'fig6_odds_ratios.png', 0.9, 1.8, 8.2)
tf = tb(s, 9.25, 2.0, 3.55, 4.3)
line(tf, 'Entirely conventional', size=15.5, bold=True, color=NAVY, first=True)
line(tf, 'Lighter, older, longer-postmenopausal women with a fracture history and no oestrogen '
         'exposure are at higher risk.', size=13.5, color=INK)
line(tf, 'Nothing here contradicts the osteoporosis literature — which is itself a form of '
         'validation. A pipeline this complicated rediscovering the textbook is evidence it is '
         'wired up correctly.', size=13.5, color=INK)
line(tf, 'Everything else is statistically indistinguishable from no effect at this sample size. '
         'Saying so plainly is more useful than a ranked list of 23 apparent effects.',
     size=13.5, color=INK2, italic=True)
takeaway(s, 'Adjusted odds ratios per clinically meaningful unit, with stratified-bootstrap CIs that carry imputation variability rather than treating imputed values as observed.')

# ===========================================================================
# 17. NULL RESULT
# ===========================================================================
s = new('Calcium and vitamin D: a measured null', 'Results — nutrition')
tf = tb(s, 0.62, 1.9, 12.1, 0.6)
line(tf, 'This is the first thing a bone specialist asks about, so it was measured about as carefully '
         'as this dataset allows — supplements added to a TWO-DAY dietary average, plus a blood level.',
     size=15.5, color=INK, first=True)
rows = [['Predictor', 'Unit', 'Odds ratio', '95% CI', 'Verdict'],
        ['`total_calcium_mg`', 'per 500 mg', '1.01', '0.90 – 1.11', 'no association'],
        ['`total_vitd_mcg`', 'per 10 mcg', '1.01', '0.99 – 1.08', 'no association (+ sign flag)'],
        ['`serum_vitd_nmol`', 'per 25 nmol/L', '0.94', '0.82 – 1.05', 'no association']]
table(s, rows, 0.62, 2.65, 12.1, col_w=[2.9, 2.1, 1.7, 2.3, 3.1], size=13, h=1.45)
tf = tb(s, 0.62, 4.3, 12.1, 2.0)
line(tf, 'Removing all three changes cross-validated AUC by +0.004 — well inside the fold-to-fold '
         'variation of ±0.027, so indistinguishable from no change. I tested this rather than assuming it.',
     size=14.5, color=INK, first=True)
line(tf, 'A null result is not a missing measurement, and the distinction matters: the careful '
         'measurement is precisely what licenses the statement. It is also consistent with the reverse '
         'causation the sign check flagged — women told their bones are thinning start taking vitamin D.',
     size=14.5, color=INK)
line(tf, 'What it does NOT license: any claim about supplementation CHANGING bone density. That needs a '
         'trial, not a cross-sectional survey.', size=14.5, color=CRIT, bold=True)
takeaway(s, 'Question for you: is a well-measured null on calcium and vitamin D in this age band interesting, or already known?')

# ===========================================================================
# 18. CLINICAL TRANSLATION
# ===========================================================================
s = new('What it would buy a clinic', 'Results — clinical translation')
figure(s, 'fig4_scans_per_case.png', 0.9, 1.78, 8.1)
tf = tb(s, 9.2, 1.95, 3.6, 4.4)
line(tf, 'AUC is not a clinical unit', size=15.5, bold=True, color=NAVY, first=True)
line(tf, 'Nobody orders 0.81 of a scan. The only unit that matters is scans ordered per case found.',
     size=13.5, color=INK)
line(tf, 'Osteoporosis, prevalence 6.3%: flagging the top half finds 85% of cases at 9.3 scans per '
         'case instead of 15.8 — a 41% cut in scanning effort, missing 14 of 94 cases.', size=13.5, color=INK)
line(tf, 'Osteopenia, prevalence 56.3%: the gain is small by construction. You cannot do much better '
         'than 1.78 scans per case when half the room is a case.', size=13.5, color=INK2)
takeaway(s, 'Tension to state openly: the nested test says this ranking is not separable from OST — so the claim belongs to "a cheap risk score", not to machine learning specifically.')

# ===========================================================================
# 19. THE SENSITIVITY TRADEOFF
# ===========================================================================
s = new('The uncomfortable arithmetic of high sensitivity', 'Results — thresholds')
tf = tb(s, 0.62, 1.9, 12.1, 0.55)
line(tf, 'A separate, deliberately different forest — shallower, weighted 3:1 toward catching cases, and '
         'sigmoid-calibrated so its probabilities mean what they say. Target: osteopenia or worse.',
     size=15, color=INK, first=True)
rows = [['Probability cutoff', 'Sensitivity', 'Specificity', 'PPV', 'Missed cases', 'Flagged for DXA'],
        ['≥ 0.50', '78.9%', '55.9%', '69.8%', '176', '946  (64%)'],
        ['≥ 0.40', '88.8%', '41.0%', '66.0%', '94', '1,124  (76%)'],
        ['≥ 0.35', '91.3%', '34.4%', '64.2%', '73', '1,188  (80%)'],
        ['≥ 0.30', '94.4%', '27.8%', '62.8%', '47', '1,257  (85%)'],
        ['≥ 0.25', '95.9%', '20.7%', '60.9%', '34', '1,316  (89%)']]
table(s, rows, 0.62, 2.6, 12.1, col_w=[2.2, 1.9, 1.9, 1.6, 2.0, 2.5], size=13, h=2.1)
tf = tb(s, 0.62, 4.9, 12.1, 1.4)
line(tf, 'At 56% prevalence, high sensitivity and useful triage are close to mutually exclusive. Missing only '
         '34 of 836 cases requires scanning 1,316 of 1,484 women — at which point this is not a triage tool, '
         'it is an expensive way of saying "scan almost everyone".', size=15, color=INK, first=True)
line(tf, 'I expect you to spot this immediately. The defensible framing is the osteoporosis target, where '
         'prevalence is 6.3% and there is real scanning effort to save.', size=15, color=INK2, italic=True)
takeaway(s, 'Calibrated forest ROC-AUC 0.764, PR-AUC 0.813 — lower ranking than the leaderboard model, because it was built for honest probabilities instead.')

# ===========================================================================
# 20. OUTPUTS
# ===========================================================================
s = new('What the pipeline produces, and who each file is for', 'Outputs')
tf = tb(s, 0.62, 1.88, 12.1, 0.5)
line(tf, 'Every table is written through one helper that stamps a tier as it writes, so the folder is '
         'self-describing and cannot drift from the code.', size=15, color=INK, first=True)
rows = [['File', 'Tier', 'What it holds and how to read it'],
        ['`nested_cv_verdict.csv`', 'PRESENT', 'The bottom line. One row per clinical threshold with a literal Verdict column: BEATS OST / NOT separable'],
        ['`clinical_predictor_table.csv`', 'PRESENT', 'Adjusted ORs per clinical unit, bootstrap CIs, permutation importance, missingness per predictor'],
        ['`forest_plot_odds_ratios.png`', 'PRESENT', 'The same ORs on a log scale; solid marks exclude 1'],
        ['`referral_table.csv`', 'PRESENT', 'Screening cost both thresholds. Column is "Top fraction flagged" — a quantile, NOT a probability'],
        ['`threshold_sweep.csv`', 'PRESENT', 'Probability cutoffs for the calibrated forest; carries its model and both AUCs on every row'],
        ['`model_leaderboard.csv`', 'PRESENT', 'Five models × test / train / OOB AUC, sensitivity, specificity, full confusion matrix'],
        ['`baseline_comparison.csv`', 'METHODS', 'All ten scores at both thresholds with ΔAUC vs OST and bootstrap intervals'],
        ['`rf_leaf_tuning.csv`', 'METHODS', 'Nested-tuned vs fixed leaf size — the answer to "why leaf = 1 when train AUC is 1.000?"'],
        ['`coefficient_diagnostics.csv`', 'DIAGNOSTIC', 'Leak alarm and sign check. Standardised units, unstable across collinear predictors — NOT findings']]
table(s, rows, 0.62, 2.48, 12.1, col_w=[3.35, 1.5, 7.25], size=10.5, h=3.9)
takeaway(s, 'Thirteen stale files from earlier scripts were removed — one contained the exact tree-importance columns this pipeline dropped for being misleading.', y=6.55)

# ===========================================================================
# 21. PRIOR WORK
# ===========================================================================
s = new('What has already been done in this space', 'Prior work')
rows = [['Study', 'Data', 'Reported', 'How this project differs'],
        ['Stacking ensemble\n(Comput Biol Med, 2025)', 'NHANES 2007–14\nn = 7,924, 50+',
         'AUC 0.94\nacc 93%',
         'Defined cases using T-scores COMBINED WITH anthropometric risk factors — which were also top predictors. Potential circularity in the outcome definition'],
        ['PrOsteoporosis\n(BMC Res Notes, 2025)', 'NHANES\nn = 8,766, 223 vars',
         'RF / NN /\nLGBM / XGB',
         'Feature selection by MRMR + SelectKBest; SMOTE for balance. Authors note important variables lost in cleaning'],
        ['KNHANES calculator\n(BioData Mining, 2026)', 'Korean NHANES\n2008–11',
         'AUC 0.845\nspec 0.897',
         'Closest in spirit — explicitly framed as a high-specificity "rule-in" tool, not a DXA replacement. Includes temporal validation (AUC 0.876)'],
        ['OST (the 1985 benchmark)', 'many cohorts,\nmeta-analysed',
         'AUC 0.71–0.79\nsens 83% spec 63%',
         'Our OST computes to 0.747 / 0.773 — inside the published range, which independently validates our implementation']]
table(s, rows, 0.62, 1.85, 12.1, col_w=[2.75, 2.2, 1.85, 5.3], size=10.5, h=3.5)
tf = tb(s, 0.62, 5.5, 12.1, 0.9)
line(tf, 'The honest read: our 0.810 is LOWER than the headline numbers in this literature. That is the point — '
         'those numbers come from larger samples, broader cohorts, looser outcome definitions, and in at least one '
         'case a label that shares information with its own predictors.', size=14.5, color=INK, first=True)
takeaway(s, 'Almost none of this literature reports a cheap-baseline comparison or nested selection. That gap is the opening.')

# ===========================================================================
# 22. HOW TO STAND OUT
# ===========================================================================
s = new('Where this can genuinely stand out', 'Positioning')
items = [('Methodological honesty as the contribution',
          'Not "we got AUC X" but "here is what survives being checked". Nested CV, a cheap-baseline comparator, '
          'a leakage alarm, a sign check, and a reported null. Reviewers see very little of this.'),
         ('The negative result is the finding',
          'Showing that 23 variables and 500 trees CANNOT beat 0.2 × (weight − age) for osteoporosis is a real, '
          'publishable, decision-relevant claim. It tells clinics not to buy complexity they do not need.'),
         ('Clinical units, not ML units',
          'Scans per case found. Missed cases at each cutoff. That is the language of a referral decision, '
          'and it is what makes a specialist able to critique it.'),
         ('Full reproducibility',
          'One script, one fixed seed, committed input caches, an asserted cohort size. A judge can rerun it. '
          'Very few science-fair projects can say that.')]
for i, (t, b) in enumerate(items):
    x = 0.62 + (i % 2) * 6.2
    y = 1.9 + (i // 2) * 2.2
    box = s.shapes.add_shape(1, Inches(x), Inches(y), Inches(5.9), Inches(1.95))
    box.fill.solid(); box.fill.fore_color.rgb = BAND
    box.line.fill.background(); box.shadow.inherit = False
    tf = box.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.24); tf.margin_top = Inches(0.16)
    line(tf, f'{i+1}.  {t}', size=15, bold=True, color=NAVY, first=True, space_after=4)
    line(tf, b, size=13, color=INK)
takeaway(s, 'The strongest version of this project is not a better AUC. It is a trustworthy answer to "does the complexity pay?"')

# ===========================================================================
# 23. WHAT WOULD STRENGTHEN IT
# ===========================================================================
s = new('What would strengthen it most, in order', 'Next steps')
rows = [['Priority', 'Action', 'Why it moves the needle'],
        ['1', 'External validation on a real clinic cohort',
         'Everything so far is internal CV on one survey. This is the single biggest gap and the thing reviewers ask first. Needs your population'],
        ['2', 'Add a calibration curve',
         'Step 13 depends on probabilities meaning what they say. The plot that demonstrates it is currently missing'],
        ['3', 'Report against TRIPOD+AI (27 items)',
         'The BMJ 2024 reporting standard for prediction models. Adherence in published ML work is still patchy — full compliance is a differentiator'],
        ['4', 'Add the missing established risk factors',
         'Parental hip fracture, height loss, current smoking intensity, weight change since 40 — all established, all absent here'],
        ['5', 'Decision-curve analysis',
         'Moves beyond AUC to net clinical benefit across threshold probabilities — what a guideline committee actually wants'],
        ['6', 'Recover education',
         'Already collected, silently dropped as a string. The cheapest available improvement']]
table(s, rows, 0.62, 1.85, 12.1, col_w=[1.0, 4.0, 7.1], size=11.5, h=3.3)
tf = tb(s, 0.62, 5.35, 12.1, 1.0)
line(tf, 'ISEF note: analysing NHANES falls under the pre-existing publicly-available data exemption — no IRB '
         'pre-approval, no Form 4. Forms 1, 1A and 1B still required. But if YOU supply clinic data, the project '
         'becomes a different category and needs written de-identification certification.', size=14, color=CRIT, first=True, bold=True)
takeaway(s, 'The 2026 ISEF rules added AI/ML requirements for the first time — a stated rationale for the model choice and a data-exclusion plan. Both already exist here.')

# ===========================================================================
# 24. PUBLICATION
# ===========================================================================
s = new('How this could get published', 'Publication path')
for i, (t, b) in enumerate([
    ('Route A — clinical journal, with you as co-author',
     'Target: Osteoporosis International, Archives of Osteoporosis, Journal of Clinical Densitometry, or Bone. '
     'Framing: "Does machine learning add incremental value over OST for DXA triage in women 50–65?" '
     'The negative osteoporosis result and the nested design are the contribution. Requires TRIPOD+AI reporting and, '
     'ideally, external validation. This is the version that carries real weight.'),
    ('Route B — informatics / methods venue',
     'Target: JAMIA Open, JMIR Medical Informatics, or PLOS ONE. Framing: selection bias in small-sample clinical ML — '
     'using this cohort as the worked example where a 0.833 headline becomes 0.806 under nested CV. '
     'Lower clinical bar, faster, still peer-reviewed.'),
    ('Route C — peer-reviewed student journal (do in parallel, not instead)',
     'Journal of Emerging Investigators, STEM Fellowship Journal. Genuine peer review with mentor feedback, '
     'and it establishes precedence while Route A proceeds. Do NOT let this substitute for Route A if a '
     'specialist is willing to co-author.')]):
    y = 1.9 + i * 1.62
    box = s.shapes.add_shape(1, Inches(0.62), Inches(y), Inches(12.1), Inches(1.42))
    box.fill.solid(); box.fill.fore_color.rgb = BAND
    box.line.fill.background(); box.shadow.inherit = False
    tf = box.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.24); tf.margin_top = Inches(0.14)
    line(tf, t, size=15, bold=True, color=NAVY, first=True, space_after=3)
    line(tf, b, size=12.5, color=INK)
takeaway(s, 'Register the analysis plan before external validation. A pre-registered validation of an already-specified model is far stronger than another development study.')

# ===========================================================================
# 25. QUESTIONS FOR THE SPECIALIST
# ===========================================================================
s = new('What I need from you', 'Questions')
tf = tb(s, 0.62, 1.85, 12.1, 0.4)
line(tf, 'Ordered by how much your answer changes the work.', size=15, color=INK2, italic=True, first=True)
qs = [('Is the target right?', 'I predict osteopenia-or-worse (T ≤ −1.0, 56% of the cohort). Is that the clinically useful question, or should the whole project move to T ≤ −2.5 despite only 94 events?'),
      ('What referral cutoff is acceptable?', 'The tables lay out the trade-off, but missed cases per hundred versus scans per case found is a clinical judgement, not one to make from code.'),
      ('Which risk factors do your notes already carry?', 'Parental hip fracture, height loss, weight change since 40, smoking intensity are all established and all absent here. Which are realistically available?'),
      ('Is the calcium / vitamin D null interesting or already known?', 'Well measured, no association, consistent with reverse causation. Worth reporting, or unsurprising?'),
      ('Would you co-author — and can you supply a validation cohort?', 'External validation is the biggest gap. Note that clinic data changes the ISEF category and needs written de-identification.'),
      ('Where would you submit?', 'Osteoporosis International vs a methods venue — and does the negative osteoporosis finding read as a contribution or as a failure to you?')]
for i, (q, b) in enumerate(qs):
    y = 2.3 + i * 0.73
    tf = tb(s, 0.62, y, 12.1, 0.7)
    p = line(tf, f'{i+1}.  {q}  ', size=14.5, bold=True, color=NAVY, first=True, space_after=0)
    r = p.add_run(); r.text = b
    r.font.size, r.font.bold = Pt(13), False
    r.font.color.rgb = INK; r.font.name = BODY_FONT
takeaway(s, 'And the one thing I most want challenged: is a triage tool that flags the top 50% actually usable in your clinic, or is that too many referrals to be worth it?', y=6.75)
notes(s, "Leave time for these. The point of the meeting is their answers, not your slides.")

# ===========================================================================
# 26. LIMITATIONS
# ===========================================================================
s = new('Limitations I would raise before you do', 'Honest limitations')
rows = [['Limitation', 'Why it matters', 'Mitigation / status'],
        ['Outcome is bone density, not fracture', 'NHANES is cross-sectional, no follow-up. This predicts a TEST RESULT, not an event. Not comparable to FRAX', 'Stated everywhere. Not fixable with this dataset'],
        ['56% prevalence is not a clinic', 'Survey sample, not a referral population. Sensitivity/specificity travel; PPV and scans-per-case do NOT', 'Referral tables need recomputing at local prevalence'],
        ['One narrow demographic', 'White women 50–65 only. Nothing generalises outside it', 'Deliberate, to preserve statistical power at n = 1,484'],
        ['Mostly self-reported predictors', 'Fractures, steroids, menopause history, smoking. Only weight, height, 25(OH)D are measured', 'Attenuates real effects — biases toward UNDERstating the ceiling'],
        ['No external validation', 'All internal CV on one dataset', 'Nested CV is the closest honest estimate. Priority 1 above'],
        ['94 osteoporosis events', '4.1 events per predictor, far below the conventional minimum of 10', 'Why that arm is reported as not separable from OST'],
        ['phq9_score 80% missing', 'Median-imputed for four in five women; contributes negatively', 'Should be dropped. Flagged, not hidden']]
table(s, rows, 0.62, 1.85, 12.1, col_w=[3.1, 5.0, 4.0], size=10.5, h=4.4)
takeaway(s, 'Every one of these is already written into the project documentation. I would rather present them than be asked about them.', y=6.5)

# ===========================================================================
# 27. CLOSING
# ===========================================================================
s = prs.slides.add_slide(BLANK)
bg(s, NAVY)
tf = tb(s, 1.0, 1.45, 11.3, 1.1)
line(tf, 'The four-sentence version', size=34, color=WHITE, font=HEAD_FONT, first=True)
tf = tb(s, 1.0, 2.6, 11.3, 3.5)
for t in ['Using six NHANES cycles we assembled 1,484 non-Hispanic White women aged 50–65 who received a hip '
          'DXA scan, and trained models to predict their bone-density category from clinic-available information '
          'alone, with every trace of the scan excluded from the inputs.',
          'A random forest reaches a cross-validated AUC of 0.810 for osteopenia or worse, at 74% sensitivity '
          'and 73% specificity.',
          'Tested honestly — model selection moved inside each training fold — that beats the 1985 two-variable '
          'OST formula by 0.063 AUC, with a confidence interval clear of zero, in every fold.',
          'For osteoporosis specifically we cannot make that claim: the advantage shrinks from +0.060 to +0.031 '
          'once selection bias is removed, and the interval crosses zero, because there are only 94 cases.']:
    line(tf, t, size=16, color=RGBColor(0xcd, 0xe2, 0xfb), space_after=13)
tf = tb(s, 1.0, 6.25, 11.3, 0.8)
line(tf, 'What I want reviewed is not the AUC. It is whether the complexity pays, and what referral '
         'cutoff makes clinical sense.', size=16.5, bold=True, color=WHITE, first=True)

prs.save(OUTP)
print(f'  slides : {len(prs.slides.__iter__.__self__._sldIdLst)}')
print(f'  saved  : {OUTP}')
print(f'  size   : {os.path.getsize(OUTP)/1024:.0f} KB')
