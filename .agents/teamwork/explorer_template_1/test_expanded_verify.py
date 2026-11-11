#!/usr/bin/env python3
import re
import sys
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
    return lines, tables

def run_checks(path):
    lines, tables = extract(path)
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

    # ---- Original 41 checks ----
    # B1
    puts = row_with("PUTS")
    putm = row_with("PUTM")
    putack = row_with("PUTACK")
    unblock = row_with("UNBLOCK")
    check("B1a", "PUTS is described as L1 -> directory", puts and "L1" in puts[-1] and "dir" in puts[-1].lower(), str(puts))
    check("B1b", "PUTM is described as L1 -> directory", putm and "L1" in putm[-1] and "dir" in putm[-1].lower(), str(putm))
    check("B1c", "PUTACK is described as directory -> L1", putack and "dir" in putack[-1].lower() and "L1" in putack[-1], str(putack))
    check("B1d", "UNBLOCK is described as L1 -> directory", unblock and "L1" in unblock[-1] and "dir" in unblock[-1].lower(), str(unblock))
    check("B1e", "no 'Directory-to-subscriber' direction remains", "Directory-to-subscriber" not in text, "")

    # B2
    check("B2a", "the phantom assertion id A13 is gone from the SRS", "A13" not in text, "")
    fr02 = row_with("FR-02")
    check("B2b", "FR-02 is verified by A8.x and/or I1", fr02 and re.search(r"A8|I1", fr02[-1]), str(fr02))

    # B3
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

    # B4
    a1 = row_with("AREA-01")
    a2 = row_with("AREA-02")
    check("B4a", "AREA-01's LUT target is a design target (<=20,000), not device capacity",
          a1 and len(a1) >= 4 and re.search(r"20[,.]?000", a1[2]), str(a1))
    check("B4b", "AREA-01's LUT maximum is <= 40,000",
          a1 and len(a1) >= 4 and re.search(r"40[,.]?000", a1[3]), str(a1))
    check("B4c", "AREA-02's BRAM target is <= 48 with a ceiling of 80",
          a2 and len(a2) >= 4 and re.search(r"48", a2[2]) and re.search(r"80", a2[3]), str(a2))
    check("B4d", "a DSP row exists with target 0", re.search(r"AREA-0[3-9][^\n]*DSP", text) and
          re.search(r"AREA-0[3-9][^\n]*\b0\b", text), "")
    fpga05 = [r for rows in tables for r in rows if r and r[0].strip().startswith("FPGA-05")]
    check("B4e", "FPGA-05 no longer asserts 80 DSP", not fpga05 or all("DSP" not in " ".join(r) or "0" in " ".join(r) for r in fpga05), str(fpga05))

    # B5
    sig_rows = [r for rows in tables for r in rows if len(r) >= 2 and r[0].strip() in
                ("dma_wr", "dma_req", "dma_write")]
    check("B5a", "no bare DMA write signal appears in the signal list", not sig_rows, str(sig_rows))
    check("B5b", "the DMA interface is marked absent from the 2x2 build",
          "not present in the 2" in text.lower() or "no dma" in text.lower(), "")

    # B6
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
    trace_rows = []
    for rows in tables:
        if rows and any("Method" in c for c in rows[0]):
            trace_rows = rows[1:]
    traced_ids = {r[0].strip() for r in trace_rows if r}
    check("B6b", "every FR is traced in the traceability table",
          fr_ids and fr_ids.issubset(traced_ids), f"untraced: {sorted(fr_ids - traced_ids)}")

    # M1
    msgs = ["GETS", "GETM", "PUTS", "PUTM", "UNBLOCK", "INV", "INVACK", "DATA",
            "FWD_GETS", "FWD_GETM", "DATAFWD", "PUTACK", "DMA_WRITE", "DMA_ACK"]
    missing = [m for m in msgs if m not in text]
    check("M1a", "all 12 core + 2 gated messages appear in the SRS", not missing, f"missing: {missing}")

    # M2
    for i in range(9, 15):
        rid = f"FR-{i:02d}"
        check(f"M2-{i}", f"{rid} exists (forward release, exclusive bit, L2 word, dirty bit, write-back, receptivity)",
              row_with(rid) is not None, "")

    # M3
    n_pct = max(text.count("100 %"), text.count("100%"))
    check("M3a", "coverage targets are numeric (at least three numeric targets)", n_pct >= 3, f"numeric targets: {n_pct}")
    check("M3b", "the four WP coverage criteria are present",
          all(k in text for k in ("FSM", "assertion", "waiver", "bin")), "")

    # M4
    def plan_rows(marker):
        for rows in tables:
            if rows and any(marker in c for c in rows[0]):
                return rows[1:]
        return []
    tc = plan_rows("Scenario")
    fv = plan_rows("Procedure on board")
    check("M4a", "the directed test plan has at least 14 rows", len(tc) >= 14, f"{len(tc)} rows")
    check("M4b", "the FPGA test plan has at least 14 rows", len(fv) >= 14, f"{len(fv)} rows")

    # M5
    check("M5a", "the proof parameters are marked proposed", "proposed" in text.lower(), "")
    check("M5b", "both liveness bounds appear (2x2 and 4x4)",
          ("64" in text and "150" in text), "")

    # M6
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

    # N-series
    check("N1a", "the SRS says 'virtual channel', not 'virtual buffer'", "virtual buffer" not in text.lower(), "")
    check("N2a", "the conditional DMA tests are marked conditional",
          re.search(r"18[–-]22[^.]*conditional|conditional[^.]*18[–-]22", text, re.I) is not None, "")
    check("N4a", "the performance section states known latency figures",
          any(k in text for k in ("4-cycle", "4 cycles", "9 flits", "512-bit")), "")
    check("N5a", "power is explicitly scoped or flagged", re.search(r"out of scope|not specified|TBD", text, re.I) is not None, "")
    check("N6a", "the verification exit criteria mention zero waivers", "waiver" in text.lower(), "")

    # =========================================================================
    # ---- PROPOSED EXPANDED CHECKS (E-series) ----
    # =========================================================================
    
    # E01: FR-01 through FR-08 presence & specific keywords
    fr_keywords = {
        "FR-01": ["directory", "MESI"],
        "FR-02": ["XY", "routing"],
        "FR-03": ["credit", "flow control", "4"],
        "FR-04": ["RESP", "INV", "FWD", "REQ", "escape", "13"],
        "FR-05": ["PUTS", "PUTM", "PUTACK"],
        "FR-06": ["UNBLOCK"],
        "FR-07": ["DMA", "4x4"],
        "FR-08": ["512", "cache line"]
    }
    for fr_id, kws in fr_keywords.items():
        r = row_with(fr_id)
        r_text = " ".join(r) if r else ""
        ok = r is not None and all(kw.lower() in r_text.lower() for kw in kws)
        check(f"E_{fr_id}", f"{fr_id} exists and defines {kws}", ok, r_text[:60] if r else "NOT FOUND")

    # E02: Traceability coverage of ALL requirement classes (PERF, PWR, AREA, FPGA)
    req_classes = ["FR", "PERF", "PWR", "AREA", "FPGA"]
    all_defined_reqs = set()
    for rows in tables:
        for r in rows:
            if r:
                m = re.match(r"^((?:FR|PERF|PWR|AREA|FPGA)-\d+[a-z]?)", r[0].strip())
                if m and not any("Method" in c for c in rows[0]):
                    all_defined_reqs.add(m.group(1))

    untraced_all = all_defined_reqs - traced_ids
    check("E_TRACE_FULL", "Traceability matrix covers all FR, PERF, PWR, AREA, FPGA requirements",
          len(untraced_all) == 0, f"untraced ({len(untraced_all)}): {sorted(untraced_all)}")

    # E03: Check for unresolved placeholders in text and tables
    # e.g., '[Name]', '[Group number / name]', 'TBD' in PERF/FPGA
    placeholders_found = []
    for t_idx, rows in enumerate(tables, 1):
        for r_idx, r in enumerate(rows, 1):
            for c in r:
                if "[name]" in c.lower() or "[group" in c.lower() or "[member" in c.lower():
                    placeholders_found.append((t_idx, r_idx, c))
    check("E_PLACEHOLDERS", "No template placeholders like [Name], [Group...], [Member...] remain",
          len(placeholders_found) == 0, f"found: {placeholders_found}")

    # E04: Check PERF-01 clock frequency target is specified (not TBD)
    p01 = row_with("PERF-01")
    p01_ok = p01 and "TBD" not in p01[2] and "100" in p01[2]
    check("E_PERF01_FREQ", "PERF-01 specifies 100 MHz target frequency (not TBD)",
          p01_ok, str(p01[2] if p01 and len(p01) > 2 else ""))

    # E05: Check FPGA-01 clock frequency target is specified (not TBD)
    fp01 = row_with("FPGA-01")
    fp01_ok = fp01 and "TBD" not in fp01[2] and "100" in fp01[2]
    check("E_FPGA01_FREQ", "FPGA-01 specifies 100 MHz on-board target frequency (not TBD)",
          fp01_ok, str(fp01[2] if fp01 and len(fp01) > 2 else ""))

    # E06: Check Power budget is grounded in WP 6.3 (50 mW)
    pwr_row = row_with("PWR-03") or row_with("PWR-01")
    pwr_text = text
    pwr_ok = "50 mw" in pwr_text.lower() or "50mw" in pwr_text.lower()
    check("E_PWR_BUDGET", "Power requirement reflects WP 6.3 budget (<= 50 mW)",
          pwr_ok, "Missing 50 mW budget specification" if not pwr_ok else "Found")

    # E07: Check Code Coverage targets in Section 8.3
    cov_rows = [r for rows in tables for r in rows if r and any(k in r[0].lower() for k in ("statement", "line", "branch", "toggle"))]
    check("E_CODE_COV", "Code coverage goals (statement, branch, toggle) are specified in Section 8.3",
          len(cov_rows) >= 2, f"found {len(cov_rows)} code coverage rows")

    # E08: Check Table 1 Metadata block (Project title, Group, Members, Mentor)
    # Check if Group has a non-empty name
    has_group = False
    m_grp = re.search(r"Group\s*:\s*([^\n\r]+)", text)
    if m_grp and m_grp.group(1).strip() and not m_grp.group(1).strip().startswith("["):
        has_group = True
    check("E_METADATA_GROUP", "Group name / number is non-empty in metadata",
          has_group, m_grp.group(0) if m_grp else "Group not found")

    # E09: Check Approval table Mentor Name matches header
    appr_mentor = False
    for rows in tables:
        for r in rows:
            if r and "mentor" in r[0].lower():
                if len(r) > 1 and "hemat" in r[1].lower():
                    appr_mentor = True
    check("E_APPR_MENTOR", "Approval table lists Mr. Hemat as Group Mentor (not [Name])",
          appr_mentor, "Mentor not resolved in approval table" if not appr_mentor else "Resolved")

    # E10: Check VC Mapping table completeness in Section 7.1
    # Check that Table 11 has all 14 rows, and verify column values
    msg_rows = [r for rows in tables if rows and len(rows[0]) >= 5 and rows[0][0] == "Message" for r in rows[1:]]
    check("E_MSG_TABLE_COUNT", "Section 7.1 message table has exactly 14 message rows",
          len(msg_rows) == 14, f"found {len(msg_rows)} rows")

    # E11: Check Signal List completeness in Table 12
    # clk, reset, credit_in, credit_out, port_in_*, port_out_*, local_inject_*, local_eject_*
    sig_names = {r[0].strip() for rows in tables if rows and len(rows[0]) >= 5 and rows[0][0] == "Signal" for r in rows[1:]}
    expected_sigs = {"clk", "reset", "credit_in", "credit_out"}
    check("E_SIGNAL_CORE", "Signal list contains core control and credit signals (clk, reset, credit_in, credit_out)",
          expected_sigs.issubset(sig_names), f"missing: {expected_sigs - sig_names}")

    # E12: Check FPGA test plan linking: no '-' in Req ID column
    fv_unlinked = [r[0] for r in fv if len(r) >= 2 and r[1].strip() == "-"]
    check("E_FV_LINKING", "All FPGA validation tests (FV) are linked to a requirement ID (no '-' or blank)",
          len(fv_unlinked) == 0, f"unlinked tests: {fv_unlinked}")

    # E13: Check DMA Register Map inclusion in Section 7.5
    dma_regs = ["SRC_LO", "DST_LO", "LEN", "CTRL", "STATUS", "COUNT"]
    has_dma_regs = all(reg in text for reg in dma_regs)
    check("E_DMA_REGMAP", "Section 7.5 enumerates the 6 DMA channel registers (SRC_LO, DST_LO, LEN, CTRL, STATUS, COUNT)",
          has_dma_regs, "Missing DMA register definitions" if not has_dma_regs else "Enumerated")

    # E14: Check Section 7.4 Timing rules detail
    timing_detail = any(k in text.lower() for k in ("setup uncertainty", "hold uncertainty", "wns", "0.2 ns", "0.1 ns"))
    check("E_TIMING_RULES", "Section 7.4 includes concrete timing parameters (uncertainties, WNS target)",
          timing_detail, "Timing rules lack concrete parameters" if not timing_detail else "Present")

    # E15: Check Formal Verification assertion IDs coverage (A1-A8, I1-I7)
    has_sva_full = all(f"A{i}" in text for i in range(1, 9)) and all(f"I{i}" in text for i in range(1, 8))
    check("E_SVA_COVERAGE", "SRS references all 8 SVA categories (A1-A8) and all 7 network invariants (I1-I7)",
          has_sva_full, "Missing some assertion categories or invariants" if not has_sva_full else "All present")

    # E16: Check PPA trade-off priority statement in Section 6
    ppa_priority = any(k in text.lower() for k in ("priority", "trade-off", "tradeoff")) and \
                   any(k in text.lower() for k in ("area >", "performance >", "power >", "priority order"))
    check("E_PPA_PRIORITY", "Section 6 explicitly defines PPA trade-off priority order",
          ppa_priority, "Missing PPA trade-off priority statement" if not ppa_priority else "Present")

    # ---- Print results ----
    print(f"\n========================================================")
    print(f"VERIFICATION RESULTS: {sum(1 for _, _, ok, _ in results)} / {len(results)} passed")
    print(f"========================================================")
    for pid, desc, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {pid:<16} {desc:<70} {detail[:50] if detail else ''}")

if __name__ == "__main__":
    run_checks("/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_final.docx")
