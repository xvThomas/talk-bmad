# Sprint Change Proposal ? Epic 10 Token Observability Revision

Date: 2026-09-16
Status: Approved
Approved by: Xavierthomas
Scope: Moderate ? revise Story 10.3 and add Stories 10.4?10.6

## 1. Issue Summary

UI review of Story 10.3 identified two semantic problems and one missing capability:

1. Publishing every per-call `token_usage` immediately makes `ctx` fluctuate during tool-loop turns, even though each value is individually correct.
2. A compact final-call `output_ratio` is easily misread because it is neither the largest call nor the authoritative total of a multi-call turn.
3. A cross-provider session consumption total cannot be reconstructed correctly in the frontend because OpenAI and Anthropic report cache categories differently.

A related investigation confirmed that OpenAI reasoning tokens are preserved as an optional output breakdown, while the current Anthropic SDK path preserves thinking content and aggregate output but not a numeric thinking-token breakdown.

## 2. Approved Product Behavior

### Stable context publication

- `token_usage` remains the source of per-call limits and ratios.
- The frontend buffers the latest valid `token_usage` during the active turn.
- A valid `turn_usage` promotes the pending final-call snapshot to displayed `ctx` and independently reconciles cumulative counts.
- Complete and interrupted/iteration-limit turns use the same boundary.
- The previous display remains stable while a turn runs and remains unchanged if no valid pending snapshot exists.

### Output presentation

- Remove compact `out` / `output_ratio` from the controls.
- Keep confirmed final-call output values in the accessible details panel.

### Reasoning tokens

- Keep `reasoning_tokens` optional.
- OpenAI reasoning remains a breakdown included in output totals.
- Anthropic reasoning remains omitted until a confirmed provider field can be captured; it is never estimated.

### Provider-normalized session total

- Calculate `total_tokens` in each backend LLM client/converter.
- OpenAI-compatible formula: `input_tokens + output_tokens`; cache-read and reasoning are subsets and are not added again.
- Anthropic formula: `input_tokens + cache_read_tokens + cache_write_tokens + output_tokens`; cached input categories are separate.
- Carry `TotalTokens` through domain aggregation and expose `total_tokens` in `token_usage` and `turn_usage`.
- The frontend accumulates only authoritative `turn_usage.total_tokens` values.
- Display normalized session consumption immediately before `ctx` after first confirmation.
- The details panel displays normalized total plus every confirmed cumulative category.

## 3. Epic and Artifact Impact

- Epic 10 remains the correct scope but expands from three to six stories.
- Backend and frontend PRDs are revised to distinguish context occupancy, processed token volume, category breakdowns, and output diagnostics.
- Story 10.3 is reopened as `ready-for-dev` for stable end-of-turn publication and compact-output removal.
- Story 10.4 adds backend provider-normalized totals.
- Story 10.5 adds frontend normalized session accumulation and presentation.
- Story 10.6 adds optional Anthropic reasoning-token capture.
- No persistence, cost calculation, extra provider request, or new endpoint is introduced.

## 4. Story Plan

### Story 10.3 ? Stable last-completed-turn context indicator

- Buffer `token_usage`; publish on `turn_usage`.
- Remove compact output ratio.
- Preserve optional detailed fields and cumulative category counts.
- Do not calculate a synthetic session total in the frontend.

### Story 10.4 ? Provider-normalized total token usage

- Add `TotalTokens` to provider-neutral usage.
- Normalize at OpenAI and Anthropic client/converter boundaries.
- Aggregate through complete/interrupted turns.
- Emit optional `total_tokens` in both usage events.

### Story 10.5 ? Session total token consumption indicator

- Sum `turn_usage.total_tokens` once per turn.
- Render session total immediately before `ctx`.
- Present exact total and every confirmed cumulative category in details.
- Reset with conversation lifecycle.

### Story 10.6 ? Anthropic reasoning token breakdown

- Verify supported Anthropic API/SDK extraction.
- Map confirmed thinking tokens to optional `ReasoningTokens`.
- Never infer counts or double-count output/normalized total.
- Require approval if an SDK dependency change is necessary.

## 5. Sequencing and Handoff

Execution order:

1. Developer: complete revised Story 10.3.
2. Backend developer: implement Story 10.4.
3. Frontend developer: implement Story 10.5 after 10.4 and 10.3.
4. Backend developer: implement Story 10.6 after capability/dependency assessment; it may proceed independently after 10.4.

Success criteria:

- `ctx` updates at most once per turn and remains correct for the final call.
- No compact `out` ratio remains.
- Session consumption uses backend-normalized totals and appears before `ctx`.
- Details expose total and all confirmed categories without frontend double counting.
- Anthropic reasoning is captured only when confirmed and does not alter total accounting.

## 6. Decision Record

The user explicitly approved all five plan items on 2026-09-16:

1. buffer `token_usage`, publish at `turn_usage`;
2. remove compact `out` / `output_ratio`;
3. keep optional `reasoning_tokens`;
4. add backend/frontend stories for provider-normalized `total_tokens` and cumulative session display before `ctx`;
5. add a backend story for Anthropic reasoning-token breakdown.
