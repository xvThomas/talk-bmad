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

## Model Metadata Sources

Provider limits should be sourced from official model documentation or provider model-discovery APIs, then maintained as local configuration. They are not inferred from `RequestMaxOutputTokens`.
