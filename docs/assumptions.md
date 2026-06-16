# Assumptions

## A1 — Single 1-D spectra only

We consider only single one-dimensional spectra (intensity versus wavenumber),
not spatial maps or higher-dimensional data.

**Justification (draft):** The core scientific questions concern band intensity
extraction from individual spectra, so a 1-D treatment captures the relevant
physics without added complexity.

**If relaxed (draft):** Supporting 2-D maps or hyperspectral data would require
spatial models and per-pixel uncertainty propagation beyond the current scope.

## A2 — Additive independent noise after despiking

We assume that, after despiking, the remaining noise is additive and independent
across spectral channels.

**Justification (draft):** Despiking removes cosmic-ray and outlier spikes,
leaving detector and shot noise that is well approximated as additive and
channel-independent.

**If relaxed (draft):** Correlated or multiplicative noise would require a full
covariance model and would change the likelihood used in fitting.

## A3 — The configuration grid samples common practice, not all practice

We assume the configuration grid samples common analysis practice rather than
exhaustively covering every possible practice.

**Justification (draft):** A grid anchored to widely used choices keeps the study
tractable while remaining representative of how practitioners actually analyze
spectra.

**If relaxed (draft):** Covering all practice would expand the grid combinatorially
and dilute statistical power per configuration.

## A4 — Calibrations used only within stated stage-1 validity

We assume each calibration is applied only within its stated stage-1 range of
validity.

**Justification (draft):** Using calibrations inside their published validity
domain avoids extrapolation error and keeps derived quantities defensible.

**If relaxed (draft):** Extrapolating beyond stated validity would introduce
uncontrolled systematic error that the uncertainty budget does not account for.

## A5 — No instrument-response or wavelength-dispersion correction; comparisons within-spectrum at fixed wavelength

We assume no instrument-response or wavelength-dispersion correction is applied,
and that comparisons are made within a single spectrum at a fixed excitation
wavelength.

**Justification (draft):** Within-spectrum comparisons at fixed wavelength cancel
shared instrument-response factors, so an explicit correction is not required.

**If relaxed (draft):** Cross-wavelength or cross-instrument comparison would
require an absolute response and dispersion calibration to be valid.
