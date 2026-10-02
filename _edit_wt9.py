# -*- coding: utf-8 -*-
import io

p = 'Notes/project_walkthrough.html'
s = io.open(p, encoding='utf-8').read()

a = """      <p>AUC is not a clinical unit. No one orders 0.81 of a scan. The last part of the script translates the
        model into the decision a clinician actually makes, in two complementary ways.</p>"""
b = """          cutoff-semantics trap above is visible in the data rather than only in this document.</p>
      </div>
    </section>"""

i = s.index(a)
j = s.index(b, i) + len(b)

new = """      <p>AUC is not a clinical unit. No one orders 0.75 of a scan. The last part of the script translates the
        model into the decision a clinician actually makes, in two complementary ways.</p>

      <h3><code>referral_table</code> — the screening cost table</h3>
      <p>For each cutoff it reports: how many DXA scans get ordered, how many cases that finds, how many are
        missed, the positive predictive value, and <strong>scans ordered per case found</strong>. The last
        row is always "scan all" — 100% sensitivity at maximum cost — so the trade-off is visible against
        the alternative of not triaging at all. The rewrite changed what score this table ranks on: it is now
        the <strong>nested-CV out-of-fold rank</strong>, not the leaderboard winner's score. That matters,
        because the leaderboard winner is chosen partly by luck on the rows it is then graded on, and a
        screening table built on it inherits that optimism.</p>

      <h3><code>threshold_sweep</code> — the sensitivity-first sweep</h3>
      <p>A separate, deliberately different forest: shallower (<code>max_depth=6</code>), larger leaves
        (<code>min_samples_leaf=15</code>), and weighted 3:1 in favour of catching cases. It is wrapped in
        <code>CalibratedClassifierCV</code> with sigmoid calibration, which matters: an uncalibrated forest's
        "0.30" is not a real 30% probability, and if you are going to set a clinical threshold at 0.30 then
        the number behind it had better mean something. The sweep then walks the cutoff down from 0.50 to
        0.25 and reports missed cases and scans flagged at each step.</p>

      <div class="note">
        <span class="note-label">Why lowering the threshold is the whole point</span>
        <p>The default 0.5 cutoff treats a missed case and a false alarm as equally bad. In screening they are
          not remotely equal: a false alarm costs one unnecessary scan, a missed case costs a hip fracture
          five years later. Both of these functions exist to let a clinician choose that trade-off explicitly
          rather than inherit a software default.</p>
      </div>

      <div class="note risk">
        <span class="note-label">Do not put these two tables on the same slide without this caveat</span>
        <p>They look contradictory and are not. They differ in <strong>two</strong> ways at once:</p>
        <ul>
          <li><strong>Different models.</strong> The referral table ranks on the nested-CV out-of-fold score,
            which is a pooled within-fold percentile and not any single model's output. The sweep uses the
            separate shallow, calibrated, 3:1-weighted forest, which scores <strong>0.753</strong> ROC-AUC —
            built for calibrated probabilities rather than maximum ranking.</li>
          <li><strong>Different meaning of "cutoff".</strong> The referral table's "0.50" means
            <em>flag the top 50% of scores</em>. In the sweep, "≥ 0.50" means <em>a predicted probability of
            0.50</em>. The same printed number denotes two different things, which is why each file carries
            its score type in a column on every row.</li>
        </ul>
        <p>There is no longer an osteoporosis referral table. It was withdrawn deliberately: at 76 events the
          power gate marks that target underpowered, and a screening-cost table implies a precision the
          sample cannot support. The previous version of this document presented one and called it "where
          triage actually pays" — that section is gone.</p>
      </div>

      <h3>Screening cost, osteopenia or worse — top-fraction cutoffs</h3>

      <div class="bleed">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr><th>Flag the top…</th><th class="num">Sensitivity</th><th class="num">DXAs ordered</th><th class="num">Cases found</th><th class="num">Missed</th><th class="num">PPV</th><th class="num">Scans per case</th></tr>
            </thead>
            <tbody>
              <tr class="row-hi"><td>50%</td><td class="num">66.4%</td><td class="num">561</td><td class="num">428</td><td class="num">217</td><td class="num">76.3%</td><td class="num">1.31</td></tr>
              <tr><td>40%</td><td class="num">55.5%</td><td class="num">445</td><td class="num">358</td><td class="num">287</td><td class="num">80.4%</td><td class="num">1.24</td></tr>
              <tr><td>35%</td><td class="num">50.2%</td><td class="num">390</td><td class="num">324</td><td class="num">321</td><td class="num">83.1%</td><td class="num">1.20</td></tr>
              <tr><td>30%</td><td class="num">44.0%</td><td class="num">335</td><td class="num">284</td><td class="num">361</td><td class="num">84.8%</td><td class="num">1.18</td></tr>
              <tr><td>25%</td><td class="num">37.1%</td><td class="num">278</td><td class="num">239</td><td class="num">406</td><td class="num">86.0%</td><td class="num">1.16</td></tr>
              <tr><td><em>scan everyone</em></td><td class="num">100%</td><td class="num">1,111</td><td class="num">645</td><td class="num">0</td><td class="num">58.1%</td><td class="num">1.72</td></tr>
            </tbody>
          </table>
        </div>
        <caption>Ranked on nested-CV out-of-fold score. Because 58% of this cohort is affected, the efficiency
          gain is modest by construction — you cannot do much better than 1.72 scans per case when more than
          half the room is a case. The honest summary is that triaging for osteopenia saves roughly a quarter
          of the scanning effort per case found, at the cost of missing a third of cases.</caption>
      </div>

      <h3>The sensitivity-first sweep</h3>

      <p>The calibrated forest, with real probability cutoffs, on the osteopenia target. This is the table
        that answers "what if we are willing to over-refer in order to miss almost nobody".</p>

      <div class="bleed">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr><th>Probability cutoff</th><th class="num">Sensitivity</th><th class="num">DXAs ordered</th><th class="num">Cases found</th><th class="num">Missed</th><th class="num">PPV</th><th class="num">Scans per case</th></tr>
            </thead>
            <tbody>
              <tr><td>≥ 0.50</td><td class="num">75.0%</td><td class="num">681</td><td class="num">484</td><td class="num">161</td><td class="num">71.1%</td><td class="num">1.41</td></tr>
              <tr class="row-hi"><td>≥ 0.40</td><td class="num">89.6%</td><td class="num">887</td><td class="num">578</td><td class="num">67</td><td class="num">65.2%</td><td class="num">1.53</td></tr>
              <tr><td>≥ 0.35</td><td class="num">94.3%</td><td class="num">971</td><td class="num">608</td><td class="num">37</td><td class="num">62.6%</td><td class="num">1.60</td></tr>
              <tr><td>≥ 0.30</td><td class="num">98.0%</td><td class="num">1,039</td><td class="num">632</td><td class="num">13</td><td class="num">60.8%</td><td class="num">1.64</td></tr>
              <tr><td>≥ 0.25</td><td class="num">99.2%</td><td class="num">1,087</td><td class="num">640</td><td class="num">5</td><td class="num">58.9%</td><td class="num">1.70</td></tr>
              <tr><td><em>scan everyone</em></td><td class="num">100%</td><td class="num">1,111</td><td class="num">645</td><td class="num">0</td><td class="num">58.1%</td><td class="num">1.72</td></tr>
            </tbody>
          </table>
        </div>
        <caption>Calibrated forest, ROC-AUC 0.753. The ≥ 0.40 row clears an 80% sensitivity target. But read
          the DXA column: at that cutoff the tool flags 887 of 1,111 women — 80% of the cohort. Pushing to
          99.2% sensitivity flags 98%. The "scan all" row is carried on this table too, so the comparison is
          always in front of you.</caption>
      </div>

      <div class="note caution">
        <span class="note-label">The uncomfortable arithmetic, stated plainly</span>
        <p>On a target with 58% prevalence, high sensitivity and useful triage are close to mutually
          exclusive. Missing only 5 of 645 cases requires scanning 1,087 of 1,111 women — at which point you
          have not built a triage tool, you have built an expensive way of saying "scan almost everyone".
          Every row of the sweep costs <em>more</em> scans per case than the "flag the top 50%" rule in the
          table above, and the 0.25 row (1.70) is barely better than scanning everyone (1.72). Expect a
          specialist to spot this immediately.</p>
        <p>The previous version of this document deferred to the osteoporosis table here, on the grounds that
          6% prevalence leaves real scanning effort to save. That is still true in principle, but the table
          is withdrawn: 76 events cannot support it, and the nested test says the ranking is not separable
          from OST at either threshold. Any claim in this direction belongs to "a cheap risk score"
          generally — which means OST — and not to this model.</p>
      </div>

      <div class="note good">
        <span class="note-label">And the calibration gap is closed</span>
        <p>Step 13 depends on its probabilities meaning something, and until this rewrite there was no
          calibration figure to check that — the only plotting code for one had been deleted with an earlier
          script. <code>calibration_curve.png</code> now ships: a reliability curve with the Brier score for
          both the raw and the sigmoid-calibrated forest. <strong>Calibrated 0.198 against raw 0.199.</strong>
          Essentially no improvement, which is itself the useful finding — this forest was already close to
          calibrated, so the <code>CalibratedClassifierCV</code> wrapper is insurance rather than a fix, and
          the probability cutoffs in the sweep above can be read as probabilities.</p>
      </div>

      <div class="note">
        <span class="note-label">Both tables are saved</span>
        <p>As <code>referral_table.csv</code> and <code>threshold_sweep.csv</code>. Each carries its score
          type and the model that produced it on every row, so the cutoff-semantics trap above is visible in
          the data rather than only in this document.</p>
      </div>
    </section>"""

s = s[:i] + new + s[j:]
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('referral section rewritten')
