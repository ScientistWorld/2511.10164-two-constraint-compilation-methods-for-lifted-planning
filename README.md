# Two Constraint Compilation Methods for Lifted Planning

<!-- scope-note -->
> [!NOTE]
> **Not a full reproduction of the paper.** This environment keeps the paper's core problem at a reduced scale so it is easy to run. It measures an AI scientist's idea and how well it is carried out, not the full research loop.

<!-- hardening-note -->
> [!NOTE]
> **Red-teamed and hardened.** A red team tried to score on this environment's hidden test without doing better research, and the environment was then fixed against the shortcuts that worked: see [`REDTEAM.md`](REDTEAM.md) and [`HARDENING.md`](HARDENING.md). The environment as it was before is kept as branch [`pre-hardening`](../../tree/pre-hardening).

| This paper | Scientist World, the framework this environment belongs to |
|:---:|:---:|
| <a href="https://arxiv.org/abs/2511.10164"><img alt="This paper on arXiv" src="https://img.shields.io/badge/arXiv-2511.10164-b31b1b?logo=arxiv&logoColor=white"></a> | <a href="https://arxiv.org/abs/2611.08478"><img alt="Scientist World on arXiv" src="https://img.shields.io/badge/arXiv-2611.08478-b31b1b?logo=arxiv&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world"><img alt="Scientist World code" src="https://img.shields.io/badge/Code-Scientist_World-181717?logo=github&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world_cli"><img alt="Command line code" src="https://img.shields.io/badge/Code-Command_line-181717?logo=github&logoColor=white"></a> |

| **Paper ID** | [2511.10164](https://arxiv.org/abs/2511.10164) |
|:---|:---|
| **Domain** | Automated Planning |
| **TL;DR** | The paper compiles qualitative PDDL trajectory constraints away in lifted form, avoiding the grounding blow-up of prior TCORE-style compilation. |

## Summary

The paper studies planning tasks with safety, ordering, and intermediate-goal trajectory constraints. It proposes LiftedTCORE, which uses lifted regression, and LCC, which uses shared monitoring logic with a final checking action. The reported experiments show that the lifted compilers preserve constraint semantics and produce compiled tasks with orders-of-magnitude fewer actions and effects than ground-first compilation.

## Problem

How can qualitative PDDL state-trajectory constraints be removed from a planning task while preserving exactly the same valid plans and avoiding explosive growth in the planning specification?

The constraints considered here are `always`, `sometime`, `at_most_once`, `sometime_before`, and `sometime_after`, including formulas with quantifiers. A solution must transform constrained planning tasks into constraint-free tasks that ordinary planners can consume.

## The paper's method

The paper introduces two lifted compilers for qualitative PDDL state-trajectory constraints: LiftedTCORE and LCC. Both remove constraints without grounding the planning task first.

## Key results of the paper

- On the paper's main benchmark, LCC solved 246/280 tasks and LiftedTCORE solved 238/280, comparable to ground TCORE at 245/280.
- Average compiled actions/effects were about 7-8 actions and 58-67 effects for lifted methods, versus about 21K actions and 95K-96K effects for ground TCORE.
- Average compilation time was milliseconds for the lifted compilers, versus several seconds for ground TCORE.

## Run it

```bash
pip install sciworld
sw research 2511.10164 --mode innovate --agent claude-code
sw evaluate 2511.10164
```

## More

The full problem statement, method notes, evaluation protocol and reproduction log are in [DETAILS.md](DETAILS.md).

