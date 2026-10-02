# -*- coding: utf-8 -*-
import io

p = 'Notes/project_walkthrough.html'
s = io.open(p, encoding='utf-8').read()


def cut(start, end):
    """Return the exact slice between two anchors, inclusive."""
    i = s.index(start)
    j = s.index(end, i) + len(end)
    return s[i:j]


# ============================================================ the feature table
old_table_start = """      <p>Grouped by where a real clinic would get them. This is the honest test of the project's premise: if
        a variable on this list is not actually obtainable in a primary-care visit, the tool does not work as
        advertised.</p>"""
old_table_end = """        <caption>The 23 features the models actually receive, from <code>define_features</code>.</caption>
      </div>"""

old = cut(old_table_start, old_table_end)

new = """      <p>Grouped by where a real clinic would get them. This is the honest test of the project's premise: if
        a variable on this list is not actually obtainable in a primary-care visit, the tool does not work as
        advertised.</p>

      <p><strong>Eighteen variables, twenty model columns.</strong> The two numbers differ because
        <code>menopause_type</code> is categorical: it expands into three indicator columns against a
        reference level of natural menopause. Clinically it is one question, so the ablation grid drops all
        three together — groups, not columns, are the unit of analysis.</p>

      <div class="bleed">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr><th>Available from</th><th>Variables</th><th>Notes</th></tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Measured in the room</strong><br><span style="color:var(--ink-3);font-size:13px">scale, stadiometer, DOB</span></td>
                <td><code>age</code> <code>weight_kg</code> <code>bmi</code></td>
                <td>Complete or near it — 0.1% missing at worst. <code>weight_kg</code> is not merely the most
                  predictive variable here; on the corrected cohort it is very nearly the <em>only</em> one.
                  <code>height_cm</code> is deliberately absent: it enters through <code>bmi</code>, and
                  carrying weight, height and BMI together makes the design near-singular.</td>
              </tr>
              <tr>
                <td><strong>Reproductive and hormonal</strong><br><span style="color:var(--ink-3);font-size:13px">interview</span></td>
                <td><code>years_since_menopause</code> <code>menopause_type</code> <code>ever_used_estrogen</code></td>
                <td>Derived, not raw — see below. 2.0% / 0% / 0.2% missing. <code>menopause_type</code> has no
                  missing category because "unknown" <em>is</em> one of its levels (104 women), which is
                  honest rather than imputed. <code>postmenopausal</code> is gone from the panel: it is now
                  a cohort filter, so it is constant by construction and carries no information.</td>
              </tr>
              <tr>
                <td><strong>Chart and family history</strong><br><span style="color:var(--ink-3);font-size:13px">notes, medication list</span></td>
                <td><code>any_prior_fracture</code> <code>steroid_use</code> <code>diabetes</code> <code>parental_hip_fracture</code> <code>family_hx_osteoporosis</code></td>
                <td>Classic clinical risk factors, most of them also in FRAX. 0% – 4.7% missing.</td>
              </tr>
              <tr>
                <td><strong>Lifestyle</strong><br><span style="color:var(--ink-3);font-size:13px">interview</span></td>
                <td><code>ever_smoked</code> <code>alcohol_drinks_day</code> <code>vigorous_activity</code> <code>sedentary_min_day</code></td>
                <td>The worst-covered block: 0%, 13.6%, 15.6%, 15.8% missing. Alcohol is
                  <em>current</em> intake with lifelong abstainers set to a true zero and former drinkers
                  left missing rather than zeroed — a former heavy drinker is not a non-drinker.</td>
              </tr>
              <tr>
                <td><strong>Social</strong></td>
                <td><code>poverty_income_ratio</code></td>
                <td>Family income relative to the federal poverty line. 5.0% missing.</td>
              </tr>
              <tr>
                <td><strong>Mood and sleep</strong></td>
                <td><code>phq9_score</code> <code>sleep_hrs</code></td>
                <td><strong>0.1% and 0.4% missing.</strong> Both were catastrophically incomplete in the old
                  pipeline — PHQ-9 at 80% missing, sleep dropped from the model entirely for sparsity. Both
                  were repaired by the rewrite, not by imputation; see below.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <caption>The 18 variables and 20 columns the models actually receive, from <code>FEATURE_GROUPS</code>.</caption>
      </div>

      <div class="note">
        <span class="note-label">Four more variables exist, but only inside a named arm</span>
        <p><code>total_calcium_mg</code> and <code>total_vitd_mcg</code> (930 women), <code>serum_vitd_nmol</code>
          (974) and <code>rheumatoid_arthritis</code> (988) are each measured on a <em>different</em> subset
          of the cohort. Putting them all in one model silently intersects those subsets and shrinks the
          analysis to whoever has everything. So the base panel excludes them and each one gets its own
          prespecified arm, run on its own complete-case sample and compared against the same base panel
          restricted to the same women. That is the only way the comparison answers "does this variable add
          anything" rather than "does this subset of women behave differently". All four arms came back
          null; the numbers are in <a href="#arms">the arms table</a>.</p>
      </div>

      <div class="note good">
        <span class="note-label">Two variables were rescued rather than imputed</span>
        <p><strong>PHQ-9 went from 80.4% missing to 0.1%.</strong> The old code summed the nine depression
          items with <code>min_count=5</code>, meaning a woman needed five answered items to get a score —
          and NHANES routes most respondents past most of those items by skip logic, so four out of five
          women ended up with no score at all. The rewrite reads the skip pattern instead of fighting it: an
          unasked item following a negative screen is a zero, not a blank. 1,110 of 1,111 women now have a
          score, and 112 of them (10.1%) screen positive at the conventional cutoff of 10 — a plausible
          prevalence, which the 20% sample never was.</p>
        <p><strong><code>sleep_hrs</code> is back in the panel.</strong> It was dropped from the old model for
          data density, on the strength of a coverage figure that was itself an artifact of not coalescing
          <code>SLD012</code> (newer cycles) with <code>SLD010H</code> (older ones). Coalesced properly it
          covers 1,107 of 1,111.</p>
      </div>"""

