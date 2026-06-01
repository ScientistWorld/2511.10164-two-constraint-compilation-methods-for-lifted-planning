# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-01 00:00] - none
- Started from scaffold and read the paper markdown.
- Identified the central claim: lifted constraint compilation preserves plan validity while avoiding ground-action blow-up.

### [2026-06-01 00:00] - method_runs
- Implemented symbolic planning representation, LiftedTCORE, LCC, and a ground TCORE-style baseline.
- Ran local smoke tests showing valid trajectories execute and invalid at-most-once trajectories are rejected by the compiled tasks.
- Added evaluation, reference metrics, documentation, and scripts.

### [2026-06-01 07:26] - method_runs
- Audited the existing implementation and confirmed it implements the paper's compilation algorithms directly rather than a surrogate.
- Added a semantic suite covering all five supported qualitative constraint families.
- Re-ran `scripts/reproduce.sh` and `python validate.py --compare` locally; both pass.

### [2026-06-01 07:30] - core_claim
- Compute job `7b3735e5-05b` completed with exit code 0 inside the packaged container.
- The reproduced artifacts show valid plan acceptance and invalid plan rejection at 1.0 for the at-most-once semantic check and the all-constraint semantic suite.
- Lifted compilation remains compact on the generated high-arity benchmarks while the ground-first baseline grows to hundreds or thousands of grounded actions.

## Stop Justification

Reached `core_claim`: the paper's actual lifted compilation algorithms run end-to-end in the packaged environment and demonstrate semantic preservation plus the expected lifted-vs-ground compactness effect on generated symbolic benchmarks.
