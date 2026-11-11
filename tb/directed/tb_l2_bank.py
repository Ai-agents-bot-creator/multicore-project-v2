"""
tb_l2_bank.py — Directed unit tests for l2_bank.sv
Tests: B1 clean miss/fill, B2 hit, B3 PLRU eviction, B4 dirty write-back flag
Requires: cocotb + verilator; run via: pytest --co or cocotb-run
"""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

# ── constants must match tile_pkg ─────────────────────────────────────────────
L2_SETS   = 8
L2_WAYS   = 4
LINE_BITS = 512
ADDR_W    = 32
HOME_HI   = 12   # 2×2 config: HOME_HI=12
L1_SET_HI = 7
L1_SET_LO = 6
L2_SET_HI = 10
L2_SET_LO = 8

def mk_addr(tag_upper, l1_set_bits, l2_set, offset=0):
    """Build a 32-bit address from field values (2×2 config)."""
    # addr[31:HOME_HI+1] = tag_upper (bits 31:13 = 19 bits)
    # addr[HOME_HI:L2_SET_HI+1] = home (bits 12:11 = 2 bits) — fixed 0 for simplicity
    # addr[L2_SET_HI:L2_SET_LO] = l2_set (bits 10:8 = 3 bits)
    # addr[L1_SET_HI:L1_SET_LO] = l1_set_bits (bits 7:6 = 2 bits)
    # addr[5:0] = offset
    return ((tag_upper & 0x7FFFF) << 13) | (l2_set << 8) | (l1_set_bits << 6) | offset

async def reset(dut):
    dut.rst_n.value = 0
    dut.req_valid.value = 0
    dut.req_we.value = 0
    dut.req_dirty.value = 0
    dut.req_addr.value = 0
    dut.req_wdata.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

async def do_read(dut, addr):
    dut.req_valid.value = 1
    dut.req_addr.value  = addr
    dut.req_we.value    = 0
    await RisingEdge(dut.clk)
    hit   = int(dut.resp_hit.value)
    rdata = int(dut.resp_rdata.value)
    dirty = int(dut.resp_dirty.value)
    dut.req_valid.value = 0
    return hit, rdata, dirty

async def do_fill(dut, addr, data, dirty=0):
    dut.req_valid.value = 1
    dut.req_addr.value  = addr
    dut.req_we.value    = 1
    dut.req_dirty.value = dirty
    dut.req_wdata.value = data
    await RisingEdge(dut.clk)
    dut.req_valid.value = 0
    dut.req_we.value    = 0

@cocotb.test()
async def test_B1_clean_miss(dut):
    """B1: Fresh bank — a read to any address misses."""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)
    addr = mk_addr(0x1, 0, 0)
    hit, _, _ = await do_read(dut, addr)
    assert hit == 0, f"Expected miss on cold bank, got hit"

@cocotb.test()
async def test_B2_fill_then_hit(dut):
    """B2: Fill a line, then read it back — must hit with correct data."""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)
    addr  = mk_addr(0x2, 1, 3)
    wdata = (0xDEADBEEF << 480) | 0x12345678
    await do_fill(dut, addr, wdata, dirty=0)
    hit, rdata, dirty = await do_read(dut, addr)
    assert hit   == 1,     f"Expected hit after fill"
    assert rdata == wdata, f"Data mismatch: {rdata:#x} != {wdata:#x}"
    assert dirty == 0,     f"Expected dirty=0 on clean fill"

@cocotb.test()
async def test_B3_dirty_fill(dut):
    """B3: Dirty fill — dirty bit must be set on the installed line."""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)
    addr  = mk_addr(0x3, 2, 5)
    wdata = (0xCAFEBABE << 480) | 0xABCD
    await do_fill(dut, addr, wdata, dirty=1)
    hit, rdata, dirty_out = await do_read(dut, addr)
    assert hit       == 1,     "Expected hit"
    assert dirty_out == 1,     "Expected dirty=1 on dirty fill"
    assert rdata     == wdata, "Data mismatch"

@cocotb.test()
async def test_B4_plru_eviction(dut):
    """B4: Fill 4 lines into the same set — 5th fill must evict PLRU victim."""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)
    SET = 2
    addrs = [mk_addr(i + 1, 0, SET) for i in range(4)]
    datas = [(0xAA + i) << 480 for i in range(4)]

    # Fill 4 ways
    for a, d in zip(addrs, datas):
        await do_fill(dut, a, d)

    # All 4 must hit
    for a, d in zip(addrs, datas):
        hit, rdata, _ = await do_read(dut, a)
        assert hit == 1,    f"Expected hit for addr {a:#x}"
        assert rdata == d,  f"Data mismatch for addr {a:#x}"

    # 5th fill to same set — should evict PLRU victim; victim read is on the
    # output lines (victim_data, victim_dirty, victim_valid) before the write.
    addr5 = mk_addr(0x10, 0, SET)
    data5 = 0x55 << 480
    await do_fill(dut, addr5, data5)

    # 5th line must hit
    hit, rdata, _ = await do_read(dut, addr5)
    assert hit == 1,    "5th line must hit after fill"
    assert rdata == data5, "5th line data mismatch"

    # Exactly one of the original 4 is now a miss
    misses = 0
    for a in addrs:
        h, _, _ = await do_read(dut, a)
        if not h:
            misses += 1
    assert misses == 1, f"Expected exactly 1 eviction, got {misses} misses"

