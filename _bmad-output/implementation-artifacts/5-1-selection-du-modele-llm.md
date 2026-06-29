---
baseline_commit: 3eb091e1ba9aff3e5413610ddc8f497a336e0da4
---

# Story 5.1: Sélection du modèle LLM

Status: done

## Story

As an end user,
I want to choose which LLM model responds to my messages,
so that I can pick the best model for my needs (speed, quality, cost).

## Acceptance Criteria (BDD)

1. **Given** the chat input area is rendered **When** the user sees the model selector **Then** a dropdown/select is displayed integrated in the input area (not in a settings page) **And** the available models are: `haiku-4.5`, `sonnet-4.6`, `opus-4.6`, `o4-mini`, `gpt-5.4`, `mistral-small`, `agent` **And** the model list is defined as a typed constant validated by Zod **And** a default model is pre-selected (`sonnet-4.6`).
2. **Given** the user selects a model **When** they send a message **Then** `forwardedProps.model` is set to the selected alias in the AG-UI request.
3. **Given** a model is selected **When** a response is streaming **Then** the selector is disabled (cannot change model mid-stream).
4. **Given** all of the above **When** I run `pnpm build && pnpm lint && pnpm test` **Then** everything passes.

## Tasks / Subtasks

- [x] Task 1: Add typed model catalog with Zod validation (AC: #1)
  - [x] Create `src/config/models.ts` (new file)
  - [x] Define a typed model alias list (`as const`) with exactly: `haiku-4.5`, `sonnet-4.6`, `opus-4.6`, `o4-mini`, `gpt-5.4`, `mistral-small`, `agent`
  - [x] Add Zod schema (`z.enum(...)`) and export a runtime validator utility for selected model values
  - [x] Export `DEFAULT_MODEL = "sonnet-4.6"`
  - [x] Add compile-time + runtime guards so only valid aliases can be used in `forwardedProps.model`

- [x] Task 2: Integrate model selector in chat input area (AC: #1, #3)
  - [x] Update `src/components/ChatInput.tsx` to render a model `<select>` integrated in the same input bar
  - [x] Add props: `selectedModel`, `onModelChange`, and keep existing `disabled`
  - [x] Disable selector while `disabled === true` (streaming)
  - [x] Preserve current message input/send behaviors (trim, Enter submit, clear after submit)

- [x] Task 3: Wire model state and forwarding in chat orchestration (AC: #2, #3)
  - [x] Update `src/components/ChatView.tsx` to own `selectedModel` state initialized to `DEFAULT_MODEL`
  - [x] Pass `selectedModel` and `onModelChange` into `ChatInput`
  - [x] Update `copilotkit.runAgent(...)` call to send `forwardedProps.model = selectedModel`
  - [x] Keep current safeguards unchanged: `if (agent.isRunning) return`, error handling, and message normalization

- [x] Task 4: Add/adjust tests (AC: #4)
  - [x] Update `src/__tests__/chat-input.test.tsx` for model selector rendering, default selected option, and disabled behavior
  - [x] Update `src/__tests__/chat-view.test.tsx` to assert selected model is forwarded in `runAgent` payload
  - [x] Add negative-path test for invalid model input if runtime parsing helper is exposed
  - [x] Keep existing tests green (auto-scroll, markdown, non-text placeholders, error alert)

- [x] Task 5: Validation and docs alignment (AC: #4)
  - [x] Run `pnpm lint`
  - [x] Run `pnpm test`
  - [x] Run `pnpm build`
  - [x] If labels are changed to English in this story, update impacted tests accordingly; otherwise preserve existing label language to avoid scope creep

### Review Findings

- [x] [Review][Patch] Replace throwing `parseModelAlias` with safe validation in `handleSend` [src/components/ChatView.tsx:84]
- [x] [Review][Patch] Type `onModelChange` prop as `(model: ModelAlias) => void` instead of `string` [src/components/ChatInput.tsx:5]
- [x] [Review][Patch] Add integration test: selector disabled when `agent.isRunning=true` [src/__tests__/chat-view.test.tsx]
- [x] [Review][Patch] Add integration test: default model forwarded without user interaction [src/__tests__/chat-view.test.tsx]
- [x] [Review][Patch] Fix `aria-label` to proper French "Modèle" or English "Model" [src/components/ChatInput.tsx:31]
- [x] [Review][Defer] Model selection not persisted across remounts — deferred, out of scope for 5.1

## Dev Notes

### Story Context and Scope Boundaries

- This story implements **model selection only** (FR-5 + model forwarding from FR-7 subset).
- Do **not** implement thinking effort selector here (that is Story 5.2).
- Do **not** implement reasoning rendering here (that is Story 5.3).
- Keep tool-call rendering roadmap unchanged (Epic 6).

### Existing Code State (Must Read Before Editing)

- `src/components/ChatView.tsx`
  - Current send path hardcodes `forwardedProps: { model: "haiku-4.5" }`.
  - Already contains critical protections that must be preserved:
    - guard against double send while streaming
    - promise rejection handling for `runAgent`
    - message normalization and defensive rendering pipeline
    - auto-scroll hook integration
- `src/components/ChatInput.tsx`
  - Currently only text input + send button.
  - Form submit behavior is stable and fully tested.
- `src/__tests__/chat-input.test.tsx`, `src/__tests__/chat-view.test.tsx`
  - Existing tests rely on labels and current button behavior.
  - Extend them rather than replacing core assertions.

### Architecture Compliance Requirements

- Keep using headless CopilotKit primitives (`useAgent`, `useCopilotKit`) and `runAgent({ agent, forwardedProps })`.
- Keep agent registration through `agents__unsafe_dev_only` untouched for this epic stage.
- Enforce runtime validation at boundaries with Zod per NFR-1.
- No `any` in implementation code.

### Library and Framework Requirements

- Reuse existing dependencies already present in `talk-ui`:
  - React + TypeScript strict
  - Zod v4 (`zod/v4`)
  - CopilotKit v2 hooks
  - Vitest + Testing Library
- No additional dependency is required for Story 5.1.

### File Structure Requirements

- New file expected: `src/config/models.ts`
- Updated files expected:
  - `src/components/ChatInput.tsx`
  - `src/components/ChatView.tsx`
  - `src/__tests__/chat-input.test.tsx`
  - `src/__tests__/chat-view.test.tsx`
- Optional update (only if needed for shared types):
  - `src/config/agent.ts` (prefer no change in 5.1)

### UX and Behavior Guardrails

- Selector must be integrated in chat input area, not separated into settings.
- Selector must clearly show default selected model (`sonnet-4.6`) on first render.
- Selector must become disabled while response is streaming.
- Changing model must only affect **next send**; no mid-stream mutation behavior.
- Preserve current message layout and non-text placeholders.

### Data Contract for Forwarded Props

When message is submitted:

```ts
copilotkit.runAgent({
  agent,
  forwardedProps: {
    model: selectedModel,
  },
});
```

- `selectedModel` must be guaranteed to be one of the allowed aliases.
- Do not send extra keys in this story.

### Testing Requirements

Minimum tests to add/update:

1. ChatInput renders model selector with all expected model aliases.
2. Default selected model is `sonnet-4.6`.
3. Selector disabled when `disabled=true`.
4. ChatView sends selected model through `forwardedProps.model`.
5. Existing submit behavior still works (trim, clear, Enter).

Regression focus:

- `runAgent` rejection path still sets error alert.
- Existing message filtering/normalization remains unchanged.

### Previous Work Intelligence

Recent commits indicate this area already underwent reliability hardening and defensive rendering:

- `3eb091e` message normalization, non-text placeholders, error display hardening
- `00a431a` auto-scroll and related tests
- `c4faae9` markdown rendering integration

Implementation should build on these patterns and avoid reverting any of them.

### Latest Tech Notes

CopilotKit headless docs confirm the intended pattern remains:

- use `useAgent` + `useCopilotKit`
- add user message, then `runAgent({ agent })`
- custom UI controls are expected in headless mode

For this story, the model selector is a custom UI control feeding `forwardedProps.model` on send.

### Missing Optional Inputs

- No dedicated architecture document found in planning artifacts.
- No dedicated UX document found in planning artifacts.
- Story context derived from epics + PRD + current codebase state.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5: Contrôle du modèle et du raisonnement]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.1: Sélection du modèle LLM]
- [Source: _bmad-output/planning-artifacts/prds/prd-talk-frontend-2026-06-28/prd.md#3.2 Model & Thinking Selection]
- [Source: _bmad-output/planning-artifacts/prds/prd-talk-frontend-2026-06-28/prd.md#4.1 Type Safety]
- [Source: talk-ui/src/components/ChatView.tsx]
- [Source: talk-ui/src/components/ChatInput.tsx]
- [Source: talk-ui/src/__tests__/chat-view.test.tsx]
- [Source: talk-ui/src/__tests__/chat-input.test.tsx]
- [Source: https://docs.copilotkit.ai/custom-look-and-feel/headless-ui]

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- Story generated via bmad-create-story workflow with explicit target `5.1`
- RED phase check: `pnpm test -- src/__tests__/chat-input.test.tsx src/__tests__/chat-view.test.tsx src/__tests__/models.test.ts` (failed as expected before implementation)
- Full validation: `pnpm lint && pnpm test && pnpm build` (all green)

### Implementation Plan

- Add a dedicated typed model catalog with Zod runtime validation and a strict default model.
- Extend `ChatInput` to include a model selector integrated in the same input bar and bound to controlled props.
- Move selected model ownership to `ChatView` and forward it via `runAgent({ forwardedProps: { model } })`.
- Expand tests to cover selector rendering/default/disabled behavior, forwarding payload, and invalid model parsing.

### Completion Notes List

- Implemented typed model catalog in `src/config/models.ts` with Zod enum, `DEFAULT_MODEL`, `parseModelAlias`, and `isModelAlias`.
- Added integrated model selector to `ChatInput` with `selectedModel` and `onModelChange` props while preserving existing send behavior.
- Updated `ChatView` to own `selectedModel` state (default `sonnet-4.6`) and send `forwardedProps.model` from selected value.
- Added/updated tests for model selector behavior, model forwarding, and invalid model parsing.
- Full validation completed successfully: lint, tests, and production build.

### File List

- `talk-ui/src/config/models.ts` (NEW)
- `talk-ui/src/components/ChatInput.tsx` (UPDATE)
- `talk-ui/src/components/ChatView.tsx` (UPDATE)
- `talk-ui/src/__tests__/chat-input.test.tsx` (UPDATE)
- `talk-ui/src/__tests__/chat-view.test.tsx` (UPDATE)
- `talk-ui/src/__tests__/models.test.ts` (NEW)

## Change Log

- 2026-06-29: Implemented Story 5.1 model selector end-to-end (typed model catalog, UI integration, model forwarding, tests, and full validation).
