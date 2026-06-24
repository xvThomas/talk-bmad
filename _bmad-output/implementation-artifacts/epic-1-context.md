# Epic 1 Context: Conversation AG-UI de bout en bout

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

End clients can send a message from a CopilotKit frontend and receive an assistant response as an AG-UI SSE event stream. This epic delivers the core server infrastructure: the `talk serve` subcommand, HTTP handler, SSE encoding, session creation, configuration loading, model resolution per request, error reporting, and graceful shutdown.

## Stories

- Story 1.1: Commande `talk serve` et serveur HTTP minimal
- Story 1.2: Handler POST /agent avec réponse SSE AG-UI
- Story 1.3: Intégration ConversationManager et config existante
- Story 1.4: Annulation sur déconnexion client

## Requirements & Constraints

- Accept POST /agent with RunAgentInput JSON body; return SSE event stream (FR-1, FR-2)
- Event sequence: RUN_STARTED → TEXT_MESSAGE_START → TEXT_MESSAGE_CONTENT → TEXT_MESSAGE_END → RUN_FINISHED
- Handle client disconnection via r.Context().Done(); cancel in-flight LLM calls (FR-3)
- Create session on first request; backend generates UUID in RUN_STARTED (FR-6)
- Server reads MCP server URLs, system prompt, and LLM API keys from existing CLI store (FR-12). Model is NOT part of this config.
- Model selection is per-request via `forwardedProps.model` — mandatory, resolved against `domain.Models` registry (FR-15)
- Missing or unknown model alias → AG-UI error event listing available models
- Configurable port: default 8090, SERVE_PORT env, --port flag (FR-13)
- Runtime errors reported as AG-UI error events, server never exits on config errors (FR-14)
- Time-to-first-event < 500ms excluding LLM latency (NFR-1)
- CORS enabled for cross-origin frontends (NFR-8)
- Graceful shutdown on SIGTERM/SIGINT (NFR-7)

## Technical Decisions

- stdlib net/http with Go 1.22+ ServeMux patterns (D-1)
- No token-level streaming in v1 — single TEXT_MESSAGE_CONTENT event with full response (D-2)
- One instance = one agent configuration (system prompt + MCP + API keys), model chosen per request (D-3, D-8)
- talk serve subcommand in existing binary, reuses all domain code (D-7)
- AG-UI Go SDK: `github.com/ag-ui-protocol/ag-ui/sdks/community/go`
- ConversationManager accepts ModelID per call via SetClient()
- domain.Lookup(alias) resolves model alias → Model struct (provider, API model ID, API key name)
- ForwardedProps is `any` type in RunAgentInput; extract with type assertion to map[string]any

## Cross-Story Dependencies

- Story 1.1 provides the HTTP server and `talk serve` command that Stories 1.2–1.4 build on
- Story 1.2 provides the AG-UI handler that Story 1.3 wires to the real ConversationManager
- Story 1.3 connects the handler to real LLM calls with model resolution from forwardedProps
- Story 1.4 adds cancellation to the flow established by 1.2 + 1.3
