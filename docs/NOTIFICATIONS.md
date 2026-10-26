# Local proactive reminders

English | [简体中文](zh-CN/NOTIFICATIONS.md)

My Big Brother can leave a local Markdown message when a daily review finds
something worth bringing to your attention: a verified mistake, a consequential
omission, or a concrete question needing your decision. The public task supplies
the selection rules and delivery helper. You do not need to write a private task.

New installations enable this by default. Messages go to `results_root/inbox/`.
Run `python -m my_big_brother paths` to see the resolved `notifications` settings.
Your installing Agent should tell you this location. Open that directory to
read messages, or let your own workflow monitor it. This feature creates files,
without email, chat push or desktop popups. It does not repair the original work.

## Choose the destination or turn reminders off

Edit the `notifications` entry in your existing `config.json`:

```json
"notifications": {
  "enabled": true,
  "inbox": null
}
```

`null` uses `results_root/inbox/`. To choose another directory, set `inbox`
to an absolute path outside disposable raw-log storage. To disable reminders,
set `enabled` to `false`. No personal profile or validator is required.
The directory must be writable by the executing Agent. The bundled Codex
launcher includes this selected directory in its write scope. Other launchers
must grant it explicitly without granting an unnecessarily broad parent.

Existing configurations without a `notifications` field keep reminders off.
An upgrade does not silently enable them or duplicate a private notification
task. To opt in, add the entry above. If a personal `post_review` already sends
similar reminders, decide which task should handle them before enabling both.
The public reminder stage runs before any separately configured private task.

## What merits a message

The Agent checks the evidence and sends only when the likely benefit exceeds
the interruption cost. Each message explains the issue, trigger evidence,
likely benefit, confidence and limits, and a minimal next step. It uses the
report language and identifies stable reports or user objects.
There is no daily quota. An empty message plan is a normal successful outcome.
An ordinary summary or every daily insight does not need a separate reminder.
An Agent may miss an error or misjudge a finding. Validation checks delivery
structure and content consistency, rather than proving semantic correctness.

The [real note-correction case](../examples/real-cases/fid-note-correction/README.md)
illustrates the value. That historical run used a personal notification task.

## Completion and retries

The same daily Agent handles reminders after report publication. `finish`
returns `actions-pending` and a prompt for `<review-run>/notifications/`.
The Agent reads the public [task](../tasks/notifications/TASK.md), checks
existing messages, stages Markdown drafts and `messages.json`, and invokes
the context's exact `delivery_command`. It writes the action receipt only
after successful delivery, then calls `finish` again. If a private task follows,
it completes that returned action in the same session and calls `finish` again.
Only `completed` means the whole review has finished.

Messages use `DATE--STABLE-ID.md`. The task checks relevant existing reminders,
including other dates, and does not repeat an unchanged issue. The helper
never overwrites a message. Identical content at the same path is already
delivered. Different existing content blocks delivery and preserves the file.
Keep human edits. Do not change an ID merely to bypass a conflict.

Failures keep reports published and the operation pending. Resume the same
run, inspect its plan and existing targets, and diagnose differences before
retrying. A partial write can leave an incomplete message. It requires manual
diagnosis rather than automatic replacement. Plans and receipts remain under
the disposable date. Messages remain in the permanent inbox. Deleting old
run material does not remove messages, and an explicit rerun must still check
the actual inbox for duplicates. There is no permanent delivery queue.
