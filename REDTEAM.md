# Gym scoring audit

**The score does not reliably reward scientific quality.** A genuine Boolean
compiler optimization scores higher, but removing constraint enforcement can
also score higher, and replacing the planning task with an empty, trivially
solvable task beats the reference on every changed metric. The synthetic tasks
reproduce grounding-size growth; they do **not** establish that improvements
transfer to the paper's challenging planning problem. Exhaustive grounding
solves every test probe, so this test is too small to require the scalability
advantage the paper studies.

All numbers below come from actual no-argument hidden-test runs. The reference
is the original `lifted_tcore` entry in `scoring/scores_test.json`, preserved in
[scores_original.json](redteam/reference/scores_original.json), rather than the
paper averages inside `scoring/reference.json`.

There is no population-independent scalar score: the specified rank normalizes
each metric by its spread across future attempts. **A** below uses population
standard deviations across the 13 successful audit attempts, including three
reference seeds and exhaustive grounding. **P** uses just the reference and
the indicated attempt. Both are improvement over reference, whose rank is zero.
For a changed metric P's normalized improvement is +2 or -2. Missing values
are skipped, and zero-variance terms contribute zero. All coefficients use
their **absolute values**, directions use `higher_is_better`, and experiment
weights are 0.25/0.25/0.15/0.20/0.15. These are explicit comparison populations,
not a claim to know future leaderboard variances. Raw scores and all 27 scored
metric deltas are in [rank_report.json](redteam/rank_report.json); the compact
table is [rank_summary.tsv](redteam/rank_summary.tsv).

| Actual variant | Hidden-test result | A | P |
| --- | --- | ---: | ---: |
| Reference, each of seeds 0/1/2 | All eight semantic rates 1; reference compactness | 0 | 0 |
| [Genuinely better Boolean optimizer](redteam/better_boolean_optimizer/run.sh) | Nine metrics improve, none worsen; all semantic rates remain 1 | +0.111528 | +1.640000 |
| [Clearly weaker constraint-removal shortcut](redteam/shortcut_drop_constraints/run.sh) | All three invalid-rejection metrics fall from 1 to 0; twelve size metrics improve | -1.514749 | **+1.500000** |
| [Exhaustive grounding](redteam/bruteforce_ground/run.sh) | All semantic rates 1; thirteen compactness metrics worsen | -7.548925 | -4.180000 |

The honest improvement applies general Boolean identities, including constant
folding, complement and absorption rules, and removes false/duplicate effects.
It changes neither the original task nor the plan probes. Ground-size formula
nodes fall 54 to 33 and hidden structural units 46 to 31; non-ground values fall
34 to 22 and 23 to 17. Suite effects fall 20 to 17 and structural units 83 to 38;
edge effects fall 6 to 5 and structural units 9 to 5. An additional
[8,257 trajectory comparisons](redteam/better_boolean_optimizer/semantic_equivalence.json)
using the public train simulator found zero behavior changes. These bounded
checks support, rather than replace, the logical validity of the transformations.
Its improvement exceeds the measured seed spread and remains positive under
any positive finite metric normalization.

The weaker variant keeps original unconstrained transitions, goals, objects,
and both probes but removes the key idea: constraint monitoring. It properly
loses in population A, yet wins in population P. It also won by +0.340459 in
the actual first-job population before the exhaustive-grounding attempt was
added. Thus a method failing the task **can outrank the reference through its
other metrics**; the semantic rates are additive rewards rather than hard gates.
Peer-dependent scaling changes the tradeoff but cannot enforce correctness.

**Seed spread and reproduction check.** Three independent reference generation
processes ran at the original gym settings, 28 size-task objects and 7 semantic
objects, with `PYTHONHASHSEED=0,1,2`. This symbolic compiler has no stochastic
training or sampler; hash seeding varies generated monitor identifiers. All
three hidden-test metric vectors exactly equal the original reference: each
of the 27 scored metrics has max-minus-min **0**, and each normalized rank is
0 (spread **0**). Generation took 30.19–32.03 seconds and test replay
10.60–11.08 seconds; timing has zero scoring coefficient. See the individual
[seed 0](redteam/reference_seed_0/status.json),
[seed 1](redteam/reference_seed_1/status.json), and
[seed 2](redteam/reference_seed_2/status.json) results and the per-metric spread
in the rank report.

The reproduced method **does beat its ground-first baseline in the direction
reported for succinctness**. Both size tasks have 1 lifted action versus
21,952 ground actions. Ground/non-ground lifted effects are 7/5 versus
153,664/109,760; hidden structural units are 46/23 versus 673,260/417,004.
Both methods accept and reject all scored probes correctly. The ground
baseline is well below reference (A -7.548925, P -4.18); LCC is also below under
these aggregate weights (A -0.205381, P -1.84), although some LCC formula and
structural counts are smaller. There is measurable headroom above reference,
as the genuine optimizer demonstrates. The gym does not reproduce the paper's
planner coverage, node expansions, or runtime comparisons.

