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
