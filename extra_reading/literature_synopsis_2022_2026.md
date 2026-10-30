# Literature synopsis, 2022–2026: what other studies found and how they published it

Compiled 2026-10-25. Companion to `literature_ml_vs_ost.md` (2026-10-02), which holds the
row-by-row comparison table. This file is the narrative version: one synopsis per paper, what it found,
**how it was written up and presented**, and how it differs from this project.

Sources were read from abstracts and, where open access, full text. Several publisher pages
(Springer, Nature, PubMed) blocked full-text access, so some details come from abstracts or from
how a review describes the paper. Those are marked **(abstract only)**. Several papers also contain
internal inconsistencies, noted where found. **Check the original before quoting any number on a
poster.**

### This project's numbers, for comparison

| Cohort | Target | Model (nested CV) | OST | Δ vs OST [95% CI] | Verdict |
|---|---|---|---|---|---|
| NH White, n = 1,111 (shipped) | Osteopenia+ (T ≤ −1.0) | 0.747 | 0.739 | +0.008 [−0.008, +0.025] | Not separable |
| NH White, n = 1,111 (shipped) | Osteoporosis (T ≤ −2.5) | 0.786 | 0.780 | +0.007 [−0.016, +0.030] | Not separable |
| All races, n = 2,820 (scratch run, not in pipeline) | Osteopenia+ | 0.757 | 0.751 | +0.007 [−0.001, +0.014] | Not separable |
| All races, n = 2,820 (scratch run, not in pipeline) | Osteoporosis | 0.822 | 0.800 | +0.021 [+0.008, +0.035] | Beats OST |

The cohort is postmenopausal women aged 50–65. The outcome is DXA, using the lowest of the femoral
neck and total hip T-scores. Predictors are questionnaire and exam variables only, with no lab values.

---

## 0. Papers with results close to this project

These papers report a best AUC of about **0.70–0.83**, or a gain over OST/OSTA or logistic
regression of about **+0.05 or less**. That's the same range as this project. Each row gives what the
paper **claimed** in its title or conclusion, and what its numbers **actually show**. Papers marked †
were checked in `literature_ml_vs_ost.md`. Papers marked ‡ are older than 2022 but are the closest
anchors and are cited by almost everyone in this area.

### 0.1 Summary table

