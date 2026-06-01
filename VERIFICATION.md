# Verification Report

## Initial Assessment

The workspace started with `core_claim` recorded in `MILESTONES.md`. The implementation is a real symbolic reproduction of the paper's lifted constraint compilers, not a surrogate: method code constructs compiled planning tasks, and evaluation code replays serialized compiled-task artifacts without importing from `method/`.

The claimed milestone remains justified from the last completed validation job, but the latest scaling change raised the default size benchmark to 28 objects while the committed `scoring/scores.json` still reflects an older smaller run. That artifact must be regenerated in the compute container before final sign-off.

## Issues Found

- Critical: `scoring/scores.json` is stale for the updated size setting. The current method default should produce at least 20K ground-first actions in both size experiments, but the committed scores still show 4096 and 343 actions.
- Minor: generated `jobs/` logs and stale `trajectory/` raw logs were tracked despite being excluded by `.gitignore`.

## Fixes Applied

- Removed tracked generated `jobs/` and `trajectory/` files from version control so they stay ignored.
- Kept `scripts/run.sh` as the validation entry point; it now regenerates the reproduction artifacts and fails unless both size experiments produce at least 20K ground-first baseline actions.

## Final Judgment

The workspace is structurally ready for gym use, but final sign-off is pending the CPU validation job that regenerates `scores.json` under the current 28-object size benchmark. If that job passes, the workspace should remain at `core_claim` and can be marked ready. Higher milestones would require the full IPC/LAMA evaluation stack or broader reproduced paper tables.

- Milestone: core_claim
- Ready for gym use: partial
- Confidence: medium
- Key limitation: generated symbolic benchmarks rather than the full IPC/LAMA suite, and current committed scores require regeneration after the scaling update
