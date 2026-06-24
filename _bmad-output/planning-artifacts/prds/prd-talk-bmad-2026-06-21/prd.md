---
title: "AG-UI Protocol Server (talk serve)"
status: approved
created: 2026-06-21
updated: 2026-06-24
---

# PRD: AG-UI Protocol Server (`talk serve`)

## 0. Document Purpose

This PRD defines the requirements for adding an AG-UI protocol server to the existing `talk` CLI application. It targets the development team (single developer) and downstream workflow owners (epic/story creation, architecture decisions). The document builds on the technical research completed on 2026-06-20 (`planning-artifacts/research/technical-ag-ui-protocol-server-go-research-2026-06-20.md`) and the project conventions in `project-context.md`.

## 1. Vision

The `talk` conversation engine currently operates exclusively through a terminal CLI. While effective for developer workflows, this limits its reach to technical users comfortable with a command line. End clients — who need conversational access to domain-specific tools (route calculation, weather, cartographic data) — require a web interface.

`talk serve` exposes the existing conversation engine as an HTTP server implementing the AG-UI protocol. This enables independent React frontends to connect via standard CopilotKit components, requiring minimal frontend code to deliver full conversational AI capabilities. Each frontend focuses entirely on its domain-specific UI (maps, charts, dashboards) while delegating all LLM interaction to pre-built AG-UI components.

The architecture is deliberately simple: one `talk serve` instance = one pre-configured agent. Multiple specialized frontends are served by multiple instances, each with its own system prompt and MCP tool set. No multi-tenant routing, no agent selection logic — just a clean, single-purpose server per use case.

## 2. Target User

### 2.1 Jobs To Be Done

- **End client (non-technical):** I want to interact with an AI assistant through a web interface to get answers that require specialized tools (route calculation, weather data, geographic information) without needing to install anything or use a terminal.
- **Frontend developer:** I want to build domain-specific web UIs that have conversational AI built-in, without implementing LLM integration, tool execution, or session management myself.
- **Platform operator (the developer):** I want to deploy specialized AI agents as standalone services, each independently configurable, using the same battle-tested conversation engine underneath.

### 2.2 Non-Users (v1)

- Users who need an admin/configuration web UI (v1 uses existing CLI for configuration)
- Users who need token-level streaming for perceived latency optimization

### 2.3 Key User Journeys

- **UJ-1. End client calculates a route via chat.**
  - **Persona + context:** Marie, field technician, needs to plan an intervention route from her office browser.
  - **Entry state:** Authenticated (future), opens the navigation frontend app.
  - **Path:** Types "Itinéraire de Paris Gare de Lyon à Marseille Saint-Charles en évitant les péages" → sees a thinking indicator → receives a text response with route details (distance, duration, steps) produced by the LLM calling the IGN navigation MCP tool.
  - **Climax:** The route information appears in the chat, formatted and actionable.
  - **Resolution:** Marie can ask follow-up questions ("et sans autoroute ?") in the same session, with full conversational context preserved.

- **UJ-2. End client resumes a previous conversation.**
  - **Persona + context:** Marie returns the next day to refine yesterday's route.
  - **Entry state:** Opens the app, selects a previous session from the session list.
  - **Path:** The chat loads with previous messages visible → she types a follow-up question → the LLM responds with full context of the prior conversation.
  - **Climax:** Seamless continuation without re-explaining the context.
  - **Resolution:** The session history grows naturally across multiple visits.

## 3. Glossary

- **AG-UI** — Agent-User Interaction protocol. Open-source event-based protocol for agent↔frontend communication over SSE. Transport: POST request → SSE event stream.
- **RunAgentInput** — The JSON body sent by the frontend in the POST request. Contains `threadId` (session ID), `messages` (new user messages), and metadata.
- **SSE** — Server-Sent Events. Unidirectional server→client streaming over HTTP. Events formatted as `data: {json}\n\n`.
- **CopilotKit** — React component library that implements the AG-UI client protocol. Provides `HttpAgent` class and pre-built chat UI components.
- **MCP** — Model Context Protocol. Protocol for LLM↔tool communication. MCP servers expose tools the LLM can invoke.
- **Session** — A conversation thread identified by a unique `threadId`. Contains ordered messages and persists across requests.
- **Agent configuration** — The combination of system prompt + MCP server URLs + LLM API keys that defines an agent's capabilities. Set at server startup, static for the lifetime of the instance. Does not include model selection, which is a per-request choice.
- **ConversationManager** — Existing internal component that orchestrates multi-turn conversations (LLM calls, tool execution loops, message storage).

## 4. Features

### 4.1 Conversation via AG-UI Protocol

