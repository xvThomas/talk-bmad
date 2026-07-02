---
stepsCompleted: [step-01, step-02, step-03]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-talk-bmad-2026-06-21/prd.md
  - _bmad-output/planning-artifacts/prds/prd-talk-frontend-2026-06-28/prd.md
  - _bmad-output/project-context.md
---

# AG-UI Protocol Server (talk serve) - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for the talk project (backend + frontend), decomposing the PRD requirements into implementable stories.

- **Epics 1–3:** Backend (`talk serve`) — AG-UI server, MCP tool execution, session persistence
- **Epics 4–7:** Frontend (`talk-ui`) — CopilotKit React app, chat UX, production transport

## Requirements Inventory

### Functional Requirements

- FR-1: Accept AG-UI POST requests (`POST /agent` with RunAgentInput JSON body)
- FR-2: Stream AG-UI response events (RUN_STARTED → TEXT_MESSAGE_START → TEXT_MESSAGE_CONTENT → TEXT_MESSAGE_END → RUN_FINISHED)
- FR-3: Handle client disconnection (cancel in-flight LLM/MCP calls, no goroutine leak)
- FR-4: Execute tool calls via MCP (loop up to 5 iterations, feed results back to LLM)
- FR-5: Emit tool call events (TOOL_CALL_START, TOOL_CALL_ARGS, TOOL_CALL_END)
- FR-5b: Emit error events on tool failure (human-readable AG-UI error events)
- FR-6: Create session on first request (backend generates UUID, returns in RUN_STARTED)
- FR-7: Resume existing session (load history, pass to LLM as context)
- FR-8: List sessions (GET /sessions with metadata)
- FR-9: Delete session (DELETE /sessions/{id})
- FR-10: Emit messages snapshot (MESSAGES_SNAPSHOT with full history including tool calls)
- FR-11: Load history for LLM context (all historical messages passed to LLM)
- FR-12: Read configuration from existing CLI store
- FR-13: Configurable server port (default 8090, SERVE_PORT env, --port flag)
- FR-14: Runtime error reporting via AG-UI (server always starts, errors as AG-UI events)
- FR-15: Model selection per request (frontend sends model alias via forwardedProps.model, mandatory)
- FR-16: Thinking/reasoning via forwardedProps (optional, emit REASONING\_\* AG-UI events when LLM produces thinking)

### Non-Functional Requirements

- NFR-1: Time-to-first-event < 500ms after POST received (excluding LLM latency)
- NFR-2: 100 simultaneous SSE connections without degradation
- NFR-3: An error on one request does not impact other active connections
- NFR-4: Full conformance with AG-UI event specification
- NFR-5: Code follows all project-context.md conventions (no CGO, stdlib net/http, wg.Go())
- NFR-6: HTTP handlers testable via httptest with no external dependencies
- NFR-7: Graceful shutdown: wait for active streams to complete, then exit
- NFR-8: Cross-origin requests accepted (CORS for independent React frontends)
- NFR-9: Request logging (duration, session ID, status) via talk-libs/logger
- NFR-10: Architecture supports auth middleware insertion without handler refactoring

### Additional Requirements

- Go 1.25, CGO_ENABLED=0, stdlib net/http only (Go 1.22+ ServeMux patterns)
- sync.WaitGroup.Go() for goroutine spawning (Go 1.25 pattern)
- Interfaces 1-3 methods max
- Pure-Go SQLite (modernc.org/sqlite) — no mattn/go-sqlite3
- Tests via httptest, no external test dependencies
- Docker multi-stage build with workspace root as build context

### FR Coverage Map

| FR     | Epic   | Description                                                           |
| ------ | ------ | --------------------------------------------------------------------- |
| FR-1   | Epic 1 | Accept AG-UI POST requests                                            |
| FR-2   | Epic 1 | Stream AG-UI response events                                          |
| FR-3   | Epic 1 | Handle client disconnection                                           |
| FR-6   | Epic 1 | Create session on first request                                       |
| FR-12  | Epic 1 | Read config from existing store                                       |
| FR-13  | Epic 1 | Configurable server port                                              |
| FR-14  | Epic 1 | Runtime error reporting via AG-UI                                     |
| FR-15  | Epic 1 | Model selection per request                                           |
| FR-16  | Epic 1 | Thinking/reasoning via AG-UI                                          |
| FR-4   | Epic 2 | Execute tool calls via MCP                                            |
| FR-5   | Epic 2 | Emit tool call events                                                 |
| FR-5b  | Epic 2 | Emit error events on tool failure                                     |
| NFR-11 | Epic 2 | Recover MCP sessions after transient network loss or host wake/resume |
| FR-7   | Epic 3 | Resume existing session                                               |
| FR-8   | Epic 3 | List sessions                                                         |
| FR-9   | Epic 3 | Delete session                                                        |
| FR-10  | Epic 3 | Emit messages snapshot                                                |
| FR-11  | Epic 3 | Load history for LLM context                                          |

