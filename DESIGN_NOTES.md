# Train/Test Evaluation Design Notes (hardening iteration)

* **Interface.** A method registers a compiler command (`outputs/compilers/<name>.json`); train and test evaluators enumerate every registration and run each compiler once per task. The test never reads `scoring/scores_train.json`.
* **Instances.** Generated in memory from fixed seeds: `eval/train/train_lib.py` (public) and `eval/test/test_lib.py` (held-out seeds; never written to disk). The two files are copies with different seeds and share no code.
* **Gate.** Hidden goal-reaching probes (witness, per-constraint violators, other valid, non-goal, inapplicable plans) on large tasks; complete product exploration on small tasks (generation keeps only small tasks with <= 2500 reachable state/monitor pairs). Any mismatch, crash, timeout (30 s), memory (4 GB) or size (32 MB) failure, malformed output or invalid registration fails the run: worst values everywhere. No registration -> `missing_submission` with worst values.
* **Comparators.** Ground-first sizes are computed analytically from the task by the evaluator.
* **Metrics.** log10 ratios vs the full grounding (effects, actions), log10 formula nodes (total, largest). Deterministic: no wall-clock metric, no sampling in the compilers.
* **Train/test split.** Same generator and settings, disjoint seeds; reference values agree within ~0.1 log10 across slices.
