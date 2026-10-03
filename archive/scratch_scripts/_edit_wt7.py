# -*- coding: utf-8 -*-
import io

p = 'Notes/project_walkthrough.html'
s = io.open(p, encoding='utf-8').read()

a = """      <p>This is the table the specialist will want, and the script generates it as
        <code>clinical_predictor_table.csv</code> plus a forest plot."""
b = """        osteoporosis literature, which is itself a form of validation: a pipeline this complicated
        rediscovering the textbook is evidence it is wired up correctly.</p>
    </section>"""

i = s.index(a)
j = s.index(b, i) + len(b)
old = s[i:j]

new = """      <p>This is the section the specialist will want, and it is the direct answer to "which variables
        actually matter". The rewrite answers it <strong>three different ways</strong>, because one way is
        not enough — and where the three disagree is itself the finding.</p>

      <div class="bleed">
        <div class="tbl-wrap">
          <table>
            <thead><tr><th>Method</th><th>The question it answers</th><th>Its blind spot</th></tr></thead>
            <tbody>
              <tr><td><strong>Odds ratio + CI</strong><br><span style="color:var(--ink-3);font-size:13px"><code>clinical_predictor_table.csv</code></span></td><td>Holding everything else fixed, how much does this variable move the odds?</td><td>Unstable when two variables measure the same thing. Says "we cannot separate these", which readers hear as "neither matters".</td></tr>
              <tr><td><strong>Permutation importance</strong><br><span style="color:var(--ink-3);font-size:13px">same file, ΔAUC columns</span></td><td>Shuffle this one column inside a fitted model. How much out-of-fold AUC is lost?</td><td>Measures what the <em>fitted</em> model relied on, not what is available. A model handed a substitute is not harmed.</td></tr>
              <tr><td><strong>Ablation</strong><br><span style="color:var(--ink-3);font-size:13px"><code>model_variable_ablation_*.csv</code><br><code>model_block_ablation_*.csv</code></span></td><td>Remove the variable entirely and refit everything from scratch. How much worse is the best achievable model?</td><td>Cannot see a variable whose information exists elsewhere in the panel — which is exactly what the block version is for.</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <h3>1 · Odds ratios: six of twenty columns have an interval that excludes 1</h3>

      <p>Adjusted odds ratios in clinically meaningful units, with 95% intervals from a stratified bootstrap,
        plus the ΔAUC from shuffling that column in the logistic model and in the forest.</p>

      <div class="bleed">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr><th>Predictor</th><th>Per</th><th class="num">OR</th><th class="num">95% CI</th><th>Direction</th><th class="num">ΔAUC (LR)</th><th class="num">ΔAUC (RF)</th><th class="num">Missing</th></tr>
            </thead>
            <tbody>
              <tr class="row-hi"><td><code>weight_kg</code></td><td>10 kg</td><td class="num">0.50</td><td class="num">0.38 – 0.62</td><td><span class="pill yes">protective</span></td><td class="num">+0.2438</td><td class="num">+0.1464</td><td class="num">0.0%</td></tr>
              <tr class="row-hi"><td><code>ever_used_estrogen</code></td><td>yes vs no</td><td class="num">0.63</td><td class="num">0.45 – 0.83</td><td><span class="pill yes">protective</span></td><td class="num">+0.0069</td><td class="num">+0.0030</td><td class="num">0.2%</td></tr>
              <tr class="row-hi"><td><code>poverty_income_ratio</code></td><td>1 unit</td><td class="num">0.90</td><td class="num">0.81 – 0.98</td><td><span class="pill yes">protective</span></td><td class="num">+0.0069</td><td class="num">+0.0195</td><td class="num">5.0%</td></tr>
              <tr class="row-hi"><td><code>age</code></td><td>5 years</td><td class="num">1.24</td><td class="num">1.03 – 1.51</td><td><span class="pill stop">risk</span></td><td class="num">+0.0090</td><td class="num">+0.0113</td><td class="num">0.0%</td></tr>
              <tr class="row-hi"><td><code>any_prior_fracture</code></td><td>yes vs no</td><td class="num">1.71</td><td class="num">1.15 – 2.73</td><td><span class="pill stop">risk</span></td><td class="num">+0.0063</td><td class="num">+0.0068</td><td class="num">0.0%</td></tr>
              <tr class="row-hi"><td><code>sedentary_min_day</code></td><td>1 hour/day</td><td class="num">1.06</td><td class="num">1.01 – 1.11</td><td><span class="pill stop">risk</span></td><td class="num">+0.0053</td><td class="num">+0.0016</td><td class="num">15.8%</td></tr>
              <tr><td><code>steroid_use</code></td><td>yes vs no</td><td class="num">1.50</td><td class="num">1.00 – 2.45</td><td><span class="pill no">ns</span></td><td class="num">+0.0041</td><td class="num">+0.0013</td><td class="num">0.5%</td></tr>
              <tr><td><code>family_hx_osteoporosis</code></td><td>yes vs no</td><td class="num">1.16</td><td class="num">0.85 – 1.64</td><td><span class="pill no">ns</span></td><td class="num">+0.0012</td><td class="num">+0.0035</td><td class="num">4.7%</td></tr>
              <tr><td><code>parental_hip_fracture</code></td><td>yes vs no</td><td class="num">1.17</td><td class="num">0.78 – 1.77</td><td><span class="pill no">ns</span></td><td class="num">+0.0004</td><td class="num">+0.0009</td><td class="num">4.4%</td></tr>
              <tr><td><code>bmi</code></td><td>5 kg/m²</td><td class="num">1.14</td><td class="num">0.81 – 1.58</td><td><span class="pill hold">sign flag</span></td><td class="num">+0.0003</td><td class="num">+0.0279</td><td class="num">0.1%</td></tr>
              <tr><td><code>vigorous_activity</code></td><td>yes vs no</td><td class="num">1.11</td><td class="num">0.72 – 1.79</td><td><span class="pill no">ns</span></td><td class="num">−0.0010</td><td class="num">−0.0001</td><td class="num">15.6%</td></tr>
              <tr><td><code>years_since_menopause</code></td><td>5 years</td><td class="num">1.10</td><td class="num">0.98 – 1.23</td><td><span class="pill no">ns</span></td><td class="num">+0.0063</td><td class="num">+0.0049</td><td class="num">2.0%</td></tr>
              <tr><td><code>phq9_score</code></td><td>5 points</td><td class="num">1.08</td><td class="num">0.91 – 1.28</td><td><span class="pill no">ns</span></td><td class="num">+0.0013</td><td class="num">−0.0001</td><td class="num">0.1%</td></tr>
              <tr><td><code>ever_smoked</code></td><td>yes vs no</td><td class="num">1.08</td><td class="num">0.82 – 1.37</td><td><span class="pill no">ns</span></td><td class="num">−0.0013</td><td class="num">−0.0000</td><td class="num">0.0%</td></tr>
              <tr><td><code>alcohol_drinks_day</code></td><td>1 drink/day</td><td class="num">0.99</td><td class="num">0.86 – 1.11</td><td><span class="pill no">ns</span></td><td class="num">−0.0000</td><td class="num">+0.0086</td><td class="num">13.6%</td></tr>
              <tr><td><code>meno_hysterectomy_ovaries_kept</code></td><td>vs natural</td><td class="num">0.93</td><td class="num">0.59 – 1.51</td><td><span class="pill no">ns</span></td><td class="num">+0.0006</td><td class="num">−0.0004</td><td class="num">0.0%</td></tr>
              <tr><td><code>sleep_hrs</code></td><td>1 hour</td><td class="num">0.92</td><td class="num">0.83 – 1.02</td><td><span class="pill no">ns</span></td><td class="num">+0.0031</td><td class="num">+0.0023</td><td class="num">0.4%</td></tr>
              <tr><td><code>meno_surgical_oophorectomy</code></td><td>vs natural</td><td class="num">0.89</td><td class="num">0.54 – 1.36</td><td><span class="pill no">ns</span></td><td class="num">−0.0008</td><td class="num">−0.0013</td><td class="num">0.0%</td></tr>
              <tr><td><code>diabetes</code></td><td>yes vs no</td><td class="num">0.88</td><td class="num">0.53 – 1.46</td><td><span class="pill no">ns</span></td><td class="num">+0.0005</td><td class="num">−0.0005</td><td class="num">0.0%</td></tr>
              <tr><td><code>meno_unknown</code></td><td>vs natural</td><td class="num">0.68</td><td class="num">0.40 – 1.11</td><td><span class="pill no">ns</span></td><td class="num">+0.0009</td><td class="num">+0.0009</td><td class="num">0.0%</td></tr>
            </tbody>
          </table>
        </div>
        <caption>All 20 model columns, sorted by |ΔAUC| in the logistic model. Highlighted rows are the six
          whose interval excludes an odds ratio of 1. "ns" means the interval includes 1 and the point
          estimate should not be interpreted. Three <code>meno_*</code> rows are one clinical variable
          against a reference level of natural menopause.</caption>
      </div>

      <p><strong>The six that clear the interval:</strong> lower weight (OR 0.50 per 10 kg — the largest
        effect in the table by a wide margin), ever having used oestrogen (0.63, protective), higher income
        relative to the poverty line (0.90 per unit, protective), older age (1.24 per 5 years), any prior
        fracture (1.71) and more sedentary time (1.06 per hour per day). <code>steroid_use</code> sits
        exactly on the boundary at 1.50 (1.00 – 2.45) and is reported as non-significant rather than rounded
        into significance.</p>

      <p>Everything else is statistically indistinguishable from no effect at this sample size. That is not a
        disappointing result — it is an accurate one, and stating it plainly is more useful to a clinician
        than a ranked list of twenty apparent effects. Note also what has <em>changed</em> from the previous
        version of this document: <code>postmenopausal</code> was previously reported as the second-strongest
        predictor at OR 2.13, and it is simply gone — it became a cohort filter, so within this cohort it is
        constant and can carry no signal. A predictor that strong disappearing on a definition change is
        itself worth understanding: it was largely encoding "is this woman older", which age already carries.</p>

      <h3>2 · Single-variable ablation: remove it and refit everything</h3>

      <p>Permutation importance asks what the fitted model leaned on. Ablation asks a harder question — drop
        the variable, refit all eight models from scratch, and see whether the <em>best achievable</em> model
        is any worse. With a paired bootstrap CI and a Holm correction across the eighteen tests.</p>

      <div class="bleed">
        <div class="tbl-wrap">
          <table>
            <thead><tr><th class="num">#</th><th>Variable dropped</th><th class="num">ΔAUC</th><th class="num">95% CI</th><th class="num">p (1-sided)</th><th class="num">p (Holm)</th></tr></thead>
            <tbody>
              <tr class="row-hi"><td class="num">1</td><td><code>weight_kg</code></td><td class="num"><strong>+0.0203</strong></td><td class="num">[+0.009, +0.032]</td><td class="num">&lt;0.001</td><td class="num"><strong>&lt;0.001</strong></td></tr>
              <tr><td class="num">2</td><td><code>poverty_income_ratio</code></td><td class="num">+0.0019</td><td class="num">[−0.002, +0.006]</td><td class="num">0.21</td><td class="num">1.00</td></tr>
              <tr><td class="num">3</td><td><code>ever_used_estrogen</code></td><td class="num">+0.0033</td><td class="num">[−0.002, +0.008]</td><td class="num">0.11</td><td class="num">1.00</td></tr>
              <tr><td class="num">4</td><td><code>sedentary_min_day</code></td><td class="num">+0.0032</td><td class="num">[−0.002, +0.008]</td><td class="num">0.10</td><td class="num">1.00</td></tr>
              <tr><td class="num">9</td><td><code>bmi</code></td><td class="num">−0.0002</td><td class="num">[−0.001, +0.001]</td><td class="num">0.64</td><td class="num">1.00</td></tr>
              <tr><td class="num">10</td><td><code>age</code></td><td class="num">+0.0018</td><td class="num">[−0.003, +0.007]</td><td class="num">0.21</td><td class="num">1.00</td></tr>
              <tr><td class="num">13</td><td><code>menopause_type</code> <span style="color:var(--ink-3)">(3 cols)</span></td><td class="num">−0.0000</td><td class="num">[−0.003, +0.003]</td><td class="num">0.53</td><td class="num">1.00</td></tr>
              <tr><td class="num">18</td><td><code>ever_smoked</code></td><td class="num">−0.0013</td><td class="num">[−0.004, +0.001]</td><td class="num">0.84</td><td class="num">1.00</td></tr>
            </tbody>
          </table>
        </div>
        <caption>Selected rows from all eighteen; full grid in <code>model_variable_ablation_osteopenia.csv</code>.
          A positive Δ means the full panel is better. Negative values are noise — dropping the variable
          happened to help by less than the fold-to-fold error.</caption>
      </div>

      <p><strong>One variable out of eighteen survives multiple-comparison correction, and it is weight.</strong>
        Every other single variable can be deleted from the panel without any measurable loss. That includes
        <code>age</code>, <code>bmi</code> and the entire <code>menopause_type</code> categorical.</p>

      <h3>3 · Block ablation: the table that resolves the disagreement</h3>

      <p>Single-variable ablation has an obvious hole. Drop <code>bmi</code> and the model reads
        <code>weight_kg</code> instead; drop <code>weight_kg</code> and it reads <code>bmi</code>. Each looks
        disposable alone while the pair is indispensable. The block ablation drops whole clinical groups at
        once, which is the only way to see that.</p>

      <div class="bleed">
        <div class="tbl-wrap">
          <table>
            <thead><tr><th>What is removed</th><th class="num">Vars left</th><th class="num">AUC</th><th class="num">Δ vs full panel</th><th class="num">95% CI</th><th>Verdict</th></tr></thead>
            <tbody>
              <tr class="row-hi"><td><strong>body size</strong> — <code>bmi</code> + <code>weight_kg</code></td><td class="num">16</td><td class="num"><strong>0.606</strong></td><td class="num"><strong>+0.150</strong></td><td class="num">[+0.114, +0.184]</td><td><span class="pill stop">panel wins</span></td></tr>
              <tr><td>all menopause / hormone variables</td><td class="num">15</td><td class="num">0.753</td><td class="num">+0.004</td><td class="num">[−0.003, +0.011]</td><td><span class="pill no">no difference</span></td></tr>
              <tr><td>all lifestyle variables</td><td class="num">14</td><td class="num">0.756</td><td class="num">+0.001</td><td class="num">[−0.005, +0.007]</td><td><span class="pill no">no difference</span></td></tr>
              <tr><td>all history / family variables</td><td class="num">14</td><td class="num">0.753</td><td class="num">+0.003</td><td class="num">[−0.004, +0.010]</td><td><span class="pill no">no difference</span></td></tr>
              <tr><td><em>keep only</em> <code>age</code> + <code>weight_kg</code> — OST's two inputs</td><td class="num">2</td><td class="num">0.739</td><td class="num">+0.018</td><td class="num">[+0.001, +0.035]</td><td><span class="pill hold">panel wins slightly</span></td></tr>
              <tr><td><em>keep only</em> <code>age</code> + <code>bmi</code></td><td class="num">2</td><td class="num">0.718</td><td class="num">+0.039</td><td class="num">[+0.018, +0.060]</td><td><span class="pill hold">panel wins</span></td></tr>
            </tbody>
          </table>
        </div>
        <caption>Full panel AUC 0.757 (Ridge → T-score, the primary model chosen per fold). Paired stratified
          bootstrap, 500 resamples. From <code>model_block_ablation_osteopenia.csv</code>.</caption>
      </div>

      <div class="note risk">
        <span class="note-label">If you take one thing from this document, take this</span>
        <p><strong>Body size is very nearly the only thing the model knows.</strong> Remove
          <code>weight_kg</code> and <code>bmi</code> and performance falls from 0.757 to <strong>0.606</strong>
          — a 0.150 collapse, with an interval nowhere near zero. Remove the menopause block, the lifestyle
          block or the history block <em>in its entirety</em> and the model loses 0.004, 0.001 and 0.003
          respectively — all three intervals straddle zero. Sixteen of the eighteen variables, taken
          together, are worth less than the measurement error.</p>
        <p>And the bottom two rows close the argument. <code>age</code> + <code>weight_kg</code> alone scores
          <strong>0.739</strong> — which is OST's own AUC on this cohort, to three decimals, because those
          are OST's two inputs. Everything the eighteen-variable panel adds on top of a scale and a date of
          birth is +0.018 AUC, and once model selection is moved inside the cross-validation folds even that
          margin loses its significance. <em>That is the whole reason the headline claim does not
          survive.</em></p>
      </div>

      <h3>Why the three methods disagreed about BMI, and which one was right</h3>

      <p><code>bmi</code> is the cleanest illustration in the dataset of why one importance measure is never
        enough:</p>

      <ul>
        <li><strong>Odds ratio:</strong> 1.14 (0.81 – 1.58), non-significant — and pointing the
          <em>wrong way</em>, which trips the sign alarm.</li>
        <li><strong>Permutation importance:</strong> +0.0279 in the forest — second highest of all twenty
          columns.</li>
        <li><strong>Single-variable ablation:</strong> −0.0002. Ranked 9th of 18. Indistinguishable from
          deleting nothing.</li>
        <li><strong>Block ablation, paired with weight:</strong> +0.150. The largest effect measured anywhere
          in this project.</li>
      </ul>

      <p>All four are correct, and together they say one thing: <strong>BMI and weight are pure substitutes
        here</strong>, correlated at |r| = 0.94 on this cohort. The fitted forest leans on BMI (hence the
        permutation number), but nothing is lost by taking it away because weight carries the same
        information (hence the ablation zero), and the odds ratio is unstable for exactly that reason — weight
        has absorbed the protective effect and BMI is left fitting a residual, which is why its sign inverts.
        The pair is what matters, which only the block test can see.</p>

      <div class="note">
        <span class="note-label">What to say when asked "which variables are important?"</span>
        <p>Quote the <strong>block ablation</strong>. It is the only one of the three that answers the
          question a clinician is actually asking — "what do I need to collect?" — rather than "what did
          this particular fitted model happen to lean on?". The answer is: a scale, and the patient's age.
          The other sixteen variables are, on this cohort and at this sample size, not measurably worth
          collecting.</p>
      </div>

      <p>The clinical picture is otherwise entirely conventional — lighter, older women with a fracture
        history, more sedentary time and no oestrogen exposure are at higher risk. Nothing here contradicts
        the osteoporosis literature, which is itself a form of validation: a pipeline this complicated
        rediscovering the textbook is evidence it is wired up correctly. What it does contradict is the idea
        that the textbook needed a machine-learning pipeline to find.</p>
    </section>"""

s = s[:i] + new + s[j:]
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('predictors section rewritten')
