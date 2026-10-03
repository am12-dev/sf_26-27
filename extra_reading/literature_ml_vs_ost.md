# Literature: ML / multivariable models vs OST/OSTA for DXA-defined osteoporosis / low BMD

Compiled 2026-10-02. Sources: Europe PMC abstracts + open-access full texts (PMC), PubMed/publisher pages. Every row was checked against the abstract and, where a PMC full text was available, the full text. If a field could not be checked it is marked **not reported** (the paper does not give it) or **unverified** (I could not access or confirm it).

Context for comparison (student project, NHANES postmenopausal women): best ML nested-CV AUC was **0.790** for osteoporosis and **0.751** for osteopenia, vs OST **0.780 / 0.739**, a statistical tie. An earlier version had duplicated respondents across cycles, which pushed RF AUC up to 0.84.

OST = 0.2 x (weight kg - age yr). OSTA is the same formula, validated in Asian populations. OSTi is the Irish name for the same index.

---

## Table A. Studies that compare ML/multivariable models against OST / OSTA

| # | First author, year, journal | Dataset | n | Target (site) | Best model, AUC | OST/OSTA AUC (same data) | CI / test of AUC difference vs OST | Validation | Notable concerns |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Kim SK, 2013, IEEE EMBC (PMID 24109656) | KNHANES V-1 (2010), Korean postmenopausal women | unverified (likely same cohort as #2) | Osteoporosis (T <= -2.5, site unverified) | SVM, 0.827 (test) | not given in abstract | Says SVM was "significantly better" than OST; which test was used is unverified | Train/test split | Conference paper. Same group and data as #2. |
| 2 | Yoo TK, 2013, Yonsei Med J (PMID 24142634, PMC3809875) | KNHANES V-1, Korean postmenopausal women | 1,674 (1,000 train / 674 test) | Osteoporosis T <= -2.5 at total hip, FN or LS | SVM, 0.827 (test); 0.822 in 10-fold CV on training set | **0.806** (test); 0.794 (training CV). ORAI 0.791, SCORE 0.766, OSIRIS 0.787 | Wilcoxon signed-rank test across the 10 CV folds (SVM vs OST p = 0.037). Test-set ROC comparison reported as significant | 60/40 split + 10-fold CV in training | Margin over OST on the test set is only +0.021. LR test-set AUC was 0.809, also about equal to OST. Single split. No calibration. |
| 3 | Ou Yang WY, 2021, IJERPH (PMID 34300086, PMC8305021) | Taiwan health check-up cohort, age > 50 | 3,053 men, 2,929 women | Osteoporosis (DXA) | Men RF 0.843; women RF 0.811 (test) | OSTA men **0.766**, women **0.734** | 95% CIs and DeLong p-values for each model vs OSTA. Women: KNN (p = 0.36) and LR (p = 0.08) were **not** significantly better than OSTA | Train/test split | Single centre, no external validation. Plain LR was close to ML. |
| 4 | Erjiang E, 2021, J Clin Densitom (PMID 33187864) | DXA-HIP cohort, West of Ireland (2000-2018) | 13,577 (11,594 women) | Osteoporosis by lowest T-score (modified ISCD) | XGBoost, women 0.833 (0.812-0.853); men 0.768 | OSTi women **0.810** (0.787-0.833); men 0.723 | 95% CIs for each AUC. The CIs overlap in women. A paired test is unverified | 80/20 stratified split | Authors call the gain "small" (+2.3% in women). Convenience referral cohort. |
| 5 | Bui HM, 2022, Sci Rep (PMID 36418408, PMC9684431) | Northern Vietnam, women > 50 | unverified | Osteoporosis | RF, 0.854 (0.825-0.881) | OSTA **0.654** (0.606-0.702) | 95% CIs; Brier scores | Development/validation split | OSTA was unusually weak here. Includes blood tests. |
| 6 | Suh B, 2023, J Med Internet Res (PMID 36482780, PMC9883743) | **NHANES 2005-06, 2007-08, 2009-10, 2013-14** (age > 50 or postmenopausal) + KNHANES 2008-11 | 8,274 NHANES; 8,680 KNHANES | Normal / osteopenia / osteoporosis by FN or total femur T-score (multiclass) | Deep NN: NHANES FN 0.851 (0.844-0.858), total femur 0.922 | NHANES OST **0.759**, OSIRIS 0.771, ORAI 0.704 | CIs for the DL model only. Formal test vs OST unverified | 5-fold CV | Reports **micro-averaged multiclass AUC**, which is not directly comparable with binary OST AUC (and probably inflated). Sexes pooled. |
| 7 | Qiu C, 2024, Front Artif Intell (PMID 38919268, PMC11196804) | Louisiana Osteoporosis Study, age > 40 | 8,134 | Hip T <= -1.0 (i.e., low BMD/osteopenia+) | DNN, 0.848 | **OST 0.819**. RF 0.828, ANN 0.839, SVM 0.785 | No CI or paired test vs OST. AUCs are averages over 10 hold-out sets | 10 repeated hold-out splits | OST beat SVM and KNN. At 25% of the sample (about 2,000), **OST had the best AUC (0.804) of all models**. Men and women pooled. |
| 8 | Je M, 2025, BMC Womens Health (PMID 40155887, PMC11951505) | KoGES Ansan/Ansung cohort, women 40-69 | 4,199 | Osteoporosis | XGBoost, AUC about 0.84 (figure) | OST AUC in figure only, numeric value unverified (OST accuracy 0.670) | No CI or test reported | Train/validation split | 122 candidate predictors, including genetics. |
| 9 | Huang WC, 2025, Bone Rep (PMID 39896106, PMC11783436) | Kaohsiung VGH, Taiwan: men >= 50, postmenopausal women | 5,510 men + 4,720 women; separate validation cohort 610 + 523 | Osteoporosis | ANN, men 0.67, women 0.77 | OSTA men **0.51**, women **0.55** | 95% CIs and p-values vs OSTA | Internal + separate (temporal/second) cohort | OSTA AUC about 0.5 is far below published values (about 0.65-0.80). This suggests a problem with how OSTA was implemented, or with the cohort. Predictors were only age, height, weight and BMI, nearly the same inputs as OSTA. |
| 10 | Wang P, 2025, Sci Rep (PMID 40164752, PMC11958675) | Tibet, middle-aged/elderly women, cluster sample 2022-24 | unverified | Osteoporosis | XGB, 0.848 (test) | OSTA **0.739** | No CI or test of difference | 80/20 split | RF had training AUC 1.000 vs test 0.772 (overfit). ANN (0.732) did worse than OSTA. Small sample. |
| 11 | Zhang Y, 2025, Arch Osteoporos (PMID 41123741) | **NHANES** (US adults >= 50; cycles unverified) for development; external: Second Hospital of Lanzhou Univ., China | 9,405 development; 3,500 external | Osteoporosis | Gradient boosting (weight, age, height): test 0.841; external **0.828** | OST **0.781** (external) | **DeLong test** (z = 10.88, p < 0.001) in the external cohort | 70/30 split + external validation | Closest analogue to the student project. A +0.047 gain from GB on age/weight/height alone. Sexes pooled. Full text not accessed. |
| 12 | Teng X, 2026, EClinicalMedicine (PMID 42016607, PMC13092471) | Shanghai Sixth People's Hospital women 50-90; 2 external cohorts | 5,745 dev; 1,839 + 305 external | Osteoporosis | Stacked ensemble (11 vars incl. 8 serum markers): internal 0.943; external 0.958 / 0.917 | OSTA: "superior to OSTA in risk stratification". OSTA AUC unverified | CIs reported for model AUCs. Test vs OSTA unverified | Split + 2 external + prospective follow-up | AUC above 0.9 from routine labs is very high for this task. Hospital (referral) population. |

