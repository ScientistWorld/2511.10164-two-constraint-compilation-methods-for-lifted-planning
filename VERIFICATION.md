# Verification Report

## Initial Assessment

The workspace started with `core_claim` recorded in `MILESTONES.md`. The implementation contains an explicit symbolic compiler, a ground-first baseline, generated planning benchmarks, reusable evaluation scripts, and scored artifacts. The claimed milestone is justified: the previous successful CPU validation ran the reproduction flow and `python validate.py --compare`, and the current workspace still validates.

## Issues Found

- Minor: `briefing/evaluation.md` described wall-clock compile time as a lower-is-better metric even though `reference.json` correctly gives `compile_seconds` zero scoring weight.
- Minor: `briefing/evaluation.md` used a method-specific baseline name in a method-agnostic file.
- Minor: `scoring/TARGETS.md` listed semantic validity as the primary metric for size experiments, while `reference.json` correctly uses the structural compactness metric as primary and semantic validity as a constraint.
- Cosmetic: the workspace root contained an untracked generated core dump.

## Fixes Applied

- Clarified that compile time is audit-only and not part of scoring.
- Reworded the baseline description to a method-agnostic ground-first compiler.
- Updated target documentation so the size experiments prioritize `slice_structural_units` while preserving semantic-validity gates.
- Removed the untracked root core dump.

## Final Judgment

The workspace is ready to serve as a research gym for the reproduced core claim. Improve-mode agents can build on the implemented method and compare against `scores.json`; from-scratch agents can use the method-agnostic problem, data format, and evaluator without importing from `method/`. The main limitation is scale: the gym uses generated symbolic planning tasks rather than the full IPC/LAMA benchmark suite from the paper.

- Milestone: core_claim
- Ready for gym use: yes
- Confidence: medium
- Key limitation: generated symbolic benchmarks rather than the full IPC/LAMA suite
