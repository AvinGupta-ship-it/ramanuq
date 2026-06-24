# Day 9 — Quiz: figures, number injection, and reproducible reporting

Three questions on the Day-9 concepts. Answers are in the separate section below;
try them before scrolling.

## Questions

**Q1 — Why recompute, and why a self-check?**
`report_data.json` could in principle be filled by copying the numbers out of
`protocol.md`. (a) Why does `reporting.py` instead *recompute* every cited number
from the parquet? (b) The module then runs a `self_check` against the
human-authored protocol/validation numbers and *refuses to write the file* if any
value disagrees beyond a rounding tolerance. What would it mean — and what is the
correct response — if that self-check ever failed?

**Q2 — Number injection and the schema-freeze constraint.**
(a) Which figures must read their cited numerals from `report_data.json` rather
than hard-coding them, and which data may be read directly from the parquet
instead? (b) `viz.py` holds palette names, nested report keys, and computed-column
names in named constants (e.g. `_PROTO_MDC = "protocol_mdc_idig"`) instead of
writing the strings as literal subscripts. What test enforces this, and what is it
actually protecting against?

**Q3 — Determinism and the honest empty/deferred states.**
(a) Name three concrete things `make_all_figures.py` does to make the PNG/PDF
output byte-identical across two runs, and why each matters. (b) F8 raises an
error when `data/digitized/` is empty and F9 shows "0 rank-eligible configs /
stability undefined". Why are these *honest* designs rather than failures to
finish the work?

---

## Answers

**A1.**
(a) The purpose of `report_data.json` is to be the *code's* record of the
results: a single artifact a reader (or the Day-10 report builder) can trust as
machine-generated from the frozen study. Copying numbers out of `protocol.md`
would only re-assert the human's transcription and could silently drift from what
the data actually say; recomputing from `tierB_grid_results.parquet` makes the
JSON an independent recomputation that *also happens to match* the authored
prose. (b) A self-check failure means the code's recomputation and the
human-authored numbers disagree — either the prose has a typo/stale value, or the
recompute logic is wrong, or the underlying data changed. That is a substantive
**finding**, not a nuisance: the correct response is to STOP, surface the exact
discrepancy, and let the human adjudicate. It is never correct to edit the
authored numbers to match, or to relax the tolerance to force a pass. Refusing to
write the file makes the failure loud instead of shipping inconsistent numbers.

**A2.**
(a) Any figure that *displays a cited result* must read it from
`report_data.json`: F6 (the protocol card), F7 (the MDC curves), and the
annotated values on F1 (coverage, floor, nominal), F4 (the coverage floor in the
title), F5 (T6b coverage, regret), and F9 (max coverage, floor). Figures may read
*raw arrays* directly from the parquet — F3's per-config abs_error and F4's
RMSE/coverage grids — because those are recomputations of the same frozen data,
not transcribed results. (b) `tests/test_grid.py::test_schema_freeze_downstream_uses_only_result_columns`
scans `selectors.py` and `viz.py` for string-literal subscripts and groupby keys
and asserts they are all frozen `RESULT_COLUMNS` (plus the robust output
columns). It protects the **schema freeze**: downstream code must reference the
study schema only through the single source of truth, so a renamed or invented
input column is caught at test time. Holding non-schema names (palette, report
keys, computed columns) in variables keeps them out of the scan while still
making the dependency explicit — the same pattern `selectors.py` already uses for
its audit-output columns.

**A3.**
(a) Three of: it forces the **Agg** backend so rendering does not depend on a
display/GUI; it sets **one fixed `SEED`** (and reseeds before each figure) so the
small positional jitter in F3 is identical every run; it pins
**`SOURCE_DATE_EPOCH`** so the PDF backend writes a fixed creation date instead of
"now"; and it **strips figure metadata** (no Software/timestamp tags in the PNG).
Each removes a source of run-to-run byte differences, so the byte-identity check
(two renders, equal SHA-256) is meaningful. (b) Both refuse to invent or
overstate. F8 has no published spectrum to reproduce yet, so fabricating a curve
would be inventing data for Gate V5; raising a clear error keeps the gate honestly
`pending`. F9's ranking is genuinely empty (no config reaches the 0.90 coverage
floor), so labeling stability "stable" would be a false claim about a quantity
that is undefined; showing the empty state with the reason states exactly what the
data support. Honesty about a null/deferred result is the finding, not a gap.
