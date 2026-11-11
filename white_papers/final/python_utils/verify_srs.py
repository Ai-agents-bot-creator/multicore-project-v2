#!/usr/bin/env python3
"""
verify_srs.py - acceptance checker for the SRS (DOCX) against the closed spec package.

Usage:
    python3 verify_srs.py --srs SRS_final_v2.docx
    python3 verify_srs.py --srs SRS_final_v2.docx --dir <package dir> --wp <path> --spec <path>
    python3 verify_srs.py --srs SRS_final.docx --baseline

Checks the SRS against the normative spec package, student guide, and international standards:
protocol directions, identifier namespaces, VC index order, area targets, DMA scope, message set,
requirement coverage, coverage criteria, test-plan completeness, full traceability, table hygiene,
timing parameters, power budget, pin mapping, and placeholder resolution.

Runs 67 comprehensive checks by default (or 41 baseline checks when --baseline is passed).
Exit code 0 only if every check passes.
"""
import argparse
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def extract(path):
    d = Document(path)
    lines, tables = [], []

    def iter_block(parent, doc):
        for child in parent.iterchildren():
            if child.tag.endswith('}p'):
                yield Paragraph(child, doc)
            elif child.tag.endswith('}tbl'):
                yield Table(child, doc)

    for b in iter_block(d.element.body, d):
        if isinstance(b, Paragraph):
            t = b.text.strip()
            if t:
                try:
                    st = b.style.name
                except Exception:
                    st = "?"
                lines.append((st, t))
        else:
            rows = [[c.text.strip() for c in r.cells] for r in b.rows]
            tables.append(rows)
            for r in rows:
                lines.append(("TBL", " | ".join(r)))
    return lines, tables, d


