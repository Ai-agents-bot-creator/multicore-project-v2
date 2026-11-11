"""F1 directed test — forward release, clean owner (WP/SLICE §5).

Flow (all through the real RTL):
  1. tile 1 GETS line 0x40  -> DIR_I fill, grant E, tile1 E
  2. tile 0 GETS line 0x40  -> DIR_E + GETS(other): FWD_GETS to tile1,
     tile1 E->S + DATAFWD(clean) -> dir -> DATA to tile0, dir -> DIR_S

Observation point: the DATAFWD head flit on the L1->dir bus (bit [39] = dirty).
The two negative controls PASS only while their fault is present; they are
expected to FAIL against the correct RTL (mutation testing proves the
discrimination, see run_mutations.py).
"""
import cocotb
from cocotb.triggers import Timer, RisingEdge
from cocotb.clock import Clock

# tile_pkg constants (2x2)
HDR_MSG_LO  = 44
HDR_HEAD    = 41
HDR_WE      = 39
HDR_EXCL    = 38
HDR_ADDR_LO = 0
HDR_SRC_LO  = 48
HDR_DEST_LO = 56
HDR_LEN_LO  = 32

MSG_GETS, MSG_GETM, MSG_PUTS, MSG_PUTM = 0, 1, 2, 3
MSG_UNBLOCK, MSG_INV, MSG_INVACK, MSG_DATA = 4, 5, 6, 7
MSG_FWD_GETS, MSG_FWD_GETM, MSG_DATAFWD, MSG_PUTACK = 8, 9, 10, 11

L1_I, L1_S, L1_E, L1_M = 0, 1, 2, 3
DIR_I, DIR_S, DIR_E, DIR_M, DIR_MEM_WAIT, DIR_FWD_WAIT = 0, 1, 2, 3, 4, 5

LINE = 0x40


class Taps:
    """Head-flit recorders for both directions."""

    def __init__(self, dut):
        self.l1_dir = []
        self.dir_l1 = []

    async def run(self, dut):
        while True:
            await RisingEdge(dut.clk)
            await Timer(1, units="ps")
            if int(dut.noc_l1_dir_valid.value):
                f = int(dut.noc_l1_dir_flit.value)
                if (f >> HDR_HEAD) & 1:
                    self.l1_dir.append(self._dec(f))
            if int(dut.noc_dir_l1_valid.value):
                f = int(dut.noc_dir_l1_flit.value)
                if (f >> HDR_HEAD) & 1:
                    self.dir_l1.append(self._dec(f))

    @staticmethod
    def _dec(f):
        return dict(
            msg=(f >> HDR_MSG_LO) & 0xF,
            src=(f >> HDR_SRC_LO) & 0x3,
            dst=(f >> HDR_DEST_LO) & 0x3,
            we=(f >> HDR_WE) & 1,
            excl=(f >> HDR_EXCL) & 1,
            addr=f & 0xFFFF_FFFF,
            len=(f >> HDR_LEN_LO) & 0x3F,
        )


async def _reset(dut):
    dut.rst_n.value = 0
    for core in (0, 1):
        getattr(dut, f"core{core}_req_valid").value = 0
        getattr(dut, f"core{core}_req_is_write").value = 0
        getattr(dut, f"core{core}_req_addr").value = 0
        getattr(dut, f"core{core}_req_wdata").value = 0
        getattr(dut, f"core{core}_evict_valid").value = 0
    await Timer(22, units="ns")
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, units="ps")


async def _issue(dut, core, addr, is_write, wdata=0):
    """Hold the core request until the L1 accepts it (state leaves stable or rsp)."""
    v = getattr(dut, f"core{core}_req_valid")
    w = getattr(dut, f"core{core}_req_is_write")
    a = getattr(dut, f"core{core}_req_addr")
    d = getattr(dut, f"core{core}_req_wdata")
    v.value = 1
    w.value = 1 if is_write else 0
    a.value = addr
    d.value = wdata
    await RisingEdge(dut.clk)
    await Timer(1, units="ps")
    v.value = 0
    w.value = 0
    a.value = 0
    d.value = 0


async def _wait_rsp(dut, core, cycles=200):
    rv = getattr(dut, f"core{core}_rsp_valid")
    for _ in range(cycles):
        await RisingEdge(dut.clk)
        await Timer(1, units="ps")
        if int(rv.value):
            return True
    return False


