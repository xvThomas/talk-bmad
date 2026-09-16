---
baseline_commit: c5aba9dcad63cc31f76686b6e4ae3c88f167c058
---

# Story 10.3: Last completed-call token indicators

Status: ready-for-dev

## Story

As a chat user,
I want to see how much context the last completed model call used,
so that I can recognize a conversation approaching the selected model's capacity.

## Acceptance Criteria

1. **Last completed call state**
   - Given the active AG-UI stream receives a custom event with `name: "token_usage"`, when the event is valid, then the UI stores its confirmed usage as the last completed LLM call for the active conversation.
   - A valid `token_usage` event received while a turn is running is stored as the **pending** latest completed-call snapshot and does not change the displayed indicator. A later valid event replaces the pending snapshot.
   - When the matching valid `turn_usage` event arrives, the pending snapshot is promoted to the displayed last completed-call state and the pending snapshot is cleared.
   - The displayed values therefore change at most once per turn and stay stable while the next turn is running.
   - A complete turn and an interrupted/iteration-limit turn both promote their pending snapshot when their `turn_usage` event arrives.
   - If a turn completes with no valid pending `token_usage`, the previously displayed snapshot is retained; no zero or estimated value is rendered.
   - Invalid, unrelated, or unknown custom events are ignored without changing the pending or displayed usage.
   - Starting, loading, or resetting a conversation clears the pending and displayed last-call usage.

2. **Context indicator**
   - Given confirmed `input_tokens` and a positive `context_window_tokens`, when the model controls render, then a compact horizontal context indicator appears beside or immediately near `ModelSelector`.
   - The indicator identifies the value as context usage for the **last completed turn**, and displays the formatted input count and percentage.
   - The percentage is based on the backend-provided `context_ratio`; the frontend does not estimate tokens or recompute a ratio from display-rounded values.
   - The indicator is not a live progress meter: it does not change for intermediate `token_usage` events within the currently running turn.
   - The exact count, percentage, and status are available through accessible text/semantics, not color alone.

3. **Context status thresholds**
   - `context_ratio < 0.70` renders normal status.
   - `0.70 <= context_ratio < 0.85` renders warning status.
   - `0.85 <= context_ratio < 1.00` renders critical status.
   - `context_ratio >= 1.00` renders blocked status.
   - Each status has a textual label and a stable semantic/test hook in addition to color styling.

4. **Unavailable context limit**
   - Given `input_tokens` exists but `context_window_tokens` is absent, zero, invalid, or otherwise unavailable, the UI shows the confirmed input count and an explicit unavailable-limit state.
   - No context percentage, progress value, or estimated limit is rendered in this state.
   - Missing input tokens do not render as zero and do not produce a context indicator pretending that usage is known.

5. **Completed-call output details**
   - No compact output-ratio chip is rendered in the control bar. `output_ratio` describes a single call measured against `provider_max_output_tokens`; in a multi-call turn the final call is frequently the shortest, so the value is neither the turn's peak nor its total and invites misreading as a turn budget.
   - The last completed call's `output_tokens` remains available in the details panel, explicitly scoped as a per-call value.
   - Output usage is shown only from the completed `token_usage` event; it is never rendered as live generation progress while a response is streaming.
   - Where an output percentage is shown in the details panel, it uses the backend-provided `output_ratio` and is not estimated or recomputed from rounded values.

6. **Usage details and omissions**
   - An accessible details affordance exposes every available value from the final call of the last completed turn: input, output, context limit, provider output limit, cache-read, cache-write, optional reasoning tokens, and ratios when available.
   - Unknown, absent, non-finite, or invalid values are omitted rather than displayed as zero.
   - The details remain understandable on narrow layouts and do not displace the existing model, thinking-effort, or tools controls.

