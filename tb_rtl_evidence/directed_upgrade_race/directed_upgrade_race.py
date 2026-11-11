"""Directed cocotb test for ruling B6: the concurrent-upgrade race.

Two sharers upgrade the same line at once (WP S3.3 rule 6, Appendix A abort
row, S12 item 12): both L1s accept a store from S in the same cycle, both
send GETM, the directory pops the first GETM and issues INV to the other
sharer - which is itself mid-miss (L1_SM_D) on that line.

Checked properties (ruling B6):

  B6.1  the race is exercised: an INV is delivered to a tile that is in a
        miss state on that line (anti-vacuity - the hazard must occur).
  B6.2  that tile aborts: abort_o pulses within a bounded window of the INV
        and the INVACK is issued immediately (never deferred).
  B6.3  both stores complete (core_rsp_valid for both cores).
  B6.4  exactly one M at the end (single-writer invariant).

Negative control: the same test against l1_mesi_ctrl_defer_inv.sv, whose
same-line INV during a miss is deferred (never answered while the miss is
open - the B6-forbidden behaviour). B6.2 must FAIL there with the fault
present: the INV reaches the mid-miss tile and no abort ever follows.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

# ---- tile_pkg encodings ------------------------------------------------
DIR_S, DIR_E, DIR_M = 1, 2, 3
L1_I, L1_S, L1_E, L1_M = 0, 1, 2, 3
L1_IS_D, L1_IM_D, L1_SM_D = 4, 5, 6
MISS_STATES = (L1_IS_D, L1_IM_D, L1_SM_D)

MSG_INV, MSG_INVACK = 5, 6

HDR_HEAD = 41
HDR_MSG_LO = 44

L1_NAME = {L1_I: "I", L1_S: "S", L1_E: "E", L1_M: "M",
           4: "IS_D", 5: "IM_D", 6: "SM_D", 7: "EI_A", 8: "MI_A"}
DIR_NAME = {0: "I", DIR_S: "S", DIR_E: "E", DIR_M: "M",
            4: "MEM_WAIT", 5: "FWD_WAIT", 6: "INV_WAIT", 7: "EVICT"}
MSG_NAME = {0: "GETS", 1: "GETM", 2: "PUTS", 3: "PUTM", 4: "UNBLOCK",
            5: "INV", 6: "INVACK", 7: "DATA", 8: "FWD_GETS", 9: "FWD_GETM",
            10: "DATAFWD", 11: "PUTACK", 14: "RSVD0", 15: "RSVD1"}

ABORT_WIN = 8     # abort_o must pulse this soon after the INV (dispatch+reg)
INVACK_WIN = 12   # the INVACK head flit must leave this soon after the INV
MONITOR_CYCLES = 600   # bounded completion window for both stores
SETTLE = 20


def _v(h):
    """Read a handle as int; idle/undriven outputs are X/Z -> -1 (never crash)."""
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


async def _boot(dut):
    """Reset both tiles and the directory; returns after reset is released."""
    dut.rst_n.value = 0
    for sig in ("c0v", "c0w", "c0e", "c1v", "c1w", "c1e"):
        getattr(dut, sig).value = 0
    dut.c0d.value = 0
    dut.c1d.value = 0
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut._log.info("BOOT dir_state=%s l1_0=%s l1_1=%s",
                  DIR_NAME.get(_v(dut.dir_state), _v(dut.dir_state)),
                  L1_NAME.get(_v(dut.l1_0_state), _v(dut.l1_0_state)),
                  L1_NAME.get(_v(dut.l1_1_state), _v(dut.l1_1_state)))


async def _phase_a(dut):
    """tile 1 GETS the line -> DIR_E, owner=1, l1_1 in {E,M}."""
    dut.c1v.value = 1
    dut.c1w.value = 0
    await RisingEdge(dut.clk)
    dut.c1v.value = 0

    for _ in range(400):
        await RisingEdge(dut.clk)
        if (_v(dut.dir_state) == DIR_E and _v(dut.dir_owner) == 1
                and _v(dut.l1_1_state) in (L1_E, L1_M)):
            break
    else:
        raise AssertionError(
            f"Phase A did not settle: dir_state="
            f"{DIR_NAME.get(_v(dut.dir_state))} owner={_v(dut.dir_owner)} "
            f"l1_1={L1_NAME.get(_v(dut.l1_1_state))}")
    dut._log.info("PHASE_A dir_state=%s owner=%d l1_1=%s",
                  DIR_NAME.get(_v(dut.dir_state)), _v(dut.dir_owner),
                  L1_NAME.get(_v(dut.l1_1_state)))


async def _phase_b(dut):
    """tile 0 GETS the line -> directory exits to DIR_S with BOTH tiles in S."""
    dut.c0v.value = 1
    dut.c0w.value = 0
    await RisingEdge(dut.clk)
    dut.c0v.value = 0

    for _ in range(400):
        await RisingEdge(dut.clk)
        if (_v(dut.dir_state) == DIR_S
                and _v(dut.l1_0_state) == L1_S
                and _v(dut.l1_1_state) == L1_S):
            break
    else:
        raise AssertionError(
            f"Phase B did not settle: dir_state="
            f"{DIR_NAME.get(_v(dut.dir_state))} l1_0="
            f"{L1_NAME.get(_v(dut.l1_0_state))} l1_1="
            f"{L1_NAME.get(_v(dut.l1_1_state))}")
    sharers = _v(dut.dir_sharers)
    dut._log.info("PHASE_B dir_state=DIR_S sharers=%s l1_0=S l1_1=S",
                  format(sharers, "02b") if sharers >= 0 else "xx")
    assert sharers == 0b11, (
        f"Phase B: expected both sharer bits set, sharers="
        f"{format(sharers, '02b') if sharers >= 0 else 'xx'}")


@cocotb.test()
async def test_concurrent_upgrade_race(dut):
    """B6: two sharers upgrade at once; the mid-miss INV must abort, not defer."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await _boot(dut)
    await _phase_a(dut)
    await _phase_b(dut)

    # Phase C: concurrent upgrade - both stores issued in the SAME cycle.
    dut.c0d.value = 0xA5A5A5A5A5A5A5A5
    dut.c1d.value = 0x5A5A5A5A5A5A5A5A
    dut.c0v.value = 1
    dut.c0w.value = 1
    dut.c1v.value = 1
    dut.c1w.value = 1
    await RisingEdge(dut.clk)
    dut.c0v.value = 0
    dut.c0w.value = 0
    dut.c1v.value = 0
    dut.c1w.value = 0
    dut._log.info("PHASE_C simultaneous stores issued (c0w=c1w=1)")

    inv_t, inv_tile, inv_state = None, None, None
    abort_t = {0: None, 1: None}
    invack_t = {0: None, 1: None}
    done = {0: None, 1: None}

    t = 0
    while t < MONITOR_CYCLES:
        # B6.1: INV head flit delivered to a tile that is mid-miss.
        for tile in (0, 1):
            rsp_valid = _v(dut.l1_0_rsp_valid if tile == 0 else dut.l1_1_rsp_valid)
            rsp_flit = _v(dut.l1_0_rsp_flit if tile == 0 else dut.l1_1_rsp_flit)
            st = _v(dut.l1_0_state if tile == 0 else dut.l1_1_state)
            if (_head_msg(rsp_valid, rsp_flit) == MSG_INV
                    and st in MISS_STATES and inv_t is None):
                inv_t, inv_tile, inv_state = t, tile, st
                dut._log.info(
                    "B6_1 t=%d INV delivered to tile %d in %s (mid-miss) "
                    "dir_state=%s", t, tile, L1_NAME[st],
                    DIR_NAME.get(_v(dut.dir_state), _v(dut.dir_state)))

        # B6.2 evidence: abort_o pulses, INVACK head flits leaving each tile.
        if _v(dut.l1_0_abort) and abort_t[0] is None:
            abort_t[0] = t
            dut._log.info("B6_2 t=%d abort_o pulse on tile 0", t)
        if _v(dut.l1_1_abort) and abort_t[1] is None:
            abort_t[1] = t
            dut._log.info("B6_2 t=%d abort_o pulse on tile 1", t)
        for tile in (0, 1):
            req_valid = _v(dut.l1_0_req_valid if tile == 0 else dut.l1_1_req_valid)
            req_flit = _v(dut.l1_0_req_flit if tile == 0 else dut.l1_1_req_flit)
            if (_head_msg(req_valid, req_flit) == MSG_INVACK
                    and invack_t[tile] is None):
                invack_t[tile] = t

        # B6.3 evidence: store completions (core_rsp_valid after Phase C).
        for tile, sig in ((0, dut.c0rv), (1, dut.c1rv)):
            if _v(sig) and done[tile] is None:
                done[tile] = t
                dut._log.info("B6_3 t=%d store completed on tile %d", t, tile)

        if done[0] is not None and done[1] is not None:
            break
        await RisingEdge(dut.clk)
        t += 1

    # Let the final state settle (the loser may still be flushing).
    for _ in range(SETTLE):
        await RisingEdge(dut.clk)

    l1_0, l1_1 = _v(dut.l1_0_state), _v(dut.l1_1_state)

    # Stall diagnostic: what the directory is actually holding (B7.1 per-VC
    # mailbox: one queue per VC, pop order RESP > INV > FWD > REQ). A non-empty
    # queue whose head is not accepted by the current transient while
    # state==INV_WAIT is the head-of-line block.
    try:
        cnts = [_v(dut.u_dir.rxq_cnt[vc]) for vc in range(4)]
        hvc = _v(dut.u_dir.h_vc)
        head = _v(dut.dir_rx_msg) if sum(cnts) > 0 else -1
        dut._log.info(
            "RXQ vc_cnt[REQ,FWD,RESP,INV]=%s h_vc=%s head_msg=%s "
            "inv_mask=%s pending_req=%s",
            cnts, hvc,
            MSG_NAME.get(head, head),
            bin(_v(dut.u_dir.inv_mask)) if _v(dut.u_dir.inv_mask) >= 0 else "x",
            _v(dut.u_dir.req_tile))
    except Exception as exc:  # hierarchy not visible: skip, the stall still stands
        dut._log.info("RXQ probe unavailable: %s", exc)

    dut._log.info(
        "SUMMARY inv_t=%s inv_tile=%s inv_state=%s abort_t=%s invack_t=%s "
        "store_done=%s final_dir=%s sharers=%s l1_0=%s l1_1=%s",
        inv_t, inv_tile, L1_NAME.get(inv_state), abort_t, invack_t,
        {k: (v is not None) for k, v in done.items()},
        DIR_NAME.get(_v(dut.dir_state), _v(dut.dir_state)),
        _v(dut.dir_sharers), L1_NAME.get(l1_0), L1_NAME.get(l1_1))

    # B6.1 - the race must actually have occurred (anti-vacuity).
    assert inv_t is not None, (
        "B6.1: no INV was delivered to a mid-miss tile - the concurrent-"
        "upgrade race was not exercised (vacuous run)")

    # B6.2 - the mid-miss tile aborts: abort_o pulse, then INVACK immediately.
    ta = abort_t[inv_tile]
    assert ta is not None and inv_t - 2 <= ta <= inv_t + ABORT_WIN, (
        f"B6.2: same-line INV delivered to tile {inv_tile} in "
        f"{L1_NAME.get(inv_state)} at t={inv_t} but abort_o never pulsed "
        f"within {ABORT_WIN} cycles (abort_t={abort_t}) - DEFER-INV FAULT "
        f"PRESENT: the outstanding miss was not aborted")
    ti = invack_t[inv_tile]
    assert ti is not None and inv_t - 2 <= ti <= inv_t + INVACK_WIN, (
        f"B6.2: INVACK from tile {inv_tile} not seen within {INVACK_WIN} "
        f"cycles of the INV at t={inv_t} (invack_t={invack_t}) - DEFER-INV "
        f"FAULT PRESENT: the INV was answered late or not at all")

    # B6.3 - both stores complete within the bounded window.
    assert done[0] is not None, (
        f"B6.3: tile 0 store never completed within {MONITOR_CYCLES} cycles "
        f"(dir_state={DIR_NAME.get(_v(dut.dir_state))} l1_0="
        f"{L1_NAME.get(l1_0)} l1_1={L1_NAME.get(l1_1)} inv_t={inv_t} "
        f"abort_t={abort_t}) - store stalled")
    assert done[1] is not None, (
        f"B6.3: tile 1 store never completed within {MONITOR_CYCLES} cycles "
        f"(dir_state={DIR_NAME.get(_v(dut.dir_state))} l1_0="
        f"{L1_NAME.get(l1_0)} l1_1={L1_NAME.get(l1_1)} inv_t={inv_t} "
        f"abort_t={abort_t}) - store stalled")

    # B6.4 - single-writer: exactly one M at the end.
    m_count = (1 if l1_0 == L1_M else 0) + (1 if l1_1 == L1_M else 0)
    assert m_count == 1, (
        f"B6.4: expected exactly one M at the end, found {m_count} "
        f"(l1_0={L1_NAME.get(l1_0)}, l1_1={L1_NAME.get(l1_1)})")
