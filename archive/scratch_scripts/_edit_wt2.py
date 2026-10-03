import io

p = 'Notes/project_walkthrough.html'
s = io.open(p, encoding='utf-8').read()
subs = []


def rep(old, new, label):
    global s
    assert old in s, 'NOT FOUND: ' + label
    s = s.replace(old, new)
    subs.append(label)


# --- day-2 recall coverage ---
rep("""does not eliminate it but materially reduces it. On this cohort, 1,369 of the 1,484 women have both
          days, 90 have one, and 25 have neither.</p>""",
    """does not eliminate it but materially reduces it. On this cohort, 1,040 of the 1,111 women have both
          days, 63 have one, and 8 have neither.</p>""",
    'day-2 coverage')

# --- features section heading ---
rep("""        <h2>The 23 things the model may look at</h2>""",
    """        <h2>The 20 things the model may look at</h2>""",
    'features heading')

# --- serum vitamin D coverage ---
rep("""                <td>Measured blood 25(OH)D. Available for 1,142 of 1,484 (23% missing) — the 2017–2020 release ships no vitamin D file at all.</td>""",
    """                <td>Measured blood 25(OH)D. Available for 974 of 1,111 (12% missing) — the 2017–2020 release ships no vitamin D file, so 159 values are crosswalked in from the 2017–2018 release by physical fingerprint.</td>""",
    'serum vitD coverage')

# --- booster regularisation rationale ---
rep("""          <code>reg_lambda=50</code>. With 1,484 rows and 23 columns, an unconstrained booster memorises the""",
    """          <code>reg_lambda=50</code>. With 1,111 rows and 20 columns, an unconstrained booster memorises the""",
    'booster n')

# --- CV split description ---
rep("""      <p>Split the 1,484 women into five groups, keeping the proportion of cases equal in each""",
    """      <p>Split the 1,111 women into five groups, keeping the proportion of cases equal in each""",
    'CV split n')

# --- regularisation aside ---
rep("""          direct consequence of how hard they were regularised. That was the right call for n = 1,484, but it""",
    """          direct consequence of how hard they were regularised. That was the right call for n = 1,111, but it""",
    'regularisation n')

# --- outputs: processed file description ---
rep("""                <td>The analysis table: 1,484 rows, every raw, renamed and derived column — including those""",
    """                <td>The analysis table: 1,111 rows, every raw, renamed and derived column — including those""",
    'processed rows')

# --- six rounds -> five rounds in the meeting lede ---
rep("""      <p class="lede">Using six rounds of NHANES data, we assembled 1,484 non-Hispanic White women aged 50–65""",
    """      <p class="lede">Using five rounds of NHANES data, we assembled 1,111 postmenopausal non-Hispanic White women aged 50–65""",
    'meeting lede n')

rep("""        <dd>To keep the statistical power focused. With 1,484 people, modelling sex, ethnicity and a wide age""",
    """        <dd>To keep the statistical power focused. With 1,111 people, modelling sex, ethnicity and a wide age""",
    'power rationale n')

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('applied:', len(subs))
for x in subs:
    print('  -', x)
