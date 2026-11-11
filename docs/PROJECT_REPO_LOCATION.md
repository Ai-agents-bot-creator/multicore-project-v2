# Project repo location

| Item | Path |
|---|---|
| Repository root | `/mnt/Code/visualstudio/Design-arch_multi-core` |
| Spec package (authoritative) | `white_papers/final/` — `FINAL_whitepaper_v3.0.md`, `SPEC_SHEET.md`, `HLD_LLD_4x4_architecture.md`, `SLICE_16_1.md`, `diagrams_rendered.html`, `verify_patch_set.py` |
| Pristine baseline copy (pre-B5, sha256 `6816243d78ef9165`) | `/home/durgesh/teamwork_projects/clean_room_verification/white_papers/final/FINAL_whitepaper_v3.0.md` |
| Frozen RTL (do not modify) | `rtl_frozen/` |
| Working RTL | `rtl/directory/dir_ctrl.sv` |
| Formal evidence | `tb_rtl_evidence/` (`sby_k64/`, `sby_k128/`) |
| Docs suite (gated, 47/47) | `docs/` |
| Independent verification copy | `/home/durgesh/teamwork_projects/clean_room_verification` |

Gates:

- docs checker: `python3 ~/.skills/hw-design-docs/scripts/check_docs.py --docs docs --wp white_papers/final/FINAL_whitepaper_v3.0.md --build-order docs/BUILD_ORDER.csv` → 47/47
- docs cross-check: `python3 verify_patch_set.py --docs docs --wp white_papers/final/FINAL_whitepaper_v3.0.md` → 46/46
- package gate (from inside `white_papers/final/`): `python3 verify_patch_set.py --dir . --build-script build_diagrams_html.py` → 134/134 (B7 landed 2026-11-07; pre-B7 ran 132, pre-B6 ran 131, pre-B5 ran 130)
