---
title: "Talk UI — CopilotKit Frontend"
status: draft
created: 2026-06-28
updated: 2026-06-28
---

# PRD: Talk UI — CopilotKit Frontend

## 0. Document Purpose

This PRD defines the requirements for `talk-ui`, a React web application that provides a browser-based chat interface to the `talk` backend AG-UI server. It targets a single developer and serves as the foundation for an evolving product that will later incorporate domain-specific interactions (mapping, data visualization). This document covers V1: the conversational chat core.

**Related documents:**

- Backend PRD: `prds/prd-talk-bmad-2026-06-21/prd.md`
- Backend epics: `planning-artifacts/epics.md`

## 1. Vision

The `talk` conversation engine currently operates through a terminal CLI. While powerful for developers, this limits access to technical users. `talk-ui` provides a web interface — accessible from any browser without installation — that exposes the full capabilities of the backend: streaming conversation, model selection, reasoning display, tool call visibility, and interrupt handling.

The application is designed as an extensible shell: V1 delivers the chat core, future iterations add domain-specific UI panels (maps, charts) alongside the conversation. The architecture and tooling choices reflect this trajectory.

## 2. Target Users

### 2.1 Jobs To Be Done

- **End user (non-technical):** I want to interact with an AI assistant through a modern web chat interface, see what it's thinking, control which model responds, and understand when tools are being used — without needing to install anything.
- **Demo audience (colleagues):** I want to see a polished proof-of-concept that demonstrates the full AG-UI protocol capabilities in a real UI.
- **Developer (maintainer):** I want a well-structured, type-safe, tested codebase that I can extend with new UI features as the backend evolves.

### 2.2 Non-Users (V1)

- Anonymous public users (no deployment, local only)
- Mobile-first users (responsive but desktop-primary)
- Users requiring authentication

## 3. Functional Requirements

### 3.1 Chat Conversation

- **FR-1:** Send a text message and receive a streaming response displayed progressively (message-level streaming, not token-level).
- **FR-2:** Display the conversation as a vertical message list: user messages right-aligned, assistant messages left-aligned.
- **FR-3:** Chat layout centered horizontally and vertically when the conversation is empty; transitions to scroll-down layout with input fixed at bottom once messages exist.
- **FR-4:** Auto-scroll to latest message during streaming; pause auto-scroll if user scrolls up.

### 3.2 Model & Thinking Selection

- **FR-5:** Provide a model selector (dropdown/select) integrated in the chat input area. Models are hardcoded in the frontend:
  - `haiku-4.5` (thinking: budget)
  - `sonnet-4.6` (thinking: budget)
  - `opus-4.6` (thinking: adaptive)
  - `o4-mini` (thinking: effort)
  - `gpt-5.4` (no thinking)
  - `mistral-small` (no thinking)
  - `agent` (no thinking)
- **FR-6:** Provide a thinking effort selector (dropdown/select) integrated in the chat input area. Visible only when the selected model supports thinking. Values: `off`, `low`, `medium`, `high`.
- **FR-7:** Selected model and thinking effort are sent as `forwardedProps.model` and `forwardedProps.thinkingEffort` in the AG-UI request.

### 3.3 Reasoning/Thinking Display

- **FR-8:** When the backend emits `REASONING_*` events, display the thinking content above the assistant's text response. Always visible (not collapsed).
- **FR-9:** Reasoning content is visually distinct from the assistant's final response (different styling — e.g., muted color, italic, or bordered block).

### 3.4 Tool Call Display

- **FR-10:** When the backend emits `TOOL_CALL_START`/`TOOL_CALL_ARGS`/`TOOL_CALL_END` events, display tool call information in the message flow.
- **FR-11:** Tool messages are collapsed by default, showing only the tool name and a chevron. Clicking expands to reveal arguments and result.
- **FR-12:** Multiple tool calls in one turn are displayed as separate collapsible items.