async def _wait_for(dut, pred, cycles=200):
    for _ in range(cycles):
        if pred():
            return True
        await RisingEdge(dut.clk)
        await Timer(1, units="ps")
    return False


def _l1_state(dut, core):
    return int(getattr(dut, f"l1_{core}_state").value)


def _dir_state(dut):
    return int(dut.dir_state.value)


async def _boot(dut, taps):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await Timer(1, units="ns")
    await _reset(dut)
    cocotb.start_soon(taps.run(dut))


async def _setup_clean_owner(dut):
    """Line 0x40 held in E by tile 1 (DIR_I fill)."""
    await _issue(dut, 1, LINE, is_write=0)
    assert await _wait_rsp(dut, 1), "setup: tile1 GETS got no DATA"
    assert _l1_state(dut, 1) == L1_E, f"setup: tile1 {_l1_state(dut,1)} != E"
    assert await _wait_for(dut, lambda: _dir_state(dut) == DIR_E), \
        f"setup: dir {_dir_state(dut)} != E (UNBLOCK not absorbed)"


@cocotb.test()
async def test_f1_forward_positive(dut):
    """F1 positive: DIR_E + GETS(other) -> FWD_GETS, DATAFWD clean, DIR_S."""
    taps = Taps(dut)
    await _boot(dut, taps)
    await _setup_clean_owner(dut)

    await _issue(dut, 0, LINE, is_write=0)
    assert await _wait_rsp(dut, 0), "F1: tile0 GETS got no DATA"
    assert await _wait_for(dut, lambda: _dir_state(dut) == DIR_S), \
        f"F1: dir stayed {_dir_state(dut)} (expected S after UNBLOCK)"

    fwds = [t for t in taps.l1_dir if t["msg"] == MSG_DATAFWD]
    assert len(fwds) == 1, f"F1: expected 1 DATAFWD, saw {fwds}"
    assert fwds[0]["we"] == 0, "F1: DATAFWD dirty bit [39] must be 0 for clean owner"
    assert fwds[0]["src"] == 1, f"F1: DATAFWD src {fwds[0]['src']} != 1"
    assert _l1_state(dut, 1) == L1_S, f"F1: owner {_l1_state(dut,1)} != S"
    assert _l1_state(dut, 0) == L1_S, f"F1: requester {_l1_state(dut,0)} != S"
    assert int(dut.dir_0.sharers.value) == 0b0011, \
        f"F1: sharers {int(dut.dir_0.sharers.value):b} != 0011"
    assert int(dut.dir_0.owner.value) == 0, "F1: owner must be invalid in DIR_S"
    dut._log.info("F1 positive: DATAFWD clean, E->S, DIR_S, sharers=01+10")


@cocotb.test()
async def test_f1_forward_negative_skip_fwd(dut):
    """NEG1: passes only if the directory omits FWD_GETS (mutation C).

    Asserts the injected fault itself: the directory must reach FWD_WAIT and
    emit no FWD_GETS. Against the correct RTL the FWD_GETS is present, so this
    control fails.
    """
    taps = Taps(dut)
    await _boot(dut, taps)
    await _setup_clean_owner(dut)

    await _issue(dut, 0, LINE, is_write=0)
    assert await _wait_for(dut, lambda: _dir_state(dut) == DIR_FWD_WAIT), \
        "NEG1: directory never entered FWD_WAIT - scenario did not reach the mutation"
    for _ in range(40):                       # let any queued FWD reach the bus
        await RisingEdge(dut.clk)
        await Timer(1, units="ps")
    fwd_sent = [t for t in taps.dir_l1 if t["msg"] == MSG_FWD_GETS]
    assert not fwd_sent, "NEG1: FWD_GETS present - skip-fault not present"


@cocotb.test()
async def test_f1_forward_negative_dirty_bit(dut):
    """NEG2: passes only if the clean owner sends DATAFWD dirty (mutation B)."""
    taps = Taps(dut)
    await _boot(dut, taps)
    await _setup_clean_owner(dut)

    await _issue(dut, 0, LINE, is_write=0)
    assert await _wait_rsp(dut, 0), "NEG2: no DATAFWD - dirty fault unobservable"
    fwds = [t for t in taps.l1_dir if t["msg"] == MSG_DATAFWD]
    assert len(fwds) == 1, f"NEG2: expected 1 DATAFWD, saw {fwds}"
    assert fwds[0]["we"] == 1, "NEG2: dirty bit [39]=0 - dirty fault not present"