## Epic List

### Epic 1: Conversation AG-UI de bout en bout

End clients can send a message from a CopilotKit frontend and receive an assistant response as an AG-UI SSE event stream.
**FRs covered:** FR-1, FR-2, FR-3, FR-6, FR-12, FR-13, FR-14, FR-15, FR-16

### Epic 2: Exécution d'outils MCP avec événements AG-UI

The assistant can call external tools (route calculation, weather) during a conversation and the frontend sees tool call progress.
**FRs covered:** FR-4, FR-5, FR-5b

### Epic 3: Sessions persistantes et historique

End clients can resume previous conversations, view history, and manage their sessions.
**FRs covered:** FR-7, FR-8, FR-9, FR-10, FR-11

---

## Epic 1: Conversation AG-UI de bout en bout

End clients can send a message from a CopilotKit frontend and receive an assistant response as an AG-UI SSE event stream. This epic delivers the core server infrastructure: the `talk serve` subcommand, HTTP handler, SSE encoding, session creation, configuration loading, error reporting, and graceful shutdown.

### Story 1.1: Commande `talk serve` et serveur HTTP minimal

As a platform operator,
I want to start an HTTP server with `talk serve`,
So that frontends can connect to the conversation engine.

**Acceptance Criteria:**

**Given** the `talk` binary is built
**When** the user runs `talk serve`
**Then** an HTTP server starts listening on port 8090
**And** the port is configurable via `--port` flag or `SERVE_PORT` env var
**And** the server responds to `OPTIONS` requests with CORS headers (Access-Control-Allow-Origin: \*)
**And** the server shuts down gracefully on SIGTERM/SIGINT (waits for active connections)
**And** startup is logged with port and config source info

### Story 1.2: Handler POST /agent avec réponse SSE AG-UI

As a frontend developer,
I want to send a POST request to `/agent` and receive an SSE event stream,
So that my CopilotKit frontend can communicate with the assistant.

**Acceptance Criteria:**

**Given** the server is running
**When** a valid `POST /agent` request is received with a JSON body containing `messages`
**Then** the response has `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`
**And** the event sequence is: `RUN_STARTED` → `TEXT_MESSAGE_START` → `TEXT_MESSAGE_CONTENT` → `TEXT_MESSAGE_END` → `RUN_FINISHED`
**And** `RUN_STARTED` includes a backend-generated `threadId` (UUID)
**And** `TEXT_MESSAGE_CONTENT` contains the full LLM response in a `delta` field
**And** events are flushed immediately (not buffered)

**Given** a request with malformed JSON
**When** it reaches `/agent`
**Then** HTTP 400 is returned with a JSON error body

**Given** a non-POST request to `/agent`
**When** it reaches the server
**Then** HTTP 405 is returned

### Story 1.3: Intégration ConversationManager et config existante

As a platform operator,
I want the server to use the same infrastructure configuration (API keys, system prompt, MCP servers) as the CLI,
So that I don't need to configure the agent twice.

**Acceptance Criteria:**

**Given** the talk CLI has been configured (LLM API keys, system prompt, MCP servers)
**When** `talk serve` starts
**Then** it reads the configuration from the same store as the CLI
**And** the system prompt is applied to all conversations
**And** all configured LLM API keys are available for model resolution

**Given** the frontend sends a valid model alias in `forwardedProps.model` (e.g., "sonnet-4.6")
**When** a `POST /agent` request is processed
**Then** the server resolves the alias against the `domain.Models` registry
**And** the corresponding LLM provider and API model ID are used for that request

**Given** the frontend does not send `forwardedProps.model` or sends an empty value
**When** a `POST /agent` request arrives
**Then** an AG-UI error event is emitted listing available models

**Given** the frontend sends an unknown model alias
**When** a `POST /agent` request arrives
**Then** an AG-UI error event is emitted with a message listing the valid model aliases

**Given** the configuration is incomplete (no API key or no system prompt)
**When** a `POST /agent` request arrives
**Then** an AG-UI error event is emitted with a user-facing message (e.g., "L'assistant n'est pas configuré correctement. Contactez l'administrateur.")
**And** an ERROR-level log is written with technical details

**Given** the database is unreachable
**When** a `POST /agent` request arrives
**Then** an AG-UI error event is emitted with message "Service temporairement indisponible, veuillez réessayer."
**And** an ERROR-level log is written

### Story 1.4: Annulation sur déconnexion client

As a frontend developer,
I want the server to cancel processing if I disconnect,
So that server resources are freed immediately.

**Acceptance Criteria:**

**Given** a `POST /agent` request is being processed (LLM call in flight)
**When** the client closes the connection
**Then** the server detects disconnection via `r.Context().Done()`
**And** the in-flight LLM call is cancelled
**And** no partial result is persisted to the session store
**And** no goroutine leak occurs (verifiable via test)

### Story 1.5: Thinking/Reasoning via AG-UI