| Paper | Population | Best model AUC | Comparator AUC | Gain | What they published (claim) | What the numbers say |
|---|---|---|---|---|---|---|
| **Wu et al. 2023**, *Prev Med Rep* | **NHANES postmenopausal women** | Bayesian network 0.764 (0.747–0.780) | Logistic regression 0.752 | +0.012 | A "predictive model" built on LR and a Bayesian network | The closest design to ours. The two methods are essentially tied |
| Shim et al. 2020, *Arch Osteoporos* ‡ † | KNHANES, 1,792 postmenopausal women | ANN 0.743 | LR 0.727 | +0.016 | ML models "can be used" to screen | Honest 5-fold CV on survey variables gives 0.65–0.74, with ML about equal to LR |
| Yoo/Kim 2013, *Yonsei Med J* ‡ † | KNHANES, 1,674 postmenopausal women | SVM 0.827 | OST 0.806; LR 0.809 | +0.021 | "SVM significantly better than OST" | Same gain as our all-race osteoporosis result. Plain LR also matched OST |
| Erjiang et al. 2021, *J Clin Densitom* ‡ † | Ireland DXA cohort, 11,594 women | XGBoost 0.833 | OSTi 0.810 | +0.023 | ML "improved" prediction | The authors themselves call the gain "small", and the CIs overlap |
| Ou Yang et al. 2021, *IJERPH* ‡ † | Taiwan check-up, 2,929 women > 50 | RF 0.811 | OSTA 0.734 | +0.08 | ML beat OSTA | In women, **LR (p = 0.08) and KNN were not significantly better than OSTA** |
| Makond et al. 2022, *Informatics* | 356 Thai postmenopausal women | Decision trees 0.64–0.77 | — | — | Decision-tree screening model | Differences between algorithms were **not statistically significant** |
| Qiu et al. 2024, *Front Artif Intell* † | Louisiana, 8,134 adults > 40 | DNN 0.848 | **OST 0.819** | +0.029 | Deep learning best | **With about 2,000 people, OST had the best AUC of all models (0.804).** OST beat SVM and KNN at full size |
| Xu et al. 2024, *Front Public Health* | NHANES 3,545 adults 50+ | **LR 0.785** | 5 ML models 0.73–0.78 | LR best | Recommended LR | Simple regression beat ML, including on a held-out NHANES cycle |
| Huang WC et al. 2025, *Bone Rep* † | Taiwan, 4,720 postmenopausal women | ANN 0.77 | OSTA 0.55 | +0.22 | ANN "significantly outperformed" OSTA | The ANN's 0.77 is in our range. OSTA at 0.55 is far below its usual 0.65–0.80, so the comparison is suspect. The predictors were OSTA's own inputs (age, height, weight, BMI) |
| Peng et al. 2025, *BMC Geriatrics* | 211 older adults at high cardiovascular risk | **LR 0.751** | SVM 0.72, RF 0.70, XGBoost 0.697, DT 0.69 | LR best | "Logistic regression outperformed machine learning" | Another null-for-ML result published as the headline |
| Zhang et al. 2025, *Arch Osteoporos* | NHANES 9,405 adults 50+ (both sexes) + Chinese external | GB 0.828 (external) | OST 0.781 | +0.047 | "Outperformed OST" | The final model uses only **weight, age, height**: body size is the signal. Mixed sexes widen the gap |
| Tang et al. 2026, *Front Endocrinol* † | NHANES 3,950 women 60+ + Chinese external | RF 0.80 → **0.74 external** | — | — | Interpretable ML with external validation | The AUC falls into our range once tested outside NHANES |
| Guo et al. 2026, *PLoS One* | 1,717 postmenopausal women in hospital wards (with labs) | Extra Trees 0.717 | LR 0.672 | +0.045 | Explainable ML | Even with bone-turnover labs, below 0.75. Calibration was poor |
| Chinese nationwide study 2026, *Osteoporos Int* (abstract only) | Chinese postmenopausal women, nationwide + 2 external cohorts | 0.775 internal; **0.750 / 0.744 external** | OSTA AUC not in the abstract | — | ML screening model with prospective fracture validation | External AUC is in our range. Reported as a **rule-out tool** (sensitivity 89–95%, NPV 91–93%) and validated against later fractures (HR 1.78) |
| Wang J et al. 2026, *BMC Musculoskelet Disord* † | NHANES older adults, 4,803 | LR nomogram 0.795 | — | — | A nomogram | Plain LR with 11 variables reaches about 0.80. Calibration and decision curves reported |
| Lao et al. 2026, *Niger Postgrad Med J* † | NHANES 2017–20, adults 60+, 3,422 | LR nomogram 0.793 | — | — | A nomogram | LR only, about 0.79 |
| Zhu et al. 2026, *Medicine* † | NHANES postmenopausal women with CKD | MLP 0.72 | — | — | AI model for osteoporosis risk | A modest AUC even in a high-risk subgroup. No CI calculated |
| Systematic review, *BMC Musculoskelet Disord* 2026 | 21 postmenopausal models | Pooled 0.77 | **ML 0.74 vs regression 0.75** | ≈0 | Models "good to excellent" but high risk of bias | No ML advantage across the field |
| Christodoulou et al. 2019, *J Clin Epidemiol* ‡ | 71 studies, 282 comparisons | — | — | **0.00** (low risk of bias) | "No performance benefit of ML over LR" | The reference finding for this whole pattern |
| Nayak et al. 2015, *Osteoporos Int* ‡ † | Meta-analysis of risk tools | OST mostly 0.60–0.80 | — | — | "Simpler instruments … performed as well as or better" than complex ones | Supports OST as the comparator to beat |

### 0.2 Synopses of the papers not described elsewhere in this file

**Wu et al. 2023, *Preventive Medicine Reports* — the closest match to this project.**
- **Data:** NHANES postmenopausal women in the US. The authors are based in China, but the data are
  NHANES.
- **Methods:** logistic regression compared with a Bayesian network model.
- **Results:** Bayesian network AUC **0.764 (0.747–0.780)**, LR **0.752**.
- **How published:** a public-health journal, framed as finding "related factors" and building a
  predictive model. The emphasis is on which risk factors matter, not on beating a benchmark.
- **What it means for us:** an independent NHANES postmenopausal analysis landed at 0.75–0.76, the same
  as our 0.747–0.757. It didn't compare against OST.