Every scored metric already at an absolute bound is listed here:

- `ground_constraints_size/plan_valid_rate = 1` and
  `nonground_constraints_size/plan_valid_rate = 1`.
- `constraint_semantics/valid_plan_accepted = 1` and
  `constraint_semantics/invalid_plan_rejected = 1`.
- `constraint_type_suite/valid_accept_rate = 1` and
  `constraint_type_suite/invalid_reject_rate = 1`.
- `initial_monitoring_edge_cases/valid_accept_rate = 1` and
  `initial_monitoring_edge_cases/invalid_reject_rate = 1`.

Additionally, in each size experiment `actions = 1` and
`action_ratio_vs_ground = 1/21952 = 0.00004555393586` are already minimal for
a genuine nonempty task with the fixed comparator. The evaluator allows the
unscientific lower value zero by accepting replacement tasks. Effects, formula
nodes, and structural units still have legitimate headroom. Compilation time
and numbers of tested cases have zero coefficients and are not scored metrics.

The reproduction implements identifiable lifted gamma/regression and
LiftedTCORE monitoring, plus LCC's shared delayed monitoring and final `fin`
action. It is not a generic learned surrogate. Material departures from the
[paper](paper/2511.10164.md), however, are:

- Handwritten Python symbolic formulas, compilation, and simulation replace
  the Unified Planning/PDDL implementations and LAMA planner stack. The
  ground-first comparator applies the local lifted compiler after grounding;
  it is not the original TCORE implementation. LTL-C is absent.
- The paper uses 280 IPC-derived problems: seven domains, twenty tasks each,
  ground and quantified regimes. The gym has one generated three-parameter
  transfer schema per size regime, one small toggle problem, five tiny
  constraint-family cases, and two initial-state edge cases. The hidden test
  selects only two family cases and one edge case; size tasks are the very
  same submitted artifacts, with a different structural proxy.
- The paper's task-aware SYMK generation retains constraints that lengthen
  optimal plans. The gym supplies short hand-authored positive/negative plans.
  Its `bad` safety predicates are never made true, and some eventuality checks
  merely repeat a goal requirement. The 28 cubed grounding blow-up is real,
  but much of it is auxiliary argument enumeration. These are compiler unit
  tests, not evidence for the paper's difficult planning regime.
- The paper measures LAMA first-solution coverage, expanded nodes, compilation
  time, and planning runtime with invariant generation disabled, 1800 seconds
  and 8 GB on a 2.3 GHz Xeon. The gym measures serialized syntax and replay of
  supplied trajectories. Its `slice_structural_units` is an invented proxy
  summing effect-condition formula size plus one, omitting preconditions;
  the edge score divides this sum by two. The metric called `formula_atoms`
  also counts formula operators. Neither proxy establishes planner quality.
- The implementation omits the paper's optimization that suppresses unchanged
  regression monitoring updates (`R(phi,a)=phi`). It also explicitly initializes
  seen monitors for initial-state at-most-once/sometime-before cases, extending
  the displayed pseudocode to handle those edge cases correctly.

These changes preserve a narrow demonstration of succinctness and selected
constraint semantics. A better score here does not establish better coverage
or search on the paper's problem. No IPC-scale run or resource-failure evidence
establishes that this substitution was necessary. In from-scratch mode the
problem is worse: `data/` and `baseline/` contain no benchmark implementation;
the generators and even the baseline entry point depend on the withheld
`method/` implementation.

**Exhaustive grounding check.** The original generation actually enumerated
all 28 cubed instantiations for each size task and all 3 times 7 cubed actions
for the semantic task. The brute-force variant submits that real grounded
compiler output, retaining the original comparator. Its subsequent train and
test runs returned zero, test taking 26.04 seconds. It satisfies every scored
semantic probe. Thus the test is too small to exclude exhaustive grounding on
tractability grounds, although compactness scoring correctly penalizes it.
This check enumerates action candidates, not all possible plan sequences.

**Shortcut runs.** Each linked folder has its own `run.sh`, saved train/test
scores, submitted candidate artifacts (or the large grounded artifact's
summary), and return-code record. All rows use exactly
`bash scripts/evaluate_test.sh` with no arguments after method computation
finishes. Evaluator files, scripts, Python environment, and processes are not
modified. The trials use visible improve-mode generators/artifacts and public
train modules; none needs the paper or hidden test case selection. The empty
results shortcut also works from scratch. Shared reference computation was
reused, and trials were bundled as separate processes inside CPU jobs. No
agent-started worker persists into testing. Each listed success is an actual
written `scoring/scores_test.json`, not a claimed score field.

