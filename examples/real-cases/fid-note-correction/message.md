This is an English translation added for readers. The delivered message was
in Chinese. It preserves the message metadata and body, omitting only the
final sentence linking to a private daily report, as noted in the
[Chinese public copy](message.zh-CN.md).

[Case](README.md) | [中文原文](message.zh-CN.md)

---

# One simplification in the FID card needs an extra condition

- Message ID: MSG-20261025T100915+0800-PRISM-fid
- Thread: MSG-20261025T100915+0800-PRISM-fid
- Sender: PRISM
- Current owner: YZH
- Type: Actionable correction reminder
- Related: yzh-srs:((q54a4a)), the FID card in ml.md

## PRISM · 2026-10-25 10:09

The covariance term `‖√Σ−√Σ′‖²_F` added to the card yesterday is not generally
equal to the original expression. It needs an additional condition, such as
commuting covariance matrices. Before following up, I checked the current
card read-only and confirmed that the condition was still missing.

A positive definite counterexample:

- `A=diag(1,4)`, `B=[[2.5,−1.5],[−1.5,2.5]]`.
- `√A=diag(1,2)`, `√B=[[1.5,−0.5],[−0.5,1.5]]`.
- The squared Frobenius norm of the difference of square roots is `1`.
- The original covariance term is
  `tr(A+B−2√(√A B √A))=10−2√20.5≈0.944615`.

The values differ, so the added line cannot stand as a general equality.
This conclusion has been checked by independent algebraic and numerical
calculations. Confidence is high.

Minimal next step: remove the added general equality, or label the line as
a special case for commuting covariance matrices. The benefit is avoiding
repeatedly memorizing a relationship with an overstated scope. The cost is
a one-line revision. This concerns only that simplification, without
rewriting the scope of the whole card. No external card was changed in this run.

When extending scalar relationships to matrices in the future, try a
two-dimensional positive definite example that breaks commutativity, rather
than testing only two diagonal matrices. Numerical agreement still cannot
replace a proof.
