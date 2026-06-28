# RamanUQ v2.1 — Uncertainty Quantification for Raman I_D/I_G Defect Metrics

## Abstract

<!-- AUTHOR: Abstract — write interpretive prose here -->
The D-to-G band intensity ratio (I_D/I_G) is the standard Raman measure of disorder and defect density in carbon nanomaterials, but the value it returns and the uncertainty reported with it both depend on peak-fitting choices that are seldom disclosed, so nominally comparable measurements may not be comparable. We quantify how these choices affect the ratio and its uncertainty, evaluating a configuration grid against hostile, out-of-family synthetic ground truth (8640 fits). Under a pre-registered coverage floor of 0.900, no configuration is rank-eligible (0; maximum coverage 0.800), because statistical intervals systematically undercover under misspecification. Accuracy and honest coverage separate: 9 of 72 configuration classes met the bias gate (best pseudo_voigt/poly5/DG/area, 0.0052) while none deliver honest 95% intervals. Goodness-of-fit does not select accurate configurations across the grid, and reported 95% error bars contain the truth only 0.276 / 0.240 / 0.183 of the time across noise regimes. An evidence-based protocol lowers the minimum detectable change versus a naive pipeline in every regime (0.271 vs 0.763, 2.819× at SNR 50). Against a published spectrum, the pipeline reproduces I_D/I_G at 1.523 versus a target of 1.600 (PASS, within ±10%). All findings hold on the spectra, configurations, and regimes tested here.

## 1 Introduction

<!-- AUTHOR: Introduction framing — write interpretive prose here -->
I_D/I_G, the ratio of the D-band intensity to the G-band intensity, is the standard measure of disorder in sp² carbon. The G band near 1580 cm⁻¹ comes from in-plane stretching of the sp² lattice. The D band near 1350 cm⁻¹ at 532 nm excitation is switched on by lattice defects, so the ratio climbs as the graphitic network is broken. Disordered carbon also produces weaker defect and disorder bands beyond this pair, including the D′ band and the broader D3 and D4 features, which some analyses add to the fitted model. Standard calibrations from Tuinstra and Koenig and from Cançado convert the ratio into physical quantities, the in-plane crystallite size Lₐ and the defect density n_D. In my own experimental work on carbon nanomaterials for solid-state hydrogen storage, where electron irradiation and hydrogenation drive the sp²→sp³ conversion, I_D/I_G is the first signal that defects have formed, and the defect density n_D it reports is the number I ultimately need to trust. That number is less solid than it appears, because I_D/I_G is never read straight off a spectrum. It is the output of an analysis pipeline with at least five degrees of freedom that papers rarely state. Spikes can be removed in more than one way, the baseline can be estimated by several methods, the lineshape fitted to each band can vary, the peak set built into the model can change, and intensity can be measured as peak height or as integrated area. Each of these choices moves the ratio. A paper that reports I_D/I_G almost never reports the full configuration behind it, so a ratio from one lab cannot be compared cleanly with a ratio from another, and the uncertainty quoted beside a ratio can be narrower than the spread the analysis choices alone would produce. This study makes those choices the object of measurement and poses four questions, all of which I registered before computing any result. Q1 asks which configurations stay accurate, with low bias, honest interval coverage, and a low fit-failure rate, when they are tested against hostile ground truth built outside every fitted model family and broken out by material class and signal-to-noise ratio (SNR). Q1b asks how stable that ranking is under jackknife resampling, both over families of configurations and over the individual spectra within each cell of the test suite. Q2 asks whether goodness-of-fit statistics, namely reduced χ² and the Akaike and Bayesian information criteria (AIC and BIC), actually select the accurate configurations. I registered a dated prediction for Q2 before running that audit. Q3 asks for the smallest change in I_D/I_G, and the matching change in n_D, that a measurement can resolve at laboratory signal-to-noise under a naive pipeline versus an evidence-based one. The approach throughout is to generate synthetic spectra whose true defect ratios are fixed by construction while their shapes fall outside the models being fit, with every question and prediction locked in advance.

## 2 Methods

### 2.1 Pre-registration

