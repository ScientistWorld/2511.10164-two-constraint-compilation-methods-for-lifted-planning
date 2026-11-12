# Overview

- **Paper ID:** 2511.10164
- **Title:** Two Constraint Compilation Methods for Lifted Planning
- **Domain:** Automated Planning
- **TL;DR:** The paper compiles qualitative PDDL trajectory constraints away in lifted form, avoiding the grounding blow-up of prior TCORE-style compilation.

## Short Summary

The paper studies planning tasks with safety, ordering, and intermediate-goal trajectory constraints. It proposes two compilers that remove the constraints without grounding the task, proves that they preserve exactly the valid plans, and shows that the compiled tasks are orders of magnitude more succinct than those of a ground-first compiler while remaining competitive for a standard planner.

## Key Results (paper)

- On the paper's main benchmark (280 IPC-2023 tasks), LCC solved 246/280 tasks and LiftedTCORE 238/280, comparable to ground TCORE at 245/280.
- Average compiled actions/effects were about 7-8 actions and 58-67 effects for the lifted methods, versus about 21K actions and 95K-96K effects for ground TCORE.
- The paper names its own limitation: with many constraints, lifted compilers add monitoring to every action that may affect each constraint.

## This gym

Generated lifted tasks with high-arity actions over 20-32 objects (full grounding: 10^6-10^8 actions), ground and quantified constraints of all five families, a many-constraints regime, and small tasks checked exhaustively. A method is a compiler command; the evaluator runs it on hidden tasks, verifies exact plan preservation and measures compiled size (see `briefing/evaluation.md`).

---

# Problem Definition

## Research Question

How can qualitative PDDL state-trajectory constraints be removed from a lifted planning task so that the resulting constraint-free task has exactly the same valid plans, while the compiled specification stays small even when actions have high arity and there are many objects?

The constraint families are `always(phi)`, `sometime(phi)`, `at_most_once(phi)`, `sometime_before(phi, psi)` and `sometime_after(phi, psi)` (PDDL3 semantics over the whole state trajectory, initial state included); `phi` and `psi` may contain quantifiers. A solution is a compiler: constrained task in, constraint-free task out, consumable by an ordinary planner that knows nothing about trajectory constraints.

## Why It Matters

Many planners do not support trajectory constraints. Compiling them away lets standard planners handle safety requirements, intermediate goals and ordering requirements. If the compiler must first ground the task, high-arity actions over many objects make the compiled task explode (millions of ground actions), so a useful compiler must work on the lifted representation.

## Success Criteria

* **Exactness (hard constraint):** every plan valid for the constrained task is valid for the compiled task and vice versa. A compiler that accepts a violating plan, rejects a valid one, fails, or produces a malformed task fails the benchmark outright.
* **Succinctness:** among exact compilers, fewer conditional effects and actions, and smaller (total and largest) precondition/effect-condition formulas, are better, including on tasks with many constraints.

---

# Paper's Method

## Key Contribution

The paper introduces two lifted compilers for qualitative PDDL state-trajectory constraints: LiftedTCORE and LCC. Both remove constraints without grounding the planning task first.

## Approach

LiftedTCORE (Algorithm 1) generalizes TCORE's regression operator to lifted formulas and lifted actions. For each constraint formula and action schema it computes the lifted regression R^L(phi, a) via the lifted gamma operator (most general unification of formula literals with possibly universally quantified conditional effects, Definitions 2-6) and adds action-specific monitoring preconditions and effects (`hold`, `seen` atoms). Updates with R^L(phi, a) = phi (the action cannot change phi) are omitted (Section 3.2).

LCC (Algorithm 2) avoids regression. It adds one shared set of monitoring preconditions and conditional effects to every action, with `hold`, `seen` and `prevent` atoms, and a final `fin` action so the last state is checked despite LCC's one-step monitoring delay.

## Implementation in this workspace

`method/planning.py` implements both compilers; `method/compile.py --variant {lifted_tcore,lcc,lifted_tcore_no_omission}` is the registered command. Two pseudo-code details are completed so that the correctness propositions hold when a monitored formula is already true initially (LiftedTCORE initialises `seen` for AtMostOnce(phi) and for the witness of SometimeBefore). Quantified constraint variables are renamed apart from action variables before regression.

## Main Claims

Constraints can be compiled away without grounding while preserving plan validity (Propositions 1 and 3). The lifted compilers produce much more succinct compiled specifications than ground-first TCORE; LiftedTCORE introduces fewer effects, LCC smaller formulas.

---

# Evaluation

## Interface: a method is a compiler command

Register a compiler by writing `outputs/compilers/<method_name>.json`:

```json
{"command": ["python3", "path/to/your_compiler.py", "--any", "flags"]}
```