### 3.5 Interrupt Handling (Max Iterations)

- **FR-13:** When the backend emits a `RUN_FINISHED` event with outcome type `interrupt` and reason `talk:max_iterations`, display a "Continue" button inline in the conversation flow.
- **FR-14:** Clicking "Continue" sends a resume request with status `resolved` and the interrupt's `threadId`.
- **FR-15:** If the user types and sends a new message instead of clicking "Continue", it is treated as a new question (standard message flow), not a resume.

### 3.6 Send & Cancel

- **FR-16:** The chat input area has a send button that submits the message.
- **FR-17:** While a response is streaming, the send button transforms into a cancel button. Clicking it disconnects the SSE stream (client-side cancellation).
- **FR-18:** After cancellation, the partial response disappears. The user's question remains visible in the conversation flow with a "Retry" button. Clicking "Retry" copies the question back into the chat input for easy reformulation or re-submission.

### 3.7 Error Display

- **FR-19:** When the backend emits an AG-UI error event (`RUN_ERROR`), display the error message inline in the conversation flow with a distinctive error style (e.g., red/orange accent, error icon).
- **FR-20:** Errors do not prevent the user from sending new messages.

### 3.8 Loading/Activity Indicators

- **FR-21:** While waiting for the backend (between sending a message and receiving the first streaming content), display a discrete but elegant activity indicator. This communicates that the LLM and backend are working.
- **FR-22:** During tool execution (between `TOOL_CALL_START` and `TOOL_CALL_END`), the tool call item shows an in-progress indicator.

### 3.9 Documentation

- **FR-23:** The repository includes a `README.md` oriented toward getting started: prerequisites, install, build, run, test commands (pnpm-based).
- **FR-24:** The README is updated with each development story to reflect the current state of the application.

## 4. Non-Functional Requirements

### 4.1 Type Safety

- **NFR-1:** All incoming data (SSE events from the backend, configuration, props) is validated at the boundary using Zod schemas. No `any` types in application code.
- **NFR-2:** TypeScript strict mode enabled (`strict: true` in tsconfig).

### 4.2 Code Quality

- **NFR-3:** ESLint with flat config (`eslint.config.ts`), using `typescript-eslint/strict` + `eslint-plugin-react` + Prettier integration.
- **NFR-4:** Prettier for formatting, enforced in CI.
- **NFR-5:** Scripts available: `pnpm lint`, `pnpm lint:fix`, `pnpm format`, `pnpm format:fix`.

### 4.3 Testing

- **NFR-6:** Unit and component tests with Vitest + Testing Library.
- **NFR-7:** Coverage target: 100% (minimum acceptable: 80%). Trivial code (type re-exports, constants) may be excluded.
- **NFR-8:** Tests run in CI on every push/PR.

### 4.4 Performance

- **NFR-9:** Streaming messages render with no perceptible lag between SSE event reception and DOM update.
- **NFR-10:** Activity indicators provide immediate visual feedback (< 100ms after request sent).

### 4.5 Accessibility

- **NFR-11:** WCAG 2.1 AA structural best effort:
  - Sufficient color contrast in dark theme
  - Keyboard navigation functional (tab, enter, escape)
  - Semantic HTML (no clickable `<div>` without role)
  - Labels on interactive controls (selects, buttons)
- **NFR-12:** No formal accessibility audit in V1, but structure avoids creating accessibility debt.

### 4.6 Responsive Design

- **NFR-13:** The application is usable on mobile, tablet, and desktop viewports.
- **NFR-14:** Desktop is the primary design target; mobile is functional but not optimized.

### 4.7 CI/CD

- **NFR-15:** GitHub Actions workflow: build + lint + test on push and PR to `main`.
- **NFR-16:** CI failure blocks merge (branch protection recommended).

## 5. Technical Constraints

