# Progress Journal

## Tuinstra & Koenig 1970

- **What it establishes:**: ID/IG is inversely proportional to the crystallite size in graphite
- **Key equation/relationship:**: ID/IG = C/La
- **Intensity definition (stated or inferred):**: Height (inferred due to no curve fitting mentioend)
- **Why it matters for RamanUQ:**: foundational observation, later built on and defined by Cancado 2006/2011

## Cancado 2006

- **What it establishes:**: wavelength-dependent L_a equation — the calibrated upgrade to TK-1970
- **Key equation/relationship:**: L_a(nm) = (2.4 × 10⁻¹⁰) · λ_l⁴ · (I_D/I_G)⁻¹
- **Intensity definition (stated or inferred):**: "integrated area (stated: 'integrated intensities (areas) of the D and G bands instead of ... peak amplitudes')"
- **Why it matters for RamanUQ:**: gives calibrated constant for L_a based on ID/IG, builds on TK-1970 to give quantitative calculations

## Cancado 2011

- **What it establishes:**: Point-defect quantification in single-layer graphene (interdefect distance L_D, areal density n_D) from I_D/I_G at any visible wavelength.
- **Key equation/relationship:**: n_D (cm⁻²) = [(1.8 ± 0.5) × 10²² / λ_L⁴] · (I_D/I_G), Eq. (6).
- **Intensity definition (stated or inferred):**: Peak heights, explicitly decoupled from area ratio.
- **Why it matters for RamanUQ:**: The point-defect calibration (vs. crystallite sizing) for irradiated SWCNT/GO/rGO; gives λ⁴ cross-laser scaling. Guards: valid only L_D ≥ 10 nm; I_D/I_G non-monotonic (peaks ~3 nm), so pair with Γ_G.

## Ferrari & Robertson 2000

- **What it establishes:**: Three-stage amorphization model (graphite → nc-graphite → a-C → ta-C); visible Raman tracks sp² clustering, not sp³ directly. Defines where TK 1/L_a holds and where it reverses.
- **Key equation/relationship:**: Stage 1 (TK): I(D)/I(G) = C(λ)/L_a, C(515.5 nm) ≈ 44 Å, Eq. (8). Stage 2: I(D)/I(G) = C′(λ)·L_a², C′(514 nm) ≈ 0.0055, Eq. (12).
- **Intensity definition (stated or inferred):**: Peak heights (stated default); BWF for G + Lorentzian for D. Height/area choice is fit-method-coupled.
- **Why it matters for RamanUQ:**: Guard rail for the whole TK/Cançado family. I(D)/I(G) vs L_a is non-monotonic (peaks ~2 nm); TK XRD-verified only down to L_a ≈ 20 Å; underestimates L_a for mixed grain sizes. Pins the height-vs-area ambiguity to fit model — the main source of silent cross-study mismatch.

## Day 2 — Instrument layer — 2026-06-18

Modules implemented: io.py frozen Spectrum container with input validation (monotonic shift, finite values, positive wavelength). despike.py rolling-median z-score cosmic-ray removal, idempotent because flagged channels are replaced with the local median. baseline.py four background estimators (linear, poly3, poly5, ALS Eilers-Boelens) under one signature, returning baseline plus diagnostics. lineshapes.py vectorized Lorentzian, Gaussian, and area-parameterized pseudo-Voigt plus height-parameterized BWF, with analytic height/area/FWHM converters. model.py bounded composite peak model from a peak set (DG, DGDp, DGDpD3D4), seeded by windowed maxima. fit.py full pipeline (despike, baseline-subtract, bounded WLS, residual bootstrap) returning FitResult with redchi, AIC, BIC, and n_failed, never raising on non-convergence.

Tests run and result: All Day-2 unit and behavioral tests pass (54); ruff clean. Coverage spans lineshape identities (area and FWHM round-trip 1e-6, height 1e-8, pseudo-Voigt eta-limits), io validation errors, despike idempotence and single-spike recovery, baseline finite outputs across all four methods, and fit returning the three criteria while counting n_failed.

Gate V6: pass. Compared src Lorentzian, Gaussian, pseudo-Voigt, BWF, and src AIC/BIC against clean-room ref_lineshapes.py and ref_criteria.py on 500 randomized valid inputs, tolerance <1e-9 relative (analytic) and <1e-6 (numeric). Today's V6 covers lineshapes and criteria only; metrics join the differential on Day 5.

What Claude Code did: Session A (implementer) built all six modules and the full unit/behavioral suite, debugging against tests autonomously. Session B (reference agent) wrote ref_lineshapes.py and ref_criteria.py from the math spec alone, never reading src, then authored test_differential_v6.py. Session C (reviewer) ran the CX-1 adversarial pass over the wave and reported findings.