assert s.count(old) == 1
s = s.replace(old, new)
print('feature table replaced')


# ============================================================ data-quality flags
old_flags_start = """      <div class="note caution">
        <span class="note-label">Three data-quality flags worth raising yourself</span>"""
old_flags_end = """          fabricated values.</p>
      </div>
    </section>"""

old2 = cut(old_flags_start, old_flags_end)

new2 = """      <div class="note caution">
        <span class="note-label">Two data-quality flags worth raising yourself</span>
        <p><strong><code>supp_data_available</code> is gone, and it should never have been there.</strong> It
          flagged whether the woman's survey <em>cycle</em> shipped a supplement file — 2005–06 did not, so
          all 173 of its women were marked unobserved. That is a dataset provenance marker sitting in a
          clinical feature list: a variable the model could learn from that no clinician could ever record.
          It was harmless in effect here (odds ratio 1.00, importance ≈ 0) but the allowlist now simply has
          no entry for it.</p>
        <p><strong>Three predictors still exceed 13% missingness:</strong> <code>sedentary_min_day</code>
          15.8%, <code>vigorous_activity</code> 15.6%, <code>alcohol_drinks_day</code> 13.6%. All are
          median-imputed <em>inside the training fold</em>, which is a defensible default and leaks nothing,
          but it does mean the reported effect for each of those variables leans partly on fabricated values.
          The imputation values actually used are written out to
          <code>Notes/imputation_values.csv</code> so a reviewer can see exactly what was filled in.</p>
      </div>
    </section>"""

assert s.count(old2) == 1
s = s.replace(old2, new2)
print('data-quality flags replaced')


# ============================================================ dropped-variables table rows
rep_pairs = [
    ("""<tr><td><code>prior_hip_fracture</code> <code>prior_spine_fracture</code> <code>prior_wrist_fracture</code></td><td>Too rare to estimate separately — 21 hip and 46 wrist events. Every tree model gave them exactly zero importance while the linear models fitted noise. Pooled into <code>any_prior_fracture</code> (233 positives, 15.7%), which is both estimable and the clinically meaningful construct.</td></tr>""",
     """<tr><td><code>prior_hip_fracture</code> <code>prior_spine_fracture</code> <code>prior_wrist_fracture</code></td><td>Too rare to estimate separately — 18 hip and 35 wrist events on this cohort. Every tree model gave them exactly zero importance while the linear models fitted noise. Pooled into <code>any_prior_fracture</code> (177 positives, 15.9%), which is both estimable and the clinically meaningful construct.</td></tr>"""),

    ("""<tr><td><code>sleep_risk</code> / <code>sleep_hrs</code></td><td>Sleep data is sparse and inconsistent across cycles. The code builds both a with-sleep and a without-sleep feature set, then trains only on the without.</td></tr>""",
     """<tr><td><code>sleep_risk</code></td><td>A hand-cut binary of <code>sleep_hrs</code>. Superseded by the continuous variable, which is now in the panel — the old with-sleep / without-sleep pair of feature sets is gone, and with it the dead <code>X_with</code> arm that was built every run and never scored.</td></tr>"""),

    ("""<tr><td><code>sedentary_min_day</code></td><td>Collected, excluded.</td></tr>""",
     """<tr><td><code>hysterectomy</code> <code>oophorectomy</code> <code>menopause_natural</code></td><td>Three overlapping binaries for one clinical question, and not mutually exclusive, so a woman could be coded several ways at once. Replaced by the single categorical <code>menopause_type</code> with natural menopause as the reference level.</td></tr>
              <tr><td><code>supp_data_available</code></td><td>A property of the survey cycle, not of the woman. See the flag above.</td></tr>
              <tr><td><code>any_arthritis</code></td><td>Pools rheumatoid with osteoarthritis, which have opposite bone implications. Rheumatoid arthritis alone is a prespecified arm instead (71 cases).</td></tr>"""),
]

for o, n in rep_pairs:
    assert s.count(o) == 1, 'row not unique/found: ' + o[:60]
    s = s.replace(o, n)
print('dropped-table rows replaced')

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('written')
