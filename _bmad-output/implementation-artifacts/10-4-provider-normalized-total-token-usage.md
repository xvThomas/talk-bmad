# Story 10.4: Provider-normalized total token usage

Status: backlog

## Story

As a chat user,
I want each completed turn to expose a provider-normalized total token count,
so that session consumption can be accumulated consistently across OpenAI-compatible and Anthropic models.

## Acceptance Criteria

1. **Normalized per-call total**
   - Each LLM client returns a confirmed `total_tokens` value as part of `domain.Usage` for every successful provider response.
   - The value represents the total token volume processed for that call using provider-specific accounting; it is not a cost estimate.

2. **OpenAI-compatible normalization**
   - `total_tokens = input_tokens + output_tokens`.
   - Cached input tokens remain a subset of `input_tokens` and reasoning tokens remain a subset of `output_tokens`; neither is added again.
   - When the provider supplies a reliable native total, tests verify it agrees with the normalized convention or document the chosen precedence.

3. **Anthropic normalization**
   - `total_tokens = input_tokens + cache_read_tokens + cache_write_tokens + output_tokens`.
   - Cache-read and cache-creation inputs are counted because Anthropic reports them separately from uncached `input_tokens`.
   - Thinking tokens are already included in `output_tokens` and are not added again.

4. **Turn aggregation and stream contract**
   - `Usage.Add` sums `TotalTokens` across all LLM calls in the turn.
   - `token_usage` and `turn_usage` expose `total_tokens` when confirmed.
   - `turn_usage.total_tokens` is the authoritative normalized total for the complete or interrupted turn.
   - Existing input, output, cache, reasoning, ratio, interrupt, and error fields remain backward compatible.

5. **Defensive behavior**
   - Totals use only finite, non-negative provider counts and do not infer missing categories.
   - Overflow and malformed usage are handled consistently with existing domain conventions.
   - No additional provider request or persistence is introduced.

6. **Tests**
   - Tests cover OpenAI usage with cache and reasoning without double counting.
   - Tests cover Anthropic uncached, cache-read, cache-write, and mixed usage.
   - Tests cover multi-call turn aggregation and normal/interrupted `turn_usage` emission.

## Tasks / Subtasks

- [ ] Extend `domain.Usage`, `TokenUsagePayload`, and `TurnUsagePayload` with `TotalTokens` / `total_tokens`.
- [ ] Calculate normalized totals in the OpenAI-compatible converter/client boundary.
- [ ] Calculate normalized totals in the Anthropic converter/client boundary.
- [ ] Preserve the normalized value through `Usage.Add`, message events, turn aggregation, observability, and AG-UI emission.
- [ ] Add provider, domain, conversation, and emitter tests.
- [ ] Run targeted and full backend validation.

## Dev Notes

- OpenAI `PromptTokensDetails.CachedTokens` is a subset of `PromptTokens`; `CompletionTokensDetails.ReasoningTokens` is a subset of `CompletionTokens`.
- Anthropic `InputTokens`, `CacheReadInputTokens`, and `CacheCreationInputTokens` are separate usage categories in the current SDK response.
- `total_tokens` is a normalized volume counter, not currency, cost, context occupancy, or a replacement for detailed fields.
- Keep provider-specific normalization at the LLM client/converter boundary; downstream domain and AG-UI code must remain provider-neutral.

## Dev Agent Record

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2026-09-16: Story created from approved Story 10.3 course correction.