**Makond et al. 2022, *Informatics* (MDPI).**
- **Data:** 356 postmenopausal Thai women.
- **Methods:** four decision-tree algorithms (CART, QUEST, CHAID, C4.5).
- **Results:** AUC about **0.64–0.77**. The algorithms did **not differ significantly** in accuracy,
  sensitivity, specificity or AUC.
- **How published:** a decision-tree screening chart a clinician can follow by hand. The value
  offered is a simple flowchart, not a higher AUC.

**Peng, Zhang & Zhou 2025, *BMC Geriatrics*.**
- **Data:** 211 older adults at high cardiovascular risk.
- **Methods:** LR compared with decision tree, RF, SVM and XGBoost.
- **Results:** **LR 0.751** was best (SVM 0.72, RF 0.70, XGBoost 0.697, DT 0.69).
- **How published:** the title itself is "comparing ML and logistic regression", and the conclusion
  states LR outperformed ML. A clean example of a null-for-ML result as the headline.
- **Caveat:** very small sample, and it includes lab and genetic markers.

**Huang WC et al. 2025, *Bone Reports* (Kaohsiung VGH, Taiwan).**
- **Data:** 5,510 men aged 50 and over and 4,720 postmenopausal women, plus a separate validation
  cohort (610 men, 523 women).
- **Methods:** ML models using **only sex, age, height and weight**.
- **Results:** ANN **0.77 in women**, 0.67 in men, similar in the validation cohort. OSTA scored
  0.51–0.55.
- **How published:** "simple and user-friendly", framed as surpassing OSTA.
- **What it means for us:** the model AUC sits in our range using our core inputs. The large gain
  comes from an implausibly weak OSTA (usually 0.65–0.80). That's the opposite of our situation: our
  OST is in its normal range, which makes it a much tougher comparator.

**Chinese nationwide screening model, *Osteoporosis International* 2026 (abstract only).**
- **Data:** postmenopausal Chinese women from a nationwide sample, with two external cohorts and
  fracture follow-up.
- **Results:** AUC 0.798 training, 0.775 internal, **0.750 and 0.744 external**. At a rule-out
  threshold, sensitivity was 94.7% and 89.3%, and NPV 91.3% and 92.7%. Women classed as high risk had
  more later clinical fractures (HR 1.78, 95% CI 1.06–2.99).
- **How published:** a **rule-out tool** ("who can safely skip a scan") with **prospective fracture
  validation**. The authors didn't claim a high AUC. They showed the model was useful at a specific
  threshold, and linked predictions to real fractures.
- **What it means for us:** a published, nationwide, externally validated model in the same 0.74–0.78
  band. Framing it around ruling out scans and predicting fractures made a modest AUC worth
  publishing in a specialty journal.

**Shim et al. 2020, *Archives of Osteoporosis*.**
- **Data:** KNHANES, 1,792 postmenopausal Korean women, 613 with osteoporosis.
- **Methods:** 7 algorithms with 5-fold CV on survey and exam variables.
- **Results:** AUC **0.65–0.74**, ANN 0.743, LR 0.727.
- **How published:** ML presented as a screening aid, but the numbers show the same ceiling we found
  with honest CV on survey data.

### 0.3 What the published claims have in common

1. **Most of these papers say "ML is better" even when the numbers show a tie.** Only a few put the
   null result in the title (Peng 2025, Christodoulou 2019, Xu 2024 in its conclusion). Where formal
   tests were run, LR or simple tools were often not significantly worse (Ou Yang 2021, Makond 2022).
2. **Large gains over OST/OSTA come with a weak comparator** (Huang WC 2025: OSTA 0.55; Bui 2022:
   0.65). When OST performs in its normal range (0.73–0.82), the gain is +0.02 to +0.05 (Yoo, Erjiang,
   Qiu, Zhang).
3. **External validation pulls AUCs into the 0.74–0.80 band** (Tang 2026, Chinese nationwide 2026,
   Yang X 2025: 0.90 → 0.81 on NHANES).
4. **Modest AUCs got published by changing what's claimed, not by inflating the AUC:**
   - a rule-out threshold and fracture follow-up (Chinese nationwide 2026)
   - a hand-usable tool such as a decision tree or nomogram (Makond 2022, Wang J 2026, Lao 2026)
   - "LR is enough" as the finding (Peng 2025, Xu 2024)
   - risk-factor discovery (Wu 2023)
5. **None of these papers reports nested CV, a paired CI on the gain over OST, a duplicate-respondent
   audit or pre-specified tests together.** This project does all four.

---