**Description:** The server accepts AG-UI-conformant POST requests and returns SSE streams containing the full conversation response. The existing `ConversationManager` handles the LLM interaction, and the server translates the result into AG-UI events. Realizes UJ-1.

**Functional Requirements:**

#### FR-1: Accept AG-UI requests

The server accepts a `POST /agent` request with a JSON body conforming to `RunAgentInput` (AG-UI protocol).

**Consequences (testable):**

- Server returns HTTP 200 with `Content-Type: text/event-stream` for valid requests.
- Server returns HTTP 400 for malformed JSON or missing required fields.
- Server returns HTTP 405 for non-POST methods on `/agent`.

#### FR-2: Stream AG-UI response events

The server emits the AG-UI event sequence: `RUN_STARTED` → `TEXT_MESSAGE_START` → `TEXT_MESSAGE_CONTENT` → `TEXT_MESSAGE_END` → `RUN_FINISHED`.

**Consequences (testable):**

- Every successful response contains exactly this event sequence in order.
- `TEXT_MESSAGE_CONTENT` contains the full LLM response text in a single `delta` field.
- All events include a valid `type` field matching the AG-UI event type enum.

#### FR-3: Handle client disconnection

If the client disconnects during processing, the server cancels the in-flight LLM call and MCP tool executions.

**Consequences (testable):**

- Server detects disconnection via `r.Context().Done()`.
- No goroutine leak after client disconnect.
- Partial results are not persisted to the session store.

### 4.2 MCP Tool Execution

**Description:** When the LLM requests tool calls during a conversation, the server executes them against the configured MCP servers and feeds results back to the LLM. The tool call loop may iterate multiple times. Realizes UJ-1.

**Functional Requirements:**

#### FR-4: Execute tool calls via MCP

When the LLM response contains tool call requests, the server executes them against the configured MCP server(s) and feeds results back for the next LLM iteration.

**Consequences (testable):**

- Tool calls are executed against the MCP server URL(s) from configuration.
- Tool results are passed back to the LLM as context for the next completion.
- The loop terminates after at most 5 iterations (matching existing CLI behavior).

#### FR-5: Emit tool call events

The server emits AG-UI tool call events during execution: `TOOL_CALL_START`, `TOOL_CALL_ARGS`, `TOOL_CALL_END`.

**Consequences (testable):**

- Each tool call produces a `TOOL_CALL_START` event before execution.
- `TOOL_CALL_ARGS` contains the serialized tool input.
- `TOOL_CALL_END` contains the tool result after execution completes.
- Events are flushed immediately (not buffered until end of response).

### 4.3 Session Management

**Description:** Sessions enable multi-turn conversations that persist across HTTP requests. A session is identified by a `threadId` provided by the frontend. Realizes UJ-1, UJ-2.

**Functional Requirements:**

#### FR-6: Create session on first request

When the frontend sends a request without a `threadId` (or with an empty one), the backend generates a new session ID (UUID) and returns it in the `RUN_STARTED` event. The frontend uses this ID for subsequent requests in the same conversation.

**Consequences (testable):**

- Missing or empty `threadId` in the request → backend generates a UUID and includes it in `RUN_STARTED`.
- The session is persisted to the store after the response completes.
- Subsequent requests with the returned `threadId` reuse the session.

#### FR-7: Resume existing session

When a valid `threadId` is provided, the server loads the existing session and its message history.

**Consequences (testable):**

- The LLM receives the full conversation history as context.
- New messages are appended to the existing session.

#### FR-8: List sessions

`GET /sessions` returns the list of available sessions with metadata (ID, creation date, last message date, message count).

**Consequences (testable):**

- Response is JSON array, ordered by last activity (most recent first).
- Empty array returned when no sessions exist (not an error).

#### FR-9: Delete session

`DELETE /sessions/{id}` removes a session and all its messages from the store.

**Consequences (testable):**

- Returns HTTP 204 on successful deletion.
- Returns HTTP 404 for unknown session ID.
- Subsequent requests with the deleted `threadId` create a new session.

#### FR-5b: Emit error events on tool failure

When an MCP tool call fails (connection error, timeout, tool error), the server emits an AG-UI error event with a human-readable message describing what went wrong.

**Consequences (testable):**

- MCP server unreachable → error event with message like "Impossible de contacter le service de navigation. Veuillez réessayer."
- Tool returns an error → error event with the tool's error description.
- The error event does not terminate the SSE stream (other events can follow if the LLM decides to respond despite the failure).

### 4.4 Conversation History

**Description:** When resuming a session, the frontend needs the historical messages to display the conversation. The server provides this via AG-UI's history mechanism. Realizes UJ-2.

**Functional Requirements:**

#### FR-10: Emit messages snapshot

