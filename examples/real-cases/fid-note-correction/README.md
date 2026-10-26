# A daily review caught an error in a study card

English | [简体中文](README.zh-CN.md)

This happened during the author's actual use of My Big Brother.
The edit and reminder are preserved below. No machine-learning or matrix
background is needed to follow the sequence.

## What happened

1. **Evening of October 24, 2026:** while reviewing a study card in `ml.md`,
   the author added a seemingly equivalent expression to an existing formula.
   The editor recording preserved this one-line addition in the
   [recorded diff](note-edit.diff).
2. **Daily review starting at 10:00 on October 25:** the Agent noticed the
   edit in the Vim records, suspected a missing condition, and tested a small
   matrix counterexample. The two expressions produced different answers.
3. **Reminder dated 10:09 on October 25:** after publishing the reports, the
   Agent followed the configured personal task and delivered a correction to
   the author's local Markdown inbox. It explained the issue, its verification
   and a minimal fix. It left the study card itself unchanged.
4. **Follow-up on October 26:** the author asked in the same Codex session
   whether the original formula was also wrong. The Agent checked the
   original authors' implementation and confirmed its order of operations.
   The problem was the equality added later. The card later included the missing condition.

The author's reaction: without the reminder, he might not have noticed the
mistake. Because this card is reviewed repeatedly, catching it mattered more
than merely recording that a note had been edited. This is one successful
finding, rather than a promise that every review will uncover an error.

## Supporting material

- [Public copy of the original Chinese reminder](message.zh-CN.md). Its body
  is preserved, with an explicitly noted omission of the final private report link.
- [English translation of the reminder](message.md), added for readers.
  The delivered message was in Chinese.
- [Recorded edit](note-edit.diff). Only the two machine-specific file headers
  were replaced with `a/ml.md` and `b/ml.md`. The original hunk is preserved.
  The added line is the expression missing its condition.

By the October 26 check, the card contained this corrected note:

```text
* 注 3. 像 ‖√Σ - √Σ'‖²_F 但不等（需 Σ,Σ' 可交换）
```

Translation: “Note 3. It resembles ‖√Σ − √Σ′‖²_F, but is not equal in
general (Σ and Σ′ must commute).”

The small historical diff fixes the state at the time of the mistake and
shows exactly which line prompted the reminder. It remains useful even if
the complete study notes change later.

## For readers interested in the math

The card concerns FID, a metric comparing two distributions of image features.
The original formula involves multiplying matrices and then taking a matrix
square root. The added expression effectively takes square roots separately
before combining them. These operations are not generally interchangeable.
The [original authors' implementation](https://github.com/bioinf-jku/TTUR/blob/master/fid.py#L133)
calls the matrix-square-root function `sqrtm` on `sigma1.dot(sigma2)`.

The reminder's counterexample gives `1` for the new expression and about
`0.944615` for the original covariance term. They cannot be a general identity.
For commuting covariance matrices, the square-root-difference form does hold.
These details support the correction, but are not needed to understand the case.

## This run and the public capability

This run used the author's personal profile to select worthwhile reminders
and write them to a local inbox. “Delivery” here means creating a readable
Markdown message file. It did not send email, push a chat message or display
a desktop alert.

The public project now ships reminder rules and a local delivery helper,
enabled by default for new installations. Users can disable reminders or
choose their inbox, without writing a private task. Existing configurations
retain their prior behavior. The same review Agent handles reminders after
publication, before any private post-review work. See
[Local reminders](../../../docs/NOTIFICATIONS.md).
Reproducing the author's private directory layout or full workflow is unnecessary.
