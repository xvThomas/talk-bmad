---
title: "talk-ui - Token Limit Observability"
status: draft
created: 2026-09-05
updated: 2026-09-05
---

## 1. Purpose

This PRD defines the frontend experience for showing the token consumption of the most recently completed LLM call. It consumes the backend's AG-UI token-usage event and does not independently estimate tokens or poll an API.

## 2. Vision

While choosing or using a model, a user can immediately understand whether the most recent call was comfortably within, approaching, or beyond its documented context capacity. The information remains compact in the conversation controls, with exact values and supporting metrics available on demand.

## 3. Target User and Journey

**UJ-1: Sam monitors a long conversation.** Sam uses a model during a multi-turn conversation. After each model response, the model controls update to show the confirmed context used by that LLM call, such as `412 k / 1 M tokens (41.2%)`. When a tool loop causes another model response, the control updates again rather than waiting for the user turn to finish. Sam can inspect the output count, cache, and reasoning details when they are available. If a provider does not supply a limit, Sam sees the token count and an explicit unavailable-limit state rather than a misleading percentage.

## 4. Functional Requirements

### 4.1 Receive and Retain Usage

- **FR-1:** The UI consumes the backend AG-UI custom token-usage event without introducing a new endpoint.
- **FR-2:** The UI retains the most recently received token-usage event for the active conversation.
- **FR-3:** When multiple LLM responses occur in one user turn, the UI updates after each event and displays the latest completed call.
- **FR-4:** Starting a new conversation clears the displayed token usage.
- **FR-5:** The UI does not calculate or display estimated usage before an LLM response has completed.

### 4.2 Context Indicator

- **FR-6:** A compact horizontal progress indicator appears near the model selector whenever confirmed input tokens and a context-window limit are available.
- **FR-7:** The indicator visibly labels itself as the context of the last completed call and shows both an exact count and percentage, for example `412 k / 1 M tokens (41.2%)`.
- **FR-8:** Context status uses four accessible states: normal below $70\%$, warning from $70\%$ up to but excluding $85\%$, critical from $85\%$ up to but excluding $100\%$, and blocked at or above $100\%$.
- **FR-9:** The status is communicated with text and accessible semantics as well as color.
- **FR-10:** When confirmed input tokens are available but the context-window limit is unavailable, the UI shows the input token count and an explicit unavailable-limit state; it does not render a ratio or a misleading progress percentage.

### 4.3 Output Indicator and Details

- **FR-11:** When output tokens and the provider maximum output limit are available, the UI displays a compact secondary value for the last completed call, for example `Sortie: 1.8 k / 16 k (11.3%)`.
- **FR-12:** The output indicator is presented as a completed-call diagnostic, not as a live progress meter while the response is generating.
- **FR-13:** The UI provides an accessible details view for available input tokens, output tokens, context and output limits, cache tokens, and reasoning tokens.
- **FR-14:** Missing optional metrics are omitted from the details view without showing zero as a substitute for unknown data.

## 5. Non-Functional Requirements

- **NFR-1:** The indicator does not reflow or resize the chat controls when values change; large counts are formatted compactly and retain an exact accessible label.
- **NFR-2:** The interface works at supported desktop and mobile layouts without text overlap or clipping.
- **NFR-3:** Unit tests cover event handling, all four context statuses, unavailable-limit rendering, and reset on a new conversation.
- **NFR-4:** Existing chat messages, model selection, reasoning blocks, and error handling remain unchanged.

## 6. Out of Scope

- Pre-send token estimates or request blocking.
- Editing output limits from the UI.
- Charts, cost estimates, historical analytics, or cross-conversation aggregation.
- Automatic context reduction or conversation summarization.

## 7. Related Artifacts

- Backend PRD: `prds/prd-token-observability-backend-2026-09-05/prd.md`
- UI rationale: `addendum.md`