## Table B. NHANES-based ML / multivariable models (no OST comparison unless noted)

| # | First author, year, journal | NHANES cycles / population | n | Target (site) | Best model, AUC | OST compared? | CI / test | Validation | Notable concerns |
|---|---|---|---|---|---|---|---|---|---|
| 13 | Huang W, 2025, BMC Med Inform Decis Mak (PMID 41013448, PMC12465568) | 2005-2020, adults > 50, both sexes | 13,133 | **Low BMD (T <= -1)** | CatBoost 0.822 (test), using demographics and anthropometrics only | No (OSTi discussed only in the introduction) | not reported (test-set CI) | Split + 5-fold CV | Pooling men and women raises AUC (sex is a strong predictor). Most comparable to the student's osteopenia target (0.751), but in a different population. |
| 14 | Karaismailoglu E, 2025, Balkan Med J (PMID 41169086, PMC12576511) | 2005-10, 2013-14, 2017-20; age >= 50, FN/total femur | 12,108 | Low BMD | Extra Trees 0.852 (0.842-0.867) | No | 95% CIs | Split + 10-fold CV; preprocessing in a "strictly nested pipeline" | Both sexes; sex is the top predictor. 57 features. |
| 15 | Si Z, 2025, BMC Res Notes (PMID 40069865, PMC11899459) | NHANES (cycles unverified) | 8,766 (933 OP) | Osteoporosis | LightGBM 0.972 (test) | No | not reported | 80/20 split | **Probable leakage.** Borderline-SMOTE was used to balance the *whole* dataset (7,833 per class) before the train/test split, so the test set contains synthetic points. AUC without SMOTE was about 0.83. Height was the top predictor (possibly an artefact of pooling sexes). |
| 16 | Carvalho FR, 2025, Comput Biol Med (PMID 40328025) | 2007-2014, age >= 50 | 7,924 | Osteoporosis labelled with "WHO densitometric standards **and anthropometric risk factors**" | Stacking ensemble 0.94 | No | CV mean 0.929 +/- 0.030 | Split + CV | **Label leakage risk.** The outcome definition uses anthropometric factors that are also predictors (weight, arm circumference, BMI). |
| 17 | Li H, 2025, Digital Health (PMID 40656854, PMC12246659) | 2005-10, 2013-14, 2017-18; CKD patients | 3,796 CKD | Osteoporosis | RF female: test 0.859, "external" 0.812 | No | 95% CIs | Split + "external" = **NHANES 2017-18** (temporal holdout of the same survey) | Not truly external. Small number of events in men. |
| 18 | Tang T, 2025, Front Endocrinol (PMID 41585803, PMC12827086) | 2003-2020, older women + Chinese hospital external cohort | 3,950 internal; 338 external | Osteoporosis | RF 0.80 (0.78-0.82) internal; **0.74 (0.72-0.76) external** | No (OSTA mentioned only in the introduction) | 95% CIs | 70/30 split, "double-nested CV" on training data, + external | AUC drops about 0.06 externally. External prevalence was 49% vs 21% internally. |
| 19 | Zhu Q, 2026, Medicine (PMID 41861191, PMC13008175) | 2005-2018, postmenopausal women with CKD | unverified | Low bone mass or OP | MLP 0.72 (test) | No | "95% CI: not calculated" | Split + 5-fold CV | Survey weights explicitly not applied. Modest AUC in a high-risk subgroup. |
| 20 | Wang Q, 2026, BMC Med Inform Decis Mak (PMID 42087181, PMC13147576) | 2017-2020, age >= 50, FN or LS | 3,735 (390 OP) | Osteoporosis | Stacking ensemble 0.95 (test) | No | not reported | 70/30 split; 5-fold CV; SMOTE on training only | AUC 0.95 from BMI/age/sex/uric acid is implausibly high. The test set was cut to 578 of 1,121 complete cases (selection). Not externally validated. |
| 21 | Wang J, 2026, BMC Musculoskelet Disord (PMID 42104292, PMC13330492) | NHANES elderly (cycles unverified) | 3,181 train / 1,622 validation | Osteoporosis | LR nomogram, 11 variables, 0.795 | No (OSTA/OSTC discussed only) | OR CIs; bootstrap/CV internal validation | Split + resampling | Calibration and DCA reported. A plain LR reaches about 0.80. |
| 22 | Lao Y, 2026, Niger Postgrad Med J (PMID 42390513) | 2017-Mar 2020, age >= 60 | 3,422 | Osteoporosis T <= -2.5 | LR nomogram 0.793 (validation) | No | not reported in abstract | 70/30 split | LR only. Calibration and DCA reported. |
| 23 | Yang X, 2025, Bone (PMID 40669588) | Chinese hospital (development); **NHANES used as external validation** | 16,274 total | Low BMD (osteopenia + OP) | LR 0.902 internal; **0.812 on NHANES** | No | Brier and MCC reported | 70/30 split + NHANES external | Logistic regression beat 9 ML models. Large drop when moved to NHANES. |