What I personally verified: Confirmed area-parameterization for Lorentzian, Gaussian, and pseudo-Voigt with BWF height-parameterized, and that no physical constant is hard-coded in source (grepped the diff for digits). Confirmed Session B authored the references from spec with no sight of src, which is what makes the V6 agreement real evidence. Confirmed V6 and the lineshape/criteria tests green in CI. Read the briefing and passed the three-question quiz. Ruled on the CX-1 findings; no blocker. No line-reading this wave, by design.

What I learned today: Area parameterization is the load-bearing choice in lineshapes.py. It makes band intensities additive when peaks overlap, and it is why pseudo-Voigt holds the same total area for any eta. BWF breaks this because its tails settle to a nonzero floor instead of decaying, so it has no finite integral and an area-based I_D/I_G becomes undefined whenever the G band is modeled as BWF. The verification logic also landed: V6 treats agreement between two independent implementations as stronger than my own line-reading, which is why the reference agent never sees src.

Unresolved issues / deferred: No CX-1 blockers. Non-blocking nits, if any, logged to carry into Day 3.

Commit hash: 4bca08e (Day 2 complete, CI green; initial commit 95aef56 + refimpl-packaging fix)

Next action: Day 3 — Tier-A synthetic generator + Gate V1.

TIER-A REALISM EYEBALL GATE — Day 3 — 2026-06-18
Plots: tierA_stage1_r1p0_noiseless.png, tierA_stage2_r1p0_noiseless.png
Stage-1: D ~1350, G ~1585, D' minor shoulder, sane widths, smooth (noiseless) — plausible.
Stage-2: broad D/G + D3/D4 humps, disordered morphology — plausible.
Two cases visibly different: yes.
RATING: PASS
My judgment: Generated spectra have correct peak heights and positions, plausible as fitted spectra collected from real samples
(one sentence in your own words — e.g. how they compare to spectra you've measured)

## Day 3 - Tier-A truth + Gate V1 - 2026-06-18
Built the Tier-A in-family validation layer (synth.py + suite + Gate V1 + determinism tests) directing Claude Code Session A; 45 cases across stage {1,2} × ratio {0.1,0.5,1.0,2.0 (stage-1)} × baseline {none,mild,strong} × SNR {200,50,15} plus noise-free recovery cases; 45 CSV/45 truth JSON, bijective pairing verified by an independent shell audit and the schema test. Gate V1 recovered every noise-free matched case to < 0.004% relative error (worst: stage-2), confirming the generator and Day-2 fitter agree on conventions and the optimizer finds in-family truth — an implementation check, not an accuracy claim, which I'm careful to keep distinct from the Tier-B science. I personally verified truth is computed analytically from the noiseless band functions (not refit), that both true_id_ig_area and true_id_ig_height are stored (they differ by the Γ_G/Γ_D factor, ≈0.629 vs 1.0 at area-ratio 1.0 — the same area/height tension I flagged between Cançado 2006 and 2011), and that no calibration or prediction file changed. Realism gate: PASS — stage-1 reads like our cleaner graphene/CNT spectra, stage-2 like disordered rGO with D3/D4 shoulders; smoothness is expected for noiseless Tier-A. CX-2 raised one NIT (malformed-input coverage), logged for Day 4. Key insight: Tier A earns the right to run Tier B by proving the engine has no excuse to be wrong. Commit <55c9eae>. Next: Day 4 — Gate V2 baselines + the hostile generators and THE realism gate.

## Day 4 — 2026-06-18
Day 4: built hostile.py (composite/EMG/mixed-η bands + smooth random baselines) and finalized Gate V2; committed 90 Tier-B spectra (2 stages × 3 baselines × 3 SNR × 5 instances), each with baseline-free, noiseless truth under both area and height definitions. The scientifically important result is that the non-Lorentzianity residuals (composite 5–53%, EMG 16–22%) clear the 1% gate by 5×+ — this is the first dataset in the project where the fitter cannot recover truth, which is exactly the regime my real rGO/CNT spectra live in and where Q1–Q3 become real questions rather than tautologies. The judgment I had to make myself: the pre-registration didn't specify which baseline method is graded on which background, so I set in-class pairing (linear on flat only, since a straight line categorically can't fit a curve) and recorded it — this was a scientific scope call, not a tolerance change. My realism gate (PASS) is the claim no test can make: the spectra are non-Lorentzian and look like data I could have collected, which is what makes the benchmark transfer to reality. CX-3 (independent agent) confirmed truth is never derived from a fit and the suite reproduces bit-for-bit; its two NITs (low-SNR negative intensities; EMG area-denominator self-normalization) I ruled pre-existing design consequences. Verified personally: all gates green by my own run, Tier-A untouched, no Day-5 scope. Next: Day 5 wires metrics.py to the YAML calibrations under a stage guard, with my hand-pin #2 — the first time today's truth gets converted toward physical defect densities. hash: <eo7ced4>