As a frontend developer,
I want to optionally activate LLM thinking/reasoning via `forwardedProps.thinkingEffort` and receive the thinking output as AG-UI `REASONING_*` events,
So that my UI can display the model's chain-of-thought to the user.

**Acceptance Criteria:**

**Given** a `POST /agent` request with `forwardedProps.thinkingEffort` set to `"low"`, `"medium"`, or `"high"`
**When** the LLM supports thinking
**Then** reasoning is activated for that request with the corresponding effort level
**And** the thinking output is emitted as AG-UI `REASONING_*` events before `TEXT_MESSAGE_*` events
**And** the event sequence is: `REASONING_START` → `REASONING_MESSAGE_START` → `REASONING_MESSAGE_CONTENT` → `REASONING_MESSAGE_END` → `REASONING_END` → `TEXT_MESSAGE_START` → ...

**Given** a `POST /agent` request without `forwardedProps.thinkingEffort` (or set to `"off"` or empty)
**When** the request is processed
**Then** thinking is not activated (backward compatible, same behavior as today)

**Given** a `POST /agent` request with an invalid `thinkingEffort` value
**When** the request is processed
**Then** the value is ignored and thinking defaults to off (no error emitted)

**Given** the tool loop executes multiple LLM calls with thinking active
**When** each intermediate LLM call returns thinking content
**Then** reasoning events are emitted for each iteration (before the tool call events of the next iteration)

---

## Epic 2: Exécution d'outils MCP avec événements AG-UI

The assistant can call external tools (route calculation, weather) during a conversation and the frontend sees tool call progress. This builds on Epic 1's conversation flow to add the tool execution loop with AG-UI event emission and error handling.

### Story 2.1: Boucle d'exécution d'outils MCP

As an end client,
I want the assistant to call external tools (route calculation, weather) during a conversation,
So that I get answers that require real-time data or computation.

**Acceptance Criteria:**

**Given** the server is configured with one or more MCP servers
**When** the LLM response contains tool call requests
**Then** the server executes tool calls against the configured MCP server(s)
**And** tool results are fed back to the LLM as context for the next completion
**And** the loop iterates until the LLM produces a final text response (max 5 iterations)
**And** the final text response is emitted as `TEXT_MESSAGE_START` → `TEXT_MESSAGE_CONTENT` → `TEXT_MESSAGE_END`

**Given** the tool loop reaches 5 iterations without a final text response
**When** the limit is hit
**Then** an AG-UI error event is emitted with a user-facing message (e.g., "J'ai atteint la limite d'appels d'outils sans pouvoir finaliser. Essayez de reformuler votre question de manière plus spécifique.")
**And** all intermediate messages (tool calls + results) are persisted in the session

### Story 2.5: Résilience des connexions MCP après perte de réseau

As a platform operator,
I want the backend to recover MCP tool connections automatically after a transient network interruption or when the host wakes from sleep,
So that MCP tool calls continue to work without restarting `talk serve`.

**Acceptance Criteria:**

**Given** a previously connected MCP server session is lost after host sleep or transient network loss
**When** the next tool call is attempted
**Then** the backend detects the invalid MCP session and attempts to reconnect it automatically
**And** the tool call is retried once after reconnecting successfully

**Given** reconnection succeeds
**When** the tool call is retried
**Then** the user-facing conversation continues normally and the frontend receives the expected AG-UI tool and text events

**Given** reconnection fails after retry
**When** the session cannot be restored
**Then** the frontend receives an AG-UI error event explaining that MCP tool execution is unavailable for this server
**And** the backend logs the reconnect failure with server identity and error details

**Given** other requests are in flight during MCP reconnect
**When** reconnect attempts are ongoing
**Then** those other requests are not blocked by the reconnection logic

### Story 2.4: Reprise de conversation après limite d'itérations (future)

As an end client,
I want to send "continue" after the assistant hit the tool iteration limit,
So that the assistant can resume its work with full context of prior tool calls.

**Acceptance Criteria:**

**Given** a previous request hit the 5-iteration limit on a session
**When** the user sends a follow-up message with the same `threadId`
**Then** the LLM receives the full detailed context of prior tool calls and results (not just a Q/A summary)
**And** this works regardless of the `CONTEXT_FULL_TURNS` configuration mode (lean, hybrid, full)

**Design note:** In lean mode (default), `BuildContextMessages` only includes detailed messages for the current turn and summarizes older turns. A turn that hit max-iterations must be force-included in detail for the resume mechanism to work. This requires either a `needs-continuation` flag on the turn or automatic context mode elevation.

**Dependencies:** Story 2.1 (sentinel error and persistence)
**Status:** not-started

---

### Story 2.2: Émission des événements tool call AG-UI

As a frontend developer,
I want to receive AG-UI tool call events during execution,
So that my UI can show the user what tools are being used (loading indicators, tool names).

**Acceptance Criteria:**