## Table C. Related KNHANES ML studies (no OST comparison) and methodological anchors

| # | Reference | Key content |
|---|---|---|
| 24 | Shim JG, 2020, Arch Osteoporos (PMID 33097976) | KNHANES V-1/V-2, 1,792 postmenopausal women (613 OP). 5-fold CV AUCs **0.65-0.74**. ANN best at 0.743, **LR 0.727**. No OST comparison. With honest CV on simple survey variables, ML is about equal to LR. |
| 25 | Kwon Y, 2022, Healthcare (PMID 35742158, PMC9222287) | KNHANES, 1,431 postmenopausal women. AdaBoost AUROC 0.921 with check-up + survey features. Much higher than other KNHANES studies (about 0.72-0.83), which suggests optimism (feature selection on the full data is a possible cause; unverified). |
| A1 | Nayak S, 2015, Osteoporos Int (PMID 25644147, PMC4401628) | Systematic review/meta-analysis of 108 references on clinical risk instruments. For OST at cutoff < 1 in US postmenopausal women (FN osteoporosis): summary sensitivity 89% (82-96%), specificity 41% (23-59%). Reported OST AUCs ranged from 0.59 to 0.99, mostly 0.60-0.80. "Simpler instruments, such as OST, generally performed as well as or better than more complex instruments." |
| A2 | Christodoulou E, 2019, J Clin Epidemiol (PMID 30763612) | Systematic review of 71 studies and 282 LR-vs-ML comparisons. For comparisons at low risk of bias, the logit(AUC) difference was **0.00 (95% CI -0.18 to 0.18)**. For high risk of bias it was 0.34 in favour of ML. 68% of studies had potentially biased validation, and 79% did not report calibration. |

