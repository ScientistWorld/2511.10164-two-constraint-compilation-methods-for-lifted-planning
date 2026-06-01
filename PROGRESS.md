# Progress

## What Works

Implemented a self-contained symbolic planning reproduction of the paper's two lifted compilers:

- LiftedTCORE with lifted unification, lifted gamma, regression, and action-specific monitoring updates.
- LCC with shared monitoring preconditions/effects and a final `fin` action.
- Ground TCORE-style baseline that grounds high-arity action schemas before applying regression compilation.
- Output-based evaluation that reads `outputs/method_results.json` and writes `scoring/scores.json`.

## Results

Local smoke run and full default run both preserve constraint semantics:

- Valid plans are accepted by LiftedTCORE, LCC, and the ground baseline.
- Invalid at-most-once trajectories are rejected.
- Lifted compiled tasks remain at 1-4 lifted actions in the included generated benchmarks, while the ground baseline grows to hundreds or thousands of actions depending on object count.

`python validate.py --compare` passes.

## Remaining

The current environment reproduces the core claim on generated symbolic benchmark tasks rather than the full IPC benchmark and LAMA planner stack. Higher milestones would require downloading/building the IPC domains and planner toolchain and reproducing Table 1 coverage.

## Issues

The paper's full benchmark depends on external planner infrastructure and IPC generators. To keep the first runnable environment robust, I used generated planning tasks that preserve the same high-arity grounding pressure and trajectory-constraint semantics.

## Deviations from Paper

The paper evaluates on 280 IPC-derived PDDL problems solved by LAMA with 1800s/8GB limits. This reproduction uses generated symbolic planning tasks and direct plan-validity checks because the full IPC/planner stack is large for a first core-claim reproduction. The algorithmic compilation procedures themselves are implemented directly: lifted regression for LiftedTCORE, delayed shared monitoring for LCC, and a ground-first TCORE-style baseline.
