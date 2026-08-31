---
stepsCompleted: [step-01, step-02, step-03]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-talk-bmad-2026-06-21/prd.md
  - _bmad-output/planning-artifacts/prds/prd-talk-frontend-2026-06-28/prd.md
  - _bmad-output/planning-artifacts/prds/prd-map-backend-2026-08-31/prd.md
  - _bmad-output/planning-artifacts/prds/prd-map-frontend-2026-08-31/prd.md
  - _bmad-output/planning-artifacts/adr/adr-001-map-visualization-architecture.md
  - _bmad-output/project-context.md
---

# AG-UI Protocol Server (talk serve) - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for the talk project (backend + frontend), decomposing the PRD requirements into implementable stories.

- **Epics 1–3:** Backend (`talk serve`) — AG-UI server, MCP tool execution, session persistence
- **Epics 4–7:** Frontend (`talk-ui`) — CopilotKit React app, chat UX, production transport
- **Epic 8:** `mcp-ign-nav` — route tool geometry support (backend)
- **Epic 9:** `talk-ui` — MapLibre map visualization panel (frontend)

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

### mcp-ign-nav Requirements (Epic 8 — Backend)

- IGN-FR-1: `route` tool unconditionally requests GeoJSON geometry (no flag)
- IGN-FR-2: `GetGeoJSONGeometry` field and `GET_GEOJSON_GEOMETRY` env var removed from `ServerEnv`
- IGN-FR-3: `DistanceTimeTool` unchanged — no geometry, no labels
- IGN-FR-4: Route tool tests updated for removed constructor parameter
- IGN-FR-5: `RouteToolInput` gains optional `StartLabel` and `EndLabel` string fields
- IGN-FR-6: `RouteToolOutput` echoes `StartLabel`/`EndLabel` verbatim from input
- IGN-FR-7: `DistanceTimeToolInput/Output` not extended

### Map Visualization Requirements (Epic 8 — Frontend)

- MAP-FR-1: Split layout — chat left, collapsible map panel right; `ChatView` unmodified
- MAP-FR-2: Map panel hidden by default at session start
- MAP-FR-3: Map panel auto-opens when a new itinerary arrives
- MAP-FR-4: User can manually toggle map panel open/closed
- MAP-FR-5: Closing panel does not discard itinerary state
- MAP-FR-6: `MapProvider` context independent of `ChatUIContext`; maintains `MapFeature[]`, `selectedFeatureId`, `isMapPanelOpen`
- MAP-FR-7: `MapProvider` accepts `mappers: ToolResultMapper[]` prop; detects tool results and applies matching mapper
- MAP-FR-8: `ToolResultMapper` and `MapFeature` interfaces in `src/map/types.ts`; no dependency on chat components
- MAP-FR-9: Session reset clears all features and closes map panel
- MAP-FR-10: MapLibre GL JS via `react-map-gl`; IGN Geopf raster WMTS base layer; no API key required
- MAP-FR-11: Each itinerary `LineString` rendered as a layer with auto-generated color; `MapPanel` lazy-loaded
- MAP-FR-12: Unselected routes at ≈40% opacity; selected route at full opacity + increased weight
- MAP-FR-13: Route start point rendered as prominent marker (green)
- MAP-FR-14: Route end point rendered as prominent marker (red), distinct from start
- MAP-FR-15: Intermediate waypoints rendered as smaller, discreet markers
- MAP-FR-16: Viewport auto-fits to new itinerary bbox; no selection → fits all itineraries
- MAP-FR-17: Legend panel embedded in map view; lists all session itineraries
- MAP-FR-18: Each legend entry: `StartLabel → EndLabel (profile, optimization)`, formatted distance, formatted duration; fallback to coordinates
- MAP-FR-19: Legend has two tabs: **Résumé** (per-itinerary) and **Étapes** (steps for selected itinerary)
- MAP-FR-20: Étapes tab lists each `RouteStep`: instruction, modifier, road name/number, distance, duration
- MAP-FR-21: Click legend entry → select itinerary, fit bbox, full opacity, dim others
- MAP-FR-22: Click step (Étapes tab) → re-center map on step start coordinates
- MAP-FR-23: Selected legend entry visually marked as active
- MAP-FR-24: `routeToolMapper` adapter in `src/map/adapters/route-tool-mapper.ts`; transforms `RouteToolOutput` → `MapFeature`
- MAP-FR-25: `routeToolMapper` registered in `MapProvider` at app root; no chat component imports it

