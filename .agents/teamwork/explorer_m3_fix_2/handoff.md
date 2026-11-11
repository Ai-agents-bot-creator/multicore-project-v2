# Handoff Report: Assertion A3.1 Packet Framing Remediation Strategy

- **Agent:** Explorer M3 Fix 2 (Assertion A3.1 Framing Fix Explorer)
- **Target Work Product:** `~/teamwork_projects/clean_room_verification/tb_acceptance/sva`
- **Reviewed Files:**
  - `tb_acceptance/sva/cache_coherence_sva.sv`
  - `tb_acceptance/sva/sva_formal_top.sv`
  - `rtl_frozen/pkg/tile_pkg.sv`
  - `rtl_frozen/l1/l1_mesi_ctrl.sv`
  - `rtl_frozen/directory/dir_ctrl.sv`
- **Status:** Complete / Hard Handoff

---

## 1. Observation

### 1.1 Verbatim Audit Failure in Assertion A3.1
In the forensic audit reports (`auditor_m3_1/handoff.md:117-127`, `reviewer_m3_1/handoff.md:83-97`, `challenger_m3_2/handoff.md:103-118`), when formal stimulus was unblocked by exposing top-level input ports on `sva_formal_top.sv`, SymbiYosys BMC failed immediately at step 12:
```
SBY 0:48:37 [test_fix] engine_0: ## 0:01:46 BMC failed!
SBY 0:48:37 [test_fix] engine_0: ## 0:01:46 Assert failed in sva_formal_top: cache_coherence_sva.sv:121.9-123.69 (_witness_.check_3961)
SBY 0:48:41 [test_fix] summary: failed assertion sva_formal_top._witness_.check_3961 at cache_coherence_sva.sv:121.9-123.69 step 12
SBY 0:48:41 [test_fix] DONE (FAIL, rc=2)
```

### 1.2 Assertion A3.1 Implementation in `cache_coherence_sva.sv`
Inspecting `tb_acceptance/sva/cache_coherence_sva.sv` lines 110–125:
```systemverilog
// =======================================================================
// Category A3: Virtual Channel Invariance
// =======================================================================

// A3.1: Virtual Channel Preservation and Invariance
// Flit header VC field [43:42] strictly matches the normative VC of the message class.
for (int k = 0; k < TILE_COUNT; k++) begin
  if (l1_noc_req_valid[k] && l1_noc_req_flit[k][HDR_HEAD]) begin
    assert (l1_noc_req_flit[k][HDR_VC_HI:HDR_VC_LO] ==
            msg_to_vc(msg_type_t'(l1_noc_req_flit[k][HDR_MSG_HI:HDR_MSG_LO])))
      else $error("[SVA FAIL A3.1] L1 flit VC mismatch");
  end
end

if (dir_noc_rsp_valid && dir_noc_rsp_flit[HDR_HEAD]) begin
  assert (dir_noc_rsp_flit[HDR_VC_HI:HDR_VC_LO] ==
          msg_to_vc(msg_type_t'(dir_noc_rsp_flit[HDR_MSG_HI:HDR_MSG_LO])))
    else $error("[SVA FAIL A3.1] Directory flit VC mismatch");
end
```
Both assertions guard solely on `flit[HDR_HEAD]` without checking whether the flit is a genuine packet header or a subsequent body flit of a multi-flit packet.

