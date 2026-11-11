"""F1-F8 directed tests against the real RTL, with the reference-model shadow.

Every directed scenario is checked at its transaction boundaries against
tb/ref_model/shadow_l1_dir.py (L1 state/data, dir state/owner/sharers, bank
data/dirty). The F1 scenario is duplicated here with the shadow; the
mutation-gated F1 test lives in test_f1_forward.py.
"""
import pathlib
import sys

import cocotb
from cocotb.triggers import RisingEdge, Timer

from tb_common import (Taps, BankTap, boot, reset, issue, pulse_evict, wait_rsp,
                       wait_for, setup_owner, l1_state, dir_state, dir_owner,
                       dir_sharers, LINE, WDATA, RDATA,
                       MSG_GETS, MSG_GETM, MSG_PUTS, MSG_PUTM, MSG_UNBLOCK,
                       MSG_INV, MSG_INVACK, MSG_DATA, MSG_FWD_GETS,
                       MSG_FWD_GETM, MSG_DATAFWD, MSG_PUTACK,
                       L1_I, L1_S, L1_E, L1_M, L1_IM_D, L1_EI_A, L1_MI_A,
                       DIR_I, DIR_S, DIR_E, DIR_M, DIR_FWD_WAIT)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "ref_model"))
from shadow_l1_dir import Shadow


@cocotb.test()
async def test_f1_forward_shadow(dut):
    """F1 with the reference shadow: clean forward, E->S, DIR_S, sharers 3."""
    taps, sh = Taps(dut), Shadow()
    await boot(dut, taps)
    await setup_owner(dut, 1, is_write=False, shadow=sh)
    sh.sync(taps)
    sh.check(dut, "F1 setup")

    sh.core_req(0, "GETS", 0)
    await issue(dut, 0, LINE, is_write=False)
    assert await wait_rsp(dut, 0), "F1: requester got no DATA"
    assert await wait_for(dut, lambda: dir_state(dut) == DIR_S), "F1: dir != S"
    sh.sync(taps)
    sh.check(dut, "F1")
    assert dir_sharers(dut) == 0b0011


@cocotb.test()
async def test_f2_dirty_owner_getm(dut):
    """F2: DIR_M + GETM(other) -> FWD_GETM, M->I, bank dirty, owner=req, DIR_M."""
    taps, bank, sh = Taps(dut), BankTap(), Shadow()
    await boot(dut, taps, bank)
    await setup_owner(dut, 1, is_write=True, shadow=sh)
    sh.sync(taps)
    sh.check(dut, "F2 setup")
    bank.writes.clear()

    sh.core_req(0, "GETM", RDATA)
    await issue(dut, 0, LINE, is_write=True, wdata=RDATA)
    assert await wait_rsp(dut, 0), "F2: requester got no DATA"
    assert await wait_for(dut, lambda: dir_state(dut) == DIR_M and dir_owner(dut) == 0), \
        f"F2: dir {dir_state(dut)} owner {dir_owner(dut)}"
    sh.sync(taps)
    sh.check(dut, "F2")

    fwd = [t for t in taps.dir_l1 if t["msg"] == MSG_FWD_GETM]
    assert len(fwd) == 1 and fwd[0]["dst"] == 1, f"F2: FWD_GETM {fwd}"
    df = [t for t in taps.l1_dir if t["msg"] == MSG_DATAFWD]
    assert len(df) == 1 and df[0]["we"] == 1, f"F2: DATAFWD {df} (dirty required)"
    assert l1_state(dut, 1) == L1_I, f"F2: old owner {l1_state(dut,1)} != I"
    assert l1_state(dut, 0) == L1_M, f"F2: requester {l1_state(dut,0)} != M"
    assert any(a == LINE and d == WDATA for a, d in bank.writes), \
        f"F2: bank write {bank.writes} (expected dirty owner data)"


@cocotb.test()
async def test_f3_dirty_owner_gets(dut):
    """F3: DIR_M + GETS(other) -> FWD_GETS, M->S, bank dirty, sharers, DIR_S."""
    taps, bank, sh = Taps(dut), BankTap(), Shadow()
    await boot(dut, taps, bank)
    await setup_owner(dut, 1, is_write=True, shadow=sh)
    sh.sync(taps)
    sh.check(dut, "F3 setup")
    bank.writes.clear()

    sh.core_req(0, "GETS", 0)
    await issue(dut, 0, LINE, is_write=False)
    assert await wait_rsp(dut, 0), "F3: requester got no DATA"
    assert await wait_for(dut, lambda: dir_state(dut) == DIR_S), \
        f"F3: dir {dir_state(dut)} != S"
    sh.sync(taps)
    sh.check(dut, "F3")

    fwd = [t for t in taps.dir_l1 if t["msg"] == MSG_FWD_GETS]
    assert len(fwd) == 1 and fwd[0]["dst"] == 1, f"F3: FWD_GETS {fwd}"
    df = [t for t in taps.l1_dir if t["msg"] == MSG_DATAFWD]
    assert len(df) == 1 and df[0]["we"] == 1, f"F3: DATAFWD {df} (dirty required)"
    assert l1_state(dut, 1) == L1_S, f"F3: old owner {l1_state(dut,1)} != S"
    assert l1_state(dut, 0) == L1_S, f"F3: requester {l1_state(dut,0)} != S"
    assert dir_sharers(dut) == 0b0011, f"F3: sharers {dir_sharers(dut):b}"
    assert any(a == LINE and d == WDATA for a, d in bank.writes), \
        f"F3: bank write {bank.writes} (expected dirty owner data)"


