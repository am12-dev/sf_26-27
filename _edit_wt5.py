# -*- coding: utf-8 -*-
import io

p = 'Notes/project_walkthrough.html'
s = io.open(p, encoding='utf-8').read()


def cut(start, end):
    i = s.index(start)
    j = s.index(end, i) + len(end)
    return s[i:j]


def swap(old, new, label):
    global s
    assert s.count(old) == 1, 'count %d for %s' % (s.count(old), label)
    s = s.replace(old, new)
    print('  ok', label)


# ---------------------------------------------------------------- heading + intro
swap("""        <h2>Six ways this could have been wrong, and the guard against each</h2>
      </div>

      <p>This section is the strongest thing to bring to a specialist meeting. Most of these are not
        hypothetical — the code comments record that they were <em>found</em> and fixed, which is a very
        different and much more credible claim than "we were careful".</p>

      <h4>1 · Target leakage</h4>""",
     """        <h2>Seven ways this could have been wrong, and the guard against each</h2>
      </div>

      <p>This section is the strongest thing to bring to a specialist meeting. None of these are
        hypothetical — every one was <em>found</em> in this codebase and fixed, which is a very different and
        much more credible claim than "we were careful". The first is the one that changed the answer.</p>

      <h4>1 · The same women counted twice</h4>
      <p>This is the defect that overturned the project's headline result, and no guard was watching for it.
        NHANES built its pre-pandemic file by pooling the complete 2017–2018 cycle with the partial
        2019–2020 sample and <strong>re-numbering every SEQN</strong>. So <code>DEMO_J</code> runs
        93703–102956 and <code>P_DEMO</code> runs 109263–124822 — disjoint ranges for overlapping people.
        Loading both cycles, as the old <code>CYCLES</code> list did, put <strong>176 of these women in the
        cohort twice</strong> under two different IDs that no deduplication on SEQN could ever catch.</p>
      <p>Cross-validation splits <em>rows</em>, not people. A woman present twice lands in the training fold
        and the test fold simultaneously, and the model is scored on a row it has already memorised. That is
        exactly the mechanism target leakage uses, arriving through the front door. The guard is now
        threefold: 2017–2018 is out of <code>CYCLES</code>; a <strong>fingerprint audit</strong> hashes
        each woman's continuous measurements (both BMD values, weight, height, age) and asserts that no two
        rows share one — <strong>this run: 1,306 rows with a complete fingerprint, 0 collisions</strong>;
        and the 2017–2018 file is still read, but only as a <em>lookup table</em> to crosswalk the missing
        vitamin D values, never as a source of cohort rows.</p>
      <p>The cost is quantified rather than asserted. <code>auc_decomposition.csv</code> reruns the whole
        pipeline at four stages, and the duplicate fix alone accounts for <strong>−0.074 AUC</strong> — the
        overwhelming majority of the total −0.083 drop from the published figure. See
        <a href="#honesty">the honesty section</a>.</p>

      <h4>2 · Target leakage</h4>""",
     'guards heading + new guard 1')

# ---------------------------------------------------------------- guard 2 (leak alarm)
swap("""      <p>Under the old blocklist, a new column derived from bone density would silently
        become an input. The standing guard is a coefficient alarm: after fitting, the script checks the
        largest standardised coefficient against a threshold of 2.0. The largest legitimate one observed is
        about 0.99 (<code>weight_kg</code>); anything leaking the target would dominate at several times
        that. <strong>This run: largest coefficient 0.990, on <code>weight_kg</code>. Clean.</strong></p>

      <h4>2 · Clinically backwards effects</h4>""",
     """      <p>Under the old blocklist, a new column derived from bone density would silently
        become an input. Two guards now sit on this. The structural one is
        <code>BMD_DENYLIST</code>: ten named columns — both raw BMD values, both site T-scores, the combined
        T-score, both labels, and the descriptive category — asserted absent from every feature matrix,
        under every arm, before any model is fitted. The statistical one is a coefficient alarm: after
        fitting, the script checks the largest standardised coefficient against a threshold of 2.0. The
        largest legitimate one is about 1.21 (<code>weight_kg</code>); anything carrying the scan would
        dominate at several times that. <strong>This run: largest coefficient 1.214, on
        <code>weight_kg</code>. No leak signature.</strong></p>

      <h4>3 · Clinically backwards effects</h4>""",
     'guard 2 leak alarm')

