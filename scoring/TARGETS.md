# Evaluation Targets

## Primary: ground_constraints_size

Tests whether a compiler keeps the constraint-free planning specification compact on tasks with ground constraints.
- **Primary metric**: `slice_structural_units` (lower is better; local generated-benchmark proxy, not a paper-reported table value)
- **Compactness metrics**: `actions`, `effects`, `formula_atoms`, and `action_ratio_vs_ground` (lower is better)
- **Semantic gate**: `plan_valid_rate` must remain 1.0

## Primary: nonground_constraints_size

Tests whether compactness is maintained when constraints contain quantifiers.
- **Primary metric**: `slice_structural_units` (lower is better; local generated-benchmark proxy, not a paper-reported table value)
- **Compactness metrics**: `actions`, `effects`, `formula_atoms`, and `action_ratio_vs_ground` (lower is better)
- **Semantic gate**: `plan_valid_rate` must remain 1.0

## Constraint: constraint_semantics

Tests whether the transformed task preserves trajectory-constraint meaning.
- **Metric**: `valid_plan_accepted` and `invalid_plan_rejected` (higher is better)

## Constraint: constraint_type_suite

Tests semantic preservation across every supported qualitative constraint family.
- **Metric**: `valid_accept_rate` and `invalid_reject_rate` (higher is better)
- **Coverage metric**: `constraint_types_tested` should remain at 5

## Constraint: initial_monitoring_edge_cases

Tests semantic preservation when a required condition is already true in the initial state.
- **Metric**: `valid_accept_rate` and `invalid_reject_rate` (higher is better)
- **Coverage metric**: `edge_cases_tested` should remain at 2

## Audit-Only Metrics

`compile_seconds` may be reported for traceability, but it has zero scoring weight because wall-clock timing is not portable across hardware.
