---
name: ue-design
description: AI-guided design for Unreal Engine features and major changes in Deadline Cloud integration. Use when designing new features, planning major refactors, creating design docs, or making architectural decisions for deadline-cloud-for-unreal-engine. Triggers on requests like "design a feature", "write a design doc", "plan a major change", or "architect a solution".
tags: [skill, deadline-cloud, deadline-cloud-for-unreal-engine, deadline-cloud-for-ue, design, architecture, feature-design]
---

# UE Design

## Overview

AI-guided interactive design process for Unreal Engine features in Deadline Cloud. The agent drives the conversation — researching, proposing options, and prompting the user for decisions at each step. Progress is saved to disk after each section.

## Usage

Use this skill when:
- Designing a new **major** feature for the UE integration
- Planning a major refactor or architectural change
- Creating or refining a design document in `docs/designs/`

Do **not** use this skill for small bug fixes, minor enhancements, or changes that can be adequately described in a PR description.

## Core Concepts

### Agent Role

You are the design driver. The user provides goals and makes decisions. You do everything else:
- **Research** the codebase, `references/references.md`, and `AGENTS.md`
- **Draft** each section with concrete proposals
- **Present** options with pros/cons for every design decision
- **Prompt** the user to choose, confirm, or redirect
- **Challenge** your own proposals — surface weaknesses and edge cases before the user asks
- **Iterate** based on user feedback before moving to the next section

You **MUST NOT** dump an entire design doc at once. Work through it section by section, getting user sign-off on each before proceeding.

### Saving Progress

You **MUST** write the design doc to `docs/designs/<feature-name>.md` incrementally — after each section is approved, write it to disk. This ensures:
- Work survives context window limits
- A new session can resume by reading the file
- The user can review progress at any time

On session start, always check `docs/designs/` for an existing draft to resume.

### Design Flow

The template (`references/design-doc-template.md`) has 4 parts. Work through Parts 1-3 with the human, then generate the summary and implementation plan.

#### Step 1: Kickoff

Prompt the user:
```
What would you like to do?
1. Start a new design
2. Refine an existing design (from docs/designs/)
```

**If new design:** Ask the user to describe the feature and any known constraints/specs.

**If refining:** Read the existing doc, ask what needs to change.

#### Step 2: Research

Before drafting anything, you **MUST**:
1. Read `AGENTS.md` for architecture and component boundaries
2. Search the codebase for existing patterns related to the feature
3. Read any linked docs, tickets, or prior art the user mentions

Summarize findings to the user. Ask if anything is missing.

#### Step 3: Part 1 — Understand the Problem

Work through: Problem Description, Background, Requirements, Out of Scope, Assumptions, Open Questions. Draft each, present to user, iterate, write to disk.

#### Step 4: Part 2 — Design the Solution

Work through: Glossary, Solution (architecture, components, dependencies, sequence diagrams, data models, backwards compatibility), Solutions Discarded, Security. For each design decision:
1. Research options — read code, check APIs, look at existing patterns
2. Present 2-3 options with pros/cons, self-challenge weaknesses
3. Wait for user decision

Write each approved section to disk.

#### Step 5: Generate Executive Summary

After the design is complete, generate the Executive Summary at the top of the document. This summarizes: the problem, proposed solution, testing plan, and work estimate. Present to user for final approval.

#### Step 6: Part 4 — Implementation Plan

Generate the agent-executable implementation plan: testing plan, correctness properties, error handling, and numbered tasks. Tasks **MUST** be structured so independent tasks can be worked on concurrently by separate agents. Mark parallel tasks with ⚡.

### Prompting Patterns

At every decision point, you **MUST** end with a clear question.

You **MUST NOT**:
- Proceed to the next section without user confirmation
- Make design decisions without presenting options
- Skip research — always check the codebase first

## Quick Reference

| Resource | Location |
|----------|----------|
| Design doc template | `references/design-doc-template.md` |
| Output directory | `docs/designs/` |
| Architecture context | `AGENTS.md` |
