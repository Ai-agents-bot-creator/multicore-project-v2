#!/usr/bin/env python3
"""verify_landing.py - confirm the amended spec package (ruling B5 + amendment) actually landed
in the worker's repository.

Usage:
    python3 verify_landing.py --repo /mnt/Code/visualstudio/Design-arch_multi-core
    python3 verify_landing.py --repo <root> --rebuild     # re-render the HTML first

Exit code 0 = the package is current and the package gate passes.
Exit code 1 = something did not land (each miss is listed).

The package files are copied in by hand (folder copy), so this script does not patch
anything: it checks the landed state against the canonical hashes and the textual
markers of ruling B5, then runs the canonical package gate.

Canonical package gate: pd/v1/verify_patch_set.py   (131 checks)
Canonical doc checker : check_docs.py                (47 checks)
"""
import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

# sha256 prefixes of the canonical files (ruling B5 + amendment, 2026-11-06)
EXPECTED = {
    "white_papers/final/FINAL_whitepaper_v3.0.md": "0612a47ce780f4d5",
    "white_papers/final/SPEC_SHEET.md": "f3c69f304f2bb5cc",
    "white_papers/final/HLD_LLD_4x4_architecture.md": "ca23ef4d6c054585",
    "white_papers/final/HLD_LLD_2x2_FPGA.md": "adb412722f473621",
    "white_papers/final/SLICE_16_1.md": "a3d7c99705f47601",
    "white_papers/final/WORK_BREAKDOWN_16.md": "ffebac6efec42378",
    "white_papers/final/diagrams_rendered.html": "024cbce799cbae10",
    "pd/v1/verify_patch_set.py": "09e5a06a531fda3a",
}

# textual markers that must be present in the landed white paper
WP_MARKERS = [
    ("A2.2 split into two clauses", r"A2\.2a\s*—\s*no missing bits"),
    ("A2.2b bounded extra bits", r"A2\.2b\s*—\s*bounded extra bits"),
    ("A2.2 vacuity note", r"vacuously true while no tile holds the line in S"),
    ("committed sharer set rule (Appendix B)", r"Committed sharer set \(ruling B5\)"),
    ("committed-set exclusion in 5.3", r"except a tile that has already released the line is not recorded as a sharer"),
    ("section 12 item 12 open", r"Lemma L1 versus a mid-miss tile"),
    ("ledger row AG", r"^\|\s*\*\*AG\*\*\s*\|"),
    ("AG no longer claims an unconditional 'No RTL change'",
     r"\*\*No RTL change is required for the Case-C bookkeeping lag\*\*"),
    # ruling B6
    ("B6: rule 6 makes a same-line INV abort the miss",
     r"\*\*A same-line INV does occur, and it aborts the miss \(ruling B6\)\.\*\*"),
    ("B6: Lemma L1 restated as 'no same-line message is serviced'",
     r"Lemma L1 \(no same-line message is serviced during a transient\)"),
    ("B6: Appendix A L1-FSM abort row",
     r"IS_D / IM_D / SM_D \| INV received \(VC3\) for the line being missed"),
    ("B6: section 12 item 12 closed",
     r"Closed by ruling B6 \u2014 the hazard is real"),
    ("B6: ledger row AH", r"^\|\s*\*\*AH\*\*\s*\|"),
]
# markers that must NOT be present (the pre-B5 wording)
WP_ANTI_MARKERS = [
    ("old single-clause A2.2 wording", r"sharers equal the S-mask exactly \(no stale bits\)"),
]

GATE_MARKERS = [
    ("J3 check present", r'check\("J3"'),
    ("J4 check present", r'check\("J4"'),
    ("132 checks expected", r"132"),
]