7. **Authoritative cumulative usage**
   - Given a valid custom event with `name: "turn_usage"`, the UI adds that event's available token counts to a session-scoped cumulative usage state.
   - Cumulative usage is driven exclusively by `turn_usage`; individual `token_usage` events are never summed into it.
   - Multiple `token_usage` events in one turn therefore promote a single last-call display but do not increase the cumulative total more than once.
   - A complete turn and an interrupted/iteration-limit turn both reconcile from their single authoritative `turn_usage` event.
   - The details panel exposes every confirmed cumulative counter individually — `input`, `output`, `cache_read`, `cache_write`, `reasoning` — and omits fields that have never been confirmed.
   - `reasoning_tokens` remains optional and must not be inferred or treated as an anomaly when unavailable.
   - Provider-normalized `total_tokens` and its compact session indicator are explicitly deferred to Stories 10.4 and 10.5; this story must not calculate a frontend total from provider-dependent categories.

8. **Conversation reset**
   - Loading, starting, or resetting a conversation clears both last-call usage and cumulative usage before the next conversation's events are displayed.
   - Reset detection must follow the existing agent lifecycle rather than introducing a second conversation source of truth: react to the agent/thread reset observable already used by the UI (including the empty-message reset transition and any agent identity/thread change available from `useAgent`).
   - A stale subscription from a previous agent/conversation cannot update the current conversation after cleanup.

9. **Regression safety**
   - Existing message rendering, streaming state, model selection, thinking-effort selection, tools visibility, interrupts, errors, map controls, and send/resume actions retain their current behavior.
   - No token-estimation endpoint, pre-send blocking, cost calculation, persistence, history compaction, chart, or new dependency is introduced.

## Tasks / Subtasks

