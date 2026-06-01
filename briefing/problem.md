# Problem Definition

## Research Question

How can qualitative PDDL state-trajectory constraints be removed from a planning task while preserving exactly the same valid plans and avoiding explosive growth in the planning specification?

The constraints considered here are `always`, `sometime`, `at_most_once`, `sometime_before`, and `sometime_after`, including formulas with quantifiers. A solution must transform constrained planning tasks into constraint-free tasks that ordinary planners can consume.

## Why It Matters

Many planners do not natively support trajectory constraints. A good transformation lets those planners handle safety requirements, intermediate goals, and ordering requirements without first generating an enormous grounded action set.

## Success Criteria

A successful system preserves constraint semantics, accepts plans that satisfy the original constrained task, rejects plans that violate the original constraints, and keeps the compiled specification compact as object counts and action arities grow.