---

## Summary of patterns

1. **Every study comparing with OST/OSTA reports the ML model as better on point estimate (12/12), but the honest margin is small.** In studies with plausible OST performance (OST AUC about 0.73-0.82), the gain is usually **+0.02 to +0.05**:
   - Yoo 2013: +0.021
   - Erjiang 2021 (women): +0.023
   - Qiu 2024: +0.029
   - Zhang 2025 external: +0.047
   - Ou Yang 2021 (women): +0.08

   The large gains come from settings where OSTA did unusually badly (Bui 2022: 0.65; Huang WC 2025: 0.51-0.55). The student's +0.010/+0.012 sits at the low end of this range. That fits Nayak 2015 ("simpler instruments ... performed as well as or better") and Christodoulou 2019 (no ML advantage once bias is low).
2. **Formal testing of ML vs OST is uncommon.** Of 12 OST-comparison studies:
   - Paired tests of the AUC difference (DeLong or similar): **4** (Ou Yang, Zhang, Huang WC, Yoo; Yoo used a Wilcoxon test over CV folds). Kim 2013 claims significance but the test is unverified.
   - CIs only, with no paired test: Erjiang, Bui, Suh, Teng.
   - No CI or test: Qiu, Wang P, Je.
   - Where tests were done, several ML models were **not** significantly better than OSTA (e.g., Ou Yang, women: KNN and LR).
3. **Validation is mostly a single random split.** Only **3/12** OST-comparison studies used a separate external cohort (Zhang 2025, Teng 2026, Huang WC 2025, the last a second local cohort). None of the OST-comparison studies reported nested CV. Among the NHANES ML studies, nested or "double-nested" CV appears only in Tang 2025 and Karaismailoglu 2025. Where external validation was done, AUC fell by about 0.01-0.09 (Tang 0.80 to 0.74; Yang 0.90 to 0.81; Li male 0.85 to 0.73).
4. **NHANES ML papers rarely benchmark against OST.** Only **2** NHANES-based studies compared with OST: Suh 2023 (OST 0.759, but with a multiclass micro-averaged AUC) and Zhang 2025 (OST 0.781 external; GB 0.828, DeLong p < 0.001). The other 11 NHANES studies in Table B do not compare against OST at all, even though OST needs only age and weight, which NHANES has.
5. **Very high NHANES AUCs (0.94-0.97) go with identifiable methodological problems:**
   - SMOTE applied before the train/test split (Si 2025)
   - an outcome label partly defined by predictors (Carvalho 2025)
   - a complete-case-restricted test set (Wang Q 2026)
   - multiclass micro-averaged AUC (Suh 2023)

   Pooling men and women also raises AUC (sex is a top predictor), so these numbers cannot be compared with the student's postmenopausal-women-only analysis.
6. **Duplicate respondents and leakage.** No checked study reported de-duplicating respondents (SEQN) after merging NHANES cycles. The student's inflation from 0.84 back to 0.79 is a concrete, publishable example of the leakage risk Christodoulou describes. SMOTE-before-split (Si 2025) is the closest published analogue: synthetic near-copies of test points end up in training.
7. **Calibration** is reported in a minority of the OST-comparison studies (Bui: Brier score; Teng: calibration curves; Zhang: calibration curve). It is more common in the 2025-26 NHANES nomogram papers (Tang, Wang J, Lao, Li, Yang X).

**Bottom line for the student:** a statistically tied ML vs OST result, under nested CV and with a paired AUC test, is consistent with the best-designed studies in this literature (Yoo 2013, Erjiang 2021, Qiu 2024, Shim 2020) and with both anchor reviews. The published claims of large ML gains mostly come from single-split, referral-cohort, or leakage-prone designs.