**Given** the LLM requests a tool call
**When** the server begins tool execution
**Then** a `TOOL_CALL_START` event is emitted with the tool name and call ID
**And** a `TOOL_CALL_ARGS` event is emitted with the serialized tool input arguments
**And** after execution, a `TOOL_CALL_END` event is emitted with the tool result
**And** all events are flushed immediately to the SSE stream (no buffering)

**Given** the LLM requests multiple tool calls in one iteration
**When** tools are executed
**Then** each tool call produces its own START/ARGS/END event triplet

### Story 2.3: Gestion des erreurs MCP avec AG-UI error events

As an end client,
I want to see a clear error message when a tool fails,
So that I understand what happened and can retry or rephrase my request.

**Acceptance Criteria:**

**Given** the server attempts to call an MCP tool
**When** the MCP server is unreachable (connection refused, timeout)
**Then** an AG-UI error event is emitted with a human-readable message (e.g., "Impossible de contacter le service de navigation. Veuillez réessayer.")
**And** the error does not terminate the SSE stream
**And** the LLM is informed of the failure and may produce a text response explaining the issue

**Given** the MCP server returns a tool error
**When** the error is received
**Then** an AG-UI error event is emitted with the tool's error description
**And** an ERROR-level log is written with the full technical details (MCP server URL, tool name, error)

---

## Epic 3: Sessions persistantes et historique

End clients can resume previous conversations, view history, and manage their sessions. This builds on the session creation from Epic 1 to add full session lifecycle management and history replay.

### Story 3.1: Reprise de session avec historique LLM

As an end client,
I want to continue a previous conversation where I left off,
So that I don't have to re-explain my context.

**Acceptance Criteria:**

**Given** a session exists with previous messages (user, assistant, tool calls, tool results)
**When** a `POST /agent` request is received with the existing `threadId`
**Then** the full message history is loaded and passed to the LLM as conversation context
**And** the LLM responds with awareness of the prior conversation
**And** new messages are appended to the existing session

**Given** a `POST /agent` request with an unknown `threadId`
**When** the server processes it
**Then** a new session is created with that `threadId` (treated as first request)

### Story 3.2: MESSAGES_SNAPSHOT pour le frontend

As a frontend developer,
I want to receive the conversation history when resuming a session,
So that my UI can display previous messages immediately.

**Acceptance Criteria:**

**Given** a `POST /agent` request with an existing `threadId` that has message history
**When** the SSE stream begins
**Then** a `MESSAGES_SNAPSHOT` event is emitted after `RUN_STARTED` and before `TEXT_MESSAGE_START`
**And** the snapshot contains all prior messages in chronological order (user, assistant, tool calls, tool results)

**Given** a `POST /agent` request for a new session (no history)
**When** the SSE stream begins
**Then** no `MESSAGES_SNAPSHOT` event is emitted

### Story 3.3: Lister et supprimer des sessions

As an end client,
I want to see my previous conversations and delete those I no longer need,
So that I can organize my conversation history.

**Acceptance Criteria:**

**Given** sessions exist in the store
**When** a `GET /sessions` request is received
**Then** a JSON array is returned with session metadata (ID, creation date, last message date, message count)
**And** sessions are ordered by last activity (most recent first)

**Given** no sessions exist
**When** a `GET /sessions` request is received
**Then** an empty JSON array is returned (not an error)

**Given** a valid session ID
**When** a `DELETE /sessions/{id}` request is received
**Then** the session and all its messages are removed from the store
**And** HTTP 204 is returned

**Given** an unknown session ID
**When** a `DELETE /sessions/{id}` request is received
**Then** HTTP 404 is returned

**Given** a deleted session's `threadId`
**When** a subsequent `POST /agent` arrives with that `threadId`
**Then** a new session is created (fresh start)

---

---

## Frontend Requirements Inventory (talk-ui)

### Functional Requirements

- UI-FR-1: Send message + streaming response
- UI-FR-2: Vertical message list (user right, assistant left)
- UI-FR-3: Centered empty state → scroll layout with fixed input
- UI-FR-4: Auto-scroll + pause on user scroll-up
- UI-FR-5: Model selector integrated in input area
- UI-FR-6: Thinking effort selector (conditional on model)
- UI-FR-7: forwardedProps transmission (model, thinkingEffort)
- UI-FR-8: Reasoning display (always visible)
- UI-FR-9: Reasoning visually distinct from response
- UI-FR-10: Tool call display in message flow
- UI-FR-11: Tool messages collapsed (name + chevron), expandable
- UI-FR-12: Multiple tool calls as separate items
- UI-FR-13: Interrupt "Continue" button inline
- UI-FR-14: Resume request with status resolved
- UI-FR-15: New message ≠ resume
- UI-FR-16: Send button
- UI-FR-17: Cancel button (replaces send during streaming)
- UI-FR-18: Cancel → partial response disappears, question stays with Retry button
- UI-FR-19: Error display inline with distinctive style
- UI-FR-20: Errors non-blocking (user can continue)
- UI-FR-21: Activity indicator (discrete, elegant)
- UI-FR-22: Tool in-progress indicator
- UI-FR-23: README.md (pnpm-based getting started)
- UI-FR-24: README updated each story
- UI-FR-25: Markdown rendering for assistant messages (headings, lists, code blocks with syntax highlighting)

