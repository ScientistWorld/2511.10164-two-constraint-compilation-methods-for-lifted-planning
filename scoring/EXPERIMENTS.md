# Experiment Overview

Every experiment runs each registered compiler on evaluator-generated constrained planning tasks (public train instances in `eval/train/`, held-out test instances generated at test time). Exact plan preservation is a gate for the whole run; the size metrics compare compiled tasks against the fully grounded task. See `briefing/evaluation.md` for the interface and metric definitions.

## ground_constraints_size (weight 0.25)

Does the compiler keep the constraint-free task small when the domain has high-arity actions over many objects (full grounding of 10^6-10^8 actions) and the constraints mention specific objects? Establishes the core succinctness claim at a scale where ground-first compilation is impractical.

## nonground_constraints_size (weight 0.25)

The same question when every constraint is quantified ("no object may ever...", "some object must at some point..."). Establishes that succinctness survives quantified constraints.

## many_constraints_size (weight 0.15)

Large tasks with 30-45 constraints of all families. Establishes how compiled size grows with the number of constraints -- the regime the paper identifies as a weakness of lifted compilation.

## constraint_type_suite (weight 0.20)

Small tasks covering all five constraint families (ground and quantified), checked exhaustively against the original task. Establishes exact plan preservation for every family, together with compactness on small tasks.

## initial_monitoring_edge_cases (weight 0.15)

Small tasks whose constraint formulas already hold in the initial state, checked exhaustively. Establishes that the compiled task handles constraints whose status is decided before the first action.
