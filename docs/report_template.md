<!--
  RamanUQ v2.1 — REPORT TEMPLATE (Day 10, manual prompt P11 / §9.10).

  PLUMBING ONLY. Every numeral that is a reported RESULT is a {{placeholder}}
  bound to a key path in docs/report_data.json. There are NO hard-coded result
  numbers in this file. scripts/build_report.py reads the PLACEHOLDER MAP block
  below, resolves each {{key}} from its JSON path, and writes docs/report_draft.md.

  Allowed bare digits (NOT results): reference years, DOIs, section/figure/table
  numbers, SNR regime LABELS (15 / 50 / 200), and equation constants inside the
  Methods model definitions.

  Interpretive prose is the AUTHOR's job. Wherever an "AUTHOR:" HTML-comment
  marker appears in the body, the block is intentionally left empty for the
  author to fill.

  PLACEHOLDER MAP (build_report.py parses every line of the form
  `name -> json.path | fmt` between the START and END markers below; fmt is one
  of int, f1, f2, f3, f4, f5, sgn3, sgn5, sci, raw; numeric path components index
  into JSON lists, e.g. gates.V5.window.0):

  PLACEHOLDER-MAP-START
  n_rows -> n_rows | int

  v1_status  -> gates.V1.status  | raw
  v1_tol     -> gates.V1.tolerance | raw
  v1b_status -> gates.V1b.status | raw
  v1b_tol    -> gates.V1b.tolerance | raw
  v2_status  -> gates.V2.status  | raw
  v2_tol     -> gates.V2.tolerance | raw
  v3_status  -> gates.V3.status  | raw
  v3_tol     -> gates.V3.tolerance_abs_bias | f3
  v4_status  -> gates.V4.status  | raw
  v4_tol     -> gates.V4.tolerance | raw
  v5_status  -> gates.V5.status  | raw
  v5_tol     -> gates.V5.tolerance | raw
  v6_status  -> gates.V6.status  | raw
  v6_tol     -> gates.V6.tolerance | raw

  v3_n_classes         -> gate_v3.n_classes | int
  v3_n_classes_passing -> gate_v3.n_classes_passing | int
  v3_best_bias         -> gate_v3.best_class_mean_abs_bias | f4
  v3_best_class        -> gate_v3.best_class_label | raw

  v5_measured  -> gates.V5.measured_idig | f3
  v5_target    -> gates.V5.target | f3
  v5_window_lo -> gates.V5.window.0 | f3
  v5_window_hi -> gates.V5.window.1 | f3
  v5_result    -> gates.V5.result | raw

  t5_n_rank_eligible  -> t5_ranking.n_rank_eligible | int
  t5_max_coverage     -> t5_ranking.max_coverage | f3
  t5_coverage_floor   -> t5_ranking.coverage_floor | f3
  t5_max_failure_rate -> t5_ranking.max_failure_rate | f3
  q1b_n_recommended   -> q1b_stability.n_recommended_configs | int

  t6b_nominal -> t6b_coverage.nominal | f2
  t6b_snr15   -> t6b_coverage.per_regime.SNR15.coverage | f3
  t6b_snr50   -> t6b_coverage.per_regime.SNR50.coverage | f3
  t6b_snr200  -> t6b_coverage.per_regime.SNR200.coverage | f3

  q2_full_redchi_rho   -> q2_audit.by_stratum.full.SNR50.redchi.spearman_rho | sgn3
  q2_full_aic_rho      -> q2_audit.by_stratum.full.SNR50.aic.spearman_rho | sgn3
  q2_full_bic_rho      -> q2_audit.by_stratum.full.SNR50.bic.spearman_rho | sgn3
  q2_within_redchi_rho -> q2_audit.by_stratum.within_peak_set.SNR50.redchi.spearman_rho | sgn3
  q2_within_aic_rho    -> q2_audit.by_stratum.within_peak_set.SNR50.aic.spearman_rho | sgn3
  q2_within_bic_rho    -> q2_audit.by_stratum.within_peak_set.SNR50.bic.spearman_rho | sgn3
  q2_full_redchi_regret   -> q2_audit.by_stratum.full.SNR50.redchi.top1_regret | f3
  q2_full_aic_regret      -> q2_audit.by_stratum.full.SNR50.aic.top1_regret | f3
  q2_full_bic_regret      -> q2_audit.by_stratum.full.SNR50.bic.top1_regret | f3
  q2_within_redchi_regret -> q2_audit.by_stratum.within_peak_set.SNR50.redchi.top1_regret | f3
  q2_within_aic_regret    -> q2_audit.by_stratum.within_peak_set.SNR50.aic.top1_regret | f3
  q2_within_bic_regret    -> q2_audit.by_stratum.within_peak_set.SNR50.bic.top1_regret | f3

  mdc_alpha      -> mdc.alpha | f2
  mdc_power      -> mdc.power | f2
  mdc_n_rep      -> mdc.n_rep | int
  mdc_wavelength -> mdc.wavelength_nm | f1
  naive_config   -> mdc.naive_config | raw

  protocol_config_snr15  -> mdc.per_regime.SNR15.protocol_config | raw
  protocol_bias_snr15    -> mdc.per_regime.SNR15.protocol_bias | sgn3
  protocol_rmse_snr15    -> mdc.per_regime.SNR15.protocol_rmse | f3
  protocol_coverage_snr15-> mdc.per_regime.SNR15.protocol_coverage | f3
  protocol_failure_snr15 -> mdc.per_regime.SNR15.protocol_failure_rate | f3
  protocol_mdc_snr15     -> mdc.per_regime.SNR15.protocol_mdc_idig | f3
  protocol_dnd_snr15     -> mdc.per_regime.SNR15.protocol_delta_nd_central | sci
  naive_mdc_snr15        -> mdc.per_regime.SNR15.naive_mdc_idig | f3
  naive_dnd_snr15        -> mdc.per_regime.SNR15.naive_delta_nd_central | sci
  ratio_snr15            -> mdc.per_regime.SNR15.naive_over_protocol_mdc_ratio | f3

  protocol_config_snr50  -> mdc.per_regime.SNR50.protocol_config | raw
  protocol_bias_snr50    -> mdc.per_regime.SNR50.protocol_bias | sgn3
  protocol_rmse_snr50    -> mdc.per_regime.SNR50.protocol_rmse | f3
  protocol_coverage_snr50-> mdc.per_regime.SNR50.protocol_coverage | f3
  protocol_failure_snr50 -> mdc.per_regime.SNR50.protocol_failure_rate | f3
  protocol_mdc_snr50     -> mdc.per_regime.SNR50.protocol_mdc_idig | f3
  protocol_dnd_snr50     -> mdc.per_regime.SNR50.protocol_delta_nd_central | sci
  naive_mdc_snr50        -> mdc.per_regime.SNR50.naive_mdc_idig | f3
  naive_dnd_snr50        -> mdc.per_regime.SNR50.naive_delta_nd_central | sci
  ratio_snr50            -> mdc.per_regime.SNR50.naive_over_protocol_mdc_ratio | f3

  protocol_config_snr200  -> mdc.per_regime.SNR200.protocol_config | raw
  protocol_bias_snr200    -> mdc.per_regime.SNR200.protocol_bias | sgn3
  protocol_rmse_snr200    -> mdc.per_regime.SNR200.protocol_rmse | f3
  protocol_coverage_snr200-> mdc.per_regime.SNR200.protocol_coverage | f3
  protocol_failure_snr200 -> mdc.per_regime.SNR200.protocol_failure_rate | f3
  protocol_mdc_snr200     -> mdc.per_regime.SNR200.protocol_mdc_idig | f3
  protocol_dnd_snr200     -> mdc.per_regime.SNR200.protocol_delta_nd_central | sci
  naive_mdc_snr200        -> mdc.per_regime.SNR200.naive_mdc_idig | f3
  naive_dnd_snr200        -> mdc.per_regime.SNR200.naive_delta_nd_central | sci
  ratio_snr200            -> mdc.per_regime.SNR200.naive_over_protocol_mdc_ratio | f3
  PLACEHOLDER-MAP-END