### Frontend FR Coverage Map

| FR       | Epic   | Description                       |
| -------- | ------ | --------------------------------- |
| UI-FR-1  | Epic 4 | Send message + streaming response |
| UI-FR-2  | Epic 4 | Vertical message list layout      |
| UI-FR-3  | Epic 4 | Centered → scroll layout          |
| UI-FR-4  | Epic 4 | Auto-scroll + pause               |
| UI-FR-5  | Epic 5 | Model selector                    |
| UI-FR-6  | Epic 5 | Thinking effort selector          |
| UI-FR-7  | Epic 5 | forwardedProps transmission       |
| UI-FR-8  | Epic 5 | Reasoning display                 |
| UI-FR-9  | Epic 5 | Reasoning visual distinction      |
| UI-FR-10 | Epic 6 | Tool call display                 |
| UI-FR-11 | Epic 6 | Tool collapse/expand              |
| UI-FR-12 | Epic 6 | Multiple tool calls               |
| UI-FR-13 | Epic 6 | Interrupt "Continue" button       |
| UI-FR-14 | Epic 6 | Resume request                    |
| UI-FR-15 | Epic 6 | New message ≠ resume              |
| UI-FR-16 | Epic 4 | Send button                       |
| UI-FR-17 | Epic 6 | Cancel button                     |
| UI-FR-18 | Epic 6 | Cancel behavior + Retry           |
| UI-FR-19 | Epic 6 | Error display                     |
| UI-FR-20 | Epic 6 | Errors non-blocking               |
| UI-FR-21 | Epic 4 | Activity indicator                |
| UI-FR-22 | Epic 6 | Tool in-progress indicator        |
| UI-FR-23 | Epic 4 | README                            |
| UI-FR-24 | All    | README updated each story         |
| UI-FR-25 | Epic 4 | Markdown rendering (assistant)    |

### Frontend Epic List

### Epic 4: Conversation de base fonctionnelle (talk-ui)

L'utilisateur peut ouvrir l'app web, envoyer un message et recevoir une réponse en streaming.
**FRs covered:** UI-FR-1, UI-FR-2, UI-FR-3, UI-FR-4, UI-FR-16, UI-FR-21, UI-FR-23, UI-FR-25

### Epic 5: Contrôle du modèle et du raisonnement

L'utilisateur peut choisir son modèle LLM et activer le mode thinking, et voir le raisonnement du modèle.
**FRs covered:** UI-FR-5, UI-FR-6, UI-FR-7, UI-FR-8, UI-FR-9

### Epic 6: Interactions avancées (tools, interrupts, erreurs, cancel)

L'utilisateur voit les tool calls, peut continuer après un interrupt, annuler un streaming, et comprend les erreurs.
**FRs covered:** UI-FR-10, UI-FR-11, UI-FR-12, UI-FR-13, UI-FR-14, UI-FR-15, UI-FR-17, UI-FR-18, UI-FR-19, UI-FR-20, UI-FR-22

### Epic 7: Client SSE AG-UI custom (production-ready)

L'app utilise son propre client SSE au lieu de `agents__unsafe_dev_only`, supprimant la dépendance à la licence CopilotKit Enterprise.
**FRs covered:** Production architecture (no new user-facing FRs)

---

## Epic 4: Conversation de base fonctionnelle (talk-ui)

L'utilisateur peut ouvrir l'app web, envoyer un message et recevoir une réponse en streaming. Inclut le scaffold projet, la CI, la connexion AG-UI, le chat layout, et le streaming.

### Story 4.1: Scaffold projet et CI

As a developer,
I want a working project scaffold with Vite, React, TypeScript, Tailwind, TanStack Router, pnpm, and CI,
So that I have a solid foundation to build features on.

**Acceptance Criteria:**

**Given** a fresh clone of the `talk-ui` repo
**When** I run `pnpm install && pnpm build`
**Then** the project compiles without errors
**And** TypeScript strict mode is enabled
**And** ESLint flat config with `typescript-eslint/strict` + React plugin is configured
**And** Prettier is configured and consistent with ESLint
**And** `pnpm lint`, `pnpm lint:fix`, `pnpm format`, `pnpm format:fix` scripts work
**And** Vitest + Testing Library are configured with a passing placeholder test
**And** TanStack Router is set up with a single route (`/`)
**And** Tailwind is configured with dark theme only
**And** a GitHub Actions workflow runs build + lint + test on push/PR
**And** a `README.md` documents: prerequisites (Node 22+, pnpm), install, build, dev, lint, test

### Story 4.2: Connexion CopilotKit + AG-UI backend

