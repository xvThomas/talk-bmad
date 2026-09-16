---
title: "talk-ui - Token Limit Observability"
status: draft
created: 2026-09-05
updated: 2026-09-16
---

## 1. Purpose

This PRD defines the frontend experience for showing stable, confirmed token observability: context occupancy from the final LLM call of the last completed turn, and provider-normalized token consumption accumulated during the current conversation. It consumes backend AG-UI usage events and does not estimate tokens or poll an API.

## 2. Vision

While using a model, a user can understand both how close the last completed turn came to the model's context capacity and how many normalized tokens the current session has consumed. Values remain stable while a turn runs, compact near the model controls, and fully explained through accessible details.

## 3. Target User and Journey

**UJ-1: Sam monitors a long conversation.** Sam sends a message that may trigger several LLM calls through tool execution. While the turn runs, the existing context indicator remains unchanged. When the turn completes normally or through an iteration-limit interruption, the UI publishes the context usage of that turn's final completed LLM call. A compact normalized session total appears immediately before `ctx` and increases once per authoritative `turn_usage`. Sam can inspect exact per-call and cumulative input, output, cache, reasoning, limits, and normalized total values. Unknown optional values are omitted rather than represented as zero.

## 4. Functional Requirements

### 4.1 Receive, Buffer, and Publish Usage

- **FR-1:** The UI consumes backend AG-UI `token_usage` and `turn_usage` custom events without introducing a new endpoint.
- **FR-2:** During an active turn, each valid `token_usage` replaces a pending latest-call snapshot without changing the displayed context indicator.
- **FR-3:** When the matching valid `turn_usage` arrives, the UI promotes the pending latest-call snapshot to the displayed last-completed-turn state and clears the pending snapshot.
- **FR-4:** Complete and interrupted/iteration-limit turns use the same `turn_usage` publication boundary.
- **FR-5:** If a completed turn has no valid pending `token_usage`, the previous displayed snapshot remains unchanged; the UI does not fabricate zero or estimated usage.
- **FR-6:** Starting, loading, or resetting a conversation clears pending usage, displayed usage, and cumulative session usage through the existing agent/thread lifecycle.

### 4.2 Context Indicator

- **FR-7:** A compact horizontal `ctx` indicator appears near the model selector whenever confirmed final-call input tokens are available.
- **FR-8:** With a positive context-window limit and backend-provided ratio, the indicator shows the exact count and percentage for the final call of the last completed turn.
- **FR-9:** Context status uses four accessible states: normal below $70\%$, warning from $70\%$ up to but excluding $85\%$, critical from $85\%$ up to but excluding $100\%$, and blocked at or above $100\%$.
- **FR-10:** When the context-window limit or ratio is unavailable, the UI shows the confirmed input count with an explicit unavailable-limit state and no estimated percentage.
- **FR-11:** The context indicator is not a live progress meter and does not change for intermediate calls while the current turn is running.

### 4.3 Session Consumption and Details

- **FR-12:** No compact `out` or `output_ratio` indicator is displayed because a final call's output ratio is neither the peak nor the authoritative total of a multi-call turn.
- **FR-13:** The UI accumulates detailed session categories exclusively from authoritative `turn_usage` events: input, output, cache-read, cache-write, and optional reasoning tokens.
- **FR-14:** When `turn_usage.total_tokens` is available, the UI adds it to a normalized session total and never reconstructs that total from provider-dependent category fields.
- **FR-15:** After the first confirmed normalized total, a compact session-consumption indicator appears immediately before `ctx`; it is clearly labelled as session-scoped and is not presented as context capacity, cost, quota, or historical usage.
- **FR-16:** An accessible details view exposes normalized session total, every confirmed cumulative category, and every available final-call value, including input, output, limits, cache, and optional reasoning tokens.
- **FR-17:** Missing, invalid, or never-confirmed optional metrics are omitted without showing zero as a substitute for unknown data.
- **FR-18:** The details explain that cache and reasoning fields can be subsets or separate categories depending on the provider and are not added again by the frontend.

## 5. Non-Functional Requirements

- **NFR-1:** Indicators do not cause disruptive control reflow; large counts are compact visually and exact in accessible text.
- **NFR-2:** The controls and details work on supported desktop and mobile layouts without overlap or clipping.
- **NFR-3:** Tests cover event buffering, end-of-turn publication, complete/interrupted turns, all context statuses, unavailable limits, normalized session accumulation, indicator ordering, omissions, reset, and stale subscription cleanup.
- **NFR-4:** Existing chat messages, model selection, thinking effort, reasoning blocks, tools, interrupts, and error handling remain unchanged.

## 6. Out of Scope

- Pre-send token estimates or request blocking.
- Editing output limits from the UI.
- Frontend provider-specific total formulas.
- Charts, cost estimates, persistence, historical analytics, or cross-conversation aggregation.
- Automatic context reduction or conversation summarization.

## 7. Related Artifacts

- Backend PRD: `prds/prd-token-observability-backend-2026-09-05/prd.md`
- UI rationale: `addendum.md`
- Epic 10: `../../epics.md`
