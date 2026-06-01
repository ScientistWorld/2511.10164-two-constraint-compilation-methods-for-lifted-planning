# Paper's Method

## Key Contribution

The paper introduces two lifted compilers for qualitative PDDL state-trajectory constraints: LiftedTCORE and LCC. Both remove constraints without grounding the planning task first.

## Approach

LiftedTCORE generalizes TCORE's regression operator to lifted formulas and lifted actions. For each constraint formula and action schema, it computes a lifted regression condition using unification against conditional effects, then adds action-specific monitoring preconditions and effects.

LCC avoids regression. It adds a shared set of constraint-monitoring preconditions and conditional effects to all actions, introduces monitoring atoms such as `hold`, `seen`, and `prevent`, and adds a final `fin` action so the last state is checked despite LCC's one-step monitoring delay.

## Main Claims

The primary claim is that constraints can be compiled away without grounding while preserving plan validity. The empirical claim is that the lifted compilers produce much more succinct compiled specifications and compile faster than ground-first TCORE, while remaining competitive when solved by a standard planner.
