# Day 11 — Science Briefing: What it means to *release* a validated pipeline

Today is not science. The study is frozen — every number, gate, and
pre-registration is locked. Day 11 is about turning a frozen repository into a
citable, reproducible *artifact* that a stranger can trust. Four ideas carry the
day.

## 1. Reproducibility and byte-identity

There are two strengths of "reproducible," and they are not the same thing.

- **Scientific reproducibility:** a fresh clone, run end-to-end, yields the same
  conclusions. Our figures and `report_data.json` are recomputed from the
  committed study parquet (`tierB_grid_results.parquet`), so anyone can rebuild
  the reported numbers without re-running the ~7-hour crossed study.
- **Byte-identity:** the regenerated file is bit-for-bit identical to the
  committed one. This is stronger and more fragile. It requires pinning every
  source of nondeterminism — a fixed `SEED`, `SOURCE_DATE_EPOCH`, the `Agg`
  matplotlib backend, stripped image metadata. Our `make_all_figures.py` checks
  that the 16 figure files are byte-identical across two consecutive runs.

The classic byte-identity trap is the **PDF creation timestamp**. A PDF embeds
`/CreationDate` and `/ModDate` in its metadata; our `report.pdf` carries
`D:20260625...`. Two PDFs built from identical Markdown one second apart differ
in bytes. *Lesson:* diff the **inputs** (Markdown draft, `report_data.json`,
figure PNGs) for byte-identity; treat the PDF as a typeset *view*, compared by
extracted text or content hash, never raw bytes.

## 2. Tagging and semantic versioning

A **git tag** is an immutable, human-meaningful name for one commit — the thing
a DOI and a citation point at. **Semantic versioning** (`MAJOR.MINOR.PATCH`)
encodes intent: `0.1.0` says "first public, pre-1.0, API may still move." A
bump to `0.1.1` would be a backward-compatible patch (e.g. the deferred cosmetic
figure-label fixes); `0.2.0` adds features; `1.0.0` declares stability. We pin
`version: 0.1.0` in `CITATION.cff` and name the release `v0.1.0` so the tag, the
citation metadata, and the release notes all agree on one identity.

## 3. Release is a human approval act

Everything up to here can be automated; the **release itself cannot be**.
Creating the tag, publishing the GitHub release, and minting the DOI are
irreversible, outward-facing acts that bind your name to a permanent record.
That is a human decision, not an agent's. So today's agent work stops at
*drafting* — release notes with author-sentence placeholders, a `CITATION.cff`
with `doi` commented out, a Definition-of-Done pre-check that *lists* gaps rather
than papering over them. The human reads the pre-check, runs the fresh-clone
reproduction by hand, then pulls the trigger. A reproduction script you *inspect*
is evidence; a tag you *push* is a commitment.

## 4. The AI-disclosure claim

The disclosure is a precise, falsifiable claim, not a hedge. Its structure:
**implementation was delegated; judgment was not.** AI agents wrote code, tests,
figures, and docs to specifications, acceptance tests, and gates the human
designed — and every science-critical formula was *independently* re-implemented
by a separate clean-room agent and asserted equal in CI (Gate V6), so no single
agent's mistake can silently define a result. Meanwhile every *scientific*
decision — the questions, the literature-sourced calibrations, the ground-truth
definitions, the tolerances, the dated Q2 prediction, the interpretation — is the
human's, timestamped *before* the results. The per-session `ai_usage_log.md` is
the audit trail that makes the claim checkable rather than merely asserted.
