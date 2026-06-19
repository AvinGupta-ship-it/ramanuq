# Tier-1 L3 Read — metrics.py calibration wiring — Day 5

Blocks read against calibrations.yaml:
1. Required-field validation — raises on missing citation/doi/validity/intensity_definition; stage_guard exempt. OK
2. Constant parsing — str->float from YAML, raises on bad parse, none hard-coded in Python. OK
3. Ratios — area = D_area/G_area; height via lorentzian_height_from_area (2A/(pi*fwhm)); differ when widths differ. OK
4. Intensity-definition matching — La<-area, n_D<-height. CAUGHT A BUG: routing chose area/height by which keyword
   appeared first in the prose intensity_definition, so it was correct only by accident of word order; a reword would
   have silently fed the area ratio into the height-based n_D formula and Gate V6 would have stayed green (both
   implementations shared the flaw). Fixed: added an explicit intensity_kind field (area/height) sourced from each
   paper; classifier now reads that field. OK after fix.
5. Wavelength + lambda^4 — La: lambda^4 numerator; n_D: lambda^4 denominator; wavelength from fit.meta, not hard-coded. OK
6. Constant uncertainty — n_d * (0.5e22/1.8e22), separate from bootstrap interval. OK
7. Stage guard — thresholds from YAML stage_guard block; fires on G FWHM>40 or D3/G>0.15; D3 condition skipped
   safely when no D3; NaNs calibrated quantities + flag + warning; id_ig stays finite; no false-fire on stage-1. OK

Overall verdict: WIRING MATCHES MY PAPERS — Y
Signed: Avin Gupta — 6/19/2026
