"""Generate the plain-language specialist review document (Word .docx).

Mirrors SpecialistUpdate.docx item by item: quotes the specialist's own wording,
answers each of his inline questions, and lists every clarification we need before
coding. Written for a clinical reader - no machine-learning vocabulary.

    python extra_reading/build_specialist_doc.py

Dependency: python-docx (installed separately; not used by OsteoporosisML.py).
All counts verified against the raw NHANES files on the 1,272 postmenopausal cohort.
"""
import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   'Specialist_Review_Questions.docx')

ACCENT = RGBColor(0x0E, 0x53, 0x60)
MUTED = RGBColor(0x55, 0x5F, 0x6A)
FLAG = RGBColor(0x8A, 0x2E, 0x10)
GOOD = RGBColor(0x1A, 0x5E, 0x40)

doc = Document()
for s in doc.sections:
    s.left_margin = s.right_margin = Inches(0.8)
    s.top_margin = s.bottom_margin = Inches(0.7)

st = doc.styles['Normal']
st.font.name = 'Calibri'
st.font.size = Pt(10.5)
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.line_spacing = 1.08

for name, size, space_before in [('Heading 1', 14.5, 16), ('Heading 2', 11.5, 11)]:
    h = doc.styles[name]
    h.font.name = 'Calibri'
    h.font.size = Pt(size)
    h.font.bold = True
    h.font.color.rgb = ACCENT
    h.paragraph_format.space_before = Pt(space_before)
    h.paragraph_format.space_after = Pt(4)


