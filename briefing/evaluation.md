# Evaluation

## Metrics

The benchmark measures compiled action count, compiled effect count, formula-size proxy (`formula_atoms`), action ratio versus the ground baseline, compile time, and semantic validity. Lower counts, lower ratios, and lower compile time are better. `plan_valid_rate`, `valid_plan_accepted`, `invalid_plan_rejected`, `valid_accept_rate`, and `invalid_reject_rate` should be 1.0.

The main constraint metric is semantic preservation: a compact compiler is not useful if it accepts an invalid trajectory or rejects a valid one. The generated benchmark is intentionally smaller than the paper's full IPC suite, so compactness should be interpreted through the reproduced counts and ratios rather than exact IPC-scale action counts.

## Baselines and Targets

The reference baseline is a ground TCORE-style compilation that first grounds action schemas and then applies constraint compilation. The target behavior is to preserve semantics while producing substantially smaller constraint-free specifications.

Paper targets in `scoring/reference.json` summarize Table 3 for compiled size and compilation time and include semantic-preservation targets from the paper's correctness claim.

## Evaluation Protocol

Run `bash scripts/reproduce.sh` to generate method artifacts in `outputs/method_results.json`, then run `bash scripts/evaluate.sh outputs/method_results.json`. The evaluator only reads the output artifact and writes `scoring/scores.json`.

The included benchmark uses generated symbolic planning tasks with high-arity actions, ground and quantified constraints, and explicit valid/invalid plan probes. It also includes a constraint-family suite for always, sometime, sometime-before, sometime-after, and at-most-once requirements, plus initial-state monitoring edge cases. Future methods should emit the same JSON artifact format: serialized compiled tasks, valid plans, optional invalid plans, and compile-time measurements.