def sha256_prefix(path, n=16):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="repository root")
    ap.add_argument("--pkg", default="white_papers/final")
    ap.add_argument("--rebuild", action="store_true",
                    help="re-render diagrams_rendered.html with pd/v1/build_diagrams_html.py first")
    args = ap.parse_args()
    root = Path(args.repo).resolve()
    fails, notes = [], []

    if not root.is_dir():
        print(f"FAIL: repo root not found: {root}")
        return 1

    # ---------------------------------------------------------------- rebuild ---
    if args.rebuild:
        builder = root / "pd/v1/build_diagrams_html.py"
        pkg = root / args.pkg
        if builder.is_file():
            cmd = [sys.executable, str(builder),
                   "--src4", str(pkg / "HLD_LLD_4x4_architecture.md"),
                   "--src2", str(pkg / "HLD_LLD_2x2_FPGA.md"),
                   "--out", str(pkg / "diagrams_rendered.html")]
            r = subprocess.run(cmd, capture_output=True, text=True)
            notes.append(f"rebuild: {' '.join(cmd[1:])}")
            if r.returncode != 0:
                fails.append(f"re-render failed (exit {r.returncode}): {(r.stderr or r.stdout).strip()[:200]}")
            else:
                notes.append(f"rebuild output: {(r.stdout or '').strip()[-160:]}")
        else:
            fails.append(f"rebuild requested but {builder} is missing")

    # ---------------------------------------------------------------- hashes ---
    for rel, want in EXPECTED.items():
        p = root / rel
        if not p.is_file():
            fails.append(f"MISSING: {rel}")
            continue
        got = sha256_prefix(p)
        if got != want:
            fails.append(f"HASH MISMATCH: {rel}\n            expected {want}  got {got}")
        else:
            notes.append(f"ok (hash): {rel}")

    # ---------------------------------------------------------------- markers ---
    wp = root / args.pkg / "FINAL_whitepaper_v3.0.md"
    if wp.is_file():
        t = wp.read_text(encoding="utf-8", errors="replace")
        for label, pat in WP_MARKERS:
            if re.search(pat, t, re.M):
                notes.append(f"ok (marker): {label}")
            else:
                fails.append(f"MARKER MISSING: {label}")
        for label, pat in WP_ANTI_MARKERS:
            if re.search(pat, t, re.M):
                fails.append(f"STALE WORDING STILL PRESENT: {label}")
            else:
                notes.append(f"ok (no stale text): {label}")
    else:
        fails.append(f"MISSING: {args.pkg}/FINAL_whitepaper_v3.0.md")

    gate = root / "pd/v1/verify_patch_set.py"
    if gate.is_file():
        g = gate.read_text(encoding="utf-8", errors="replace")
        for label, pat in GATE_MARKERS:
            if re.search(pat, g):
                notes.append(f"ok (marker): gate {label}")
            else:
                fails.append(f"MARKER MISSING: gate {label}")
    else:
        fails.append("MISSING: pd/v1/verify_patch_set.py")

    # ---------------------------------------------------------------- gate run ---
    if gate.is_file() and (root / args.pkg).is_dir():
        cmd = [sys.executable, str(gate), "--dir", args.pkg,
               "--build-script", "pd/v1/build_diagrams_html.py"]
        r = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        first = (r.stdout or r.stderr or "").strip().splitlines()[:1]
        notes.append(f"package gate: {(first[0] if first else 'no output')} (exit {r.returncode})")
        if r.returncode != 0:
            fails.append(f"package gate exit code {r.returncode}")
            for line in (r.stdout or "").splitlines():
                if line.startswith("[FAIL]"):
                    fails.append(f"  {line.strip()[:160]}")

    print("=" * 78)
    print("LANDING VERIFICATION - ruling B5 (spec change + amendment)")
    print("=" * 78)
    for n in notes:
        print(f"  [ok]   {n}")
    for f in fails:
        print(f"  [FAIL] {f}")
    print("-" * 78)
    if fails:
        print(f"RESULT: FAIL - {len(fails)} problem(s). The package is NOT current.")
        print("Copy the amended package over white_papers/final/ and the updated gate over")
        print("pd/v1/verify_patch_set.py, then re-run this script.")
        return 1
    print("RESULT: PASS - the amended package is landed and the package gate is green.")
    print("The spec package is current. The implementation is NOT: ruling B6 (the same-line")
    print("INV abort, section 16.15) must be implemented in the RTL, modelled, asserted and")
    print("mutation-tested before the package can be signed off.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