### 1.3 Flit Protocol & Bit Definitions in `rtl_frozen/pkg/tile_pkg.sv`
Inspecting `rtl_frozen/pkg/tile_pkg.sv` lines 117–134 and 190–207:
```systemverilog
localparam int FLIT_W      = 64;
localparam int BODY_FLITS  = 8;   // per cache-line packet
localparam int LINE_PKT_LEN = 9;  // 1 header + 8 body

// Header field positions
localparam int HDR_DEST_HI = 63, HDR_DEST_LO = 56;
localparam int HDR_SRC_HI  = 55, HDR_SRC_LO  = 48;
localparam int HDR_MSG_HI  = 47, HDR_MSG_LO  = 44;
localparam int HDR_VC_HI   = 43, HDR_VC_LO   = 42;
localparam int HDR_HEAD     = 41;
localparam int HDR_TAIL     = 40;
localparam int HDR_WE       = 39;   // write-enable / DATAFWD dirty bit
localparam int HDR_EXCL     = 38;
localparam int HDR_LEN_HI  = 37, HDR_LEN_LO  = 32;
localparam int HDR_ADDR_HI = 31, HDR_ADDR_LO =  0;

function automatic vc_id_t msg_to_vc(msg_type_t m);
  case (m)
    MSG_GETS, MSG_GETM, MSG_PUTS, MSG_PUTM, MSG_DMA_WRITE: return VC_REQ;
    MSG_FWD_GETS, MSG_FWD_GETM:                             return VC_FWD;
    MSG_UNBLOCK, MSG_INVACK, MSG_DATA, MSG_DATAFWD,
    MSG_PUTACK, MSG_DMA_ACK:                                 return VC_RESP;
    MSG_INV:                                                 return VC_INV;
    default:                                                 return VC_REQ;
  endcase
endfunction

function automatic logic [5:0] msg_to_len(msg_type_t m);
  case (m)
    MSG_PUTM, MSG_DATA, MSG_DATAFWD, MSG_DMA_WRITE: return 6'd9;
    default:                                          return 6'd1;
  endcase
endfunction
```

### 1.4 RTL Transmit Serialization and Body Flit Composition
1. In `rtl_frozen/directory/dir_ctrl.sv` lines 120–124:
   ```systemverilog
   mk_hdr[HDR_HEAD]                = 1'b1;
   mk_hdr[HDR_TAIL]                = (msg_to_len(m) == 6'd1);
   mk_hdr[HDR_WE]                  = we;
   mk_hdr[HDR_EXCL]                = excl;
   mk_hdr[HDR_LEN_HI:HDR_LEN_LO]   = msg_to_len(m);
   mk_hdr[HDR_ADDR_HI:HDR_ADDR_LO] = a;
   ```
2. In `rtl_frozen/directory/dir_ctrl.sv` lines 624–641:
   ```systemverilog
   if (tx_busy) begin
     if (tx_flt == 4'd0) begin
       noc_rsp_flit = mk_hdr(msg_type_t'(tx_cur_msg), tx_cur_dst, tx_cur_addr,
                             tx_cur_we, tx_cur_excl);
     end else begin
       case (tx_flt)
         4'd1: noc_rsp_flit = tx_cur_data[ 63:  0];
         4'd2: noc_rsp_flit = tx_cur_data[127: 64];
         4'd3: noc_rsp_flit = tx_cur_data[191:128];
         4'd4: noc_rsp_flit = tx_cur_data[255:192];
         4'd5: noc_rsp_flit = tx_cur_data[319:256];
         4'd6: noc_rsp_flit = tx_cur_data[383:320];
         4'd7: noc_rsp_flit = tx_cur_data[447:384];
         4'd8: noc_rsp_flit = tx_cur_data[511:448];
         default: ;
       endcase
     end
   end
   ```
3. In `rtl_frozen/l1/l1_mesi_ctrl.sv` lines 134–138 and 526–543:
   Identical structure exists on `l1_noc_req_flit`: Flit 0 is generated by `mk_hdr`, while flits 1 through 8 are raw slices of `tx_cur_data`.
4. In `sva_formal_top.sv` line 295, the L2 bank storage is initialized to:
   ```systemverilog
   bank_storage <= {8{64'hA0A1A2A3A4A5A6A0}};
   ```
   In `64'hA0A1A2A3A4A5A6A0`:
   - Byte 5 (bits [47:40]) is `8'hA2` = `8'b1010_0010`.
   - Bit 41 is `1'b1` (`HDR_HEAD`).
   - Bit 40 is `1'b0` (`HDR_TAIL`).
   - Bits [47:44] are `4'b1010` (`MSG_DATAFWD`).
   - Bits [43:42] are `2'b00` (`VC_REQ`).

---

## 2. Logic Chain

