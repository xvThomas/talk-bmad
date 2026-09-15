# Backend Addendum: Token Limit Observability

## Effective Limit Rule

Let $P$ be `ProviderMaxOutputTokens` and $R$ be `RequestMaxOutputTokens`.

$$
E =
\begin{cases}
\min(R, P) & \text{if } P > 0 \\
R & \text{if } P = 0 \text{ and } R > 0 \\
0 & \text{otherwise}
\end{cases}
$$

An effective limit of $0$ means that no provider output-limit parameter is sent.

## Observability Ratios

For a completed LLM API response with confirmed usage $I$ input tokens and $O$ output tokens:

$$
\text{contextRatio} = \frac{I}{\text{ContextWindowTokens}}
$$

$$
\text{outputRatio} = \frac{O}{\text{ProviderMaxOutputTokens}}
$$

Each ratio is omitted when its denominator is absent or zero. The backend does not add a safety margin in this observability-only scope.

## Suggested Event Payload

Use an AG-UI `CUSTOM` event with name `token_usage`. Its value contains the model alias, confirmed input and output tokens, optional configured limits, and optional ratios. The event is emitted after each completed provider response, including each response in a tool loop.

## Turn-Level Reconciliation Event (`turn_usage`)

The per-call `token_usage` events power the frontend's "last completed call" indicator. They are NOT to be summed client-side into the session cumulative (missed/duplicated events, tool-loop grouping, stream-interruption drift).

Instead, emit a second AG-UI `CUSTOM` event with name `turn_usage` at the end of every turn. Its value is `TurnEvent.TotalUsage`, the authoritative sum accumulated server-side across all LLM calls of the turn. This is the single reconciliation source for the frontend's session-scoped cumulative usage indicator.

Payload (same omission rules as `token_usage`; no ratios — ratios only make sense per call):

```json
{
  "model": "sonnet-4.6",
  "input_tokens": 41230,
  "output_tokens": 1352,
  "cache_read_tokens": 10000,
  "cache_write_tokens": 0,
  "reasoning_tokens": 200
}
```

Design constraints: stream-only, zero persistence, no new HTTP endpoint. A missed `turn_usage` on a dropped stream is self-healing — the cumulative is per-session ("current consumption"), reset on conversation load and page reload. This is a deliberate UX decision.

## Model Metadata Sources

Provider limits should be sourced from official model documentation or provider model-discovery APIs, then maintained as local configuration. They are not inferred from `RequestMaxOutputTokens`.
