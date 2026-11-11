#!/usr/bin/env python3
"""Mutation gate for the F1 forward slice + the upgrade-race (B8.1) column.

Variants
  baseline : real RTL
  MUT-B    : L1 clean owner answers FWD_GETS with DATAFWD dirty (we=1)
  MUT-C    : directory omits FWD_GETS on DIR_E + GETS(other)
  MUT-D    : directory inserts a 1-flit arrival at the HEAD of its per-VC
             queue instead of the back (ruling B8.1 forbids this)

Matrix (each cell is the expected result for that variant x test; the count
is derived from len(VARIANTS) x len(TESTS), never hard-coded):
             positive   neg_skip_fwd   neg_dirty_bit   race   vc0_fifo
  baseline     PASS        FAIL            FAIL         PASS      PASS
  MUT-B        FAIL        FAIL            PASS         PASS      PASS
  MUT-C        FAIL        PASS            FAIL         FAIL      FAIL
  MUT-D        PASS        FAIL            FAIL         FAIL      FAIL

The `race` column is the directed concurrent-upgrade test: its two GETMs
reach the directory on consecutive cycles (tb merge-FIFO), so a head-insert
either steals the queue position of the older request (wrong INV target)
or is orphaned by the same-cycle pop (stall/timeout) - both are catches.

The `vc0_fifo` column is the three-tile VC0 FIFO-ordering test (ruling
B8.1 / invariant I4). Three tiles put two pending REQs for the SAME line
on VC0 at once, so a head insertion is observable as an ORDER swap: the
newest request is served before the oldest. The mutant is killed by the
FIFO-order detector itself (the line still completes), not by a stall.

Each run is a fresh compile (make clean) and a single cocotb TESTCASE.
The source file is restored from a byte copy and md5-verified after every
variant; a missing/ambiguous anchor is a hard error.
"""
import hashlib
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
L1 = HERE / "../../rtl/l1/l1_mesi_ctrl.sv"
DIR = HERE / "../../rtl/directory/dir_ctrl.sv"
RACE = HERE / "../../tb_rtl_evidence/directed_upgrade_race"
VC0FIFO = HERE / "../../tb_rtl_evidence/directed_vc0_fifo"

L1_ANCHOR = """          if (state == L1_E && rx_addr == addr_q)
            send(MSG_DATAFWD, addr_q, data_q, 1'b0, 1'b0);  // clean
          else if (state == L1_M && rx_addr == addr_q)
            send(MSG_DATAFWD, addr_q, data_q, 1'b1, 1'b0);  // dirty"""
L1_MUT = """          if (state == L1_E && rx_addr == addr_q)
            send(MSG_DATAFWD, addr_q, data_q, 1'b1, 1'b0);  // MUT-B: dirty on clean owner
          else if (state == L1_M && rx_addr == addr_q)
            send(MSG_DATAFWD, addr_q, data_q, 1'b1, 1'b0);  // dirty"""

DIR_ANCHOR = """                send(MSG_FWD_GETS, owner, dline, '0, 1'b0, 1'b0);
            end
          end else if (h_msg == MSG_PUTS) begin"""
DIR_MUT = """                ;  // MUT-C: forward omitted
            end
          end else if (h_msg == MSG_PUTS) begin"""

# B8.1: a new arrival goes to the BACK of the per-VC queue (rxq_wr). MUT-D
# inserts it at the head instead: write one slot before the current head and
# move the read pointer back, so the newest arrival is served first.
HEAD_ANCHOR = """              rxq_msg[rx_push_vc][rxq_wr[rx_push_vc]]  <= noc_req_flit[HDR_MSG_HI:HDR_MSG_LO];
              rxq_src[rx_push_vc][rxq_wr[rx_push_vc]]  <= noc_req_flit[HDR_SRC_LO +: TILE_ID_W];
              rxq_addr[rx_push_vc][rxq_wr[rx_push_vc]] <= noc_req_flit[HDR_ADDR_HI:HDR_ADDR_LO];
              rxq_we[rx_push_vc][rxq_wr[rx_push_vc]]   <= noc_req_flit[HDR_WE];
              rxq_excl[rx_push_vc][rxq_wr[rx_push_vc]] <= noc_req_flit[HDR_EXCL];
              rxq_data[rx_push_vc][rxq_wr[rx_push_vc]] <= '0;
              rxq_wr[rx_push_vc] <= rxq_wr[rx_push_vc] + 1'b1;"""