As a developer,
I want the app to connect to the `talk serve` backend via CopilotKit's AG-UI integration,
So that messages can flow between frontend and backend.

**Acceptance Criteria:**

**Given** the app is running with `VITE_AGENT_URL=http://localhost:8090`
**When** the CopilotKit provider is initialized
**Then** an `HttpAgent` is created pointing at the configured URL
**And** it is registered via `agents__unsafe_dev_only`
**And** the agent URL is validated with a Zod schema at startup
**And** the connection configuration is typed (no `any`)

### Story 4.3: Chat layout et envoi de message

As an end user,
I want to see a chat interface and send a message,
So that I can converse with the assistant.

**Acceptance Criteria:**

**Given** the app is loaded with no messages
**When** the page renders
**Then** the chat input is centered horizontally and vertically (empty state)

**Given** the user types a message and clicks Send (or presses Enter)
**When** the message is submitted
**Then** the user's message appears right-aligned in the conversation
**And** the input is cleared
**And** a discrete activity indicator is shown (assistant is working)

**Given** messages exist in the conversation
**When** the layout renders
**Then** messages scroll vertically downward
**And** the input is fixed at the bottom, centered horizontally

### Story 4.4: Streaming message et auto-scroll

As an end user,
I want to see the assistant's response appear progressively,
So that I know the assistant is actively responding.

**Acceptance Criteria:**

**Given** the backend is streaming a response (TEXT_MESSAGE_CONTENT events)
**When** content arrives
**Then** the assistant's message bubble grows progressively (message-level streaming)
**And** the assistant's message is left-aligned
**And** auto-scroll keeps the latest content visible

**Given** the user scrolls up during streaming
**When** new content arrives
**Then** auto-scroll is paused (user stays at their scroll position)

**Given** the user scrolls back to the bottom
**When** new content arrives
**Then** auto-scroll resumes

### Story 4.5: Rendu markdown des messages assistant

As an end user,
I want the assistant's messages to be rendered as rich markdown,
So that headings, lists, code blocks, and other formatting are readable and visually structured.

**Acceptance Criteria:**

**Given** the assistant sends a response containing markdown syntax (headings, bold, italic, lists, links, inline code, fenced code blocks)
**When** the message is displayed
**Then** it is rendered as rich HTML — not raw markdown text
**And** fenced code blocks include syntax highlighting (language-aware)
**And** links are clickable and open in a new tab (`target="_blank"`, `rel="noopener noreferrer"`)

**Given** the assistant's response is streaming
**When** partial markdown arrives (e.g., an incomplete code block)
**Then** the rendering updates progressively without visual glitches
**And** incomplete blocks are displayed as plain text until the closing fence arrives

**Given** the message contains no markdown
**When** the message is displayed
**Then** it renders as plain text (no blank wrapper elements)

**Technical notes:**

- Use `react-markdown` with `remark-gfm` (tables, strikethrough, task lists) and `rehype-highlight` (syntax highlighting)
- Apply Tailwind `prose` class (`@tailwindcss/typography`) for consistent markdown styling in dark theme
- The same renderer should be reusable for reasoning blocks (Epic 5) and tool result display (Epic 6)

---

## Epic 5: Contrôle du modèle et du raisonnement

L'utilisateur peut choisir son modèle LLM, activer le mode thinking, et voir le raisonnement du modèle affiché dans la conversation.

### Story 5.1: Sélection du modèle LLM

As an end user,
I want to choose which LLM model responds to my messages,
So that I can pick the best model for my needs (speed, quality, cost).

**Acceptance Criteria:**

**Given** the chat input area is rendered
**When** the user sees the model selector
**Then** a dropdown/select is displayed integrated in the input area (not in a settings page)
**And** the available models are: `haiku-4.5`, `sonnet-4.6`, `opus-4.6`, `o4-mini`, `gpt-5.4`, `mistral-small`, `agent`
**And** the model list is defined as a typed constant validated by Zod
**And** a default model is pre-selected (`sonnet-4.6`)

**Given** the user selects a model
**When** they send a message
**Then** `forwardedProps.model` is set to the selected alias in the AG-UI request

**Given** a model is selected
**When** a response is streaming
**Then** the selector is disabled (cannot change model mid-stream)

### Story 5.2: Sélection du thinking effort

As an end user,
I want to control the thinking/reasoning effort when the model supports it,
So that I can decide between faster responses or deeper reasoning.

**Acceptance Criteria:**

**Given** the selected model supports thinking (`haiku-4.5`, `sonnet-4.6`, `opus-4.6`, `o4-mini`)
**When** the input area renders
**Then** a thinking effort selector is visible with options: `off`, `low`, `medium`, `high`
**And** the default is `off`

**Given** the selected model does NOT support thinking (`gpt-5.4`, `mistral-small`, `agent`)
**When** the input area renders
**Then** the thinking effort selector is hidden

**Given** a thinking effort is selected
**When** the user sends a message
**Then** `forwardedProps.thinkingEffort` is set to the selected value

