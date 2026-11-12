# Evaluation Targets

All experiments share the same metrics (definitions in `briefing/evaluation.md`). Primary metric of every experiment: `effects_vs_ground_log10` (lower is better).

## Constraint (gate): exact plan preservation

`semantic_agreement` must be 1.0 in every experiment. Any disagreement on any task, or a crash, timeout, oversized or malformed compiled task, fails the run: every metric of every experiment gets its worst value.

## Benefit: succinctness

| experiment | metrics | reference (LiftedTCORE, held-out test) |
|---|---|---|
| ground_constraints_size | effects / actions vs ground (log10), formula nodes, largest formula | -6.95 / -6.89 / 2.32 / 1.45 |
| nonground_constraints_size | same | -7.13 / -6.83 / 2.48 / 1.51 |
| many_constraints_size | same | -5.94 / -6.36 / 3.38 / 2.39 |
| constraint_type_suite | same, exhaustive check | -0.88 / -0.94 / 2.06 / 1.36 |
| initial_monitoring_edge_cases | same, exhaustive check | -0.85 / -0.93 / 2.12 / 1.43 |

Paper reference points (Table 3, IPC scale, TCORE grounded by reachability): LiftedTCORE 7 actions / 58-60 effects, LCC 8 / 63-67, TCORE 21K / 95-96K; largest introduced formula (non-ground) 26 vs 18 atoms. They are kept under `_paper_reported` in `reference.json`; the gym's comparator is the full grounding, so gym ratios are 3-4 orders of magnitude smaller.

## Not scored

Compilation time (hardware dependent) and planner coverage/expansions (the paper's LAMA experiments) are not measured.