## 1. Studies that compared ML directly with OST / OSTA

### Suh et al., *J Med Internet Res* 2023 — deep learning on NHANES + KNHANES
- **What they did:** a deep neural network on 8,274 NHANES and 8,680 KNHANES respondents (adults over
  50 or postmenopausal, both sexes pooled), predicting normal / osteopenia / osteoporosis by femoral
  neck or total femur BMD. They used LIME to explain individual predictions.
- **Results:** NHANES AUC 0.851 (femoral neck) and 0.922 (total femur); KNHANES 0.827 and 0.912. OST
  scored 0.759 on NHANES, OSIRIS 0.771, ORAI 0.704.
- **How published:** a full paper in a digital-health journal. The title leads with "interpretable"
  and "individualized feature analysis". Explaining predictions for one person at a time was the
  selling point.
- **How it differs from us:** wide age range and both sexes. The AUC is **micro-averaged across three
  classes**, which isn't directly comparable with OST's two-class AUC and is probably inflated. They
  report no formal test of the difference against OST.

### Zhang et al., *Archives of Osteoporosis* 2025 — gradient boosting vs OST (abstract only)
- **What they did:** 9,405 NHANES adults aged 50 and over (both sexes). They started from 13
  "clinically accessible" candidate predictors, selected with Lasso, compared 6 models and explained
  them with SHAP. External validation used a Chinese hospital cohort of about 3,500.
- **Results:** gradient boosting with **weight, age and height** only: test AUC 0.841, external
  **0.828 vs OST 0.781** (DeLong test p < 0.001). Gain: **+0.047**.
- **How published:** an osteoporosis specialty journal. The abstract leads with "outperformed OST",
  and the paper is framed as a "screening tool" with SHAP interpretability.
- **How it differs from us:** men are pooled with women and the age range runs to 85+. Height and sex
  carry signal there that they can't carry in women aged 50–65. Its 3-variable final model agrees
  with our finding that body size is the signal.
- **Caveat:** the 2026 medRxiv meta-analysis quotes this study as 0.841 vs 0.781, which pairs the
  test-set AUC with the external OST AUC.

### Wang et al., *Scientific Reports* 2025 — Tibetan women
- **What they did:** 645 middle-aged and older Tibetan women from a 2022–24 high-altitude survey,
  outcome T ≤ −2.5. Predictors were age and BMI **plus blood tests** (LDL, uric acid, creatinine, liver
  enzymes). 80/20 split.
- **Results:** XGBoost **0.848 vs OSTA 0.739** on the test set. RF had training AUC 1.000 against test
  0.772 (overfit), and the ANN (0.732) did worse than OSTA.
- **How published:** a general-science journal, framed as an option where DXA scanners are scarce.
- **How it differs from us:** uses labs, a single small test set of about 130 women, and no
  confidence interval on the gain.

---

## 2. NHANES ML studies with no OST comparison

### Xu et al., *Frontiers in Public Health* 2024 — logistic regression won
- **What they did:** 3,545 NHANES adults aged 50 and over (both sexes). **Trained on 2017–2020 and
  tested on 2013–2014 (temporal validation).** The outcome was femoral neck T < −1 or a self-reported
  diagnosis. They used 19 Lasso-selected predictors, including labs (ALP, CPK, cholesterol, HbA1c).
- **Results:** logistic regression 0.785 was the best of 6 models (SVM 0.780, GBM 0.775, ANN 0.771,
  RF 0.768, naive Bayes 0.729), with 0.78 on the held-out cycle. RF scored 1.0 on training data.
- **How published:** ROC curves, calibration curves and decision curves for all models, plus a SHAP
  summary for the LR model. They **recommended the simplest model** after weighing discrimination,
  calibration and net benefit together.
- **Relevance:** the closest template for holding out one NHANES cycle as a test set, and an example
  of "simple beat ML" being published.

### Huang et al., *BMC Med Inform Decis Mak* 2025 — body measurements only
- **What they did:** 13,133 NHANES adults over 50 (52% men), 2005–2020. Outcome T ≤ −1 at femoral
  neck or total femur. Predictors were **only demographics and body measurements**: age, sex,
  ethnicity, weight, height, BMI, waist, arm and leg measures.
- **Results:** CatBoost 0.822, XGBoost 0.808, SVM 0.782, LR 0.781. Top SHAP features were weight, sex,
  age, waist and ethnicity.