- [x] Task 1: Define validated frontend usage contracts (AC: #1, #4, #5, #6, #7)
  - [x] Add typed usage/domain shapes for per-call and per-turn values using the existing TypeScript conventions.
  - [x] Add Zod schemas or equivalent runtime guards at the AG-UI custom-event boundary for `token_usage` and `turn_usage`.
  - [x] Validate `event.name` and `event.value` from `@ag-ui/core` `CustomEvent`; the protocol value is `z.ZodAny`/unknown and must not be trusted as a typed object.
  - [x] Accept only finite, non-negative integer token counts and finite non-negative ratios/limits; omit unavailable fields instead of coercing malformed values to zero.
  - [x] Preserve the backend field names: `model`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `reasoning_tokens`, `context_window_tokens`, `provider_max_output_tokens`, `context_ratio`, and `output_ratio`.
  - [x] Keep `turn_usage` counts-only; do not require per-call limits or ratios for reconciliation.

- [ ] Task 2: Buffer per-call events and publish at the turn boundary (AC: #1, #7, #8)
  - [x] Extend `ChatUIProvider` state and effects to subscribe to `agent.subscribe({ onCustomEvent })` from `useAgent()`.
  - [x] Handle only validated `token_usage` and `turn_usage` events; leave all existing CopilotKit error subscription behavior intact.
  - [ ] Store each valid `token_usage` as the pending latest-call snapshot without changing displayed usage; repeated events replace only the pending snapshot.
  - [ ] On valid `turn_usage`, promote the pending snapshot to displayed usage, clear it, and independently add authoritative turn counts to cumulative state.
  - [ ] Retain the previous display when `turn_usage` arrives without a valid pending snapshot.
  - [x] Return the subscription cleanup from the React effect and ensure the callback cannot mutate state after the agent/conversation changes.
  - [ ] Reset pending, displayed, and cumulative usage on the existing conversation reset signal and agent/thread identity changes. Do not clear displayed usage merely because a response is running.

- [x] Task 3: Expose state through the UI context (AC: #1, #7, #9)
  - [x] Extend `chat-ui-context-types.ts` and the context value with last-call usage, cumulative usage, and any derived status/detail data needed by presentation components.
  - [x] Use stable, explicit types; do not add `any`, broad casts, or duplicate conversation state.
  - [x] Keep provider callbacks and existing context consumers backward compatible.

- [ ] Task 4: Stabilize the compact context indicator and details UI (AC: #2, #3, #4, #5, #6, #9)
  - [x] Add a focused presentation component under `src/components` (for example `TokenUsageIndicator.tsx`) rather than embedding parsing or aggregation logic in `ChatView`.
  - [x] Render it adjacent to `ModelSelector` in the existing model-controls area, preserving the current responsive layout and controls.
  - [x] Render normal/warning/critical/blocked context states with both visual styling and accessible status text.
  - [x] Render the unavailable-limit state without a percentage or progress value.
  - [ ] Remove the compact `out` / output-ratio chip from the controls while retaining confirmed per-call output values in the details panel.
  - [x] Provide an accessible details disclosure/popover using existing project primitives and semantics; do not add a UI library solely for this story.
  - [x] Ensure long counts, labels, and details remain usable at narrow viewport widths.

- [ ] Task 5: Update provider and component tests for revised behavior (AC: #1-#9)
  - [ ] Extend `src/__tests__/chat-ui-context.test.tsx` with pending replacement, end-of-turn promotion, invalid payload rejection, authoritative cumulative reconciliation, complete/interrupted turns, missing-snapshot retention, cleanup, and reset cases.
  - [ ] Extend focused indicator/ChatView tests with placement, all four thresholds, unavailable-limit behavior, absence of compact output ratio, details omissions, accessibility text/roles, and narrow-layout-safe rendering.
  - [ ] Assert that repeated `token_usage` events do not change the displayed indicator until one matching `turn_usage` promotes only the latest snapshot and adds cumulative counts once.
  - [ ] Assert that reset clears pending, displayed, and cumulative state and that a stale/unsubscribed agent cannot update the new conversation.
  - [x] Use the repository's existing Vitest and Testing Library mocks; keep tests deterministic and dependency-free.

- [ ] Task 6: Validate the revised frontend behavior (AC: #9)
  - [ ] Run the existing formatter/linter/type-check/build commands defined by `talk-ui/package.json`.
  - [ ] Run the focused context and component tests, then the full existing frontend test suite.
  - [x] Do not install dependencies or alter package versions unless an existing command proves a dependency is missing.

## Dev Notes

### Scope and invariants

- This story consumes the stream-only backend contract from Story 10.2. It does not modify `talk-backend`, the AG-UI protocol, model metadata, or backend event names.
- `token_usage` describes exactly one completed LLM call. It is the source for the last-call display only.
- `turn_usage` is the authoritative total for one completed or interrupted turn. It is the only source for the session cumulative display.
- Do not infer missing values, estimate tokens, calculate cost, persist usage, or derive cumulative totals by summing per-call events.
- Backend payloads omit unavailable fields. Frontend state should preserve that distinction; `0` is meaningful only when explicitly received and valid.

### Provider token semantics and deferred normalized total

Usage categories are not mutually disjoint in the same way across providers. OpenAI cache/reasoning counts are subsets of input/output, while Anthropic cache-read/cache-creation input counts are separate from uncached input. Story 10.3 must therefore not calculate or display a synthetic session total.

Story 10.4 introduces backend-normalized `total_tokens` at each LLM client boundary. Story 10.5 consumes its authoritative `turn_usage.total_tokens` values and renders cumulative session consumption immediately before `ctx`. Optional Anthropic reasoning-token breakdown is tracked separately by Story 10.6.

### AG-UI integration contract

`@ag-ui/client` exposes `AbstractAgent.subscribe(subscriber): { unsubscribe(): void }` and `AgentSubscriber.onCustomEvent({ event })`. The event is the AG-UI core `CustomEvent` shape:

```ts
{
  type: EventType.CUSTOM,
  name: string,
  value: unknown,
  timestamp?: number,
  rawEvent?: unknown,
}
```

The installed `@ag-ui/core@0.0.57` declaration models `value` as `z.ZodAny`; therefore TypeScript's imported event type does not validate the application payload. Runtime narrowing is required before state updates. Match `event.name` exactly (`token_usage` or `turn_usage`) and parse `event.value` with the project's existing Zod approach in `src/config/agui-schemas.ts` or a narrowly scoped sibling module.

Subscribe to the agent instance returned by `useAgent`, not to rendered messages and not to a second SSE transport. Preserve the existing `copilotkit.subscribe` error handling. Effects must unsubscribe on cleanup and when the agent/thread identity changes.

### Existing UI architecture to preserve

- `src/context/ChatUIContext.tsx` owns selected model, thinking effort, visible messages, errors, running state, interrupts, tools visibility, and send/resume actions. It is the intended owner for usage state and event subscription.
- `src/context/chat-ui-context-types.ts` defines the public context contract and must be updated with explicit usage types.
- `src/components/ChatView.tsx` renders the model/thinking/tools controls and is the intended placement surface.
- `src/components/ModelSelector.tsx` is an existing accessible custom dropdown; place the indicator near it without altering its selection behavior.
- `src/map/MapProvider.tsx` already uses the agent's empty-message lifecycle as precedent for clearing UI-derived state. Reuse the existing lifecycle signal instead of inventing a parallel conversation manager.
- Existing tests mock `useAgent`, `useCopilotKit`, and mutable mock agent objects. Add subscription/unsubscribe behavior to those mocks rather than introducing a new test harness.

### State model guidance

Represent last-call usage and cumulative usage separately. A useful shape is an object of optional confirmed fields, not a fully populated object of zeros. For cumulative counts, add only fields present in the incoming valid `turn_usage`; do not fabricate a zero for an absent field. If backend events from different models are possible in one UI session, the cumulative display must remain counts-based and must not present one model's limit as a global limit.

For status, prefer the backend `context_ratio` when it is valid. If a valid ratio is missing, do not manufacture a percentage; an input count with a missing limit uses the explicit unavailable-limit state. Treat exact threshold boundaries as warning at 0.70, critical at 0.85, and blocked at 1.00.

### Error handling and defensive behavior

Malformed custom events are external input. Ignore them after safe schema validation, with behavior consistent with existing frontend logging/error conventions; do not throw from the subscription callback and do not replace valid state with malformed data. Unknown event names must be ignored. Do not use broad catches or success-shaped fallback values.

### File structure expectations

Likely updates/additions (confirm against the current tree before editing):

- Update: `talk-ui/src/context/ChatUIContext.tsx`
- Update: `talk-ui/src/context/chat-ui-context-types.ts`
- Update: `talk-ui/src/components/ChatView.tsx`
- Add or update: `talk-ui/src/config/agui-schemas.ts` for custom usage schemas, or add a narrowly scoped usage schema module if that better matches current responsibilities
- Add: `talk-ui/src/components/TokenUsageIndicator.tsx` and focused subcomponents only if needed
- Update: `talk-ui/src/__tests__/chat-ui-context.test.tsx`
- Update: `talk-ui/src/__tests__/chat-view.test.tsx` or add a focused `token-usage-indicator.test.tsx`

Do not change `talk-backend`, package manifests, AG-UI dependency versions, unrelated map behavior, or model-selector semantics.

### Accessibility and responsive requirements

- Do not communicate threshold status by color alone. Include status text in the accessible name/description and expose exact counts and percentages to assistive technology.
- Use semantic progress semantics only when a real positive context limit and valid ratio are present; omit `aria-valuenow`/percentage semantics for unavailable-limit state rather than implying a value.
- Details must be keyboard accessible, have an explicit accessible label, and preserve focus behavior using existing primitives.
- Keep the compact control usable on small screens: allow wrapping or a responsive details layout rather than clipping counts or controls.

## Previous Story Intelligence

### Story 10.2 backend contract

- The backend emits `token_usage` once for each completed assistant LLM response, including initial and tool-result assistant calls. The payload is per-call, not a running turn total.
- The backend emits exactly one `turn_usage` event for each complete or interrupted turn. Its payload contains authoritative counts and no ratios.
- Event field names and omission behavior are contractual. Cache-write is provider-specific; unavailable values are omitted.
- Backend tests now cover multi-call turns, exactly one `turn_usage`, aggregated totals, interrupted turns with partial totals, complete payload fields, and independent ratio omission cases.
- Do not â€œfixâ€ or reinterpret backend omissions in the UI.

### Story 10.1 frontend/project conventions

- The frontend uses strict TypeScript (`noUnusedLocals`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`) and React 19 with Vitest/Testing Library.
- Existing AG-UI parsing uses Zod patterns in `src/config/agui-schemas.ts`; follow those patterns rather than adding unsafe casts.
- Existing custom controls are accessible and Tailwind-based. Preserve established styling, focus, and responsive conventions.
- Story 10.1's model metadata and provider-limit semantics are already represented by the backend contract; 10.3 only displays confirmed event values.

## Technical Requirements

- Use the existing dependency versions from `talk-ui/package.json`: React `^19.2.7`, TypeScript `~6.0.3`, `@ag-ui/client` `^0.0.57`, Vitest `^4.1.9`, Tailwind CSS `^4.3.2`, and Zod `^4.4.3`.
- No new dependency is required or in scope.
- Keep parsing/normalization pure and testable; keep React effects responsible only for subscription and lifecycle synchronization.
- Avoid `as any`, `as unknown as`, non-null assertions, and broad `catch` blocks. Use imported AG-UI types plus runtime schemas/type guards.
- Follow existing naming, import, formatting, and Tailwind conventions. Keep comments rare and explanatory only.

## Testing Requirements

| Area | Required coverage |
| --- | --- |
| Event boundary | Valid `token_usage` and `turn_usage`; unknown names; malformed values; absent optional fields; invalid negative/non-finite values |
| Latest call | First event stores values; second event replaces all displayed values; missing fields are omitted rather than retained as stale data unless the contract explicitly supplies them |
| Status | `<0.70`, exactly `0.70`, just below `0.85`, exactly `0.85`, just below `1.00`, exactly `1.00`, and unavailable-limit state |
| Output | No compact `out` ratio; confirmed final-call output values remain details-only; absent output/limit omitted |
| Details | Input/output/limits/cache/reasoning values when present; absent values not rendered as zero |
| Cumulative | Two per-call events plus one turn total add once; multiple turns add authoritative totals; partial/interrupted turn reconciles; absent fields remain absent |
| Lifecycle | Initial state; conversation start/load/reset; empty-message transition; agent/thread change; unsubscribe cleanup; stale callback cannot update current state |
| UI | Placement near model selector; accessible names/roles/text; keyboard-open details; narrow-layout rendering; existing controls unaffected |

## References

- [Source: `_bmad-output/planning-artifacts/epics.md` â€” Epic 10, Story 10.3, frontend FR-1 to FR-14]
- [Source: `_bmad-output/planning-artifacts/prds/prd-token-observability-frontend-2026-09-05/prd.md` â€” functional requirements, thresholds, accessibility, reset, cumulative usage]
- [Source: `_bmad-output/planning-artifacts/prds/prd-token-observability-frontend-2026-09-05/addendum.md` â€” compact horizontal indicator and last-completed-call semantics]
- [Source: `_bmad-output/planning-artifacts/prds/prd-token-observability-frontend-2026-09-05/.decision-log.md` â€” placement and update decisions]
- [Source: `_bmad-output/planning-artifacts/prds/prd-token-observability-backend-2026-09-05/addendum.md` â€” event payload and authoritative `turn_usage` reconciliation]
- [Source: `_bmad-output/implementation-artifacts/10-2-per-response-token-usage-in-the-ag-ui-stream.md` â€” backend event contract and omission rules]
- [Source: `talk-ui/src/context/ChatUIContext.tsx` â€” provider state and agent lifecycle]
- [Source: `talk-ui/src/context/chat-ui-context-types.ts` â€” context public contract]
- [Source: `talk-ui/src/components/ChatView.tsx` â€” model-controls placement]
- [Source: `talk-ui/src/components/ModelSelector.tsx` â€” accessible model selector]
- [Source: `talk-ui/src/config/agui-schemas.ts` â€” existing AG-UI validation patterns]
- [Source: `talk-ui/src/map/MapProvider.tsx` â€” existing empty-message reset precedent]
- [Source: `talk-ui/node_modules/.pnpm/@ag-ui+core@0.0.57/node_modules/@ag-ui/core/dist/index.d.ts` â€” `CustomEvent` shape]
- [Source: `talk-ui/node_modules/@ag-ui/client/dist/index.d.ts` â€” `AbstractAgent.subscribe` and `AgentSubscriber.onCustomEvent`]

## Project Structure Notes

- The repository is a shared BMad planning hub; this story targets the sibling `talk-ui` repository and must not modify backend implementation files.
- The story file belongs in `_bmad-output/implementation-artifacts` and follows the existing numbered-story naming convention.
- Keep the implementation within the existing context/components/config/tests structure. Do not create a parallel state store or transport layer.

## Dev Agent Record

### Agent Model Used

GPT-5.6 Sol (story context preparation)
HydraFusion (implementation)

### Debug Log References

- `npm run lint` initially failed with `react-hooks/set-state-in-effect` for the conversation-reset effects; replaced with the React "adjust state during render" pattern keyed on agent identity + empty-message transition.
- `npm test` initially failed in `app.test.tsx` because its `useAgent` mock lacked `subscribe`; mock extended with `subscribe`, `agentId` and `threadId`.
- `npm run format:fix` reformatted unrelated repository files (line endings); those changes were reverted so the diff stays limited to this story.

### Completion Notes List

- Ultimate context-engine analysis completed - comprehensive developer guide created.
- AG-UI custom-event type and subscription lifecycle verified against installed `@ag-ui/client@0.0.57` / `@ag-ui/core@0.0.57` declarations.
- Story is ready for frontend implementation; no frontend or backend source code was changed by this workflow.
- Implemented `src/config/token-usage-schemas.ts`: Zod runtime guards for `token_usage`/`turn_usage` (non-negative integer counts, finite non-negative ratios), authoritative cumulative addition, threshold mapping (0.70 / 0.85 / 1.00), context/output view derivation and formatting helpers. Unavailable fields are omitted, never coerced to zero.
- `ChatUIProvider` now subscribes to `agent.subscribe({ onCustomEvent })`, replaces last-call usage on each valid `token_usage`, adds only authoritative `turn_usage` totals to cumulative state, unsubscribes on cleanup and guards against stale callbacks. Usage resets on agent/thread identity change and on the empty-message conversation reset; running state never clears it. Existing CopilotKit error subscription untouched.
- Added `TokenUsageIndicator` rendered next to `ModelSelector`: compact context chip with `data-status` hook, accessible label carrying exact counts/percentage/status, `role="progressbar"` only when a real limit and backend ratio exist, explicit limit-unavailable state without percentage, completed-call output chip, and a keyboard-accessible details panel listing only confirmed per-call and session values. Controls row now wraps on narrow layouts.
- Tests: 28 schema tests, 15 indicator tests, 12 provider ingestion/lifecycle tests, 3 ChatView placement tests. Full suite: 249 passing, `eslint` clean, `prettier --check` clean, `tsc -b && vite build` successful.
- No backend change, no new dependency, no estimation, persistence or cost logic introduced.
- 2026-09-16 course correction approved: reopen implementation to buffer per-call usage until `turn_usage`, remove the compact output ratio, retain optional reasoning details, and defer normalized session total to Stories 10.4/10.5.

### File List

- `_bmad-output/implementation-artifacts/10-3-last-completed-call-token-indicators.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `talk-ui/src/config/token-usage-schemas.ts` (added)
- `talk-ui/src/components/TokenUsageIndicator.tsx` (added)
- `talk-ui/src/components/ChatView.tsx` (modified)
- `talk-ui/src/context/ChatUIContext.tsx` (modified)
- `talk-ui/src/context/chat-ui-context-types.ts` (modified)
- `talk-ui/src/__tests__/token-usage-schemas.test.ts` (added)
- `talk-ui/src/__tests__/token-usage-indicator.test.tsx` (added)
- `talk-ui/src/__tests__/chat-ui-context.test.tsx` (modified)
- `talk-ui/src/__tests__/chat-view.test.tsx` (modified)
- `talk-ui/src/__tests__/app.test.tsx` (modified)

## Change Log

- 2026-09-16: Implemented initial last completed-call and cumulative token indicators in the frontend (schemas, provider ingestion, context contract, indicator UI, tests). Status ready-for-dev → review.
- 2026-09-16: Approved course correction revised AC/tasks: stable end-of-turn context publication, no compact output ratio, optional reasoning preserved; normalized session total moved to Stories 10.4/10.5. Status review/in-progress → ready-for-dev.