### Epic 8 FR Coverage Map

| FR          | Story  | Description                                                       |
| ----------- | ------ | ----------------------------------------------------------------- |
| IGN-FR-1    | 8.1    | `route` always returns geometry                                   |
| IGN-FR-2    | 8.1    | Remove `GetGeoJSONGeometry` / `GET_GEOJSON_GEOMETRY`              |
| IGN-FR-3    | 8.1    | `DistanceTimeTool` unchanged                                      |
| IGN-FR-4    | 8.1    | Update route tool tests                                           |
| IGN-FR-5    | 8.2    | Add `StartLabel`/`EndLabel` to `RouteToolInput`                   |
| IGN-FR-6    | 8.2    | Echo labels in `RouteToolOutput`                                  |
| IGN-FR-7    | 8.2    | `DistanceTimeToolInput/Output` not extended                       |
| MAP-FR-1    | 9.1    | Split layout, `ChatView` unmodified                               |
| MAP-FR-2    | 9.1    | Map panel hidden at session start                                 |
| MAP-FR-3    | 9.1    | Auto-open on new itinerary                                        |
| MAP-FR-4    | 9.1    | Manual toggle                                                     |
| MAP-FR-5    | 9.1    | Close does not discard state                                      |
| MAP-FR-6    | 9.1    | `MapProvider` independent context                                 |
| MAP-FR-7    | 9.1    | `ToolResultMapper` dispatch                                       |
| MAP-FR-8    | 9.1    | `MapFeature`/`ToolResultMapper` types isolated                    |
| MAP-FR-9    | 9.1    | Session reset clears map state                                    |
| MAP-FR-10   | 9.2    | MapLibre + IGN Geopf base layer                                   |
| MAP-FR-11   | 9.2    | LineString layer per itinerary, lazy-load                         |
| MAP-FR-12   | 9.2    | Opacity differentiation selected vs. unselected                   |
| MAP-FR-13   | 9.2    | Start marker                                                      |
| MAP-FR-14   | 9.2    | End marker                                                        |
| MAP-FR-15   | 9.2    | Intermediate waypoint markers                                     |
| MAP-FR-16   | 9.2    | Viewport bbox auto-fit                                            |
| MAP-FR-17   | 9.3    | Legend panel                                                      |
| MAP-FR-18   | 9.3    | Legend entry format + fallback                                    |
| MAP-FR-19   | 9.3    | Résumé / Étapes tabs                                              |
| MAP-FR-20   | 9.3    | Étapes step list                                                  |
| MAP-FR-21   | 9.3    | Click legend entry interaction                                    |
| MAP-FR-22   | 9.3    | Click step → re-center                                            |
| MAP-FR-23   | 9.3    | Active legend entry styling                                       |
| MAP-FR-24   | 9.3    | `routeToolMapper` adapter                                         |
| MAP-FR-25   | 9.3    | Adapter registered at app root                                    |

## Epic List

### Epic 1: End-to-End AG-UI Conversation

End clients can send a message from a CopilotKit frontend and receive an assistant response as an AG-UI SSE event stream.
**FRs covered:** FR-1, FR-2, FR-3, FR-6, FR-12, FR-13, FR-14, FR-15, FR-16

### Epic 2: MCP Tool Execution with AG-UI Events

The assistant can call external tools (route calculation, weather) during a conversation and the frontend sees tool call progress.
**FRs covered:** FR-4, FR-5, FR-5b

### Epic 3: Persistent Sessions and History

End clients can resume previous conversations, view history, and manage their sessions.
**FRs covered:** FR-7, FR-8, FR-9, FR-10, FR-11

---

## Epic 1: End-to-End AG-UI Conversation

