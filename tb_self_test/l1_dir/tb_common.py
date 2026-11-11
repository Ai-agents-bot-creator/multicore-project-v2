"""Shared helpers for the F1-F8 directed tests (real RTL)."""
import cocotb
from cocotb.triggers import Timer, RisingEdge
from cocotb.clock import Clock

# tile_pkg constants
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

L1_I, L1_S, L1_E, L1_M, L1_IS_D, L1_IM_D, L1_SM_D, L1_EI_A, L1_MI_A = range(9)
DIR_I, DIR_S, DIR_E, DIR_M, DIR_MEM_WAIT, DIR_FWD_WAIT, DIR_INV_WAIT = range(7)

LINE = 0x40
WDATA = 0xDD << 504              # recognizable 512-bit store pattern
RDATA = 0xAA << 504


class Taps:
    """Head-flit recorders for both NoC directions."""

    def __init__(self, dut):
        self.l1_dir = []
        self.dir_l1 = []
        self.events = []          # ordered head flits: ("l1"|"d1", decoded)

    async def run(self, dut):
        while True:
            await RisingEdge(dut.clk)
            await Timer(1, units="ps")
            if int(dut.noc_l1_dir_valid.value):
                f = int(dut.noc_l1_dir_flit.value)
                if (f >> HDR_HEAD) & 1:
                    ev = self._dec(f)
                    self.l1_dir.append(ev)
                    self.events.append(("l1", ev))
            if int(dut.noc_dir_l1_valid.value):
                f = int(dut.noc_dir_l1_flit.value)
                if (f >> HDR_HEAD) & 1:
                    ev = self._dec(f)
                    self.dir_l1.append(ev)
                    self.events.append(("d1", ev))

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


class BankTap:
    """Records directory writes to the L2 bank model."""

    def __init__(self):
        self.writes = []

    async def run(self, dut):
        while True:
            await RisingEdge(dut.clk)
            await Timer(1, units="ps")
            if int(dut.bank_req_valid.value) and int(dut.bank_req_is_write.value):
                self.writes.append((int(dut.bank_req_addr.value),
                                    int(dut.bank_req_wdata.value)))


async def reset(dut):
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


async def issue(dut, core, addr, is_write, wdata=0):
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


async def pulse_evict(dut, core):
    e = getattr(dut, f"core{core}_evict_valid")
    e.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, units="ps")
    e.value = 0


async def wait_rsp(dut, core, cycles=300):
    rv = getattr(dut, f"core{core}_rsp_valid")
    for _ in range(cycles):
        if int(rv.value):          # a store hit responds in the request cycle
            return True
        await RisingEdge(dut.clk)
        await Timer(1, units="ps")
    return int(rv.value) == 1


async def wait_for(dut, pred, cycles=300):
    for _ in range(cycles):
        if pred():
            return True
        await RisingEdge(dut.clk)
        await Timer(1, units="ps")
    return False


def l1_state(dut, core):
    return int(getattr(dut, f"l1_{core}_state").value)


def dir_state(dut):
    return int(dut.dir_state.value)


def dir_owner(dut):
    return int(dut.dir_0.owner.value)


def dir_sharers(dut):
    return int(dut.dir_0.sharers.value)


async def boot(dut, taps=None, banktap=None):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await Timer(1, units="ns")
    await reset(dut)
    if taps is not None:
        cocotb.start_soon(taps.run(dut))
    if banktap is not None:
        cocotb.start_soon(banktap.run(dut))


async def setup_owner(dut, core, is_write, shadow=None):
    """Bring `core` to E (read) or M (store) on LINE with the directory in lockstep."""
    if shadow is not None:
        shadow.core_req(core, "GETM" if is_write else "GETS", WDATA)
    await issue(dut, core, LINE, is_write, wdata=WDATA)
    assert await wait_rsp(dut, core), f"setup: core{core} got no DATA"
    want = L1_M if is_write else L1_E
    assert l1_state(dut, core) == want, \
        f"setup: core{core} state {l1_state(dut, core)} != {want}"
    want_dir = DIR_M if is_write else DIR_E
    assert await wait_for(dut, lambda: dir_state(dut) == want_dir), \
        f"setup: dir {dir_state(dut)} != {want_dir}"
