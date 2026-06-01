# Evaluation Targets

## Primary: ground_constraints_size

Tests whether a compiler keeps the constraint-free planning specification compact on tasks with ground constraints.
- **Metric**: `actions`, `effects`, and `formula_atoms` (lower is better)
- **Constraint metric**: `plan_valid_rate` must remain high

## Primary: nonground_constraints_size

Tests whether compactness is maintained when constraints contain quantifiers.
- **Metric**: `actions`, `effects`, and `formula_atoms` (lower is better)
- **Constraint metric**: `plan_valid_rate` must remain high

## Constraint: constraint_semantics

Tests whether the transformed task preserves trajectory-constraint meaning.
- **Metric**: `valid_plan_accepted` and `invalid_plan_rejected` (higher is better)

## Constraint: constraint_type_suite

Tests semantic preservation across every supported qualitative constraint family.
- **Metric**: `valid_accept_rate` and `invalid_reject_rate` (higher is better)
- **Coverage metric**: `constraint_types_tested` should remain at 5
