# Evaluation Targets

## Primary: ground_constraints_size

Tests whether a compiler keeps the constraint-free planning specification compact on tasks with ground constraints.
- **Primary metric**: `plan_valid_rate` must remain high
- **Compactness metrics**: `actions`, `effects`, `formula_atoms`, and `action_ratio_vs_ground` (lower is better)

## Primary: nonground_constraints_size

Tests whether compactness is maintained when constraints contain quantifiers.
- **Primary metric**: `plan_valid_rate` must remain high
- **Compactness metrics**: `actions`, `effects`, `formula_atoms`, and `action_ratio_vs_ground` (lower is better)

## Constraint: constraint_semantics

Tests whether the transformed task preserves trajectory-constraint meaning.
- **Metric**: `valid_plan_accepted` and `invalid_plan_rejected` (higher is better)

## Constraint: constraint_type_suite

Tests semantic preservation across every supported qualitative constraint family.
- **Metric**: `valid_accept_rate` and `invalid_reject_rate` (higher is better)
- **Coverage metric**: `constraint_types_tested` should remain at 5

## Constraint: initial_monitoring_edge_cases

Tests semantic preservation when a monitoring condition is already true in the initial state.
- **Metric**: `valid_accept_rate` and `invalid_reject_rate` (higher is better)
- **Coverage metric**: `edge_cases_tested` should remain at 2
