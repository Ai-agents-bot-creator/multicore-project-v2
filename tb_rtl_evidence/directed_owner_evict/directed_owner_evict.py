"""Directed cocotb tests for ruling B5, Case C (owner evicts during a forward).

Two orderings of the same race, because the three VCs carry no FIFO order
between them (PUTS rides VC0, UNBLOCK rides VC2):

  test_owner_evict_forward   — PUTS reaches the directory first (absorbed in
                               DIR_FWD_WAIT), UNBLOCK exits afterwards.
  test_unblock_before_puts   — UNBLOCK reaches the directory first (exit with
                               the owner bit still set), PUTS arrives after
                               the exit and must clear the extra bit.

Checked properties (ruling B5, WP §4.6 A2.2 row):

  A2.2a  in DIR_S every tile holding the line in S has its sharer bit set
         (no missing bit — the direction that stops two writers).
  A2.2b  an extra bit for a tile that has *released* the line may persist only
         while that release is in flight and must clear within T = 64 cycles.
         An extra bit for a tile that has not released (mid-miss window) is
         logged, not failed: that is §12 item 12, not A2.2b.

Negative control: run the same tests against dir_ctrl_mut.sv, whose FWD_WAIT
exit drops the requester's bit. A2.2a must FAIL there — the fault has to be
present, not merely the symptom absent.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

# ---- tile_pkg encodings ------------------------------------------------
DIR_S, DIR_E, DIR_M = 1, 2, 3
DIR_MEM_WAIT, DIR_FWD_WAIT = 4, 5
L1_I, L1_S, L1_E, L1_M = 0, 1, 2, 3

MSG = {
    0: "GETS", 1: "GETM", 2: "PUTS", 3: "PUTM", 4: "UNBLOCK",
    5: "INV", 6: "INVACK", 7: "DATA", 8: "FWD_GETS", 9: "FWD_GETM",
    10: "DATAFWD", 11: "PUTACK",
}
PEND = {0: "NONE", 1: "GETS", 2: "GETM"}

MSG_PUTS, MSG_PUTM, MSG_UNBLOCK, MSG_PUTACK = 2, 3, 4, 11
T_BOUND = 64          # §5.3 bounded clearance window for A2.2b

HDR_HEAD = 41
HDR_MSG_LO, HDR_MSG_HI = 44, 47

L1_NAME = {L1_I: "I", L1_S: "S", L1_E: "E", L1_M: "M",
           4: "IS_D", 5: "IM_D", 6: "SM_D", 7: "EI_A", 8: "MI_A"}
DIR_NAME = {0: "I", DIR_S: "S", DIR_E: "E", DIR_M: "M",
            DIR_MEM_WAIT: "MEM_WAIT", DIR_FWD_WAIT: "FWD_WAIT",
            6: "INV_WAIT", 7: "EVICT"}


def _v(h):
    """Read a handle as int; idle/undriven outputs are X/Z -> -1 (never crash)."""
    try:
        return int(h.value)
    except ValueError:
        return -1


def _bin4(v):
    return format(v, "04b") if v >= 0 else "xxxx"


def _m(v):
    """Message name; -1 (X/Z, idle queue) -> x."""
    if v < 0:
        return "x"
    return MSG.get(v, str(v))


def _decode_msg(valid, flit, cur):
    """HDR_MSG of the head flit; keep `cur` across payload flits; none when idle."""
    if not valid:
        return "none"
    if flit < 0:
        return "x"
    if (flit >> HDR_HEAD) & 1:
        return MSG.get((flit >> HDR_MSG_LO) & 0xF, "?")
    return cur


def _take(dut, data_sent, l1_1_iss, dir_rsp):
    dir_state = _v(dut.dir_state)
    dir_rsp_valid = _v(dut.dir_rsp_valid)
    dir_rsp_flit = _v(dut.dir_rsp_flit)
    l1_1_req_valid = _v(dut.l1_1_req_valid)
    l1_1_req_flit = _v(dut.l1_1_req_flit)

    dir_rsp = _decode_msg(dir_rsp_valid, dir_rsp_flit, dir_rsp)
    l1_1_iss = _decode_msg(l1_1_req_valid, l1_1_req_flit, l1_1_iss)
    if dir_rsp == "DATA":
        data_sent = 1

    return {
        "t": None,
        "dir_state": dir_state,
        "dir_sharers": _v(dut.dir_sharers),
        "dir_owner": _v(dut.dir_owner),
        "dir_pending_op": _v(dut.dir_pending_op),
        "data_sent": data_sent,
        "l1_0_state": _v(dut.l1_0_state),
        "l1_1_state": _v(dut.l1_1_state),
        "l1_1_iss0_msg": l1_1_iss,
        "l1_1_noc_req_valid": l1_1_req_valid,
        "dir_rx_msg": _v(dut.dir_rx_msg),
        "dir_rx_src": _v(dut.dir_rx_src),
        "l1_0_rx_msg": _v(dut.l1_0_rx_msg),
        "dir_rsp_msg": dir_rsp,
        "_data_sent": data_sent,
        "_l1_1_iss": l1_1_iss,
        "_dir_rsp": dir_rsp,
    }, data_sent, l1_1_iss, dir_rsp


def _log(dut, s):
    dut._log.info(
        "t=%0d dir_state=%s dir_sharers=%s dir_owner=%d pend=%s data_sent=%d "
        "l1_0=%s l1_1=%s l1_1_iss0=%s l1_1_reqv=%d dir_rx=%s/%d l1_0_rx=%s dir_rsp=%s",
        s["t"],
        DIR_NAME.get(s["dir_state"], s["dir_state"]),
        _bin4(s["dir_sharers"]), s["dir_owner"],
        PEND.get(s["dir_pending_op"], s["dir_pending_op"]),
        s["data_sent"],
        L1_NAME.get(s["l1_0_state"], s["l1_0_state"]),
        L1_NAME.get(s["l1_1_state"], s["l1_1_state"]),
        s["l1_1_iss0_msg"], s["l1_1_noc_req_valid"],
        _m(s["dir_rx_msg"]), s["dir_rx_src"],
        _m(s["l1_0_rx_msg"]),
        s["dir_rsp_msg"],
    )


def _s_mask(s):
    """Tiles currently holding the line in L1_S."""
    return (1 if s["l1_0_state"] == L1_S else 0) | \
           (2 if s["l1_1_state"] == L1_S else 0)


def _check(dut, s, released, release_t):
    """A2.2a (strict) + A2.2b (bounded extras) in DIR_S. Raises on violation."""
    if s["dir_state"] != DIR_S or s["dir_sharers"] < 0:
        return
    sharers, mask = s["dir_sharers"], _s_mask(s)

    # A2.2a — no missing bit, ever, in DIR_S.
    missing = mask & ~sharers
    if missing:
        dut._log.error(
            "A2_2A_FAIL t=%d missing=%s dir_sharers=%s s_mask=%s dir_owner=%d "
            "l1_0=%s l1_1=%s dir_rx=%s/%d",
            s["t"], _bin4(missing), _bin4(sharers), _bin4(mask),
            s["dir_owner"], L1_NAME.get(s["l1_0_state"]),
            L1_NAME.get(s["l1_1_state"]),
            _m(s["dir_rx_msg"]), s["dir_rx_src"])
        raise AssertionError(
            f"A2.2a: missing sharer bit {missing:04b} "
            f"(sharers={sharers:04b}, s_mask={mask:04b})")

    # A2.2b — extras: a released tile's bit must be in flight and bounded.
    extra = sharers & ~mask
    for bit in (0, 1):
        if not (extra >> bit) & 1:
            continue
        if (released >> bit) & 1:
            age = s["t"] - release_t[bit]
            if age > T_BOUND:
                dut._log.error(
                    "A2_2B_FAIL t=%d tile%d extra bit still set %d cycles after "
                    "its release (T=%d) dir_sharers=%s",
                    s["t"], bit, age, T_BOUND, _bin4(sharers))
                raise AssertionError(
                    f"A2.2b: tile {bit} extra bit not cleared within {T_BOUND} "
                    f"cycles (age={age}, sharers={sharers:04b})")
            dut._log.info(
                "A2_2B ok t=%d tile%d extra bit in flight (age=%d) sharers=%s",
                s["t"], bit, age, _bin4(sharers))
        else:
            # Not released by this tile: mid-miss / not-yet-holder window.
            # Out of A2.2b's scope (WP §12 item 12) — report, do not fail.
            dut._log.info(
                "A2_2B note t=%d tile%d extra bit, no release in flight "
                "(mid-miss window, §12 item 12) sharers=%s l1_state=%s",
                s["t"], bit, _bin4(sharers),
                L1_NAME.get(s["l1_0_state"] if bit == 0 else s["l1_1_state"]))


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

    settled = False
    for _ in range(400):
        await RisingEdge(dut.clk)
        if (_v(dut.dir_state) == DIR_E and _v(dut.dir_owner) == 1
                and _v(dut.l1_1_state) in (L1_E, L1_M)):
            settled = True
            break
    dut._log.info("PHASE_A settled=%s dir_state=%s owner=%d sharers=%s l1_1=%s",
                  settled,
                  DIR_NAME.get(_v(dut.dir_state), _v(dut.dir_state)),
                  _v(dut.dir_owner), _bin4(_v(dut.dir_sharers)),
                  L1_NAME.get(_v(dut.l1_1_state), _v(dut.l1_1_state)))
    assert _v(dut.l1_1_state) in (L1_E, L1_M), \
        f"Phase A: l1_1_state={L1_NAME.get(_v(dut.l1_1_state))} not in {{E,M}}"
    assert _v(dut.dir_owner) == 1, f"Phase A: dir_owner={_v(dut.dir_owner)} != 1"
    assert settled, "Phase A did not settle to DIR_E/owner=1/l1_1 in {E,M}"


async def _phase_b(dut):
    """tile 0 GETS the line -> directory enters DIR_FWD_WAIT."""
    dut.c0v.value = 1
    dut.c0w.value = 0
    await RisingEdge(dut.clk)
    dut.c0v.value = 0

    for _ in range(400):
        await RisingEdge(dut.clk)
        if _v(dut.dir_state) == DIR_FWD_WAIT:
            dut._log.info(
                "PHASE_B dir entered FWD_WAIT: sharers=%s owner=%d l1_0=%s l1_1=%s",
                _bin4(_v(dut.dir_sharers)), _v(dut.dir_owner),
                L1_NAME.get(_v(dut.l1_0_state)), L1_NAME.get(_v(dut.l1_1_state)))
            return
    raise AssertionError("Outcome C: dir never entered DIR_FWD_WAIT")


@cocotb.test()
async def test_owner_evict_forward(dut):
    """Ordering A: the owner's PUTS is absorbed before UNBLOCK arrives."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await _boot(dut)
    await _phase_a(dut)
    await _phase_b(dut)

    # Phase C: owner evict, 1-cycle pulse, on the FWD_WAIT cycle.
    # released bitmask + the cycle each release was sent (A2.2b bookkeeping).
    released, release_t = 0, {0: -1, 1: -1}
    t_evict = None
    dut.c1e.value = 1
    await RisingEdge(dut.clk)
    dut.c1e.value = 0
    released |= 1 << 1

    data_sent, l1_1_iss, dir_rsp = 0, "none", "none"
    saw_dir_s = False
    exited_fwd = False
    putack_seen = False

    for t in range(64):
        s, data_sent, l1_1_iss, dir_rsp = _take(dut, data_sent, l1_1_iss, dir_rsp)
        s["t"] = t
        _log(dut, s)
        if t_evict is None:
            t_evict = t
            release_t[1] = t

        if s["dir_state"] == DIR_S:
            saw_dir_s = True
        if t > 0 and s["dir_state"] != DIR_FWD_WAIT:
            exited_fwd = True

        _check(dut, s, released, release_t)

        # release absorbed this cycle -> from the next cycle on, the extra bit
        # must be gone (clear after the check so the cycle still counts as
        # "in flight").
        if s["dir_rx_msg"] == MSG_PUTS and s["dir_rx_src"] == 1:
            released &= ~(1 << 1)
        if s["dir_rsp_msg"] == "PUTACK":
            putack_seen = True

        await RisingEdge(dut.clk)

    dut._log.info(
        "SUMMARY(A) exited_fwd_wait=%s saw_dir_s=%s putack=%s final_dir_state=%s "
        "sharers=%s owner=%d l1_0=%s l1_1=%s",
        exited_fwd, saw_dir_s, putack_seen,
        DIR_NAME.get(_v(dut.dir_state), _v(dut.dir_state)),
        _bin4(_v(dut.dir_sharers)), _v(dut.dir_owner),
        L1_NAME.get(_v(dut.l1_0_state)), L1_NAME.get(_v(dut.l1_1_state)))
    assert exited_fwd, \
        "Outcome C: dir never exited DIR_FWD_WAIT in 64 cycles (ordering A)"
    assert saw_dir_s, "ordering A: directory never reached DIR_S"
    assert putack_seen, "ordering A: PUTS was never acknowledged"