@cocotb.test()
async def test_f4_clean_owner_getm(dut):
    """F4: DIR_E + GETM(other) -> FWD_GETM, E->I, bank write clean, owner=req, DIR_M."""
    taps, bank, sh = Taps(dut), BankTap(), Shadow()
    await boot(dut, taps, bank)
    await setup_owner(dut, 1, is_write=False, shadow=sh)
    sh.sync(taps)
    sh.check(dut, "F4 setup")
    bank.writes.clear()

    sh.core_req(0, "GETM", RDATA)
    await issue(dut, 0, LINE, is_write=True, wdata=RDATA)
    assert await wait_rsp(dut, 0), "F4: requester got no DATA"
    assert await wait_for(dut, lambda: dir_state(dut) == DIR_M and dir_owner(dut) == 0), \
        f"F4: dir {dir_state(dut)} owner {dir_owner(dut)}"
    sh.sync(taps)
    sh.check(dut, "F4")

    fwd = [t for t in taps.dir_l1 if t["msg"] == MSG_FWD_GETM]
    assert len(fwd) == 1 and fwd[0]["dst"] == 1, f"F4: FWD_GETM {fwd}"
    df = [t for t in taps.l1_dir if t["msg"] == MSG_DATAFWD]
    assert len(df) == 1 and df[0]["we"] == 0, f"F4: DATAFWD {df} (clean required)"
    assert l1_state(dut, 1) == L1_I, f"F4: old owner {l1_state(dut,1)} != I"
    assert l1_state(dut, 0) == L1_M, f"F4: requester {l1_state(dut,0)} != M"
    assert any(a == LINE for a, _ in bank.writes), f"F4: no bank write {bank.writes}"


@cocotb.test()
async def test_f5_silent_upgrade_evict(dut):
    """F5: DIR_E + silent E->M then PUTM -> DIR_I, bank dirty, PUTACK."""
    taps, bank, sh = Taps(dut), BankTap(), Shadow()
    await boot(dut, taps, bank)
    await setup_owner(dut, 1, is_write=False, shadow=sh)
    sh.sync(taps)
    sh.check(dut, "F5 setup")
    n_before = len(taps.l1_dir)

    sh.core_req(1, "GETM", WDATA)
    await issue(dut, 1, LINE, is_write=True, wdata=WDATA)
    assert await wait_rsp(dut, 1), "F5: store hit got no response"
    for _ in range(6):
        await RisingEdge(dut.clk)
        await Timer(1, units="ps")
    assert l1_state(dut, 1) == L1_M, f"F5: silent upgrade missing ({l1_state(dut,1)})"
    assert dir_state(dut) == DIR_E, f"F5: dir left E on silent upgrade ({dir_state(dut)})"
    assert len(taps.l1_dir) == n_before, \
        f"F5: silent upgrade emitted {taps.l1_dir[n_before:]}"
    sh.sync(taps)
    sh.check(dut, "F5 silent")

    bank.writes.clear()
    await pulse_evict(dut, 1)
    assert await wait_for(dut, lambda: l1_state(dut, 1) == L1_I), "F5: owner did not release"
    assert await wait_for(dut, lambda: dir_state(dut) == DIR_I), "F5: dir did not return to I"
    sh.sync(taps)
    sh.check(dut, "F5 evict")

    puts = [t for t in taps.l1_dir if t["msg"] == MSG_PUTM]
    assert len(puts) == 1 and puts[0]["len"] == 9, f"F5: PUTM {puts}"
    assert any(a == LINE and d == WDATA for a, d in bank.writes), \
        f"F5: bank write {bank.writes} (expected dirty owner data)"
    acks = [t for t in taps.dir_l1 if t["msg"] == MSG_PUTACK]
    assert acks, "F5: no PUTACK from the directory"