- **How published:** framed as "interpretable" screening from cheap measurements, with a SHAP summary
  plot as the centrepiece. A random 90/10 split, with no OST comparison.
- **How it differs from us:** sex is the second-strongest predictor. In women only, the same inputs
  give roughly our 0.757.

### Tang et al., *Frontiers in Endocrinology* 2026 — external validation drop
- **What they did:** 3,950 NHANES women aged 60 and over (2003–2020) for development. External
  validation used 338 women from a Chinese geriatrics department. 10 Lasso-selected predictors,
  including routine labs.
- **Results:** RF **0.80 internal, falling to 0.74 external.** Osteoporosis prevalence was 21%
  internally and 49% externally.
- **How published:** calibration plots, decision curves and SHAP rankings, plus a deployed tool that
  gives a probability for each patient. The abstract appears to swap sensitivity and specificity.
- **Relevance:** shows the size of the drop to expect when a model moves to a new population.

### Si et al. ("PrOsteoporosis"), *BMC Research Notes* 2025 — 0.97 AUC
- **What they did:** 8,766 NHANES respondents (2013–14 and 2017–20). Outcome was **"has a doctor ever
  told you that you had osteoporosis"** (self-reported). Predictors were narrowed from 223 to 18 and
  included prescription use, prior fracture and cancer history. Classes were balanced with
  borderline-SMOTE.
- **Results:** LightGBM test AUC **0.972**.
- **How published:** a short research note with a SHAP waterfall plot walking through one
  80-year-old woman.
- **How it differs from us:** a self-reported diagnosis means the woman has already been scanned. The
  predictors partly encode prior medical contact. SMOTE appears to have been applied before the
  split, so synthetic cases can reach the test set. Without SMOTE the AUC was about 0.83.

### Stacking ensemble, *BMC Med Inform Decis Mak* 2026 (abstract only)
- 3,735 NHANES respondents, test AUC 0.95 from age, sex, BMI, uric acid and others. The test set was
  reduced to 578 of 1,121 complete cases. No external validation.

---

## 3. Questionnaire and primary-care tools

### POST (Yang et al.), *JMIR Aging* 2023 — Hong Kong questionnaire tool
- **What they did:** 800 adults from 6 community clinics (73% women, mean age 61). Boruta selected
  from 113 questionnaire items. DXA at spine and femoral neck, 10.6% prevalence.
- **Results:** a 7-item naive Bayes model (age, sex, education, **height loss**, BMI, **number of teeth
  lost**, vitamin D supplement) scored **0.858**, with LR at 0.845. Sensitivity and specificity were
  both 0.83 at the cutoff.
- **How published:** positioned as a self-assessment tool for community or home use. It isn't
  compared head to head with OSTA; instead it argues POST balances sensitivity and specificity better
  than OSTA's published figures.
- **How it differs from us:** about 85 cases, a single 70/30 split and no external validation.

### Wändell et al., *Scientific Reports* 2025 — Stockholm primary care
- **What they did:** 338,151 primary-care patients aged 40 and over. Outcome was an **osteoporosis
  diagnosis code**, not DXA. Age- and sex-matched case-control design. Predictors were 174–320
  diagnosis codes plus visit counts. Stochastic gradient boosting.
- **Results:** AUC 0.92–0.95 across sex and age groups. **The strongest predictor was the number of
  primary-care visits in the previous year.**
- **How published:** ROC curves, confusion matrices and relative-influence charts. The authors state
  that clinical usefulness isn't established and external validation is needed.
- **How it differs from us:** the AUC measures who gets diagnosed, which tracks contact with the
  health system, not bone density.

### Zhang et al., *BioData Mining* 2026 — online calculator (abstract only)
- **What they did:** 18,179 participants, non-imaging clinical data, with **temporal validation**
  (3,432). Gradient boosting, CatBoost and XGBoost, explained with SHAP.
- **Results:** abnormal DXA AUC 0.845 development, **0.876 temporal**. A three-class version reached
  about 0.72–0.74 accuracy.
- **How published:** deployed as an **interactive online calculator with public code on GitHub.** A
  usable tool was part of the contribution.

---

## 4. Hospital study using labs

### Guo et al., *PLoS One* 2026 — labs didn't rescue it
- **What they did:** 1,717 postmenopausal women in orthopaedic wards at two Chinese hospitals. 30
  features including **bone-turnover markers, vitamin D and electrolytes**. Outcome was lumbar spine
  T ≤ −2.5. 10 algorithms.
