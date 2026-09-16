# Story 10.5: Session total token consumption indicator

Status: backlog

## Story

As a chat user,
I want to see the normalized total tokens consumed since the current conversation started,
so that I can understand session consumption while separately monitoring current context occupancy.

## Acceptance Criteria

1. **Authoritative cumulative total**
   - The frontend accepts finite, non-negative integer `total_tokens` values from valid `turn_usage` events.
   - Session total is accumulated exclusively from `turn_usage.total_tokens`; per-call `token_usage` totals are never summed into it.
   - Complete and interrupted/iteration-limit turns both contribute exactly once.

2. **Compact placement**
   - After the first confirmed `turn_usage.total_tokens`, a compact session-consumption indicator appears immediately before the `ctx` indicator in the model-controls area.
   - The indicator clearly identifies itself as the current session total and displays a compact formatted value.
   - It is visually and semantically distinct from `ctx`, which represents context occupancy for the final call of the last completed turn.
   - No zero or unknown indicator is shown before a total has been confirmed.

3. **Accessible exact value**
   - The exact cumulative token count and its session scope are available through accessible text/semantics.
   - The indicator is not presented as cost, context capacity, provider quota, or persistent historical usage.

4. **Details panel**
   - The information panel presents cumulative `total_tokens` plus every confirmed cumulative category: input, output, cache-read, cache-write, and reasoning.
   - Category values continue to be accumulated from their authoritative `turn_usage` fields.
   - Optional or never-confirmed fields are omitted rather than displayed as zero.
   - The panel explains that cache/reasoning categories can overlap provider input/output accounting and are therefore not added again to `total_tokens` by the frontend.

5. **Lifecycle reset**
   - Starting, loading, or resetting a conversation clears normalized session total and category totals.
   - Reset follows the existing agent/thread lifecycle and empty-message reset signal.
   - A stale subscription cannot update the new conversation after cleanup.

6. **Regression safety**
   - The new indicator preserves model, thinking-effort, tools, context, send/resume, interrupt, error, and responsive behavior.
   - No frontend provider-specific formula, cost calculation, persistence, endpoint, or dependency is introduced.

## Tasks / Subtasks

- [ ] Extend frontend `turn_usage` schemas and context types with optional `total_tokens`.
- [ ] Accumulate normalized session totals exclusively from valid `turn_usage.total_tokens` values.
- [ ] Add the compact session indicator immediately before `ctx`.
- [ ] Extend the details panel with exact normalized total and all confirmed cumulative categories.
- [ ] Add tests for ordering, accessibility, multiple turns, interrupted turns, omissions, resets, and stale cleanup.
- [ ] Run frontend formatting, lint, type-check/build, focused tests, and full regression tests.

## Dev Notes

- Depends on Story 10.4's provider-normalized backend contract.
- The frontend must never reconstruct `total_tokens` from input/output/cache/reasoning fields because overlap rules differ by provider.
- The cumulative is session-scoped and stream-only; it resets on conversation load/start and is not historical analytics.

## Dev Agent Record

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2026-09-16: Story created from approved Story 10.3 course correction.
