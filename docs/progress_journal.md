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

Commit hash: 

Next action: Day 3 — Tier-A synthetic generator + Gate V1.