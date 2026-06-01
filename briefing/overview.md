# Overview

- **Paper ID:** 2511.10164
- **Title:** Two Constraint Compilation Methods for Lifted Planning
- **Domain:** Automated Planning
- **TL;DR:** The paper compiles qualitative PDDL trajectory constraints away in lifted form, avoiding the grounding blow-up of prior TCORE-style compilation.

## Short Summary

The paper studies planning tasks with safety, ordering, and intermediate-goal trajectory constraints. It proposes LiftedTCORE, which uses lifted regression, and LCC, which uses shared monitoring logic with a final checking action. The reported experiments show that the lifted compilers preserve constraint semantics and produce compiled tasks with orders-of-magnitude fewer actions and effects than ground-first compilation.

## Key Results

- On the paper's main benchmark, LCC solved 246/280 tasks and LiftedTCORE solved 238/280, comparable to ground TCORE at 245/280.
- Average compiled actions/effects were about 7-8 actions and 58-67 effects for lifted methods, versus about 21K actions and 95K-96K effects for ground TCORE.
- Average compilation time was milliseconds for the lifted compilers, versus several seconds for ground TCORE.