At the start of a resumed session's SSE stream, the server emits a `MESSAGES_SNAPSHOT` event containing the conversation history.

**Consequences (testable):**

- `MESSAGES_SNAPSHOT` is emitted after `RUN_STARTED` and before `TEXT_MESSAGE_START`.
- Contains all prior messages (user and assistant) in chronological order.
- Not emitted for new sessions (no history to show).

#### FR-11: Load history for LLM context

When resuming a session, all historical messages are loaded and passed to the LLM as conversation context.

**Consequences (testable):**

- The LLM's completion call includes the full message history.
- History loading does not block event emission (snapshot can be sent while LLM processes).

### 4.5 Configuration

**Description:** The server reads its agent configuration (system prompt, MCP servers, LLM provider) from the existing store used by the CLI. No separate configuration mechanism. Realizes platform operator JTBD.

**Functional Requirements:**

#### FR-12: Read configuration from existing store

The server reads MCP server URLs, system prompt, and LLM API keys from the same persisted configuration used by the CLI. Model selection is not part of this configuration — it comes from the frontend per request (see FR-15).

**Consequences (testable):**

- A `talk serve` instance started after `talk` CLI configuration works without additional setup.
- Changes to configuration via CLI are reflected on next server restart.
- The server does not require a default model in its configuration.

#### FR-13: Configurable server port

The HTTP server port is configurable via environment variable or CLI flag.

**Consequences (testable):**

- Default port is 8090 when no override is specified.
- `SERVE_PORT` environment variable overrides the default.
- `--port` flag overrides the environment variable.

#### FR-14: Runtime error reporting via AG-UI

The server always starts and listens on its port regardless of configuration state. Configuration and infrastructure errors are reported to the frontend via AG-UI error events when a request arrives.

**Consequences (testable):**

- Missing or invalid LLM API key → AG-UI error event with user-facing message (e.g., "L'assistant n'est pas configuré correctement. Contactez l'administrateur.").
- Missing system prompt → AG-UI error event with user-facing message.
- Database unreachable → AG-UI error event with message ("Service temporairement indisponible, veuillez réessayer.") + `ERROR` level log with technical details for the operator.
- The server process never exits due to configuration errors — it remains available and can recover (e.g., DB reconnection) without restart.
- Health-degraded state is visible in logs (structured logging with error category).

#### FR-15: Model selection per request

The frontend sends a model alias in each request via `forwardedProps.model`. The server resolves the alias against the known model registry (`domain.Models`) and uses the corresponding LLM provider/model for that request. The model alias is mandatory — requests without it are rejected.

**Consequences (testable):**

- A valid `forwardedProps.model` value (e.g., `"sonnet-4.6"`, `"haiku-4.5"`) causes the server to use that model for the LLM call.
- Missing `forwardedProps.model` → AG-UI error event with message "Le champ model est requis. Modèles disponibles : haiku-4.5, sonnet-4.6, opus, o4-mini, gpt-5.4, mistral-small."
- Unknown model alias → AG-UI error event listing the available models.
- The model alias is passed via the AG-UI standard `forwardedProps` field (`RunAgentInput.ForwardedProps`), which CopilotKit supports natively.

## 5. Non-Goals (Explicit)

- **Token-level streaming** — v1 sends the complete response in one event. Token streaming is a future UX optimization (Phase 6 in research doc).
- **Multi-agent routing** — The server serves one agent configuration. Multiple agents = multiple instances.
- **Web-based configuration UI** — Configuration is done via the existing CLI. Web admin is a future feature.
- **Authentication/Authorization** — Deferred to a subsequent phase. The architecture supports middleware insertion without refactoring.
- **WebSocket transport** — AG-UI uses SSE (unidirectional). No WebSocket needed.
- **Frontend development** — This PRD covers the backend server only. Frontend apps are separate projects using CopilotKit.
- **PostgreSQL migration** — SQLite is the persistence layer for v1. Migration is a separate initiative.

## 6. MVP Scope

### 6.1 In Scope

- `talk serve` subcommand in the existing `talk` binary
- AG-UI protocol compliance (POST → SSE events)
- Single-message-content response (synchronous Complete())
- Tool call execution with AG-UI events
- Session create/resume/list/delete
- History snapshot on session resume
- CORS support for cross-origin frontends
- Graceful shutdown on SIGTERM/SIGINT
- Logging via existing `talk-libs/logger`

### 6.2 Out of Scope for MVP

