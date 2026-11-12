# Verification Report

Superseded by the hardening iteration; see `HARDENING.md`.

* Reproduction: LiftedTCORE (Algorithm 1, lifted gamma/regression with unification against forall effects, omission of R(phi,a)=phi updates) and LCC (Algorithm 2, shared monitoring + `fin`) in `method/planning.py`.
* Correctness: both compilers pass the evaluator's semantic gate on every train and held-out task (hidden probes on 40 large tasks, complete product exploration on 40 small tasks per slice).
* Paper direction: both lifted compilers are 6-7 orders of magnitude smaller than full grounding; LiftedTCORE adds fewer effects than LCC, LCC has smaller largest formulas (paper: 58 vs 63 effects; 26 vs 18 largest-formula atoms).
* Jobs: `7214d826-e8c` (hardening audit + reference runs, exit 0).
