# Progress

## What Works

Implemented a self-contained symbolic planning reproduction of the paper's two lifted compilers:

- LiftedTCORE with lifted unification, lifted gamma, regression, and action-specific monitoring updates.
- LCC with shared monitoring preconditions/effects and a final `fin` action.
- Ground TCORE-style baseline that grounds high-arity action schemas before applying regression compilation.
- Output-based evaluation that reads `outputs/method_results.json` and writes `scoring/scores.json`.
- A constraint-family semantic suite covering always, sometime, sometime-before, sometime-after, and at-most-once checks.

## Results

Local smoke run and compute job `7b3735e5-05b` both preserve constraint semantics:

- Valid plans are accepted by LiftedTCORE, LCC, and the ground baseline.
- Invalid at-most-once trajectories are rejected.
- Valid and invalid trajectories are classified correctly for all five supported qualitative constraint families.
- Lifted compiled tasks remain at 1-3 lifted actions in the generated high-arity size benchmarks, while the ground baseline grows to 343 actions on the quantified small task and 4096 actions on the larger ground task.
- In the all-constraint semantic suite, LiftedTCORE, LCC, and the ground baseline all achieve `valid_accept_rate = 1.0` and `invalid_reject_rate = 1.0` across five constraint families.

`python validate.py --compare` passes.

## Remaining

The current environment reaches `core_claim` on generated symbolic benchmark tasks rather than the full IPC benchmark and LAMA planner stack. Higher milestones would require downloading/building the IPC domains and planner toolchain and reproducing Table 1 coverage.

## Issues

The paper's full benchmark depends on external planner infrastructure and IPC generators. To keep the first runnable environment robust, I used generated planning tasks that preserve the same high-arity grounding pressure and trajectory-constraint semantics.

## Deviations from Paper

The paper evaluates on 280 IPC-derived PDDL problems solved by LAMA with 1800s/8GB limits. This reproduction uses generated symbolic planning tasks and direct plan-validity checks because the full IPC/planner stack is large for a first core-claim reproduction. The algorithmic compilation procedures themselves are implemented directly: lifted regression for LiftedTCORE, delayed shared monitoring for LCC, and a ground-first TCORE-style baseline.