1. **Premise 1 (Two Packet Length Classes):**
   Per `tile_pkg.sv:201-206`, messages belong to either:
   - Single-flit control packets ($\text{len}=1$): `GETS`, `GETM`, `PUTS`, `UNBLOCK`, `INV`, `INVACK`, `PUTACK`, `DMA_ACK`, `FWD_GETS`, `FWD_GETM`.
   - Multi-flit data packets ($\text{len}=9$): `PUTM`, `DATA`, `DATAFWD`, `DMA_WRITE`.

2. **Premise 2 (Body Flit Semantic Isolation):**
   In a 9-flit packet, flit 0 is the sole flit formatted with header fields (`Dest, Src, Msg, VC, Head, Tail, Len, Addr`). Flits 1 through 8 carry 64-bit unformatted data payload slices (`tx_cur_data`). The hardware does **not** inject framing bits into body flits:
   - Payload bit 41 (`HDR_HEAD` position) is arbitrary memory data.
   - Payload bit 40 (`HDR_TAIL` position) is arbitrary memory data.
   - Body flit 8 does **not** have `HDR_TAIL` forced to 1.

3. **Inference 1 (Mechanism of False Assertion Failure at Step 12):**
   When the directory serves a cache read miss, it transmits a 9-flit `MSG_DATA` packet. At step 12 (flit 1), `dir_noc_rsp_valid` is 1 and `dir_noc_rsp_flit` carries `64'hA0A1A2A3A4A5A6A0`.
   Because payload bit 41 is 1, `cache_coherence_sva.sv:120` evaluates `dir_noc_rsp_flit[HDR_HEAD]` as true. It extracts:
   - Extracted VC `[43:42]` = `2'b00` (`VC_REQ`).
   - Extracted Msg `[47:44]` = `4'b1010` (`MSG_DATAFWD`).
   - Expected VC `msg_to_vc(MSG_DATAFWD)` = `VC_RESP` (`2'b10`).
   Because `2'b00 != 2'b10`, assertion A3.1 fails falsely on data payload bytes.

4. **Inference 2 (Identical Vulnerability on L1 Egress Ports):**
   On the L1 request egress ports (`l1_noc_req_flit[k]`), multi-flit packets occur during dirty writeback (`MSG_PUTM`) and forward response (`MSG_DATAFWD`). Any cache line payload with bit 41 = 1 will falsely trigger line 113 on flits 1 through 8.

5. **Inference 3 (Sequence Tracker Requirements & Design):**
   To strictly isolate header evaluations from data bytes:
   - Each egress port must maintain a dedicated sequence tracker (`rem` down-counter) initialized to 0 on reset.
   - Flit 0 is identified by `rem == 4'd0`. Assertion A3.1 must evaluate **strictly and exclusively** when `valid && (rem == 4'd0) && flit[HDR_HEAD]`.
   - On flit 0, if the packet is multi-flit (`!flit[HDR_TAIL] && flit[HDR_LEN] > 1`), `rem` is loaded with `flit[HDR_LEN] - 1` (e.g. $9 - 1 = 8$).
   - On each subsequent valid body flit, `rem` decrements by 1 down to 0. During body flits, A3.1 is disabled.
   - When `rem == 1`, consuming that body flit returns `rem` to 0 (end-of-packet reached). The interface is immediately ready to accept the next header flit.
   - **Critical Safety Constraint:** The tracker must **not** check `flit[HDR_TAIL]` during body flits (`rem > 0`), because payload bit 40 can be 1, which would prematurely abort the body countdown.

6. **Inference 4 (Synthesis Immunity in Yosys/Slang):**
   As recorded in `DEAD_ENDS.md`, undriven internal unpacked arrays synthesize as unwritten `$mem_v2` cells. To prevent memory inference, tracker registers must be declared as standard packed bitvectors:
   - `logic [3:0] dir_rsp_rem;`
   - `logic [TILE_COUNT-1:0][3:0] l1_req_rem;`
   Empirical RTLIL inspection proves these synthesize into direct D-flip-flops (`$dff`), producing 0 memory cells, 0 latches, and 0 warnings.

