# Day 10 Briefing — Report assembly: number injection, section→finding mapping, Gate V5

**Audience:** the author (Avin). **Time:** ~15 minutes. **Scope:** what Day-10
plumbing does and does not do, so you can write the prose with confidence that
every number under it is traceable.

---

## 1. Number injection (≈5 min)

The Day-10 deliverable is a *report that cannot drift from the data*. The
mechanism is a strict separation between three files:

- **`docs/report_data.json`** — the single source of truth for numbers. Every
  value here was recomputed from the frozen study parquet by
  `ramanuq.reporting` (Day 9). Nothing is hand-typed.
- **`docs/report_template.md`** — the prose skeleton. It contains **no result
  numerals**. Wherever a number belongs, there is a `{{placeholder}}`. At the top
  of the file, inside an HTML comment, a **PLACEHOLDER MAP** lists each
  placeholder and the exact JSON path it binds to, e.g.

  ```
  protocol_mdc_snr50 -> mdc.per_regime.SNR50.protocol_mdc_idig | f3
  ```

  The trailing token (`f3`, `sci`, `int`, `raw`, `sgn3`, …) is a *display
  format only* — it never changes the stored value.
- **`scripts/build_report.py`** — the injector. It parses the PLACEHOLDER MAP,
  resolves each path out of `report_data.json`, formats it, substitutes it into
  the body, and writes **`docs/report_draft.md`** (and `report.pdf` when pandoc
  is installed).

Two safety properties matter:

1. **Fail-loud.** If any `{{key}}` in the body has no MAP entry, or a mapped path
   does not resolve in the JSON, the build aborts and lists the offenders. A
   placeholder can never silently survive into the draft.
2. **One-way flow.** Numbers flow JSON → draft, never the reverse. To change a
   number in the report you must change the *data* (and the recompute that
   produced it), not the prose. This is what makes the report auditable.

Allowed bare digits in the template (not results, so not placeholders): reference
years, DOIs, section/figure/table numbers, the equation constants in the Methods
model definitions, and the SNR regime **labels** (15 / 50 / 200).

**What you do:** write prose only in the empty `<!-- AUTHOR: … -->` slots, and
paste your Day-7 Q2 verdict verbatim into its marked slot. Then run
`python3 scripts/build_report.py` and read `report_draft.md`.

## 2. Section → finding mapping (≈5 min)

The skeleton's sections map to the project's findings as follows:

| Section | Finding it carries | Key JSON it draws from |
| --- | --- | --- |
| 3 Instrument validation | V3 hostile-bias pass; V5 published-spectrum pass | `gate_v3.*`, `gates.V5.*` |
| 4 Q1 / Q1b | **Headline: the coverage-gated ranking is empty** (0 rank-eligible; max coverage 0.80 < 0.90 floor); Q1b vacuous; T6b undercoverage | `t5_ranking.*`, `t6b_coverage.*`, `q1b_stability.*` |
| 5 Q2 | Selectors don't track accuracy (ρ≈0, full regret > within regret); your verbatim verdict | `q2_audit.by_stratum.*` |
| 6 Q3 | MDC: protocol detects a smaller change than naive, per regime, in I_D/I_G and Δn_D | `mdc.per_regime.*` |

The interpretive sections (Abstract, Introduction, the Q1/Q1b, Q2, and Q3
interpretation blocks, Limitations, the disclosure checklist, and the two README
finding sentences) are deliberately **empty**. The plumbing supplies the
numbers; you supply the meaning. The honest framing already baked into the data —
empty ranking, undercoverage, vacuous Q1b — should anchor your prose; do not let
the prose imply a config "passed" coverage when none did.

## 3. Gate V5 (≈5 min)

V5 is the only gate that touches the outside world: it asks whether the pipeline
reproduces a **published** I_D/I_G within ±10% on a digitized spectrum.

- **Spectrum:** Cançado et al. 2011 (*Nano Lett.* **11**, 3190; DOI
  10.1021/nl201432g), the L_D = 7 nm graphene trace, digitized in
  `data/digitized/` (twice, for verification).
- **Mode:** HEIGHT. The paper explicitly defines I_D/I_G as the peak-**height**
  (intensity) ratio, distinct from the area ratio A_D/A_G — so V5 runs the
  pipeline in height mode and reads `compute_metrics(..., "height").id_ig`.
- **Config choice:** fixed *a priori* from the paper's stated method
  (height ratio, D & G peaks) plus the textbook first-order graphene Lorentzian
  lineshape and the simplest documented baseline (linear). The paper specifies no
  baseline/lineshape recipe, so this is a documented demonstration choice — **not
  tuned to hit the target.**
- **Result:** measured I_D/I_G = **1.5227**, target **1.6**, window
  **[1.44, 1.76]** → **PASS**. Written into `gates.V5` in `report_data.json`,
  replacing the `pending_day10` placeholder.

Caveat to keep in mind for the Limitations prose: the digitized intensity axis is
arbitrary-units and baseline-relative; V5 is a *demonstration* of plausibility on
one published spectrum, not a calibration claim. The ±10% tolerance is
pre-registered and was not relaxed.

---

**Run it yourself:** `python3 scripts/build_report.py`, then open
`docs/report_draft.md`. Every numeral you see there is one `{{key}}` away from a
line in `docs/report_data.json`.