All gates, tolerances, the Q1 ranking rule, the Q1b jackknife, the Q2 metrics,
and the Q2 prediction were registered and frozen in `docs/validation_plan.md`
(dated 2026-06-15) before the corresponding code was run. No tolerance was
changed after the fact.

### 2.2 Two-tier ground truth

Truth is the generator's noiseless, baseline-free band functions. True *area* is
the integral of each band function; true *height* is its maximum. Both are stored
per spectrum. Tier-A supplies matched-recovery and baseline-only cases; Tier-B
supplies the hostile, out-of-family disordered-carbon suite. The grid study
analyzed here comprises 8640 rows from
`data/synthetic/results/tierB_grid_results.parquet`.

### 2.3 Validation gates

| Gate | Tolerance | Status |
| --- | --- | --- |
| V1 — Parameter recovery | < 0.1% relative recovery error | PASS |
| V1b — Empirical coverage | 0.90-0.98 | REPORTED |
| V2 — Baseline fit | < 2% of G-band height (in-class) | PASS |
| V3 — Hostile-spectrum bias | mean abs bias < 0.050 | PASS |
| V4 — Selector sanity | exact recovery (atol 1e-12) | PASS |
| V5 — Published-spectrum reproduction | within +/-10% of >=1 digitized published spectrum | PASS |
| V6 — Cross-implementation agreement | 1e-9 relative (analytic) / 1e-6 (numerical) | PASS |

## 3 Instrument validation

Gate V3 (hostile-spectrum bias, stage-1 / SNR 50 slice): of 72
configuration classes, 9 achieve mean absolute bias below
the registered tolerance (0.050); the best class has mean absolute bias
0.0052.

Gate V5 (published-spectrum reproduction): the digitized Cançado et al. 2011
(Nano Lett. 11, 3190; DOI 10.1021/nl201432g) L_D = 7 nm graphene spectrum, run
through the pipeline in HEIGHT mode (the paper defines I_D/I_G as the peak-height
ratio), yields I_D/I_G = 1.523 against the published target
1.600. With the registered ±10% window [1.440,
1.760], the result is PASS.

## 4 Q1 and Q1b

### 4.1 Q1 — coverage-gated ranking

Under the pre-registered rule (RMSE ascending, subject to empirical 95% coverage
≥ 0.900 and failure rate ≤ 0.050), the number of
rank-eligible configurations is 0 in every SNR regime. The
maximum empirical 95% coverage over all (config × SNR) cells is
0.800, below the 0.900 floor.

Coverage of the typical configuration's nominal 0.95 interval, pooled
per regime (T6b):

| SNR | empirical coverage |
| --- | --- |
| 15 | 0.276 |
| 50 | 0.240 |
| 200 | 0.183 |

### 4.2 Q1b — rank stability

With 0 rank-eligible configurations, the jackknife has no
recommended configuration to resample; rank stability is undefined (not "stable").

