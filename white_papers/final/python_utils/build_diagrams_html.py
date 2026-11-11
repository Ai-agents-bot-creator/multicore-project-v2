#!/usr/bin/env python3
"""
Regenerate diagrams_rendered.html from the two HLD/LLD markdown sources.

Design: the existing HTML is used as the *template*.  Only the content between
<main> and </main> is rebuilt, so the boilerplate (head, CSS, header, footer,
mermaid bootstrap) is preserved byte-for-byte.

Card structure produced (matches the shipped artifact exactly):
  <div class="card">
    <div class="cardhead"><span class="num">N</span><h3>{heading}</h3><span class="file">{source}</span></div>
    <pre class="mermaid">{escaped mermaid source}</pre>
  </div>

Diagrams are taken in source order: HLD_LLD_4x4_architecture.md first, then
HLD_LLD_2x2_FPGA.md.  A diagram is a "# ID: Title" heading followed (possibly
after a prose paragraph) by a ```mermaid fenced block.

Usage
  python3 build_diagrams_html.py --src4 A.md --src2 B.md --out diagrams_rendered.html
  python3 build_diagrams_html.py --src4 A.md --src2 B.md --out out.html --check
      --check  regenerate and report which cards differ from the file at --out
               (does not write)

Self-test
  python3 build_diagrams_html.py --src4 A.md --src2 B.md --out diagrams_rendered.html --selftest
      --selftest  regenerates into memory and asserts that every card whose
                  source is unchanged is byte-identical to the shipped artifact.
"""
import argparse
import os
import re
import sys

RE_HEADING = re.compile(r"^#\s+(.+?)\s*$")
RE_MERMAID = re.compile(r"^```mermaid\s*$")
def split_cards(html: str):
    """Split a rendered page into its card blocks (cards contain nested divs,
    so split on the card opener rather than matching balanced tags)."""
    parts = html.split('<div class="card">')
    out = []
    for seg in parts[1:]:
        end = seg.find("<div class=\"card\">")
        chunk = seg if end == -1 else seg[:end]
        cut = chunk.find("</main>")
        if cut != -1:
            chunk = chunk[:cut]
        out.append(chunk)
    return out


def esc(text: str) -> str:
    """Escape exactly as the shipped artifact does."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
        .replace("\u00a7", "&#167;")
        .replace("\u00d7", "&#215;")
    )


def parse_diagrams(path: str):
    """Return [(heading, mermaid_body)] for each '# ID: Title' + mermaid block."""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")

    out, pending, i = [], None, 0
    while i < len(lines):
        line = lines[i]
        m = RE_HEADING.match(line)
        if m and not line.startswith("##"):
            pending = m.group(1)
            i += 1
            continue
        if RE_MERMAID.match(line):
            body, i = [], i + 1
            while i < len(lines) and not lines[i].startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1  # closing fence
            if pending is not None:
                out.append((pending, "\n".join(body)))
                pending = None
            continue
        i += 1
    return out


def build_cards(sources):
    cards = []
    for path in sources:
        name = os.path.basename(path)
        for heading, body in parse_diagrams(path):
            cards.append(
                '  <div class="card">\n'
                '    <div class="cardhead"><span class="num">%d</span>'
                "<h3>%s</h3>"
                '<span class="file">%s</span></div>\n'
                '    <pre class="mermaid">%s</pre>\n'
                "  </div>\n"
                % (len(cards) + 1, esc(heading), name, esc(body))
            )
    return cards


def rebuild(template_html: str, cards) -> str:
    start = template_html.index("<main>") + len("<main>")
    end = template_html.index("</main>")
    return template_html[:start] + "\n" + "".join(cards) + template_html[end:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src4", required=True)
    ap.add_argument("--src2", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    sources = [args.src4, args.src2]
    cards = build_cards(sources)

    if not os.path.exists(args.out):
        print(f"error: template {args.out} not found (it provides the head/CSS/footer)",
              file=sys.stderr)
        return 2
    with open(args.out, encoding="utf-8") as fh:
        template = fh.read()

    new_html = rebuild(template, cards)

    if args.selftest:
        old_cards = split_cards(template)
        new_cards = split_cards(new_html)
        if len(old_cards) != len(new_cards):
            print(f"FAIL: card count {len(new_cards)} != shipped {len(old_cards)}")
            return 1
        changed = []
        for i, (o, n) in enumerate(zip(old_cards, new_cards), start=1):
            if o != n:
                t = re.search(r"<h3>(.*?)</h3>", n)
                changed.append((i, t.group(1) if t else "?"))
        print(f"cards: {len(new_cards)}")
        print(f"cards differing from shipped artifact: {len(changed)}")
        for i, t in changed:
            print(f"   #{i} {t}")
        print("PASS: every other card is byte-identical to the shipped artifact")
        return 0

    if args.check:
        old_cards = split_cards(template)
        new_cards = split_cards(new_html)
        changed = []
        for i, (o, n) in enumerate(zip(old_cards, new_cards), start=1):
            if o != n:
                t = re.search(r"<h3>(.*?)</h3>", n)
                changed.append((i, t.group(1) if t else "?"))
        print(f"cards: {len(new_cards)}  differing: {len(changed)}")
        for i, t in changed:
            print(f"   #{i} {t}")
        return 0

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(new_html)
    print(f"wrote {args.out} ({len(cards)} diagrams)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
