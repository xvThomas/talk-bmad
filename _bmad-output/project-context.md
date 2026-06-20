---
project_name: "talk-bmad"
user_name: "Xavierthomas"
date: "2026-06-20"
sections_completed:
  [
    "technology_stack",
    "language_rules",
    "framework_rules",
    "testing_rules",
    "code_quality",
    "critical_rules",
  ]
status: "complete"
rule_count: 67
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

- **Go 1.25.0** — workspace multi-modules (`go.work`). Minimum strict: Go 1.25 required for `sync.WaitGroup.Go()` and enhanced `net/http.ServeMux` patterns.
- **MCP SDK**: `github.com/modelcontextprotocol/go-sdk v1.6.0` — pre-stable, pin exact version, never bump without running full test suite across all `mcp-*` modules.
- **Anthropic SDK**: `github.com/anthropics/anthropic-sdk-go v1.27.1` — breaking changes between minors.
- **OpenAI SDK**: `github.com/openai/openai-go v1.12.0` — breaking changes between minors.
- **CLI**: `github.com/spf13/cobra v1.10.2`, `github.com/c-bata/go-prompt v0.2.6`
- **Auth**: `github.com/golang-jwt/jwt/v5 v5.3.1`
- **Database**: `modernc.org/sqlite v1.50.1` — pure Go, **CGO_ENABLED=0 mandatory**. Never use `mattn/go-sqlite3`.
- **Config**: `github.com/joho/godotenv v1.5.1`
- **Rate limiting**: `golang.org/x/time v0.15.0`
- **Tooling**: `golangci-lint v2.12+` (v2 config format only), `goimports`
- **Build**: `make`, Docker multi-stage with **workspace root as build context** (required for `replace` directive resolution).

### Version Constraints AI Agents Must Know

| Constraint                                          | Failure if ignored                                                    |
| --------------------------------------------------- | --------------------------------------------------------------------- |
| Go ≥ 1.25 in all `go.mod`                           | `wg.Go()` undefined; old pattern (`wg.Add/Done`) breaks project style |
| CGO_ENABLED=0                                       | Docker build fails silently on Alpine (no libc)                       |
| `go.work` is the only valid local build entry point | `replace` directives unresolved without workspace                     |
| MCP/Anthropic/OpenAI SDKs pinned                    | Breaking changes between patches — always run `make test` after bump  |
| golangci-lint v2.x config                           | v1 config syntax causes parser errors in CI                           |
| No cross-module imports between `mcp-*` or `talk`   | Import cycle error, unresolvable                                      |

---

## Critical Implementation Rules

### Go Language Rules

**Concurrency:**

- Use `sync.WaitGroup.Go(fn)` (Go 1.25) — never the legacy `wg.Add/Done` pattern.
- Goroutines spawned in event handlers MUST have `defer recover()` with `errors.Join()` for panic aggregation.
- Use channel-based semaphore (`make(chan struct{}, n)`) for max concurrent executions — not worker pools.
- Protect shared error aggregation with `sync.Mutex` + `errors.Join()`.

**Interface Design:**

- Compile-time interface compliance: `var _ domain.LlmClient = (*AnthropicClient)(nil)`.
- Optional interface pattern: check with type assertion `handler, ok := h.(OptionalInterface)` — don't force all implementations.
- Interfaces are tiny: 1-3 methods max. `LlmClient` is a single `Complete()` method.

**Constructor Patterns:**

- Large parameter sets → config struct (`NewConversationManager(cfg ConversationManagerConfig)`).
- Functional options for framework code (`WithAPIKey(key)`, `WithOAuth(cfg)`).
- Nil-safe defaults: if optional dependency is nil, substitute a `NoOp` implementation silently.
- Constructors may return multiple related types sharing state (`New() → *Repo, *Browser, error`).

**Error Handling:**

- Wrap with operation name: `fmt.Errorf("anthropic completion: %w", err)`.
- Never log AND return — choose one.
- Lowercase, no trailing punctuation.
- Concurrent errors: `errors.Join()`, not error channels.