**Given** the user switches to a non-thinking model
**When** the model changes
**Then** the thinking selector disappears
**And** `forwardedProps.thinkingEffort` is omitted from the next request

### Story 5.3: Affichage du raisonnement

As an end user,
I want to see the model's reasoning/thinking when it is produced,
So that I understand how the assistant arrived at its answer.

**Acceptance Criteria:**

**Given** the backend emits `REASONING_*` events during a response
**When** reasoning content is received
**Then** it is displayed above the assistant's text response
**And** it is always visible (not collapsed)
**And** it is visually distinct from the final response (muted color, italic, or bordered block)

**Given** a response has no reasoning events
**When** the assistant responds
**Then** no reasoning block is shown (only the text response)

**Given** multiple LLM iterations (tool loop) each produce reasoning
**When** reasoning arrives for each iteration
**Then** each reasoning block is displayed in order above the final text

---

## Epic 6: Interactions avancées (tools, interrupts, erreurs, cancel)

L'utilisateur voit les tool calls en cours, peut continuer après un interrupt max-iterations, annuler un streaming en cours, et comprend les erreurs affichées dans le fil de conversation.

### Story 6.1: Affichage des tool calls (collapse/expand)

As an end user,
I want to see which tools the assistant uses during a conversation,
So that I understand what external actions are being performed on my behalf.

**Acceptance Criteria:**

**Given** the backend emits `TOOL_CALL_START` / `TOOL_CALL_ARGS` / `TOOL_CALL_END` events
**When** a tool call is in progress
**Then** a tool item appears in the message flow with an in-progress indicator

**Given** a tool call completes (`TOOL_CALL_END`)
**When** it renders
**Then** the item shows the tool name + a chevron, collapsed by default

**Given** the user clicks on a collapsed tool item
**When** it expands
**Then** the arguments and result are displayed
**And** clicking again collapses it

**Given** multiple tool calls occur in one turn
**When** they render
**Then** each tool call is a separate collapsible item in sequence

### Story 6.1.5: Façade UI context (séparation CopilotKit / présentation)

As a developer,
I want a dedicated React UI context between CopilotKit hooks and presentation components,
So that the UI layer is decoupled, easier to test, and safer to evolve during Epic 6.

**Acceptance Criteria:**

**Given** the chat UI reads conversation state
**When** `ChatView` renders
**Then** presentation components consume a dedicated UI context/view-model instead of directly reading CopilotKit internals
**And** no functional behavior changes for end users

**Given** tool calls, reasoning, errors, and activity states
**When** events flow through the app
**Then** the UI context exposes normalized state for presentation components
**And** Story 6.1, 6.2, 6.3, and 6.4 behaviors remain unchanged

**Given** tests for chat rendering
**When** the refactor is complete
**Then** existing tests continue to pass
**And** new tests cover context provider behavior and view-model contract

**Given** future migration away from `HttpAgent`
**When** the transport implementation changes in Epic 7
**Then** presentation components require minimal or no changes thanks to the UI context boundary

**Given** a tool call has started and no final assistant message has been emitted yet
**When** the UI receives tool-call events
**Then** the corresponding tool item is rendered immediately in the conversation
**And** the item is expandable/clickable while still in progress
**And** partial args/result content is visible as soon as available

**Given** tool-call events arrive before the final assistant completion event
**When** state is reconciled in the UI context
**Then** rendering does not wait for final assistant completion to expose tool details
**And** final assistant completion only transitions run status, without gating tool item interactivity

**Given** a user wants to reduce visual noise in the conversation flow
**When** they toggle the Tools selector from `Show` to `Hide`
**Then** `tool-call` rows are hidden from the message list
**And** non-tool messages remain visible and unchanged

**Given** tool rows are hidden via the Tools selector
**When** the user toggles back to `Show`
**Then** tool rows are rendered again immediately using current normalized state
**And** no new backend request is triggered by this display toggle

### Story 6.2: Interrupt max-iterations et bouton Continue

As an end user,
I want to see a "Continue" option when the assistant hits its tool call limit,
So that I can let it resume working without starting over.

**Acceptance Criteria:**

**Given** the backend emits a `RUN_FINISHED` event with outcome type `interrupt` and reason `talk:max_iterations`
**When** the event is received
**Then** an inline message is displayed in the conversation explaining the limit was reached
**And** a "Continue" button is shown below the message

**Given** the user clicks "Continue"
**When** the resume request is sent
**Then** it includes status `resolved` and the original `threadId`
**And** the assistant continues processing (new streaming response begins)
**And** the "Continue" button disappears

**Given** the user types and sends a new message instead of clicking "Continue"
**When** the message is submitted
**Then** it is treated as a new question (standard flow, not a resume)
**And** the "Continue" button remains visible but becomes inactive/dimmed

### Story 6.3: Annulation de streaming et bouton Retry

As an end user,
I want to cancel a response in progress and easily retry my question,
So that I'm not stuck waiting for a response I no longer want.