---

## 3. Caveats

1. **RTL Black-Box Constraint:** Frozen RTL in `rtl_frozen/` was treated strictly as a read-only black box. No modifications were made to `tile_pkg.sv`, `l1_mesi_ctrl.sv`, or `dir_ctrl.sv`.
2. **Read-Only Acceptance Suite:** As an Explorer, no files under `~/teamwork_projects/clean_room_verification/tb_acceptance/` were modified. Empirical validations were executed in clean-room isolated temporary directories (`/tmp/test_framing/`) and purged immediately upon verification.
3. **Network Egress Port Scope:** In the current formal verification harness (`sva_formal_top.sv`), `cache_coherence_sva.sv` observes `l1_noc_req_flit[k]` (L1 egress) and `dir_noc_rsp_flit` (Directory egress). Across these two egress interfaces, all four message categories (`L1 requests`, `L1 responses`, `Directory requests`, `Directory responses`) and all four virtual channels (`VC0`, `VC1`, `VC2`, `VC3`) are fully present and verified. If the Worker also chooses to monitor interconnect outputs (`dir_noc_req` and `l1_noc_rsp`), the exact same sequence tracker pattern applies identically.

---

## 4. Conclusion

### Summary Assessment
The failure of assertion A3.1 at BMC step 12 is a classic framing false-positive caused by inspecting `HDR_HEAD` on un-framed body data flits carrying arbitrary 64-bit cache-line payloads. The remedy is a lightweight, Slang-synthesizable flit countdown register per egress channel that gates A3.1 to Flit 0 only.

### Concrete Remediation Specification for Worker M3

Target File: `~/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_coherence_sva.sv`

#### Step 1: Sequence Tracker Declaration & State Update
Add the sequence tracking registers and sequential state update block immediately above the SVA assertion block (around line 40):

```systemverilog
  // ===========================================================================
  // Egress Flit Sequence Trackers
  // Tracks remaining body flits to distinguish Header flits (flit 0) from body flits.
  // Packed 2D vectors ensure synthesis into direct D-flip-flops ($dff) in Yosys.
  // ===========================================================================
  logic [3:0]                 dir_rsp_rem;
  logic [TILE_COUNT-1:0][3:0] l1_req_rem;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      dir_rsp_rem <= 4'd0;
      l1_req_rem  <= '0;
    end else begin
      // Directory response egress port tracking
      if (dir_noc_rsp_valid) begin
        if (dir_rsp_rem == 4'd0) begin
          // Flit 0: load remaining count if multi-flit packet
          if (dir_noc_rsp_flit[HDR_HEAD] && !dir_noc_rsp_flit[HDR_TAIL] &&
              (dir_noc_rsp_flit[HDR_LEN_HI:HDR_LEN_LO] > 6'd1)) begin
            dir_rsp_rem <= 4'(dir_noc_rsp_flit[HDR_LEN_HI:HDR_LEN_LO] - 6'd1);
          end
        end else begin
          // Body flit: decrement until end-of-packet reached
          dir_rsp_rem <= dir_rsp_rem - 4'd1;
        end
      end

      // L1 request egress ports tracking per tile
      for (int k = 0; k < TILE_COUNT; k++) begin
        if (l1_noc_req_valid[k]) begin
          if (l1_req_rem[k] == 4'd0) begin
            // Flit 0: load remaining count if multi-flit packet
            if (l1_noc_req_flit[k][HDR_HEAD] && !l1_noc_req_flit[k][HDR_TAIL] &&
                (l1_noc_req_flit[k][HDR_LEN_HI:HDR_LEN_LO] > 6'd1)) begin
              l1_req_rem[k] <= 4'(l1_noc_req_flit[k][HDR_LEN_HI:HDR_LEN_LO] - 6'd1);
            end
          end else begin
            // Body flit: decrement until end-of-packet reached
            l1_req_rem[k] <= l1_req_rem[k] - 4'd1;
          end
        end
      end
    end
  end
```

