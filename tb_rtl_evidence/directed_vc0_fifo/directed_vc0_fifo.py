"""Directed cocotb test for ruling B8.1 / invariant I4: per-VC FIFO ordering.

The property under test (WP S3.3 rule 6, ruling B8):

    A new arrival is enqueued at the BACK of the directory's request queue
    for that line (FIFO within VC0, invariant I4) - it never re-enters at
    the head.

Setup (three tiles - the minimum that makes the property observable):

    tile0 GETs line X. The directory leaves DIR_I for DIR_MEM_WAIT and
    waits for the DATA/UNBLOCK round trip (a 9-flit DATA plus the UNBLOCK
    back), which keeps it busy for many cycles. While it is busy, tile1 and
    tile2 each GET the SAME line X. Both REQs therefore sit pending in VC0
    at the same time - proved below from the queue pointers, not inferred.

    When the directory becomes free it pops VC0 in FIFO order: the request
    that arrived FIRST must be served first.

Checked properties:

    B8.1.1  the setup is real: two REQs for the same line are pending on
            VC0 at the same time (read from rxq_cnt/rxq_rd and the queue
            entries) - anti-vacuity for the whole test.
    B8.1.2  the baseline serves them in arrival order (the oldest pending
            request for the line completes first - Lemma L2).
    B8.1.3  the line still completes: every requester gets its data and the
            directory reaches a stable state with the expected sharers.

The FIFO-order detector (B8.1.2) is the detector that must kill the MUT-D
mutant. It must fire on the ORDERING property itself, not on a stall: the
mutant swaps the two entries in the queue, so both requests are still
servable and the line still completes - only the order changes.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

# ---- tile_pkg encodings ------------------------------------------------
DIR_S, DIR_E, DIR_M = 1, 2, 3
L1_I, L1_S, L1_E, L1_M = 0, 1, 2, 3

MSG_GETS, MSG_GETM = 0, 1
MSG_UNBLOCK = 4
MSG_INV = 5
MSG_INVACK = 6
MSG_DATA = 7

HDR_HEAD = 41
HDR_MSG_LO = 44
HDR_SRC_LO = 48
HDR_ADDR_HI = 31
HDR_ADDR_LO = 0

VC_REQ = 0

DIR_NAME = {0: "I", DIR_S: "S", DIR_E: "E", DIR_M: "M",
            4: "MEM_WAIT", 5: "FWD_WAIT", 6: "INV_WAIT", 7: "EVICT"}
MSG_NAME = {0: "GETS", 1: "GETM", 2: "PUTS", 3: "PUTM", 4: "UNBLOCK",
            5: "INV", 6: "INVACK", 7: "DATA", 8: "FWD_GETS", 9: "FWD_GETM",
            10: "DATAFWD", 11: "PUTACK"}

ABORT_WIN = 8
MONITOR_CYCLES = 900   # bounded completion window
SETTLE = 30
LINE = 0x40


def _v(h):
    """Read a handle as int; idle/undriven outputs are X/Z -> -1."""
    try:
        return int(h.value)
    except ValueError:
        return -1


def _head_msg(valid, flit):
    """HDR_MSG of a head flit, or None when idle / not a head / unknown."""
    if not valid or flit < 0:
        return None
    if not (flit >> HDR_HEAD) & 1:
        return None
    return (flit >> HDR_MSG_LO) & 0xF


def _head_src(flit):
    return (flit >> HDR_SRC_LO) & 0x3


async def _boot(dut):
    dut.rst_n.value = 0
    for sig in ("c0v", "c0w", "c0e", "c1v", "c1w", "c1e", "c2v", "c2w", "c2e"):
        getattr(dut, sig).value = 0
    for sig in ("c0d", "c1d", "c2d"):
        getattr(dut, sig).value = 0
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(4):
        await RisingEdge(dut.clk)


async def _issue(dut, tile):
    """Assert a read request on one tile for one cycle."""
    v = getattr(dut, f"c{tile}v")
    v.value = 1
    await RisingEdge(dut.clk)
    v.value = 0


@cocotb.test()
async def test_vc0_fifo_order(dut):
    """B8.1: two pending same-line REQs on VC0 are served in arrival order."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await _boot(dut)

    # ── Step 1: tile0 GETs the line. The directory leaves DIR_I for
    #    DIR_MEM_WAIT and blocks there for the DATA/UNBLOCK round trip.
    await _issue(dut, 0)

    # Wait for the directory to actually leave DIR_I (it must be busy, or
    # the two later REQs would be popped one at a time and never be pending
    # together).
    busy = False
    for _ in range(200):
        await RisingEdge(dut.clk)
        st = _v(dut.dir_state)
        if st in (4, 5, 6):        # MEM_WAIT / FWD_WAIT / INV_WAIT
            busy = True
            break
    assert busy, (
        "setup: the directory never entered a transient state, so two REQs "
        "could never be pending on VC0 at the same time")
    dut._log.info("SETUP dir is busy in %s", DIR_NAME.get(st, st))

    # ── Step 2: while the directory is busy, tile1 and tile2 each GET the
    #    SAME line. Their REQs land on VC0 and stay pending.
    await _issue(dut, 1)
    await _issue(dut, 2)

    # ── Step 3: watch the VC0 queue. Record the order in which the two
    #    requests arrived (the order in which they were pushed) and prove
    #    they are pending simultaneously, from the queue pointers.
    arrival = []              # (tile, cycle) in push order
    pending_evidence = None   # the proof that both were pending at once
    served = []               # (tile, cycle) in service order
    done = {}                 # tile -> cycle of core_rsp_valid
    data_seen = {}            # tile -> cycle of DATA arrival

    t = 0
    while t < MONITOR_CYCLES:
        # --- VC0 queue state (the directory's own pointers) --------------
        q_cnt = _v(dut.q_cnt)
        q_rd = _v(dut.q_rd)
        q_wr = _v(dut.q_wr)
        # The queue entries are visible only at the head (rd) and the slot
        # after it; with two pending entries the head is the OLDEST.
        entries = []
        for slot in (0, 1, 2, 3):
            src = _v(getattr(dut, f"q_src{slot}"))
            addr = _v(getattr(dut, f"q_addr{slot}"))
            msg = _v(getattr(dut, f"q_msg{slot}"))
            entries.append((src, addr, msg))

        if q_cnt is not None and q_cnt >= 2:
            # Two entries pending on VC0: identify them by walking from the
            # read pointer (the head is the oldest).
            pend = []
            for k in range(q_cnt):
                slot = (q_rd + k) % 4
                pend.append(entries[slot])
            addrs = {a for (_s, a, _m) in pend}
            srcs = {s for (s, _a, _m) in pend}
            if (len(addrs) == 1 and len(srcs) == 2
                    and pending_evidence is None):
                pending_evidence = {
                    "cycle": t,
                    "cnt": q_cnt,
                    "rd": q_rd,
                    "wr": q_wr,
                    "pending": [(s, MSG_NAME.get(m, m), format(a, "08x"))
                                for (s, a, m) in pend],
                }
                dut._log.info(
                    "B8_1_1 t=%d VC0 holds %d pending REQs: %s "
                    "(cnt=%d rd=%d wr=%d) - same line, two requesters",
                    t, q_cnt, pending_evidence["pending"], q_cnt, q_rd, q_wr)

        # --- the order in which requests ARRIVE at the directory ---------
        # (the push order is the FIFO order the property is about)
        dflit = _v(dut.dir_req_flit)
        if _v(dut.dir_req_valid) and dflit >= 0 and (dflit >> HDR_HEAD) & 1:
            m = (dflit >> HDR_MSG_LO) & 0xF
            if m in (MSG_GETS, MSG_GETM):
                src = _head_src(dflit)
                addr = (dflit >> HDR_ADDR_LO) & 0xFFFFFFFF
                if addr == LINE:
                    arrival.append((src, t))
                    dut._log.info("ARRIVAL t=%d tile %d issued %s for 0x%08x",
                                  t, src, MSG_NAME.get(m, m), addr)

        # --- the order in which requests are SERVED ----------------------
        # A request is served when the directory issues the DATA for it.
        for tile in (0, 1, 2):
            rv = _v(getattr(dut, f"l1_{tile}_rsp_valid"))
            rf = _v(getattr(dut, f"l1_{tile}_rsp_flit"))
            if _head_msg(rv, rf) == MSG_DATA and tile not in data_seen:
                data_seen[tile] = t
                served.append((tile, t))
                dut._log.info("SERVED t=%d tile %d got DATA", t, tile)

        for tile in (0, 1, 2):
            if _v(getattr(dut, f"c{tile}rv")) and tile not in done:
                done[tile] = t
                dut._log.info("COMPLETED t=%d tile %d", t, tile)

        if len(done) == 3:
            break
        await RisingEdge(dut.clk)
        t += 1

    for _ in range(SETTLE):
        await RisingEdge(dut.clk)

    l1_states = [_v(dut.l1_0_state), _v(dut.l1_1_state), _v(dut.l1_2_state)]
    sharers = _v(dut.dir_sharers)
    dir_st = _v(dut.dir_state)

    dut._log.info(
        "SUMMARY arrival=%s served=%s done=%s pending_evidence=%s "
        "final_dir=%s sharers=%s l1=%s",
        arrival, served, done, pending_evidence,
        DIR_NAME.get(dir_st, dir_st), sharers, l1_states)

    # ── B8.1.1 - anti-vacuity: the two same-line REQs really were pending
    #    on VC0 at the same time, proved from the queue pointers.
    assert pending_evidence is not None, (
        "B8.1.1: no cycle was observed with two same-line REQs pending on "
        "VC0 - the setup did not put two requests for one line on the "
        "queue, so the ordering property was never exercised "
        "(arrival=%s)" % (arrival,))

    # ── B8.1.2 - the FIFO-ORDER detector. The request that arrived first
    #    must be served first. This is the detector that must kill MUT-D.
    req_arrivals = [src for (src, _t) in arrival if src in (1, 2)]
    req_served = [tile for (tile, _t) in served if tile in (1, 2)]
    assert len(req_arrivals) == 2, (
        "B8.1.2: expected two same-line requests to arrive at the "
        "directory, got %r (arrival=%s)" % (req_arrivals, arrival))
    assert len(req_served) == 2, (
        "B8.1.2: expected both same-line requests to be served, got %r "
        "(served=%s, dir=%s)" % (req_served, served, DIR_NAME.get(dir_st)))

    assert req_served == req_arrivals, (
        "B8.1.2 FIFO-ORDER VIOLATION: the requests for the same line "
        "arrived in the order %r but were served in the order %r - the "
        "directory did not serve the oldest pending request first (ruling "
        "B8: a new arrival is enqueued at the BACK of the queue, FIFO "
        "within VC0, invariant I4)" % (req_arrivals, req_served))

    # ── B8.1.3 - the line still completes for every requester, and the
    #    directory reaches a stable state holding the line.
    for tile in (0, 1, 2):
        assert tile in done, (
            "B8.1.3: tile %d never completed within %d cycles "
            "(dir=%s sharers=%s l1=%s arrival=%s served=%s done=%s)"
            % (tile, MONITOR_CYCLES, DIR_NAME.get(dir_st, dir_st), sharers,
               l1_states, arrival, served, done))

    assert dir_st == DIR_S, (
        "B8.1.3: expected the directory to settle in DIR_S with all three "
        "tiles sharing the line, got %s (sharers=%s l1=%s)"
        % (DIR_NAME.get(dir_st, dir_st), sharers, l1_states))
    assert sharers == 0b111, (
        "B8.1.3: expected sharers=0b111 (all three tiles sharing), got %s"
        % (format(sharers, "03b") if sharers is not None and sharers >= 0
           else "xx"))
    assert l1_states == [L1_S, L1_S, L1_S], (
        "B8.1.3: expected all three L1s in L1_S, got %r" % (l1_states,))
