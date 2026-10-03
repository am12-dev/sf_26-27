# -*- coding: utf-8 -*-
import io

p = 'Notes/project_walkthrough.html'
s = io.open(p, encoding='utf-8').read()


def cut(a, b):
    i = s.index(a)
    j = s.index(b, i) + len(b)
    return s[i:j]


def swap(old, new, label):
    global s
    assert s.count(old) == 1, 'count %d for %s' % (s.count(old), label)
    s = s.replace(old, new)
    print('  ok', label)


# ===================================================== leaderboard prevalence line
swap("""      <p>Target: <code>at_risk</code>, T ≤ −1.0, prevalence 56.3%. AUC is the probability that the model
        scores a randomly chosen affected woman higher than a randomly chosen unaffected one: 0.5 is a coin
        flip, 1.0 is perfect.</p>""",
     """      <p>Target: <code>at_risk</code>, T ≤ −1.0, prevalence 58.1%. AUC is the probability that the model
        scores a randomly chosen affected woman higher than a randomly chosen unaffected one: 0.5 is a coin
        flip, 1.0 is perfect.</p>

      <div class="note risk">
        <span class="note-label">These are not the numbers to quote</span>
        <p>The leaderboard exists to be <em>compared against</em> the nested-CV estimate, not to be reported.
          Fitting eight models and reporting the best is upward-biased by construction. The defensible
          figures are in <a href="#honesty">the honesty checks</a>; the script prints
          <em>"Do NOT quote the leaderboard figure as a result for this target"</em> beneath this very
          table.</p>
      </div>""",
     'leaderboard prevalence + caveat')

# ===================================================== leaderboard table + how to read
old = cut("""              <tr class="row-hi"><td><strong>Random Forest</strong></td><td class="num"><strong>0.810</strong></td>""",
          """          quote the two together.</p>
      </div>
    </section>""")

new = """              <tr class="row-hi"><td><strong>Logistic Regression (L2)</strong></td><td class="num"><strong>0.755</strong></td><td class="num">0.770</td><td class="num">—</td><td class="num">67.9%</td><td class="num">67.8%</td></tr>
              <tr><td>Elastic Net Logistic Regression</td><td class="num">0.754</td><td class="num">0.769</td><td class="num">—</td><td class="num">67.9%</td><td class="num">67.6%</td></tr>
              <tr><td>Random Forest</td><td class="num">0.753</td><td class="num">1.000</td><td class="num">0.753</td><td class="num">67.6%</td><td class="num">68.5%</td></tr>
              <tr><td>LightGBM (aggressive reg.)</td><td class="num">0.742</td><td class="num">0.813</td><td class="num">—</td><td class="num">62.0%</td><td class="num">72.7%</td></tr>
              <tr><td>XGBoost (aggressive reg.)</td><td class="num">0.739</td><td class="num">0.837</td><td class="num">—</td><td class="num">63.9%</td><td class="num">71.2%</td></tr>
            </tbody>
          </table>
        </div>
        <caption>Five-fold cross-validated, five classifiers; three T-score regressors are scored alongside
          them and enter the nested selection. Sensitivity and specificity are at the default 0.5 probability
          cutoff — see <a href="#referral">Scans per case found</a> for what happens when that cutoff moves.
          The forest's train AUC of 1.000 is inflated by construction; 0.753 out-of-bag is its honest
          in-sample number, and it happens to land exactly on its test AUC.</caption>
      </div>

      <h3>How to read this</h3>
      <ul>
        <li><strong>Nothing wins.</strong> The top three models are separated by 0.002 AUC — logistic
          regression 0.755, elastic net 0.754, random forest 0.753 — which is far inside the fold-to-fold
          noise of about 0.021. <em>This is a change of finding.</em> The previous version of this document
          reported the forest winning clearly at 0.810 against 0.753 for the linear models, and read that gap
          as evidence of real non-linear structure. On the corrected cohort the gap is gone. The forest's
          advantage was being manufactured by duplicated women: a tree that memorises a training row scores
          it perfectly when the same woman reappears in the test fold, and a forest memorises every row.
          Linear models, which cannot memorise, were the ones telling the truth all along.</li>
        <li><strong>The boosters come last</strong>, by about 0.014, which is a direct consequence of how
          hard they were regularised. That was the right call for n = 1,111, but a less-constrained booster
          was not systematically searched.</li>
        <li><strong>L2 and elastic net are indistinguishable</strong> (0.755 vs 0.754). With 18
          pre-specified predictors there is nothing much for a sparsity penalty to remove.</li>
        <li><strong>The forest's train/test gap is as alarming as ever and still means nothing</strong> —
          1.000 in-sample against 0.753 out. Its out-of-bag AUC is 0.753, identical to its test AUC, which is
          the cleanest possible demonstration that the gap is an artifact of bagging rather than
          overfitting in any actionable sense.</li>
        <li><strong>Balanced, not skewed</strong> — roughly 68% sensitivity and 68% specificity at the
          default cutoff. No model is achieving its AUC by flagging everyone.</li>
      </ul>

      <div class="note risk">
        <span class="note-label">The number that takes 0.755's meaning away</span>
        <p>By itself, 0.755 is unreadable. The comparison that makes it interpretable is that
          <strong>OST — weight minus age, times 0.2 — scores 0.739 on the same folds</strong>, and
          <strong>weight on its own scores 0.737</strong>. So eighteen variables, a diet survey and eight
          models buy about +0.016 AUC over a formula you can do in your head — and once model selection is
          moved inside the folds, that margin does not survive its own confidence interval. Always quote the
          two together; quoting the first alone is the single easiest way to misrepresent this project.</p>
      </div>
    </section>"""

assert s.count(old) == 1
s = s.replace(old, new)
print('  ok leaderboard table + read')

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('written')
