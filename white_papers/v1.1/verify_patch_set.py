#!/usr/bin/env python3
"""
Acceptance verifier for patch set P1-P15 (N12-N17 + labels + S2).

Checks every acceptance criterion for the applied patches against the four
source files plus the re-rendered HTML.  Exit code 0 = all checks pass.

Usage
  python3 verify_patch_set.py --dir <folder containing the 5 files>
  python3 verify_patch_set.py --wp A.md --lld4 B.md --lld2 C.md --spec D.md --html E.html

Expected filenames (used with --dir):
  FINAL_whitepaper_v3.0.md  HLD_LLD_4x4_architecture.md  HLD_LLD_2x2_FPGA.md
  SPEC_SHEET.md             diagrams_rendered.html
"""
import argparse
import os
import re
import subprocess
import sys

results = []


def check(pid, desc, ok, detail=""):
    results.append((pid, desc, bool(ok), detail))


def contains(text, *needles):
    missing = [n for n in needles if n not in text]
    return (not missing), (", ".join(m[:60] for m in missing))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--wp")
    ap.add_argument("--lld4")
    ap.add_argument("--lld2")
    ap.add_argument("--spec")
    ap.add_argument("--html")
    ap.add_argument("--wb", default=None, help="WORK_BREAKDOWN_16.md")
    ap.add_argument("--slice", default=None, help="SLICE_16_1.md")
    ap.add_argument("--build-script", default=None,
                    help="path to build_diagrams_html.py, to re-check the HTML is in sync")
    args = ap.parse_args()

    def path(explicit, default):
        return explicit if explicit else os.path.join(args.dir, default)

    wp_p = path(args.wp, "FINAL_whitepaper_v3.0.md")
    l4_p = path(args.lld4, "HLD_LLD_4x4_architecture.md")
    l2_p = path(args.lld2, "HLD_LLD_2x2_FPGA.md")
    sp_p = path(args.spec, "SPEC_SHEET.md")
    ht_p = path(args.html, "diagrams_rendered.html")
    wb_p = args.wb if args.wb else (os.path.join(args.dir, "WORK_BREAKDOWN_16.md") if args.dir else None)

    for p in (wp_p, l4_p, l2_p, sp_p, ht_p):
        if not os.path.exists(p):
            print(f"ERROR: missing file {p}")
            return 2
    wb = ""
    if wb_p and os.path.exists(wb_p):
        wb = open(wb_p, encoding="utf-8").read()
    else:
        print(f"NOTE: {wb_p} not found - group H (work breakdown) will be skipped")
    sl_p = args.slice if args.slice else (os.path.join(args.dir, "SLICE_16_1.md") if args.dir else None)
    sl = ""
    if sl_p and os.path.exists(sl_p):
        sl = open(sl_p, encoding="utf-8").read()
    else:
        print(f"NOTE: {sl_p} not found - group I (implementation slice) will be skipped")

    wp = open(wp_p, encoding="utf-8").read()
    l4 = open(l4_p, encoding="utf-8").read()
    l2 = open(l2_p, encoding="utf-8").read()
    sp = open(sp_p, encoding="utf-8").read()
    ht = open(ht_p, encoding="utf-8").read()

    # ---------------- P1  rule 9 (DATA exclusive bit) ----------------
    ok, d = contains(wp, "9. **The DATA exclusive bit is 1 only when the requester becomes the sole holder.**")
    check("P1", "WP rule 9 (DATA exclusive bit) present", ok, d)
    ok, d = contains(wp, "§3.3" if "§3.3" in wp else "")
    check("P1b", "rule 9 mentions GETS grant / forward", "forward" in wp and "GETS grant" in wp, d)

    # ---------------- P2  Appendix A EI_A / MI_A defensive rows ------
    ok, d = contains(wp, "| EI_A | FWD_GETS/FWD_GETM received (VC1) | EI_A |",
                         "| MI_A | FWD_GETS/FWD_GETM received (VC1) | MI_A |")
    check("P2", "Appendix A: EI_A + MI_A defensive FWD rows", ok, d)

    # ---------------- P3  Appendix B DIR_FWD_WAIT rows ----------------
    ok, d = contains(wp, "| DIR_FWD_WAIT | PUTM (owner) |",
                         "| DIR_FWD_WAIT | PUTS (owner) |",
                         "| DIR_FWD_WAIT | INVACK (defensive) |")
    check("P3", "Appendix B: PUTM + PUTS + INVACK rows in DIR_FWD_WAIT", ok, d)
    m = re.search(r"\| DIR_FWD_WAIT \| PUTM \(owner\) \|(.+?)\|\s*—\s*\(awaiting", wp)
    check("P3b", "DIR_FWD_WAIT|PUTM row sends PUTACK",
          bool(m) and "PUTACK" in m.group(1),
          "" if m else "row not found")

    # ---------------- P4  L2 per-line word {valid, tag, dirty} --------
    ok, d = contains(wp, "19 b address tag + valid + dirty = 21 b",
                         "21 b address tag + valid + dirty = 23 b")
    check("P4", "WP 3.6 stored-tag table shows valid+dirty widths", ok, d)
    ok, d = contains(wp, "neither participates in the tag comparison")
    check("P4b", "valid/dirty excluded from the tag comparison", ok, d)
    ok, d = contains(wp, "On every bank write the dirty bit is set to the dirtiness of the data written")
    check("P15", "dirty bit set to the dirtiness of the data written", ok, d)
    ok, d = contains(wp, "0x0000_0000")
    check("P13", "address-0 alias reason (valid bit) stated", ok, d)

    # ---------------- P5  section 6.1 BRAM table ---------------------
    ok, d = contains(wp, "L2 tag (32 × 23 b")
    check("P5", "WP 6.1 per-tile table: L2 tag 32 x 23 b", ok, d)

    # ---------------- P6  adjudication ledger row E ------------------
    ok, d = contains(wp, "superseded by N3a/N13")
    check("P6", "section 13 ledger row E annotated", ok, d)

    # ---------------- P7/P8/P9/P12/P13  4x4 LLD ----------------------
    ok, d = contains(l4, "21 b per-line word")
    check("P7", "4x4 LLD-5 tag label updated", ok, d)
    ok, d = contains(l4, "valid + 19 b address tag + dirty = 21 b")
    check("P8", "4x4 LLD-7 tag label updated", ok, d)
    ok, d = contains(l4, "is SPECIFIED")
    check("P9", "4x4 LLD-7 X/Y bit-order claim corrected (A13)", ok and "NOT SPECIFIED IN WP</br/>The bit order" not in l4, d)
    ok, d = contains(l4, "EI_A --> EI_A : FWD received", "MI_A --> MI_A : FWD received")
    check("P12", "4x4 LLD-2: EI_A/MI_A defensive FWD edges", ok, d)
    ok, d = contains(l4, "PUTM from owner, satisfies the forward",
                         "PUTS from owner, cancel the forward",
                         "INVACK defensive")
    check("P13", "4x4 LLD-3: DIR_FWD_WAIT rows drawn", ok, d)
    ok, d = contains(l4, "INV, DATA, INVACK or FWD for a DIFFERENT line")
    check("P12b", "4x4 LLD-2 Premise-R note includes FWD", ok, d)

    # ---------------- P10/P11  2x2 LLD ------------------------------
    ok, d = contains(l2, "per-line word = valid + 21 b address tag + dirty = 23 b")
    check("P10", "2x2 LLD-F1 tag label updated", ok, d)
    ok, d = contains(l2, "32 x 23 b per-line word at 2x2")
    check("P11", "2x2 LLD-F2 BRAM label updated", ok, d)

    # ---------------- P14  SPEC_SHEET -------------------------------
    ok, d = contains(sp, "TAG 32 × 23 b")
    check("P14a", "SPEC section 3: L2 bank block 23 b", ok, d)
    ok, d = contains(sp, "23 b at 2×2 and 21 b at 4×4")
    check("P14b", "SPEC section 6: per-line word widths", ok, d)
    ok, d = contains(sp, "Normative rules (10)")
    check("P14c", "SPEC section 7: rules count updated to 10", ok, d)
    ok, d = contains(sp, "(10) no eviction is started while a miss is outstanding")
    check("P14c2", "SPEC section 7: rule 10 (deferred eviction) listed", ok, d)
    ok, d = contains(sp, "EI_A", "MI_A")
    check("P14d", "SPEC section 7: evict-during-forward covered", ok, d)
    ok, d = contains(sp, "valid")
    check("P14e", "SPEC section 7: valid bit documented", ok, d)

    # ---------------- P17  section 15 / 16 split --------------------
    ok, d = contains(sp, "## 16.")
    check("P17", "SPEC has a section 16 (pending RTL)", ok, d)
    ok, d = contains(sp, "pending RTL")
    check("P17b", "section 16 labelled 'pending RTL'", ok, d)
    check("P17c", "section 15 still holds the WP-gap items",
          "Not specified in WP" in sp, "")

    # ---------------- stale-claim sweep -----------------------------
    stale = {
        "WP": [s for s in ("32 × 22 b", "L2 tag (32 × 19 b)") if s in wp],
        "4x4 LLD": [s for s in ("32 entries x 19 b stored tag",) if s in l4],
        "2x2 LLD": [s for s in ("32 x 21 b stored at 2x2",) if s in l2],
        "SPEC": [s for s in ("TAG 32 × 22 b",) if s in sp],
    }
    for k, v in stale.items():
        check("SWEEP", f"no stale tag-width claim in {k}", not v, "; ".join(v))
    check("SWEEP2", "4x4 LLD-7 no longer claims X/Y order is unspecified",
          "The bit order of X and Y inside the 4-bit home field is NOT SPECIFIED" not in l4, "")

    # ---------------- S2  HTML in sync ------------------------------
    n_cards = ht.count('<div class="card">')
    check("S2a", "HTML contains 19 cards", n_cards == 19, f"found {n_cards}")
    ok, d = contains(ht, "EI_A --&gt; EI_A", "PUTS from owner, cancel the forward")
    check("S2b", "HTML carries the new LLD-2 / LLD-3 content", ok, d)
    if args.build_script:
        r = subprocess.run(
            [sys.executable, args.build_script, "--src4", l4_p, "--src2", l2_p,
             "--out", ht_p, "--selftest"],
            capture_output=True, text=True)
        out = r.stdout + r.stderr
        m = re.search(r"cards differing from shipped artifact: (\d+)", out)
        n = int(m.group(1)) if m else -1
        check("S2c", "HTML is byte-in sync with the .md sources (selftest)", n == 0,
              out.strip().splitlines()[-1] if out.strip() else "no output")


    # ============ GROUP G: propagation checks (Batch 2/3 -> rest of the doc) ============
    # G1 fairness bound: the 13-round service bound must appear everywhere the
    #    8-round *escape threshold* was previously used as the *service bound*.
    ok, d = contains(wp, "within at most **13** arbitration rounds")
    check("G1a", "Premise F (4.6) uses the 13-round service bound", ok, d)
    ok, d = contains(wp, "| Bounded service | Every VC with pending traffic is served within 13 arbitration rounds (Premise F) |")
    check("G1b", "5.3 liveness table uses 13 rounds", ok, d)
    ok, d = contains(wp, "every VC with pending traffic is served within 13 arbitration rounds.")
    check("G1c", "Appendix E uses 13 rounds", ok, d)
    check("G1d", "no stale 'served within 8 arbitration rounds' left",
          "served within 8 arbitration rounds" not in wp and "within at most 8 arbitration rounds" not in wp, "")
    ok, d = contains(sp, "13 arbitration rounds")
    check("G1e", "SPEC 9.3 carries the 13-round bound", ok, d)

    # G2 A14: no PUTACK to a sharer -> 3.4 and 5.1 must not still promise one
    m = re.search(r"\| L1 clean eviction \|(.+?)\|\s*$", wp, re.M)
    check("G2a", "3.4 clean-eviction row states the S case takes no PUTACK",
          bool(m) and ("no PUTACK" in m.group(1) or "S direct" in m.group(1) and "no PUTACK" in m.group(1)),
          "" if m else "row not found")
    m = re.search(r"\| 9 \| L1 clean eviction \(S/E\) \|(.+?)\|\s*$", wp, re.M)
    check("G2b", "5.1 test 9 states the S case takes no PUTACK",
          bool(m) and ("no PUTACK" in m.group(1) or "E only" in m.group(1)),
          "" if m else "row not found")

    # G3 A15: pending_op encoding must reach the SPEC sheet (6 codes incl. NONE)
    ok, d = contains(sp, "000 NONE")
    check("G3", "SPEC 4 DTR pending-op encoding includes NONE", ok, d)

    # G4 B2: rule 10 must reach the SPEC sheet
    ok, d = contains(sp, "Normative rules (10)")
    check("G4", "SPEC 7 rule count is 10 (B2 rule 10 added)", ok, d)

    # G5 diagram claims that the WP now specifies
    check("G5a", "4x4 LLD-1 no longer calls tile-ID->position unspecified",
          "Tile-ID to mesh-position mapping: NOT SPECIFIED IN WP" not in l4, "")
    check("G5b", "2x2 HLD-F2 no longer calls the stimulus source unspecified",
          "is NOT SPECIFIED IN WP. ILA/VIO" not in l2 and "host bridge, VIO, or free-running generator" not in l2, "")
    ok, d = contains(l4, "bank's request queue")
    check("G5c", "4x4 LLD-5 names the bank request queue (A12)", ok, d)

    # G6 A8: BRAM ceiling 70 -> 80 in the 2x2 diagram
    check("G6", "2x2 LLD-F2 BRAM ceiling is 80, not 70",
          "BRAM at or below 70" not in l2 and "BRAM at or below 80" in l2, "")

    # G7 SPEC 16 must list the Batch-2/3 normative items
    for key, label in [("deferred until the miss completes", "rule 10 deferred eviction"),
                       ("PLRU", "tree-PLRU update rule"),
                       ("4 flits per VC", "NIC FIFO depth"),
                       ("512-bit", "intra-tile datapath width"),
                       ("mesh row Y, column X", "tile-ID -> mesh position"),
                       ("DMA_WRITE", "DMA path mapping"),
                       ("13 arbitration rounds", "13-round fairness bound")]:
        ok, d = contains(sp, key)
        check("G7", f"SPEC 16 lists: {label}", ok, d)

    # G8 pending_op = EVICT is unreachable once DIR_EVICT is entered only from DIR_MEM_WAIT
    m = re.search(r"\| Pending op \| 3 b \|(.+?)\|", wp)
    # strip the state name DIR_EVICT so only a pending-op *code* named EVICT is flagged
    if m and "EVICT" in m.group(1).replace("DIR_EVICT", ""):
        ok, d = contains(wp, "pending_op = EVICT")
        check("G8", "dead pending-op code EVICT is either dropped or documented", ok, d)
    else:
        check("G8", "dead pending-op code EVICT is either dropped or documented", True, "")

    # G9 B4: the DMA path rests on an L1-lite that the WP must describe
    ok, d = contains(wp, "DMA L1-lite")
    check("G9a", "WP describes the DMA L1-lite's coherence receive path", ok, d)
    ok, d = contains(wp.replace("*", ""), "before the DMA")
    check("G9b", "WP states the inline-data vs owner-write-back ordering", ok, d)

    # G10 12 items 10/11 wording
    check("G10a", "WP 6.1 states the FPGA stimulus source (JTAG bridge)",
          "JTAG" in wp, "")
    m = re.search(r"\| 11 \| 2×2 DMA configuration \|(.+?)\|\s*Week (\d+) \|", wp)
    check("G10b", "12 item 11 closure is not the gate week (Week 8)",
          bool(m) and m.group(2) != "8", "" if m else "item 11 row not found")

    # G11 one round == one switch-arbitration cycle (so 13 < T=64 is dimensionally sound)
    ok, d = contains(wp, "one switch-arbitration cycle")
    check("G11", "3.5 defines a round as a switch-arbitration cycle", ok, d)


    # G12 section 12 open-item numbering must be contiguous, and cross-references must match
    sec12 = re.search(r"^## 12\. Open Items.*?(?=^## 13\.)", wp, re.S | re.M)
    sec12 = sec12.group(0) if sec12 else ""
    nums = [int(n) for n in re.findall(r"^\| *(\d+) *\|", sec12, re.M)]
    check("G12a", "section 12 item numbers are contiguous from 1",
          bool(nums) and nums == list(range(1, len(nums) + 1)),
          f"found {nums}")
    dma_rows = [r for r in re.findall(r"^\| *\d+ *\|.*$", sec12, re.M) if "DMA configuration" in r]
    dma_num = None
    dma_week = None
    if dma_rows:
        mm = re.match(r"^\| *(\d+) *\|", dma_rows[0])
        dma_num = int(mm.group(1)) if mm else None
        wm = re.search(r"\| *Week (\d+) *\|", dma_rows[0])
        dma_week = int(wm.group(1)) if wm else None
    check("G12b", "the 2x2 DMA open item exists and is not closed in the gate week",
          dma_week is not None and dma_week != 8,
          f"item {dma_num}, Week {dma_week}")
    m = re.search(r'DMA22\["([^"]*)"', l2)
    if m and "open item" in m.group(1):
        rm = re.search(r"open item (\d+)", m.group(1))
        check("G12c", "2x2 diagram's 'open item N' matches the section 12 item number",
              rm is not None and dma_num is not None and int(rm.group(1)) == dma_num,
              f"diagram says {rm.group(1) if rm else '?'}, section 12 says {dma_num}")


    # G13 every section-12 cross-reference must point at an item that exists
    sec12b = re.search(r"^## 12\. Open Items.*?(?=^## 13\.)", wp, re.S | re.M)
    sec12b = sec12b.group(0) if sec12b else ""
    existing = set(re.findall(r"^\| *(\d+) *\|", sec12b, re.M))
    refs = set()
    for txt in (wp, sp, l4, l2):
        refs |= set(re.findall(r"§\s*12\s*(?:item|#)\s*(\d+)", txt))
        refs |= set(re.findall(r"open item (\d+)", txt))
    dangling = sorted(r for r in refs if r not in existing)
    check("G13", "no dangling section-12 cross-reference", not dangling,
          f"references {sorted(refs)}; missing {dangling}")


    # G14 a bare "(section 12)" pointer must name the item it refers to
    bare = re.findall(r"\(\u00a712\s*\)", wp.replace("*", ""))
    check("G14", "no bare section-12 pointer (must cite 'section 12 item N')",
          not bare, f"{len(bare)} bare pointer(s)")
    m = re.search(r"L1-lite's own FSM is a gated open item \(\u00a7?12(?: item (\d+))?\)", wp)
    check("G14b", "the DMA L1-lite FSM open item is numbered",
          bool(m) and m.group(1) is not None,
          "" if m else "sentence not found")


    # G15 the network-invariant enumeration I1-I7 must name exactly seven
    #     properties, and the same set must appear in the WP and both diagrams.
    # G15 the network invariants I1-I7 must name exactly seven properties, and the
    #     same seven must be named in the WP and in both diagram files.
    INVARIANTS = {
        "XY path": ["XY path"],
        "VC equals class": ["class(flit.msg)", "VC equals class", "VC == class"],
        "credit invariant": ["credit invariant"],
        "no send at zero credit": ["zero credit", "zero-credit", "zero-credit stall"],
        "per-VC FIFO order": ["per-VC FIFO"],
        "delivery or termination": ["delivery or", "delivery-or", "delivery-or-termination"],
        "VC preservation": ["VC preservation", "VC index is preserved", "VC index preservation",
                            "VC is never rewritten", "never rewritten"],
        "inter-class edge ascent": ["ascend", "ascending"],
    }

    def names(text):
        t = text.replace("\u00a7", " ").replace("*", "")
        return {k for k, alts in INVARIANTS.items() if any(a in t for a in alts)}

    for pid, label, doc in (("G15a", "WP", wp), ("G15b", "4x4 diagram", l4), ("G15c", "2x2 diagram", l2)):
        got = names(doc)
        missing = sorted(set(INVARIANTS) - got)
        check(pid, f"{label} names all seven network invariants", not missing,
              f"missing {missing}")

    # the seven named properties must be the same set in all three documents
    check("G15d", "the invariant sets agree across WP and both diagrams",
          names(wp) == names(l4) == names(l2),
          f"wp={sorted(names(wp))}")

    # no number-only citation of an invariant that has no numbered definition
    check("G15e", "no invariant is cited by number without a numbered definition",
          not re.search(r"\bI[1-7]\b\s*\((?:XY|VC|credit|no |per-VC|delivery)", wp),
          "")


    # ============ GROUP H: P18 (network invariants) + P19 (work breakdown) ============
    if wb:
        # H1 fourteen item rows, and the document must claim fourteen
        rows = re.findall(r"^### \u00a716\.(\d+) ", wb, re.M)
        check("H1", "work breakdown has 14 item rows", [int(x) for x in rows] == list(range(1, 15)),
              f"rows {rows}")
        check("H1b", "work breakdown no longer claims 11 items",
              "11 \u00a716 items" not in wb and "14 \u00a716 items" in wb,
              "stale '11 items' claim" if "11 \u00a716 items" in wb else "")

        # H2 no mis-attributed assertion categories
        check("H2a", "no 'A4.x (directory FSM legality)' mis-attribution",
              "A4.x (directory FSM legality)" not in wb, "")
        check("H2b", "no 'A7.x (replacement determinism)' mis-attribution",
              "A7.x (replacement determinism)" not in wb, "")
        blk = re.search(r"### \u00a716\.10[\s\S]{0,1600}?\*\*SVA / formal\*\* \|([^|]*)\|", wb)
        check("H2c", "intra-tile path row cites a data-integrity assertion, not a router FIFO invariant",
              bool(blk) and "per-VC FIFO" not in blk.group(1) and "A6" in blk.group(1),
              "" if not blk else blk.group(1).strip()[:60])

        # H3 the circular dependency is gone
        m = re.search(r"### \u00a716\.1[\s\S]{0,1400}?\*\*Depends on\*\* \|([^|]*)\|", wb)
        check("H3", "16.1 does not depend on 16.2 (no circular dependency)",
              bool(m) and "16.2" not in m.group(1),
              "" if not m else m.group(1).strip()[:60])

        # H4 the assertion-coverage section names the uncovered items
        ok, d = contains(wb, "no direct assertion")
        check("H4", "work breakdown has an assertion-coverage statement", ok, d)
        for key in ("replacement determinism", "deferred eviction", "tile-ID", "exclusive bit"):
            ok, d = contains(wb.lower(), key.lower())
            check("H4b", f"coverage section names: {key}", ok, d)

        # H5 effort stated as a range
        ok, d = contains(wb, "15\u201318 days")
        check("H5", "effort total stated as a range (15-18 days)", ok, d)
        ok, d = contains(wb, "19\u201323 days")
        check("H5b", "DMA-inclusive effort stated as a range (19-23 days)", ok, d)

        # H6 assertion-dependent items are not all gated at Week 4
        wk4 = re.findall(r"\|\s*(?:§16\.\d+[^|]*)\|[^|]*\|[^|]*\|\s*Week 4\s*\|", wb)
        check("H6", "assertion-dependent items are not all gated at Week 4", len(wk4) < 6,
              f"{len(wk4)} rows still gated Week 4")

    # H7 the WP must define and number I1..I7
    numbered = re.findall(r"\bI([1-7])\b[\s:\u2013-]+([A-Za-z`][^;,.|]{4,60})", wp)
    check("H7", "WP numbers and names all seven network invariants",
          len({n for n, _ in numbered}) == 7,
          f"numbered: {sorted({n for n, _ in numbered})}")
    ok, d = contains(wp, "I6", "I7")
    check("H7b", "WP names I6 (VC preservation) and I7 (inter-class edge ascent)", ok, d)


    # ============ GROUP I: the 16.1 implementation slice must not diverge from the WP ============
    if sl:
        # I1 L1 forward transitions must match Appendix A
        for a in ("`E` | `FWD_GETS`", "`M` | `FWD_GETS`", "`E` | `FWD_GETM`", "`M` | `FWD_GETM`"):
            ok, d = contains(sl, a)
            check("I1", f"slice has the Appendix A forward transition: {a}", ok, d)
        for a in ("`EI_A`", "`MI_A`"):
            ok, d = contains(sl, a)
            check("I2", f"slice covers the defensive state {a}", ok, d)

        # I3 directory forward rows must match Appendix B
        for a in ("`DIR_FWD_WAIT` | `DATAFWD`", "`DIR_FWD_WAIT` | `PUTM (owner)`",
                  "`DIR_FWD_WAIT` | `PUTS (owner)`", "`DIR_FWD_WAIT` | `INVACK`",
                  "`DIR_E` | `PUTM (owner)`"):
            ok, d = contains(sl, a)
            check("I3", f"slice has the Appendix B row: {a}", ok, d)

        # I4 pending_op encoding must match the WP verbatim
        wp_enc = re.search(r"\| Pending op \| 3 b \|([^|]*)\|", wp)
        if wp_enc:
            codes = re.findall(r"\b\d{3} [A-Z_]+", wp_enc.group(1))
            ok, d = contains(sl, *codes)
            check("I4", "slice uses the WP's pending_op encoding", ok, d)

        # I5 assertion-category descriptions must match the WP's A1-A8 table
        a1 = re.search(r"\| A1 [^|]*\| 5 \|([^|]*)\|", wp)
        a3 = re.search(r"\| A3 [^|]*\| 6 \|([^|]*)\|", wp)
        check("I5a", "slice does not call A1 'directory state consistency'",
              "Directory state consistency" not in sl, "")
        check("I5b", "slice does not attribute 'owner in sharers' to A1.5",
              not re.search(r"A1\.5[^\n]{0,40}owner", sl, re.I), "")
        check("I5c", "slice does not describe A3.x as forward-path legality",
              "Forward-path legality" not in sl, "")
        # I5d A2.6 must be cited once in the A2 row (it was duplicated when owner-in-sharers moved)
        a2row = re.search(r"\| \*\*A2\.x\*\* \| 7 \|([^|]*)\|", sl)
        n26 = a2row.group(1).count("A2.6") if a2row else 0
        check("I5d", "the A2.x row cites A2.6 exactly once", n26 == 1, f"A2.6 appears {n26}x in the A2 row")
        # I5e the FSM-legality content belongs to A7.x, not A3.x
        a3row = re.search(r"\| \*\*A3\.x\*\* \| 6 \|([^|]*)\|", sl)
        a7row = re.search(r"\| \*\*A7\.x\*\* \| 4 \|([^|]*)\|", sl)
        check("I5e", "the A3.x row carries no FSM-legality content",
              bool(a3row) and "single-exit" not in a3row.group(1) and "pending_op" not in a3row.group(1), "")
        check("I5f", "the A7.x row carries the DIR_FWD_WAIT single-exit content",
              bool(a7row) and ("single-exit" in a7row.group(1) or "exactly one exit" in a7row.group(1)), "")
        # I5g the A1 row must keep the A1.2 'at most one L1 in E' clause
        a1row = re.search(r"\| \*\*A1\.x\*\* \| 5 \|([^|]*)\|", sl)
        check("I5g", "the A1.x row keeps the 'at most one in E' clause (A1.2)",
              bool(a1row) and "one in E" in a1row.group(1), "")
        # I5h the deferral must cite Appendix B - WP rule 9 is the exclusive bit, rule 10 deferred eviction
        # scoped to the shadow rules only: the WP's own headings may legitimately cite rule 9/10
        _rules_i5h = re.findall(r"^\d+\.\s+On [^\n]*$", sl, re.M)
        check("I5h", "the shadow deferral cites Appendix B, not WP rule 9/rule 10",
              not any(re.search(r"\(rule (9|10)\)", r) for r in _rules_i5h),
              "")
        check("I5i", "the shadow rules label their internal cross-references 'shadow rule'",
              bool(re.search(r"\(shadow rule \d+", sl, re.I)), "")

        # I6 the DATAFWD dirty indication is header bit [39], never the exclusive bit
        check("I6", "slice does not call the DATAFWD dirty flag the exclusive bit",
              not re.search(r"DATAFWD[^\n]{0,80}excl bit", sl, re.I)
              and not re.search(r"excl bit (clear|set)\)", sl), "")

        # I7 the shadow rules must cover the requester's install on DATA
        rules = re.findall(r"^\d+\.\s+On [^\n]*$", sl, re.M)
        check("I7", "the shadow-rule list has a rule for DATA arriving at the requester",
              any(re.match(r"^\d+\.\s+On\s+`?DATA`?\b", r, re.I) for r in rules),
              f"{len(rules)} shadow rules; none starts with 'On DATA'")
        check("I7b", "a shadow rule covers UNBLOCK selecting the successor",
              any("UNBLOCK" in r for r in rules), "")
        # the Owner/sharer update commits on the UNBLOCK exit (WP Appendix B), so the
        # shadow must set the sharer bits there - not at the forward entry
        unblock_gets = [r for r in rules if "UNBLOCK" in r and "GETS" in r]
        check("I7c", "the sharer update is committed on the UNBLOCK exit, not at the forward entry",
              bool(unblock_gets) and "sharer" in unblock_gets[0].lower(),
              "" if not unblock_gets else unblock_gets[0][:70])

        # I8 the test plan and exit criteria
        ok, d = contains(sl, "F1", "F5", "F9")
        check("I8a", "slice has a directed test plan F1-F9", ok, d)
        ok, d = contains(sl, "verify_patch_set.py")
        check("I8b", "exit criteria require running verify_patch_set.py", ok, d)
        ok, d = contains(sl, "Reference model", "SVA", "RTL")
        check("I8c", "exit criteria cover RTL + SVA + reference model", ok, d)

        # I9 the deferred-eviction rule and the exclusive-bit rule must be stated
        ok, d = contains(sl, "deferred")
        check("I9", "slice states the deferred-eviction rule (rule 10)", ok, d)
        ok, d = contains(sl, "excl = 1", "excl = 0")
        check("I9b", "slice states the exclusive-bit rule (rule 9)", ok, d)

    # ---------------- self-consistency: the stated check count must equal the count actually run
    # (this closes the propagation class for the verifier count itself: the breakdown and the
    #  slice quote a number; if the verifier grows, these fail until the prose is updated)
    if wb:
        stated_all = [int(x) for x in re.findall(r"(\d+)[- ]checks?\b", wb)]
        exp1 = len(results) + 2
        check("J1", "every count the breakdown quotes for the verifier equals the count actually run",
              bool(stated_all) and all(x == exp1 for x in stated_all),
              f"breakdown quotes {stated_all}; verifier runs {exp1}")
    if sl:
        m_cnt2 = re.search(r"reports\s+(\d+)\s*/\s*(\d+)", sl)
        stated2 = int(m_cnt2.group(2)) if m_cnt2 else None
        exp2 = len(results) + 1
        check("J2", "the count the slice's exit criteria quote equals the count actually run",
              stated2 == exp2,
              f"slice quotes {stated2}; verifier runs {exp2}")

    # ---------------- report ----------------------------------------
    print()
    width = max(len(d) for _, d, _, _ in results) + 2
    npass = sum(1 for _, _, ok, _ in results if ok)
    for pid, desc, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {pid:<6} {desc:<{width}} {detail}")
    print(f"\n{npass}/{len(results)} checks passed")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