- **Results:** Extra Trees **0.717** (LR 0.672). The authors report a poorly fitting calibration curve.
- **How published:** SHAP (age and BMI on top) and a decision curve. They acknowledge the AUC is
  below the 0.8 they cite as good.
- **Relevance:** counters the assumption that adding labs fixes performance.

---

## 5. The simple tools in women aged 50–64

### Zheng, Crandall et al., *JAMA Network Open* 2025 — WHI Bone Density Substudy
- **What they did:** 6,067 women aged 50–64 (mean 57.7), cross-sectional. Outcome was osteoporosis at
  any of femoral neck, total hip or lumbar spine (14.1% prevalence). Tested the USPSTF-recommended
  tools at their published cutoffs.
- **Results:** any site: **ORAI 0.663, OST 0.654, OSIRIS 0.633.** Femoral neck alone: about 0.80–0.83.
- **How published:** a **largely negative finding in a major general-medicine journal.** The
  conclusion is that the tools are "fair to moderate" in younger postmenopausal women. Results are
  given as AUC plus sensitivity and specificity at the official cutoffs.
- **Relevance:** the same tool scored 0.65 or 0.82 depending only on which bone site defined the
  outcome.

### Crete study, 2024 — 258 women aged 50–64
- OSIRIS 0.696 and OST 0.690 at T ≤ −2.5. Published conclusion: the analysis "failed to confirm clear
  superiority" of any tool. Another null result written up as the finding.

### Network meta-analysis, *Int J Nursing Studies* 2025
- 17 studies, 9,669 women with and 34,143 without osteoporosis. **SCORE, ORAI and OST are the more
  sensitive tools; FRAX and OSIRIS are the more specific.** No tool is best on both. Tools were ranked
  by SUCRA, a ranking score from network meta-analysis.

### USPSTF recommendation, 2025
- For postmenopausal women under 65 with risk factors, use a risk tool first, citing **OST or ORAI**
  for identifying osteoporosis. Notes that the tools are less well studied in Asian, Hispanic and
  Black women.

---

## 6. Systematic reviews and methodology anchors

| Review | Scope | Key results | Criticisms of the field |
|---|---|---|---|
| *BMC Musculoskelet Disord* 2026 (search to Aug 2023) | 21 postmenopausal models, 45,383 women | Pooled AUC **0.77**. **ML 0.74 vs regression 0.75.** Internal-only 0.76 vs externally validated 0.74 | **All high risk of bias.** Calibration in about 3 models. 4 externally validated. Mostly East Asian |
| Risk models for PMOP 2026 | 7 models, all Asian | Pooled 0.78. Publication-bias adjustment drops 0.845 → 0.795. Lab-based models about 0.92 (2 studies) | All under 20 events per predictor. **No study compared against OST** |
| medRxiv 2026 (preprint) | 33 ML studies, 2021–25 | Pooled **0.879**. Internal 0.897 vs external 0.868. Deep learning 0.909, imaging 0.905 | Smaller studies report higher AUCs (publication bias). Only 18% handled class imbalance. 45% assessed calibration |
| Christodoulou et al., *J Clin Epidemiol* 2019 | 71 studies, 282 LR-vs-ML comparisons | **No AUC difference in studies at low risk of bias**; ML looked better only in studies at high risk of bias | 68% had possibly biased validation; 79% didn't report calibration |
| Leslie et al., Manitoba 2013 | 18,315 women aged 50–64 | OST AUC **0.72** for osteoporotic BMD | Proposed a combined rule (FRAX ≥ 10% or OST < 1) reported as **42% referred, 72% of treatment-eligible captured, NPV 90%** |
| TRIPOD+AI, *BMJ* 2024 | Reporting guideline | 27 items for the paper, 13 for the abstract. Covers regression and ML | Calibration expected; enough of the model for others to use it (equation or code) |
| Smets et al., *JBMR* 2021 | ML review | — | New tools must at least show equivalence with existing tools. Common failures: unclear model selection, poor data splits, no external validation |

Christodoulou 2019 and Leslie 2013 are older than the 4-year window. They're included because they're
the standard references for "ML ≈ regression" and for reporting screening results as clinic counts.

---

## 7. Why the reported AUCs vary from 0.65 to 0.97

