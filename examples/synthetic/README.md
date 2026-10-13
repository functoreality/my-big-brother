# Synthetic daily review

These English files were produced by a real Codex review of invented work
records during the Linux smoke test. They are examples, not someone's actual
work history. The fictional review date is 2020-01-15.

The input describes a CSV importer fix, an installation-guide update, and a
release-checklist draft. All times in this saved example use UTC+08:00, the
validation machine's local offset. Other installations use their local time.
The saved run used UTC source timestamps. The current harness anchors events
to the local clock so they stay within one review day across time zones.
Clock times in a fresh run can therefore differ from this saved example.

- [Worklog](worklog.md): work, reported outcomes, and pending publication.
- [Time Use](time-use.md) and [canonical JSON](time-use.json): chronological
  activity with uncertainty and overlapping evidence.
- [Daily Insights](insights.md): grounded, conditional suggestions.
- [Duration samples](time-estimates.json): elapsed spans with unknown human
  effort left null.

Reproduce a fresh preparation with `python3 tests/smoke.py` from the repository.
Add `--run-analyzer` to request a new model-generated review using the installed
Codex account. The result can differ in wording and organization.