The evaluator appends two paths and runs the command once per task, from the workspace root:
`<command...> <input.json> <output.json>`. The input is one constrained task; the compiler must write one constraint-free task to `output.json` and exit 0. Every registered compiler is scored; `scripts/method.sh` and `scripts/baseline.sh` show the registrations of the reference compilers. Per task the compiler gets 30 s, 4 GB of address space and at most 32 MB of output.

### Task format (JSON)

```
{"objects": ["o0", ...],
 "predicates": {"f0": 2, ...},                       # informative
 "actions": [{"name": "act0", "params": ["?x0", ...],
              "precondition": F,
              "effects": [{"forall": ["?z0"], "condition": F,
                           "literal": {"pred": "f1", "args": ["?z0", "?x0"], "negated": false}}]}],
 "init": [{"pred": "f0", "args": ["o1", "o3"]}, ...],
 "goal": F,
 "constraints": [{"name": "c0", "kind": "always|sometime|at_most_once|sometime_before|sometime_after",
                  "phi": F, "psi": F}]}               # psi only for the two binary kinds
```

Formulas `F` are `{"op": "bool", "value": b}`, `{"op": "atom", "literal": L}`, `not` (`child`), `and`/`or` (`children`), `imply` (`left`, `right`), `eq` (`left`, `right` terms), `exists`/`forall` (`vars`, `child`). Variables start with `?`; objects are distinct constants (unique names). Effects follow PDDL: all conditions are evaluated in the state before the action, deletes are applied before adds, a `forall` effect applies for every assignment of its variables to objects.

### What the compiled task must look like

* Same JSON format, no (or an empty) `constraints` list; `objects` are taken from the input.
* Every action of the input keeps its name and number of parameters (plans are written in the original action names). Alternatively an input action may be replaced by ground copies named `name(o1,o2,...)` without parameters.
* Any other action is *auxiliary*: it must have no parameters; a planner may interleave auxiliary actions anywhere in a plan.
* A plan of the input task is accepted by the compiled task if it can be executed, with auxiliary actions inserted (up to 3 between consecutive steps and at the end), so that the compiled goal holds.

## Instances

All instances are generated by the evaluator in memory from fixed seeds: random lifted domains (static and fluent predicates of arity 0-3, action schemas of arity up to 5, conditional effects and universally quantified effects), a random initial state, a goal reached by a hidden witness plan, and task-aware constraints that the witness satisfies and that other goal-reaching plans violate. `eval/train/` generates the public train instances; the held-out test instances come from different seeds and are never written to disk.

## Semantic gate

* **Large tasks** (size experiments): a set of hidden plans per task -- the witness, goal-reaching plans that violate each constraint, other valid plans, non-goal and inapplicable plans -- is replayed on the original task (with its trajectory constraints) and on the compiled task; the verdicts must agree.
* **Small tasks** (3-4 objects): the product of the original task, its constraint monitors and the compiled task is explored over every ground action sequence until no new state pair appears (complete; tasks with more than 2500 reachable state pairs are not generated); acceptance must agree in every reached pair.

Any disagreement, crash, timeout, oversized or malformed output fails the method's whole run: every metric of every experiment then gets its worst value (`semantic_agreement` 0, ratio metrics 1.0, formula metrics 7.0). If no compiler is registered at all, a `missing_submission` entry with worst values is written.

## Metrics (per experiment; computed by the evaluator from the compiled tasks)

| metric | better | meaning |
|---|---|---|
| `semantic_agreement` | higher | fraction of agreeing checks (1.0 for any run that passes the gate) |
| `effects_vs_ground_log10` | lower | mean log10(compiled conditional effects / effects of the fully grounded task) |
| `actions_vs_ground_log10` | lower | mean log10(compiled actions / actions of the fully grounded task) |
| `formula_nodes_log10` | lower | mean log10(nodes of all preconditions, effect conditions and the goal, + 1 per initial-state atom added or removed) |
| `max_formula_nodes_log10` | lower | mean log10(nodes of the largest single precondition / effect condition / goal) |

The fully grounded task (every schema instantiated for every object tuple, quantified effects expanded) is computed analytically by the evaluator; it is the ground-first comparator. Compilation time is not scored.

## Baselines

`baseline/ground_tcore.py` grounds the task and compiles the constraints by ground regression (TCORE-style). On the benchmark's tasks (10^6-10^8 ground actions) it exceeds its ground-action budget, so its run is scored as failed.

## Protocol

```
bash scripts/method.sh          # register the reference compilers (or write your own registration)
bash scripts/baseline.sh        # register the ground-first baseline
bash scripts/evaluate_train.sh  # -> scoring/scores_train.json (public instances; failures report a counterexample plan)
bash scripts/evaluate_test.sh   # -> scoring/scores_test.json  (held-out instances; no counterexamples)
```

`bash scripts/evaluate.sh` writes the same train-slice report to `scoring/scores.json`.

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

