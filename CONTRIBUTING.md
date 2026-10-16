# Document-first development

English | [简体中文](docs/zh-CN/CONTRIBUTING.md)

Before changing implementation, establish the agreed product and technical
contract. A suggestion, a successful experiment or existing code is not
approval to change that contract. This applies to contributors, coordinating
Agents and their subagents, including task prompts and installer instructions.

Start with the [documentation map](docs/README.md),
[PRD](docs/REQUIREMENTS.md) and [technical overview](docs/ARCHITECTURE.md).
The overview must summarize current behavior and choices. Links carry detail,
not the information needed to understand the whole system.

## 1. Classify the work before editing implementation

| Kind of work | What may happen first | Implementation permission |
| --- | --- | --- |
| Documentation correction with no meaning change | Fix wording, translation or navigation | Does not itself authorize code changes |
| Implementation of an already agreed contract | Identify the exact PRD/technical/detail sections and the authorized task | Implement those sections, preserving other behavior |
| New behavior, a changed technical strategy or unclear coverage | Discuss the issue and prepare a concrete documentation proposal | Wait for explicit agreement before implementing the proposal |

A bug fix can restore an already documented invariant without inventing a new
requirement. Record the invariant and reproduction, then implement the fix.
A refactor can preserve an existing design. Neither label permits adding
fields, dependencies, retention, retries, locks, permissions or compatibility
branches outside the agreed contract. If those are needed, take the third route.

Implementation includes executable Markdown tasks, prompts, collector behavior,
validators, default settings and installation actions. Changing a task's meaning
can change runtime behavior even without editing Python.

## 2. Propose and review the document change

For a contract change, provide a short proposal or the exact proposed document
diff before changing implementation. Use `docs/proposals/<topic>.md` only when
a separate proposal helps. Do not create an empty hierarchy or a proposal for
every wording correction. A proposal should state:

- The user problem, scenario and present behavior.
- The proposed behavior and the exact PRD/technical/detail sections affected.
- What stays unchanged, including inputs, outputs, access and retention.
- Relevant alternatives, costs and failure cases.
- Acceptance examples and what remains undecided.

Label unagreed text **Proposed**. Keep it separate from current contracts.
An issue, README roadmap item, subagent recommendation, code diff, test result
or Git commit is not approval. Record the explicit user/maintainer decision and
its scope in the change discussion or task brief. Private conversation details
need not be copied into the public repository.

After agreement, update the current documents before implementation.
Update PRD for user-visible behavior, architecture for technical strategy,
and the relevant detailed contract for exact interfaces and edge cases.
Update the overview's summary as well as its links. A proposal containing the
only account of the new current behavior is insufficient.

If approval covers only part of a proposal, only that part becomes current.
Unresolved items remain proposed. If documents conflict or omit a material
choice, surface the conflict and ask rather than infer agreement from code.

## 3. Implement the agreed scope

In the task brief, name the agreed document sections, owned files/components,
acceptance examples and any pending decisions. Documentation work and isolated
investigation can continue while a new decision is pending. Do not implement
the dependent proposal or run a real installation to demonstrate it first.

For parallel work, give all Agents the same current contract and explicit file
ownership. A subagent reports proposals that exceed it. It cannot approve its
own suggestion, expand another Agent's assignment, or edit the runtime while
its proposal is still being reviewed.

Use the smallest implementation that satisfies the contract. Do not add
migration or compatibility for an unpublished abandoned layout. New collectors,
outputs or launchers follow [Extending](docs/EXTENDING.md), after their contract
is agreed. Keep personal files and development audits outside this public repo.

## 4. Verify and hand off

Run checks appropriate to the changed behavior using isolated evidence and
temporary destinations. Verify the affected examples and preserved invariants,
not just the new happy path. Tests must verify agreed behavior, not redefine it.
For a substantial change, use an independent review or fresh-context reader
check. Assess findings against the contract. New proposals return to step 2.
Repeat review when the fixes materially affect other contracts. Small corrections
that clearly restore the agreed behavior do not require an endless review loop.

Report the document basis, changed behavior, checks and meaningful limits.
Distinguish unit/fixture checks, real Agent interpretation, native platforms
and actual scheduler triggers. Git commits should form reviewable units.
When practical, commit the agreed document update before implementation.
A commit sequence does not replace the agreement requirement.

## Document roles and ownership

- **Current:** PRD, architecture and domain contracts describe the agreed scope.
  Update the document that owns a fact, rather than copying a second full spec.
- **Proposed:** alternatives and unresolved decisions cannot drive implementation.
  Once accepted, summarize the outcome in the current owner documents.
- **Historical/evidence:** audits, development notes and past code describe what
  happened or was checked. They cannot override current requirements.

The PRD owns user outcomes and acceptance. Architecture owns the means and
tradeoffs. Detail documents own exact formats and protocols within that scope.
If a lower-level detail would change a higher-level contract, review that
change first. User instructions remain authoritative and must be reflected in
the relevant documents before dependent implementation.

English is the canonical shared contract. Keep Simplified Chinese human-facing
versions aligned, with matching requirement/section IDs. A translation conflict
is a documentation defect, not a new policy choice. Shared Agent task files,
JSON keys and commands keep one version. No private paths belong in the public
PRD or architecture.

## Development baseline

Keep the core standard-library only. Python 3.11+ is recommended.
Prefer Python 3.7-era syntax and standard-library APIs when doing so remains
simple. Do not introduce newer features merely for style or claim old-runtime
support without verification. Optional dependencies remain capability-specific.

Use synthetic, isolated tests. Do not modify actual histories, shell/editor
settings, schedules or personal outputs as a test side effect.

```sh
python -m unittest discover -s tests
```

For a change description, a short record is usually enough:

```text
Contract basis: PRD P…, architecture T…, detail section …
Decision: existing agreement / explicit approval reference / proposed only
Scope: concrete behavior changed and invariants preserved
Verification: relevant scenarios, results and unverified limits
```