| Design choice | Typical effect on AUC | Example | This project |
|---|---|---|---|
| Outcome is self-reported diagnosis or a diagnosis code | Very large inflation | Si 2025 (0.97), Stockholm 2025 (0.92–0.95) | DXA T-score |
| Men pooled with women, or wide age range | Large inflation | Huang 2025 (0.822), Zhang 2025 (0.841), Suh 2023 (0.85–0.92) | Women 50–65 only |
| Lab values or imaging added | Variable, from none to large | Wang 2025 (0.848); but Guo 2026 (0.717) | Excluded by design |
| Which bone site defines the outcome | ±0.15 for the same tool | WHI: OST 0.65 any site vs 0.82 femoral neck | Lowest of femoral neck and total hip |
| Case-control design, or SMOTE before the split | Inflation | Stockholm 2025, Si 2025 | Real population, no synthetic cases |
| Single random split with a small test set | Noisy, usually optimistic | POST 2023, Wang 2025 | Nested CV + bootstrap CI |
| External or temporal validation | Usually −0.03 to −0.06 | Tang 2026 (0.80 → 0.74) | Not yet done |
| Comparator | Without OST any AUC looks good | Most studies | OST on the same folds |

Among clinical-predictor models in postmenopausal women, the pooled AUC is **0.75–0.78**. This
project's 0.747–0.822 sits in or slightly above that range.

---

## 8. How results in this area are published and presented

### Standard figures and tables
1. **ROC curves** for every model on one plot. Used in essentially every paper.
2. **SHAP plots:** a summary plot for overall importance, and a waterfall plot for one patient (Si 2025,
   Huang 2025, Tang 2026, Guo 2026, Zhang 2025). Suh 2023 used LIME instead.
3. **Calibration curves.** Often shown as a picture and called "good" with no slope or intercept.
4. **Decision curve analysis.** Now routine in 2024–26 papers (Xu, Tang, Guo, Zhang).
5. **Sensitivity and specificity** at a chosen cutoff, often with a confusion matrix.

### What stronger papers added
- **A usable tool:** a web calculator with public code (BioData Mining 2026) or a printed nomogram,
  which is common in Chinese papers.
- **Temporal validation** framed as a real-world test (Xu 2024, BioData Mining 2026).
- **The comparison with the simple tool in the headline** (Zhang 2025: "outperformed OST").
- **Clinic-level counts** instead of AUC alone: how many referred, how many captured, NPV (Leslie
  2013, Crandall 2014).

### How null or "simple is enough" results got published
- **The null result goes in the title:** Christodoulou 2019, "no performance benefit of machine
  learning over logistic regression"; Crete 2024, "failed to confirm clear superiority".
- **"The tools are only fair" as the headline:** Zheng/Crandall 2025 in *JAMA Network Open*.
- **Simplicity presented as the contribution:** Zhang 2025's 3-variable final model; Xu 2024
  recommending logistic regression.
- **Reported against a checklist** (TRIPOD+AI) so reviewers can see what was and wasn't done.

### What almost no paper reports, and this project does
- A paired 95% CI on the model-minus-OST difference
- Nested CV, with the gap between leaderboard and nested AUC reported
- Pre-specified add-on tests (arms), including the nulls
- A duplicate-respondent audit
- OST AUC by race
- A sensitivity check excluding women already on osteoporosis treatment

---

## 9. Implications for this project

1. **The results agree with the honest literature.** OST at 0.74–0.80 matches published OST
   performance in comparable groups. An ML gain of +0.007 to +0.021 is about the size of the +0.02 to
   +0.05 that studies with a plausible OST comparison report, and it's tested more strictly here.
2. **"ML ≈ OST" is publishable.** The 2019 and 2026 reviews, WHI 2025 and Crete 2024 all published
   results like this. The framing that works: equivalence (with a margin set by the specialist in
   advance), simplicity, and clinic-level counts.
3. **What to borrow:**
   - a temporal hold-out of one NHANES cycle (Xu 2024)
   - calibration slope and intercept
   - a decision curve against OST
   - a SHAP summary plot
   - scans per 1,000 women (Leslie 2013)
   - a TRIPOD+AI checklist
4. **Expect an outside dataset to score lower than internal validation** (Tang 2026: −0.06).

---

## Sources

