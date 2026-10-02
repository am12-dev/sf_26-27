# -*- coding: utf-8 -*-
import io

p = 'Notes/project_walkthrough.html'
s = io.open(p, encoding='utf-8').read()


def swap(old, new, label):
    global s
    assert s.count(old) == 1, 'count %d for %s' % (s.count(old), label)
    s = s.replace(old, new)
    print('  ok', label)


def cut(a, b):
    i = s.index(a)
    j = s.index(b, i) + len(b)
    return s[i:j]


# ===================================================== stale: the gap is now closed
swap("""      <div class="note caution">
        <span class="note-label">One genuine gap this opened, worth knowing about</span>
        <p>Deleting <code>calibration_curve.png</code> leaves the project with no calibration figure, and
          step 13 depends on calibrated probabilities being trustworthy — that is the whole reason it wraps
          the forest in <code>CalibratedClassifierCV</code>. The numbers are sound (the sweep reports
          PR-AUC alongside ROC-AUC), but if a specialist asks "are these probabilities real?", the honest
          answer today is that the sweep table implies it and no plot demonstrates it. Regenerating a
          calibration curve <em>from this script</em> is the obvious next addition.</p>
      </div>""",
     """      <div class="note good">
        <span class="note-label">The one gap this opened is now closed</span>
        <p>Deleting the old <code>calibration_curve.png</code> left the project with no calibration figure,
          while step 13 depends on calibrated probabilities being trustworthy — that is the whole reason it
          wraps the forest in <code>CalibratedClassifierCV</code>. The earlier version of this document
          flagged regenerating one <em>from this script</em> as the obvious next addition. The rewrite does
          it: <code>calibration_curve.png</code> is now written by the pipeline itself, as a reliability
          curve with the Brier score for both the raw and the sigmoid-calibrated forest — 0.198 calibrated
          against 0.199 raw. The figure exists, and it says the probabilities were close to honest already.</p>
      </div>

      <div class="note caution">
        <span class="note-label">Two more files were deleted in this round, for a different reason</span>
        <p><code>baseline_comparison.csv</code> and the single combined <code>model_leaderboard.csv</code>
          are gone. Not stale-by-neglect like the thirteen above — stale-by-correction. They held the 0.810
          and 0.833 figures computed on the duplicated cohort, and nothing in the current script regenerates
          them: the baseline comparison was folded into <code>nested_cv_verdict.csv</code> (which now carries
          both comparators), and the leaderboard is written once per target. Leaving them in place would have
          left a withdrawn result sitting in the same folder as its replacement.</p>
        <p><code>outputs/run_log.txt</code> was deliberately <em>not</em> touched. It is your manual capture,
          not the script's artifact, and deleting someone's own audit trail is not the pipeline's call.</p>
      </div>""",
     'stale: calibration gap closed')

