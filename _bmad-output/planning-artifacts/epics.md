---
stepsCompleted: [step-01, step-02, step-03]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-talk-bmad-2026-06-21/prd.md
  - _bmad-output/project-context.md
---

# AG-UI Protocol Server (talk serve) - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for the AG-UI Protocol Server (`talk serve`), decomposing the PRD requirements into implementable stories.

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

| FR    | Epic   | Description                       |
| ----- | ------ | --------------------------------- |
| FR-1  | Epic 1 | Accept AG-UI POST requests        |
| FR-2  | Epic 1 | Stream AG-UI response events      |
| FR-3  | Epic 1 | Handle client disconnection       |
| FR-6  | Epic 1 | Create session on first request   |
| FR-12 | Epic 1 | Read config from existing store   |
| FR-13 | Epic 1 | Configurable server port          |
| FR-14 | Epic 1 | Runtime error reporting via AG-UI |
| FR-4  | Epic 2 | Execute tool calls via MCP        |
| FR-5  | Epic 2 | Emit tool call events             |
| FR-5b | Epic 2 | Emit error events on tool failure |
| FR-7  | Epic 3 | Resume existing session           |
| FR-8  | Epic 3 | List sessions                     |
| FR-9  | Epic 3 | Delete session                    |
| FR-10 | Epic 3 | Emit messages snapshot            |
| FR-11 | Epic 3 | Load history for LLM context      |

## Epic List

### Epic 1: Conversation AG-UI de bout en bout

End clients can send a message from a CopilotKit frontend and receive an assistant response as an AG-UI SSE event stream.
**FRs covered:** FR-1, FR-2, FR-3, FR-6, FR-12, FR-13, FR-14

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
I want the server to use the same LLM configuration and system prompt as the CLI,
So that I don't need to configure the agent twice.

**Acceptance Criteria:**

**Given** the talk CLI has been configured (LLM API key, system prompt, provider)
**When** `talk serve` starts
**Then** it reads the configuration from the same store as the CLI
**And** the LLM responds using the configured provider and model
**And** the system prompt is applied to all conversations

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
**Then** an AG-UI error event is emitted with a message inviting the user to continue (e.g., "Le traitement nécessite plus d'étapes. Dites « continue » pour poursuivre.")
**And** all intermediate messages (tool calls + results) are persisted in the session
**And** a subsequent "continue" message from the user resumes with full context

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
