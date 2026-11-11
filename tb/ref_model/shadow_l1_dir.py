"""Transaction-level reference shadow for the F1-F8 forward slice.

The shadow is driven by the same operations the directed test issues plus the
observed NoC head flits. It encodes WP Appendix A (L1) and Appendix B
(directory) transitions, and tracks the L1 line data and the L2 bank contents.
`check(dut)` compares every observable the slice scoreboard owns:

  L1 state, L1 data, dir state, dir owner, dir sharers, bank data, bank dirty.

A mismatch raises AssertionError with the field and both values.
"""
from tb_common import (LINE, MSG_GETS, MSG_GETM, MSG_PUTS, MSG_PUTM,
                       MSG_UNBLOCK, MSG_INV, MSG_INVACK, MSG_DATA,
                       MSG_FWD_GETS, MSG_FWD_GETM, MSG_DATAFWD, MSG_PUTACK,
                       L1_I, L1_S, L1_E, L1_M, L1_IS_D, L1_IM_D, L1_SM_D,
                       L1_EI_A, L1_MI_A,
                       DIR_I, DIR_S, DIR_E, DIR_M, DIR_MEM_WAIT,
                       DIR_FWD_WAIT, DIR_INV_WAIT)

STATE_INT = {
    "I": L1_I, "S": L1_S, "E": L1_E, "M": L1_M,
    "IS_D": L1_IS_D, "IM_D": L1_IM_D, "SM_D": L1_SM_D,
    "EI_A": L1_EI_A, "MI_A": L1_MI_A,
}
DIR_INT = {"I": DIR_I, "S": DIR_S, "E": DIR_E, "M": DIR_M,
           "MEM_WAIT": DIR_MEM_WAIT, "FWD_WAIT": DIR_FWD_WAIT,
           "INV_WAIT": DIR_INV_WAIT}


