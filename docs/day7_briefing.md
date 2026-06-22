# Day-7 Briefing — The Selector Audit (Q2)

A ~15-minute read on what Q2 asks, the four numbers we compute, the two strata,
the spectrum-level bootstrap, table T6b, and the two gates (V4 and the
V6-for-selectors differential). No result is interpreted here — this is the
machinery, not the verdict.

---

## 1. The question (Q2)

Day 6 (Q1) asked *which configuration is most accurate*. Q2 asks a different,
operational question:

> **If you had to pick a configuration using only a model-selection criterion you
> can compute without truth — reduced chi-squared, AIC, or BIC — how well would
> that pick track the configuration's actual accuracy?**

This matters because in the real world you never see `true_id_ig`. You fit a
spectrum under several configurations and you must *choose one* from quantities
the fit itself reports. A selector is only useful if low selector value really
does mean low error. Q2 measures exactly that, per regime, with honest
uncertainty.

The three selectors are taken straight from the frozen result schema
(`grid.RESULT_COLUMNS`): `redchi`, `aic`, `bic`. All three are **lower-is-better**
— a smaller value is the model the criterion prefers. The "ground truth" the
selector is judged against is `abs_error = |id_ig − true_id_ig|` (also
lower-is-better).

Recall the information criteria (same definitions used in `fit.py`, natural log):

```
AIC = n·ln(RSS/n) + 2k
BIC = n·ln(RSS/n) + k·ln(n)
```

with `n` data points, `k` free parameters, `RSS` the residual sum of squares.
BIC penalizes parameters harder than AIC once `ln(n) > 2` (i.e. `n > 7`), so BIC
leans toward simpler peak sets. We do **not** recompute these in the audit — they
are already columns in the parquet; the audit only *ranks by* them.

---

## 2. The four per-spectrum numbers

For one spectrum and one selector, over its set of surviving configurations:

### Spearman rho — *does the ranking agree?*
`rho = spearmanr(selector_value, abs_error)`. Spearman is the Pearson
correlation of the **ranks**, so it measures monotonic agreement, not linear
fit, and is immune to the very different scales of (say) BIC and `abs_error`.

- **rho ≈ +1**: the selector orders configs exactly as accuracy does — the config
  it likes least is the least accurate, the one it likes most is the most
  accurate. This is the *good* outcome (low selector ↔ low error).
- **rho ≈ 0**: the selector is blind to accuracy.
- **rho ≈ −1**: the selector is actively misleading — it prefers the *worst*
  configs.

**Ties use AVERAGE ranks** (the `scipy.stats.spearmanr` convention): two configs
with the same selector value share the mean of the ranks they would have
occupied. This is deliberate — an ordinal/first-occurrence tie-break would invent
an ordering the data does not support and bias rho. The tie-handling test pins
this down.

### Top-1 regret — *how much accuracy did the pick cost?*
`top1_regret = abs_error[argmin(selector)] − min(abs_error)`.

You pick the single config the selector ranks first (its argmin, because
lower-is-better). Regret is how much worse that pick is than the *oracle* — the
best config you could have picked if you'd had truth. It is **≥ 0 by
construction** (the oracle is by definition the minimum, so nothing can beat it);
that non-negativity is itself a correctness check. Regret is in the natural units
of `abs_error` (I_D/I_G units), so it is directly interpretable: "using this
selector costs you, typically, X in I_D/I_G error versus a perfect chooser."

### Top-quartile hit — *did the pick land among the best?*
A 0/1 indicator: `1` if the selector-min config's `abs_error` is in the
most-accurate quartile of the spectrum's configs. The threshold is the 25th
percentile of `abs_error`, and membership uses a **single, consistent inclusive
rule**: `abs_error ≤ threshold` → hit. Aggregated over spectra this becomes a
*hit rate* — the fraction of spectra on which the selector's top pick was at
least top-quartile accurate. It is a coarser, more forgiving companion to regret.

---

## 3. The two strata — *full* vs *within_peak_set*

The same four numbers are computed under two rankings:

- **full** — rank ALL of a spectrum's surviving configs against each other. This
  is the honest end-to-end question ("pick any config off the whole grid").
  Because the grid mixes 1-, 2-, and 4-band peak sets with wildly different
  parameter counts, the information criteria here are partly comparing model
  *complexity*, not just fit quality.
