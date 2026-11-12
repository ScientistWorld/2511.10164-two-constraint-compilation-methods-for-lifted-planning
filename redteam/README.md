This audit uses one CPU job. `python3 redteam/run_all.py` runs every individual
`redteam/<name>/run.sh`, then computes `rank_report.json` from actual hidden-test
output. Heavy work must run through the scheduler, not on the login node.

Each run stages ordinary submitted artifacts, finishes method computation,
runs `bash scripts/evaluate_train.sh`, then runs exactly
`bash scripts/evaluate_test.sh` without arguments in a new process. No trial
imports hidden evaluator code, changes the Python environment of evaluation,
edits restored evaluator files, or leaves a worker running during evaluation.
The registration shortcut intentionally edits the train method-selection file
after running train scoring; that file survives the specified handoff.

Shortcuts read only improve-mode method files, visible train modules, and their
own regenerated artifacts. The empty-results shortcut additionally works from
scratch without any reference artifact. The paper is used only to audit
reproduction fidelity, never to construct a shortcut.

The three reference reruns compile the original 28-object size problems and
7-object semantic problem with Python hash seeds 0, 1, and 2. There is no
stochastic training or data sampler. The Boolean optimizer is a real compiler
improvement: general logical identities, removal of false conditional effects,
and duplicate-effect removal. Extra train-simulator trajectory checks record
whether the optimization preserves behavior beyond the scored probes.

`bruteforce_ground` uses the actual exhaustively grounded compiler output as
the submitted method, with the original ground comparator kept present.
`shortcut_drop_constraints` is both the deliberately weaker scientific variant
and a shortcut trial if compactness compensates for incorrect semantics.

`rank_report.json` uses the coefficients' absolute values, metric directions,
experiment weights, and population standard deviations over successful audit
attempts. Future attempt variances are unknown. Two-attempt gains are also
reported for a population containing just the reference and that trial. Raw
scores and metric-by-metric deltas are authoritative; these explicitly defined
local rank comparisons are not predictions of an unknown future leaderboard.

The full original output is temporarily saved in ignored `.work/`, as are
reusable reference artifacts. Large generated outputs and logs are not
committed. Small submitted candidate artifacts, scores, errors, and rank
reports are retained. The job restores all original outputs and scoring files
and the original `scripts/run.sh` on exit.

Initial workspace state: README.md and manifest.json are pre-existing character
devices, and five tracked trajectory files are pre-existing deletions. The audit
does not change those system-managed paths. `base_commit.txt` records the start
commit; only the job runner and action signal are changed outside this folder
to submit the requested computation.