# ---------------------------------------------------------------- guard 3 (signs)
swap("""        the age / age-at-menopause collinearity in the first place. <strong>This run flags one:
        <code>total_vitd_mcg</code></strong>, where higher intake associates with slightly higher risk — a
        classic reverse-causation pattern, since women told they have thinning bones start taking vitamin D.
        Worth saying out loud rather than hiding.</p>

      <h4>3 · Fabricated totals</h4>""",
     """        the age / age-at-menopause collinearity in the first place. <strong>This run flags one:
        <code>bmi</code></strong>, at +0.171 where a protective sign was expected. The script does not
        merely flag it, it <em>diagnoses</em> it: it reports the flagged variable's strongest collinear
        partner and that partner's coefficient, and prints
        <em>"strongest partner <code>weight_kg</code> (|r| 0.94, coef −1.214): partner absorbed the effect,
        so this is a residual with no clinical reading."</em> At a correlation of 0.94, weight has taken the
        entire protective effect and BMI is fitting what is left over. The block ablation below confirms
        this directly — the two together are worth +0.150 AUC, either one alone is worth almost nothing.
        This is also why the old run's flag on <code>total_vitd_mcg</code> no longer appears: vitamin D
        intake is no longer in the base panel at all.</p>
      <p>Note what is deliberately <em>not</em> in <code>EXPECTED_SIGNS</code>: diabetes. Type 2 diabetes
        raises measured bone density while also raising fracture risk — the diabetic bone paradox — so the
        protective coefficient here (−0.040) is the expected result and flagging it would be wrong.</p>

      <h4>4 · Fabricated totals</h4>""",
     'guard 3 signs')

# ---------------------------------------------------------------- guard 4 (totals counts)
swap("""        blank, not 0). <strong>206 women unobserved; 229 totals left missing.</strong></p>

      <h4>4 · A variable running under a false name</h4>
      <p><code>MCQ160A</code> was previously called <code>rheumatoid_arthritis</code> in this code. It is not
        rheumatoid-specific — it asks whether a doctor ever mentioned arthritis of any type, and it is
        positive in 45.8% of this cohort. Rheumatoid arthritis is a genuine FRAX risk factor with a 1–2%
        prevalence. Under the wrong name, a common, weakly-relevant variable was masquerading as a rare,
        strongly-relevant one. It is now <code>any_arthritis</code>.</p>

      <h4>5 · Importance measures that lie</h4>""",
     """        blank, not 0). <strong>173 women unobserved; 181 totals left missing.</strong></p>
      <p>The rewrite added a second layer here: per-variable plausibility ranges. A global
        refused/don't-know list cannot catch a decode error, because NHANES's sentinel codes mean different
        things in different files. So each variable declares its own valid interval —
        <code>DR2TCALC</code> 0–8,000 mg, <code>DR2TVD</code> 0–400 µg — and anything outside it is set
        to missing with a count printed. <strong>This run: 3 of 38,222 calcium values rejected, 0 of 29,958
        vitamin D values.</strong> Near-zero, which is the useful result: the guard confirms the decode was
        already right rather than papering over a problem.</p>

      <h4>5 · A variable running under a false name</h4>
      <p><code>MCQ160A</code> was previously called <code>rheumatoid_arthritis</code> in this code. It is not
        rheumatoid-specific — it asks whether a doctor ever mentioned arthritis of any type, and it is
        positive in 47.7% of this cohort. Rheumatoid arthritis is a genuine FRAX risk factor at a few
        percent prevalence. Under the wrong name, a common, weakly-relevant variable was masquerading as a
        rare, strongly-relevant one.</p>
      <p>The rewrite went further than renaming it. <code>MCQ195</code> asks which <em>type</em> of arthritis,
        so real rheumatoid arthritis is recoverable: <strong>71 of 988 women (7.2%)</strong>, with 123
        excluded because they reported arthritis but no type. That is now a prespecified arm of its own, and
        <code>any_arthritis</code> — which pools rheumatoid with osteoarthritis, two conditions with
        opposite bone implications — is off the panel entirely. <strong>The arm came back null:
        Δ +0.000.</strong></p>

      <h4>6 · Importance measures that lie</h4>""",
     'guard 4-5')