- **within_peak_set** — rank only configs that share a `peak_set` (DG vs DGDp vs
  DGDpD3D4). This holds the band structure fixed, so the selector is judged on a
  more apples-to-apples choice (baseline, lineshape, intensity) within one model
  family. It isolates "can the criterion choose *settings*" from "can it choose
  *how many bands*."

Comparing the two strata is informative: a selector that looks useless in `full`
but reasonable `within_peak_set` is being defeated by the cross-family complexity
comparison, not by within-family noise.

---

## 4. Aggregation: the spectrum-level bootstrap

The per-spectrum numbers are aggregated per
`(material_class, SNR regime, stratum, selector)` cell. Two design choices matter:

**Central statistic = MEDIAN (for rho and regret).** We deliberately do **not**
report a plain arithmetic mean of the raw correlations. Per-spectrum rho values
are bounded in [−1, 1], skewed, and heavy-tailed near the bounds; their mean is
not a faithful "typical" value. The median is robust and defensible. (The
quartile-hit, being a 0/1 event, is summarized by its mean = hit rate.)

**Resampling unit = the SPECTRUM.** The bootstrap (1000 draws, seeded from the
project `SEED = 20260615`) resamples whole **spectra** (`case_id`) with
replacement — a *clustered* bootstrap. When a spectrum is drawn, all of its
sub-units travel with it (in `within_peak_set`, that means all three of its
per-peak-set rho values move together). This respects the real unit of
replication: we have many configs per spectrum but they are NOT independent
observations — the independent draws in this experiment are the spectra. Bootstrapping
configs would massively understate uncertainty. The 2.5/97.5 percentiles of the
1000 resampled medians give the reported 95% CI. The seed is fixed and mixed with
the cell key so the CIs are exactly reproducible and order-independent.

---

## 5. Table T6b — coverage under misspecification

T6b is a separate, complementary diagnostic.
`coverage_under_misspecification(study_df)` reports, per
`(material_class, SNR regime)`, the empirical fraction of interval rows whose
`true_id_ig` falls inside `[lo95, hi95]`, **inclusive of both endpoints**
(`lo95 ≤ true ≤ hi95`).

The "under misspecification" framing is the point: rather than scoring one
correctly-specified model, T6b **pools over the entire grid** — including the
misspecified configurations — to ask what coverage you actually get if you draw
configs indiscriminately. The bootstrap intervals are *statistical-only*
(residual bootstrap on the fit); they do not know about model-form bias, so on a
hostile suite where misspecification dominates, T6b is expected to sit well below
the nominal 0.95. It quantifies how badly the honest-but-naive interval
undercovers once you stop assuming the model is right.

---

## 6. The gates

### Gate V4 — exact rigged-case recovery (`@pytest.mark.validation`)
Before trusting any real number, we prove the machinery is arithmetically correct
on cases whose answers are known by hand. `rigged_cases()` builds:

- a **correlated** spectrum (selector rises monotonically with `abs_error`) →
  must return rho **exactly +1** and regret **exactly 0** (the selector-min is
  also the oracle);
- an **anti-correlated** spectrum (selector falls as `abs_error` rises) → must
  return rho **exactly −1**.

V4 asserts these to floating-point epsilon (`atol = 1e-12`). The notebook runs V4
*first*, so no real audit number is ever displayed before the engine is
validated.

### Gate V6 for selectors — the differential
The existing V6 differential strategy ("main package must agree with an
independent clean-room reference on ~500 randomized inputs") is extended to
selectors. For 500 random valid frames, `selectors.score_configs` must match
`refimpl.ref_selectors.score_configs` on both rho and `top1_regret` to `< 1e-6`.
The reference is authored by a **separate blind session** and copied in later, so
the test is *expected to error on import* until then — the import is deferred into
the test body so only that one test errors, leaving the rest of the V6 suite
green. This catches any subtle disagreement (tie convention, argmin tie-break,
percentile rule) between two independently-written implementations.

---

## 7. One-line mental model

> T6 asks *"would this truth-free criterion have chosen well?"* — measured by rank
> agreement (rho), the accuracy cost of its top pick (regret), and how often that
> pick was top-quartile — with uncertainty bootstrapped over **spectra**, the real
> unit of replication. T6b asks the dual question — *"if I trust the naive
> interval across the whole misspecified grid, how often does it actually contain
> the truth?"* V4 proves the arithmetic; the V6 differential proves two
> independent implementations agree.