End clients can send a message from a CopilotKit frontend and receive an assistant response as an AG-UI SSE event stream. This epic delivers the core server infrastructure: the `talk serve` subcommand, HTTP handler, SSE encoding, session creation, configuration loading, error reporting, and graceful shutdown.

### Story 1.1: The `talk serve` command and minimal HTTP server

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

### Story 1.2: POST /agent handler with AG-UI SSE response

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

### Story 1.3: ConversationManager integration and existing config

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
**Then** an AG-UI error event is emitted with a user-facing message (e.g., "The assistant is not configured correctly. Contact the administrator.")
**And** an ERROR-level log is written with technical details

**Given** the database is unreachable
**When** a `POST /agent` request arrives
**Then** an AG-UI error event is emitted with message "Service temporarily unavailable, please try again."
**And** an ERROR-level log is written

### Story 1.4: Cancellation on client disconnection

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

## Epic 2: MCP Tool Execution with AG-UI Events

The assistant can call external tools (route calculation, weather) during a conversation and the frontend sees tool call progress. This builds on Epic 1's conversation flow to add the tool execution loop with AG-UI event emission and error handling.

### Story 2.1: MCP tool execution loop

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
**Then** an AG-UI error event is emitted with a user-facing message (e.g., "I reached the tool call limit without being able to finalize. Try rephrasing your question more specifically.")
**And** all intermediate messages (tool calls + results) are persisted in the session

### Story 2.2: AG-UI tool call event emission

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

### Story 2.3: MCP error handling with AG-UI error events

As an end client,
I want to see a clear error message when a tool fails,
So that I understand what happened and can retry or rephrase my request.

**Acceptance Criteria:**

**Given** the server attempts to call an MCP tool
**When** the MCP server is unreachable (connection refused, timeout)
**Then** an AG-UI error event is emitted with a human-readable message (e.g., "Unable to reach the navigation service. Please try again.")
**And** the error does not terminate the SSE stream
**And** the LLM is informed of the failure and may produce a text response explaining the issue

**Given** the MCP server returns a tool error
**When** the error is received
**Then** an AG-UI error event is emitted with the tool's error description
**And** an ERROR-level log is written with the full technical details (MCP server URL, tool name, error)

### Story 2.4: Conversation resume after iteration limit (future)

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

### Story 2.5: MCP connection resilience after network loss

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

---

## Epic 3: Persistent Sessions and History

End clients can resume previous conversations, view history, and manage their sessions. This builds on the session creation from Epic 1 to add full session lifecycle management and history replay.

### Story 3.1: Session resume with LLM history

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

### Story 3.2: MESSAGES_SNAPSHOT for the frontend

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

### Story 3.3: List and delete sessions

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

### Epic 4: Basic Functional Conversation (talk-ui)

The user can open the web app, send a message, and receive a streaming response.
**FRs covered:** UI-FR-1, UI-FR-2, UI-FR-3, UI-FR-4, UI-FR-16, UI-FR-21, UI-FR-23, UI-FR-25

### Epic 5: Model and Reasoning Control

The user can choose their LLM model, enable thinking mode, and see the model's reasoning.
**FRs covered:** UI-FR-5, UI-FR-6, UI-FR-7, UI-FR-8, UI-FR-9

### Epic 6: Advanced Interactions (tools, interrupts, errors, cancel)

The user sees tool calls in progress, can continue after an interrupt, cancel a streaming response, and understands errors.
**FRs covered:** UI-FR-10, UI-FR-11, UI-FR-12, UI-FR-13, UI-FR-14, UI-FR-15, UI-FR-17, UI-FR-18, UI-FR-19, UI-FR-20, UI-FR-22

### Epic 7: Custom AG-UI SSE Client (production-ready)

The app uses its own SSE client instead of `agents__unsafe_dev_only`, removing the CopilotKit Enterprise license dependency.
**FRs covered:** Production architecture (no new user-facing FRs)
### Epic 8: `mcp-ign-nav` — Route Tool Geometry Support