### Iteration 2: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 3m | **GPU**: 0.0h
- **Jobs**: 2 total (2 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-01 00:00] - method_runs
- Implemented and ran the paper's actual lifted constraint compilation procedures on generated symbolic planning tasks.
- LiftedTCORE, LCC, and the ground-first TCORE baseline execute end-to-end.

### [2026-06-01 00:00] - core_claim
- Local reproduction validates the central claim on generated high-arity planning tasks: lifted compilers preserve trajectory-constraint semantics while producing far fewer actions/effects than a ground-first compiler.
- Semantic checks cover all five constraint families in the paper: always, sometime, at-most-once, sometime-before, and sometime-after.

### [2026-06-01 00:00] - core_claim
- Continuing-agent audit confirmed the implementation is the paper's actual compiler family, not a surrogate.
- Fixed lifted unification for repeated variables so lifted gamma/regression emits equality conditions required by the paper's weakest-condition definitions.

### [2026-06-01 07:35] - core_claim
- Compute job `f285ea84-69a` completed successfully in the container.
- The job ran repeated-variable lifted unification tests, regenerated reproduction scores, and passed validation.

</details>

### Iteration 3: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 13m | **GPU**: 0.0h
- **Jobs**: 1 total (1 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 4: gpt-5.5 (designer_stage_1)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 7m | **GPU**: 0.0h
- **Jobs**: 1 total (1 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 5: gpt-5.5 (designer_stage_2)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 4m | **GPU**: 0.0h
- **Jobs**: 1 total (1 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 6: gpt-5.5 (designer_stage_3)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 7m | **GPU**: 0.0h
- **Jobs**: 3 total (3 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 7: gpt-5.5 (packager)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 2m | **GPU**: 0.0h
- **Jobs**: 3 total (3 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 8: gpt-5.5 (verifier)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 5m | **GPU**: 0.0h
- **Jobs**: 3 total (3 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 9: gpt-5.5 (verifier)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 6m | **GPU**: 0.0h
- **Jobs**: 4 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

### [2026-06-01 09:35] - core_claim
- Added an explicit compute-job assertion that both ground and non-ground size benchmarks generate at least 20K grounded baseline actions.
- Re-submitting the full CPU reproduction path because the checked score artifact still reflected an older smaller size run.

### [2026-06-01 09:45] - core_claim
- Final verification job `50dd2235-44c` completed with exit code 0.
- The job regenerated `scoring/scores.json` at the 28-object size setting and confirmed both size benchmarks produce 21,952 ground-first baseline actions.
- Train/test scoring and `python validate.py --compare` passed inside the compute container.

</details>

### Iteration 10: gpt-6.1-sol (redteam)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 10m | **GPU**: 0.0h
- **Jobs**: 4 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

### [2026-06-01 09:35] - core_claim
- Added an explicit compute-job assertion that both ground and non-ground size benchmarks generate at least 20K grounded baseline actions.
- Re-submitting the full CPU reproduction path because the checked score artifact still reflected an older smaller size run.

### [2026-06-01 09:45] - core_claim
- Final verification job `50dd2235-44c` completed with exit code 0.
- The job regenerated `scoring/scores.json` at the 28-object size setting and confirmed both size benchmarks produce 21,952 ground-first baseline actions.
- Train/test scoring and `python validate.py --compare` passed inside the compute container.

</details>

### Iteration 11: claude-opus-5-5 (hardener)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 1.0h | **GPU**: 0.0h
- **Jobs**: 6 total (6 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

### [2026-06-01 09:35] - core_claim
- Added an explicit compute-job assertion that both ground and non-ground size benchmarks generate at least 20K grounded baseline actions.
- Re-submitting the full CPU reproduction path because the checked score artifact still reflected an older smaller size run.

### [2026-06-01 09:45] - core_claim
- Final verification job `50dd2235-44c` completed with exit code 0.
- The job regenerated `scoring/scores.json` at the 28-object size setting and confirmed both size benchmarks produce 21,952 ground-first baseline actions.
- Train/test scoring and `python validate.py --compare` passed inside the compute container.

### [2026-11-12] - core_claim (hardening iteration)
- Restored the paper's Section 3.2 omission of R^L(phi,a)=phi updates in LiftedTCORE; constraint variables renamed apart.
- Replaced the artifact-based evaluator with evaluator-owned generated tasks (held-out ones generated at test time), a compiler-command interface, an exact-plan-preservation gate (hidden probes + complete product exploration), worst values for failed/missing runs, and analytic ground-first comparators.
- Added the many-constraints experiment (paper's stated limitation). Job 7214d826-e8c: reference passes every gate; paper direction reproduced (lifted >> grounded; LiftedTCORE fewer effects, LCC smaller formulas); all shortcuts fail; better variant scores higher, weaker lower. See HARDENING.md.

</details>


---

# Reproduction Milestones

**Current: core_claim**

## Stop Justification
- Completed at milestone `core_claim`.
