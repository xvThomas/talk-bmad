# Story 10.6: Anthropic reasoning token breakdown

Status: backlog

## Story

As an operator and chat user,
I want Anthropic thinking-token usage exposed as optional reasoning tokens,
so that detailed usage reporting is as complete as the provider contract permits.

## Acceptance Criteria

1. **Provider capability investigation**
   - Verify against the pinned Anthropic API and `anthropic-sdk-go` version whether a structured thinking-token count is available.
   - Record whether the count is exposed directly, only in raw JSON, only for specific models/modes, or not available.

2. **Reasoning-token capture**
   - When Anthropic returns a confirmed thinking-token breakdown, the client maps it to `domain.Usage.ReasoningTokens`.
   - The value remains optional and zero/omitted when the provider does not supply it.
   - No reasoning count is estimated from thinking text, token budgets, latency, or output length.

3. **Accounting semantics**
   - Anthropic reasoning tokens remain a breakdown of `output_tokens`; they are not added again to normalized `total_tokens`.
   - Existing input, output, cache, normalized total, and context-ratio values remain unchanged.

4. **Compatibility path**
   - Prefer a supported SDK field when available.
   - If an SDK upgrade is required, assess compatibility and obtain dependency-change approval before implementation.
   - Raw JSON parsing is acceptable only when narrowly scoped, tested, and necessary to access a documented stable field.

5. **Propagation**
   - Confirmed Anthropic reasoning tokens propagate through per-call usage, turn aggregation, console/observability reporting, `token_usage`, and `turn_usage`.
   - Clients that ignore the optional field remain compatible.

6. **Tests**
   - Tests cover present, absent, zero, malformed/unavailable, and multi-call aggregation cases.
   - Existing Anthropic thinking-content handling and all provider tests remain green.

## Tasks / Subtasks

- [ ] Verify Anthropic API and pinned SDK support for thinking-token details.
- [ ] Choose and document the supported extraction path.
- [ ] Implement optional Anthropic `ReasoningTokens` mapping without changing total accounting.
- [ ] Add converter/client, aggregation, and AG-UI payload tests.
- [ ] Update observability documentation as needed.
- [ ] Run targeted and full backend validation.

## Dev Notes

- Current `anthropic-sdk-go v1.27.1` `Usage` exposes input, output, cache-read, and cache-creation counts but no typed thinking-token breakdown in the inspected response model.
- Thinking content is already captured in `Message.Thinking`; content presence is not a safe token-count source.
- This story may require explicit dependency approval if the only robust path is an SDK upgrade.

## Dev Agent Record

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2026-09-16: Story created from approved Story 10.3 course correction and reasoning-token investigation.