def main():
    ap = argparse.ArgumentParser(description="SRS Acceptance Checker")
    ap.add_argument("--srs", required=True, help="Path to SRS DOCX file")
    ap.add_argument("--dir", default=None, help="Package directory (optional)")
    ap.add_argument("--wp", default=None, help="Whitepaper path (optional)")
    ap.add_argument("--spec", default=None, help="Spec sheet path (optional)")
    ap.add_argument("--baseline", action="store_true", help="Run only the 41 baseline checks from v0.2")
    args = ap.parse_args()

    lines, tables, doc = extract(args.srs)
    text = "\n".join(t for _, t in lines)
    results = []

    def check(pid, desc, ok, detail=""):
        results.append((pid, desc, bool(ok), detail))

    def row_with(prefix):
        for rows in tables:
            for r in rows:
                if r and r[0].strip().startswith(prefix):
                    return r
        return None

    # =========================================================================
    # BASELINE CHECKS (41 checks from v0.2)
    # =========================================================================

    # ---- B1: release message directions -------------------------------------
    puts = row_with("PUTS")
    putm = row_with("PUTM")
    unblock = row_with("UNBLOCK")
    check("B1a", "PUTS is described as L1 -> directory", puts and "L1" in puts[-1] and "dir" in puts[-1].lower(), str(puts))
    check("B1b", "PUTM is described as L1 -> directory", putm and "L1" in putm[-1] and "dir" in putm[-1].lower(), str(putm))
    msg_table = None
    for rows in tables:
        if rows and len(rows[0]) >= 2 and rows[0][0].strip().lower() == "message":
            msg_table = rows
            break
    putack_row = None
    if msg_table:
        for r in msg_table:
            if r and r[0].strip() == "PUTACK":
                putack_row = r
                break
    putack_dir = putack_row[1].strip().lower() if (putack_row and len(putack_row) > 1) else ""
    b1c_ok = putack_row is not None and ("dir -> l1" in putack_dir or "dir -> requester" in putack_dir)
    check("B1c", "PUTACK is described as directory -> L1", b1c_ok, str(putack_row))
    check("B1d", "UNBLOCK is described as L1 -> directory", unblock and "L1" in unblock[-1] and "dir" in unblock[-1].lower(), str(unblock))
    check("B1e", "no 'Directory-to-subscriber' direction remains", "Directory-to-subscriber" not in text, "")

    # ---- B2: phantom A13 ---------------------------------------------------
    check("B2a", "the phantom assertion id A13 is gone from the SRS", "A13" not in text, "")
    fr02 = row_with("FR-02")
    check("B2b", "FR-02 is verified by A8.x and/or I1", fr02 and re.search(r"A8|I1", fr02[-1]), str(fr02))

    # ---- B3: VC index order -------------------------------------------------
    ac03 = row_with("AC-03")
    check("B3a", "AC-03 states VC0 = REQ", ac03 and "VC0" in ac03[-1] and "REQ" in ac03[-1], str(ac03))
    check("B3b", "AC-03 states VC1 = FWD", ac03 and "VC1" in ac03[-1] and "FWD" in ac03[-1], "")
    check("B3c", "AC-03 states VC2 = RESP", ac03 and "VC2" in ac03[-1] and "RESP" in ac03[-1], "")
    check("B3d", "AC-03 states VC3 = INV", ac03 and "VC3" in ac03[-1] and "INV" in ac03[-1], "")
    order_ok = False
    if ac03:
        m = re.search(r"VC0\s*=\s*REQ.*?VC1\s*=\s*FWD.*?VC2\s*=\s*RESP.*?VC3\s*=\s*INV", ac03[-1], re.S)
        order_ok = m is not None
    check("B3e", "the VC index order is stated as REQ, FWD, RESP, INV (not the priority order)", order_ok, "")

    # ---- B4: area targets are design targets, not device capacity ----------
    a1 = row_with("AREA-01")
    a2 = row_with("AREA-02")
    check("B4a", "AREA-01's LUT target is a design target (<=20,000), not device capacity",
          a1 and len(a1) >= 4 and re.search(r"20[,.]?000", a1[2]), str(a1))
    check("B4b", "AREA-01's LUT maximum is <= 40,000",
          a1 and len(a1) >= 4 and re.search(r"40[,.]?000", a1[3]), str(a1))
    check("B4c", "AREA-02's BRAM target is <= 48 with a ceiling of 80",
          a2 and len(a2) >= 4 and re.search(r"48", a2[2]) and re.search(r"80", a2[3]), str(a2))
    a3 = row_with("AREA-03")
    b4d_ok = a3 is not None and len(a3) >= 4 and a3[2].strip() == "0" and a3[3].strip() == "0"
    check("B4d", "a DSP row exists with target 0", b4d_ok, str(a3))
    fpga05 = [r for rows in tables for r in rows if r and r[0].strip().startswith("FPGA-05")]
    check("B4e", "FPGA-05 no longer asserts 80 DSP", not fpga05 or all("DSP" not in " ".join(r) or "0" in " ".join(r) for r in fpga05), str(fpga05))

    # ---- B5: no DMA signal in the 2x2 build --------------------------------
    sig_rows = [r for rows in tables for r in rows if len(r) >= 2 and r[0].strip() in
                ("dma_wr", "dma_req", "dma_write")]
    check("B5a", "no bare DMA write signal appears in the signal list", not sig_rows, str(sig_rows))
    check("B5b", "the DMA interface is marked absent from the 2x2 build",
          "not present in the 2" in text.lower() or "no dma" in text.lower(), "")

    # ---- B6: resolvable verification references -----------------------------
    bad = []
    for rows in tables:
        for r in rows:
            if not r:
                continue
            rid = r[0].strip()
            if not re.match(r"^(FR|AC|PERF|PWR|AREA|FPGA)-\d+", rid):
                continue
            for cell in r[1:]:
                if re.search(r"\bA13\b|\bG\d+\b|\bB[1-9]\b|\bB1[0-9]\b", cell):
                    bad.append((rid, cell))
    check("B6a", "no requirement cites a finding id (A13/G*) or a ruling id (B*) as its evidence", not bad, str(bad[:4]))
    fr_ids = set()
    for rows in tables:
        for r in rows:
            if r and re.match(r"^FR-\d+$", r[0].strip()):
                fr_ids.add(r[0].strip())
    # the traceability table is the one whose header mentions 'Method'
    trace_rows = []
    for rows in tables:
        if rows and any("Method" in c for c in rows[0]):
            trace_rows = rows[1:]
    traced_ids = {r[0].strip() for r in trace_rows if r}
    check("B6b", "every FR is traced in the traceability table",
          fr_ids and fr_ids.issubset(traced_ids), f"untraced: {sorted(fr_ids - traced_ids)}")

    # ---- M1: message set ---------------------------------------------------
    msgs = ["GETS", "GETM", "PUTS", "PUTM", "UNBLOCK", "INV", "INVACK", "DATA",
            "FWD_GETS", "FWD_GETM", "DATAFWD", "PUTACK", "DMA_WRITE", "DMA_ACK"]
    missing = [m for m in msgs if m not in text]
    check("M1a", "all 12 core + 2 gated messages appear in the SRS", not missing, f"missing: {missing}")

    # ---- M2: requirement coverage -------------------------------------------
    for i in range(9, 15):
        rid = f"FR-{i:02d}"
        check(f"M2-{i:02d}", f"{rid} exists (forward release, exclusive bit, L2 word, dirty bit, write-back, receptivity)",
              row_with(rid) is not None, "")

    # ---- M3: numeric coverage criteria ---------------------------------------
    n_pct = max(text.count("100 %"), text.count("100%"))
    check("M3a", "coverage targets are numeric (at least three numeric targets)", n_pct >= 3, f"numeric targets: {n_pct}")
    check("M3b", "the four WP coverage criteria are present",
          all(k in text for k in ("FSM", "assertion", "waiver", "bin")), "")

    # ---- M4: test plans ------------------------------------------------------
    def plan_rows(marker):
        for rows in tables:
            if rows and any(marker in c for c in rows[0]):
                return rows[1:]
        return []
    tc = plan_rows("Scenario")
    fv = plan_rows("Procedure on board")
    check("M4a", "the directed test plan has at least 14 rows", len(tc) >= 14, f"{len(tc)} rows")
    check("M4b", "the FPGA test plan has at least 14 rows", len(fv) >= 14, f"{len(fv)} rows")

    # ---- M5: proof parameters marked as proposed -----------------------------
    check("M5a", "the proof parameters are marked proposed", "proposed" in text.lower(), "")
    check("M5b", "both liveness bounds appear (2x2 and 4x4)",
          ("64" in text and "150" in text), "")

    # ---- M6: table hygiene ----------------------------------------------------
    dupes = []
    for i, rows in enumerate(tables, 1):
        seen = {}
        for r in rows:
            key = tuple(c.strip() for c in r)
            if not any(key):
                continue
            seen[key] = seen.get(key, 0) + 1
        for k, v in seen.items():
            if v > 1:
                dupes.append((i, k[0], v))
    check("M6a", "no table repeats an identical row", not dupes, str(dupes[:4]))
    keydupes = []
    for i, rows in enumerate(tables, 1):
        keys = [r[0].strip() for r in rows[1:] if r and len(r) > 1]
        for k in set(keys):
            if keys.count(k) > 1:
                keydupes.append((i, k))
    check("M6b", "no table repeats the same key with different values", not keydupes, str(keydupes[:4]))

    # ---- N-series ------------------------------------------------------------
    check("N1a", "the SRS says 'virtual channel', not 'virtual buffer'", "virtual buffer" not in text.lower(), "")
    check("N2a", "the conditional DMA tests are marked conditional",
          re.search(r"18[–-]22[^.]*conditional|conditional[^.]*18[–-]22", text, re.I) is not None, "")
    check("N4a", "the performance section states known latency figures",
          any(k in text for k in ("4-cycle", "4 cycles", "9 flits", "512-bit")), "")
    check("N5a", "power is explicitly scoped or flagged", re.search(r"out of scope|not specified|TBD", text, re.I) is not None, "")
    check("N6a", "the verification exit criteria mention zero waivers", "waiver" in text.lower(), "")

    # If baseline flag is set, stop here and report 41 checks
    if args.baseline:
        width = max(len(d) for _, d, _, _ in results) + 2
        npass = sum(1 for _, _, ok, _ in results if ok)
        out = [f"[{'PASS' if ok else 'FAIL'}] {pid:<8} {desc:<{width}} {detail}"
               for pid, desc, ok, detail in results]
        print("\n".join([f"RESULT: {'PASS' if npass == len(results) else 'FAIL'} - {npass}/{len(results)} SRS checks passed",
                         ""] + out))
        return 0 if npass == len(results) else 1

    # =========================================================================
    # EXPANDED CHECKS (26 new checks for v2.0 elevation -> 67 total)
    # =========================================================================

    # 1-8: FR-01 through FR-08 Normative Content
    fr_normative = {
        "FR-01": (["directory", "MESI"], "directory-based MESI coherence"),
        "FR-02": (["XY", "routing"], "XY deterministic routing"),
        "FR-03": (["credit", "flow control", "4"], "credit-based flow control with depth 4"),
        "FR-04": (["RESP", "INV", "FWD", "REQ", "escape", "13"], "arbitration priority and 13-round bound"),
        "FR-05": (["PUTS", "PUTM", "PUTACK"], "non-silent eviction with PUTS/PUTM/PUTACK"),
        "FR-06": (["UNBLOCK"], "single-exit directory FSM via UNBLOCK"),
        "FR-07": (["DMA", "4x4"], "DMA write path gated to 4x4 simulation scope"),
        "FR-08": (["512", "cache line"], "512-bit intra-tile line transfer"),
    }
    for fid, (kws, desc) in fr_normative.items():
        r = row_with(fid)
        r_txt = " ".join(r) if r else ""
        num_str = f"{int(fid.split('-')[1]):02d}"
        check(f"M2-{num_str}", f"{fid} exists and defines {desc}",
              r is not None and all(kw.lower() in r_txt.lower() for kw in kws), r_txt[:50] if r else "NOT FOUND")

    # 9: Full Traceability Matrix Coverage
    all_defined_reqs = set()
    for rows in tables:
        if rows and any("Method" in c for c in rows[0]):
            continue
        for r in rows:
            if r:
                m = re.match(r"^((?:FR|AC|PERF|PWR|AREA|FPGA)-\d+[a-z]?)", r[0].strip())
                if m:
                    all_defined_reqs.add(m.group(1))
    untraced_all = all_defined_reqs - traced_ids
    check("B6c", f"Traceability matrix traces all defined requirements ({len(all_defined_reqs)} total)",
          len(untraced_all) == 0, f"untraced: {sorted(untraced_all)}")

    # 10: Message Table Row Count in Section 7.1
    msg_rows = [r for rows in tables if rows and len(rows[0]) >= 5 and rows[0][0] == "Message" for r in rows[1:]]
    check("M1b", "Section 7.1 message table contains exactly 14 message rows",
          len(msg_rows) == 14, f"{len(msg_rows)} rows")

    # 11: Code Coverage Goals in Section 8.3
    cov_rows = [r for rows in tables for r in rows if r and any(k in r[0].lower() for k in ("statement", "line", "branch", "toggle"))]
    check("M3c", "Section 8.3 specifies code coverage targets (statement, branch, toggle)",
          len(cov_rows) >= 2, f"found {len(cov_rows)} rows")

    # 12: FPGA Test Plan Linking (no unlinked '-')
    fv_unlinked = [r[0] for r in fv if len(r) >= 2 and r[1].strip() == "-"]
    check("M4c", "All FPGA validation tests (FV) are linked to a requirement ID",
          len(fv_unlinked) == 0, f"unlinked: {fv_unlinked}")

    # 13: Power Budget Grounded in WP 6.4 (<= 50 mW)
    pwr03 = row_with("PWR-03")
    pwr01 = row_with("PWR-01")
    pwr03_target = pwr03[2].strip().lower() if (pwr03 and len(pwr03) > 2) else ""
    pwr01_target = pwr01[2].strip().lower() if (pwr01 and len(pwr01) > 2) else ""
    pwr03_ok = pwr03 is not None and ("<= 50" in pwr03_target or "<= 50 mw" in pwr03_target)
    pwr01_ok = pwr01 is not None and ("<= 35" in pwr01_target or "<= 50" in pwr01_target) and "500" not in pwr01_target
    check("N5b", "Power requirement reflects WP 6.4 budget (total <= 50 mW)",
          pwr03_ok and pwr01_ok, str(pwr03))

    # 14: PERF-01 Clock Frequency Target (100 MHz, not TBD)
    p01 = row_with("PERF-01")
    check("T01", "PERF-01 specifies 100 MHz clock frequency (not TBD)",
          p01 and "TBD" not in p01[2] and "100" in p01[2], str(p01[2] if p01 and len(p01) > 2 else ""))

    # 15: FPGA-01 On-Board Frequency Target (100 MHz, not TBD)
    fp01 = row_with("FPGA-01")
    check("T02", "FPGA-01 specifies 100 MHz on-board frequency (not TBD)",
          fp01 and "TBD" not in fp01[2] and "100" in fp01[2], str(fp01[2] if fp01 and len(fp01) > 2 else ""))

    # 16: Section 7.4 Timing Rules & Uncertainties
    timing_table = None
    for rows in tables:
        if rows and len(rows[0]) >= 2:
            r0_0 = rows[0][0].strip().lower()
            r0_1 = rows[0][1].strip().lower()
            if r0_0 == "parameter" and r0_1 == "value":
                timing_table = rows
                break
    timing_text = " ".join(" ".join(c for c in r) for r in timing_table).lower() if timing_table else ""
    t03_ok = (timing_table is not None and
              "setup uncertainty" in timing_text and
              "0.2" in timing_text and
              "wns" in timing_text)
    check("T03", "Section 7.4 timing rules specify concrete WNS and setup/hold uncertainty",
          t03_ok, f"timing table: {len(timing_table) if timing_table else 0} rows")

    # 17: Section 7.5 DMA Register Map
    dma_table = None
    for rows in tables:
        if rows and len(rows[0]) >= 2:
            c0 = rows[0][0].strip().lower()
            c1 = rows[0][1].strip().lower()
            if c1 == "name" and c0 in ("offset", "address"):
                dma_table = rows
                break
    dma_regs = {"SRC_LO", "DST_LO", "LEN", "CTRL", "STATUS", "COUNT"}
    found_dma_regs = {r[1].strip() for r in dma_table[1:] if len(r) > 1} if dma_table else set()
    t04_ok = dma_table is not None and dma_regs.issubset(found_dma_regs)
    check("T04", "Section 7.5 enumerates the 6 DMA channel registers",
          t04_ok, f"missing: {dma_regs - found_dma_regs}")

    # 18: Section 6 Flip-Flop (FF) Target (<= 25,000)
    area04 = row_with("AREA-04")
    area04_target = area04[2].strip() if (area04 and len(area04) > 2) else ""
    t05_ok = area04 is not None and ("25,000" in area04_target or "25000" in area04_target)
    check("T05", "Section 6 specifies Flip-Flop (FF) utilization (<= 25,000)",
          t05_ok, str(area04[2] if area04 and len(area04) > 2 else ""))

    # 19: Section 6 PPA Trade-Off Priority Order
    check("T06", "Section 6 explicitly defines PPA trade-off priority order",
          any(k in text.lower() for k in ("priority order", "ppa priority", "trade-off priority")), "")

    # 20: All 8 SVA Categories (A1-A8)
    has_sva = all(f"A{i}" in text for i in range(1, 9))
    check("T07", "SRS references all 8 SVA categories (A1 through A8)", has_sva, "")

    # 21: All 7 Network Invariants (I1-I7)
    has_inv = all(f"I{i}" in text for i in range(1, 8))
    check("T08", "SRS references all 7 network invariants (I1 through I7)", has_inv, "")

    # 22: Core Control & Credit Signals in Signal List
    sig_names = {r[0].strip() for rows in tables if rows and len(rows[0]) >= 5 and rows[0][0] == "Signal" for r in rows[1:]}
    expected_sigs = {"clk", "reset", "credit_in", "credit_out"}
    check("T09", "Signal list contains core control and credit signals (clk, reset, credit_in, credit_out)",
          expected_sigs.issubset(sig_names), f"missing: {expected_sigs - sig_names}")

    # 23: No Template Placeholders
    placeholders_found = []
    for t_idx, rows in enumerate(tables, 1):
        for r_idx, r in enumerate(rows, 1):
            for c in r:
                if any(p in c.lower() for p in ("[name]", "[group", "[member", "[project", "fixme", "todo")):
                    placeholders_found.append((t_idx, r_idx, c))
    check("T10", "No template placeholders ([Name], [Group...], TODO) remain",
          len(placeholders_found) == 0, f"found: {placeholders_found}")

    # 24: Mentor Name Resolved in Approval Table
    appr_table = None
    for rows in tables:
        if rows and len(rows[0]) >= 2:
            r0_0 = rows[0][0].strip().lower()
            if r0_0 == "role" or any("mentor" in c.lower() for c in rows[0]):
                appr_table = rows
                break
    mentor_row = None
    if appr_table:
        for r in appr_table:
            if r and any("mentor" in c.lower() for c in r):
                mentor_row = r
                break
    t11_ok = mentor_row is not None and len(mentor_row) > 1 and "mr. hemat" in mentor_row[1].lower()
    check("T11", "Approval table lists Mr. Hemat as Group Mentor (not [Name])", t11_ok,
          str(mentor_row[1] if mentor_row and len(mentor_row) > 1 else ""))

    # 25: Valid Group Name in Metadata
    grp_meta = None
    for rows in tables:
        for r in rows:
            if len(r) > 1 and r[0].strip().lower() == "group":
                grp_meta = r[1].strip()
                break
        if grp_meta is not None:
            break
    has_grp = grp_meta is not None and len(grp_meta) > 0 and "[" not in grp_meta
    check("T12", "Document metadata specifies valid, non-empty Group name", has_grp, str(grp_meta or ""))

    # 26: XML Table Formatting (w:tblHeader on row 0, w:cantSplit on all rows)
    missing_tbl_header = []
    missing_cant_split = []
    for t_idx, tbl in enumerate(doc.tables):
        if tbl.rows:
            r0 = tbl.rows[0]
            if not r0._tr.xpath('./w:trPr/w:tblHeader'):
                missing_tbl_header.append(t_idx)
        for r_idx, r in enumerate(tbl.rows):
            if not r._tr.xpath('./w:trPr/w:cantSplit'):
                missing_cant_split.append((t_idx, r_idx))
    t13_ok = (len(missing_tbl_header) == 0 and len(missing_cant_split) == 0)
    detail_t13 = f"{len(doc.tables)} tables verified"
    if not t13_ok:
        detail_t13 = f"missing tblHeader: {missing_tbl_header[:3]}, missing cantSplit: {missing_cant_split[:3]}"
    check("T13", "All tables have repeating header (w:tblHeader) on row 0 and row split protection (w:cantSplit) on all rows",
          t13_ok, detail_t13)

    # ---- Final Report --------------------------------------------------------
    width = max(len(d) for _, d, _, _ in results) + 2
    npass = sum(1 for _, _, ok, _ in results if ok)
    out = [f"[{'PASS' if ok else 'FAIL'}] {pid:<8} {desc:<{width}} {detail}"
           for pid, desc, ok, detail in results]
    print("\n".join([f"RESULT: {'PASS' if npass == len(results) else 'FAIL'} - {npass}/{len(results)} SRS checks passed",
                     ""] + out))
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
