# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-01 00:00] - method_runs
- Implemented and ran the paper's actual lifted constraint compilation procedures on generated symbolic planning tasks.
- LiftedTCORE, LCC, and the ground-first TCORE baseline execute end-to-end.

### [2026-06-01 00:00] - core_claim
- Local reproduction validates the central claim on generated high-arity planning tasks: lifted compilers preserve trajectory-constraint semantics while producing far fewer actions/effects than a ground-first compiler.
- Semantic checks cover all five constraint families in the paper: always, sometime, at-most-once, sometime-before, and sometime-after.

### [2026-06-01 00:00] - core_claim
- Continuing-agent audit confirmed the implementation is the paper's actual compiler family, not a surrogate.
- Fixed lifted unification for repeated variables so lifted gamma/regression emits equality conditions required by the paper's weakest-condition definitions.

### [2026-06-01 07:35] - core_claim
- Compute job `f285ea84-69a` completed successfully in the container.
- The job ran repeated-variable lifted unification tests, regenerated reproduction scores, and passed validation.
