# Day-6 Quiz

A short self-check on the Day-6 analysis: the ranking rule, descriptive-vs-causal
decomposition, and what Q1b proves. Questions first; answers further down.

---

## Questions

**Q1 — The ranking rule.**
Within a regime, two configurations are compared: config A has the lower RMSE of
I_D/I_G error but an empirical 95% coverage of 0.80; config B has a higher RMSE but
coverage of 0.95 and a 0% failure rate. Under the pre-registered Q1 rule (coverage
floor 0.90, failure cap 0.05), which one ranks higher — and what happened to the
hostile suite in this study?

**Q2 — Descriptive vs causal.**
`grid.decompose` reports that the marginal mean |error| for `peak_set=DG` is ~0.21
while `DGDp` is ~1.15. May you conclude that "adding the D′ band *causes* a ~5×
increase in error"? Why or why not, and what is the most you are allowed to say?

**Q3 — What Q1b proves.**
The Q1b jackknife table (T9) came back empty this study. What attack is Q1b designed
to defend against, and what — if anything — does an *empty* T9 let you claim about
rank stability?

---
---

## Answers

**A1.**
**Config B ranks higher; config A is excluded entirely.** RMSE is only the *ordering*
metric — it ranks configs that have already passed the eligibility floors. Coverage
≥ 0.90 and failure ≤ 0.05 are *gates*: a config below the coverage floor is **dropped
from the ranking, not ranked last**. So A (coverage 0.80) is ineligible regardless of
its better RMSE, and B becomes the higher-ranked survivor. In this study that gate bit
*everything*: the maximum empirical coverage across all 288 (config × regime) cells
was **0.80**, so **no** configuration was rank-eligible in any SNR regime and the Q1
table (T5) is empty. The bootstrap intervals are statistical-only and undercover on
hostile, non-Lorentzian spectra where misspecification bias dominates.

**A2.**
**No.** `grid.decompose` is explicitly a **DESCRIPTIVE, non-causal** summary — not an
ANOVA and not a variance partition. The per-factor level means are *marginal*
summaries confounded by the factorial layout (the DG cells differ from the DGDp cells
in more than just the D′ band's presence), so they cannot be read as main effects or
causal contrasts. The most you may say is descriptive: *"in this grid, configurations
using the DG peak set had ~5× lower mean absolute error than D′-containing peak sets,"*
with no causal attribution.

**A3.**
Q1b defends against a **grid-dependence / fragility attack**: the worry that the
rank-1 "winner" is an artefact of which configuration families or which random suite
instances happened to be in the grid. It recomputes the ranking under leave-one-out
(drop each baseline / lineshape / peak set, and each instance) and reports, for the
recommended config, top-quartile retention, rank IQR, and a flip flag. An **empty T9
lets you claim *nothing* about rank stability** — it is **vacuous**, not reassuring.
Q1b can only assess a recommended configuration, and this study produced none (no
config cleared the coverage floor). The correct statement is: "there was no
rank-eligible configuration to test, so rank stability is undefined," **not** "the
ranking is stable."