def para(text='', bold=False, italic=False, size=None, color=None, after=6, align=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    if size:
        r.font.size = Pt(size)
    if color:
        r.font.color.rgb = color
    p.paragraph_format.space_after = Pt(after)
    if align:
        p.alignment = align
    return p


def rich(parts, after=6):
    p = doc.add_paragraph()
    for item in parts:
        r = p.add_run(item[0])
        r.bold = item[1]
        if len(item) > 2 and item[2] is not None:
            r.font.color.rgb = item[2]
        if len(item) > 3 and item[3]:
            r.italic = True
    p.paragraph_format.space_after = Pt(after)
    return p


def quote(text):
    """The specialist's own words."""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run('“' + text + '”')
    r.italic = True
    r.font.size = Pt(10)
    r.font.color.rgb = MUTED
    return p


def bullet(text, head=None):
    p = doc.add_paragraph(style='List Bullet')
    if head:
        p.add_run(head).bold = True
    p.add_run(text)
    p.paragraph_format.space_after = Pt(3)
    return p


def table(headers, rows, widths=None, hs=9, bs=9):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = ''
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(hs)
        r.font.color.rgb = ACCENT
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ''
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            txt = str(val)
            bold = txt.startswith('**') and txt.endswith('**')
            if bold:
                txt = txt[2:-2]
            r = p.add_run(txt)
            r.font.size = Pt(bs)
            r.bold = bold
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def question(tag, title, body_parts):
    p = doc.add_paragraph()
    r = p.add_run('%s. %s' % (tag, title))
    r.bold = True
    r.font.size = Pt(10.5)
    r.font.color.rgb = ACCENT
    p.paragraph_format.space_before = Pt(9)
    p.paragraph_format.space_after = Pt(2)
    rich(body_parts, after=3)
    p2 = doc.add_paragraph()
    p2.paragraph_format.left_indent = Inches(0.25)
    p2.paragraph_format.space_after = Pt(4)
    r2 = p2.add_run('Your answer: ')
    r2.bold = True
    r2.font.size = Pt(10)
    p2.add_run('_' * 62).font.size = Pt(10)


# ============================================================ TITLE
h = doc.add_paragraph()
r = h.add_run('Osteoporosis Risk Without DXA')
r.bold = True
r.font.size = Pt(20)
r.font.color.rgb = ACCENT
h.paragraph_format.space_after = Pt(2)

para('Response to your variable list — what we found, what is ready to code, '
     'and the decisions we need from you', size=11.5, color=MUTED, after=8)
para('NHANES 2005–2020 · non-Hispanic White women aged 50–65 · '
     'every count verified directly against the survey files', size=9, color=MUTED, after=13)

# ============================================================ IN SHORT
doc.add_heading('In short', level=1)
para('We went through all twenty items on your list and checked each one against the raw survey '
     'files, cycle by cycle. Eighteen are usable, one does not exist in this survey at all, and '
     'one exists but is not yet downloaded. Four of your questions have answers, and four of your '
     'assumptions turned out to be wrong — three in our favour.')

rich([('Better than your notes assumed. ', True, GOOD),
      ('Father’s hip fracture, which you asked us to look for, is present in all six cycles. '
       'Steroid duration is recorded for 111 of the 112 women who report steroid use. '
       'The depression questionnaire is not 20% complete as your notes expected but '
       '99.9% — 1,271 of 1,272 women. Sleep is also near-complete. Both of the last two were '
       'faults in our own code, not gaps in the survey, and we have fixed them.', False)])

rich([('Worse than hoped. ', True, FLAG),
      ('Blood vitamin D was never released for the 2017–2020 survey period, so 264 women '
       'cannot have a blood level no matter what we do.', False)])

rich([('One finding contradicts your notes. ', True, FLAG),
      ('Diabetes runs in the opposite direction to what you predicted. We set out the numbers in '
       'Question 8 — it is a real finding, not an error, and it changes what a '
       'diabetes analysis can show.', False)])

rich([('Four things you did not specify. ', True),
      ('Your notes list the predictors but not the outcome, the bone site that defines it, '
       'whether to use the survey’s population weights, or the age and ethnicity limits. '
       'We have carried forward what we did previously, but these need your confirmation — '
       'Questions 1, 2, 11 and 12.', False)], after=10)

# ============================================================ VOCAB
doc.add_heading('Two terms, so the results make sense when they arrive', level=1)
bullet('we report how well a score separates women who do have low bone density from those who '
       'do not. It runs from 0.50, a coin toss, to 1.00, perfect. For reference the OST score — '
       'a published formula using only weight and age — reaches 0.73 in our women. Anything we '
       'build has to beat that to be worth having.',
       head='Accuracy (the c-statistic, sometimes written AUC): ')
bullet('exactly as you asked. For every variable we run the whole analysis twice, once using the '
       'variable and once leaving it out, and report how much accuracy changes. That shows what '
       'each variable contributes, not merely whether it looks statistically significant.',
       head='“With and without”: ')
para('Every score is always tested on women who were not used to build it, so the accuracy figures '
     'are not flattered by the data they came from.', after=10)

# ============================================================ 1. GENERAL INSTRUCTIONS
doc.add_heading('1. Your three general instructions — how each is handled', level=1)

doc.add_heading('a. Keep variables continuous to preserve power', level=2)
quote('Since sample size is small around 1500, using continuous variables preserves statistical '
      'power and avoids arbitrary thresholds.')
rich([('Followed throughout, and your point is now stronger: ', False),
      ('after removing the women still having periods the group is 1,272, not about 1,500.', True),
      (' Age, BMI, years since menopause, activity, calcium, vitamin D, income ratio, sleep and '
       'the depression score all enter the analysis as continuous numbers. Your BMI, calcium and '
       'income-ratio categories are used only for the demographic table, never for the analysis '
       'itself. Sleep is the one exception, because you asked for it both ways — continuous '
       'for the main analysis and in your five bands as a secondary one.', False)])

doc.add_heading('b. Check the distribution of every variable first', level=2)
quote('Also, check the distribution of each variable before doing statistical analysis.')
para('Done — section 4 below gives the figures for every variable. Four of them are heavily '
     'lopsided and will need mathematical rescaling before analysis, which we flag there. '
     'This check will also be produced as a permanent table and a set of histograms with every run.')

doc.add_heading('c. For categorical variables, show the model with and without', level=2)
quote('Categorical – Use the variable with the data and how does the model behave without '
      'using that variable.')
rich([('This is the default for every variable, categorical and continuous alike, since it costs '
       'nothing extra to do both. It will be reported separately for prior fracture, mother’s '
       'hip fracture and father’s hip fracture, so you can see each on its own. ', False),
      ('If you would also like them combined — an “any fracture history” variable, '
       'or “either parent” — we can add those; combining raises the number of '
       'positive answers and steadies the estimate, at the cost of not knowing which relative '
       'mattered.', False)], after=10)

# ============================================================ 2. ITEM BY ITEM
doc.add_heading('2. Your twenty items, one by one', level=1)
para('“Women with data” is out of the 1,272 postmenopausal group. Items marked with a '
     'question number need your decision in section 6.', size=9, color=MUTED, after=6)

table(['#', 'Your item', 'What we have', 'Women with data', 'Status'],
      [['1', 'Age, continuous', 'Years', '1,272 (all)', 'Ready'],
       ['2', 'BMI, continuous', 'kg/m²; your six WHO bands used for the demographic table only',
        '1,271', 'Ready'],
       ['3', 'Years since menopause, continuous',
        'Age now minus age at last period', '1,248', 'Ready — Q3, Q4'],
       ['4', 'Ever used estrogen, yes/no', 'Yes / No — 532 yes', '1,270', 'Ready'],
       ['', '   …and when it was used', '**Duration recorded for 272 of the 532 users (51%)**',
        '272', '**Q5**'],
       ['5', 'Rheumatoid arthritis, yes/no', 'From “which type of arthritis” — 49 yes',
        '1,173', '**Q7**'],
       ['6', 'Diabetes, yes/no', '130 yes', '1,239', '**Q8**'],
       ['7', 'Smoking, yes/no', 'Ever smoked 100 cigarettes — 669 yes', '1,272', 'Ready'],
       ['8', 'Current alcohol, 3 categories',
        'Zero 285 · under 3/day 745 · 3 or more/day 152', '1,182', 'Ready'],
       ['9', 'Prior fracture, yes/no', 'Hip, spine or wrist — 206 yes', '1,272', 'Ready'],
       ['', '   …age at fracture', '**Recorded for 198 of the 206 (96%)**', '198',
        '**Better than your note**'],
       ['10', 'Steroid use, yes/no', 'Ever taken daily — 112 yes', '1,267', 'Ready'],
       ['', '   …duration', '**Recorded for 111 of the 112 users**', '**111**',
        '**Better than your note**'],
       ['11', 'Activity converted to MET', 'MET-minutes/week by the published method', '1,095',
        'Ready — Q6'],
       ['', '   Moderate activity, min/week', 'Secondary, as you asked', '1,096', 'Ready'],
       ['', '   Vigorous activity, min/week', 'Secondary, as you asked', '1,097', 'Ready'],
       ['', '   Sitting time, hours/day', 'The “potentially” item', '1,095', 'Ready'],
       ['12', 'Calcium, diet + supplement', 'mg/day; your four bands for the table', '1,090',
        'Ready'],
       ['13', 'Vitamin D intake, IU/day', 'Converted from micrograms', '1,090', '**Q9**'],
       ['14', 'Blood 25-hydroxy vitamin D, ng/mL', 'Converted from nmol/L', '**974**', '**Q9**'],
       ['15', 'Poverty income ratio', 'Your three bands for the table', '1,208', 'Ready'],
       ['16', 'Mother hip fracture, yes/no', '149 yes', '1,247', 'Ready'],
       ['16a', '**Father hip fracture — you asked us to search**',
        '**Yes / No — 53 yes. Present in all six cycles**', '**1,213**', '**Found — Q10**'],
       ['17', 'Depression score (PHQ-9)',
        '**Not 20% as expected — 99.9%. Total score; 127 women score 10 or more**',
        '**1,271**', '**Q6 — no longer a subset**'],
       ['18', 'Antidepressant medication — you asked us to search',
        'Exists in the survey; not yet downloaded', '—', 'Proposed for later'],
       ['19', 'Falls or fall risk — you asked us to search',
        '**No question on falls or balance in any of our six cycles**', '—',
        '**Not available**'],
       ['20', 'Sleep, continuous + categorical',
        'Hours/night; your five bands as the secondary analysis', '**1,267**', 'Ready']],
      widths=[0.32, 1.55, 2.45, 0.78, 1.25], hs=8.5, bs=8.5)

rich([('One extra variable you did not ask for, worth considering. ', True),
      ('The survey asks whether any blood relative has been told they have osteoporosis. '
       'It was asked of all 1,272 women with no missing answers, and 365 say yes (28.7%) — '
       '348 naming the mother, 37 the father. That is six times more common than father’s hip '
       'fracture and has no missing data, so it would be a considerably steadier predictor. '
       'See Question 10.', False)], after=10)

# ============================================================ 3. HIS QUESTIONS
doc.add_heading('3. Your specific questions, answered', level=1)

doc.add_heading('Do we have information about when estrogen was used?', level=2)
quote('4. Ever used Estrogen: Yes or No - categorical (question: do we have info about when '
      'estrogen was used?)')
rich([('Partly. ', True),
      ('Of the 532 women who report ever using hormones, ', False),
      ('272 (51%) have a usable duration', True),
      (' — a number of months or years. We do not have a reliable age at which they started. '
       'So we can build “years of hormone use” for about half of users, but not '
       '“how long ago they stopped”. Question 5 asks how you want this handled.', False)])

doc.add_heading('Age at prior fracture — known in only 224 subjects?', level=2)
quote('9. Prior fracture: Yes or No - categorical (limitation as the age of fracture is known in '
      'only 224 subjects)')
rich([('Slightly different in our group, and better than your note suggests. ', True),
      ('In the 1,272 postmenopausal women, ', False),
      ('206 report a hip, spine or wrist fracture, and 198 of those (96%) have an age recorded',
       True),
      ('. So the limitation is not that age is missing — it is that only 206 women have a '
       'fracture at all, and without a description of how it happened we cannot separate a '
       'fragility fracture from an accident. Your 224 figure presumably came from the larger '
       '1,484 group before the menopause filter.', False)])

doc.add_heading('Steroid use — is age and duration unknown?', level=2)
quote('10. Steroid use: Yes or No - categorical (limitation as the age and duration of steroid '
      'use in unknown)')
rich([('Duration is available. ', True, GOOD),
      ('Of the 112 women reporting ever taking daily steroids, ', False),
      ('111 have a duration recorded', True),
      (' as a number of months or years. What is genuinely missing is the ', False),
      ('dose', True),
      (' and the age at which they started — neither is ever asked. So we can offer '
       '“length of steroid exposure” as a continuous variable if you want it.', False)])

doc.add_heading('Is there data on antidepressant medication?', level=2)
quote('18. Search to see if they have data on antidepressant medication use.')
para('Yes, the survey records prescription medications including antidepressants, but those files '
     'are not downloaded and using them needs a drug-name-to-class mapping built and checked. '
     'We propose leaving this for a later round rather than delaying the main analysis, unless '
     'you consider it essential now.')

doc.add_heading('Is there data on falls or fall risk?', level=2)
quote('19. Search to see if they have data on falls or fall risk')
rich([('No. ', True, FLAG),
      ('There is no question about falls or balance in any of the six survey periods we use. '
       'The nearest substitute would be questions on difficulty walking or standing from a chair, '
       'but those are also absent for 2017–2020, which is 264 of our women. '
       'We propose recording this as a limitation rather than using a poor proxy.', False)])

doc.add_heading('Your three references', level=2)
para('We checked two of the three. Both confirm the activity calculation we plan to use: 8 METs for '
     'vigorous work and vigorous recreation, 4 METs for moderate work, moderate recreation and '
     'walking or cycling for transport, multiplied by minutes per day and days per week and summed. '
     'Both report MET-hours per week rather than MET-minutes, so we will give both. The third '
     'reference (PubMed 37454096) is behind a login — please send the PDF if you would like it '
     'checked too.', after=10)

# ============================================================ 4. DISTRIBUTIONS
doc.add_heading('4. Distribution of every variable, as you asked', level=1)
para('Middle value is the median; average is the mean. Where the two differ widely the variable is '
     'lopsided and needs rescaling before analysis — flagged in the last column.',
     size=9, color=MUTED, after=6)

table(['Variable', 'Average', 'Middle value', 'Shape'],
      [['Age, years', '58.3', '59.0', 'Even'],
       ['BMI, kg/m²', '28.9', '28.0', 'Even'],
       ['Years since menopause', '12.3', '10.0', 'Mildly skewed'],
       ['Poverty income ratio', '3.2', '3.4', 'Even'],
       ['Sleep, hours/night', '7.2', '7.0', 'Even'],
       ['Depression score (PHQ-9)', '3.9', '2.0', 'Skewed — rescale'],
       ['Calcium, mg/day', '1,168', '1,028', 'Skewed — rescale'],
       ['Blood vitamin D, ng/mL', '30.9', '29.8', 'Mildly skewed'],
       ['**Vitamin D intake, IU/day**', '**996**', '**439**',
        '**Very heavily skewed — must rescale**'],
       ['**Activity, MET-min/week**', '**2,456**', '**720**',
        '**Very heavily skewed; 27% report none**'],
       ['Moderate activity, min/week', '388', '150', 'Heavily skewed; 29% none'],
       ['**Vigorous activity, min/week**', '**113**', '**0**',
        '**76% report none — may be better as yes/no**'],
       ['Sitting, hours/day', '6.4', '6.0', 'Even']],
      widths=[2.3, 1.0, 1.1, 2.3], bs=8.5)

para('The two most extreme are vitamin D intake, where the average is more than twice the middle '
     'value, and vigorous activity, where three quarters of women report none at all. For vigorous '
     'activity we would suggest treating it as yes/no rather than as a quantity — please say '
     'if you disagree.', after=8)

doc.add_heading('Your categories, populated', level=2)
table(['BMI', 'n', 'Calcium mg/day', 'n', 'Income ratio', 'n', 'Sleep', 'n'],
      [['Under 18.5', '18', 'Under 600', '184', 'Under 1', '165', '5 h or less', '120'],
       ['18.5–24.9', '368', '600–999', '348', '1 to under 3', '383', '6 h', '219'],
       ['25.0–29.9', '379', '1,000–1,199', '126', '3 and over', '660',
        '**7–8 h (reference)**', '**745**'],
       ['30.0–34.9', '281', '1,200 and over', '432', '', '', '9 h', '108'],
       ['35.0–39.9', '147', '', '', '', '', '10 h or more', '75'],
       ['40 and over', '78', '', '', '', '', '', '']],
      widths=[1.05, 0.45, 1.25, 0.45, 1.1, 0.45, 1.25, 0.45], hs=8, bs=8)
para('Every band has usable numbers; none needs collapsing.', size=9, color=MUTED, after=10)

# ============================================================ 5. MISSING VALUES
doc.add_heading('5. What value we would use when an answer is absent', level=1)
rich([('This is the table we most need you to review. ', True),
      ('Where only a few answers are absent we propose filling the gap so that no woman is dropped '
       'from the analysis. The column “value we would insert” shows exactly what each of '
       'those women would be given — please tell us if any of them is clinically '
       'unreasonable, and whether you prefer the average or the middle value. '
       'The two differ materially only for activity, vitamin D intake and the depression score.',
       False)])

table(['Variable', 'Answers absent', 'Value we would insert', 'Average, for comparison'],
      [['Age', '0', 'not needed', '—'],
       ['Smoking', '0', 'not needed', '—'],
       ['Prior fracture', '0', 'not needed', '—'],
       ['BMI', '1', '28.0 kg/m²', '28.9'],
       ['Depression score (PHQ-9)', '1', '2 points', '3.9'],
       ['Ever used estrogen', '2', 'No (58% answer No)', '—'],
       ['Sleep', '5', '7.0 hours', '7.2'],
       ['Steroid use', '5', 'No (91% answer No)', '—'],
       ['Years since menopause', '24', '10.0 years', '12.3'],
       ['Mother hip fracture', '25', 'No (88% answer No)', '—'],
       ['Diabetes', '33', 'No (90%) — but see Q8', '—'],
       ['Father hip fracture', '59', 'No (96% answer No)', '—'],
       ['Poverty income ratio', '64', '3.4', '3.2'],
       ['Alcohol', '90', 'under 3/day (63% of answers)', '—'],
       ['Rheumatoid arthritis', '99', 'No (96%) — but see Q7', '—']],
      widths=[2.0, 1.0, 2.2, 1.4], bs=8.5)

rich([('For four variables we propose inserting nothing at all, ', True),
      ('because the gap is not a few individual non-answers but an entire survey period that never '
       'collected the measurement. Filling those would mean inventing one survey period’s '
       'values from women interviewed years earlier or later.', False)])

table(['Variable', 'Answers absent', 'Why', 'What we would do instead'],
      [['Activity (all four measures)', '175–177',
        '173 of them are every woman in 2005–06, which used a different, incompatible '
        'activity questionnaire',
        'Report activity analyses on the 1,099 women who have it'],
       ['Calcium', '182', 'Same 173 women — no supplement questionnaire exists for '
                          '2005–06',
        'Report on the 1,090 who have it'],
       ['Vitamin D intake', '182', 'Same 173 women', 'Report on the 1,090 who have it'],
       ['**Blood vitamin D**', '**298**',
        '**264 of them are every woman in 2017–2020, for whom the laboratory file was never '
        'released**',
        '**Report on the 974 who have it, as in Q9**']],
      widths=[1.7, 0.85, 2.5, 1.55], bs=8.5)
para('Full figures are also in the accompanying file imputation_values.csv.',
     size=9, color=MUTED, after=10)

# ============================================================ 6. QUESTIONS
doc.add_heading('6. Decisions we need from you', level=1)
para('Everything else is specified and ready to code. These twelve change what we build.',
     after=4)

question('Q1', 'What is the outcome we are predicting?',
         [('Your notes list the predictors but not the outcome. We have previously reported two: '
           'low bone mass or worse (T-score −1.0 or below), which applies to 751 of the 1,272 '
           'women, and osteoporosis (T-score −2.5 or below), which applies to 91. We can also '
           'predict the T-score itself as a number. We propose keeping all three. '
           'Please confirm which is the primary result.', False)])

question('Q2', 'Which bone site defines the T-score?',
         [('We currently take the lower of the femoral neck and the total hip. The choice matters:',
           False)])
table(['Definition', 'T −1.0 or below', 'T −2.5 or below'],
      [['Femoral neck only', '722', '81'],
       ['Total hip only', '495', '43'],
       ['**Lower of the two (what we do now)**', '**751**', '**91**']],
      widths=[3.0, 1.5, 1.5], bs=8.5)
para('Both measurements are available for all 1,272 women, so this is purely a definitional '
     'choice. Taking the lower of available sites follows the usual reporting convention, but '
     'many published NHANES papers use the femoral neck alone. Please confirm which you want.',
     after=4)
p = doc.add_paragraph()
p.paragraph_format.left_indent = Inches(0.25)
p.paragraph_format.space_after = Pt(4)
p.add_run('Your answer: ').bold = True
p.add_run('_' * 62)

question('Q3', 'Is 1,272 the group we report?',
         [('You asked us to remove anyone with a cycle in the last twelve months. That removes '
           '170 women who reported a period, and a further 42 whose menopausal status cannot be '
           'determined at all — they are blank on the period question, hysterectomy, ovary '
           'removal and age at last period alike. That leaves ', False),
          ('1,272 women, with 751 at T −1.0 or below (59.0%) and 91 at −2.5 or below '
           '(7.2%)', True),
          ('. The excluded 170 are genuinely different: median age 52 against 59, 63% of them '
           'aged 50–52, mean T-score −0.488 against −1.162, and only 2 cases of '
           'osteoporosis between all of them. Critically, ', False),
          ('not one of the 170 has a recorded age at last menstrual period', True),
          (' — zero out of 170 — so years since menopause does not exist for them. '
           'Keeping them would mean assigning a menopause date to women who have not reached '
           'menopause. We also cannot tell perimenopausal from premenopausal within those 170, '
           'because this survey has no question on cycle regularity in any of our six periods; '
           'we propose calling them “not yet postmenopausal” and describing them as an '
           'excluded group in the demographic table. Please confirm 1,272.', False)])

question('Q4', 'Do you also want the analysis repeated on all 1,484? And how should years since '
               'menopause be defined after hysterectomy?',
         [('Two parts. ', True),
          ('First: we can repeat everything including the 212 excluded women, but it needs care, '
           'because adding them makes the group easier to sort quite apart from anything we do. '
           'Scoring both groups on age alone, with nothing fitted, accuracy rises from 0.555 to '
           '0.588; the OST formula rises from 0.733 to 0.747. A higher figure on 1,484 would '
           'therefore reflect an easier mix of patients, not a better score. If you want it, we '
           'would build the score on all 1,484 but measure it on the same 1,272 women, so only the '
           'information used differs and not the patients judged. ', False),
          ('Second: of the 1,272, 460 report a hysterectomy and 206 removal of the ovaries. '
           'Our date comes from age at last menstrual period, which after a hysterectomy is the '
           'operation. If the ovaries were kept, estrogen continued afterwards, so the figure '
           'overstates true estrogen-deficient years — the quantity that actually drives bone '
           'loss. Should we define years since menopause for natural menopause only and carry '
           'surgical menopause as a separate marker, or compute it for everyone and state the '
           'limitation?', False)])

question('Q5', 'How much detail do you want on estrogen use?',
         [('We have yes/no for 1,270 women and a usable duration for 272 of the 532 users (51%). '
           'Options: keep yes/no only, which is complete; add duration, which is richer but '
           'available for only half of users; or both, with duration as a secondary analysis. '
           'We suggest the third.', False)])

question('Q6', 'The depression score is far more complete than your notes assumed — '
               'do you still want it as a subset analysis only?',
         [('Your note says ', False),
          ('“PHQ9 – Subset analysis only as 20% data available”', False, None, True),
          ('. That was our error, not the survey’s: the nine questions are stored as words '
           'rather than numbers in five of the six periods, and our code was reading only the '
           'numbers. Corrected, ', False),
          ('the score is available for 1,271 of 1,272 women, and 127 (10.0%) score 10 or above',
           True),
          (', the usual threshold for probable depression. It can now be a full predictor rather '
           'than a subset analysis. Do you want it in the main analysis, and would you also like '
           'the 10-or-above threshold as a yes/no variable alongside the score?', False)])

question('Q7', 'Rheumatoid arthritis — predictor, or description only?',
         [('Two problems. ', True),
          ('Only 49 of the 1,272 women have rheumatoid arthritis, and the 2009–10 survey does '
           'not ask which type of arthritis at all, so 98 women who report arthritis in that '
           'period cannot be classified either way. Against 91 cases of osteoporosis, an estimate '
           'built on 49 affected women will be very uncertain. It is also self-reported rather '
           'than confirmed by blood tests. Options: keep it as a predictor with an explicit '
           '“unknown” category for those 98 women, accepting wide uncertainty; or report '
           'it in the demographic table only. We would rather you chose than we assumed.', False)])

question('Q8', 'Diabetes runs opposite to your prediction — does our proposed approach match '
               'what you want?',
         [('Your note treats diabetes as a risk factor for lower bone density. ', False),
          ('In our women it goes the other way: mean T-score −0.807 in diabetics against '
           '−1.211 in non-diabetics, and 5.4% osteoporosis against 7.5%.', True),
          (' The explanation is body weight — diabetic women here average 5.7 kg/m² more '
           'BMI, and ', False),
          ('once age and BMI are accounted for, diabetes has no independent relationship with '
           'T-score at all', True),
          (' (p = 0.79). This matches the recognised type-2 picture of normal or high bone density '
           'alongside raised fracture risk, which a DXA T-score cannot show; and this survey does '
           'not distinguish type 1 from type 2. There is also a hard limit: ', False),
          ('the diabetic group contains only 7 cases of osteoporosis', True),
          (', far too few to build a separate score on. We propose describing the two groups '
           'side by side, testing whether diabetes changes the effect of BMI, and building the '
           'score in non-diabetic women (1,109 women, 83 cases), with the diabetic group reported '
           'for the lower threshold only and clearly marked as underpowered. Does that match what '
           'you want?', False)])

question('Q9', 'Vitamin D — blood level or dietary intake?',
         [('You said to use one or the other and never both, and preferred the blood level. '
           'The blood level is available for 974 women; intake for 1,090. We propose the blood '
           'level as the primary measure, with intake run separately for comparison and never in '
           'the same score. Note that 264 of the 298 women without a blood level are every woman '
           'in 2017–2020, for whom the laboratory file was never released, so that gap cannot '
           'be closed. Please confirm.', False)])

question('Q10', 'Family history — how much do you want?',
         [('Father’s hip fracture is available as you hoped, with 53 positive answers out of '
           '1,213. We can also offer: ', False),
          ('family history of osteoporosis, which is complete for all 1,272 women with 365 '
           'positive answers (28.7%)', True),
          ('; parental fracture before age 50, since the parent’s age is recorded for 147 of '
           '149 mothers and all 53 fathers; and a combined “either parent” variable. '
           'Which of these would you like included?', False)])

question('Q11', 'Should we use the survey’s population weights?',
         [('NHANES is a weighted survey. Applying its weights makes the results represent the '
           'US population; not applying them describes only the women actually sampled. '
           'Our previous analysis did not use them. The weights are available for all six periods. '
           'One of your own references applied them. This affects how we may describe the findings, '
           'so we would like your view — our suggestion is unweighted for the prediction '
           'work, since the goal is to rank individual patients rather than estimate population '
           'prevalence, with the demographic table shown both ways.', False)])

question('Q12', 'Confirm the inclusion limits',
         [('The group is restricted to non-Hispanic White women aged 50 to 65 with a hip DXA scan. '
           'Your notes do not mention these limits, and they were carried over from our earlier '
           'work. The narrow definition reduces confounding by ethnicity but means the findings '
           'cannot be generalised beyond that group. Please confirm you are happy with it, or tell '
           'us what to change.', False)])

# ============================================================ 7. LIMITATIONS
doc.add_heading('7. Limitations, stated plainly', level=1)
para('These travel with the results. None prevents us proceeding, but each limits what we may '
     'claim.', after=4)

table(['Variable', 'Limitation'],
      [['**Falls**', '**No question on falls or balance exists in any of our six survey periods. '
                      'Not obtainable.**'],
       ['Antidepressants', 'Obtainable but not downloaded; proposed for a later round.'],
       ['**Blood vitamin D**',
        '**Never released for 2017–2020, so 264 women can never have a value. A single '
        'reading also varies with season and sun exposure, so it is an imperfect measure of '
        'long-term status — as your notes observed.**'],
       ['Activity', 'The 2005–06 survey used a different, incompatible activity '
                    'questionnaire, so 173 women cannot be scored at all. All activity is '
                    'self-reported, and reported minutes are known to be overstated.'],
       ['Rheumatoid arthritis', 'Only 49 affected women. The 2009–10 survey does not ask '
                                'which type of arthritis, leaving 98 women unclassifiable. '
                                'Self-reported, not confirmed serologically.'],
       ['Diabetes', 'Type 1 and type 2 are not distinguished. The relationship with T-score is '
                    'entirely explained by body weight. Only 7 osteoporosis cases among '
                    'diabetics.'],
       ['Prior fracture', 'Only 206 women have one, and the survey never records how it happened, '
                          'so fragility fractures cannot be separated from accidents. Age is '
                          'recorded for 198 of the 206.'],
       ['Steroid use', 'Dose is never recorded, nor the age at which use started. Duration is '
                       'available for 111 of the 112 users.'],
       ['Estrogen use', 'Duration available for only 272 of 532 users; no reliable age at start.'],
       ['Years since menopause', '460 women report a hysterectomy and 206 removal of the ovaries, '
                                 'for whom the date reflects surgery rather than ovarian failure.'],
       ['Alcohol', 'The survey changed its alcohol questions in 2017. The drinks figure is per '
                   'drinking day, not averaged across the week.'],
       ['Father hip fracture', '59 women answered “don’t know”, and only 53 are '
                               'positive. Paternal history is recalled less reliably than '
                               'maternal.'],
       ['Calcium', 'A two-day diet average plus supplements, so it reflects recent rather than '
                   'lifetime intake. No supplement questionnaire exists for 2005–06.'],
       ['Sleep', 'Recorded in whole hours before 2017 and half hours afterwards. Self-reported.'],
       ['Depression', 'A screening questionnaire, not a diagnosis. Low mood may as easily follow '
                      'from poor health as contribute to it.'],
       ['Income ratio', 'A household measure used as a proxy for individual circumstances.'],
       ['**The study overall**',
        '**Non-Hispanic White women aged 50–65 only, so findings do not generalise beyond '
        'that group. Everything is measured at a single point in time with no follow-up, so we '
        'can predict low bone density but can make no claim whatever about future fractures. '
        'With 91 osteoporosis cases and around 19 variables, estimates for uncommon variables '
        'will be uncertain.**']],
      widths=[1.55, 4.85], bs=8.5)

# ============================================================ 8. NEXT
doc.add_heading('8. What happens once you have answered', level=1)
para('We rewrite the analysis around your list and produce, for every variable and each of our '
     'eight scoring approaches, the accuracy with that variable and without it — so you can '
     'see exactly what each one contributes. Alongside that: the demographic table in your '
     'categories, the distribution check on every variable before any analysis is run, and this '
     'limitations list as a table that travels with the results.')
para('The three questions that most change the work are Q1 and Q2, which define what we are '
     'predicting, and Q3, which fixes the group. The rest can be answered in any order.')

para('Prepared in response to your SpecialistUpdate notes. Every count verified directly against '
     'the NHANES files and reproducible from the analysis code.',
     size=8.5, color=MUTED, after=0)

doc.save(OUT)
print('wrote %s' % OUT)