## Day 5 — 2026-06-19
Day 5: Built the metrics layer — the bridge from fitted I_D/I_G to L_a and n_D through my Cançado calibrations, with all constants read from YAML and a stage guard that refuses to apply stage-1 calibrations to stage-2-looking spectra (NaN + reason + warning). I hand-computed La=19.22 nm and n_D=2.25e11 cm⁻² and pinned the tests to my arithmetic. During the Tier-1 read I caught a real physics bug: the code chose area-vs-height by which keyword appeared first in my provenance prose, so it was right only by accident of word order — a reword would have silently fed the area ratio into the height-based n_D formula, and Gate V6 would have stayed green because both implementations shared the same flaw. I replaced it with an explicit intensity_kind field I sourced from each paper. Gate V6 now covers metrics; next is the Day-6 grid and Q1 ranking. <commit:dd89103a2cae541d39b91e77f731724da1171eca>

## Day 6 — 2026-06-22

**Built:** grid.py (96-config factorial over baseline × lineshape × bwf_g × peak_set × intensity; run_study with truth-join; descriptive decompose; rank_configurations) and robust.py (Q1b jackknife). Gate V3 and schema-freeze tests added. Study ran 8640 rows at n_boot=40.

**What the ranking showed:** The headline is that nothing is rank-eligible — T5 is empty. At first that reads like a broken pipeline, but it's the opposite: it's the pipeline correctly refusing to certify any configuration. Every config's empirical 95% coverage tops out at 0.80, so none clears my pre-registered 0.90 floor. The ranking isn't empty because the code failed; it's empty because no standard analysis choice produces honest uncertainty on hostile data. That's a finding, and a sharper one than "config X won" would have been — it says the whole field's default practice (report a ratio with a bootstrap error bar) is dishonest about its own uncertainty when the model is wrong.

**The coverage finding:** The bootstrap intervals only capture statistical scatter — they have no idea the lineshape itself is misspecified. On Tier-B the dominant error is bias from fitting a Lorentzian-family model to genuinely non-Lorentzian bands, and the interval just doesn't span that bias. So the point estimate is off (I_D/I_G under-estimated by ~0.1–0.35 on a true ~1.0) while the interval stays narrow, and the truth lands outside it most of the time → coverage ~0.80, never 0.90. This is exactly FM4 from my pre-registration, landing as the headline instead of a footnote.

**Accuracy vs honesty:** The thing that struck me is that these come apart. Gate V3 passed — 9 classes (all DG/area) are near-unbiased, best at 0.5% bias. So configs absolutely can hit the right central value. But those same accurate configs still undercover. A config can be accurate and dishonest at the same time: right answer, lying error bar. That split is the real methodological lesson — "low bias" and "trustworthy interval" are different properties and you can't assume one from the other.

**Q1b:** Vacuous here, and that's honest, not a dodge. With no rank-1 config, there's no recommendation to jackknife — 0 configs, 0 flips, retention undefined. If a config had been eligible, Q1b would've told me whether its #1 spot survived dropping a baseline class or a suite instance. The "your ranking depends on your grid" attack can't even arise when the grid produced no winner. I'm recording it as undefined, not "stable."

**What I verified:** Hand-checked als·pseudo_voigt·DG·area on tierB_stage1_blmild_snr50_i3. Confirmed the area config joined the area truth (0.988), not the height truth (2.031) — so the Day-5 intensity routing is working end-to-end in the study — and error = 0.99860 − 0.98808 = +0.01052 checks out. That row also makes the headline concrete: +1% error, but coverage 0.23. Accurate, dishonest.

**What I learned / what surprised me:** I expected a ranking with a winner and some caveats. Getting no winner felt wrong until I understood why — and then it became the most interesting result of the project. Also surprised that the simplest configs (DG/area, fewest parameters) are both the most accurate and the least dishonest; adding D′/D3/D4 bands didn't help, it overfit (~5× worse error). Complexity hurt. <commit: d6cf19?>

**Next (Day 7):** Selector audit Q2. 

## Q2 Verdict — Selector Audit (Day 7)

**Prediction (Section 5, registered 2026-06-15, verbatim):**
"I predict H_C (mixed), specifically that fit quality and I_D/I_G accuracy will be
decoupled across different peak sets but loosely correlated within one fixed set.
Practically: if you let the model pick from many different peak configurations, the
best-scoring one often isn't the most accurate (high regret); but if all candidates
share the same peaks, the best-scoring one usually is close to accurate (low regret).
I expect the within-set correlation to be positive but weak, and weakest for messy
spectra like hydrogenated SWCNTs and rGO."

