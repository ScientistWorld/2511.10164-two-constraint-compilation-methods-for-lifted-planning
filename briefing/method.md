# Paper's Method

## Key Contribution

The paper introduces two lifted compilers for qualitative PDDL state-trajectory constraints: LiftedTCORE and LCC. Both remove constraints without grounding the planning task first.

## Approach

LiftedTCORE (Algorithm 1) generalizes TCORE's regression operator to lifted formulas and lifted actions. For each constraint formula and action schema it computes the lifted regression R^L(phi, a) via the lifted gamma operator (most general unification of formula literals with possibly universally quantified conditional effects, Definitions 2-6) and adds action-specific monitoring preconditions and effects (`hold`, `seen` atoms). Updates with R^L(phi, a) = phi (the action cannot change phi) are omitted (Section 3.2).

LCC (Algorithm 2) avoids regression. It adds one shared set of monitoring preconditions and conditional effects to every action, with `hold`, `seen` and `prevent` atoms, and a final `fin` action so the last state is checked despite LCC's one-step monitoring delay.

## Implementation in this workspace

`method/planning.py` implements both compilers; `method/compile.py --variant {lifted_tcore,lcc,lifted_tcore_no_omission}` is the registered command. Two pseudo-code details are completed so that the correctness propositions hold when a monitored formula is already true initially (LiftedTCORE initialises `seen` for AtMostOnce(phi) and for the witness of SometimeBefore). Quantified constraint variables are renamed apart from action variables before regression.

## Main Claims

Constraints can be compiled away without grounding while preserving plan validity (Propositions 1 and 3). The lifted compilers produce much more succinct compiled specifications than ground-first TCORE; LiftedTCORE introduces fewer effects, LCC smaller formulas.
