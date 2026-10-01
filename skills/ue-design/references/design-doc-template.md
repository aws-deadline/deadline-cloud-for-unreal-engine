# Design Document Template

> **When to use:** This template is intended for major features, architectural changes, or cross-team integrations. For smaller changes, a brief description in the PR is sufficient — avoid creating design docs that add maintenance burden without proportional value.

Generate `docs/designs/<feature-name>.md` using this structure. Write each section to disk as it's approved.

**Design flow:** Work through Parts 1-3 with the human in the loop. After the design is complete, generate the Executive Summary at the top.

---

# Feature Name

Status: Draft | In Review | Accepted | Implemented

## Executive Summary

_Generated last, after the design is complete._

One paragraph summary of the problem, proposed solution, testing plan, and work estimate. This is the TL;DR for reviewers.

---

# PART 1 — UNDERSTAND THE PROBLEM

## 1. Problem Description

### 1.1 Problem

Brief (one paragraph, max 200 words) summary of the problem in terms of customer impact. State the stakeholders.

### 1.2 Background

Context for new readers. Current state of the system, scope of the problem, relation to other components. Include a diagram if necessary. Max 300 words — move detail to appendices.

### 1.3 References

Link to supplemental documents (max 5 links): prior designs, tickets, external docs.

## 2. Solution Requirements

### 2.1 User Stories

User stories or link to PRD. If no natural home elsewhere, place them here.

### 2.2 Technical Requirements

Numbered list of requirements. Focus on _what_ is required, not _how_. Use RFC 2119 keywords with component as subject:
- WHEN [condition], THE [component] SHALL [behavior]
- IF [condition], THEN THE [component] SHALL [behavior]

## 3. Out of Scope

Explicitly call out what is NOT in scope.

## 4. Assumptions

What must be true for the solution to succeed?

## 5. Open Questions and Risks

Numbered list of unknowns, risks, and one-way doors.

---

# PART 2 — DESIGN THE SOLUTION

## 6. Glossary

Define new terms used in this document.

## 7. Solution

### 7.1 System Architecture Diagram

High-level Mermaid diagram showing component relationships and data flow.

### 7.2 Components

For each modified component:
- What changes
- New types/interfaces (complete definitions)
- Modified functions/methods
- Code snippets (inline: show only what changes with `...` for existing code)

### 7.3 Dependencies

Upstream and downstream dependencies. For each: what happens when it fails?

### 7.4 Sequence Diagrams

Mermaid sequence diagrams for key interaction flows.

### 7.5 Data Models

Complete definitions of new or modified data structures.

### 7.6 Backwards Compatibility

- Is this a breaking change?
- Impact on existing users, templates, or workflows
- Migration path if breaking

### 7.7 Additional Considerations

- How will the solution scale?
- How will it handle failure and recovery?
- How might it evolve for future requirements?

## 8. Solutions Considered and Discarded

Alternatives considered, why they were discarded. Be brief.

## 9. Security Considerations

### 9.1 Threat Model

New threats from this design. Input validation, sensitive data, attack vectors, mitigations.

### 9.2 Data Inventory

Any new data being stored or transmitted.

## 10. Work Required

### 10.1 Effort Estimates

High-level breakdown with t-shirt sizes. Call out cross-team dependencies.

### 10.2 Proposed Milestones

Deliver incrementally. What can be done first to unlock parallel work?

#### Milestone M1: [Name]

**Acceptance criteria:** How we determine this milestone is complete.

1. First item to develop
2. ...

---

# PART 3 — IMPLEMENTATION PLAN (Agent-executable)

_This section is the detailed implementation guide. Each task should be self-contained enough for an AI agent to implement independently. Mark which tasks can run in parallel._

## Testing Plan

### Unit Tests by Component

| Test | Type | Validates |
|------|------|-----------|
| `test_name` | Unit | Req N |

### Integration / E2E Tests

| Test | Type | Validates |
|------|------|-----------|
| `test_name` | E2E | Req N |

## Correctness Properties

Formal properties bridging requirements to testable invariants.

### Property N: Title
_For any_ [universal quantifier], [property statement].

**Validates: Requirements N, M**

## Error Handling

| Scenario | Behavior |
|----------|----------|
| [error condition] | [expected handling] |

## Tasks

Numbered task list. Each task references requirements for traceability.

```
* N. Task title (ComponentName)
  * N.1 Sub-task description
    * Detail of what to do
    * _Requirements: N_
  * N.2 Write unit tests
    * Test case descriptions
    * _Requirements: N_
* N+1. Checkpoint - Ensure [component] builds and tests pass
```

Rules:
- Group tasks by component
- Mark which tasks can run in parallel (⚡) vs sequential
- Include unit tests as sub-tasks within each task group
- Add checkpoints after logical groupings
- Reference build commands from AGENTS.md

## Notes

- Key assumptions
- Risks and mitigations
