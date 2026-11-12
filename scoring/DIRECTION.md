# Research Direction

## Research Problem

Constraint compilation for lifted planning: transforming planning tasks with qualitative trajectory constraints into constraint-free lifted tasks with exactly the same valid plans, while controlling the size of the compiled specification.

## Core Contribution Scope

Improve lifted (or otherwise grounding-free) constraint compilation: fewer added conditional effects, smaller and simpler monitoring formulas, better scaling with the number of constraints, exploiting what is provably known about the reachable states of the compiled task, sharing monitoring between constraints, or choosing encodings per constraint -- always exact.

## Out of Bounds

Grounding the task; returning tasks that are only correct on sampled trajectories; solving the planning task inside the compiler; reading the evaluator's held-out instances; dropping support for any constraint family or for quantified formulas.
