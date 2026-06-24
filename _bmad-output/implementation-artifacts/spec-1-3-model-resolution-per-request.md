---
title: "Story 1.3: Model resolution per request via forwardedProps"
type: "feature"
created: "2025-06-25"
status: "in-progress"
context:
  - "{project-root}/talk/internal/domain/model.go"
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The AG-UI server currently requires a `--model` flag at startup, locking all requests to a single LLM. The frontend should choose the model per request via `forwardedProps.model`, matching the principle that model is a user choice, not an agent configuration.

**Approach:** Extract `forwardedProps.model` from RunAgentInput in the handler, validate presence and registry membership, pass the resolved alias to ChatFunc which performs per-request LLM client creation. Remove the `--model` required flag from `talk serve`.

## Boundaries & Constraints

**Always:** Model alias is mandatory — reject requests without it. Error messages list available models. Use `domain.Lookup` and `router.Get` for resolution. AG-UI error events for validation failures (not HTTP errors).

**Ask First:** Adding a default/fallback model if forwardedProps is absent.

**Never:** Cache LLM clients across requests (stateless per request for now). Do not add model validation to the handler package directly (keep domain dependency in serve.go's chatFn). Do not break existing handler_test.go patterns.

## I/O & Edge-Case Matrix

| Scenario                 | Input / State                             | Expected Output / Behavior                  | Error Handling                            |
| ------------------------ | ----------------------------------------- | ------------------------------------------- | ----------------------------------------- |
| Valid model              | `forwardedProps: {"model": "sonnet-4.6"}` | Model resolved, LLM called, normal SSE flow | N/A                                       |
| Missing forwardedProps   | `forwardedProps: null` or absent          | SSE error event before RUN_STARTED          | Message lists available models            |
| Empty model              | `forwardedProps: {"model": ""}`           | SSE error event before RUN_STARTED          | Message lists available models            |
| Unknown model            | `forwardedProps: {"model": "unknown"}`    | SSE error event before RUN_STARTED          | Message includes alias + available models |
| forwardedProps not a map | `forwardedProps: "string"`                | SSE error event before RUN_STARTED          | Message lists available models            |

</frozen-after-approval>

## Code Map

- `talk/internal/agui/handler.go` -- AG-UI handler: add model extraction from forwardedProps, update ChatFunc signature
- `talk/internal/agui/handler_test.go` -- Tests for model validation scenarios
- `talk/cmd/cli/serve.go` -- Remove --model required flag, move resolution into per-request chatFn

## Tasks & Acceptance

**Execution:**

- [ ] `talk/internal/agui/handler.go` -- Change ChatFunc signature to add modelAlias string param; extract model from input.ForwardedProps; emit error event if missing/invalid
- [ ] `talk/internal/agui/handler_test.go` -- Add tests for missing model, empty model, valid model passthrough, non-map forwardedProps
- [ ] `talk/cmd/cli/serve.go` -- Remove --model required flag; in chatFn resolve model via router.Get + domain.Lookup per request; format user-facing error for unknown model

**Acceptance Criteria:**

- Given a valid `forwardedProps.model`, when POST /agent, then the corresponding LLM is used for that request
- Given missing forwardedProps.model, when POST /agent, then an AG-UI error event lists available models (no RUN_STARTED emitted)
- Given an unknown model alias, when POST /agent, then an AG-UI error event includes the bad alias and lists valid models
- Given `talk serve` started without --model flag, when requests arrive with different model aliases, then each uses its own model

## Verification

**Commands:**

- `cd talk && go test ./internal/agui/ -run TestHandler -v` -- expected: all handler tests pass
- `cd talk && go build ./cmd/cli/` -- expected: compiles without --model required
