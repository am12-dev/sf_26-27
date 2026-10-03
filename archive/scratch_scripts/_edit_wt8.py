# -*- coding: utf-8 -*-
import io

p = 'Notes/project_walkthrough.html'
s = io.open(p, encoding='utf-8').read()


def swap(old, new, label):
    global s
    assert s.count(old) == 1, 'count %d for %s' % (s.count(old), label)
    s = s.replace(old, new)
    print('  ok', label)


def region(a, b, new, label):
    global s
    i = s.index(a)
    j = s.index(b, i) + len(b)
    s = s[:i] + new + s[j:]
    print('  ok', label)


swap("""      <p>An AUC of 0.810 sounds respectable. Two questions decide whether it means anything, and roughly half
        the script's length exists to answer them.</p>""",
     """      <p>An AUC of 0.755 sounds respectable. Three questions decide whether it means anything, and roughly
        half the script's length exists to answer them. On the corrected cohort, all three answers come back
        against the project's original claim.</p>""",
     'honesty lede')

swap("""      <p>Reporting a bare AUC without that comparison would be uninterpretable. A model that scores 0.81
        while OST scores 0.80 has added a great deal of complexity for nothing.</p>""",
     """      <p>Reporting a bare AUC without that comparison would be uninterpretable. A model that scores 0.755
        while OST scores 0.739 has added a great deal of complexity for very little — which, as it turns
        out, is precisely the situation.</p>""",
     'OST comparison line')

swap("""          <text class="svg-t" x="798" y="61" text-anchor="middle">best AUC 0.810</text>""",
     """          <text class="svg-t" x="798" y="61" text-anchor="middle">best AUC 0.755</text>""",
     'svg leaderboard label')

swap("""      <p>Both the <code>at_risk</code> and the <code>osteoporosis</code> targets go through this whole
        apparatus, and the script ends with an explicit verdict for each — "beats OST" only if the nested
        95% confidence interval on the difference excludes zero. Its own closing words:
        <em>"the nested row is the defensible number."</em></p>""",
     """      <p>Both the <code>at_risk</code> and the <code>osteoporosis</code> targets go through this whole
        apparatus, and the script ends with an explicit verdict for each — "beats OST" only if the nested
        95% confidence interval on the difference excludes zero. Its own closing words:
        <em>"the nested row is the defensible number."</em></p>

      <h3>Question three: were these the same women twice?</h3>

      <p>This question was not asked in the original project, and it is the one that mattered most. It is
        <a href="#guards">guard 1</a> in full: NHANES re-numbered every SEQN when it built the pre-pandemic
        file, so loading both the 2017–2018 cycle and the pooled 2017–2020 release put 176 women in the
        cohort twice under IDs no deduplication could match. Cross-validation splits rows, not people, so
        those women trained and tested the same model simultaneously.</p>

      <p>The rewrite now measures the cost rather than asserting it. <code>auc_decomposition.csv</code> reruns
        the entire pipeline at four cohort definitions, changing one thing at a time:</p>

      <div class="bleed">
        <div class="tbl-wrap">
          <table>
            <thead><tr><th>Stage</th><th class="num">n</th><th class="num">Events</th><th class="num">Best AUC</th><th class="num">OST</th><th class="num">Δ vs OST</th></tr></thead>
            <tbody>
              <tr><td><strong>A.</strong> 6 cycles, all DXA <span style="color:var(--ink-3)">(as published)</span></td><td class="num">1,484</td><td class="num">836</td><td class="num">0.840</td><td class="num">0.747</td><td class="num">+0.093 <span style="font-size:12px">[+0.075, +0.113]</span></td></tr>
              <tr><td><strong>B.</strong> 6 cycles, postmenopausal only</td><td class="num">1,272</td><td class="num">751</td><td class="num">0.837</td><td class="num">0.733</td><td class="num">+0.104 <span style="font-size:12px">[+0.081, +0.126]</span></td></tr>
              <tr><td><strong>C.</strong> 5 cycles, all DXA <span style="color:var(--ink-3)">(duplicates removed)</span></td><td class="num">1,308</td><td class="num">724</td><td class="num">0.766</td><td class="num">0.753</td><td class="num">+0.013 <span style="font-size:12px">[−0.001, +0.026]</span></td></tr>
              <tr class="row-hi"><td><strong>D.</strong> 5 cycles, postmenopausal <span style="color:var(--ink-3)">(shipped)</span></td><td class="num">1,111</td><td class="num">645</td><td class="num">0.757</td><td class="num">0.739</td><td class="num">+0.018 <span style="font-size:12px">[+0.001, +0.034]</span></td></tr>
            </tbody>
          </table>
        </div>
        <caption>All four stages run the <em>rebuilt</em> feature panel, so the only thing changing down the
          column is the cohort. Stage A therefore scores 0.840 rather than the published 0.810 — the rebuilt
          panel is slightly better on the duplicated cohort too, which is why A-vs-C is the valid subtraction
          and A-vs-published is not.</caption>
      </div>

      <p><strong>The arithmetic is unambiguous.</strong> The duplicate fix alone (A → C) costs
        <strong>−0.074</strong>. The menopause gate alone (A → B) costs <strong>−0.003</strong>. Both
        together (A → D) cost <strong>−0.083</strong>. Ninety per cent of the collapse is the bug.</p>

      <div class="note caution">
        <span class="note-label">A correction to an earlier explanation</span>
        <p>An earlier draft of this document attributed part of the AUC drop to the deliberate narrowing to
          postmenopausal women — the reasoning being that removing younger, denser, still-cycling women takes
          away easy negatives and leaves a harder cohort. That reasoning is sound and the effect is real, but
          the decomposition shows it is worth only 0.003 AUC. It is not an explanation for what happened
          here. The claim died at stage C, <em>before</em> the menopause gate was applied at all.</p>
      </div>""",
     'question three + decomposition')

