# Day 11 — Quiz

Answer from today's release-prep concepts, then check the separate answers
section below.

## Questions

**Q1 (reproducibility / byte-identity).** A colleague rebuilds `report.pdf` from
the exact same `report_draft.md` one minute after you did, runs `diff` on the two
PDFs, and reports they are *not* identical — then concludes your pipeline is not
reproducible. What is almost certainly the real cause, and what is the right way
to check reproducibility of the report?

**Q2 (tagging / semantic versioning).** You are about to release `v0.1.0`. (a)
What is the difference between a git tag and a branch, and why does a citation/DOI
point at a tag? (b) The only outstanding work is the two deferred cosmetic
figure-label fixes. Under semantic versioning, what version number should the
release that contains those fixes carry, and why not `0.2.0` or `1.0.0`?

**Q3 (human approval + AI disclosure).** (a) Name two acts in the release process
that an automated agent should *not* perform on its own, and say in one phrase why.
(b) The AI-usage disclosure says implementation was delegated to AI but all
scientific decisions are the author's. What single mechanism in this repository
makes "the AI didn't silently get a science-critical formula wrong" a *checkable*
claim rather than a promise?

---

## Answers

**A1.** The cause is the PDF's embedded `/CreationDate` (and `/ModDate`) metadata
timestamp: two PDFs typeset from byte-identical Markdown at different wall-clock
times differ in those bytes. This is not a reproducibility failure of the
*science*. The right check is to diff the **inputs** that feed the PDF —
`report_draft.md`, `docs/report_data.json`, and the figure PNGs (which *are*
pinned to byte-identity via fixed seed, `SOURCE_DATE_EPOCH`, and stripped
metadata) — and to compare the PDF by its extracted text or a content hash, never
by raw bytes.

**A2.** (a) A *branch* is a moving pointer that advances with new commits; a *tag*
is an immutable label naming one specific commit forever. A DOI/citation must
resolve to fixed content, so it points at a tag, not a branch. (b) `v0.1.1` — a
PATCH bump. The fixes are cosmetic and backward-compatible (no new features, no
API change), so MINOR (`0.2.0`) is wrong; and the project is still pre-1.0 and
not declaring API stability, so MAJOR (`1.0.0`) is wrong.

**A3.** (a) Creating the git tag and publishing the GitHub release / minting the
DOI — because they are irreversible, outward-facing acts that permanently bind a
person's name and record to the artifact, i.e. a human accountability decision.
(Running `repro.sh` from a fresh clone is likewise the human's verification step.)
(b) Gate V6: every science-critical formula is re-implemented by a *separate,
independent (clean-room)* agent and asserted equal to the production code on
randomized inputs in continuous integration — so an undetected formula error
would have to occur identically in two independent implementations.