# ===================================================== meeting: four-sentence version + stats
swap("""      <h3>The four-sentence version</h3>
      <p class="lede">Using five rounds of NHANES data, we assembled 1,111 postmenopausal non-Hispanic White women aged 50–65
        who received a hip DXA scan, and trained models to predict their bone-density category from
        clinic-available information alone, with every trace of the scan excluded from the inputs. A random
        forest reaches a cross-validated AUC of 0.810 for detecting osteopenia or worse, at 74% sensitivity
        and 73% specificity. Tested honestly — with model selection moved inside each training fold — that
        beats the OST formula by 0.063 AUC with a confidence interval clear of zero, and it
        beats it in every fold. For osteoporosis specifically we cannot make that claim: the apparent
        advantage shrinks from +0.060 to +0.031 once selection bias is removed, and the interval crosses
        zero, because there are only 94 cases.</p>

      <div class="stats">
        <div class="stat">
          <dt>Osteopenia or worse</dt>
          <dd>+0.063 <small>nested AUC gain over OST, CI [+0.046, +0.082] — a real, reproducible improvement</small></dd>
        </div>
        <div class="stat">
          <dt>Osteoporosis</dt>
          <dd>+0.031 <small>nested AUC gain, CI [−0.013, +0.077] — not separable from OST at n = 94 cases</small></dd>
        </div>
        <div class="stat">
          <dt>Ask for</dt>
          <dd>2 <small>the referral cutoff, and which risk factors their notes already carry</small></dd>
        </div>
      </div>""",
     """      <h3>The four-sentence version</h3>
      <p class="lede">Using five rounds of NHANES data, we assembled 1,111 postmenopausal non-Hispanic White
        women aged 50–65 who received a hip DXA scan, and trained eight models to predict their bone-density
        category from clinic-available information alone, with every trace of the scan excluded from the
        inputs. Tested honestly — with model selection moved inside each training fold — the best of them
        reaches AUC 0.751 for detecting osteopenia or worse, against <strong>0.739 for the OST formula</strong>
        (weight minus age, times 0.2) and <strong>0.737 for weight on its own</strong>: a margin of +0.012
        whose interval crosses zero. <strong>The eighteen-variable panel is not separable from a two-input
        formula, at either clinical threshold, against either comparator.</strong> The reason is visible in
        the ablation grid — body size carries essentially all of the signal, and the other sixteen variables
        can be deleted one at a time without measurable loss.</p>

      <div class="stats">
        <div class="stat">
          <dt>Osteopenia or worse</dt>
          <dd>+0.012 <small>nested AUC over OST, CI [−0.005, +0.030], p = 0.074 — not separable</small></dd>
        </div>
        <div class="stat">
          <dt>Osteoporosis</dt>
          <dd>+0.010 <small>nested AUC over OST, CI [−0.015, +0.035] — not separable, and underpowered at 76 events</small></dd>
        </div>
        <div class="stat">
          <dt>Drop body size</dt>
          <dd>−0.150 <small>AUC lost when <code>bmi</code> and <code>weight_kg</code> both go: 0.757 → 0.606</small></dd>
        </div>
      </div>

      <div class="note risk">
        <span class="note-label">Read this before quoting anything from an older version of this document</span>
        <p>The previous four-sentence version of this section said "a random forest reaches a cross-validated
          AUC of 0.810 … that beats the OST formula by 0.063 AUC with a confidence interval clear of zero,
          and it beats it in every fold." <strong>That claim is withdrawn.</strong> It was produced on a
          cohort containing 176 women counted twice — NHANES pooled the 2017–2018 cycle into its
          2017–March 2020 pre-pandemic file under re-numbered SEQNs, so loading both cycles duplicated
          people under IDs no de-duplication on SEQN could see. Cross-validation splits <em>rows</em>, not
          <em>people</em>, so the same woman sat in the training and test folds at once and the trees
          memorised her. Correcting it costs −0.074 of the −0.083 total drop
          (<a href="#honesty">the decomposition</a>); the narrowing to postmenopausal women costs only
          −0.003. The figures 0.810, 0.833 and 0.806 should not leave this document except as history.</p>
      </div>

      <h3>If they ask one question, it will be "so which variables matter?"</h3>
      <p>This is worth rehearsing, because the answer is short, defensible, and not what the project set out
        to find. Three methods were run and they agree
        (<a href="#predictors">the full tables</a>):</p>
      <ul>
        <li><strong>Body size is very nearly the whole model.</strong> Remove <code>bmi</code> and
          <code>weight_kg</code> together and AUC falls from 0.757 to <strong>0.606</strong>
          (Δ +0.150 [+0.114, +0.184]). Remove the <em>entire</em> menopause and hormone block and it costs
          0.004. The whole lifestyle block: 0.001. The whole history and family block: 0.003. All three
          intervals straddle zero.</li>
        <li><strong>One variable of eighteen survives multiple-comparison correction:</strong>
          <code>weight_kg</code>, +0.0203 AUC when deleted, p &lt; 0.001 after Holm. <code>age</code> is
          +0.0018. <code>bmi</code> is −0.0002 — because weight already carries it, at |r| = 0.94.</li>
        <li><strong>Age plus weight alone scores 0.739</strong>, reproducing OST's AUC to three decimals.
          That is the crux: the panel cannot beat OST because OST is already using the two variables that
          carry the signal.</li>
      </ul>
      <p>Six predictors still show odds ratios whose intervals exclude 1 — weight, prior estrogen use,
        poverty-income ratio, age, prior fracture and sedentary minutes — and those are legitimate
        associations worth discussing. They just do not add <em>discrimination</em> on top of body size, and
        "associated with the outcome" and "improves the prediction" are different claims.</p>""",
     'meeting: four-sentence + stats + variables')

# ===================================================== meeting: prevalence question
swap("""        <dt>56% prevalence? That is nothing like my clinic.</dt>""",
     """        <dt>58% prevalence? That is nothing like my clinic.</dt>""",
     'meeting: prevalence question heading')

