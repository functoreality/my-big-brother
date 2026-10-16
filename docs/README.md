# Documentation map

English | [简体中文](zh-CN/README.md)

My Big Brother reviews selected local activity with one executing Agent,
publishes daily records and optional cumulative knowledge, and keeps disposable
work in dated raw-log directories. This map separates what the product promises,
how it works, and how those agreements change.

## Three core documents

| Document | Summary | When to read |
| --- | --- | --- |
| [PRD](REQUIREMENTS.md) | User control, inputs/outputs, one-day unattended review, manual reruns, retention, personalization and current limits | Understand or propose product behavior |
| [Technical overview](ARCHITECTURE.md) | Collector/reader/task/startup boundaries, path/time model, staged publication, locks, conflicts and recovery | Understand or propose the means of delivering that behavior |
| [Document-first development](../CONTRIBUTING.md) | Distinguish existing-contract implementation from new proposals, obtain agreement, update documents, then implement and verify | Before any implementation assignment or review-driven change |

The PRD and technical overview must be readable without opening every detail
link. They retain the system-wide summary. Detail documents specify precise
formats and protocols within that scope, not separate product policies.

## Technical details and execution contracts

| Topic | Summary and owner |
| --- | --- |
| [Storage](STORAGE.md) | Platform discovery, one-path TXT, permanent outputs, dated status/journals and the fixed-size publication lock |
| [Input sources](INPUT-SOURCES.md) | Native/collected formats, cross-date retrieval, metadata, coverage gaps and screenshot assets |
| [Bash](BASH.md), [Vim](VIM.md) | Recorder installation, fixed start-date sessions, exact capture semantics and known limitations |
| [Profiles](PROFILES.md) | Explicit personal references, output binding/schema, validators, read authorization and scoped follow-up |
| [Scheduling](SCHEDULING.md) | Native or OS triggers, startup environment, single-Agent execution and manual dated reruns |
| [Daily task](../tasks/daily-review/TASK.md) | Agent execution entry, evidence boundaries and interpretation principles |
| [Automation](../tasks/daily-review/AUTOMATION.md), [workflow](../tasks/daily-review/WORKFLOW.md) | Command/receipt sequence and complete evidence reading with one shared task interpretation |
| [Output task](../tasks/daily-review/OUTPUTS.md), [knowledge task](../tasks/daily-review/KNOWLEDGE.md) | Standard report schemas, content and cumulative knowledge merge rules |
| [Knowledge guide](KNOWLEDGE.md) | How users enable, locate and reuse the standard knowledge outputs |
| [Extending](EXTENDING.md) | Existing adapter, task, output and launcher interfaces, used after the change is agreed |

## Installation and operation

[Agent installation](../INSTALLATION.md) is the installer's executable guide.
[Setup](SETUP.md) explains manual configuration and the first review.
[Cleanup](CLEANUP.md) explains the user's direct deletion of inactive date
folders, with formal outputs preserved. [Synthetic examples](../examples/synthetic/README.md)
illustrate outcomes, not real evidence or another source of requirements.
The [README](../README.md) introduces capabilities and proposed directions.

## Authority and change status

- User/maintainer decisions define scope. Capture new decisions in the owner
  documents before dependent implementation.
- Current PRD and technical contracts guide implementation. Code, tests and
  execution instructions should conform to them, not silently change them.
- A proposal is not current until explicitly accepted and integrated into
  the owner documents. Roadmap items are not approval.
- Audits and experiments record evidence. Historical designs are not current
  contracts, even if they once contained an approval label.

When a claim conflicts with another document, identify the discrepancy rather
than picking the nearest file or treating code as the product decision.
Use the [change process](../CONTRIBUTING.md). Human translations retain the same
scope and IDs. English task instructions, command names and JSON schemas are
shared. This public map contains no personal deployment or migration authority.