**Naming:**

- Variable name mirrors type in lowerCamelCase: `ToolExecutor` → `toolExecutor`.
- No generic abbreviations (`svc`, `mgr`, `exec`) — use the full type-derived name.

**HTTP Clients:**

- Never store `*http.Request` on the struct. Fresh request per call.
- Test constructors accept a `baseURL` parameter for `httptest.Server` injection.

**Testing:**

- Stubs use closure fields: `type mockTool struct { executeFunc func(...) }`.
- Test helpers build full dependency graphs: `newManager(client, tools) → (*Manager, *stubReporter)`.
- HTTP tools: production constructor uses `defaultBaseURL`, unexported test constructor accepts custom URL.

**Database (SQLite):**

- `MaxOpenConns(1)` + `PRAGMA journal_mode=WAL` — always.
- Shared `*db` wrapper between repos — never open multiple connections.
- `sync.RWMutex` on the `db` struct for write protection.

**Style:**

- Function bodies ≤ 50 lines, cognitive complexity ≤ 15.
- No emoji in code/comments. Comments in English.
- Self-documenting code preferred. Document "why", not "what".

### MCP Server Framework Rules

**Tool Implementation:**

- Every tool implements `MCPTool[TInput, TOutput]` (Name, Description, Call).
- Input structs: every field MUST have both `json` and `description` tags — `description` is the LLM-facing schema. Missing tag = LLM never fills the parameter (silent zero value).
- Output structs: freely structured, serialized as JSON in MCP response.
- Tool must accept injectable `baseURL` + `*http.Client` for testability. Hardcoded URLs = untestable.
- Tool `Description()` must include WHEN to call (use case), not just what it does — this is the LLM contract.

**Server Wiring (`cmd/main.go`):**

- `main.go` exposes `run(ctx) error` separate from `main()` — tests call `run()`.
- Must stay thin: load env → build tools → `mcpserver.Run(...)`. No business logic.
- Functional options: `WithTools(...)`, `WithAPIKey(...)`, `WithOAuth(...)`, `WithPrompts(...)`.
- Conditional tool registration (plan tiers, feature flags) — both branches must be tested.

**Testing (two levels):**

- `cmd/main_test.go`: wiring smoke test — verifies tools register without panic using `t.Setenv()`.
- `internal/tools/*_test.go`: unit tests with `httptest.NewServer` + injected baseURL/client.
- Always `defer srv.Close()` in httptest — goroutine leaks cause flaky parallel tests.

**Transport & Concurrency:**

- **stdio**: single-client, tools can be stateful without synchronization.
- **SSE/streamable-HTTP**: multi-client, all tools must be thread-safe (rate limiter, shared state).
- Dockerfile exposes a port → implies HTTP transport. Don't mix stdio config with Docker.

**Prompts:**

- Prompts are static constants registered at startup via `WithPrompts(...)`.
- Variability via prompt arguments, not conditional prompt sets.
- Located in `internal/prompts/`.

**Scaffolding a New Server:**

- Copy `mcp-playground/` as template.
- Own `go.mod` with `replace ../talk-libs`.
- Add to `go.work` AND root `Makefile` MODULES list.
- Dockerfile: COPY both server dir and `talk-libs/` — build context is workspace root.

**Configuration:**

- Use `BaseEnv` helpers (`envInt`, `envBool`) with safe defaults — never read env in `init()`.
- Tests inject env via `t.Setenv()`, never from `.env` files.

**Rate Limiting:**

- Per-tool, not per-server. Inject `*rate.Limiter` into tool constructor.

### Testing Rules

**Organization:**

- Tests live next to the code they test (same package, `_test.go` suffix).
- Test function naming: `Test_functionName_scenario` with `t.Run()` subtests.
- Table-driven tests for multiple cases — struct slice with `name`, inputs, expected.

**Mocking Approach:**

