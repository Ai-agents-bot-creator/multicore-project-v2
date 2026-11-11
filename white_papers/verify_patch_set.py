#!/usr/bin/env python3
"""apply_b7_repo.py - apply ruling B7 to the design repo, in place.

Small on purpose: this is the artefact a human copies into the repository. It
patches only the B7 deltas (the B5/B6 edits are already in the repo), verifies
every replacement, updates the package gate to 133 checks, re-renders the HTML
and runs the gate.

    python3 apply_b7_repo.py --repo /mnt/Code/visualstudio/Design-arch_multi-core
    python3 apply_b7_repo.py --repo <root> --dry-run

Idempotent: re-running reports "already applied" and changes nothing.
Exit 0 = applied and the gate is green. Exit 1 = something failed; nothing is
rolled back.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_REPO = "/mnt/Code/visualstudio/Design-arch_multi-core"


# ---------------------------------------------------------------- WP edits ---
ARB_OLD = (
    "1. **VC arbitration per input port:** fixed priority by *class* — **RESP > INV > FWD > "
    "REQ** — so protocol-critical responses and invalidations are never queued behind request "
    "traffic."
)
ARB_NEW = ARB_OLD + (
    "\n\n**The directory controller's receive path is per-VC (ruling B7).** The home tile's "
    "receive path holds **one queue per VC** and pops them by the **same class priority** as the "
    "fabric (**RESP > INV > FWD > REQ**), so a response can never be head-of-line blocked behind a "
    "request that arrived earlier. The previous wording fixed the priority only *inside the router* "
    "(item 1 above), which left a single arrival-ordered directory queue specification-conformant "
    "— and that queue deadlocks the concurrent-upgrade race (§3.3 rule 6, ruling B6): while a "
    "transient is open the directory pops only `INVACK`/`PUTS`/`PUTM`/`UNBLOCK`, so a `GETM` queued "
    "ahead of the `INVACK` blocks the invalidation from ever completing. Per-VC ordering is what "
    "makes the `INVACK` reachable."
)

RULE6_TAIL = (
    "Deferring the same-line INV would deadlock, because the directory waits for the INVACK "
    "while blocking the bank (§3.7) and therefore cannot deliver the DATA the tile is waiting for."
)
RULE6_NEW_TAIL = RULE6_TAIL + (
    " **The aborted access is then completed or re-issued (ruling B7):** the directory may still "
    "grant the abandoned request, and the tile may either accept that grant as the completion of its "
    "access (installing the line and sending UNBLOCK) or discard it and re-issue the access — but "
    "it must never leave the directory's transient unexited, and the directory must never record a "
    "tile as the owner of a line that tile has declined."
)

L1_TAIL = (
    "(iv) the one case that does occur — a concurrent upgrade race — is handled by the abort path "
    "rather than by deferral."
)
L1_NEW_TAIL = L1_TAIL + (
    " **The abort is completed through the directory's normal grant path (ruling B7):** the per-VC "
    "receive order (§3.5) guarantees the `INVACK` is not blocked behind the abandoned request, and "
    "the requester either accepts the stale grant or declines it, so the transient always exits."
)

ITEM13 = (
    "| 13 | **Bounded progress under repeated upgrade-race aborts** — can two tiles livelock, each "
    "aborting the other's upgrade in turn? | **Open — raised by the verification team (ruling B6 "
    "challenge).** The abort-and-re-issue path can, in principle, ping-pong: two tiles upgrading the "
    "same line repeatedly abort and re-issue against each other, with no protocol-level bound on "
    "consecutive aborts. Premise F (§4.6) bounds *message service*, not request-level progress, so it "
    "does not cover this case. Candidate resolutions: an explicit bound on consecutive aborts with an "
    "ageing rule (the request that has been aborted more times wins the next grant), a queued ticket, "
    "or exponential backoff | Decide when the upgrade-race slice is green; the fix belongs in the "
    "request-admission policy, not in the L1's abort path | Week 10 |"
)

AI_ROW = (
    "| **AI** | Directory receive-path ordering and the completion of an aborted access (ruling B7) | "
    "— | — | — | — | — | — | **The home tile's receive path holds one queue per VC and pops them by "
    "the same class priority as the fabric (RESP > INV > FWD > REQ), so a response is never "
    "head-of-line blocked behind a request. An aborted access is completed or re-issued: the tile may "
    "accept the stale grant (installing the line and sending UNBLOCK) or decline it, but the "
    "directory's transient must always exit and the directory must never record a declining tile as "
    "the owner** | Ruling B7: with the B6 abort implemented, the directed upgrade-race test still "
    "stalled — the directory sat in `DIR_INV_WAIT` with `RXQ cnt=2 head_msg=GETM` and the `INVACK` "
    "behind it. The WP fixed VC priority only inside the router (§3.5 item 1), so a single "
    "arrival-ordered directory queue was specification-conformant and deadlocked: the directory pops "
    "only `INVACK`/`PUTS`/`PUTM`/`UNBLOCK` while a transient is open, so a queued `GETM` blocks the "
    "invalidation that must complete it. Two changes close it: the per-VC receive order (which makes "
    "the `INVACK` reachable) and the explicit completion/decline rule for the abandoned request (which "
    "keeps the directory's state consistent with what the tile actually holds). |"
)

# --------------------------------------------------------------- SPEC edit ---
SPEC_ANCHOR = "- **Directory path:**"
SPEC_LINE = (
    "\n**Directory receive path (ruling B7):** the home tile's receive path is **per-VC** — one "
    "queue per VC, popped by the class priority **RESP > INV > FWD > REQ** (WP §3.5), so a response "
    "is never head-of-line blocked behind a request."
)

# ---------------------------------------------------------------- LLD edit ---
LLD_OLD = (
    '    Q["Pending request handling per bank<br/>the queue is the bank\'s request queue, behind the '
    'single serialized L2 port - WP 3.2, 3.7;<br/>queue depth and service order: NOT SPECIFIED IN WP '
    '- open item 9, Week 4"]'
)
LLD_NEW = (
    '    Q["Pending request handling per bank<br/>the queue is the bank\'s request queue, behind the '
    'single serialized L2 port - WP 3.2, 3.7;<br/>queue depth and service order: NOT SPECIFIED IN WP '
    '- open item 9, Week 4<br/>the receive path is PER-VC: one queue per VC, popped by class priority '
    'RESP &gt; INV &gt; FWD &gt; REQ - B7"]'
)

# ------------------------------------------------------------ gate patches ---
J5_CHECK = '''
    # J5 (ruling B7): the directory's receive path is per-VC, and an aborted access has
    # an explicit completion rule. Both were gaps that let a spec-conformant directory
    # deadlock the concurrent-upgrade race.
    _pervc = "The directory controller's receive path is per-VC (ruling B7)" in wp
    _prio = "one queue per VC" in wp and "RESP > INV > FWD > REQ" in wp
    _comp = "The aborted access is then completed or re-issued (ruling B7)" in wp
    _it13 = re.search(r"^\\| 13 \\| \\*\\*Bounded progress under repeated upgrade-race aborts\\*\\*", wp, re.M)
    _ai = re.search(r"^\\|\\s*\\*\\*AI\\*\\*\\s*\\|", wp, re.M)
    _lld = "the receive path is PER-VC" in l4
    check("J5", "B7: the directory receive path is per-VC, the aborted access has a completion rule, and section 12 item 13 is open",
          _pervc and _prio and _comp and bool(_it13) and bool(_ai) and _lld,
          f"pervc={_pervc} prio={_prio} completion={_comp} item13={bool(_it13)} rowAI={bool(_ai)} lld={_lld}")
'''


def patch_text(path, old, new, dry):
    """Replace `old` with `new` in `path`. Idempotent. Returns 'applied'|'already'|'missing'."""
    if not path.is_file():
        return "missing"
    t = path.read_text(encoding="utf-8")
    if new in t:
        # already applied. (Note: `new` usually CONTAINS `old`, so the old text is
        # still present after a successful patch - testing for it would re-apply.)
        return "already"
    if t.count(old) != 1:
        return "missing"
    if not dry:
        path.write_text(t.replace(old, new), encoding="utf-8")
    return "applied"


def insert_line_after(path, anchor_prefix, new_line, dry):
    if not path.is_file():
        return "missing"
    lines = path.read_text(encoding="utf-8").split("\n")
    if any(l.startswith(new_line[:60]) for l in lines):
        return "already"
    idx = [i for i, l in enumerate(lines) if l.startswith(anchor_prefix)]
    if len(idx) != 1:
        return "missing"
    if not dry:
        lines.insert(idx[0] + 1, new_line)
        path.write_text("\n".join(lines), encoding="utf-8")
    return "applied"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--pkg", default="white_papers/final")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = Path(args.repo).resolve()
    if not root.is_dir():
        print(f"ERROR: repo root not found: {root}")
        return 1
    pkg = root / args.pkg
    wp = pkg / "FINAL_whitepaper_v3.0.md"
    sp = pkg / "SPEC_SHEET.md"
    l4 = pkg / "HLD_LLD_4x4_architecture.md"
    sl = pkg / "SLICE_16_1.md"
    wb = pkg / "WORK_BREAKDOWN_16.md"
    gate = root / "pd/v1/verify_patch_set.py"
    builder = root / "pd/v1/build_diagrams_html.py"
    html = pkg / "diagrams_rendered.html"

    print(f"repo: {root}")
    print("-" * 78)
    steps = [
        ("WP 3.5  per-VC receive path", lambda: patch_text(wp, ARB_OLD, ARB_NEW, args.dry_run)),
        ("WP 3.3  rule 6 completion clause", lambda: patch_text(wp, RULE6_TAIL, RULE6_NEW_TAIL, args.dry_run)),
        ("WP 4.6  Lemma L1 completion clause", lambda: patch_text(wp, L1_TAIL, L1_NEW_TAIL, args.dry_run)),
        ("WP 12   item 13 (bounded progress)", lambda: insert_line_after(wp, "| 12 | **Lemma L1 versus a mid-miss tile**", ITEM13, args.dry_run)),
        ("WP 13   ledger row AI", lambda: insert_line_after(wp, "| **AH** |", AI_ROW, args.dry_run)),
        ("SPEC    directory receive path", lambda: insert_line_after(sp, SPEC_ANCHOR, SPEC_LINE.strip(), args.dry_run)),
        ("LLD4    per-VC note", lambda: patch_text(l4, LLD_OLD, LLD_NEW, args.dry_run)),
        ("SLICE   count 132 -> 133", lambda: patch_text(sl, "still reports 132/132 (no spec regression).", "still reports 133/133 (no spec regression).", args.dry_run)),
        ("BREAKDN count 132 -> 133", lambda: patch_text(wb, "the LLD `.md` sources (132 checks).", "the LLD `.md` sources (133 checks).", args.dry_run)),
        ("BREAKDN note 132 -> 133", lambda: patch_text(wb, "- The 132-check verifier (`verify_patch_set.py`)", "- The 133-check verifier (`verify_patch_set.py`)", args.dry_run)),
    ]
    fails = []
    for label, fn in steps:
        try:
            r = fn()
        except Exception as e:                       # noqa: BLE001
            r = f"error: {e}"
        if r == "missing":
            fails.append(f"{label}: anchor not found (the repo copy may differ from the expected revision)")
        print(f"  [{r:>7}] {label}")
    if fails:
        print("-" * 78)
        for f in fails:
            print(f"  [FAIL] {f}")
        print("RESULT: FAIL - the repo copy does not match the expected revision; "
              "send the diff to the specification owner before patching.")
        return 1

    if args.dry_run:
        print("-" * 78)
        print("RESULT: dry run complete - nothing written.")
        return 0

    # ---- the gate: add the J5 check ---------------------------------------
    if gate.is_file():
        g = gate.read_text(encoding="utf-8")
        if 'check("J5"' not in g:
            anchor = "    if wb and not args.partial:"
            if g.count(anchor) != 1:
                print("  [FAIL]   gate: cannot locate the J5 insertion point")
                return 1
            g = g.replace(anchor, J5_CHECK.lstrip("\n") + "\n" + anchor, 1)
            gate.write_text(g, encoding="utf-8")
            print("  [applied] gate: J5 check added")
        else:
            print("  [already] gate: J5 check present")

    # ---- re-render the HTML ----------------------------------------------
    if builder.is_file() and html.is_file():
        cmd = [sys.executable, str(builder), "--src4", str(l4), "--src2",
               str(pkg / "HLD_LLD_2x2_FPGA.md"), "--out", str(html)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        print(f"  [{'ok' if r.returncode == 0 else 'FAIL':>7}] HTML re-render "
              f"({(r.stdout or r.stderr).strip().splitlines()[-1][:80] if (r.stdout or r.stderr).strip() else ''})")
        if r.returncode != 0:
            return 1
    else:
        print("  [skip  ] HTML re-render: builder or template missing")

    # ---- run the gate -----------------------------------------------------
    print("-" * 78)
    if gate.is_file():
        r = subprocess.run([sys.executable, str(gate), "--dir", args.pkg,
                            "--build-script", "pd/v1/build_diagrams_html.py"],
                           cwd=root, capture_output=True, text=True)
        for line in (r.stdout or "").splitlines()[:1]:
            print(f"package gate: {line}")
        if r.returncode != 0:
            for line in (r.stdout or "").splitlines():
                if line.startswith("[FAIL]"):
                    print(f"  {line.strip()[:170]}")
            print("RESULT: FAIL - the package gate is not green. Paste the output above.")
            return 1
    else:
        print("RESULT: FAIL - pd/v1/verify_patch_set.py not found")
        return 1
    print("RESULT: PASS - ruling B7 is applied and the package gate is green (133 checks).")
    print("Next: Task 3.5 (implement the per-VC receive path) and Task 3.6 (re-run the "
          "directed upgrade-race test). B7 is not closed until B6.3 and B6.4 pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