# =================== the results table and the conclusions that invert
region("""      <h3>The answers, and they differ by target</h3>""",
       """        <caption>The random forest was the model chosen by inner CV in 5 of 5 folds for osteopenia and 4 of 5
          for osteoporosis (a Ridge T-score regressor won the fifth).</caption>
      </div>""",
       """      <h3>The answers, and they are the same at both targets now</h3>

      <p>This is the single most important result in the project. The previous version of this document
        reported it as a split verdict — osteopenia clearly beaten, osteoporosis not separable. On the
        corrected cohort both rows say the same thing, and the script tests each target against
        <em>two</em> comparators rather than one.</p>

      <div class="bleed">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr><th>Target</th><th>Comparator</th><th class="num">Comp. AUC</th><th class="num">Leaderboard</th><th class="num">Nested</th><th class="num">Nested Δ</th><th class="num">p</th><th>Verdict</th></tr>
            </thead>
            <tbody>
              <tr class="row-hi">
                <td rowspan="2"><strong>Osteopenia or worse</strong><br><span style="color:var(--ink-3);font-size:13px">T ≤ −1.0 · 645 events<br>32.3 per predictor</span></td>
                <td>OST</td>
                <td class="num">0.739</td>
                <td class="num">0.755</td>
                <td class="num"><strong>0.751</strong></td>
                <td class="num">+0.012<br><span style="font-size:12px">[−0.005, +0.030]</span></td>
                <td class="num">0.074</td>
                <td><span class="pill stop">Not separable</span></td>
              </tr>
              <tr class="row-hi">
                <td>Weight alone</td>
                <td class="num">0.737</td>
                <td class="num">0.755</td>
                <td class="num"><strong>0.751</strong></td>
                <td class="num">+0.014<br><span style="font-size:12px">[−0.003, +0.032]</span></td>
                <td class="num">0.055</td>
                <td><span class="pill stop">Not separable</span></td>
              </tr>
              <tr>
                <td rowspan="2"><strong>Osteoporosis</strong><br><span style="color:var(--ink-3);font-size:13px">T ≤ −2.5 · 76 events<br>3.8 per predictor — <strong>underpowered</strong></span></td>
                <td>OST</td>
                <td class="num">0.780</td>
                <td class="num">0.782</td>
                <td class="num">0.790</td>
                <td class="num">+0.010<br><span style="font-size:12px">[−0.015, +0.035]</span></td>
                <td class="num">0.21</td>
                <td><span class="pill stop">Not separable</span></td>
              </tr>
              <tr>
                <td>Weight alone</td>
                <td class="num">0.766</td>
                <td class="num">0.782</td>
                <td class="num">0.790</td>
                <td class="num">+0.024<br><span style="font-size:12px">[−0.002, +0.052]</span></td>
                <td class="num">0.037</td>
                <td><span class="pill stop">Not separable</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <caption>From <code>nested_cv_verdict.csv</code> — open this file first. p is one-sided from a paired
          stratified bootstrap; the verdict follows the 95% interval, so a p above 0.025 necessarily has an
          interval touching zero. Inner CV chose a T-score regressor or a forest depending on the fold:
          for osteopenia the five outer folds picked RF→T, forest, Ridge→T, forest, Ridge→T.</caption>
      </div>""",
       'verdict table')