- Suh et al. 2023, JMIR — https://www.jmir.org/2023/1/e40179
- Zhang et al. 2025, Arch Osteoporos — https://pubmed.ncbi.nlm.nih.gov/41123741/
- Wang et al. 2025, Sci Rep (Tibet) — https://www.nature.com/articles/s41598-025-95707-2
- Xu et al. 2024, Front Public Health — https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2024.1347219/full
- Huang et al. 2025, BMC Med Inform Decis Mak — https://pmc.ncbi.nlm.nih.gov/articles/PMC12465568/
- Tang et al. 2026, Front Endocrinol — https://www.frontiersin.org/journals/endocrinology/articles/10.3389/fendo.2025.1719698/full
- Si et al. 2025, BMC Res Notes — https://pmc.ncbi.nlm.nih.gov/articles/PMC11899459/
- Stacking ensemble 2026, BMC Med Inform Decis Mak — https://link.springer.com/article/10.1186/s12911-026-03350-2
- Yang et al. 2023 (POST), JMIR Aging — https://pmc.ncbi.nlm.nih.gov/articles/PMC10686208/
- Wändell et al. 2025, Sci Rep (Stockholm) — https://pmc.ncbi.nlm.nih.gov/articles/PMC12537854/
- Zhang et al. 2026, BioData Mining — https://link.springer.com/article/10.1186/s13040-026-00520-w
- Guo et al. 2026, PLoS One — https://pmc.ncbi.nlm.nih.gov/articles/PMC13293431/
- Zheng, Crandall et al. 2025, JAMA Netw Open — https://pmc.ncbi.nlm.nih.gov/articles/PMC11920839/
- Crete 2024 — https://pmc.ncbi.nlm.nih.gov/articles/PMC11609562/
- Network meta-analysis 2025, Int J Nurs Stud — https://pubmed.ncbi.nlm.nih.gov/40037005/
- USPSTF 2025 — https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/osteoporosis-screening
- BMC Musculoskelet Disord 2026 review — https://pmc.ncbi.nlm.nih.gov/articles/PMC12857129/
- Risk prediction models for PMOP 2026 — https://pmc.ncbi.nlm.nih.gov/articles/PMC12829196
- medRxiv 2026 meta-analysis — https://www.medrxiv.org/content/10.64898/2026.07.03.26357134v1.full
- Christodoulou et al. 2019 — https://pubmed.ncbi.nlm.nih.gov/30763612/
- Leslie et al. 2013 — https://pubmed.ncbi.nlm.nih.gov/23452870/
- TRIPOD+AI 2024 — https://pmc.ncbi.nlm.nih.gov/articles/PMC11019967/
- Smets et al. 2021, JBMR — https://asbmr.onlinelibrary.wiley.com/doi/10.1002/jbmr.4292
- Wu et al. 2023, Prev Med Rep — https://pmc.ncbi.nlm.nih.gov/articles/PMC10472296/
- Makond et al. 2022, Informatics — https://doi.org/10.3390/informatics9040083
- Peng, Zhang & Zhou 2025, BMC Geriatrics — https://pmc.ncbi.nlm.nih.gov/articles/PMC11954202
- Huang WC et al. 2025, Bone Rep — https://pmc.ncbi.nlm.nih.gov/articles/PMC11783436/
- Chinese nationwide screening model 2026, Osteoporos Int — https://pubmed.ncbi.nlm.nih.gov/42658240/
- Shim et al. 2020, Arch Osteoporos — https://pubmed.ncbi.nlm.nih.gov/33097976/
- Nayak et al. 2015, Osteoporos Int — https://pmc.ncbi.nlm.nih.gov/articles/PMC4401628/
- Yoo et al. 2013, Yonsei Med J — https://pmc.ncbi.nlm.nih.gov/articles/PMC3809875/
- Erjiang et al. 2021, J Clin Densitom — https://pubmed.ncbi.nlm.nih.gov/33187864/
- Ou Yang et al. 2021, IJERPH — https://pmc.ncbi.nlm.nih.gov/articles/PMC8305021/
- Qiu et al. 2024, Front Artif Intell — https://pmc.ncbi.nlm.nih.gov/articles/PMC11196804/
- Wang J et al. 2026, BMC Musculoskelet Disord — https://pmc.ncbi.nlm.nih.gov/articles/PMC13330492/
- Lao et al. 2026, Niger Postgrad Med J — https://pubmed.ncbi.nlm.nih.gov/42390513/
- Zhu et al. 2026, Medicine — https://pmc.ncbi.nlm.nih.gov/articles/PMC13008175/
- Yang X et al. 2025, Bone — https://pubmed.ncbi.nlm.nih.gov/40669588/
