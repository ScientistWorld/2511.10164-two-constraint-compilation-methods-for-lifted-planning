# Progress

## What Works

Implemented a self-contained symbolic planning reproduction of the paper's two lifted compilers:

- LiftedTCORE with lifted unification, lifted gamma, regression, and action-specific monitoring updates.
- LCC with shared monitoring preconditions/effects and a final `fin` action.
- Ground TCORE-style baseline that grounds high-arity action schemas before applying regression compilation.
- Output-based evaluation that reads `outputs/method_results.json` and writes `scoring/scores.json`.
- Evaluator-side plan replay over serialized compiled tasks, so scores are recomputed from artifacts rather than trusted method-reported flags.
- A constraint-family semantic suite covering always, sometime, sometime-before, sometime-after, and at-most-once checks.
- Initial-state monitoring edge cases for sometime-before and at-most-once constraints.
- Audit fix: lifted unification now handles repeated variables by producing equality conditions instead of incorrectly failing unification.
- Continuation audit fix: LiftedTCORE now initializes monitoring state when sometime-before witnesses or at-most-once protected formulas already hold initially.

## Results

Local smoke runs and compute jobs `7b3735e5-05b` and `f285ea84-69a` preserve constraint semantics:

- Valid plans are accepted by LiftedTCORE, LCC, and the ground baseline.
- Invalid at-most-once trajectories are rejected.
- Valid and invalid trajectories are classified correctly for all five supported qualitative constraint families.
- Lifted compiled tasks remain at 1-3 lifted actions in the generated high-arity size benchmarks, while the ground baseline grows to 343 actions on the quantified small task and 4096 actions on the larger ground task.
- In the all-constraint semantic suite, LiftedTCORE, LCC, and the ground baseline all achieve `valid_accept_rate = 1.0` and `invalid_reject_rate = 1.0` across five constraint families.

Local continuation checks pass after the initial-state monitoring and evaluator-artifact replay fixes:

- `PYTHONPATH=method python method/test_planning.py`
- `bash scripts/reproduce.sh`
- `python validate.py --compare`

A fresh CPU validation job verified the same path inside the compute container.

After the train/test split audit, `scripts/run.sh` was restored to the full core-claim path: planning regression tests, `scripts/reproduce.sh`, train/test split scoring, and `python validate.py --compare`. The paper-level evaluator now emits the same `slice_structural_units` compactness primary used by `reference.json`, so `scores.json`, `scores_train.json`, and `scores_test.json` all validate against the current scoring schema.

Continuation scaling update: the size experiments now default to 28 objects, so the ground-first baseline expands to `28^3 = 21952` grounded actions, matching the order of magnitude reported in the paper's Table 3. Semantic accept/reject checks keep their smaller object count because they test constraint preservation rather than grounding blow-up.

Current milestone: `core_claim`.

Compute job `f285ea84-69a` completed with exit code 0 after the audit fix. It ran the lifted repeated-variable unification tests, reproduced all method outputs, and passed `python validate.py --compare` inside the container.

Compute job `0ca61d79-64b` completed with exit code 0 after the continuation fixes. It ran the full `scripts/run.sh` path in the container: planning regression tests, artifact generation through `scripts/reproduce.sh`, and `python validate.py --compare`. The validator reported all structure checks passed and all scored semantic-preservation rates were 1.0.

## Audit Notes

The existing implementation was a real reproduction of the paper's algorithm, not a surrogate: LiftedTCORE computes lifted gamma/regression and LCC applies shared delayed monitoring with a final `fin` action. The evaluator is independent from `method/` and reads `outputs/method_results.json`.

During the first audit, repeated variables in lifted unification were found to be under-handled. This has been fixed in `method/planning.py` and covered by `method/test_planning.py`; `scripts/run.sh` now executes those checks before the full reproduction.

During the continuation audit, two lifted monitoring edge cases were found and fixed:

- `sometime-before(phi, psi)` must count `psi` as already seen when `psi` is true in the initial state.
- `at-most-once(phi)` must count `phi` as already seen when `phi` is true in the initial state, so later re-entry is rejected.

The evaluator was also strengthened to replay serialized compiled artifacts independently instead of trusting method-emitted validity booleans.

## Remaining

The current environment reaches `core_claim` on generated symbolic benchmark tasks rather than the full IPC benchmark and LAMA planner stack. The submitted scaling job tests a stronger size setting; if it passes, the next milestone can be raised to `core_claim_plus`. Higher milestones would require downloading/building the IPC domains and planner toolchain and reproducing Table 1 coverage.

## Issues

The paper's full benchmark depends on external planner infrastructure and IPC generators. To keep the first runnable environment robust, I used generated planning tasks that preserve the same high-arity grounding pressure and trajectory-constraint semantics.

Validation note: the generated benchmark is smaller than the paper's full IPC evaluation, so the size experiments use semantic validity as their primary metric in `reference.json`; action/effect counts and action ratios remain reported as compactness metrics.

Workspace note: the root `README.md` appears as a busy character device in this environment and could not be replaced with normal markdown. Reproduction instructions are provided in `README_REPRODUCTION.md` instead.

## Deviations from Paper

The paper evaluates on 280 IPC-derived PDDL problems solved by LAMA with 1800s/8GB limits. This reproduction uses generated symbolic planning tasks and direct plan-validity checks because the full IPC/planner stack is large for a first core-claim reproduction. The algorithmic compilation procedures themselves are implemented directly: lifted regression for LiftedTCORE, delayed shared monitoring for LCC, and a ground-first TCORE-style baseline.