# ---------------------------------------------------------------- guard 6 (importances)
swap("""        real ranking: <code>total_calcium_mg</code> placed 7th despite a completely flat outcome gradient
        across its quartiles (57.8 / 55.0 / 57.6 / 58.5%), while <code>oophorectomy</code> placed last
        despite an odds ratio of 1.28. They were replaced with <strong>permutation importance</strong> —
        literally: shuffle one column, refit nothing, and measure how much out-of-fold AUC is lost. That is
        model-agnostic, in the same units for every model, and not biased by variable type.</p>""",
     """        real ranking: <code>total_calcium_mg</code> placed 7th despite a completely flat outcome gradient
        across its quartiles (57.8 / 55.0 / 57.6 / 58.5%), while <code>oophorectomy</code> placed last
        despite an odds ratio of 1.28. They were replaced with <strong>permutation importance</strong> —
        literally: shuffle one column, refit nothing, and measure how much out-of-fold AUC is lost. That is
        model-agnostic, in the same units for every model, and not biased by variable type.</p>
      <p>The rewrite added two more importance methods, because permutation importance has its own blind
        spot: when two variables carry the same information, shuffling either one costs nothing, since the
        model simply reads the other. So the script now also runs <strong>single-variable ablation</strong>
        (drop a variable, refit everything, remeasure) and <strong>block ablation</strong> (drop a whole
        clinical group at once). Where the three disagree is exactly where collinearity lives, and that
        disagreement is the finding rather than a nuisance — see
        <a href="#predictors">which variables actually matter</a>.</p>""",
     'guard 6 importances')

# ---------------------------------------------------------------- guard 7 (OOB)
swap("""      <h4>6 · An in-sample score that flatters a forest</h4>""",
     """      <h4>7 · An in-sample score that flatters a forest</h4>""",
     'guard 7 heading')

swap("""        it. That is the honest in-sample figure for a bagged ensemble, and the leaderboard prints it in its
        own column with an explicit instruction not to rank models by the train/test gap.</p>""",
     """        it. That is the honest in-sample figure for a bagged ensemble, and the leaderboard prints it in its
        own column with an explicit instruction not to rank models by the train/test gap.</p>
      <p>That guard needed a guard of its own. On the osteoporosis target, out-of-bag scoring silently
        breaks: <code>class_weight='balanced'</code> oversamples the 76 cases so heavily that most of them
        are in nearly every tree's bootstrap sample and are therefore almost never out-of-bag. Rows with no
        out-of-bag coverage come back from scikit-learn as all-<em>zero</em> score rows rather than as
        missing, so they score as confident negatives and the OOB AUC <strong>inverts</strong> — the
        unfixed code printed <strong>0.108</strong> in a table labelled PRESENT. The rewrite checks coverage
        before reporting and withholds the number instead, printing
        <em>"OOB withheld: only 28% of class 1 rows are ever out-of-bag (class_weight oversamples them)"</em>.
        A refused number is a result; an inverted one is a lie.</p>""",
     'guard 7 OOB fix')

# ---------------------------------------------------------------- leaf tuning numbers
swap("""          CV picked leaf = 1 in 5 of 5 folds for the osteopenia target and 3 of 5 for osteoporosis, lifting
          test AUC from 0.784 to 0.810 and from 0.829 to 0.835 respectively.</p>""",
     """          CV picked small leaves, and the sweep across the grid falls monotonically once past leaf = 2:
          0.753, 0.754, 0.751, 0.749, 0.747, 0.744 at leaves 1, 2, 5, 10, 20, 50. The spread is 0.010 AUC
          against a fold-to-fold SD of about 0.021 — which is the more useful reading of this table than
          the ranking: on the corrected cohort, <strong>this hyperparameter does not matter</strong>. That
          is worth knowing before spending effort tuning it.</p>""",
     'leaf tuning')

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('written')
