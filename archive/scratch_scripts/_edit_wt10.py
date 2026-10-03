# -*- coding: utf-8 -*-
import io

p = 'Notes/project_walkthrough.html'
s = io.open(p, encoding='utf-8').read()

a = """      <div class="kv">
        <div><dt>PRESENT</dt><dd>For the clinical audience. Six files.</dd></div>"""
b = """      <div class="note caution">
        <span class="note-label">One trap survives by necessity — it is now labelled rather than removed</span>
        <p><code>referral_table.csv</code> and <code>threshold_sweep.csv</code> both have a cutoff column
          containing 0.50, 0.40, 0.35, 0.30, 0.25 — and they mean different things, for different models.
          The first is a <em>top fraction of the score distribution</em> from the leaderboard forest
          (AUC 0.810); the second is a <em>predicted probability</em> from the calibrated forest (AUC 0.764).
          The column names and the per-row model labels now make this visible in the files themselves, but
          the two tables still must not be merged or plotted on shared axes.</p>
      </div>
    </section>"""

i = s.index(a)
j = s.index(b, i) + len(b)

new = """      <div class="kv">
        <div><dt>PRESENT</dt><dd>For the clinical audience. Twelve files.</dd></div>
        <div><dt>METHODS</dt><dd>Backs up a methodological choice if it is challenged. Three files.</dd></div>
        <div><dt>DIAGNOSTIC</dt><dd>A bug detector. Standardised units, unstable across collinear
          predictors — not findings, and not to be shown as results. One file.</dd></div>
      </div>

      <div class="bleed">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr><th>File</th><th>Tier</th><th>What it holds</th></tr>
            </thead>
            <tbody>
              <tr class="row-hi">
                <td><code>nested_cv_verdict.csv</code></td>
                <td><span class="pill yes">Present</span></td>
                <td><strong>The headline result. Open this first.</strong> Four rows — two clinical
                  thresholds × two comparators. Comparator AUC, leaderboard best, nested AUC, optimism,
                  nested Δ with interval and one-sided p, and a literal <code>Verdict</code> column. All four
                  currently read "Not separable".</td>
              </tr>
              <tr class="row-hi">
                <td><code>model_block_ablation_osteopenia.csv</code><br><span style="color:var(--ink-3);font-size:12.5px">new in the rewrite</span></td>
                <td><span class="pill yes">Present</span></td>
                <td><strong>The variable-importance answer.</strong> Drop a whole clinical block, refit
                  everything, remeasure. This is the file that shows body size is carrying the model
                  (Δ +0.150) and that the menopause, lifestyle and history blocks are not.</td>
              </tr>
              <tr class="row-hi">
                <td><code>model_variable_ablation_osteopenia.csv</code><br><span style="color:var(--ink-3);font-size:12.5px">new in the rewrite</span></td>
                <td><span class="pill yes">Present</span></td>
                <td>The same test one variable at a time, all eighteen, across all eight models, with paired
                  bootstrap intervals and a Holm correction. Exactly one variable survives correction.</td>
              </tr>
              <tr class="row-hi">
                <td><code>clinical_predictor_table.csv</code></td>
                <td><span class="pill yes">Present</span></td>
                <td>Adjusted odds ratios per clinical unit, bootstrap 95% CIs, permutation importance for two
                  model families, missingness per predictor.</td>
              </tr>
              <tr class="row-hi">
                <td><code>forest_plot_odds_ratios.png</code></td>
                <td><span class="pill yes">Present</span></td>
                <td>The same odds ratios on a log scale. Solid marks are intervals excluding 1; dashed red
                  line at OR = 1.</td>
              </tr>
              <tr class="row-hi">
                <td><code>table_one.csv</code><br><span style="color:var(--ink-3);font-size:12.5px">new in the rewrite</span></td>
                <td><span class="pill yes">Present</span></td>
                <td>The cohort description every clinical paper opens with: each variable's distribution
                  overall and split by outcome, with missingness. Continuous as mean (SD), binary as percent
                  positive.</td>
              </tr>
              <tr class="row-hi">
                <td><code>prespecified_arms.csv</code><br><span style="color:var(--ink-3);font-size:12.5px">new in the rewrite</span></td>
                <td><span class="pill yes">Present</span></td>
                <td>Every secondary question, each with its null stated before the run: vitamin D intake,
                  serum 25(OH)D, rheumatoid arthritis, PHQ-9 as a binary, two diabetes recodes, and the two
                  single-site T-score sensitivity analyses. All null.</td>
              </tr>
              <tr class="row-hi">
                <td><code>calibration_curve.png</code><br><span style="color:var(--ink-3);font-size:12.5px">new in the rewrite</span></td>
                <td><span class="pill yes">Present</span></td>
                <td>Reliability curve plus Brier score, raw and sigmoid-calibrated. The gap the previous
                  version of this document flagged as its "obvious next addition".</td>
              </tr>
              <tr class="row-hi">
                <td><code>referral_table.csv</code></td>
                <td><span class="pill yes">Present</span></td>
                <td>Screening cost at the osteopenia threshold: DXAs ordered, cases found, missed, PPV, scans
                  per case. The cutoff column is named <code>Top fraction flagged</code>, and the score
                  column says <em>"Nested CV out-of-fold rank (not a probability)"</em> on every row.</td>
              </tr>
              <tr class="row-hi">
                <td><code>threshold_sweep.csv</code></td>
                <td><span class="pill yes">Present</span></td>
                <td>The sensitivity-first sweep. Carries <code>Model</code> and its AUC on every row so it
                  can never be mistaken for the table above.</td>
              </tr>
              <tr class="row-hi">
                <td><code>model_leaderboard_osteopenia.csv</code><br><code>model_leaderboard_osteoporosis.csv</code></td>
                <td><span class="pill yes">Present</span></td>
                <td>Five classifiers × test / train / OOB AUC, sensitivity, specificity and the full confusion
                  matrix. Now one file per target, and the OOB column carries an
                  <code>oob_note</code> saying why a number is absent when it is.</td>
              </tr>
              <tr>
                <td><code>auc_decomposition.csv</code><br><span style="color:var(--ink-3);font-size:12.5px">new in the rewrite</span></td>
                <td><span class="pill hold">Methods</span></td>
                <td><strong>Where the AUC went.</strong> Four cohort definitions, one change at a time,
                  attributing the −0.083 drop from the published figure: −0.074 duplicates, −0.003
                  menopause gate. Written by <code>_decompose.py</code>, not the main script.</td>
              </tr>
              <tr>
                <td><code>power_gate.csv</code><br><span style="color:var(--ink-3);font-size:12.5px">new in the rewrite</span></td>
                <td><span class="pill hold">Methods</span></td>
                <td>Events per predictor for every analysis cohort × target, with an OK / UNDERPOWERED label
                  against a floor of 10. Computed <em>before</em> the models run, so an underpowered result
                  is declared rather than discovered afterwards.</td>
              </tr>
              <tr>
                <td><code>rf_leaf_tuning.csv</code></td>
                <td><span class="pill hold">Methods</span></td>
                <td>Nested-tuned versus fixed <code>min_samples_leaf</code> across the grid. The answer to
                  "why leaf = 1, when the training AUC is 1.000?"</td>
              </tr>
              <tr>
                <td><code>coefficient_diagnostics.csv</code></td>
                <td><span class="pill stop">Diagnostic</span></td>
                <td>Standardised coefficients powering the leakage alarm and the sign check, and — new in
                  the rewrite — the collinear partner of any variable that trips the sign check. Not
                  interpretable as effect sizes.</td>
              </tr>
              <tr>
                <td><code>data/processed/analysis_cohort_postmenopausal.csv</code></td>
                <td><span class="pill no">Dataset</span></td>
                <td>The analysis table: 1,111 rows × 119 columns — every raw, renamed and derived variable,
                  including those excluded from the model. The audit trail, and the only file the script
                  writes outside <code>outputs/</code>.</td>
              </tr>
              <tr>
                <td><code>data/raw/&lt;cycle&gt;/DSQTOT_*.csv</code><br><code>data/raw/&lt;cycle&gt;/DR2TOT_*_calcium_vitd.csv</code></td>
                <td><span class="pill no">Cache</span></td>
                <td>Download cache for the supplement and day-2 diet files. Plumbing; lets the pipeline run
                  offline.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <caption>Sixteen files in <code>outputs/</code>, every one written by a line in this script (bar the
          decomposition, which has its own) and labelled at the moment it is written. Seven were added by the
          rewrite, and two — <code>baseline_comparison.csv</code> and the single combined
          <code>model_leaderboard.csv</code> — were deleted, because they held the withdrawn 0.810 / 0.833
          figures on the duplicated cohort and nothing regenerates them.</caption>
      </div>

      <h3>Why the coefficient file is explicitly not for presentation</h3>
      <p>Its job is to catch bugs, not to describe biology. Standardised coefficients are in units of "per one
        standard deviation of this dataset", which is not a clinical unit; and because weight and BMI share
        information at |r| = 0.94, the individual numbers shift around between them — which is precisely why
        <code>bmi</code> currently shows a positive coefficient where biology says negative. It is a smoke
        alarm: a coefficient above 2.0 means a leak, a coefficient with the wrong sign means either a wiring
        error or a collinear partner having absorbed the effect, and the file now names that partner so the
        two cases can be told apart. Both are useful to <em>you</em>. Neither belongs in front of a
        clinician, who would reasonably read −1.21 for weight as a finding rather than a diagnostic. The
        script says so in its own output, on the line after it writes the file.</p>

      <div class="note good">
        <span class="note-label">Both problems from the first draft of this document are now closed</span>
        <p><strong>The presentable results are on disk.</strong> The leaderboard, the verdict, the ablation
          grids, the arms, the calibration curve, Table 1, the referral tables and the sweep are all written
          as files rather than printed and lost. The verdict file in particular is the one to open first: it
          is a four-row summary of the entire project.</p>
        <p><strong>The folder is unambiguous.</strong> Every file carries an explicit tier. A colleague
          opening <code>outputs/</code> can tell the clinical table from the diagnostic one without reading
          the source.</p>
      </div>

      <div class="note caution">
        <span class="note-label">One trap survives by necessity — it is labelled rather than removed</span>
        <p><code>referral_table.csv</code> and <code>threshold_sweep.csv</code> both have a cutoff column
          containing 0.50, 0.40, 0.35, 0.30, 0.25 — and they mean different things. The first is a
          <em>top fraction of the score distribution</em>, ranked on the nested-CV out-of-fold score; the
          second is a <em>predicted probability</em> from the separate calibrated forest (AUC 0.753). The
          column names and the per-row score labels make this visible in the files themselves, but the two
          tables still must not be merged or plotted on shared axes.</p>
      </div>
    </section>"""

s = s[:i] + new + s[j:]
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('outputs section rewritten')