The `route` tool unconditionally returns GeoJSON geometry and optional place-name labels, enabling frontend map rendering without environment configuration.
**Codebase:** `mcp-ign-nav`
**Source PRD:** `prd-map-backend-2026-08-31`
**FRs covered:** IGN-FR-1 to IGN-FR-7

### Epic 9: `talk-ui` — MapLibre Map Visualization Panel

Users see itineraries plotted on an interactive MapLibre GL JS map panel alongside the conversation. The map infrastructure is tool-agnostic (extensible via `ToolResultMapper`).
**Codebase:** `talk-ui`
**Source PRD:** `prd-map-frontend-2026-08-31`
**Architecture:** `adr-001-map-visualization-architecture.md`
**FRs covered:** MAP-FR-1 to MAP-FR-25
---

## Epic 4: Basic Functional Conversation (talk-ui)

The user can open the web app, send a message, and receive a streaming response. Includes project scaffold, CI, AG-UI connection, chat layout, and streaming.

### Story 4.1: Project scaffold and CI

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

### Story 4.2: CopilotKit + AG-UI backend connection

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

### Story 4.3: Chat layout and message sending

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

### Story 4.4: Message streaming and auto-scroll

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

### Story 4.5: Markdown rendering for assistant messages

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

## Epic 5: Model and Reasoning Control

The user can choose their LLM model, enable thinking mode, and see the model's reasoning displayed in the conversation.

### Story 5.1: LLM model selection

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

### Story 5.2: Thinking effort selection

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

### Story 5.3: Reasoning display

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

## Epic 6: Advanced Interactions (tools, interrupts, errors, cancel)

The user sees tool calls in progress, can continue after a max-iterations interrupt, cancel an ongoing streaming response, and understands errors displayed in the conversation flow.

### Story 6.1: Tool call display (collapse/expand)

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

### Story 6.1.5: UI context facade (CopilotKit / presentation separation)

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
**And** Story 6.1, 6.3, 6.4, and 6.5 behaviors remain unchanged

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

### Story 6.2: Type-safe AG-UI messages (Zod) and cast elimination

As a frontend developer,
I want AG-UI message parsing and normalization to be fully type-safe with Zod,
So that the message pipeline is robust and no runtime type casts are needed in UI code.

**Acceptance Criteria:**

**Given** AG-UI messages arrive from the stream
**When** they are parsed at the normalization boundary
**Then** supported payloads are validated with explicit Zod schemas
**And** malformed payloads are safely ignored without crashing the app.

**Given** message rendering in chat UI
**When** TypeScript strict checks run
**Then** no type assertions (`as`) are required in the AG-UI message handling and presentation path
**And** no `any` is introduced.

**Given** existing behavior for tool-call reconciliation and reasoning ordering
**When** parser-first normalization is introduced
**Then** behavior remains unchanged and covered by regression tests.

### Story 6.3: Max-iterations interrupt and Continue button

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

### Story 6.4: Streaming cancellation and Retry button

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

### Story 6.5: Inline error display

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

## Epic 7: Custom AG-UI SSE Client (production-ready)

The app uses its own SSE client instead of `agents__unsafe_dev_only`, removing the CopilotKit Enterprise license dependency for production deployment.

### Story 7.1: Fetch SSE client with AG-UI event parsing

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

### Story 7.2: AbstractAgent interface implementation

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

### Story 7.3: Client unit tests and migration

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

### Story 7.4: Client-side conversation persistence (post-migration)

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

---

## Epic 8: Map Visualization of Itineraries

Users see itineraries returned by the `route` MCP tool plotted on an interactive map panel alongside the conversation. The backend always returns GeoJSON geometry; the frontend renders it with MapLibre GL JS on an IGN Geopf base map. The map infrastructure is fully decoupled from chat components via a `MapProvider` / `ToolResultMapper` pattern, making it reusable for any future geo-aware MCP tool.

**Prerequisites:** none (8.1 and 8.2 are self-contained `mcp-ign-nav` changes)
**Execution order:** 8.1 → 8.2 → 8.3 → 8.4 → 8.5

---

### Story 8.1: Remove `getGeometry` flag — `route` always returns GeoJSON geometry

