# Day 9 — Science briefing: the nine figures, number injection, and reproducible reporting

Day 9 turns measured results into a fixed visual record. No new science is
computed: the Day-6 study is frozen in `data/synthetic/results/tierB_grid_results.parquet`,
and the MDC/Q2/T6b layers were settled on Days 7-8. Day 9 builds the *reporting
plumbing* — one JSON of recomputed numbers, nine figures that read from it, a
deterministic build, and a QA harness — so the eventual report cites the code's
numbers, not a human transcription.

## 1. The nine figures and the finding each carries

Each figure is one claim made visible. The point is not decoration; it is that a
reader can see the finding without re-running anything.

- **F1 — Recovery parity + coverage.** Recovered I_D/I_G against truth for the
  protocol configs, beside the empirical 95% coverage per regime with the 0.95
  nominal line and the 0.90 rank floor. *Finding:* points sit near the truth but
  the intervals do not reach the floor — accuracy without honest coverage.
- **F2 — Hostile-fit anatomy.** One Tier-B spectrum in baseline-subtracted
  space: the true out-of-family bands (composite-Lorentzian D, EMG G, mixed-Voigt
  satellites) dashed, and the single-lineshape fit solid. *Finding:* the fit
  cannot represent the true band shapes — this is the misspecification (FM4) that
  makes intervals undercover.
- **F3 — Per-configuration accuracy strip.** All 96 configs ordered by mean
  |error|, colored by it, with the naive and protocol configs flagged.
  *Finding:* DG configs cluster at low error; D′-containing peak sets are ~5×
  worse. Peak set dominates accuracy.
- **F4 — RMSE / coverage maps.** baseline × lineshape heatmaps for DG/area, per
  SNR, RMSE on top and coverage below. *Finding:* RMSE varies modestly across
  baselines/lineshapes; coverage is low *everywhere* (max ~0.53) — no cell
  reaches 0.90.
- **F5 — Selector + regret + misspecification coverage.** Raw fit-quality vs
  accuracy scatter, top-1 regret per selector/stratum, and T6b coverage per
  regime. *Finding:* selectors barely track accuracy (small ρ, real regret), and
  pooled coverage is only 18-28%.
- **F6 — Protocol card.** The recommendation table, numbers identical to
  `protocol.md` but sourced from `report_data.json`. *Finding:* the documented
  per-regime pick with its bias/RMSE/coverage/failure/MDC and the honest
  "stability undefined" cell.
- **F7 — MDC curves.** Minimum detectable change vs SNR, protocol vs naive, in
  I_D/I_G and Δn_D (with the published-constant uncertainty band). *Finding:* the
  protocol pipeline resolves a smaller change than the naive one in every regime.
- **F8 — Demonstration spectra (deferred).** Reproduction of digitized published
  spectra for Gate V5. Today `data/digitized/` is empty, so the figure code
  *raises a clear error* rather than inventing data; it joins the green set after
  the human digitizes a spectrum.
- **F9 — Rank stability (empty state).** Honestly shows 0 rank-eligible configs
  per regime and that max coverage 0.80 < 0.90 floor, so Q1b stability is
  *undefined* — not silently reported as "stable".

## 2. `report_data.json` and number injection

The discipline is: **one module recomputes every cited number, one file holds
them, and figures read only from that file.** `reporting.py` reads the parquet
and the frozen calibrations, recomputes the gates, the empty ranking, Gate V3,
the Q2 audit, T6b, and the MDC block, and writes `docs/report_data.json`. It does
*not* copy numbers from `protocol.md`; the whole point is that the JSON carries
the *code's* numbers.

A built-in **self-check** then compares those recomputed numbers to the values
the human authored in `protocol.md`/`validation_plan.md` (protocol MDC, naive
MDC, bias, RMSE, coverage, T6b, Gate V3 best). If anything disagrees beyond a
rounding tolerance, `write_report_data` refuses to write and surfaces the
discrepancy — a disagreement is a *finding to adjudicate*, never something the
code silently "fixes".

Figures then **inject** numbers by reading `report_data.json` — F6's table cells,
F7's curves, and every annotated value on F1/F4/F5/F9 come from the JSON, never a
literal typed into `viz.py`. Raw arrays (per-config abs_error, RMSE/coverage
grids) may be read directly from the parquet, because those are recomputations of
the same frozen data, not transcribed results.

## 3. Deterministic, byte-identical figures

A figure that changes byte-for-byte between runs cannot be trusted as a record.
`make_all_figures.py` removes every source of nondeterminism: the **Agg** backend
(no display), one fixed **SEED** for the small jitter in F3, **`SOURCE_DATE_EPOCH`**
pinned so the PDF backend writes a fixed creation date, and figure metadata
stripped (no "Software"/timestamp tags). The driver renders twice and verifies
all 16 PNG/PDF files have identical SHA-256 — a self-proving determinism check.

## 4. The figure-QA harness

`figure_qa.py` is the gate that keeps the figures publishable. Per figure it
asserts: the on-disk PNG and PDF exist and exceed a size floor (catching empty or
truncated renders); axis labels are present where the figure has data axes; an
explanatory element appropriate to the figure kind is present (a legend, or a
colorbar for the maps/strip, or the table for F6, or the annotation for F9); and
two in-memory renders are byte-identical. F8 is reported DEFERRED until digitized
data exists.

## 5. Demonstration spectra, method-stating, and Gate V5

Gate V5 — reproducing at least one digitized *published* spectrum within ±10% —
is the project's contact with the real world. Two principles govern it on Day 9:
**method-stating** (a figure declares which config produced it, e.g. F2's legend
names the fit pipeline, so the reader knows the method, not just the picture) and
**no fabrication** (F8 reads `data/digitized/` and raises if empty rather than
inventing a curve). The human selects and digitizes the demonstration spectra;
the implementer never picks them. V5 is therefore marked `pending_day10` in
`report_data.json`, and F8 is the one figure deferred today.