-->

# RamanUQ v2.1 — Uncertainty Quantification for Raman I_D/I_G Defect Metrics

## Abstract

<!-- AUTHOR: Abstract — write interpretive prose here -->
The D-to-G band intensity ratio (I_D/I_G) is the standard Raman measure of disorder and defect density in carbon nanomaterials, but the value it returns and the uncertainty reported with it both depend on peak-fitting choices that are seldom disclosed, so nominally comparable measurements may not be comparable. We quantify how these choices affect the ratio and its uncertainty, evaluating a configuration grid against hostile, out-of-family synthetic ground truth ({{n_rows}} fits). Under a pre-registered coverage floor of {{t5_coverage_floor}}, no configuration is rank-eligible ({{t5_n_rank_eligible}}; maximum coverage {{t5_max_coverage}}), because statistical intervals systematically undercover under misspecification. Accuracy and honest coverage separate: {{v3_n_classes_passing}} of {{v3_n_classes}} configuration classes met the bias gate (best {{v3_best_class}}, {{v3_best_bias}}) while none deliver honest 95% intervals. Goodness-of-fit does not select accurate configurations across the grid, and reported 95% error bars contain the truth only {{t6b_snr15}} / {{t6b_snr50}} / {{t6b_snr200}} of the time across noise regimes. An evidence-based protocol lowers the minimum detectable change versus a naive pipeline in every regime ({{protocol_mdc_snr50}} vs {{naive_mdc_snr50}}, {{ratio_snr50}}× at SNR 50). Against a published spectrum, the pipeline reproduces I_D/I_G at {{v5_measured}} versus a target of {{v5_target}} ({{v5_result}}, within ±10%). All findings hold on the spectra, configurations, and regimes tested here.

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
analyzed here comprises {{n_rows}} rows from
`data/synthetic/results/tierB_grid_results.parquet`.