**Codebase:** `mcp-ign-nav`

As a platform operator,
I want the `route` tool to always return GeoJSON geometry without any environment configuration,
So that map visualization works reliably in all deployments and the codebase is simpler.

**Acceptance Criteria:**

**Given** the current `RouteTool` with a `getGeometry bool` constructor parameter
**When** story 8.1 is implemented
**Then** `NewRouteTool(limiter *rate.Limiter)` takes no `getGeometry` parameter
**And** the tool unconditionally sets `GetGeometry: true` in the IGN API request
**And** `RouteToolOutput.Geometry` is always populated (never nil for a successful call)

**Given** `ServerEnv` currently has a `GetGeoJSONGeometry bool` field
**When** story 8.1 is implemented
**Then** the field is removed from `ServerEnv`
**And** `GET_GEOJSON_GEOMETRY` is no longer read from the environment
**And** the field is removed from `.env.example` and any README section that documents it

**Given** `DistanceTimeTool`
**When** story 8.1 is implemented
**Then** it is unchanged — it continues to request no geometry and return no geometry

**Given** existing tests that call `NewRouteTool(limiter, false)` or `NewRouteTool(limiter, true)`
**When** story 8.1 is implemented
**Then** all call sites are updated to `NewRouteTool(limiter)`
**And** tests asserting the absence of geometry are removed
**And** the full test suite passes

**FRs:** IGN-FR-1, IGN-FR-2, IGN-FR-3, IGN-FR-4

---

### Story 8.2: Add `StartLabel`/`EndLabel` to route tool input and output

**Codebase:** `mcp-ign-nav`

As an LLM agent,
I want to pass the human-readable place names I already know into the `route` tool call,
So that the frontend can display a meaningful legend label without performing reverse geocoding.

**Acceptance Criteria:**

**Given** `RouteToolInput`
**When** story 8.2 is implemented
**Then** it has two new optional fields: `StartLabel string` (json: `"startLabel,omitempty"`) and `EndLabel string` (json: `"endLabel,omitempty"`)
**And** their `description` struct tags instruct the LLM to populate them with the human-readable origin and destination names it resolved during prior geocoding
**And** both fields are optional — calls without them continue to work

**Given** `RouteToolOutput`
**When** story 8.2 is implemented
**Then** it has two new fields: `StartLabel string` (json: `"startLabel,omitempty"`) and `EndLabel string` (json: `"endLabel,omitempty"`)
**And** both fields echo the corresponding input values verbatim
**And** if input fields are empty, output fields are also empty (no processing)

**Given** `DistanceTimeToolInput` and `DistanceTimeToolOutput`
**When** story 8.2 is implemented
**Then** they are unchanged — labels are only meaningful when geometry is present

**Given** existing route tool tests
**When** story 8.2 is implemented
**Then** a new test asserts that non-empty input labels are echoed in the output
**And** a test asserts that empty input labels produce empty output labels
**And** all existing tests continue to pass

**FRs:** IGN-FR-5, IGN-FR-6, IGN-FR-7

---

## Epic 9: `talk-ui` — MapLibre Map Visualization Panel

Users see itineraries plotted on an interactive MapLibre GL JS map panel alongside the conversation. The backend is fully decoupled from chat components via a `MapProvider` / `ToolResultMapper` pattern, making it reusable for any future geo-aware MCP tool.

**Prerequisites:** Epic 8 complete (geometry + labels in `route` output)
**Execution order:** 9.1 → 9.2 → 9.3

---

### Story 9.1: Split layout + `MapProvider` + session itinerary state

**Codebase:** `talk-ui`
**Dependencies:** Epic 8 (geometry in `route` output)

As an end user,
I want a map panel to appear automatically alongside my conversation when a route is returned,
So that I can immediately see the itinerary without any manual action.

**Acceptance Criteria:**

**Given** the existing `ChatView` component
**When** story 8.3 is implemented
**Then** `ChatView` is wrapped in a layout container that places the map panel to its right
**And** `ChatView` itself is not modified (no new props, no new imports)
**And** the layout container accepts a `mapPanelOpen: boolean` prop to show/hide the map panel area

