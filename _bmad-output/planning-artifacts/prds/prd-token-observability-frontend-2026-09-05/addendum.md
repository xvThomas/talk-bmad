# Frontend Addendum: Token Limit Observability

## Display Model

The control bar presents two distinct values in this order:

1. a compact normalized `session` consumption total, when confirmed;
2. a compact horizontal `ctx` indicator for the final LLM call of the last completed turn.

The two values must not be conflated. Session total is cumulative processed volume; `ctx` is occupancy relative to the selected model's context window at one confirmed call.

The compact `out` ratio is intentionally removed. In a multi-call tool turn, the final call's output ratio is neither the turn total nor necessarily the largest call, so it is easily misread. Output counts remain available in the details view.

## Event Handling

`token_usage` remains a per-call event. The UI buffers the latest valid event during the active turn but does not publish it immediately. A valid `turn_usage` is the publication boundary: it promotes the buffered final-call snapshot to the displayed `ctx` state and independently reconciles cumulative category and normalized-total values.

The previous completed-turn `ctx` remains visible while the next turn runs. Complete and interrupted/iteration-limit turns behave identically. A turn without a valid buffered call does not replace prior display values with zero or estimates.

## Session Total

The frontend consumes backend-normalized `turn_usage.total_tokens` and sums it once per turn. It does not calculate a provider-specific total from input, output, cache, or reasoning fields. The compact session total is hidden until first confirmed and resets with the current conversation lifecycle.

The details view exposes normalized total and every confirmed cumulative category. Optional reasoning tokens remain omitted when unavailable, including Anthropic responses until the backend can obtain a documented breakdown.

## Status Thresholds

| Status   | Ratio                 |
| -------- | --------------------- |
| Normal   | $r < 0.70$            |
| Warning  | $0.70 \leq r < 0.85$ |
| Critical | $0.85 \leq r < 1.00$ |
| Blocked  | $r \geq 1.00$         |
