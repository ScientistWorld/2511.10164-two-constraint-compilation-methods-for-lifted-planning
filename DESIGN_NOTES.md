# Train/Test Evaluation Design Notes

## Checks

- Read `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` side by side. The test script calls `eval/test/evaluate.py`, writes `scoring/scores_test.json`, and passes the optional train scores only to align method keys.
- Checked train/test evaluators for method attachment. Both slices read `outputs/method_results.json` artifacts produced by the method rather than importing or rerunning `method/`.
- Grepped for train/test cross-imports and direct path leakage. The split evaluators do not import each other.
- Grepped for hardcoded method defaults. The split evaluators enumerate methods present in the artifact and the test side can restrict to methods already scored by train.
- Checked for `scoring/scores_train.json` and `scoring/scores_test.json`; neither exists.
- Ran `bash -n` on both split scripts.

## Changes

- Removed `compile_seconds` from active train/test score outputs and kept it zero-weighted in `scoring/reference.json` only so legacy result files validate. Wall-clock timing is hardware-dependent and must not affect scoring.
- Added required `description` fields to every active metric in `scoring/reference.json`.
- Reweighted compactness slightly toward machine-independent structural measures: `formula_atoms` and `action_ratio_vs_ground` now carry more of the removed timing pressure.
- Made case coverage strict in both slices. A method now fails the slice if it omits any selected train or held-out test constraint case instead of receiving rates computed on a partial subset.

## Runtime Concerns For Runner Iteration

- The size experiments are global artifact rescoring rather than a true data split because the method currently emits one ground and one non-ground size task. They still measure the paper's compactness claim, but they will not create a train/test gap for a method that only overfits the semantic case names.
- `compile_seconds` remains in historical reference results, existing `scores.json`, and method artifacts. It has `coefficient: 0.0`, so it is schema-known but not an active scoring signal; the split evaluators do not emit it.
- The semantic rates may saturate for correct methods. The train/test distinction therefore depends mainly on held-out constraint families and strict coverage, while compactness metrics guard against bloated encodings.

## Real Run Assessment

- Job `c9bb701f-47e` ran `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` successfully on a CPU node and produced `scoring/scores_train.json` and `scoring/scores_test.json`.
- Method identifiers match exactly between train and test for every experiment: `ground_tcore`, `lcc`, and `lifted_tcore`.
- Every active metric declared in `scoring/reference.json` is present in both split score files. The split scripts emit no wall-clock `compile_seconds` values.
- Train and test are not byte-identical. The held-out semantic slices score different constraint families: train uses `always`, `sometime_before`, and `at_most_once`, while test uses `sometime` and `sometime_after`; the initial-monitoring edge case is also different across slices.
- Semantic acceptance/rejection rates are saturated at 1.0 for all existing methods. This is expected for the current artifact and remains useful as a constraint guard, while compactness metrics distinguish the proposed lifted compiler from expanded baselines.
- The real run showed that `constraint_types_tested` and `edge_cases_tested` are constant coverage audit fields once strict missing-case failure is enabled. They are now zero-weighted in `scoring/reference.json` so active scores are not driven by a method-independent count.
- The declared primary metrics were also saturated in the real split. I added `slice_structural_units` as a benchmark-only compactness primary: the train evaluator scores precondition-side structural units, and the test evaluator scores effect-side structural units. This creates a held-out metric-axis split for compactness while the semantic rates remain active constraints.
- `python validate.py` passes after adding the metric split, including primary train/test differentiation and primary train-slice method discrimination.