| Constraint         | Value                                                                                                     |
| ------------------ | --------------------------------------------------------------------------------------------------------- |
| Framework          | React (via Vite)                                                                                          |
| Build tool         | Vite                                                                                                      |
| Styling            | Tailwind CSS + CopilotKit style overrides                                                                 |
| Chat SDK           | CopilotKit (AG-UI protocol)                                                                               |
| Routing            | TanStack Router                                                                                           |
| Data fetching      | TanStack Query                                                                                            |
| Data architecture  | Layered: HTTP client (fetch) → React Query hook + Zod validation → Component                              |
| Validation         | Zod                                                                                                       |
| Package manager    | pnpm                                                                                                      |
| Language           | TypeScript (strict mode)                                                                                  |
| Node version       | LTS (22+)                                                                                                 |
| Backend URL        | `VITE_AGENT_URL` environment variable (default: `http://localhost:8090`)                                  |
| Repository         | `talk-ui` (separate git repo, integrated in VS Code workspace)                                            |
| Theme              | Dark only                                                                                                 |
| CopilotKit styling | Mixed approach: override default CopilotKit styles with targeted Tailwind CSS for non-headless components |

## 6. Scope — Out of V1

The following are explicitly excluded from this PRD:

- Authentication / authorization
- Docker / deployment / hosting
- Session sidebar / conversation history persistence (depends on backend Epic 3)
- User-initiated turn cancellation mid-stream (backend not ready)
- Dynamic model list from backend API (hardcoded in frontend)
- Light theme / theme switching
- Internationalization (i18n)
- E2E tests (Playwright) — may be added later
- Offline support / PWA

## 6.1 Production Readiness (Final Epic)

The last epic replaces CopilotKit's `agents__unsafe_dev_only` transport layer with a custom AG-UI SSE client built on the Fetch API. This removes the production licensing dependency on CopilotKit Enterprise while keeping all React UI components (MIT licensed). The custom client implements the same `AbstractAgent` interface so existing hooks and components continue to work unchanged.

## 7. Success Metrics

| Metric                                         | Target                                                      | Counter-metric                         |
| ---------------------------------------------- | ----------------------------------------------------------- | -------------------------------------- |
| All backend AG-UI features exercisable from UI | 100% (chat, streaming, reasoning, tools, interrupt, errors) | No feature requires curl/CLI to test   |
| Test coverage                                  | ≥ 80% (target 100%)                                         | No test takes > 5s                     |
| Lint                                           | 0 errors, 0 warnings                                        | No rule disabled without justification |
| Build time (dev)                               | < 3s hot reload                                             | —                                      |
| Time to first meaningful paint                 | < 1s (local, empty state)                                   | —                                      |

## 8. Integration Pattern (Verified)

CopilotKit is natively built on the AG-UI protocol. Connection to `talk serve` uses:

- `@ag-ui/client` → `HttpAgent({ url: VITE_AGENT_URL })` — handles POST + SSE natively
- `<CopilotKit agents__unsafe_dev_only={{ "talk": agent }}>` — local dev mode, no runtime needed
- `useAgent()` hook — exposes `.messages`, `.isRunning`, `.subscribe()` for all AG-UI events
- `CopilotChat` / headless components work directly against this agent

**Production note:** `selfManagedAgents` (the production equivalent) requires CopilotKit Enterprise Intelligence license. Out of scope for V1 (local only). Revisit when deploying.

## 9. Open Questions

- [TO VERIFY] Passing `forwardedProps` (model, thinkingEffort) through `HttpAgent` — likely via `runAgent()` options but needs confirmation during implementation.
- [CONFIRMED] TanStack Router is used even though V1 has a single route (`/`). Prepares for future multi-page navigation (sessions list, settings).
- [NOTE FOR PM] When backend Epic 3 (sessions) ships, the frontend will need a new epic for session management UI.
- [NOTE FOR PM] When deploying to production, evaluate CopilotKit Enterprise license vs. building a thin AG-UI SSE client directly.