### 2.3 Validation gates

| Gate | Tolerance | Status |
| --- | --- | --- |
| V1 — Parameter recovery | {{v1_tol}} | {{v1_status}} |
| V1b — Empirical coverage | {{v1b_tol}} | {{v1b_status}} |
| V2 — Baseline fit | {{v2_tol}} | {{v2_status}} |
| V3 — Hostile-spectrum bias | mean abs bias < {{v3_tol}} | {{v3_status}} |
| V4 — Selector sanity | {{v4_tol}} | {{v4_status}} |
| V5 — Published-spectrum reproduction | {{v5_tol}} | {{v5_status}} |
| V6 — Cross-implementation agreement | {{v6_tol}} | {{v6_status}} |

## 3 Instrument validation

Gate V3 (hostile-spectrum bias, stage-1 / SNR 50 slice): of {{v3_n_classes}}
configuration classes, {{v3_n_classes_passing}} achieve mean absolute bias below
the registered tolerance ({{v3_tol}}); the best class has mean absolute bias
{{v3_best_bias}}.

Gate V5 (published-spectrum reproduction): the digitized Cançado et al. 2011
(Nano Lett. 11, 3190; DOI 10.1021/nl201432g) L_D = 7 nm graphene spectrum, run
through the pipeline in HEIGHT mode (the paper defines I_D/I_G as the peak-height
ratio), yields I_D/I_G = {{v5_measured}} against the published target
{{v5_target}}. With the registered ±10% window [{{v5_window_lo}},
{{v5_window_hi}}], the result is {{v5_result}}.

## 4 Q1 and Q1b

### 4.1 Q1 — coverage-gated ranking

Under the pre-registered rule (RMSE ascending, subject to empirical 95% coverage
≥ {{t5_coverage_floor}} and failure rate ≤ {{t5_max_failure_rate}}), the number of
rank-eligible configurations is {{t5_n_rank_eligible}} in every SNR regime. The
maximum empirical 95% coverage over all (config × SNR) cells is
{{t5_max_coverage}}, below the {{t5_coverage_floor}} floor.