**Given** the application starts with no conversation
**When** the map panel state is initialized
**Then** `isMapPanelOpen` is `false` and `itineraries` is an empty array
**And** the map panel area is not rendered (not merely hidden)

**Given** the `route` tool returns a result in the message stream
**When** `MapProvider` processes `agent.messages`
**Then** the result is passed through the `routeToolMapper` (registered at app root)
**And** a new `MapFeature` is added to `itineraries`
**And** if `isMapPanelOpen` was `false`, it is set to `true`

**Given** the user clicks the map panel toggle control
**When** it is currently open
**Then** `isMapPanelOpen` becomes `false` and the panel area collapses
**And** the itinerary state is preserved

**Given** the user closes then re-opens the panel
**When** the panel reopens
**Then** the previously accumulated itineraries are still displayed

**Given** `MapProvider` internal implementation
**When** story 8.3 is implemented
**Then** `ToolResultMapper` and `MapFeature` interfaces live in `src/map/types.ts`
**And** `src/map/types.ts` has zero imports from chat components
**And** `MapProvider` depends on `agent.messages` from `@copilotkit/react-core` but not on `ChatUIContext`

**Given** the user resets the conversation (new session)
**When** the reset is triggered
**Then** `itineraries` is cleared and `isMapPanelOpen` is set to `false`
**And** the map panel area is removed from the DOM

**FRs:** MAP-FR-1, MAP-FR-2, MAP-FR-3, MAP-FR-4, MAP-FR-5, MAP-FR-6, MAP-FR-7, MAP-FR-8, MAP-FR-9

**Technical notes:**
- `MapProvider` and `ChatUIProvider` are siblings in the React tree, composed at `App.tsx`
- The map panel toggle control can be a simple button on the panel edge or a toolbar icon — visual design is implementation choice
- `MapFeature.id` should be derived from the AG-UI `toolCallId` to ensure uniqueness and idempotency (reprocessing the same message does not duplicate features)

---

### Story 9.2: Map rendering — MapLibre GL JS, IGN tiles, routes and markers

**Codebase:** `talk-ui`
**Dependencies:** Story 9.1 (`MapProvider` + `MapFeature` available)

As an end user,
I want to see my itinerary drawn on an interactive map with clear start and end markers,
So that I can spatially understand the route.

**Acceptance Criteria:**

**Given** `MapPanel` is rendered for the first time
**When** the map initializes
**Then** it uses MapLibre GL JS via `react-map-gl`
**And** the base layer is the IGN Geopf Plan IGN v2 raster WMTS tile layer
**And** no API key is required to load the tiles
**And** `MapPanel` is lazy-loaded via React `lazy` + `Suspense`

**Given** one or more `MapFeature` objects in `MapProvider` state
**When** `MapPanel` renders
**Then** each feature's `geometry` (GeoJSON `LineString`) is rendered as a `<Source type="geojson">` + `<Layer type="line">`
**And** each feature has an auto-generated color distinct from others (minimum 4 visually distinct colors before cycling)
**And** the unselected features are rendered at ≈40% opacity
**And** the selected feature is rendered at 100% opacity with a slightly increased line weight

**Given** a new `MapFeature` is added
**When** the map updates
**Then** the viewport fits to the new feature's `bbox` using MapLibre's `fitBounds`

**Given** no feature is selected and multiple features exist
**When** the map renders
**Then** the viewport fits the combined bounding box of all features

**Given** a `MapFeature` with `geometry.type === "LineString"`
**When** the feature is rendered
**Then** the first coordinate is rendered as a prominent start marker (green circle, larger)
**And** the last coordinate is rendered as a prominent end marker (red circle, larger)
**And** any intermediate waypoint coordinates (derived from `properties.portions` start/end points) are rendered as smaller neutral-color dot markers

**FRs:** MAP-FR-10, MAP-FR-11, MAP-FR-12, MAP-FR-13, MAP-FR-14, MAP-FR-15, MAP-FR-16

