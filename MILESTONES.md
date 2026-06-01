# Reproduction Milestones

**Current: method_runs**

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

## Stop Justification
- Not stopped. Fresh validation is pending after continuation fixes.
