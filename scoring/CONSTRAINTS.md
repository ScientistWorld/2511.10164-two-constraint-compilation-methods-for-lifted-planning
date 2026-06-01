# Scientist Constraints

## Problem Representation

Use the provided symbolic planning task format and generated benchmark settings. Do not replace the benchmark with an easier task family or remove quantified constraints.

## Evaluation

Use `scripts/evaluate.sh` and write the same `outputs/method_results.json` artifact format. Evaluation must read method outputs; it must not recompute the submitted method internally.

## Resources

Do not improve scores by reducing object counts, omitting high-arity actions, or dropping the ground baseline comparison. Changes must preserve the setting that exposes grounding growth.

## Compliance Checklist

- [ ] Uses the provided benchmark task families and constraint types
- [ ] Reports all metrics required by `scoring/reference.json`
- [ ] Keeps semantic-preservation checks enabled
- [ ] Keeps all five constraint-family checks in `constraint_type_suite`
- [ ] Keeps initial-state monitoring checks in `initial_monitoring_edge_cases`
- [ ] Does not edit `eval/` to import from `method/`
