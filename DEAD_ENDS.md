# Dead Ends Log

| Iteration | Approach Tried | Why It Failed | Files Touched |
|-----------|---------------|---------------|---------------|
| M3-Iter1 | Internal unpacked arrays for stimulus & un-framed A3.1 HDR_HEAD check | Slang/Yosys synthesizes internal unpacked arrays as unwritten memory locked to 0 (vacuous BMC); bit 41 in multi-flit data payload causes false A3.1 violations at step 12 | `tb_acceptance/sva/sva_formal_top.sv`, `tb_acceptance/sva/cache_coherence_sva.sv` |
