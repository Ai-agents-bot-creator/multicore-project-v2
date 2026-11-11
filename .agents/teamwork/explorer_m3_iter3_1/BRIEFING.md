# BRIEFING — 2026-11-06T01:32:00Z

## Mission
Investigate solver execution and performance scaling for BMC depth 64 on cache_sva.sby, evaluate solver options (Boolector, smtbmc flags, unroll, presat, timeout, monitoring), and recommend an exact execution plan for the worker to achieve authentic completion at K=64.

## 🔒 My Identity
- Archetype: explorer
- Roles: SMT and formal verification scaling explorer
- Working directory: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m3_iter3_1
- Original parent: be241bc4-e291-4439-8a29-a04573a62cec
- Milestone: Milestone 3 Gate Iteration 3

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Do NOT modify source code or formal testbench files
- Provide concrete, evidence-backed recommendations and execution commands

## Current Parent
- Conversation ID: be241bc4-e291-4439-8a29-a04573a62cec
- Updated: 2026-11-06T01:32:00Z

## Investigation State
- **Explored paths**: `cache_sva.sby`, `sva_formal_top.sv`, `cache_coherence_sva.sv`, `sby_engine_smtbmc.py`, `sby_core.py`, reviewer and auditor handoffs, empirical benchmark tests on `design_smt2.smt2` with Boolector, Bitwuzla, Z3.
- **Key findings**:
  - `smtbmc boolector` automatically supplies `--presat --unroll --noprogress`.
  - Empirical benchmarking at depth 12 proved `--presat` speeds up Boolector (29.4s vs >65s without presat) by pre-warming SAT clause databases, while preventing vacuous assumption passes.
  - Step solving times scale from 12s at step 10 to ~53s at step 14, yielding an expected wall-clock runtime of 45–60 minutes for depth 64.
  - Monolithic execution of `sby -f cache_sva.sby bmc` is necessary; chunking steps does not reduce runtime and invalidates standard acceptance artifacts.
  - Worker must launch BMC as a background task (`run_command` with `WaitMsBeforeAsync: 1000`) and maintain 5-minute heartbeat polling using native `schedule(DurationSeconds=300)`.
- **Unexplored areas**: None. All solver execution, scaling, monitoring, and command-line requirements are resolved.

## Key Decisions Made
- Confirmed Boolector configuration in `cache_sva.sby` should remain `smtbmc boolector`.
- Formulated turnkey 6-step execution and monitoring plan for Worker in `handoff.md`.

## Artifact Index
- DISPATCH.md — record of incoming dispatch
- progress.md — liveness heartbeat and milestone tracker
- BRIEFING.md — persistent working memory
- handoff.md — final 5-component report