Coverage of the typical configuration's nominal {{t6b_nominal}} interval, pooled
per regime (T6b):

| SNR | empirical coverage |
| --- | --- |
| 15 | {{t6b_snr15}} |
| 50 | {{t6b_snr50}} |
| 200 | {{t6b_snr200}} |

### 4.2 Q1b — rank stability

With {{q1b_n_recommended}} rank-eligible configurations, the jackknife has no
recommended configuration to resample; rank stability is undefined (not "stable").

<!-- AUTHOR: Q1+Q1b interpretation — write interpretive prose here -->
Q1 asks which configurations stay accurate under hostile, out-of-family ground truth. I fixed the ranking rule before any spectrum was fit. Order the configurations by root-mean-square error (RMSE). Keep only those whose empirical 95% interval coverage sits at or above {{t5_coverage_floor}} and whose fit-failure rate sits at or below {{t5_max_failure_rate}}. Applying that rule to the hostile suite yields an empty ranking. The maximum empirical coverage across every cell of the suite was {{t5_max_coverage}}, which falls below the floor, so {{t5_n_rank_eligible}} configurations were rank-eligible. The empty table is the result. I dropped no configuration for being inaccurate, and I never lowered the coverage floor to admit one. Every configuration in the grid reports an uncertainty interval from a residual bootstrap. Under ground truth built outside every fitted model family, those intervals are too narrow to cover the true ratio at their stated rate. The empty ranking measures that undercoverage. This is the headline finding of the study rather than a gap in it. Statistical-only intervals understate their own error when the fitted model fails to match the spectrum, and some mismatch between the fitted model and the measured spectrum is generally expected in real measurements. Gate V3 passed at the same time. {{v3_n_classes_passing}} of {{v3_n_classes}} configuration classes reached mean absolute bias below the V3 tolerance on stage-1 spectra at SNR 50. The most accurate was {{v3_best_class}} at {{v3_best_bias}}. These two facts sit together without contradiction. A configuration class can place its central value close to the truth while none of its configurations report honest coverage. Accuracy in the point estimate and honesty in the interval are separate properties, and a method can hold the first while missing the second. A low bias figure beside a too-narrow error bar is a precise-looking answer carrying overstated confidence. The descriptive decomposition adds one structural note, and I report it as an association rather than a mechanism. The D and G peak set ran tighter in mean error than any set containing D′ by roughly fivefold. This is a marginal comparison, and the factorial layout of the grid confounds it, so the gap cannot be attributed cleanly to the extra bands. One interpretation consistent with the pattern is that the D′, D3, and D4 bands give the model more freedom to absorb the hostile baselines and asymmetric shapes, trading smaller residuals for a less accurate recovered ratio. The present design does not isolate that effect from the factors it co-varies with, so the overfitting account stays a candidate explanation rather than a demonstrated one. Q1b asks how stable the Q1 ranking is under jackknife resampling, both over configuration families and over the individual spectra within each suite cell. The ranking is empty, so there is nothing to resample. There were {{q1b_n_recommended}} rank-eligible configurations to jackknife in every regime, which leaves rank stability undefined. The jackknife machinery ran and found no surviving configuration to test. This is reported honestly as a vacuous result that follows from the empty ranking. The robustness analysis behaved correctly. Two results close this section. Statistical-only bootstrap intervals undercover under out-of-family misspecification, and accuracy in central value gives no assurance of honest coverage, on the spectra, configurations, and regimes tested here.

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
| redchi | {{q2_full_redchi_rho}} | {{q2_within_redchi_rho}} | {{q2_full_redchi_regret}} | {{q2_within_redchi_regret}} |
| aic | {{q2_full_aic_rho}} | {{q2_within_aic_rho}} | {{q2_full_aic_regret}} | {{q2_within_aic_regret}} |
| bic | {{q2_full_bic_rho}} | {{q2_within_bic_rho}} | {{q2_full_bic_regret}} | {{q2_within_bic_regret}} |

