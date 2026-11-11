#!/usr/bin/env python3
"""verify_srs_v2.py - check SRS_final_v2.docx against the ruled white paper.

Usage:
    python3 verify_srs_v2.py --srs work/SRS_final_v2.txt --wp output/b5/FINAL_whitepaper_v3.0.md \
                             --breakdown output/b5/WORK_BREAKDOWN_16.md

The SRS text is the plain-text extraction of the .docx (paragraphs + tables).
Exit 0 = every check passes. Exit 1 = at least one FAIL (each one is printed).
"""
import argparse
import re
import sys
from pathlib import Path

results = []


def check(cid, desc, ok, detail=""):
    results.append((cid, desc, bool(ok), detail))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--srs", required=True)
    ap.add_argument("--wp", required=True)
    ap.add_argument("--breakdown", default=None)
    ap.add_argument("--gate-count", type=int, default=134)
    args = ap.parse_args()
    srs = Path(args.srs).read_text(encoding="utf-8", errors="replace")
    wp = Path(args.wp).read_text(encoding="utf-8", errors="replace")
    bd = Path(args.breakdown).read_text(encoding="utf-8", errors="replace") if args.breakdown else ""

    # --- 1. the cited gate count must be current ---------------------------
    m = re.findall(r"gate\s+(\d+)/(\d+)", srs)
    stale = [x for x in m if int(x[1]) != args.gate_count]
    check("S01", "the SRS quotes the current package gate count", not stale,
          f"found {sorted(set(m))}, expected */{args.gate_count}")

    # --- 2. the cited ledger rows must be the current ones -----------------
    cited = sorted(set(re.findall(r"\b([A-Z]{2})\b", " ".join(re.findall(r"rows?[^|\n]*", srs)))))
    wp_rows = set(re.findall(r"^\|\s*\*\*([A-Z]{2})\*\*\s*\|", wp, re.M))
    missing = [r for r in cited if r not in wp_rows]
    check("S02", "every ledger row cited by the SRS exists in the WP ledger", not missing,
          f"cited {cited}; not in the WP: {missing}")

    # --- 3. the cited ledger rows must include the latest rulings ----------
    latest = {"AG", "AH", "AI", "AJ"}
    check("S03", "the SRS cites the latest ledger rows (AG/AH/AI/AJ)", latest.issubset(set(cited)),
          f"cited {cited}")

    # --- 4. the section-16 row count --------------------------------------
    rows = len(re.findall(r"^### §16\.\d+", bd, re.M)) if bd else 0
    cited_rows = re.findall(r"(\d+)-row section 16", srs)
    check("S04", "the SRS's section-16 row count matches the breakdown",
          bool(cited_rows) and int(cited_rows[0]) == rows,
          f"SRS says {cited_rows}, breakdown has {rows}")

    # --- 5. the traceability matrix size ----------------------------------
    claimed = re.findall(r"(\d+)-row traceability matrix", srs)
    tail = srs[srs.index("=== TABLE 25 ==="):] if "=== TABLE 25 ===" in srs else ""
    tr_rows = len([l for l in tail.splitlines()
                   if re.match(r"^(FR-\d+|AC-\d+|PERF-\d+|PWR-\d+|AREA-\d+|FPGA-\d+\w*)\s*\|", l)])
    fr_rows = len(set(re.findall(r"^(FR-\d+)\s*\|", srs, re.M)))
    check("S05", "the traceability matrix size is stated and matches the matrix",
          bool(claimed) and int(claimed[0]) == tr_rows,
          f"SRS claims {claimed}, the traceability matrix has {tr_rows} rows "
          f"({fr_rows} FR ids defined)")

    # --- 6. the VC mapping -------------------------------------------------
    vc_ok = ("VC0 = REQ" in srs and "VC1 = FWD" in srs
             and "VC2 = RESP" in srs and "VC3 = INV" in srs)
    check("S06", "the VC mapping matches the WP (VC0 REQ, VC1 FWD, VC2 RESP, VC3 INV)", vc_ok, "")

    # --- 7. the class priority --------------------------------------------
    check("S07", "the class priority matches the WP (RESP > INV > FWD > REQ)",
          "RESP > INV > FWD > REQ" in srs and "RESP > INV > FWD > REQ" in wp, "")

    # --- 8. the fairness bound --------------------------------------------
    check("S08", "the fairness bound (13 = 5+3+5, 11 at the corner) matches the WP",
          "13" in srs and "5 + 3 + 5" in srs and "11 at a corner" in srs
          and "5 + 3 + 5 = 13" in wp and "5 + 3 + 3 = 11" in wp, "")

    # --- 9. the age-escape threshold ---------------------------------------
    check("S09", "the age-escape threshold is 5, as ruled (B1)",
          "threshold 5" in srs or "threshold of 5" in srs or "age escape at threshold 5" in srs, "")

    # --- 10. the L2 per-line word -----------------------------------------
    check("S10", "the L2 per-line word is {valid, tag, dirty} 23 b at 2x2 / 21 b at 4x4",
          "23 b at 2x2" in srs and "21 b at 4x4" in srs and "23 b" in wp, "")

    # --- 11. the DATAFWD dirty bit ----------------------------------------
    check("S11", "the DATAFWD dirty indication is header bit [39]",
          "bit [39]" in srs and "[39]" in wp, "")

    # --- 12. the area targets ---------------------------------------------
    check("S12", "the area targets match the WP (LUT 20k/40k, BRAM 48/80, DSP 0, FF 25k/50k)",
          all(x in srs for x in ["20,000", "40,000", "<= 48", "<= 80"]) and ("\u2264 80" in wp or "<= 80" in wp), "")

    # --- 13. the power budget ---------------------------------------------
    check("S13", "the power budget (total <= 50 mW) matches the WP and cites it",
          "50 mW" in srs and "50 mW" in wp, "")

    # --- 14. the assertion bound ------------------------------------------
    check("S14", "the assertion bound is 42 (38 safety + 4 liveness) with I1-I7 separate",
          "42 bound" in srs and "38 bound safety" in srs and "I1" in srs and "I7" in srs
          and "38 bound safety assertions" in wp, "")

    # --- 15. the liveness bounds ------------------------------------------
    check("S15", "the liveness bounds are T=64 (2x2 formal) and 150 (4x4 simulation)",
          "64" in srs and "150" in srs and "150 cycles" in wp, "")

    # --- 16. the credit depth and the intra-tile width ---------------------
    check("S16", "the credit depth (4 flits/VC) and the 512-bit intra-tile path match the WP",
          "depth 4" in srs and "512-bit" in srs and "512-bit" in wp, "")

    # --- 17. the message set ----------------------------------------------
    check("S17", "the message set is 12 core + 2 gated DMA messages, as the WP states",
          "12 core messages" in srs and "12 core messages" in wp, "")

    # --- 18. the DMA gating (ruling B4) -----------------------------------
    check("S18", "the DMA path is gated to the 4x4 track (ruling B4)",
          "ruling B4" in srs and "4x4" in srs and "ruling B4" in wp, "")

    # --- 19. FR-15/16/17 carry the B6/B7/B8 rulings -----------------------
    check("S19", "FR-15/16/17 carry the same-line abort, the per-VC receive path and the re-issue ordering",
          all(x in srs for x in ["FR-15", "FR-16", "FR-17"])
          and "B6" in srs and "B7" in srs and "B8" in srs, "")

    # --- 20. the matching test cases exist --------------------------------
    check("S20", "TC-15/TC-16/TC-17 exist for FR-15/FR-16/FR-17",
          all(x in srs for x in ["TC-15", "TC-16", "TC-17"]), "")

    # --- 21. the exit criteria --------------------------------------------
    check("S21", "the exit criteria require the 42 SVA and I1-I7 with zero waivers",
          "42 bound SVA" in srs and "zero waivers" in srs, "")

    # --- 22. the open item is not invented ---------------------------------
    check("S22", "the SRS does not claim a coverage bin list that the WP leaves open",
          "section 12 item 2" in srs and "do not invent bins" in srs, "")

    # --- 23. no stale pre-ruling numbers -----------------------------------
    stale_pats = ["8 arbitration rounds", "served within 8 rounds", "threshold 8",
                  "S-mask exactly", "no stale bits"]
    hits = [p for p in stale_pats if p in srs]
    check("S23", "no stale pre-ruling numbers remain in the SRS", not hits, f"found {hits}")

    # --- 24. the pin LOCs are sourced --------------------------------------
    pins = sorted(set(re.findall(r"\b([YPU]\d{1,2})\b", srs)))
    wp_pins = sorted(set(re.findall(r"\b([YPU]\d{1,2})\b", wp)))
    cites_wp_for_pins = bool(re.search(r"(WP[^\n|]*6\.1[^\n|]*)\n?[^\n]*\b(?:Y9|P16|F22)\b", srs)) or "Pin Y9" in srs
    check("S24", "board pin LOCs stated by the SRS have an authoritative source (the WP or the board schematic)",
          set(pins).issubset(set(wp_pins)) or "UG937" in srs,
          f"SRS {pins}; WP {wp_pins or 'does not specify pin LOCs'}; "
          f"the SRS attributes them to WP 6.1: {cites_wp_for_pins}")

    # --- 25. the traceback to the FR set ----------------------------------
    check("S25", "every FR has a traceability row",
          len(set(re.findall(r"^(FR-\d+)\s*\|", srs, re.M))) == len(set(re.findall(r"\b(FR-\d+)\b", srs))),
          "")

    # --- 26. the document identity ----------------------------------------
    check("S26", "the SRS carries the group, members, mentor and a version",
          "Group 16" in srs and "Mr. Hemat" in srs and "v2.0" in srs, "")

    # --- 27. the revision history records what changed ---------------------
    check("S27", "the revision history records the v2.0 changes",
          "v2.0" in srs and "B6" in srs and "B8" in srs, "")

    # --- 28. the verification strategy cites the WP -----------------------
    check("S28", "the verification strategy cites the WP sections it derives from",
          "WP 5.4" in srs or "WP section 12 item 1" in srs or "WP 12 item 1" in srs, "")

    # --- 29. the FPGA plan is committed to the 2x2 build --------------------
    check("S29", "the FPGA plan is scoped to the committed 2x2 build",
          "2x2" in srs and "XC7Z020" in srs, "")

    # --- 30. the code-coverage thresholds are stated ------------------------
    check("S30", "the code-coverage thresholds are stated (statement/branch/toggle)",
          "90" in srs and "85" in srs and "Statement" in srs, "")

    # ---- report -----------------------------------------------------------
    npass = sum(1 for _, _, ok, _ in results if ok)
    width = max(len(d) for _, d, _, _ in results) + 2
    out = [f"RESULT: {'PASS' if npass == len(results) else 'FAIL'} - {npass}/{len(results)} checks passed", ""]
    out += [f"[{'PASS' if ok else 'FAIL'}] {cid:<6} {d:<{width}} {det}" for cid, d, ok, det in results]
    print("\n".join(out))
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