- Token streaming (deferred to Phase 6) `[NON-GOAL for MVP]`
- Authentication middleware (deferred — architecture-ready) `[NON-GOAL for MVP]`
- Rate limiting (deferred — can reuse `talk-libs/mcpserver` patterns when needed)
- Web configuration UI (deferred)
- PostgreSQL support (deferred — separate initiative)
- Reasoning events (`REASONING_*` for thinking blocks — Phase 5 in research)
- Health check endpoint (low priority, add when deploying behind load balancer)

## 7. Success Metrics

**Primary**

- **SM-1**: A CopilotKit frontend can send a message and receive a streamed AG-UI response — validates FR-1, FR-2.
- **SM-2**: A conversation with tool calls (e.g., route calculation via mcp-ign-nav) completes successfully end-to-end — validates FR-4, FR-5.

**Secondary**

- **SM-3**: A session can be resumed the next day with full history context — validates FR-7, FR-10, FR-11.
- **SM-4**: Zero additional configuration required beyond existing CLI setup to start the server — validates FR-12.

**Counter-metrics (do not optimize)**

- **SM-C1**: Response time — do not optimize at the expense of correctness. A correct response in 10s beats a fast wrong answer.

## 8. Cross-Cutting NFRs

| NFR    | Category       | Requirement                                                                                |
| ------ | -------------- | ------------------------------------------------------------------------------------------ |
| NFR-1  | Performance    | Time-to-first-event < 500ms after POST received (excluding LLM latency)                    |
| NFR-2  | Concurrency    | 100 simultaneous SSE connections without degradation                                       |
| NFR-3  | Resilience     | An error on one request does not impact other active connections                           |
| NFR-4  | Protocol       | Full conformance with AG-UI event specification                                            |
| NFR-5  | Integration    | Code follows all `project-context.md` conventions (no CGO, stdlib net/http, wg.Go(), etc.) |
| NFR-6  | Testability    | HTTP handlers testable via `httptest` with no external dependencies                        |
| NFR-7  | Shutdown       | Graceful shutdown: wait for active streams to complete (configurable timeout), then exit   |
| NFR-8  | CORS           | Cross-origin requests accepted (required for independent React frontends)                  |
| NFR-9  | Observability  | Request logging (duration, session ID, status) via `talk-libs/logger`                      |
| NFR-10 | Security-ready | Architecture supports auth middleware insertion without handler refactoring                |

## 9. Integration and Dependencies

| Dependency                       | Type     | Notes                                                                   |
| -------------------------------- | -------- | ----------------------------------------------------------------------- |
| `talk/internal/domain`           | Internal | ConversationManager, LlmClient, MessageStore, SessionBrowser interfaces |
| `talk/internal/llm`              | Internal | Anthropic/OpenAI provider implementations                               |
| `talk/internal/memory/sqlite`    | Internal | Session persistence (v1)                                                |
| `talk/internal/mcp`              | Internal | MCP client for tool execution                                           |
| AG-UI Protocol spec              | External | Event types, transport format                                           |
| AG-UI Go SDK (community)         | External | Type definitions, encoding helpers                                      |
| CopilotKit (frontend)            | External | Primary consumer of the server                                          |
| LLM providers (Anthropic/OpenAI) | External | Rate limits apply per-provider                                          |

## 10. Open Questions

_All initial questions resolved during PRD review (2026-06-23)._

| #   | Question                                                      | Resolution                                                                                                                                                                                           |
| --- | ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Should `MESSAGES_SNAPSHOT` include tool call/result messages? | Yes — include tool calls and results for full context.                                                                                                                                               |
| 2   | Default port?                                                 | 8090 (avoids conflict with MCP servers on 8080).                                                                                                                                                     |
| 3   | Should the server emit `STATE_SNAPSHOT` events?               | No — `STATE_SNAPSHOT` pushes arbitrary structured state (JSON); for a chat-based use case `MESSAGES_SNAPSHOT` is sufficient. Revisit only if frontends need shared structured state beyond messages. |
| 4   | How to surface MCP connection failures to the frontend?       | Emit an AG-UI error event with a human-readable, expressive message describing the tool failure.                                                                                                     |

## 11. Assumptions Index

- `[ASSUMPTION]` §4.1 FR-2: A single `TEXT_MESSAGE_CONTENT` event with the full response is AG-UI compliant (not all implementations use chunked deltas).
- `[ASSUMPTION]` §4.3 FR-6: CopilotKit's `HttpAgent` can be configured to read the `threadId` from the `RUN_STARTED` event and reuse it for subsequent requests (standard AG-UI flow).
- `[ASSUMPTION]` §4.5 FR-12: The CLI's persisted configuration (MCP servers, prompt) is accessible to `talk serve` without modification to the store layer.
- `[ASSUMPTION]` §4.2 FR-4: The existing MCP client in `talk/internal/mcp` can connect to configured MCP servers at runtime without protocol changes.