#### Step 2: Gating Assertion A3.1 to True Header Flits Only
Replace lines 110–125 of `cache_coherence_sva.sv` with:

```systemverilog
      // =======================================================================
      // Category A3: Virtual Channel Invariance
      // =======================================================================

      // A3.1: Virtual Channel Preservation and Invariance
      // Evaluated strictly on TRUE HEADER FLITS (flit 0) of outgoing packets.
      for (int k = 0; k < TILE_COUNT; k++) begin
        if (l1_noc_req_valid[k] && (l1_req_rem[k] == 4'd0) && l1_noc_req_flit[k][HDR_HEAD]) begin
          assert (l1_noc_req_flit[k][HDR_VC_HI:HDR_VC_LO] ==
                  msg_to_vc(msg_type_t'(l1_noc_req_flit[k][HDR_MSG_HI:HDR_MSG_LO])))
            else $error("[SVA FAIL A3.1] L1 flit VC mismatch");
        end
      end

      if (dir_noc_rsp_valid && (dir_rsp_rem == 4'd0) && dir_noc_rsp_flit[HDR_HEAD]) begin
        assert (dir_noc_rsp_flit[HDR_VC_HI:HDR_VC_LO] ==
                msg_to_vc(msg_type_t'(dir_noc_rsp_flit[HDR_MSG_HI:HDR_MSG_LO])))
          else $error("[SVA FAIL A3.1] Directory flit VC mismatch");
      end
```

#### Step 3: Optional Egress/Ingress Network Checks (Reference Extension)
If the Worker or team also desires to assert VC preservation across the request FIFO and response demux in `cache_coherence_sva.sv`, the exact same pattern applies:
- Ports: `input logic dir_noc_req_valid, input logic [FLIT_W-1:0] dir_noc_req_flit, input logic [TILE_COUNT-1:0] l1_noc_rsp_valid, input logic [FLIT_W-1:0] l1_noc_rsp_flit [TILE_COUNT]`.
- Trackers: `logic [3:0] dir_req_rem;` and `logic [TILE_COUNT-1:0][3:0] l1_rsp_rem;`.
- Guards: `(dir_req_rem == 4'd0) && dir_noc_req_flit[HDR_HEAD]` and `(l1_rsp_rem[k] == 4'd0) && l1_noc_rsp_flit[k][HDR_HEAD]`.

---

## 5. Verification Method

To independently verify this strategy:

### 5.1 Slang Synthesis & DFF Inspection Test
Run Yosys with the Slang plugin to verify that the proposed logic elaborates cleanly without memory inference:
```bash
export PATH="/home/durgesh/.local/oss-cad-suite/bin:$PATH"
yosys -p "read_slang /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/pkg/tile_pkg.sv \
          /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_coherence_sva.sv; \
          prep -top cache_coherence_sva; stat"
```
**Expected Outcome:**
- 0 errors, 0 warnings from Slang frontend.
- `l1_req_rem` and `dir_rsp_rem` are mapped directly to `$dff` cells. Zero unwritten memory arrays (`$mem_v2` with `rom: true`) created.

### 5.2 SBY BMC Bound K=64 Execution
Once Worker M3 applies both the top-level stimulus port fix (from Explorer M3 Fix 1) and this framing fix (from Explorer M3 Fix 2):
```bash
export PATH="/home/durgesh/.local/oss-cad-suite/bin:$PATH"
cd ~/teamwork_projects/clean_room_verification/tb_acceptance/sva
sby -f cache_sva.sby
```
**Expected Outcome:**
- BMC reaches depth $K=64$ with return code 0 (`DONE (PASS, rc=0)`).
- Step 12 passes cleanly without false VC mismatches on DATA body flits.

### 5.3 Invalidation Conditions
- Any sequence tracker that inspects `flit[HDR_TAIL]` while `rem > 0` (invalidated by payload data with bit 40 = 1).
- Any sequence tracker declared as an internal unpacked array without primary drivers (invalidated by Yosys `$mem_v2` ROM inference).
- Any assertion check evaluating VC on flits where `rem != 0`.
