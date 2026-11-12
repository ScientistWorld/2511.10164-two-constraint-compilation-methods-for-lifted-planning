# Problem Definition

## Research Question

How can qualitative PDDL state-trajectory constraints be removed from a lifted planning task so that the resulting constraint-free task has exactly the same valid plans, while the compiled specification stays small even when actions have high arity and there are many objects?

The constraint families are `always(phi)`, `sometime(phi)`, `at_most_once(phi)`, `sometime_before(phi, psi)` and `sometime_after(phi, psi)` (PDDL3 semantics over the whole state trajectory, initial state included); `phi` and `psi` may contain quantifiers. A solution is a compiler: constrained task in, constraint-free task out, consumable by an ordinary planner that knows nothing about trajectory constraints.

## Why It Matters

Many planners do not support trajectory constraints. Compiling them away lets standard planners handle safety requirements, intermediate goals and ordering requirements. If the compiler must first ground the task, high-arity actions over many objects make the compiled task explode (millions of ground actions), so a useful compiler must work on the lifted representation.

## Success Criteria

* **Exactness (hard constraint):** every plan valid for the constrained task is valid for the compiled task and vice versa. A compiler that accepts a violating plan, rejects a valid one, fails, or produces a malformed task fails the benchmark outright.
* **Succinctness:** among exact compilers, fewer conditional effects and actions, and smaller (total and largest) precondition/effect-condition formulas, are better, including on tasks with many constraints.
