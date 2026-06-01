# Experiment Overview

## ground_constraints_size

Tests whether constrained planning tasks with ground trajectory requirements can be converted into compact constraint-free tasks while preserving a valid solution trajectory.

## nonground_constraints_size

Tests whether the same compactness and semantic preservation hold when the constraints use quantified formulas rather than only object constants.

## constraint_semantics

Tests whether the converted task accepts a valid trajectory and rejects a trajectory that violates an at-most-once requirement.

## constraint_type_suite

Tests whether converted tasks accept valid trajectories and reject invalid trajectories for each supported temporal constraint family.

## initial_monitoring_edge_cases

Tests whether converted tasks correctly handle constraints whose relevant witness or protected condition is true before the first action.
