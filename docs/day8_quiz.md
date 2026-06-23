# Day 8 — Quiz: Minimum Detectable Change (MDC)

Three questions on the MDC concept. Answers are in the separate section below;
try them before scrolling.

## Questions

**Q1 — The formula, term by term.**
Write the MDC formula used in `ramanuq.mdc.mdc`. Identify each of the two
z-values (with their numeric values at alpha = 0.05 and power = 0.8), explain why
the `sqrt(2)` factor is present, say what `sigma_single` is in *this project*,
and state what happens to the MDC when `n_rep` goes from 1 to 4.

**Q2 — Bias vs precision, and Δn_D propagation.**
(a) Why is **bias** computed and reported *separately* from `sigma_single` rather
than added into the MDC? (b) Given an MDC in I_D/I_G units, how is it propagated
into Δn_D units, and why is the constant-uncertainty band carried
*multiplicatively*? Where do the constant `1.8e22` and its uncertainty `0.5e22`
come from in the code?

**Q3 — Naive vs protocol, the FM5 caveat, and the legitimacy of the pick.**
(a) Define the NAIVE configuration and the PROTOCOL configuration used in
notebook 04, and say which direction their MDCs differ and why. (b) State the
FM5 illustrative caveat. (c) Using the Day-6 accuracy ranking and the Day-7
selector/coverage findings, justify why the protocol pick (DG/area, smallest
error sd) is a *legitimate* choice and not cherry-picking.

---

## Answers

**A1.**
`MDC = (z_{1-alpha/2} + z_power) * sqrt(2) * sigma_single / sqrt(n_rep)`.
- `z_{1-alpha/2}` is the **two-sided false-positive** critical value; at
  alpha = 0.05 it is `norm.ppf(0.975) ≈ 1.95996`. The split across both tails
  covers changes in either direction.
- `z_power` is the **one-sided power** value; at power = 0.8 it is
  `norm.ppf(0.8) ≈ 0.84162`. It gives the margin so a true change of size MDC is
  caught 80% of the time, not 50%.
- `sqrt(2)` is present because a detectable *change* is the **difference of two
  independent measurements**; the variance of that difference is 2σ², so its sd
  carries `sqrt(2)`.
- `sigma_single` is the **single-measurement precision** — in this project the
  sample sd (ddof=1) of the *signed I_D/I_G error* over the suite spectra of one
  (config, regime) cell.
- Going `n_rep` 1 → 4 multiplies the MDC by `1/sqrt(4) = 1/2`: the MDC **halves**.

**A2.**
(a) `sigma_single` measures only **scatter (precision)**; it is blind to a
systematic offset. **Bias** is the *mean* signed error — the accuracy / zero-point
error. They answer different questions (MDC = "what change can I resolve?", bias =
"how far off is my center?"). Folding bias into the MDC would mask a
precise-but-inaccurate configuration, so bias is reported as its own number
(`estimate_bias`) and never added into the MDC.
(b) The Cancado-2011 relation `n_D = [const/λ⁴]·(I_D/I_G)` is **linear and
multiplicative** in the ratio, so a change `MDC` in I_D/I_G maps to
`C(λ)·MDC` in n_D with `C(λ) = const/λ⁴`. Because the map is a pure
multiplication, the published constant uncertainty propagates multiplicatively
too: carry `C_lo/C_central/C_hi = (const ∓/± uncertainty)/λ⁴` and return
`(C_central·MDC, C_lo·MDC, C_hi·MDC)`. The numbers `1.8e22` and `0.5e22`
(cm⁻² nm⁴) are **read from `calibrations.yaml`** via `load_calibrations` (the
`cancado_2011` entry's `constant_value` and `constant_uncertainty`); they are not
hard-coded in Python, and `to_delta_nd` raises if the uncertainty field is
missing rather than guessing.

**A3.**
(a) **NAIVE** = `linear` baseline, single `lorentzian` (no BWF), `DG` peak set,
`height` ratio — the non-specialist default. **PROTOCOL** = the DG/area
configuration with the **smallest signed-error sd** in each SNR regime. The
protocol's smaller `sigma_single` gives a **smaller MDC** (it resolves finer
changes) — observed in notebook 04 in both I_D/I_G and Δn_D currencies.
(b) **FM5 caveat:** the naive-vs-protocol MDC numbers are an **illustration** of
the methodology on this synthetic disordered-carbon suite, not a validated field
protocol; they are scoped to these spectra/configs/SNR regimes, and the
protocol's stability is undefined because the Q1b jackknife is vacuous (no
rank-eligible config under the pre-registered coverage floor).
(c) The pick is legitimate, not cherry-picked: **Day 6** showed peak set is the
dominant accuracy driver (DG ~5× tighter than band-heavy sets) and that the
low-bias Gate-V3 passers were all DG/area — so the candidate pool is fixed to
DG/area on *prior* accuracy grounds, before looking at the sd. **Day 7's Q2
audit** showed fit-quality selectors track accuracy only weakly (and only at
SNR15), so we do *not* let a selector roam across peak sets to choose; and
**T6b** showed standard intervals undercover (18–28%), so the protocol card
reports MDC and bias as measured quantities and flags coverage honestly rather
than asserting 95% trust.
