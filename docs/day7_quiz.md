# Day-7 Quiz

A short closed-book self-check on the Day-7 selector audit: the regret/rho
conventions, the resampling unit, and what V4 vs the V6 differential each prove.
Exactly 3 questions. Questions first; answers in a separate section below so the
author can take it closed-book.

---

## Questions

**Q1 — Sign and zero conventions.**
A selector is "lower-is-better." For one spectrum you compute Spearman
`rho(selector_value, abs_error) = -0.9` and `top1_regret = 0.0`. (a) Is a rho of
*−0.9* good or bad news about that selector, and why? (b) Explain how regret can
be exactly `0.0` *at the same time*, and what regret being `0` means operationally.
(c) Could regret ever come out negative? Why or why not?

**Q2 — The resampling unit.**
The audit aggregates per `(material_class, SNR regime, stratum, selector)` with a
1000-draw bootstrap. A colleague proposes resampling the **configuration rows**
within each cell with replacement, arguing "there are ~96 configs per spectrum,
so that gives tighter, better-powered CIs." Why is that wrong, what *is* the
resampling unit we use instead, and what specifically happens to a spectrum's
`within_peak_set` sub-values when that unit is drawn? Also: why is the reported
central statistic the **median** of the per-spectrum rho rather than the mean?

**Q3 — What each gate proves (and what it doesn't).**
(a) Gate V4 passes green. Does that tell you the selectors are *useful* on the
real hostile data? What exactly does V4 establish? (b) When you run the full
suite today, `test_selectors_match_reference` shows up as an **error**, not a
pass or a fail. Is the build broken? What is that test waiting on, and why was its
reference import deliberately written *inside* the test body? (c) T6b reports a
coverage of, say, 0.18 at SNR 200 — far below 0.95. Is that a bug in the interval
code?

---
---

## Answers

**A1 — Sign and zero conventions.**
(a) **Bad news — in fact the worst kind.** Because the selector is
lower-is-better and `abs_error` is lower-is-better, positive rho is the *good*
outcome (low selector value ↔ low error). A rho of **−0.9** means the criterion is
strongly *anti*-correlated with accuracy: the configs it likes best tend to be the
*least* accurate. It is not merely uninformative (that would be rho ≈ 0); it is
actively misleading.
(b) Regret looks only at the **single** config the selector ranks first
(`abs_error[argmin(selector)] − min(abs_error)`), not at the whole ordering. The
selector can rank the rest of the field backwards (driving rho to −0.9) yet still
happen to put the genuinely most-accurate config in *first* place — then
`abs_error[argmin] == min(abs_error)` and regret is exactly `0`. Operationally,
regret `0` means *"the config you would have picked is the oracle's pick; your
top choice cost you nothing in accuracy."*
(c) **No, never.** The oracle term `min(abs_error)` is by definition the smallest
`abs_error` in the set, so `abs_error[argmin selector] − min(abs_error) ≥ 0`
always. Non-negativity is structural, and we rely on it as a built-in correctness
check (V4 asserts the `= 0` case exactly).

**A2 — The resampling unit.**
The colleague is wrong because the ~96 configs of a spectrum are **not
independent observations** — they are 96 correlated fits of the *same* spectrum.
Treating them as independent draws would dramatically *understate* the
uncertainty and produce dishonestly tight CIs. The true unit of replication is the
**spectrum** (`case_id`), so we use a **clustered bootstrap over spectra**:
resample whole spectra with replacement. When a spectrum is drawn, **all of its
sub-values travel with it as a block** — in the `within_peak_set` stratum, all
three of that spectrum's per-peak-set rho values move together (they are never
split apart). The central statistic is the **median** because per-spectrum rho is
bounded in [−1, 1], skewed, and heavy-tailed near ±1; a plain arithmetic mean of
such raw correlations is not a faithful "typical" value, whereas the median is
robust and defensible. (The 0/1 quartile-hit is summarized by its mean = hit
rate, which is the natural estimator for a Bernoulli event.)

**A3 — What each gate proves (and what it doesn't).**
(a) **No — V4 says nothing about usefulness on real data.** V4 only proves the
*arithmetic* is correct: on two rigged spectra with answers known by hand, the
audit recovers rho **exactly +1**/regret **exactly 0** (correlated) and rho
**exactly −1** (anti-correlated), to floating-point epsilon. It validates the
engine, not the science; whether `redchi`/`aic`/`bic` actually track accuracy on
the hostile suite is what T6 *measures* (and the author interprets), not what V4
asserts.
(b) **The build is not broken.** `test_selectors_match_reference` is the
V6-style differential against `refimpl/ref_selectors.py`, which is authored by a
**separate blind session** and copied in afterward. Until that file exists the
import fails, so the test **errors by design**. The reference import is placed
*inside the test body* (deferred) specifically so the failure is **isolated to
that one test** — a module-level import would have collapsed the entire V6
differential module and taken the other (passing) gates down with it. Once
`ref_selectors.py` lands, the test should go green (agreement to < 1e-6).
(c) **Not a bug — it is the intended diagnostic.** T6b is *coverage under
misspecification*: it pools over the **whole grid, including misspecified
configs**, and the `[lo95, hi95]` intervals are **statistical-only** (a residual
bootstrap that knows nothing about model-form bias). On a hostile, largely
non-Lorentzian suite where misspecification bias dominates, the honest-but-naive
interval is *expected* to undercover badly. A low T6b is the system correctly
reporting how far the naive interval falls short of nominal — exactly the number
T6b exists to expose.