@cocotb.test()
async def test_f6_evict_during_forward_clean(dut):
    """F6: FWD_GETS in flight, owner evicts (EI_A) -> defensive INVACK, dir absorbs PUTS."""
    taps, bank, sh = Taps(dut), BankTap(), Shadow()
    await boot(dut, taps, bank)
    await setup_owner(dut, 1, is_write=False, shadow=sh)
    sh.sync(taps)
    sh.check(dut, "F6 setup")

    sh.core_req(0, "GETS", 0)
    await issue(dut, 0, LINE, is_write=False)
    assert await wait_for(dut, lambda: dir_state(dut) == DIR_FWD_WAIT), \
        "F6: dir never entered FWD_WAIT"
    await pulse_evict(dut, 1)                      # evict races the forward

    assert await wait_for(dut, lambda: dir_state(dut) == DIR_S), \
        f"F6: dir {dir_state(dut)} != S"
    assert l1_state(dut, 0) == L1_S, f"F6: requester {l1_state(dut,0)} != S"
    assert l1_state(dut, 1) == L1_I, f"F6: owner {l1_state(dut,1)} != I"
    assert dir_sharers(dut) == 0b0001, f"F6: sharers {dir_sharers(dut):b}"
    sh.sync(taps)
    sh.check(dut, "F6")

    assert not any(t["msg"] == MSG_DATAFWD for t in taps.l1_dir), \
        "F6: owner sent DATAFWD instead of evicting"
    assert any(t["msg"] == MSG_INVACK for t in taps.l1_dir), \
        "F6: no defensive INVACK from EI_A"
    assert any(t["msg"] == MSG_PUTS for t in taps.l1_dir), "F6: no PUTS"
    datas = [t for t in taps.dir_l1 if t["msg"] == MSG_DATA and t["dst"] == 0]
    assert datas and datas[-1]["excl"] == 0, f"F6: DATA {datas} (shared required)"


@cocotb.test()
async def test_f7_evict_during_forward_dirty(dut):
    """F7: FWD_GETM in flight, owner evicts (MI_A) -> PUTM satisfies the forward."""
    taps, bank, sh = Taps(dut), BankTap(), Shadow()
    await boot(dut, taps, bank)
    await setup_owner(dut, 1, is_write=True, shadow=sh)
    sh.sync(taps)
    sh.check(dut, "F7 setup")
    bank.writes.clear()

    sh.core_req(0, "GETM", RDATA)
    await issue(dut, 0, LINE, is_write=True, wdata=RDATA)
    assert await wait_for(dut, lambda: dir_state(dut) == DIR_FWD_WAIT), \
        "F7: dir never entered FWD_WAIT"
    await pulse_evict(dut, 1)

    assert await wait_for(dut, lambda: dir_state(dut) == DIR_M and dir_owner(dut) == 0), \
        f"F7: dir {dir_state(dut)} owner {dir_owner(dut)}"
    assert l1_state(dut, 0) == L1_M, f"F7: requester {l1_state(dut,0)} != M"
    assert l1_state(dut, 1) == L1_I, f"F7: owner {l1_state(dut,1)} != I"
    sh.sync(taps)
    sh.check(dut, "F7")

    assert not any(t["msg"] == MSG_DATAFWD for t in taps.l1_dir), \
        "F7: owner sent DATAFWD instead of PUTM"
    assert any(t["msg"] == MSG_PUTM for t in taps.l1_dir), "F7: no PUTM"
    assert any(t["msg"] == MSG_INVACK for t in taps.l1_dir), \
        "F7: no defensive INVACK from MI_A"
    assert any(a == LINE and d == WDATA for a, d in bank.writes), \
        f"F7: bank write {bank.writes} (expected PUTM data)"


@cocotb.test()
async def test_f8_exclusive_bit(dut):
    """F8: forward GETS grants excl=0 (requester S); forward GETM grants excl=1 (requester M)."""
    taps, sh = Taps(dut), Shadow()
    await boot(dut, taps)
    await setup_owner(dut, 1, is_write=False, shadow=sh)
    sh.sync(taps)
    sh.check(dut, "F8a setup")

    sh.core_req(0, "GETS", 0)
    await issue(dut, 0, LINE, is_write=False)
    assert await wait_rsp(dut, 0), "F8: GETS forward got no DATA"
    assert await wait_for(dut, lambda: dir_state(dut) == DIR_S), "F8: dir != S"
    sh.sync(taps)
    sh.check(dut, "F8a")
    datas = [t for t in taps.dir_l1 if t["msg"] == MSG_DATA and t["dst"] == 0]
    assert datas and datas[-1]["excl"] == 0, f"F8: GETS DATA {datas} (excl must be 0)"
    assert l1_state(dut, 0) == L1_S, f"F8: requester {l1_state(dut,0)} != S"

    await reset(dut)
    sh.reset()
    taps.l1_dir.clear()
    taps.dir_l1.clear()
    taps.events.clear()
    await setup_owner(dut, 1, is_write=False, shadow=sh)
    sh.sync(taps)
    sh.check(dut, "F8b setup")

    sh.core_req(0, "GETM", RDATA)
    await issue(dut, 0, LINE, is_write=True, wdata=RDATA)
    assert await wait_rsp(dut, 0), "F8: GETM forward got no DATA"
    assert await wait_for(dut, lambda: dir_state(dut) == DIR_M), "F8: dir != M"
    sh.sync(taps)
    sh.check(dut, "F8b")
    datas = [t for t in taps.dir_l1 if t["msg"] == MSG_DATA and t["dst"] == 0]
    assert datas and datas[-1]["excl"] == 1, f"F8: GETM DATA {datas} (excl must be 1)"
    assert l1_state(dut, 0) == L1_M, f"F8: requester {l1_state(dut,0)} != M"
