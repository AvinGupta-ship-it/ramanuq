"""Build the final report by injecting recomputed numbers into the template.

Day-10 role (manual prompt P11 / §9.10): this is PLUMBING. It does not author
prose and it hard-codes no result numbers. It

  1. loads ``docs/report_data.json`` (the recomputed numbers),
  2. parses the PLACEHOLDER MAP block in ``docs/report_template.md``
     (``name -> json.path | fmt`` lines), which is the single source of truth for
     where every ``{{key}}`` comes from,
  3. resolves and formats every ``{{key}}`` from its documented JSON path,
  4. writes the substituted Markdown to ``docs/report_draft.md``, and
  5. renders ``docs/report.pdf`` via pandoc + xhtml2pdf, a route that needs no
     system LaTeX distribution and no native libraries (best-effort).

If any ``{{key}}`` in the template body has no mapping entry, or any mapped JSON
path does not resolve, the script FAILS LOUDLY listing the offenders rather than
leaving a placeholder behind.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATE_PATH = os.path.join(_REPO_ROOT, "docs", "report_template.md")
REPORT_DATA_PATH = os.path.join(_REPO_ROOT, "docs", "report_data.json")
DRAFT_PATH = os.path.join(_REPO_ROOT, "docs", "report_draft.md")
PDF_PATH = os.path.join(_REPO_ROOT, "docs", "report.pdf")

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")
_MAP_LINE_RE = re.compile(
    r"^\s*([A-Za-z0-9_]+)\s*->\s*([A-Za-z0-9_.]+)\s*(?:\|\s*([A-Za-z0-9]+)\s*)?$"
)


def _format_value(value, fmt):
    """Format ``value`` per the documented ``fmt`` token (display only)."""
    if fmt in (None, "raw"):
        return str(value)
    if fmt == "int":
        return str(int(value))
    if fmt == "f1":
        return f"{float(value):.1f}"
    if fmt == "f2":
        return f"{float(value):.2f}"
    if fmt == "f3":
        return f"{float(value):.3f}"
    if fmt == "f4":
        return f"{float(value):.4f}"
    if fmt == "f5":
        return f"{float(value):.5f}"
    if fmt == "sgn3":
        return f"{float(value):+.3f}"
    if fmt == "sgn5":
        return f"{float(value):+.5f}"
    if fmt == "sci":
        return f"{float(value):.3e}"
    raise ValueError(f"unknown format token {fmt!r}")


def parse_placeholder_map(template_text):
    """Extract the ``name -> json.path | fmt`` mapping from the template block."""
    start = template_text.find("PLACEHOLDER-MAP-START")
    end = template_text.find("PLACEHOLDER-MAP-END")
    if start == -1 or end == -1 or end < start:
        raise ValueError(
            "report_template.md is missing a PLACEHOLDER-MAP-START/END block"
        )
    block = template_text[start + len("PLACEHOLDER-MAP-START"):end]
    mapping = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = _MAP_LINE_RE.match(line)
        if not m:
            raise ValueError(f"unparseable PLACEHOLDER MAP line: {raw_line!r}")
        name, path, fmt = m.group(1), m.group(2), m.group(3)
        mapping[name] = (path, fmt)
    if not mapping:
        raise ValueError("PLACEHOLDER MAP block is empty")
    return mapping


def resolve_path(data, path):
    """Resolve a dotted JSON path; numeric components index into lists.

    Returns ``(found, value)``; ``found`` is False when any component is absent.
    """
    node = data
    for part in path.split("."):
        if isinstance(node, list):
            if not part.isdigit() or int(part) >= len(node):
                return (False, None)
            node = node[int(part)]
        elif isinstance(node, dict):
            if part not in node:
                return (False, None)
            node = node[part]
        else:
            return (False, None)
    return (True, node)


def build(template_path=TEMPLATE_PATH, data_path=REPORT_DATA_PATH,
          draft_path=DRAFT_PATH, pdf_path=PDF_PATH):
    """Resolve placeholders, write the draft, and render the PDF (best-effort)."""
    with open(template_path) as fh:
        template = fh.read()
    with open(data_path) as fh:
        data = json.load(fh)

    mapping = parse_placeholder_map(template)

    # Strip the leading HTML comment header (it carries the map + author notes)
    # so it does not appear in the rendered report.
    body = template
    if body.lstrip().startswith("<!--"):
        close = body.find("-->")
        if close != -1:
            body = body[close + len("-->"):].lstrip("\n")

    used = set(_PLACEHOLDER_RE.findall(body))

    # 1. Every placeholder used in the body must have a mapping entry.
    unmapped = sorted(k for k in used if k not in mapping)

    # 2. Every used+mapped placeholder must resolve to a JSON value.
    unresolved = []
    resolved = {}
    for key in sorted(used):
        if key in unmapped:
            continue
        path, fmt = mapping[key]
        found, value = resolve_path(data, path)
        if not found:
            unresolved.append(f"{key} -> {path}")
            continue
        resolved[key] = _format_value(value, fmt)

    if unmapped or unresolved:
        msg = ["build_report FAILED: unresolved placeholders."]
        if unmapped:
            msg.append("  No PLACEHOLDER MAP entry for: " + ", ".join(unmapped))
        if unresolved:
            msg.append("  JSON path did not resolve for:")
            msg.extend(f"    - {u}" for u in unresolved)
        raise SystemExit("\n".join(msg))

    n_subs = 0

    def _sub(match):
        nonlocal n_subs
        n_subs += 1
        return resolved[match.group(1)]

    out = _PLACEHOLDER_RE.sub(_sub, body)

    # Defensive: no placeholder may survive substitution.
    leftover = sorted(set(_PLACEHOLDER_RE.findall(out)))
    if leftover:
        raise SystemExit(
            "build_report FAILED: placeholders survived substitution: "
            + ", ".join(leftover)
        )

    os.makedirs(os.path.dirname(draft_path), exist_ok=True)
    with open(draft_path, "w") as fh:
        fh.write(out)

    print(f"Resolved {len(resolved)} unique placeholders "
          f"({n_subs} substitutions) -> {os.path.relpath(draft_path, _REPO_ROOT)}")

    # 5. Render the PDF without a system LaTeX distribution: pandoc converts the
    #    Markdown draft to an HTML fragment, then xhtml2pdf (pure Python, no
    #    native libraries) renders that HTML to PDF. Best-effort; the Markdown
    #    draft is the primary artifact and is already written above.
    rel_pdf = os.path.relpath(pdf_path, _REPO_ROOT)
    if shutil.which("pandoc") is None:
        print(f"NOTE: pandoc not found on PATH; skipped PDF render ({rel_pdf} "
              "not written). Install pandoc to produce the PDF.")
        return resolved
    try:
        from xhtml2pdf import pisa
    except ImportError:
        print(f"NOTE: xhtml2pdf not installed in this environment; skipped PDF "
              f"render ({rel_pdf} not written). "
              "Install it with: python3 -m pip install xhtml2pdf")
        return resolved
    try:
        fragment = subprocess.run(
            ["pandoc", draft_path, "-t", "html"], check=True,
            capture_output=True, text=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        print("WARNING: pandoc failed to convert the draft to HTML (the Markdown "
              f"draft was still written). pandoc stderr:\n{exc.stderr}",
              file=sys.stderr)
        return resolved
    # Default Helvetica lacks glyphs for cm-1, superscripts, chi-squared, rho,
    # arrows, +/-, etc. Reuse the DejaVu Sans TTFs bundled with matplotlib (a
    # dependency already on disk -- no new pip install) so every Unicode glyph
    # renders. xhtml2pdf registers and embeds fonts declared via @font-face, so
    # the CSS below both registers the family and points the body at it.
    font_css = ""
    try:
        import matplotlib
    except ImportError:
        matplotlib = None
    if matplotlib is not None:
        ttf_dir = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
        # (css family, descriptor, filename)
        faces = [
            ("DejaVuSans", "", "DejaVuSans.ttf"),
            ("DejaVuSans", "font-weight: bold;", "DejaVuSans-Bold.ttf"),
            ("DejaVuSans", "font-style: italic;", "DejaVuSans-Oblique.ttf"),
            ("DejaVuSans", "font-weight: bold; font-style: italic;",
             "DejaVuSans-BoldOblique.ttf"),
            ("DejaVuSansMono", "", "DejaVuSansMono.ttf"),
        ]
        regular = os.path.join(ttf_dir, "DejaVuSans.ttf")
        if os.path.exists(regular):
            rules = []
            for family, descriptor, filename in faces:
                path = os.path.join(ttf_dir, filename)
                if not os.path.exists(path):
                    continue
                src = path.replace("\\", "/")
                rules.append(
                    f'@font-face {{ font-family: "{family}"; {descriptor} '
                    f'src: url("{src}"); }}'
                )
            rules.append('body { font-family: "DejaVuSans"; }')
            rules.append('code, pre, tt { font-family: "DejaVuSansMono"; }')
            font_css = "<style>" + " ".join(rules) + "</style>"
        else:
            print(f"NOTE: DejaVuSans.ttf not found at {regular}; PDF will use the "
                  "default font and may show missing-glyph boxes for Unicode "
                  "characters.", file=sys.stderr)
    html = ('<html><head><meta charset="utf-8">' + font_css + "</head><body>"
            + fragment + "</body></html>")
    with open(pdf_path, "wb") as fh:
        result = pisa.CreatePDF(html, dest=fh, encoding="utf-8")
    if result.err:
        print(f"WARNING: xhtml2pdf reported {result.err} error(s) while rendering "
              f"{rel_pdf} (the Markdown draft was still written).",
              file=sys.stderr)
    else:
        print(f"Rendered {rel_pdf} via pandoc + xhtml2pdf")
    return resolved


if __name__ == "__main__":
    build()