region("""      <p>Read the two rows side by side and the whole point of the exercise becomes visible:</p>""",
       """          straight at what the next round of work needs: more osteoporosis cases.</p>
      </div>""",
       """      <p>Read the four rows together and the whole point of the exercise becomes visible:</p>

      <ul>
        <li><strong>Neither target is separable from OST.</strong> The osteopenia interval is
          [−0.005, +0.030] and the osteoporosis interval is [−0.015, +0.035]. Both include zero. The
          correct statement for both is that we cannot show an eighteen-variable model beats
          <code>0.2 × (weight − age)</code>.</li>
        <li><strong>Nor from weight on its own.</strong> This is the harsher of the two comparisons and it is
          why the script computes it. Age adds so little that dropping it from the comparator barely changes
          the gap: +0.014 [−0.003, +0.032] at the osteopenia threshold. The panel is not beating a formula;
          it is not reliably beating a bathroom scale.</li>
        <li><strong>Selection bias was small this time, and in one case negative.</strong> Optimism is +0.003
          for osteopenia and −0.008 for osteoporosis — the nested estimate came out <em>higher</em> than the
          leaderboard for the rarer target, which happens when different folds genuinely prefer different
          models and pooling their out-of-fold ranks beats any single fixed choice. In the previous run this
          gap was the story (0.833 collapsing to 0.806). Here the cohort defect had already removed the
          performance that selection bias was inflating.</li>
        <li><strong>The osteoporosis row should not be quoted at all.</strong> 76 events against 20 columns
          is 3.8 events per predictor, against a conventional floor of 10. The power gate labels it
          UNDERPOWERED before the model runs. Its nested AUC of 0.790 is a number with an interval wide
          enough to contain almost any conclusion, and the honest reading is "we do not have the cases to
          answer this", not "0.790".</li>
      </ul>

      <div class="note risk">
        <span class="note-label">What was previously claimed, and what replaces it</span>
        <p>The published result was <strong>nested AUC 0.810 against OST 0.747, Δ +0.063 [+0.046, +0.082],
          "beats OST"</strong>, with per-fold differences positive in all five folds. That result does not
          survive. It is replaced by <strong>0.751 against 0.739, Δ +0.012 [−0.005, +0.030], not
          separable</strong>. The figures 0.810, 0.833 and 0.806 should not be quoted from this project in
          any context except this one — an explanation of what went wrong.</p>
        <p>The second published claim, that machine learning "earns its keep" for osteopenia because the
          nested and leaderboard numbers agreed, was also an artifact. They agreed because the random forest
          won in all five folds, and it won in all five folds because duplicated rows reward memorisation.
          With the duplicates gone, the forest ties with logistic regression and the folds disagree about
          which model to use.</p>
      </div>

      <div class="note good">
        <span class="note-label">Why this is still a good result to present, and a better one than before</span>
        <p>A project that reported "AUC 0.810, beats OST" would be reporting a number produced by a data
          defect. This one built the machinery to catch that — a fingerprint audit, a decomposition harness,
          a power gate, two comparators instead of one — ran it, and printed the uncomfortable verdict
          itself. Bringing a specialist a null result <em>with the mechanism of the earlier false positive
          fully traced and quantified</em> is a stronger piece of work than the impressive number was. It
          also points straight at what the next round needs, which is not a better model: it is either more
          cases, or a variable that is not another measurement of body size.</p>
      </div>""",
       'inverted conclusions')

swap("""        <p>The leaf-size sweep confirms the counterintuitive claim in the code comments. For osteopenia,
          per-fold AUC falls monotonically as leaves get larger: 0.810 at leaf = 1, then 0.798, 0.784, 0.775,
          0.770, 0.762 at leaf = 50. Every attempt to "fix" the forest's perfect training score by
          constraining it makes real performance worse. The gap is the price of the performance.</p>""",
     """        <p>The leaf-size sweep still points the counterintuitive way, but it no longer points very hard.
          Per-fold AUC across the grid: 0.753, 0.754, 0.751, 0.749, 0.747, 0.744 at leaves 1, 2, 5, 10, 20,
          50. Constraining the forest to "fix" its perfect training score does make real performance worse,
          as the code comments claim — but the whole range spans 0.010 against a fold-to-fold SD of 0.021,
          so on the corrected cohort the honest summary is that this hyperparameter does not matter. The old
          run's much steeper slope (0.810 down to 0.762) was another duplicate artifact: deep trees look
          dramatically better when memorisation pays.</p>""",
     'leaf sweep in honesty')

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('written')