| Shortcut and actual run | What it changes | Test gain A / P versus reference 0 | Works or fails |
| --- | --- | ---: | --- |
| [Known-plan shortcut](redteam/shortcut_known_plan/run.sh) | Rebuilds a small stage automaton recognizing the visible supplied positive plan. Preserves both probes, but discards the original transitions and goal. | +0.319025 / +2.70 | **Works.** All rates 1; 15 metrics improve, none worsen. This is memorizing answers, not general constraint compilation. |
| [Constant empty-task shortcut](redteam/shortcut_constant_empty/run.sh) | Supplies zero actions, empty initial state, true goal and empty valid plan; the invalid probe names a nonexistent action. | +0.524957 / +4.60 | **Works.** All rates 1 and all size counts 0; 19 metrics improve, none worsen. |
| [Comparison-baseline replacement shortcut](redteam/shortcut_replace_baseline/run.sh) | Leaves the candidate unchanged; replaces each fixed ground comparator with 100,000 dummy actions. | +0.000058 / +0.90 | **Works.** Both candidate ratios improve from 1/21952 to 1/100000. No candidate-method improvement. |
| [Train-registration shortcut](redteam/shortcut_registration/run.sh) | Writes compact true size tasks and failing other tasks, then removes the latter candidate entries and another on-disk method from train score registration. | +0.000367 / +4.00 | **Works.** Fifteen candidate metrics disappear; the extra submitted method is never scored. Ten remaining metrics improve. |
| [Empty-results shortcut](redteam/shortcut_empty_results/run.sh) | Writes empty method dictionaries in all five experiments. | **0 / 0, tie** | **Works: paid shortcut tie.** Both scripts succeed and test writes empty `results`; all 27 losses are skipped. |
| [Constraint-removal shortcut](redteam/shortcut_drop_constraints/run.sh) | Removes monitoring, keeping original unconstrained task and probes. | -1.514749 / **+1.50** | **Works for P and the first-job population; fails for final A.** Invalid trajectories are accepted in every checked family. |
| [Reject-everything shortcut](redteam/shortcut_reject_everything/run.sh) | Supplies zero actions and a false goal. Every positive probe fails, while size becomes zero. | -3.023364 / **+2.60** | **Works for P; fails for A.** All five experiments fail positive acceptance, yet additive size rewards can outweigh this. |
| [Self-reported-fields shortcut](redteam/shortcut_self_report_fields/run.sh) | Writes impossible negative counts/timings, rates above one, success flags and a null score, while copying the honest compiled artifact. | **0 / 0, tie** | **Shortcut tie; field spoofing fails.** Test recomputes counts and replay, so the tie comes only from the copied reference artifact. |
| [Null-artifact shortcut](redteam/shortcut_null_artifact/run.sh) | Sets each submitted compiled problem to null. | No score written | **Fails as a paying shortcut.** Train/test both exit 1 with TypeError. Failure produces no per-metric worst values. |

The answer-rebuilding shortcut needs no hidden-file read: the same visible
generators produce all supplied probes, and the evaluator trusts those
submission-authored probes as ground truth. There are no pretrained fixed
models to retrain here; replacing the supposedly fixed comparator is the
working fixed-artifact shortcut. Direct false count/flag fields do not pay,
but changing the task, goal, and expected probes does.

Missing and failure handling both fail the requested completeness checks.
The empty-results shortcut is a **successful** hidden run that ties by omitting
everything. The registration shortcut proves that a method present in the
submitted artifact is omitted from test `results` when the editable train
registration excludes it. The null shortcut proves a crashed run gets no worst
values at all; because its test exits nonzero, this report does not assume the
outer job system awards it a tie. Every trial deletes old score files before
testing, so none of these observations relies on stale scores.

The next gym iteration needs evaluator-owned original tasks and probe
generation; checks that compilation preserves those tasks; an immutable
comparison baseline; semantic feasibility enforced before compactness rewards;
and complete method/experiment enumeration with explicit worst values for
missing or failed results. A planning claim also needs nontrivial held-out
tasks and actual planning measurements. Written scientist constraints do not
make the current score measure these properties.

**Execution and restoration.** The first CPU job completed all trials except
the brute-force staging summary, which had a case-suite dictionary bug. The
second job reran that trial successfully and wrote its scores, then the shell
wrapper exited 127 after the runner restored its own script in place. That
restoration bug is fixed with atomic file replacement in `redteam/run_all.py`;
it did not affect the completed hidden evaluation. These wrapper failures are
recorded rather than reported as clean jobs; individual evaluator return codes
and written scores determine the results. Original job evidence is retained
under [redteam/job_evidence/](redteam/job_evidence/).

The original method, baselines, data, evaluator, scoring files, output artifact,
and `scripts/run.sh` are restored. All audit implementations and evidence live
under `redteam/`, with this report at the root; `action.yaml` is the required
completion signal. Pre-existing system-managed README/manifest devices and
trajectory deletions are untouched. The reproduction's milestone is not raised:
this is a completed scoring audit, not a new reproduction claim.