<!-- AUTHOR: Q1+Q1b interpretation — write interpretive prose here -->
Q1 asks which configurations stay accurate under hostile, out-of-family ground truth. I fixed the ranking rule before any spectrum was fit. Order the configurations by root-mean-square error (RMSE). Keep only those whose empirical 95% interval coverage sits at or above 0.900 and whose fit-failure rate sits at or below 0.050. Applying that rule to the hostile suite yields an empty ranking. The maximum empirical coverage across every cell of the suite was 0.800, which falls below the floor, so 0 configurations were rank-eligible. The empty table is the result. I dropped no configuration for being inaccurate, and I never lowered the coverage floor to admit one. Every configuration in the grid reports an uncertainty interval from a residual bootstrap. Under ground truth built outside every fitted model family, those intervals are too narrow to cover the true ratio at their stated rate. The empty ranking measures that undercoverage. This is the headline finding of the study rather than a gap in it. Statistical-only intervals understate their own error when the fitted model fails to match the spectrum, and some mismatch between the fitted model and the measured spectrum is generally expected in real measurements. Gate V3 passed at the same time. 9 of 72 configuration classes reached mean absolute bias below the V3 tolerance on stage-1 spectra at SNR 50. The most accurate was pseudo_voigt/poly5/DG/area at 0.0052. These two facts sit together without contradiction. A configuration class can place its central value close to the truth while none of its configurations report honest coverage. Accuracy in the point estimate and honesty in the interval are separate properties, and a method can hold the first while missing the second. A low bias figure beside a too-narrow error bar is a precise-looking answer carrying overstated confidence. The descriptive decomposition adds one structural note, and I report it as an association rather than a mechanism. The D and G peak set ran tighter in mean error than any set containing D′ by roughly fivefold. This is a marginal comparison, and the factorial layout of the grid confounds it, so the gap cannot be attributed cleanly to the extra bands. One interpretation consistent with the pattern is that the D′, D3, and D4 bands give the model more freedom to absorb the hostile baselines and asymmetric shapes, trading smaller residuals for a less accurate recovered ratio. The present design does not isolate that effect from the factors it co-varies with, so the overfitting account stays a candidate explanation rather than a demonstrated one. Q1b asks how stable the Q1 ranking is under jackknife resampling, both over configuration families and over the individual spectra within each suite cell. The ranking is empty, so there is nothing to resample. There were 0 rank-eligible configurations to jackknife in every regime, which leaves rank stability undefined. The jackknife machinery ran and found no surviving configuration to test. This is reported honestly as a vacuous result that follows from the empty ranking. The robustness analysis behaved correctly. Two results close this section. Statistical-only bootstrap intervals undercover under out-of-family misspecification, and accuracy in central value gives no assurance of honest coverage, on the spectra, configurations, and regimes tested here.

## 5 Q2

### 5.1 Registered prediction (verbatim, 2026-06-15)

> I predict H_C (mixed), specifically that fit quality and I_D/I_G accuracy will
> be decoupled across different peak sets but loosely correlated within one fixed
> set. Practically: if you let the model pick from many different peak
> configurations, the best-scoring one often isn't the most accurate (high
> regret); but if all candidates share the same peaks, the best-scoring one
> usually is close to accurate (low regret). I expect the within-set correlation
> to be positive but weak, and weakest for messy spectra like hydrogenated
> SWCNTs and rGO.

### 5.2 Selector audit (SNR 50; ρ = median per-spectrum Spearman; regret in I_D/I_G)

| selector | full ρ | within-set ρ | full regret | within-set regret |
| --- | --- | --- | --- | --- |
| redchi | -0.020 | +0.003 | 0.552 | 0.282 |
| aic | -0.003 | +0.003 | 0.552 | 0.282 |
| bic | +0.063 | +0.004 | 0.668 | 0.336 |

(The full per-cell audit across all SNR regimes and both strata lives in
`docs/report_data.json` and `notebooks/03_selector_q2.ipynb`.)

### 5.3 Verdict

