import io

p = 'Notes/project_walkthrough.html'
s = io.open(p, encoding='utf-8').read()
subs = []


def rep(old, new, label):
    global s
    assert old in s, 'NOT FOUND: ' + label
    assert s.count(old) == 1, 'NOT UNIQUE (%d): %s' % (s.count(old), label)
    s = s.replace(old, new)
    subs.append(label)


# ---------- feature selection: exclusion -> allowlist ----------
rep("""      <p>In code, that wall is the <code>exclude</code> list inside <code>define_features</code>. It names
        <code>femoral_neck_bmd</code>, <code>total_hip_bmd</code>, <code>t_femoral_neck</code>,
        <code>t_total_hip</code>, <code>t_score</code>, <code>bone_status</code>, <code>at_risk</code> and
        <code>osteoporosis</code> — every column that carries any trace of the scan.</p>

      <div class="note caution">
        <span class="note-label">A design decision worth knowing about</span>
        <p>Feature selection here works by <em>exclusion</em>, not inclusion: the code takes every column in
          the table and removes the ones on the blocklist. That is convenient — a newly engineered variable
          is picked up automatically with no extra wiring — but it cuts the other way too. Any future column
          derived from bone density silently becomes an input unless someone remembers to add it to the list.
          This is why the script carries a standing leak alarm; see
          <a href="#guards">Six ways of cheating, guarded</a>.</p>
      </div>""",
    """      <p>In code, that wall used to be an <code>exclude</code> list: a blocklist naming
        <code>femoral_neck_bmd</code>, <code>total_hip_bmd</code>, <code>t_femoral_neck</code>,
        <code>t_total_hip</code>, <code>t_score</code>, <code>bone_status</code>, <code>at_risk</code> and
        <code>osteoporosis</code>. <strong>The rewrite inverted it.</strong> <code>FEATURE_PANEL</code> is now
        an <em>allowlist</em>: eighteen named source variables, and nothing else can reach a model no matter
        what else the table happens to contain.</p>

      <div class="note caution">
        <span class="note-label">Why the direction matters</span>
        <p>A blocklist is convenient — a newly engineered variable is picked up automatically with no extra
          wiring — but it fails in the dangerous direction. Any future column derived from bone density
          silently becomes an input unless someone remembers to add it to the list, and the failure is
          invisible: the model simply gets better. An allowlist fails in the safe direction instead. A new
          column is ignored until someone writes its name down, so the worst outcome is a variable you meant
          to use sitting idle, not the scan leaking into the thing that is supposed to replace it. The
          standing leak alarm is still there as a second line; see
          <a href="#guards">Seven ways of cheating, guarded</a>.</p>
      </div>""",
    'allowlist inversion')

rep("""      <p>Because features are chosen by exclusion, a new column derived from bone density would silently""",
    """      <p>Under the old blocklist, a new column derived from bone density would silently""",
    'guards exclusion sentence')

rep("""              <tr><td><code>education</code></td><td>Not an explicit exclusion — it survives as text and is then swept up by the blanket drop of non-numeric columns. An accidental omission rather than a decision.</td></tr>""",
    """              <tr><td><code>education</code></td><td>Under the old blocklist this was an <em>accident</em>: it survived as text and was then swept up by a blanket drop of non-numeric columns, so nobody ever decided to leave it out. Under the allowlist it is simply not on the panel — the same outcome, now as a recorded choice.</td></tr>""",
    'education note')

# ---------- outcome counts ----------
rep("""          <dt>at_risk — T ≤ −1.0</dt>
          <dd>836 <small>56.3% of the cohort. Osteopenia <em>or worse</em>. This is the primary target.</small></dd>""",
    """          <dt>at_risk — T ≤ −1.0</dt>
          <dd>645 <small>58.1% of the cohort. Osteopenia <em>or worse</em>. This is the primary target.</small></dd>""",
    'at_risk count')

rep("""          <dt>osteoporosis — T ≤ −2.5</dt>
          <dd>94 <small>6.3%. The WHO diagnostic threshold. A secondary target, evaluated separately.</small></dd>""",
    """          <dt>osteoporosis — T ≤ −2.5</dt>
          <dd>76 <small>6.8%. The WHO diagnostic threshold. A secondary target, evaluated separately.</small></dd>""",
    'osteoporosis count')

rep("""          <dd>−1.08 <small>mean, with SD 1.02 — the cohort average sits right at the osteopenia line.</small></dd>""",
    """          <dd>−1.14 <small>mean, with SD 0.98 — the cohort average sits just past the osteopenia line.</small></dd>""",
    'tscore distribution')

rep("""        <p>The primary target is <strong>not osteoporosis</strong>. It is osteopenia-or-worse, which describes
          <strong>56.3%</strong> of this cohort — more than half. A model that predicts it well is answering
          "does this woman have any measurable bone loss", not "does this woman have osteoporosis". The
          osteoporosis-only target has just 94 cases against 23 predictors — about 4 events per predictor,
          well under the conventional minimum of 10 — so anything estimated on that target alone is fragile.
          The script evaluates both and reports them side by side rather than picking the flattering one.</p>""",
    """        <p>The primary target is <strong>not osteoporosis</strong>. It is osteopenia-or-worse, which describes
          <strong>58.1%</strong> of this cohort — more than half. A model that predicts it well is answering
          "does this woman have any measurable bone loss", not "does this woman have osteoporosis". The
          osteoporosis-only target has just 76 cases against 20 model columns — 3.8 events per predictor,
          well under the conventional minimum of 10 — so anything estimated on that target alone is fragile.
          The rewrite made that arithmetic a gate rather than a footnote: <code>power_gate.csv</code> computes
          events per predictor for every analysis before it runs and labels this target
          <strong>UNDERPOWERED</strong> in the output itself. The script still evaluates both targets and
          reports them side by side rather than picking the flattering one.</p>""",
    'target caution')

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('applied:', len(subs))
for x in subs:
    print('  -', x)
