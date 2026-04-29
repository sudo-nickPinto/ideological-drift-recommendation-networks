---
name: project-status-check
description: 'Beginner-friendly project progress check. Use when you need a plain-English status update that compares the intended goal, starting point, planned steps, current step, blockers, completed work, and next actions using the repo as evidence.'
argument-hint: 'Project goal, where you started, planned steps, or current blocker'
user-invocable: true
---

# Project Status Check

## What This Skill Produces

This skill produces a plain-English project check-in that answers:

- Our goal is...
- We started from...
- We planned to get there by...
- We are currently at this step...
- We are stuck because...
- We need to do this next...

It is designed for beginner-friendly status updates, not deep architectural design or bug fixing.

## When To Use

Use this skill when you want to:

- explain where the project stands right now
- compare the intended plan with the current repository state
- identify the current step in a multi-step workflow
- name the blocker in simple language
- decide the next concrete action

## Repository Grounding Rules

In this repository, build the status update from these sources in this order:

1. `README.md` for project goal, workflow, and current status.
2. `docs/SYSTEM_DESIGN.md` for implemented architecture and pipeline order.
3. `data/README.md` for dataset assumptions when data questions matter.
4. `tests/` for what behavior is actually implemented and validated.
5. `src/` for final confirmation of code that exists today.

If these sources disagree, trust implemented code and tests first, then explain the mismatch plainly.

For this project, the normal pipeline order is:

1. `graph_builder.py`
2. `ideology.py`
3. `simulator.py`
4. `metrics.py`
5. `visualize.py`
6. `run.py` or `src/run_pipeline.py` when you need the full end-to-end flow

## Inputs To Collect

Ask for these if they are not already clear:

1. The intended goal
2. The starting point or original state
3. The planned steps or expected workflow
4. The current blocker, if one is already known

If some inputs are missing, infer them from the repository and clearly label them as assumptions.

## Procedure

1. Restate the goal in plain English.
2. Restate the starting point in plain English.
3. Reconstruct the intended path.
4. Check the repository for what is actually done.
5. Map current progress onto the planned steps.
6. Identify the current step.
7. Explain the blocker in simple terms.
8. Give the next concrete action.

## How To Reconstruct The Intended Path

- Prefer the user's own plan if they gave one.
- Otherwise, infer the plan from `README.md` and `docs/SYSTEM_DESIGN.md`.
- Keep the step list ordered and short.
- If the project has both a module pipeline and a workflow pipeline, explain which one you are using.

## How To Identify The Current Step

- Mark each step as `done`, `in progress`, `blocked`, or `not started`.
- Choose the current step as the first required step that is not clearly complete.
- If the code is complete but outputs are missing, treat the work as implemented but not yet demonstrated.
- If tests exist and pass for a stage, count that as strong evidence that the stage is implemented.

## Beginner-Friendly Language Rules

- Prefer plain English before technical jargon.
- If you must use a technical term, define it in one short sentence.
- Separate confirmed facts from assumptions.
- Do not bury the answer in a long repo tour.
- End with one immediate next step and one optional follow-up step.

## Output Format

Use this exact structure unless the user asks for a shorter answer.

### Goal

Our goal is:

### Starting Point

We started from:

### Planned Path

We expected to move through these steps:

1. ...
2. ...
3. ...

### Current Step

Right now, we are at step:

Because:

### What Is Already Done

- ...

### What Is Blocking Us

- ...

### What We Need To Do Next

1. ...
2. ...

### Evidence Checked

- `README.md`
- `docs/SYSTEM_DESIGN.md`
- relevant files from `tests/`
- relevant files from `src/`

## Completion Checks

Before finishing, make sure the status update:

- states the goal in one sentence
- states the starting point or labels it as inferred
- shows the planned steps in order
- names exactly one current step
- explains the blocker in plain language
- gives at least one concrete next action
- mentions what evidence was checked

## Example Prompts

- `/project-status-check Our goal is to finish the recommendation-network analysis and produce presentation-ready findings. We started from raw CSV files and a scaffolded Python repo.`
- `/project-status-check Help me explain where we are on the pipeline, what is done, and what is still blocking us.`
- `/project-status-check Compare our intended plan with the current repo and tell me the next step in beginner-friendly language.`