<!-- AUTHOR: Q2 VERDICT — paste verbatim from Day-7 validation_plan.md, do not write -->
The registered prediction held that fit quality and I_D/I_G accuracy would be decoupled across different peak sets but loosely and positively correlated within a single fixed peak set, with the within-set correlation expected to be weak and weakest for messy spectra such as hydrogenated SWCNTs and reduced graphene oxide; practically, selecting the best-scoring fit from many different peak configurations should often miss the most accurate one (high regret), whereas selecting among candidates sharing the same peaks should usually land close to accurate (low regret). On the synthetic disordered-carbon suite (30 spectra per cell, ρ defined as the median per-spectrum Spearman correlation with 95% spectrum-level bootstrap confidence intervals, regret in I_D/I_G units), full-stratum ρ values all fell within ±0.08 of zero (range −0.079 to +0.063), with the confidence interval clearing zero in 4 of 9 cells (bic SNR15 +0.046, redchi SNR15 −0.079, redchi SNR200 −0.077, aic SNR200 −0.052), the established redchi cells leaning negative; within-peak-set ρ was positive in all 9 cells but cleared zero in only 3, all at SNR15 (aic +0.094, bic +0.084, redchi +0.081), while the SNR50 and SNR200 cells straddled zero; and regret was 2–3× larger at the full-stratum level than within-stratum at every noise level (1.37 vs ~0.44 at SNR15; 0.55–0.67 vs 0.28–0.34 at SNR50; 0.88 vs 0.38–0.42 at SNR200). The decoupling-across-peak-sets claim was partially confirmed, since ρ stayed near zero with mostly straddling intervals though 4 cells cleared zero, while the high-regret contrast held strongly; the coupling-within-a-fixed-set claim was likewise partially confirmed, with positive median ρ everywhere but statistical establishment only at the noisiest SNR15 spectra and consistently lower within-set regret; the prediction that the within-set correlation would be positive but weak was confirmed, the established values of +0.08 to +0.09 being positive and genuinely tiny and even weaker (positive but unestablished) at higher SNR; and the claim that messy spectra would show the weakest coupling was untestable as written because the suite contains a single material class with no material-class axis, and using SNR as a messiness proxy it ran backwards, with within-set coupling strongest and only established at the noisiest SNR15 and washed out at the cleanest SNR200. The central structural prediction—accuracy decoupled across peak sets and coupled within a fixed set—broadly held, with the full grid near-decoupled and carrying 2–3× higher regret and the within-set correlation positive with lower regret, though that within-set coupling was statistically established only for the noisiest spectra. Mechanistically, peak set is the dominant accuracy driver, with DG configurations roughly 5× more accurate than band-heavy sets; within a fixed peak set only baseline, lineshape, and intensity vary and these shift accuracy little, leaving a small accuracy signal for fit quality to track and producing the weak positive within-set ρ, whereas across peak sets the selector can swing between DG and overfitting band-heavy sets to produce the high full-grid regret. The practically important finding lies not in ρ but in coverage: the typical configuration's nominal 95% interval contained the truth only 18–28% of the time across noise regimes (0.276, 0.240, 0.183 at SNR 15, 50, and 200), so reported error bars are not honest 95% intervals under realistic misspecification. These results hold on the spectra, configurations, and SNR regimes of the synthetic disordered-carbon suite tested.

### 5.4 Interpretation

<!-- AUTHOR: Q2 interpretation — write interpretive prose here -->
Goodness-of-fit is not a usable accuracy selector on these hostile spectra, with every correlation sitting at or below about 0.09. Across the full configuration grid, all three selectors correlate with accuracy at essentially zero (-0.020, -0.003, +0.063 at SNR 50), so fit quality does not pick out accurate configurations grid-wide. Within a fixed peak set the correlation is positive but weak (+0.003, +0.003, +0.004), and it clears zero only at SNR15, so the within-set signal is real but not statistically established at higher SNR. The apparent grid-wide signal is therefore almost entirely the peak-set decision, not goodness-of-fit. Full-grid regret runs 2–3× the within-set regret, so letting the selector roam across peak sets costs accuracy. The headline result concerns coverage, where reported 95% error bars contain the true ratio only 0.276 / 0.240 / 0.183 of the time at SNR 15/50/200. These conclusions hold on the spectra, configurations, and SNR regimes tested here.

## 6 Q3

Minimum detectable change (MDC) in I_D/I_G units (single-measurement precision;
alpha = 0.05, power = 0.80, n_rep = 1; excitation
532.0 nm), protocol configuration versus the naive everyday pipeline
(`baseline=linear|lineshape=lorentzian|bwf_g=False|peak_set=DG|intensity=height`). Δn_D is the defect-density currency (cm⁻²).

| regime | protocol config | bias | RMSE | coverage | failure | protocol MDC | naive MDC | naive/protocol | protocol Δn_D | naive Δn_D |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SNR15 | baseline=poly5|lineshape=gaussian|bwf_g=False|peak_set=DG|intensity=area | +0.022 | 0.133 | 0.467 | 0.000 | 0.529 | 0.745 | 1.407 | 1.189e+11 | 1.673e+11 |
| SNR50 | baseline=als|lineshape=pseudo_voigt|bwf_g=False|peak_set=DG|intensity=area | -0.086 | 0.109 | 0.233 | 0.000 | 0.271 | 0.763 | 2.819 | 6.082e+10 | 1.714e+11 |
| SNR200 | baseline=als|lineshape=pseudo_voigt|bwf_g=False|peak_set=DG|intensity=area | -0.016 | 0.141 | 0.200 | 0.000 | 0.565 | 0.703 | 1.245 | 1.269e+11 | 1.580e+11 |