---

## Sources

1. Kim SK et al. 2013 EMBC. https://pubmed.ncbi.nlm.nih.gov/24109656/ (doi:10.1109/EMBC.2013.6609469)
2. Yoo TK et al. 2013 Yonsei Med J. https://pubmed.ncbi.nlm.nih.gov/24142634/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC3809875/
3. Ou Yang WY et al. 2021 IJERPH. https://pmc.ncbi.nlm.nih.gov/articles/PMC8305021/
4. Erjiang E et al. 2021 J Clin Densitom. https://pubmed.ncbi.nlm.nih.gov/33187864/ (doi:10.1016/j.jocd.2020.10.004)
5. Bui HM et al. 2022 Sci Rep. https://pmc.ncbi.nlm.nih.gov/articles/PMC9684431/
6. Suh B et al. 2023 JMIR. https://pmc.ncbi.nlm.nih.gov/articles/PMC9883743/
7. Qiu C et al. 2024 Front Artif Intell. https://pmc.ncbi.nlm.nih.gov/articles/PMC11196804/
8. Je M et al. 2025 BMC Womens Health. https://pmc.ncbi.nlm.nih.gov/articles/PMC11951505/
9. Huang WC et al. 2025 Bone Rep. https://pmc.ncbi.nlm.nih.gov/articles/PMC11783436/
10. Wang P et al. 2025 Sci Rep. https://pmc.ncbi.nlm.nih.gov/articles/PMC11958675/
11. Zhang Y et al. 2025 Arch Osteoporos. https://pubmed.ncbi.nlm.nih.gov/41123741/ ; https://link.springer.com/article/10.1007/s11657-025-01602-8
12. Teng X et al. 2026 EClinicalMedicine. https://pmc.ncbi.nlm.nih.gov/articles/PMC13092471/
13. Huang W et al. 2025 BMC Med Inform Decis Mak. https://pmc.ncbi.nlm.nih.gov/articles/PMC12465568/
14. Karaismailoglu E et al. 2025 Balkan Med J. https://pmc.ncbi.nlm.nih.gov/articles/PMC12576511/
15. Si Z et al. 2025 BMC Res Notes. https://pmc.ncbi.nlm.nih.gov/articles/PMC11899459/
16. Carvalho FR, Gavaia PJ. 2025 Comput Biol Med. https://pubmed.ncbi.nlm.nih.gov/40328025/ ; https://www.sciencedirect.com/science/article/pii/S0010482525006407
17. Li H et al. 2025 Digital Health. https://pmc.ncbi.nlm.nih.gov/articles/PMC12246659/
18. Tang T et al. 2025 Front Endocrinol. https://pmc.ncbi.nlm.nih.gov/articles/PMC12827086/
19. Zhu Q et al. 2026 Medicine. https://pmc.ncbi.nlm.nih.gov/articles/PMC13008175/
20. Wang Q et al. 2026 BMC Med Inform Decis Mak. https://pmc.ncbi.nlm.nih.gov/articles/PMC13147576/
21. Wang J et al. 2026 BMC Musculoskelet Disord. https://pmc.ncbi.nlm.nih.gov/articles/PMC13330492/
22. Lao Y et al. 2026 Niger Postgrad Med J. https://pubmed.ncbi.nlm.nih.gov/42390513/ (doi:10.4103/npmj.npmj_441_25)
23. Yang X et al. 2025 Bone. https://pubmed.ncbi.nlm.nih.gov/40669588/ (doi:10.1016/j.bone.2025.117592)
24. Shim JG et al. 2020 Arch Osteoporos. https://pubmed.ncbi.nlm.nih.gov/33097976/ ; https://link.springer.com/article/10.1007/s11657-020-00802-8
25. Kwon Y et al. 2022 Healthcare. https://pmc.ncbi.nlm.nih.gov/articles/PMC9222287/
26. Nayak S et al. 2015 Osteoporos Int. https://pmc.ncbi.nlm.nih.gov/articles/PMC4401628/
27. Christodoulou E et al. 2019 J Clin Epidemiol. https://pubmed.ncbi.nlm.nih.gov/30763612/ (doi:10.1016/j.jclinepi.2019.02.004)

Items marked "unverified" (e.g., Zhang 2025 NHANES cycles, Kim 2013 n, Je 2025 numeric OST AUC, Teng 2026 OSTA AUC) should be checked against the full text before citing.