# ===================================================== meeting: which single number
swap("""        <dt>Which single number should I trust?</dt>
        <dd>The nested cross-validated difference against OST: <strong>+0.063 [+0.046, +0.082]</strong> for
          osteopenia-or-worse, and <strong>+0.031 [−0.013, +0.077]</strong> for osteoporosis. Not the
          leaderboard's 0.810 and 0.833 — those were chosen partly because they looked good on those
          particular rows. For osteopenia the two agree exactly, which is itself reassuring. For osteoporosis
          they do not, and the nested one is right.</dd>

        <dt>Is a two-variable formula really the benchmark?</dt>
        <dd>It is the right benchmark precisely because it is so cheap: weight minus age, times 0.2. It
          scores 0.747 here. Any model that needs 23 variables, blood work and a diet survey has to justify
          itself against that, and for osteoporosis specifically it currently cannot. If a specialist prefers
          FRAX as the comparator, that is a fair challenge — FRAX is not implemented here, and it predicts
          fracture rather than density, so it is not directly substitutable.</dd>""",
     """        <dt>Which single number should I trust?</dt>
        <dd>The nested cross-validated difference against OST: <strong>+0.012 [−0.005, +0.030]</strong> for
          osteopenia-or-worse, and <strong>+0.010 [−0.015, +0.035]</strong> for osteoporosis. Both cross
          zero. Not the leaderboard's 0.755 and 0.782 — those were chosen partly because they looked good on
          those particular rows — and certainly not 0.810 or 0.833, which were computed on the duplicated
          cohort and are withdrawn. The four-row <code>nested_cv_verdict.csv</code> is the whole bottom line
          and it is the first file to open.</dd>

        <dt>Is a two-variable formula really the benchmark?</dt>
        <dd>It is the right benchmark precisely because it is so cheap: weight minus age, times 0.2. It
          scores 0.739 here for osteopenia and 0.780 for osteoporosis — both inside its published range,
          which is a check on the implementation. A model that needs eighteen variables, blood work and a
          diet survey has to justify itself against that, and <strong>on this cohort it does not</strong>. We
          also ran a harsher second comparator, <em>weight alone</em> (0.737 / 0.766), and the panel is not
          separable from that either. If a specialist prefers FRAX as the comparator, that is a fair
          challenge — FRAX is not implemented here, and it predicts fracture rather than density, so it is
          not directly substitutable.</dd>

        <dt>So did the project fail?</dt>
        <dd>No — it produced a negative result and caught its own error, which is a different thing. The
          claim it started with does not survive; what it can say now is narrower and much more solid: on a
          clean cohort of 1,111 postmenopausal women, clinic-available questionnaire data adds nothing
          measurable to a scale and a date of birth for predicting hip bone density. That is worth knowing,
          it is worth writing down, and it is the kind of finding that does not get published often enough.
          The defect that produced the earlier number is documented, quantified and fixed in code
          (<a href="#guards">guard 1</a>), and every artifact on disk now traces to the corrected cohort.</dd>""",
     'meeting: single number + benchmark + did it fail')

# ===================================================== meeting: calcium/vitD answer figures
swap("""          of them from the model changes cross-validated AUC by +0.004, well inside the fold-to-fold
          variation of ±0.027 — statistically indistinguishable from no change.""",
     """          of them from the model changes cross-validated AUC by −0.002 [−0.006, +0.001] for intake and
          −0.001 [−0.008, +0.005] for serum 25(OH)D — both intervals containing zero, and both nulls
          written down <em>before</em> the run in <code>prespecified_arms.csv</code>.""",
     'meeting: calcium/vitd figures')

# ===================================================== meeting: 23 predictors in missing-risk-factors ask
swap("""        <li><strong>Missing risk factors.</strong> Parental hip fracture, height loss, current smoking
          intensity and weight change since 40 are all established and all absent here. If any are routinely
          in their notes, they are candidates for the next iteration.</li>""",
     """        <li><strong>Missing risk factors.</strong> Height loss, current smoking intensity and weight change
          since 40 are all established and all absent here. (Parental hip fracture <em>is</em> in the panel
          now, at 4.4% missing; deleting it costs −0.001 AUC.) If any of the absent three are routinely in
          their notes, they are candidates for the next iteration — though the ablation grid sets a low
          prior: sixteen of eighteen existing variables add nothing measurable, so a nineteenth would have to
          be carrying information that body size does not.</li>""",
     'meeting: missing risk factors')

# ===================================================== frax: OST/model figures
swap("""                <td>FRAX separated osteoporosis (T &le; &minus;2.5) with AUC 0.72–0.75 among 2,991
                  community-dwelling adults aged 60+ — below both OST (0.773 on this cohort) and this model
                  (0.806 nested).</td>""",
     """                <td>FRAX separated osteoporosis (T &le; &minus;2.5) with AUC 0.72–0.75 among 2,991
                  community-dwelling adults aged 60+ — in the same range as OST (0.780 on this cohort) and
                  this model (0.790 nested), neither of which is separable from the other.</td>""",
     'frax: OST and model figures')

# ===================================================== sources: OST benchmark figures
swap("""            <p style="margin-bottom:0"><strong>The benchmark.</strong> OST scores 0.747 (osteopenia) and 0.773 (osteoporosis) on this cohort — inside the published range, which independently validates the implementation rather than merely asserting it. Its high-sensitivity, moderate-specificity profile is the triage shape any new tool has to beat.</p>""",
     """            <p style="margin-bottom:0"><strong>The benchmark — and, as it turns out, the winner.</strong> OST scores <strong>0.739</strong> (osteopenia) and <strong>0.780</strong> (osteoporosis) on this cohort — inside the published 0.71–0.79 range, which independently validates the implementation rather than merely asserting it. Its high-sensitivity, moderate-specificity profile is the triage shape any new tool has to beat, and on this cohort the eighteen-variable panel does not beat it: +0.012 [−0.005, +0.030]. A second, harsher comparator — weight alone — scores 0.737 and is also not beaten.</p>""",
     'sources: OST benchmark')

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('written')
