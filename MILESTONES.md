# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-01 07:39] - core_claim
- Implemented LiftedTCORE with lifted regression, LCC with delayed shared monitoring, and a ground-first TCORE-style baseline.
- Reproduced the core semantic-preservation claim on generated symbolic planning tasks covering ground constraints, quantified constraints, and all five supported trajectory-constraint families.
- A completed compute job ran the reproduction script and `python validate.py --compare` successfully.

### [2026-06-01 08:30] - method_runs
- Continuation audit reset the milestone to `method_runs`.
- Fixed initial-state monitoring edge cases in LiftedTCORE and added regression tests and a scored edge-case experiment.
- Strengthened evaluation to recompute plan validity from serialized compiled-task artifacts rather than trusting method-reported booleans.
- Submitting a fresh CPU validation job before restoring `core_claim`.

### [2026-06-01 08:52] - core_claim
- CPU validation job `0ca61d79-64b` completed with exit code 0.
- The job ran planning regression tests, `scripts/reproduce.sh`, and `python validate.py --compare` inside the container.
- All five scored experiments passed semantic-preservation checks, including the initial-state monitoring edge cases.

### [2026-06-01 09:00] - core_claim
- Restored `scripts/run.sh` to execute the full reproduction path after the split-scoring audit.
- Added the paper-level `slice_structural_units` primary to `eval/evaluate_outputs.py` and regenerated `scoring/scores.json`.
- Local full-run validation passed: planning tests, method artifact generation, paper-level scoring, train/test scoring, and `python validate.py --compare`.

### [2026-06-01 09:20] - core_claim
- Increased the default size benchmark to 28 objects so the ground-first comparator reaches 21K-scale grounded actions, matching the order of magnitude in the paper's compiled-size table.
- Local smoke validation passed at a small scale.
- Submitting a CPU validation job before claiming `core_claim_plus`.

## Stop Justification
- Completed at milestone `core_claim`.
