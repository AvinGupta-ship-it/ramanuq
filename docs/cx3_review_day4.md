# CX-3 Numerical Edge-Case Review — Day 4

Reviewer: fresh Claude Code session (review-only), 2026-06-18
Triaged by: Avin Gupta

Result: 0 BLOCKERs, 2 NITs.

Verification the reviewer performed: regenerated all 90 Tier-B cases in memory
and confirmed bit-for-bit match to committed CSV + truth JSON (0 mismatches);
measured non-Lorentzianity residuals across all 90 cells; confirmed 90/90
pairing with no orphans.

Highest-priority check PASSED: truth (true_id_ig_area, true_id_ig_height) is
computed from the noiseless, baseline-free generator callables BEFORE baseline
and noise are added. No truth derived from any fit or observed spectrum.

Non-Lorentzianity margin: composite D residuals 5.1%-53.3%, EMG G 15.6%-21.7%;
the >1% gate clears by 5x+ in the worst case.

NIT 1 (recorded, no fix): negative observed intensities occur at low SNR with
no baseline, from the pre-registered additive Gaussian noise model already used
by Tier-A. Physically expected; not a Day-4 defect.

NIT 2 (recorded, no fix): the EMG G-band self-normalizes to ~1000 total area,
so the area-ratio truth denominator is ~fixed by construction and area-ratio
spread across cases is D-band-driven. Correct and documented; noted for
interpretation of area-definition results later. Height-ratio truth unaffected.

Decision: Day 4 is safe to commit. No blockers; both NITs are pre-existing
design consequences, not defects.