(The full per-cell audit across all SNR regimes and both strata lives in
`docs/report_data.json` and `notebooks/03_selector_q2.ipynb`.)

### 5.3 Verdict

<!-- AUTHOR: Q2 VERDICT — paste verbatim from Day-7 validation_plan.md, do not write -->
The registered prediction held that fit quality and I_D/I_G accuracy would be decoupled across different peak sets but loosely and positively correlated within a single fixed peak set, with the within-set correlation expected to be weak and weakest for messy spectra such as hydrogenated SWCNTs and reduced graphene oxide; practically, selecting the best-scoring fit from many different peak configurations should often miss the most accurate one (high regret), whereas selecting among candidates sharing the same peaks should usually land close to accurate (low regret). On the synthetic disordered-carbon suite (30 spectra per cell, ρ defined as the median per-spectrum Spearman correlation with 95% spectrum-level bootstrap confidence intervals, regret in I_D/I_G units), full-stratum ρ values all fell within ±0.08 of zero (range −0.079 to +0.063), with the confidence interval clearing zero in 4 of 9 cells (bic SNR15 +0.046, redchi SNR15 −0.079, redchi SNR200 −0.077, aic SNR200 −0.052), the established redchi cells leaning negative; within-peak-set ρ was positive in all 9 cells but cleared zero in only 3, all at SNR15 (aic +0.094, bic +0.084, redchi +0.081), while the SNR50 and SNR200 cells straddled zero; and regret was 2–3× larger at the full-stratum level than within-stratum at every noise level (1.37 vs ~0.44 at SNR15; 0.55–0.67 vs 0.28–0.34 at SNR50; 0.88 vs 0.38–0.42 at SNR200). The decoupling-across-peak-sets claim was partially confirmed, since ρ stayed near zero with mostly straddling intervals though 4 cells cleared zero, while the high-regret contrast held strongly; the coupling-within-a-fixed-set claim was likewise partially confirmed, with positive median ρ everywhere but statistical establishment only at the noisiest SNR15 spectra and consistently lower within-set regret; the prediction that the within-set correlation would be positive but weak was confirmed, the established values of +0.08 to +0.09 being positive and genuinely tiny and even weaker (positive but unestablished) at higher SNR; and the claim that messy spectra would show the weakest coupling was untestable as written because the suite contains a single material class with no material-class axis, and using SNR as a messiness proxy it ran backwards, with within-set coupling strongest and only established at the noisiest SNR15 and washed out at the cleanest SNR200. The central structural prediction—accuracy decoupled across peak sets and coupled within a fixed set—broadly held, with the full grid near-decoupled and carrying 2–3× higher regret and the within-set correlation positive with lower regret, though that within-set coupling was statistically established only for the noisiest spectra. Mechanistically, peak set is the dominant accuracy driver, with DG configurations roughly 5× more accurate than band-heavy sets; within a fixed peak set only baseline, lineshape, and intensity vary and these shift accuracy little, leaving a small accuracy signal for fit quality to track and producing the weak positive within-set ρ, whereas across peak sets the selector can swing between DG and overfitting band-heavy sets to produce the high full-grid regret. The practically important finding lies not in ρ but in coverage: the typical configuration's nominal 95% interval contained the truth only 18–28% of the time across noise regimes (0.276, 0.240, 0.183 at SNR 15, 50, and 200), so reported error bars are not honest 95% intervals under realistic misspecification. These results hold on the spectra, configurations, and SNR regimes of the synthetic disordered-carbon suite tested.

### 5.4 Interpretation

