# Calibration Provenance

This document summarizes the calibration provenance recorded in
`data/calibrations/calibrations.yaml`. It introduces **no** source fact not
already in that YAML; the YAML remains the single source of truth, and every
physical constant used by `src/ramanuq/metrics.py` is read from it at runtime
(none are hard-coded).

## Tuinstra & Koenig 1970 — `tuinstra_koenig_1970`

- **Quantity:** L_a (crystallite size) — foundational inverse relationship.
- **Citation:** Tuinstra & Koenig, J. Chem. Phys. 53, 1126 (1970).
- **DOI:** 10.1063/1.1674108
- **Access date:** 2026-06-15
- **Relationship:** I_D/I_G proportional to 1/L_a (Fig. 3).
- **Constant + units:** none — `constant_value` is `n/a`; the paper gives a
  proportionality only ("not given in closed form").
- **Intensity definition:** height (inferred: no fitting, ratio of maxima).
- **Validity:** stage-1 nanocrystalline graphite.
- **Role in project:** foundational observation; the calibrated constant is
  taken from Cançado 2006/2011, not from this paper.

## Cançado 2006 — `cancado_2006`

- **Quantity:** in-plane crystallite size L_a of nanographite.
- **Citation:** Cançado et al., Appl. Phys. Lett. 88, 163106 (2006).
- **DOI:** 10.1063/1.2196057
- **Access date:** 2026-06-15
- **Equation:** L_a(nm) = (2.4 × 10⁻¹⁰) · λ_l⁴ · (I_D/I_G)⁻¹ — wavelength form
  (λ in nm), with **λ⁴ in the numerator**.
- **Constant + units:** 2.4e-10, units nm⁻³ (bare numeric coefficient, Eq. 2).
- **Intensity definition:** integrated area (the paper states it uses
  integrated intensities/areas of the D and G bands rather than peak
  amplitudes). → `metrics.py` feeds this calibration the **area** ratio.
- **Validity:** visible range of excitation laser energies used in the work
  (1.92–2.71 eV; ~647–457.9 nm).

## Cançado 2011 — `cancado_2011`

- **Quantity:** point-defect density n_D (areal) in single-layer graphene.
- **Citation:** Cançado et al., Nano Lett. 11, 3190 (2011).
- **DOI:** 10.1021/nl201432g
- **Access date:** 2026-06-15
- **Equation:** n_D (cm⁻²) = [(1.8 ± 0.5) × 10²² / λ_L⁴] · (I_D/I_G) — with
  **λ⁴ in the denominator**.
- **Constant + units + uncertainty:** 1.8e22 ± 0.5e22, units cm⁻² nm⁴.
- **Intensity definition:** peak intensity ratio (heights), explicitly
  decoupled from the area ratio; the working relation uses I_D/I_G amplitudes,
  not integrated areas. → `metrics.py` feeds this calibration the **height**
  ratio. The constant uncertainty is propagated **multiplicatively and
  separately** from the bootstrap interval as `n_d_const_uncertainty`.
- **Validity:** low-defect-density / stage-1 regime, L_D ≥ 10 nm, visible-range
  excitation; only defects that activate the D peak.
- **Guard notes (from YAML):** I_D/I_G is non-monotonic (peaks near L_D ~3 nm),
  so one ratio can map to two defect densities; disambiguate with the G-band
  width Γ_G (~14 cm⁻¹ in stage 1, much larger in stage 2). Silent defects
  produce no D peak and are not captured. ~±30% experimental error band.

## Intentional NaNs

- **`la_tk`** is intentionally `NaN`: Tuinstra & Koenig 1970 records **no
  project constant** (`constant_value: n/a`), so no L_a value is computed from
  it. The flag `tk_foundational_no_project_constant` is emitted.
- **`l_d`** is intentionally `NaN`: **no L_D equation is recorded** in the
  YAML. The flag `ld_equation_not_recorded` is emitted.

No TK or L_D constant is invented anywhere.

## Stage guard

The `stage_guard` block in the YAML holds **documented assumptions** (Day 5),
not paper-sourced calibration constants:

- `g_fwhm_max_cm1: 40` — fitted G-band FWHM above this is treated as
  stage-2-like.
- `d3_over_g_area_max: 0.15` — fitted D3 area / G area above this is treated as
  stage-2-like (checked only when a D3 band is present).

When either condition fires, `metrics.py` suppresses `la_cancado2006`, `la_tk`,
`n_d`, `l_d`, their intervals, and `n_d_const_uncertainty` to `NaN`, appends a
`stage2_guard:*` flag, and emits a warning. `id_ig` and its interval remain
valid. Per the YAML `source` note, the thresholds sit between the project's
synthetic stage-1 (G FWHM ~22 cm⁻¹, no D3) and stage-2 (G FWHM ~70 cm⁻¹, D3
~30% of G) regimes so the guard fires on stage 2 and never on stage 1.
