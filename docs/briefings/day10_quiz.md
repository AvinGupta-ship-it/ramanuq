# Day 10 Quiz — Report assembly, number injection, Gate V5

Closed-book. Answer the three questions, then check the separate Answers section.

## Questions

**Q1.** In the Day-10 pipeline, where do the numbers in `docs/report_draft.md`
come from, and what guarantees that a `{{placeholder}}` can never silently appear
in the finished draft? Name the three files involved and the role of each.

**Q2.** The template forbids hard-coded result numerals but still allows some
bare digits. Give two categories of bare digit that are allowed (not treated as
results), and explain why a per-regime MDC value like 0.529 is *not* in those
categories.

**Q3.** Gate V5 reproduces the Cançado-2011 L_D = 7 nm spectrum. (a) Why is it run
in HEIGHT mode rather than AREA mode? (b) The measured value was 1.5227 against a
target of 1.6 — state the pass window and the verdict. (c) Why does the choice of
the linear baseline / Lorentzian lineshape config not count as "tuning the gate
to pass"?

---
---

## Answers

**A1.** Three files: (1) `docs/report_data.json` holds every number, recomputed
from the frozen study parquet (the single source of truth). (2)
`docs/report_template.md` holds the prose skeleton with `{{placeholder}}` tokens
and a PLACEHOLDER MAP binding each placeholder to a JSON path + display format.
(3) `scripts/build_report.py` parses the MAP, resolves each path from the JSON,
substitutes, and writes `docs/report_draft.md`. The guarantee is **fail-loud
resolution**: if any used placeholder lacks a MAP entry or its JSON path does not
resolve, the build aborts and lists the offenders; it also re-scans the output and
errors if any placeholder survived substitution. Numbers flow JSON → draft only.

**A2.** Allowed bare digits include any two of: reference years, DOIs,
section/figure/table numbers, equation constants inside the Methods model
definitions, and SNR regime labels (15/50/200). An MDC value like 0.529 is a
**reported result** — a quantity computed from the study data — so it must be a
`{{key}}` bound to `mdc.per_regime.SNR15.protocol_mdc_idig`, not typed into the
prose. (The allowed categories are fixed identifiers/labels/constants, not
study-derived measurements.)

**A3.** (a) The Cançado 2011 paper explicitly defines I_D/I_G as the peak-height
(intensity) ratio, distinct from the integrated-area ratio A_D/A_G; reproducing
the *published* number requires matching its definition, so V5 runs in HEIGHT
mode. (b) Window = target ± 10% = [1.44, 1.76]; 1.5227 falls inside, so the
verdict is **PASS**. (c) The config (height ratio + D,G peaks from the paper's
stated method; textbook graphene Lorentzian; simplest documented linear baseline)
was fixed *a priori* from the paper and standard practice, before reading the
outcome — not selected from among configs by which one lands nearest 1.6 — and the
pre-registered ±10% tolerance was left unchanged.