**Technical notes:**
- Use `react-map-gl` with `mapLib` prop pointing to MapLibre GL JS (not Mapbox)
- IGN Geopf WMTS tile URL pattern: `https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2&STYLE=normal&FORMAT=image/png&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}`
- Auto-color palette: derive from a fixed hue-spaced list (e.g., `["#2196F3", "#FF5722", "#4CAF50", "#9C27B0", "#FF9800"]`), indexed by feature order
- Intermediate waypoints are identified from `MapFeature.properties.portions`: each portion's `start` coordinate (except the first, which is the route start) is a waypoint

---

### Story 9.3: Legend panel — Résumé / Étapes tabs, selection, and step re-center

**Codebase:** `talk-ui`
**Dependencies:** Story 9.2 (map renders features; selection opacity behavior in place)

As an end user,
I want a legend panel that lists all my itineraries and lets me explore turn-by-turn steps,
So that I can identify routes, compare them, and navigate the map with precision.

**Acceptance Criteria:**

**Given** `MapPanel` with one or more features
**When** it renders
**Then** a legend panel is displayed on the right side of the map
**And** it has two tabs: **Résumé** and **Étapes**

**Given** the **Résumé** tab is active
**When** it renders
**Then** each feature appears as one entry showing: `StartLabel → EndLabel (profile, optimization)`, formatted distance (e.g., "461 km"), formatted duration (e.g., "2h28")
**And** if `StartLabel` or `EndLabel` is empty, the snapped coordinate string is shown as fallback
**And** the currently selected feature's entry has a distinct active style (highlighted background, bold label)

**Given** the user clicks a legend entry in the **Résumé** tab
**When** the click is handled
**Then** `selectedFeatureId` in `MapProvider` is set to that feature's id
**And** the map viewport fits to that feature's `bbox`
**And** the clicked entry is styled as active
**And** all other entries lose their active style

**Given** the **Étapes** tab is active and a feature is selected
**When** it renders
**Then** the turn-by-turn steps for the selected feature are listed
**And** each step shows: instruction type (e.g., "turn"), modifier (e.g., "left"), road name or number, formatted step distance, formatted step duration
**And** steps are ordered as returned by the `route` tool (from `portions[].steps[]`)

**Given** no feature is selected and the **Étapes** tab is active
**When** it renders
**Then** a prompt is shown inviting the user to select a route in the Résumé tab

**Given** the user clicks a step in the **Étapes** tab
**When** the click is handled
**Then** the map re-centers on that step's `start` coordinates
**And** the zoom level is unchanged
**And** no pin or marker is added to the map

**Given** the `routeToolMapper` adapter (`src/map/adapters/route-tool-mapper.ts`)
**When** it processes a `RouteToolOutput`
**Then** it produces one `MapFeature` with:
  - `id`: the AG-UI `toolCallId`
  - `label`: `"${startLabel} → ${endLabel} (${profile}, ${optimization})"` (with coordinate fallback)
  - `geometry`: `RouteToolOutput.geometry` (GeoJSON `LineString`)
  - `bbox`: `RouteToolOutput.bbox`
  - `properties`: `{ distance, duration, profile, optimization, portions }` (typed, not `unknown`)
**And** the adapter has no import dependency on any React component or context

**Given** the `routeToolMapper` is registered in `MapProvider` at app root (`App.tsx`)
**When** a `route` tool result arrives in `agent.messages`
**Then** `MapProvider` applies the mapper and the feature appears in the legend without any change to chat components

**FRs:** MAP-FR-17, MAP-FR-18, MAP-FR-19, MAP-FR-20, MAP-FR-21, MAP-FR-22, MAP-FR-23, MAP-FR-24, MAP-FR-25

**Technical notes:**
- Format distance: `< 1000m` → `"Xm"`, `≥ 1000m` → `"X.X km"` (round to 1 decimal)
- Format duration: convert seconds → `"Xh YYmin"` or `"Xmin"` if under 1 hour
- The legend panel width should be fixed (e.g., 280px) and scrollable independently of the map
- Tab state (Résumé / Étapes) is local component state — not in `MapProvider`