HEAD_MUT = """              rxq_msg[rx_push_vc][rxq_rd[rx_push_vc] - 1'b1]  <= noc_req_flit[HDR_MSG_HI:HDR_MSG_LO];  // MUT-D: head
              rxq_src[rx_push_vc][rxq_rd[rx_push_vc] - 1'b1]  <= noc_req_flit[HDR_SRC_LO +: TILE_ID_W];
              rxq_addr[rx_push_vc][rxq_rd[rx_push_vc] - 1'b1] <= noc_req_flit[HDR_ADDR_HI:HDR_ADDR_LO];
              rxq_we[rx_push_vc][rxq_rd[rx_push_vc] - 1'b1]   <= noc_req_flit[HDR_WE];
              rxq_excl[rx_push_vc][rxq_rd[rx_push_vc] - 1'b1] <= noc_req_flit[HDR_EXCL];
              rxq_data[rx_push_vc][rxq_rd[rx_push_vc] - 1'b1] <= '0;
              rxq_rd[rx_push_vc] <= rxq_rd[rx_push_vc] - 1'b1;  // MUT-D: insert at head"""

VARIANTS = {
    "baseline": (L1, None, None),
    "MUT-B": (L1, L1_ANCHOR, L1_MUT),
    "MUT-C": (DIR, DIR_ANCHOR, DIR_MUT),
    "MUT-D": (DIR, HEAD_ANCHOR, HEAD_MUT),
}

TESTS = ["positive", "neg_skip_fwd", "neg_dirty_bit", "race", "vc0_fifo"]
TESTCASE = {
    "positive": "test_f1_forward_positive",
    "neg_skip_fwd": "test_f1_forward_negative_skip_fwd",
    "neg_dirty_bit": "test_f1_forward_negative_dirty_bit",
    # "race" runs the directed upgrade-race test in its own directory.
    # "vc0_fifo" runs the three-tile VC0 FIFO-ordering test in its own
    # directory.
}
EXPECTED = {
    "baseline": {"positive": True, "neg_skip_fwd": False, "neg_dirty_bit": False, "race": True, "vc0_fifo": True},
    "MUT-B": {"positive": False, "neg_skip_fwd": False, "neg_dirty_bit": True, "race": True, "vc0_fifo": True},
    "MUT-C": {"positive": False, "neg_skip_fwd": True, "neg_dirty_bit": False, "race": False, "vc0_fifo": False},
    "MUT-D": {"positive": True, "neg_skip_fwd": False, "neg_dirty_bit": False, "race": False, "vc0_fifo": False},
}


def md5(path):
    return hashlib.md5(path.read_bytes()).hexdigest()


def apply_mutation(path, anchor, replacement):
    text = path.read_text()
    n = text.count(anchor)
    if n != 1:
        sys.exit(f"ERROR: anchor in {path} found {n} times, expected exactly 1")
    path.write_text(text.replace(anchor, replacement, 1))


def run_test(case):
    if case == "race":
        cwd, args = RACE, ["MODULE=directed_upgrade_race"]
    elif case == "vc0_fifo":
        cwd, args = VC0FIFO, ["MODULE=directed_vc0_fifo"]
    else:
        cwd = HERE
        args = [f"MODULE=test_f1_forward", f"TESTCASE={TESTCASE[case]}"]
    subprocess.run(["make", "clean"], cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    r = subprocess.run(["make", *args],
                       cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0


def main():
    originals = {L1: L1.read_bytes(), DIR: DIR.read_bytes()}
    md5_before = {p: md5(p) for p in originals}
    results = {}
    try:
        for name, (path, anchor, repl) in VARIANTS.items():
            for p, data in originals.items():
                p.write_bytes(data)
            if anchor is not None:
                apply_mutation(path, anchor, repl)
            results[name] = {case: run_test(case) for case in TESTS}
            for p, data in originals.items():
                p.write_bytes(data)
                assert md5(p) == md5_before[p], f"restore failed for {p}"
    finally:
        for p, data in originals.items():
            p.write_bytes(data)
            assert md5(p) == md5_before[p], f"restore failed for {p}"

    ok = results == EXPECTED
    print(f"{'variant':10s} " + "".join(f"{t:>14s}" for t in TESTS))
    for name in VARIANTS:
        row = "".join(f"{'PASS' if results[name][t] else 'FAIL':>14s}" for t in TESTS)
        print(f"{name:10s} " + row)
    passed = sum(results[n][t] == EXPECTED[n][t] for n in VARIANTS for t in TESTS)
    total = len(VARIANTS) * len(TESTS)   # derived from the matrix, not negotiated
    print(f"MUTATIONS: {passed}/{total} expected")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