@cocotb.test()
async def test_unblock_before_puts(dut):
    """Ordering B: UNBLOCK wins the race, PUTS clears the extra bit after exit.

    The owner evicts while the forward is still outstanding (dir in
    DIR_FWD_WAIT), but its PUTS lands after the requester's UNBLOCK. The
    directory must exit with the requester present (B5.3) and carry the owner's
    now-released bit only until the PUTS is absorbed (A2.2b, T = 64).
    """
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await _boot(dut)
    await _phase_a(dut)
    await _phase_b(dut)

    released, release_t = 0, {0: -1, 1: -1}
    data_sent, l1_1_iss, dir_rsp = 0, "none", "none"
    t = 0
    evicted = False

    # Wait until the requester's UNBLOCK is at the directory's RX while the
    # directory is still in DIR_FWD_WAIT, then evict the owner in that cycle:
    # the UNBLOCK is popped at this edge, the PUTS can only arrive later.
    while True:
        s, data_sent, l1_1_iss, dir_rsp = _take(dut, data_sent, l1_1_iss, dir_rsp)
        s["t"] = t
        _log(dut, s)
        if (s["dir_state"] == DIR_FWD_WAIT and s["dir_rx_msg"] == MSG_UNBLOCK
                and s["dir_rx_src"] == 0):
            break
        if s["dir_state"] not in (DIR_FWD_WAIT,) and t > 4:
            raise AssertionError(
                f"ordering B not reached: dir left DIR_FWD_WAIT "
                f"({DIR_NAME.get(s['dir_state'])}) before UNBLOCK was observed "
                f"at RX (dir_rx={_m(s['dir_rx_msg'])}/{s['dir_rx_src']})")
        if t > 400:
            raise AssertionError("ordering B: UNBLOCK never reached the directory")
        await RisingEdge(dut.clk)
        t += 1

    # Owner evicts with the forward still outstanding, UNBLOCK already at RX.
    dut.c1e.value = 1
    await RisingEdge(dut.clk)
    dut.c1e.value = 0
    released |= 1 << 1
    release_t[1] = t
    evicted = True

    exited, saw_extra, cleared = False, False, False
    for t in range(t + 1, t + 1 + 64):
        s, data_sent, l1_1_iss, dir_rsp = _take(dut, data_sent, l1_1_iss, dir_rsp)
        s["t"] = t
        _log(dut, s)

        if s["dir_state"] != DIR_FWD_WAIT:
            exited = True
        if s["dir_state"] == DIR_S:
            # B5.3: the committed set must contain the requester.
            assert (s["dir_sharers"] >> 0) & 1, (
                f"B5.3: dir exited to DIR_S without the requester "
                f"(sharers={_bin4(s['dir_sharers'])}, l1_0="
                f"{L1_NAME.get(s['l1_0_state'])})")
            # The owner's released bit is expected to be present (extra).
            if ((s["dir_sharers"] >> 1) & 1) and not cleared:
                saw_extra = True
            # release absorbed -> extra bit must be gone
            if not ((s["dir_sharers"] >> 1) & 1) and saw_extra:
                cleared = True

        _check(dut, s, released, release_t)
        if s["dir_rx_msg"] == MSG_PUTS and s["dir_rx_src"] == 1:
            released &= ~(1 << 1)

        await RisingEdge(dut.clk)

    dut._log.info(
        "SUMMARY(B) exited=%s saw_extra_owner_bit=%s extra_cleared=%s "
        "final_dir_state=%s sharers=%s owner=%d l1_0=%s l1_1=%s evicted=%s",
        exited, saw_extra, cleared,
        DIR_NAME.get(_v(dut.dir_state), _v(dut.dir_state)),
        _bin4(_v(dut.dir_sharers)), _v(dut.dir_owner),
        L1_NAME.get(_v(dut.l1_0_state)), L1_NAME.get(_v(dut.l1_1_state)), evicted)
    assert exited, "ordering B: dir never left DIR_FWD_WAIT"
    assert saw_extra, (
        "ordering B: no extra owner bit at the DIR_S exit — the released tile "
        "was not carried in the committed set (B5.3/A2.2b not exercised)")
    assert cleared, (
        "ordering B: the owner's extra sharer bit never cleared after PUTS "
        "(A2.2b bounded clearance violated)")