<!-- AUTHOR: Q3 interpretation — write interpretive prose here -->
The protocol detects smaller changes in I_D/I_G than the naive comparator in every noise regime. The minimum detectable change under the evidence-based protocol was 0.529 / 0.271 / 0.565 at SNR 15/50/200, against 0.745 / 0.763 / 0.703 for the illustrative naive baseline=linear|lineshape=lorentzian|bwf_g=False|peak_set=DG|intensity=height pipeline, so the protocol resolves a smaller change in every regime. The improvement is sharpest at SNR 50 (2.819×), where the protocol's precision advantage over the naive comparator is largest. This minimum detectable change is a precision statement: it rides on the repeatability, or spread, of the signed error rather than on whether the reported interval is honest. The protocol configuration is precision-picked, the DG/area config with the smallest signed-error standard deviation, and although its coverage is low the protocol MDC still beats the naive one, because detection depends on the spread of repeated measurements and not on interval honesty. Bias is reported separately, so a biased-but-precise configuration can detect changes while still misestimating absolute levels. In defect-density terms, the protocol resolves a change as small as 6.082e+10 cm⁻² at SNR 50, setting the floor on the smallest defect-density shift the protocol can claim to detect, such as the kind a hydrogenation or defect-engineering step is meant to produce. These conclusions hold on the spectra, configurations, and SNR regimes tested here.

## 7 Protocol and disclosure checklist

The per-regime protocol recommendations are in `docs/protocol.md`. The AI-usage
disclosure is in `docs/provenance/ai_usage_log.md`.

<!-- AUTHOR: the disclosure checklist — write interpretive prose here -->
I defined all four research questions — Q1, Q1b, Q2, and Q3 — before any result was generated, and I registered the Q2 prediction, with a date, before any selector code existed. Every calibration constant was sourced from the primary literature, namely Tuinstra and Koenig (1970) and Cançado et al. (2006, 2011), and I personally verified the band-intensity definition that each of those works adopted. I defined the operational ground-truth definition, the gate tolerances, and the coverage floor, all pre-registered and frozen before any result was produced. Every interpretive sentence in this report is my own, including the Q2 verdict and the protocol recommendations. The AI agents implemented code to my specifications and acceptance tests, and each science-critical formula (lineshapes, fit criteria, metrics, MDC, and selectors) was independently reimplemented by a separate agent and asserted equal in continuous integration (Gate V6). The public, dated audit trail comprises the validation_plan.md whose timestamps precede the results, the per-session ai_usage_log.md, and the Gate V6 differential.

## 8 Limitations

<!-- AUTHOR: Limitations — write interpretive prose here -->
Our ground truth is synthetic and realistic-by-construction rather than instrument-measured, which lets us know the true I_D/I_G ratio exactly but does not establish behavior on real spectra we did not measure. The selector audit covers reduced χ², AIC, and BIC, the three most common goodness-of-fit statistics, so that conclusion concerns those three and not all possible selectors. High fit-failure rates on the most hostile spectra are reported as a failure-rate column rather than excluded, since non-convergence is information about the configuration and not a defect in the analysis. The D′ and G bands can trade off against each other in the fit, a bounded and reported degeneracy that is part of why D′-containing peak sets overfit. The weak, stratified outcome of the goodness-of-fit audit is itself a genuine finding, reported with its stratification and confidence intervals rather than treated as a failure to detect an effect. The naive comparator pipeline represents common default practice and is labeled illustrative, not a claim that any specific published study used exactly that configuration. All of these findings are conditional on the configuration grid, the spectral generators, and the SNR regimes tested here, and the recommended protocol is evidence-based for those regimes rather than universally correct.

## References

1. Cançado, L. G.; Jorio, A.; Martins Ferreira, E. H.; Stavale, F.; Achete,
   C. A.; Capaz, R. B.; Moutinho, M. V. O.; Lombardo, A.; Kulmala, T. S.;
   Ferrari, A. C. "Quantifying Defects in Graphene via Raman Spectroscopy at
   Different Excitation Energies." *Nano Lett.* **2011**, *11*, 3190–3196.
   DOI: 10.1021/nl201432g.
