# Frontend Addendum: Token Limit Observability

## Display Model

The primary control is a compact horizontal progress bar with exact text. It is better suited than a circular gauge for a dense model-control area because users can compare the numerator, denominator, and status at a glance.

The output ratio is secondary because it becomes meaningful only after a response completes. It should be displayed as a compact line and included in the detailed usage view, rather than animated as generation progresses.

## Event Handling

The UI stores the latest confirmed usage event per active conversation. The payload represents an individual completed LLM call, not the sum of all calls in a user turn. This preserves useful information when tool execution causes multiple model calls.

## Status Thresholds

| Status   | Ratio                |
| -------- | -------------------- |
| Normal   | $r < 0.70$           |
| Warning  | $0.70 \leq r < 0.85$ |
| Critical | $0.85 \leq r < 1.00$ |
| Blocked  | $r \geq 1.00$        |