class Shadow:
    def __init__(self):
        self.reset()

    def reset(self):
        self.l1 = ["I", "I"]
        self.data = [0, 0]
        self.wdata = [0, 0]
        self.pending = [None, None]
        self.dir = "I"
        self.owner = None
        self.sharers = set()
        self.pending_op = None
        self.req = None
        self.inv_mask = set()
        self.bank = {}                 # addr -> (data, dirty)
        self.bank_written = set()      # tb bm_dirty is a write marker, not spec dirty
        self.next_data = 0
        self.next_excl = 0
        self.fwd_kind = None
        self.nseen = 0

    # ── test-side driver ────────────────────────────────────────────────────
    def core_req(self, tile, op, wdata):
        st = self.l1[tile]
        if st in ("S", "E", "M"):
            if op == "GETM":
                self.wdata[tile] = wdata
                if st in ("E", "M"):
                    self.data[tile] = wdata      # silent upgrade / write in place
                    self.l1[tile] = "M"
                else:                             # S store hit
                    self.pending[tile] = "GETM"
                    self.l1[tile] = "SM_D"
            # read hit: no state change
        else:
            self.pending[tile] = op
            self.wdata[tile] = wdata
            self.l1[tile] = "IS_D" if op == "GETS" else "IM_D"

    def sync(self, taps):
        while self.nseen < len(taps.events):
            direction, ev = taps.events[self.nseen]
            self.nseen += 1
            self._feed(direction, ev)

    # ── message model ───────────────────────────────────────────────────────
    def _bank_read(self, addr):
        return self.bank.get(addr, (0, 0))[0]

    def _feed(self, direction, ev):
        m, src, dst = ev["msg"], ev["src"], ev["dst"]
        if direction == "l1":
            self._l1_to_dir(m, src, ev)
        else:
            self._dir_to_l1(m, dst, ev)

    def _l1_to_dir(self, m, tile, ev):
        if m in (MSG_GETS, MSG_GETM):
            op = "GETS" if m == MSG_GETS else "GETM"
            if self.dir == "I":
                self.dir = "MEM_WAIT"
                self.pending_op, self.req = op, tile
                self.next_data = self._bank_read(ev["addr"])
                self.next_excl = 1
            elif self.dir in ("E", "M") and tile != self.owner:
                self.dir = "FWD_WAIT"
                self.pending_op, self.req = op, tile
                self.sharers = {self.owner, tile}
                self.fwd_kind = op
            elif self.dir == "S" and m == MSG_GETS:
                self.next_data = self._bank_read(ev["addr"])
                self.next_excl = 0
                self.sharers.add(tile)
            elif self.dir in ("E", "M") and tile == self.owner:
                self.next_data = self._bank_read(ev["addr"])
                self.next_excl = 1
            # DIR_S + GETM (INV_WAIT) is outside the F1-F8 directed set

        elif m == MSG_PUTS:
            if self.l1[tile] == "E":
                self.l1[tile] = "EI_A"
            elif self.l1[tile] == "S":
                self.l1[tile] = "I"
            if self.dir == "FWD_WAIT" and tile == self.owner:
                self.sharers.discard(tile)
                self.next_data = self._bank_read(ev["addr"])
                self.next_excl = 1 if self.pending_op == "GETM" else 0
            elif self.dir in ("E", "M") and tile == self.owner:
                self.owner = None
                self.sharers.discard(tile)
                self.dir = "I"
            elif self.dir == "S":
                self.sharers.discard(tile)
                if not self.sharers:
                    self.dir = "I"

        elif m == MSG_PUTM:
            self.bank[ev["addr"]] = (self.data[tile], 1)
            self.bank_written.add(ev["addr"])
            if self.l1[tile] == "M":
                self.l1[tile] = "MI_A"
            if self.dir == "FWD_WAIT":
                self.sharers.discard(tile)
                self.next_data = self.data[tile]
                self.next_excl = 1 if self.pending_op == "GETM" else 0
                if self.pending_op == "GETM":
                    self.owner = self.req
            elif self.dir in ("E", "M") and tile == self.owner:
                self.owner = None
                self.sharers.discard(tile)
                self.dir = "I"

        elif m == MSG_DATAFWD:
            self.bank[ev["addr"]] = (self.data[tile], ev["we"])
            self.bank_written.add(ev["addr"])
            self.next_data = self.data[tile]
            self.next_excl = 1 if self.pending_op == "GETM" else 0
            if self.fwd_kind == "GETS":
                self.l1[tile] = "S"
            else:
                self.l1[tile] = "I"

        elif m == MSG_UNBLOCK:
            if self.dir == "MEM_WAIT" and tile == self.req:
                self.owner = self.req
                self.sharers = {self.req}
                self.dir = "M" if self.pending_op == "GETM" else "E"
            elif self.dir == "FWD_WAIT" and tile == self.req:
                if self.pending_op == "GETM":
                    self.owner = self.req
                    self.sharers = {self.req}
                    self.dir = "M"
                else:
                    self.owner = None
                    self.dir = "S"

        elif m == MSG_INVACK:
            pass

    def _dir_to_l1(self, m, tile, ev):
        if m == MSG_DATA:
            data = self.next_data if self.next_excl else self.next_data
            if self.l1[tile] in ("IS_D", "IM_D", "SM_D"):
                if self.l1[tile] == "IS_D":
                    self.l1[tile] = "E" if ev["excl"] else "S"
                    self.data[tile] = data
                elif self.l1[tile] == "IM_D":
                    if ev["excl"]:
                        self.l1[tile] = "M"
                        self.data[tile] = self.wdata[tile]
                    else:
                        self.l1[tile] = "S"
                        self.data[tile] = data
                else:                              # SM_D
                    if ev["excl"]:
                        self.l1[tile] = "M"
                        self.data[tile] = self.wdata[tile]
                    else:
                        self.l1[tile] = "S"
                        self.data[tile] = data

        elif m == MSG_FWD_GETS:
            if self.l1[tile] in ("E", "M"):
                self.l1[tile] = "S"
        elif m == MSG_FWD_GETM:
            if self.l1[tile] in ("E", "M"):
                self.l1[tile] = "I"
        elif m == MSG_INV:
            if self.l1[tile] in ("S", "E", "M"):
                self.l1[tile] = "I"
        elif m == MSG_PUTACK:
            if self.l1[tile] in ("EI_A", "MI_A"):
                self.l1[tile] = "I"

    # ── scoreboard ──────────────────────────────────────────────────────────
    def check(self, dut, label=""):
        def eq(name, got, want):
            assert got == want, f"{label} shadow mismatch: {name}={got} expected {want}"

        for t in (0, 1):
            eq(f"l1_{t}.state", int(getattr(dut, f"l1_{t}_state").value),
               STATE_INT[self.l1[t]])
            eq(f"l1_{t}.data", int(getattr(dut, f"l1_{t}.data_q").value),
               self.data[t])

        eq("dir.state", int(dut.dir_state.value), DIR_INT[self.dir])
        eq("dir.owner", int(dut.dir_0.owner.value),
           0 if self.owner is None else self.owner)
        eq("dir.sharers", int(dut.dir_0.sharers.value),
           sum(1 << s for s in self.sharers))

        bdata, bdirty = 0, 0
        for i in range(8):
            if int(dut.bm_valid[i].value) and int(dut.bm_tag[i].value) == LINE:
                bdata = int(dut.bm_data[i].value)
                bdirty = int(dut.bm_dirty[i].value)
        want_data = self.bank.get(LINE, (0, 0))[0]
        want_dirty = 1 if LINE in self.bank_written else 0
        eq("bank.data", bdata, want_data)
        eq("bank.dirty", bdirty, want_dirty)

        return True
