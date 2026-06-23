# Protocol

Measured cells only — filled from the Tier-B grid study
(`data/synthetic/results/tierB_grid_results.parquet`), the Day-8 MDC computation
(`notebooks/04_mdc_casestudy_q3.ipynb`, `src/ramanuq/mdc.py`), and the Q1b
stability output (`ramanuq.robust.jackknife_ranking`). Material class:
`synthetic_disordered_carbon`. `recommended` = the protocol config selected per
regime (DG/area config with the smallest signed-error sd). `bias` is the mean
signed error (reported separately from precision). `MDC` is in I_D/I_G units
(single-measurement precision, alpha=0.05, power=0.8, n_rep=1); the Delta-n_D
currency is in notebook 04. The author writes all interpretation below.

| regime | recommended | bias | RMSE | coverage | failure | MDC | stability |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SNR15 | baseline=poly5, lineshape=gaussian, bwf_g=False, peak_set=DG, intensity=area | +0.02213 | 0.13314 | 0.467 | 0.000 | 0.52906 | undefined (Q1b vacuous; 0 rank-eligible configs) |
| SNR50 | baseline=als, lineshape=pseudo_voigt, bwf_g=False, peak_set=DG, intensity=area | -0.08613 | 0.10922 | 0.233 | 0.000 | 0.27065 | undefined (Q1b vacuous; 0 rank-eligible configs) |
| SNR200 | baseline=als, lineshape=pseudo_voigt, bwf_g=False, peak_set=DG, intensity=area | -0.01569 | 0.14105 | 0.200 | 0.000 | 0.56488 | undefined (Q1b vacuous; 0 rank-eligible configs) |

## Recommendations and scope (author writes this)

For the SNR15 regime, the recommended configuration is poly5 / gaussian / DG / area. It achieved a RMSE of 0.133, bias of +0.022, coverage of 0.467, a failure rate of 0, and an MDC of 0.529 in I_D/I_G (1.19e+11 in Δn_D) - versus the naive pipelines 0.745 in I_D/I_G. This gap means that the naive config requires a ~1.4x larger change to detect than the protocol config. However, no config reached the 0.90 coverage floor, so error bars undercover. This pick follows from measured accuracy, not goodness-of-fit, because the selector audit found fit statistics don't track accuracy. Rank-stability is undefined here because the coverage-gated ranking is empty. This recommendation holds on the spectra, configurations, and regimes tested here. 

For the SNR50 regime, the recommended configuration is als / pseudo_voigt / DG / area. It achieved a RMSE of 0.109, bias of −0.086, coverage of 0.233, a failure rate of 0, and an MDC of 0.271 in I_D/I_G (6.08e+10 in Δn_D) - versus the naive pipelines 0.763 in I_D/I_G. This gap means that the naive config requires a ~2.8x larger change to detect than the protocol config. However, no config reached the 0.90 coverage floor, so error bars undercover. This pick follows from measured accuracy, not goodness-of-fit, because the selector audit found fit statistics don't track accuracy. Rank-stability is undefined here because the coverage-gated ranking is empty. This recommendation holds on the spectra, configurations, and regimes tested here. 

For the SNR200 regime, the recommended configuration is als / pseudo_voigt / DG / area. It achieved a RMSE of 0.141, bias of −0.016, coverage of 0.200, a failure rate of 0, and an MDC of 0.565 in I_D/I_G (1.27e+11 in Δn_D) - versus the naive pipelines 0.703 in I_D/I_G. This gap means that the naive config requires a ~1.2x larger change to detect than the protocol config. However, no config reached the 0.90 coverage floor, so error bars undercover. This pick follows from measured accuracy, not goodness-of-fit, because the selector audit found fit statistics don't track accuracy. Rank-stability is undefined here because the coverage-gated ranking is empty. This recommendation holds on the spectra, configurations, and regimes tested here. 

Recommendations authored 2026-06-22 (Avin Gupta).