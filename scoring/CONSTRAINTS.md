# Scientist Constraints

## Problem Representation

A method is a compiler registered in `outputs/compilers/<name>.json`; it receives one constrained task (JSON) per call and must return a constraint-free task in the same format. It must work for any task in the format: no hard-coding of instances, seeds or generator internals.

## Evaluation

Use `scripts/evaluate_train.sh` / `scripts/evaluate.sh` for development. Do not read, import or modify anything under `eval/test/`, and do not have the compiler read evaluator files at run time. Do not edit `eval/` or the scoring files to change how compiled tasks are checked or measured.

## Exactness

The compiled task must accept exactly the plans the constrained task accepts (original action names and arities, optional parameterless auxiliary actions). Shrinking a compiled task by dropping monitoring that is only "rarely" needed, or by testing removals against sampled trajectories, is not an improvement: it must be exact for every plan, not only for the plans the evaluator happens to replay.

## Resources

Per task: 30 s, 4 GB, 32 MB of output. Compilers must not ground the task's high-arity actions over all objects.

## Compliance Checklist

- [ ] Registers a compiler command; does not write score files itself
- [ ] Keeps the original action names and parameter counts
- [ ] Exact on every constraint family, ground and quantified, including formulas true in the initial state
- [ ] Never touches `eval/test/`