**Result** (synthetic_disordered_carbon suite, 30 spectra/cell; ρ = median per-spectrum
Spearman, 95% spectrum-level bootstrap CI; regret in I_D/I_G units):
- Full-stratum ρ: all medians within ±0.08 of zero (range −0.079 to +0.063); CI clears
  zero in 4 of 9 cells (bic SNR15 +0.046 [+0.006,+0.078]; redchi SNR15 −0.079
  [−0.142,−0.014]; redchi SNR200 −0.077 [−0.144,−0.001]; aic SNR200 −0.052
  [−0.132,−0.001]) — the established ones for redchi lean negative.
- Within-peak-set ρ: positive in all 9 cells; CI clears zero in only 3 (all SNR15:
  aic +0.094 [+0.024,+0.160], bic +0.084 [+0.023,+0.180], redchi +0.081
  [+0.024,+0.165]); the other 6 (SNR50, SNR200) straddle zero.
- Regret: full-stratum 2–3× within-stratum at every SNR (SNR15: 1.37 vs ~0.44;
  SNR50: 0.55–0.67 vs 0.28–0.34; SNR200: 0.88 vs 0.38–0.42).
- T6b coverage under misspecification: 0.276 / 0.240 / 0.183 at SNR 15 / 50 / 200.

**Sub-claim 1 — decoupling across peak sets (full grid):** Predicted full-stratum ρ near
zero and high regret. ρ near zero with mostly straddling CIs, but 4 cells clear zero
(decoupling holds for most, not all cells). Full regret is 2–3× within regret at every
SNR (the high-regret prediction holds). → **PARTIALLY CONFIRMED** (regret contrast strong;
ρ near-zero but a few faint effects, redchi leaning slightly negative).

**Sub-claim 2 — coupling within a fixed peak set:** Predicted within-set ρ positive and
low regret. Median ρ positive in all 9 cells, but the CI clears zero in only 3 (all at
SNR15); the other 6 straddle zero, so coupling is established only for the noisiest
spectra and not statistically established at SNR50/200. Within regret is the low side of
the contrast (2–3× below full). → **PARTIALLY CONFIRMED** (real positive coupling at SNR15;
positive-but-not-established at higher SNR).

**Sub-claim 3 — within-set correlation positive but weak:** Predicted small positive
within-set ρ. The established within-set ρ's are +0.08 to +0.09 — positive and genuinely
tiny, exactly as predicted; at SNR50/200 the effect is even weaker (positive but not
established). → **CONFIRMED** (if anything, weaker than predicted at higher SNR).

**Sub-claim 4 — weakest for messy spectra (hydrogenated SWCNTs, rGO):** This suite has a
single material_class (synthetic_disordered_carbon) and no material-class axis, so the
prediction as written is UNTESTABLE here. Using SNR as a noise/messiness proxy, within-set
coupling was *strongest* (and only established) at the noisiest SNR15 and washed out at the
cleanest SNR200 — the opposite direction. → **UNTESTABLE AS WRITTEN; REFUTED VIA SNR PROXY.**
Flagged for future work with a multi-material suite.

**Overall verdict: PARTIALLY CONFIRMED.** The central structural prediction — accuracy
decoupled across peak sets, coupled within a fixed set — broadly held: the full grid is
near-decoupled with 2–3× higher regret, and within-set correlation is positive with lower
regret. But the within-set coupling is statistically established only for the noisiest
(SNR15) spectra, and the specific claim that messy spectra would show the weakest coupling
was untestable as written and ran backwards under an SNR proxy.

**Mechanism:** Day-6 established peak set as the dominant accuracy driver (DG configs ~5×
more accurate than band-heavy sets). Within a fixed peak set, only baseline/lineshape/
intensity vary, and these move accuracy little — leaving a small accuracy signal for fit
quality to track (the weak positive within-set ρ). Across peak sets, the selector can swing
between DG and overfitting band-heavy sets, producing the high full-grid regret.

**Headline result:** The practically important finding is not in ρ but in T6b: the typical
configuration's nominal 95% interval contains the truth only 18–28% of the time across SNR
regimes — reported error bars are not honest 95% intervals under realistic misspecification
(the expected FM4 outcome, elevated to a headline).

**Scope:** Holds on the spectra, configurations, and SNR regimes of the synthetic
disordered-carbon suite tested here.

— Avin Gupta, 2026-06-22

## Day 7 - 2026-06-22
The deeper point is that goodness-of-fit is not a usable accuracy selector on hostile spectra — its apparent signal is almost entirely the peak-set decision, which AIC/BIC's complexity penalty handles only coarsely. The practical advice the protocol should carry is therefore don't trust fit statistics to pick your analysis, and the citable result is the undercoverage, not the selectors. The CX-4 catch is also worth keeping: a filter that looked correct in my read (uniform across selectors) was incomplete (wrong columns), and the independent audit caught what I skimmed — exactly why the two-pass design exists.<hasH: 0fb6ff0baedef3ba790603f883e621a33021c040>