**Acceptance Criteria:**

**Given** the assistant is streaming a response
**When** the user looks at the input area
**Then** the Send button has transformed into a Cancel button

**Given** the user clicks Cancel
**When** the stream is interrupted
**Then** the SSE connection is closed (client-side disconnection)
**And** the partial assistant response disappears
**And** the user's question remains in the conversation with a "Retry" button

**Given** the user clicks "Retry"
**When** the action triggers
**Then** the question text is copied back into the chat input
**And** the user can edit and re-submit (or submit as-is)

**Given** a response completes normally
**When** streaming finishes
**Then** the Cancel button reverts to Send

### Story 6.4: Affichage des erreurs inline

As an end user,
I want to see error messages clearly in the conversation flow,
So that I understand what went wrong and know I can continue.

**Acceptance Criteria:**

**Given** the backend emits a `RUN_ERROR` event
**When** it is received
**Then** the error message is displayed inline in the conversation flow
**And** it has a distinctive error style (red/orange accent, error icon)
**And** it is visually different from normal assistant messages

**Given** an error was displayed
**When** the user wants to continue
**Then** the chat input is still active (errors don't block new messages)
**And** the Send button is in its normal state

---

## Epic 7: Client SSE AG-UI custom (production-ready)

L'app utilise son propre client SSE au lieu de `agents__unsafe_dev_only`, supprimant la dépendance à la licence CopilotKit Enterprise pour le déploiement production.

### Story 7.1: Client SSE Fetch avec parsing d'événements AG-UI

As a developer,
I want a custom SSE client that connects to the backend and parses AG-UI events,
So that the app no longer depends on CopilotKit's `HttpAgent` for transport.

**Acceptance Criteria:**

**Given** the client is instantiated with a backend URL
**When** a message is sent (POST with `RunAgentInput` body)
**Then** the client opens an SSE stream via `fetch` with `Content-Type: text/event-stream` response
**And** each SSE `data:` line is parsed into a typed AG-UI event
**And** all event types are validated against Zod schemas (RUN*STARTED, TEXT_MESSAGE*_, TOOL*CALL*_, REASONING\_\*, RUN_FINISHED, RUN_ERROR)
**And** malformed events are logged and skipped (no crash)
**And** the client supports cancellation via `AbortController`

**Given** the backend closes the stream
**When** the SSE connection ends
**Then** the client emits a completion signal

**Given** a network error occurs
**When** the fetch fails
**Then** a typed error is propagated to the consumer

### Story 7.2: Implémentation de l'interface AbstractAgent

As a developer,
I want the custom SSE client to implement the same interface used by CopilotKit components,
So that existing hooks and UI components work unchanged after the swap.

**Acceptance Criteria:**

**Given** the custom agent implements the `AbstractAgent`-compatible interface
**When** it replaces `HttpAgent` in the CopilotKit provider
**Then** `useAgent()` returns the custom agent with `.messages`, `.isRunning`, `.subscribe()` working
**And** `CopilotChat` (or custom chat components) function identically
**And** `forwardedProps` (model, thinkingEffort) are passed in the POST body

**Given** the swap is complete
**When** `agents__unsafe_dev_only` is removed from the provider
**Then** the app functions without any CopilotKit Enterprise dependency
**And** all existing features (streaming, reasoning, tools, interrupts, cancel, errors) pass their tests

### Story 7.3: Tests unitaires du client et migration

As a developer,
I want the custom SSE client to be thoroughly tested,
So that I'm confident it handles all AG-UI event flows correctly.

**Acceptance Criteria:**

**Given** the test suite for the SSE client
**When** tests run
**Then** coverage is ≥ 80% (target 100%) on the client module
**And** tests cover: happy path (full conversation), cancellation, network error, malformed event, interrupt flow, multiple tool calls

**Given** the migration from `HttpAgent` to custom client is complete
**When** the full app test suite runs
**Then** all existing tests pass without modification (interface-compatible swap)
**And** `@ag-ui/client` is removed from dependencies (or only type imports remain)
**And** README is updated to reflect the production-ready transport

### Story 7.4: Persistance conversation côté client (post-migration)

As a user,
I want my in-progress conversation and key UI state to survive hot reload and page refresh,
So that I can continue my flow without losing context during development and local usage.

**Acceptance Criteria:**

**Given** a conversation with messages and UI state (expanded tools, pending interrupt context)
**When** the page hot-reloads or refreshes
**Then** the app restores the latest persisted state from client storage
**And** the chat remains usable without manual reconstruction

**Given** persisted data is invalid, outdated, or corrupted
**When** the app starts
**Then** it safely falls back to a clean state without crashing
**And** logs a recoverable warning in development mode

**Given** the custom SSE client is active (Epic 7 complete)
**When** persistence is implemented
**Then** persistence hooks into the app-level UI context/store (not transport-specific internals)
**And** the implementation remains transport-agnostic for future evolution
