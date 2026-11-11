## Dispatch Task — Challenger 1 (Ref Model & Re-issue Ordering Adversarial Verification)

Working directory: /home/durgesh/teamwork_projects/clean_room_verification
State folder: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_challenger_1/
Original Request file: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md
Scope document: /mnt/Code/visualstudio/Design-arch_multi-core/PROJECT.md
Worker handoff report: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_worker_m1/handoff.md

### Objective
Adversarially challenge and stress-test the reference model and re-issue ordering:
1. Virtual Channel Priority Stress:
   - Challenge the pop priority `RESP(2) > INV(3) > FWD(1) > REQ(0)` in `tb_acceptance/ref_model/slice_ref_model.py`.
   - What happens when all 4 queues have messages simultaneously? Does RESP pop first, followed by INV, FWD, REQ?
   - What happens when directory is in `DIR_INV_WAIT` or `DIR_FWD_WAIT`? Is VC0 deferred?
2. Re-issue Ordering & Progress Bounding (Lemma L2):
   - Adversarially evaluate re-issuing at head vs back. Confirm that head insertion causes starvation / priority inversion, and back insertion (FIFO) guarantees progress.
   - Test accept vs decline termination paths. Does declining tile ever end up as owner? (Invariant check: `dir_owner != declining_tile`).
3. Execute empirical tests and checks to stress these properties.
4. Formulate your explicit verdict: `APPROVE` (correctness confirmed) or `REJECT`.

Write your full challenger report to:
`/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_challenger_1/handoff.md`