<!-- AUTHOR: Q2 interpretation — write interpretive prose here -->
Goodness-of-fit is not a usable accuracy selector on these hostile spectra, with every correlation sitting at or below about 0.09. Across the full configuration grid, all three selectors correlate with accuracy at essentially zero ({{q2_full_redchi_rho}}, {{q2_full_aic_rho}}, {{q2_full_bic_rho}} at SNR 50), so fit quality does not pick out accurate configurations grid-wide. Within a fixed peak set the correlation is positive but weak ({{q2_within_redchi_rho}}, {{q2_within_aic_rho}}, {{q2_within_bic_rho}}), and it clears zero only at SNR15, so the within-set signal is real but not statistically established at higher SNR. The apparent grid-wide signal is therefore almost entirely the peak-set decision, not goodness-of-fit. Full-grid regret runs 2–3× the within-set regret, so letting the selector roam across peak sets costs accuracy. The headline result concerns coverage, where reported 95% error bars contain the true ratio only {{t6b_snr15}} / {{t6b_snr50}} / {{t6b_snr200}} of the time at SNR 15/50/200. These conclusions hold on the spectra, configurations, and SNR regimes tested here.

## 6 Q3

Minimum detectable change (MDC) in I_D/I_G units (single-measurement precision;
alpha = {{mdc_alpha}}, power = {{mdc_power}}, n_rep = {{mdc_n_rep}}; excitation
{{mdc_wavelength}} nm), protocol configuration versus the naive everyday pipeline
(`{{naive_config}}`). Δn_D is the defect-density currency (cm⁻²).

| regime | protocol config | bias | RMSE | coverage | failure | protocol MDC | naive MDC | naive/protocol | protocol Δn_D | naive Δn_D |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SNR15 | {{protocol_config_snr15}} | {{protocol_bias_snr15}} | {{protocol_rmse_snr15}} | {{protocol_coverage_snr15}} | {{protocol_failure_snr15}} | {{protocol_mdc_snr15}} | {{naive_mdc_snr15}} | {{ratio_snr15}} | {{protocol_dnd_snr15}} | {{naive_dnd_snr15}} |
| SNR50 | {{protocol_config_snr50}} | {{protocol_bias_snr50}} | {{protocol_rmse_snr50}} | {{protocol_coverage_snr50}} | {{protocol_failure_snr50}} | {{protocol_mdc_snr50}} | {{naive_mdc_snr50}} | {{ratio_snr50}} | {{protocol_dnd_snr50}} | {{naive_dnd_snr50}} |
| SNR200 | {{protocol_config_snr200}} | {{protocol_bias_snr200}} | {{protocol_rmse_snr200}} | {{protocol_coverage_snr200}} | {{protocol_failure_snr200}} | {{protocol_mdc_snr200}} | {{naive_mdc_snr200}} | {{ratio_snr200}} | {{protocol_dnd_snr200}} | {{naive_dnd_snr200}} |

<!-- AUTHOR: Q3 interpretation — write interpretive prose here -->
The protocol detects smaller changes in I_D/I_G than the naive comparator in every noise regime. The minimum detectable change under the evidence-based protocol was {{protocol_mdc_snr15}} / {{protocol_mdc_snr50}} / {{protocol_mdc_snr200}} at SNR 15/50/200, against {{naive_mdc_snr15}} / {{naive_mdc_snr50}} / {{naive_mdc_snr200}} for the illustrative naive {{naive_config}} pipeline, so the protocol resolves a smaller change in every regime. The improvement is sharpest at SNR 50 ({{ratio_snr50}}×), where the protocol's precision advantage over the naive comparator is largest. This minimum detectable change is a precision statement: it rides on the repeatability, or spread, of the signed error rather than on whether the reported interval is honest. The protocol configuration is precision-picked, the DG/area config with the smallest signed-error standard deviation, and although its coverage is low the protocol MDC still beats the naive one, because detection depends on the spread of repeated measurements and not on interval honesty. Bias is reported separately, so a biased-but-precise configuration can detect changes while still misestimating absolute levels. In defect-density terms, the protocol resolves a change as small as {{protocol_dnd_snr50}} cm⁻² at SNR 50, setting the floor on the smallest defect-density shift the protocol can claim to detect, such as the kind a hydrogenation or defect-engineering step is meant to produce. These conclusions hold on the spectra, configurations, and SNR regimes tested here.

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
