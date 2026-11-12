# Overview

- **Paper ID:** 2511.10164
- **Title:** Two Constraint Compilation Methods for Lifted Planning
- **Domain:** Automated Planning
- **TL;DR:** The paper compiles qualitative PDDL trajectory constraints away in lifted form, avoiding the grounding blow-up of prior TCORE-style compilation.

## Short Summary

The paper studies planning tasks with safety, ordering, and intermediate-goal trajectory constraints. It proposes two compilers that remove the constraints without grounding the task, proves that they preserve exactly the valid plans, and shows that the compiled tasks are orders of magnitude more succinct than those of a ground-first compiler while remaining competitive for a standard planner.

## Key Results (paper)

- On the paper's main benchmark (280 IPC-2023 tasks), LCC solved 246/280 tasks and LiftedTCORE 238/280, comparable to ground TCORE at 245/280.
- Average compiled actions/effects were about 7-8 actions and 58-67 effects for the lifted methods, versus about 21K actions and 95K-96K effects for ground TCORE.
- The paper names its own limitation: with many constraints, lifted compilers add monitoring to every action that may affect each constraint.

## This gym

Generated lifted tasks with high-arity actions over 20-32 objects (full grounding: 10^6-10^8 actions), ground and quantified constraints of all five families, a many-constraints regime, and small tasks checked exhaustively. A method is a compiler command; the evaluator runs it on hidden tasks, verifies exact plan preservation and measures compiled size (see `briefing/evaluation.md`).
