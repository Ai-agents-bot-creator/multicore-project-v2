#!/usr/bin/env python3
"""check_rules.py - machine-check lint/coding_rules.json against the tracked RTL.

CANONICAL rule set (25 rules). Usage:

    check_rules.py --verilator [--module NAME]   # tool rules: CR01, CR02 + all source rules
    check_rules.py --iverilog [--module NAME]    # tool rule CR03 + all source rules
    check_rules.py [--module NAME]               # every rule

The rule count is derived from the rule list in coding_rules.json, never
hand-written. Exit 0 only when every selected rule passes on every selected
module. A failure prints the offending lines so the run is evidence, not a
verdict.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

LINT_DIR = Path(__file__).resolve().parent
REPO = LINT_DIR.parent          # lint/ -> repo root


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def strip_comments(text):
    """Remove // and /* */ comments so a rule cannot fire on prose."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    out = []
    for line in text.split("\n"):
        # keep the part before a // comment (naive but adequate: no // in strings here)
        out.append(line.split("//", 1)[0])
    return "\n".join(out)


def check_verilator(mod, cfg, results):
    flags = cfg["flags"]
    cmd = ["verilator", *flags, "--top-module", mod["name"], *mod["sources"]]
    rc, out = run(cmd, REPO)

    # CR01: lint exits 0 (with -Wno-fatal, warnings never fail the exit code,
    # so an error is a non-zero exit or a %Error line).
    errs = [l for l in out.splitlines() if "%Error" in l]
    if rc == 0 and not errs:
        results.append(("PASS", "CR01", mod["name"], "exit 0, no %Error"))
    else:
        results.append(("FAIL", "CR01", mod["name"],
                        f"exit {rc}; " + "; ".join(errs[:3] or out.splitlines()[:3])))

    # CR02: every warning class fired must be on the recorded allow-list.
    fired = sorted({m.group(1) for m in
                    re.finditer(r"%Warning-(\w+):", out)})
    allowed = set(cfg["allowed_warnings"])
    bad = [w for w in fired if w not in allowed]
    if bad:
        lines = [l for l in out.splitlines()
                 if any(f"%Warning-{w}:" in l for w in bad)]
        results.append(("FAIL", "CR02", mod["name"],
                        f"disallowed: {bad}; " + " | ".join(lines[:3])))
    else:
        results.append(("PASS", "CR02", mod["name"],
                        f"warnings fired: {fired or 'none'}"))


def check_iverilog(mod, cfg, results):
    flags = cfg["flags"]
    out_vvp = cfg.get("output", "/tmp/opencode/check_rules_iverilog.vvp")
    cmd = ["iverilog", *flags, "-o", out_vvp, *mod["sources"]]
    rc, out = run(cmd, REPO)
    # CR03: compile exits 0; Icarus 'sorry:' limitation notes are not violations.
    real = [l for l in out.splitlines()
            if l.strip() and not any(s in l for s in cfg.get("ignore_lines", []))]
    if rc == 0:
        results.append(("PASS", "CR03", mod["name"],
                        f"exit 0 ({len(real)} non-'sorry:' lines)"))
    else:
        results.append(("FAIL", "CR03", mod["name"],
                        f"exit {rc}; " + " | ".join(real[:3])))


def check_source(mod, rules, results):
    """Run the source-level rules (CR04..CR25) against a module's sources."""
    for rule in rules:
        rid, kind = rule["id"], rule["kind"]
        pat = rule.get("pattern")
        rx = re.compile(pat, re.M | re.S)
        hits = []
        for src in mod["sources"]:
            path = REPO / src
            if not path.exists():
                results.append(("FAIL", rid, mod["name"], f"source missing: {src}"))
                hits = None
                break
            text = strip_comments(path.read_text())
            for m in rx.finditer(text):
                line_no = text[:m.start()].count("\n") + 1
                hits.append(f"{src}:{line_no}: {m.group(0).strip()[:60]}")
        if hits is None:
            continue
        if kind == "forbid":
            if hits:
                results.append(("FAIL", rid, mod["name"],
                                f"{len(hits)} hit(s); " + " | ".join(hits[:3])))
            else:
                results.append(("PASS", rid, mod["name"], "no match"))
        elif kind == "require":
            if hits:
                results.append(("PASS", rid, mod["name"],
                                f"{len(hits)} match(es)"))
            else:
                results.append(("FAIL", rid, mod["name"], "required pattern absent"))
        else:
            results.append(("FAIL", rid, mod["name"], f"unknown rule kind {kind}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verilator", action="store_true")
    ap.add_argument("--iverilog", action="store_true")
    ap.add_argument("--module", default=None)
    args = ap.parse_args()
    do_v, do_i = args.verilator, args.iverilog
    if not do_v and not do_i:
        do_v = do_i = True

    cfg = json.loads((LINT_DIR / "coding_rules.json").read_text())
    mods = cfg["modules"]
    if args.module:
        mods = [m for m in mods if m["name"] == args.module]
        if not mods:
            print(f"unknown module: {args.module}")
            return 1

    src_rules = [r for r in cfg["rules"] if r["tool"] == "source"]

    results = []
    for mod in mods:
        if do_v:
            check_verilator(mod, cfg["verilator"], results)
        if do_i:
            check_iverilog(mod, cfg["iverilog"], results)
        check_source(mod, src_rules, results)

    for status, rid, name, detail in results:
        print(f"[{status}] {rid:<5} {name:<16} {detail}")
    nfail = sum(1 for s, *_ in results if s == "FAIL")
    nrules = len(cfg["rules"])
    print(f"RULES: {nrules} canonical rules in coding_rules.json")
    print(f"RESULT: {'FAIL' if nfail else 'PASS'} - {len(results) - nfail}/{len(results)} "
          f"coding-rule checks passed")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