- No external mock framework (no `gomock`, no `testify/mock`).
- Stubs are hand-written structs with closure fields: `type stubClient struct { completeFunc func(...) }`.
- Each test controls behavior by setting the closure.

**Test Helpers:**

- Marked with `t.Helper()`.
- Build full dependency graphs for integration-style tests.
- Use `t.Cleanup()` for resource teardown.

**HTTP Testing:**

- `httptest.NewServer` with custom handler per test.
- Tool constructors accept `baseURL` + `*http.Client` for injection.
- Always `defer srv.Close()`.

**Environment:**

- `t.Setenv()` for env vars in tests — never `.env` files.
- No global test state — each test is self-contained.

**Coverage:**

- `make cover` runs per-module coverage.
- Conditional branches (feature flags, plan tiers) must both be tested.

### Code Quality & Project Structure

**Monorepo Structure:**

- Each module is independently buildable with its own `go.mod` and `Makefile`.
- Shared code goes in `talk-libs/` only — zero application logic there.
- No cross-imports between application modules (`talk`, `mcp-owm`, `mcp-ign-nav`, `mcp-playground`).
- `domain/` packages have zero external dependencies (except `jsonschema-go` for schema reflection).

**File Organization:**

- `cmd/` — entry points only (main.go + main_test.go).
- `internal/config/` — env var loading per module.
- `internal/tools/` — tool implementations (MCP servers).
- `internal/domain/` — business types and interfaces (talk module).
- `internal/llm/` — provider adapters (talk module).

**Formatting & Linting:**

- `gofmt` + `goimports` — mandatory, run via `make fmt`.
- `golangci-lint v2.12+` — run via `make lint` with v2 config format.
- No hand-organized imports — let `goimports` handle grouping.

**Documentation Sync:**

- When env vars change in `config/loader.go`, README.md "Environment variables" table MUST be updated.
- `.env.example` must stay in sync with the Config struct.

**Git & CI:**

- `make vet test` must pass before any merge.
- Each module tagged independently (`talk/v1.0.0`, `mcp-owm/v0.8.0`).
- CI runs without `go.work` — `replace` directives ensure builds work.

### Critical Don't-Miss Rules

**Anti-Patterns:**

- NEVER add `mattn/go-sqlite3` or any CGO dependency — pure Go only.
- NEVER import between application modules — only `talk-libs` is shared.
- NEVER use `wg.Add(1)` / `go func() { defer wg.Done() }()` — use `wg.Go(fn)`.
- NEVER store per-request state on HTTP client structs.
- NEVER use gorilla/mux, chi, or external routers — use stdlib `net/http.ServeMux` (Go 1.22+ patterns).
- NEVER use `interface{}` — use `any`.
- NEVER bump MCP/Anthropic/OpenAI SDKs without running `make test` on ALL modules.
- NEVER read env vars in `init()` — use config structs with safe defaults.
- NEVER hardcode external API URLs in tools — always injectable for tests.

**Edge Cases:**

- `go.work` masks broken `replace` directives — always verify CI passes without workspace.
- `description` tag missing on `TInput` field = LLM silently ignores the parameter.
- Docker build context must be workspace root — a Dockerfile that COPYs only its own module will fail.
- SQLite single-writer: `MaxOpenConns(1)` is mandatory — removing it causes `database is locked` errors.

**CLI-Specific (`talk/cmd/cli/`):**

- All output via `a.Printf`, `a.Println`, `a.Errorf` — never `fmt.Print*` directly.
- Never colorize user-provided content (LLM answers, prompt text, tool output).
- Only use the 6 ANSI helpers (`cyan`, `green`, `yellow`, `red`, `faint`, `emphasize`) — no external color libs.

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing any code.
- Follow ALL rules exactly as documented.
- When in doubt, prefer the more restrictive option.
- Update this file if new patterns emerge.

**For Humans:**

- Keep this file lean and focused on agent needs.
- Update when technology stack changes.
- Review quarterly for outdated rules.
- Remove rules that become obvious over time.

Last Updated: 2026-06-20
