# Overview

- **Paper ID:** 2511.10164
- **Title:** Two Constraint Compilation Methods for Lifted Planning
- **Domain:** Automated Planning
- **TL;DR:** The paper compiles qualitative PDDL trajectory constraints away in lifted form, avoiding the grounding blow-up of prior TCORE-style compilation.

## Short Summary

The paper studies planning tasks with safety, ordering, and intermediate-goal trajectory constraints. It proposes LiftedTCORE, which uses lifted regression, and LCC, which uses shared monitoring logic with a final checking action. The reported experiments show that the lifted compilers preserve constraint semantics and produce compiled tasks with orders-of-magnitude fewer actions and effects than ground-first compilation.

## Key Results

- On the paper's main benchmark, LCC solved 246/280 tasks and LiftedTCORE solved 238/280, comparable to ground TCORE at 245/280.
- Average compiled actions/effects were about 7-8 actions and 58-67 effects for lifted methods, versus about 21K actions and 95K-96K effects for ground TCORE.
- Average compilation time was milliseconds for the lifted compilers, versus several seconds for ground TCORE.

---

# Problem Definition

## Research Question

How can qualitative PDDL state-trajectory constraints be removed from a planning task while preserving exactly the same valid plans and avoiding explosive growth in the planning specification?

The constraints considered here are `always`, `sometime`, `at_most_once`, `sometime_before`, and `sometime_after`, including formulas with quantifiers. A solution must transform constrained planning tasks into constraint-free tasks that ordinary planners can consume.

## Why It Matters

Many planners do not natively support trajectory constraints. A good transformation lets those planners handle safety requirements, intermediate goals, and ordering requirements without first generating an enormous grounded action set.

## Success Criteria

A successful system preserves constraint semantics, accepts plans that satisfy the original constrained task, rejects plans that violate the original constraints, and keeps the compiled specification compact as object counts and action arities grow.

---

# Paper's Method

## Key Contribution

The paper introduces two lifted compilers for qualitative PDDL state-trajectory constraints: LiftedTCORE and LCC. Both remove constraints without grounding the planning task first.

## Approach

LiftedTCORE generalizes TCORE's regression operator to lifted formulas and lifted actions. For each constraint formula and action schema, it computes a lifted regression condition using unification against conditional effects, then adds action-specific monitoring preconditions and effects.

LCC avoids regression. It adds a shared set of constraint-monitoring preconditions and conditional effects to all actions, introduces monitoring atoms such as `hold`, `seen`, and `prevent`, and adds a final `fin` action so the last state is checked despite LCC's one-step monitoring delay.

## Main Claims

The primary claim is that constraints can be compiled away without grounding while preserving plan validity. The empirical claim is that the lifted compilers produce much more succinct compiled specifications and compile faster than ground-first TCORE, while remaining competitive when solved by a standard planner.

---

# Evaluation

## Metrics

The benchmark measures compiled action count, compiled effect count, formula-size proxy (`formula_atoms`), action ratio versus the ground baseline, compile time, and semantic validity. Lower counts, lower ratios, and lower compile time are better. `plan_valid_rate`, `valid_plan_accepted`, `invalid_plan_rejected`, `valid_accept_rate`, and `invalid_reject_rate` should be 1.0.

The main constraint metric is semantic preservation: a compact compiler is not useful if it accepts an invalid trajectory or rejects a valid one. The generated benchmark is intentionally smaller than the paper's full IPC suite, so compactness should be interpreted through the reproduced counts and ratios rather than exact IPC-scale action counts.

## Baselines and Targets

The reference baseline is a ground TCORE-style compilation that first grounds action schemas and then applies constraint compilation. The target behavior is to preserve semantics while producing substantially smaller constraint-free specifications.

Paper targets in `scoring/reference.json` summarize Table 3 for compiled size and compilation time and include semantic-preservation targets from the paper's correctness claim.

## Evaluation Protocol

Run `bash scripts/reproduce.sh` to generate method artifacts in `outputs/method_results.json`, then run `bash scripts/evaluate.sh outputs/method_results.json`. The evaluator only reads the output artifact and writes `scoring/scores.json`.

The included benchmark uses generated symbolic planning tasks with high-arity actions, ground and quantified constraints, and explicit valid/invalid plan probes. It also includes a constraint-family suite for always, sometime, sometime-before, sometime-after, and at-most-once requirements. Future methods should emit the same JSON artifact format.

---

# Reproduction Log

### Iteration 1: gpt-5.5
- **Milestone**: `none` | **Status**: error
- **Working time**: 15m | **GPU**: 0.0h

<details>
<summary>Progress Log</summary>

<!-- Write your progress here -->

</details>

### Iteration 1: gpt-5.5
- **Milestone**: `none` | **Status**: error
- **Working time**: 30m | **GPU**: 0.0h

### Iteration 1: gpt-5.5
- **Milestone**: `none` | **Status**: error
- **Working time**: 30m | **GPU**: 0.0h

### Iteration 1: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 11m | **GPU**: 0.0h
- **Jobs**: 1 total (1 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

</details>


---

# Reproduction Milestones

**Current: core_claim**

## Stop Justification
- Completed at milestone `core_claim`.
