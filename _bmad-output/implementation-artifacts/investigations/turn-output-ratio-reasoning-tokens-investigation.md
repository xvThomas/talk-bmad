# Investigation: Turn output ratio and reasoning-token accounting

## Hand-off Brief

1. **What happened.** UI review raised two questions: whether a per-call output ratio is useful when only published at turn completion, and whether backend `ReasoningTokens` is preserved, lost, or included in another token counter.
2. **Where the case stands.** Active; direct references confirm `ReasoningTokens` exists in the domain usage aggregate, OpenAI conversion, console observability, and AG-UI payload construction, but its full provider-to-stream path and accounting semantics are not yet traced.
3. **What's needed next.** Trace every provider adapter and the turn aggregation path, then compare output-ratio semantics with the user-facing information need.

## Case Info

| Field | Value |
| --- | --- |
| Ticket | Story 10.3 follow-up |
| Date opened | 2026-09-16 |
| Status | Active |
| System | talk-backend and Story 10.3 frontend usage contract |
| Evidence sources | User UI observation; backend source and tests; planning artifacts |

## Problem Statement

User report: "1. je ne vois pas l'interet d'afficher le ratio out car il represnte uniquement la derniere iteration du tour et ce n'est pas forcement le plus conséquent. 2. Je vois pas dans le code un réel usage de reasoning_token, soit il est perdu soit il est pris en compte dans l'input_token, pouvez analyser ?"

The report contains two hypotheses: the final-call output ratio may not be useful to users, and reasoning-token data may either be lost or folded into input tokens.

## Evidence Inventory

| Source | Status | Notes |
| --- | --- | --- |
| `talk-backend/talk/internal/domain/message_event_handlers.go` | Available | Defines and adds `ReasoningTokens` independently from input/output counts. |
| `talk-backend/talk/internal/llm/openai/converter.go` | Available | Maps OpenAI completion reasoning-token details into domain usage. |
| `talk-backend/talk/internal/domain/token_usage.go` | Available | Copies reasoning tokens into per-call and per-turn AG-UI payloads. |
| Provider adapters other than OpenAI | Partial | Not yet traced. |
| Turn aggregation and event emission | Partial | Known entry points, full caller chain not yet traced. |
| Runtime provider responses/logs | Missing | Needed to verify actual non-zero values by model/provider. |

## Investigation Backlog

| # | Path to Explore | Priority | Status | Notes |
| --- | --- | --- | --- | --- |
| 1 | Trace `Usage.ReasoningTokens` from every provider response into `MessageEvent` | High | Open | Determine provider coverage and semantics. |
| 2 | Trace `Usage.Add` through turn aggregation and `turn_usage` emission | High | Open | Confirm no loss and no double counting. |
| 3 | Inspect tests for non-zero reasoning counts across per-call and turn events | High | Open | Confirm contract behavior. |
| 4 | Establish whether reasoning tokens are included in provider output totals | High | Open | Provider-specific accounting distinction. |
| 5 | Assess `output_ratio` user value against final-call versus whole-turn semantics | Medium | Open | Product/UX conclusion grounded in contract. |

## Timeline of Events

| Time | Event | Source | Confidence |
| --- | --- | --- | --- |
| 2026-09-16 | Story 10.3 UI displayed per-call context and output ratios. | Story implementation artifact | Confirmed |
| 2026-09-16 | UI review identified unstable within-turn display; publication-at-turn-end proposed. | User observation | Confirmed |
| 2026-09-16 | User questioned final-call output-ratio value and reasoning-token accounting. | User input | Confirmed |

## Confirmed Findings

### Finding 1: Reasoning tokens are a separate domain usage field

**Evidence:** `talk-backend/talk/internal/domain/message_event_handlers.go:52`, `talk-backend/talk/internal/domain/message_event_handlers.go:62`

**Detail:** The domain model stores `ReasoningTokens` independently and sums it independently in `Usage.Add`; it is not explicitly merged into `InputTokens` at this layer.

### Finding 2: OpenAI reasoning tokens are captured from completion-token details

**Evidence:** `talk-backend/talk/internal/llm/openai/converter.go:91`

**Detail:** The OpenAI converter maps `CompletionTokensDetails.ReasoningTokens` into `domain.Usage.ReasoningTokens`.

### Finding 3: Reasoning tokens are exposed in both usage event payloads

**Evidence:** `talk-backend/talk/internal/domain/token_usage.go:35`, `talk-backend/talk/internal/domain/token_usage.go:51`

**Detail:** Both per-call `token_usage` and aggregate `turn_usage` payload constructors copy the field when non-zero.

## Deduced Conclusions

### Deduction 1: Reasoning tokens are not lost in the known OpenAI-to-AG-UI path

**Based on:** Findings 1–3.

**Reasoning:** OpenAI response details populate a distinct domain field; aggregation retains it; payload construction emits it.

**Conclusion:** The current direct evidence contradicts the hypothesis that reasoning tokens are universally discarded. Provider coverage and whether provider-reported `output_tokens` already includes reasoning remain open.

## Hypothesized Paths

### Hypothesis 1: Reasoning tokens are lost or included in input tokens

**Status:** Open

**Theory:** The backend may fail to preserve reasoning counts, or providers may report them as input.

**Supporting indicators:** The UI does not prominently display the field, and only one provider mapping has been located so far.

**Would confirm:** A provider adapter lacking available reasoning-token mapping, or provider documentation/code showing reasoning included in prompt/input count.

**Would refute:** Complete provider traces showing separate capture and emission, with tests/runtime evidence for non-zero values.

**Resolution:** Partial refutation for OpenAI: the field is captured separately from completion details and emitted. Other providers and accounting inclusion remain open.

### Hypothesis 2: Final-call output ratio is not meaningful enough for the compact indicator

**Status:** Open

**Theory:** The final LLM call's output length may be small after tool iterations and does not represent the turn's largest or total output consumption.

**Supporting indicators:** `token_usage` is per-call while `turn_usage.output_tokens` is the authoritative whole-turn sum; final-call publication changes timing but not the per-call scope.

**Would confirm:** Product intent focuses on turn-level consumption or output-capacity risk, for which final-call ratio is not representative.

**Would refute:** A concrete user need to know whether the final provider response approached its per-call output ceiling.

**Resolution:** Pending contract and UX assessment.

## Missing Evidence

| Gap | Impact | How to Obtain |
| --- | --- | --- |
| Anthropic and other provider usage conversions | Cannot conclude provider-wide reasoning preservation | Trace all implementations constructing `domain.Usage`. |
| Provider accounting semantics | Cannot say whether reasoning is included in output totals as well as exposed separately | Inspect SDK response fields and provider documentation/tests. |
| Real non-zero runtime usage | Cannot verify production model behavior | Capture a response or console event from a reasoning-enabled model. |

## Source Code Trace

| Element | Detail |
| --- | --- |
| Error origin | N/A — exploratory usage-accounting investigation |
| Trigger | Completed LLM call and completed/interrupted turn |
| Condition | Provider returns usage metadata; emitter serializes per-call and aggregate usage |
| Related files | `domain/message_event_handlers.go`, `llm/openai/converter.go`, `domain/token_usage.go`, `agui/emitter.go`, provider adapters/tests |

## Conclusion

**Confidence:** Low (investigation active)

Reasoning tokens are demonstrably preserved for the known OpenAI path and copied into AG-UI event payloads. It remains unconfirmed whether all providers populate them and whether provider output totals already include reasoning tokens. The output-ratio usefulness question requires distinguishing final-call output-ceiling pressure from whole-turn consumption.

## Recommended Next Steps

### Fix direction

Pending investigation.

### Diagnostic

Trace all provider usage converters, turn aggregation, and relevant tests; establish provider accounting semantics.

## Reproduction Plan

Run a reasoning-enabled model call, capture provider usage, domain `MessageEvent.Usage`, `TurnEvent.TotalUsage`, and emitted custom-event payloads, then compare all token categories.

## Side Findings

- The backend already logs reasoning counts in console observability when non-zero (`talk-backend/talk/internal/observability/console.go:34-35`, `:71-72`).

## Follow-up: 2026-09-16

### New Evidence

- Anthropic converter maps `InputTokens`, `OutputTokens`, `CacheReadInputTokens`, and `CacheCreationInputTokens`, but no reasoning-token field: `talk-backend/talk/internal/llm/anthropic/converter.go:135-140`.
- The installed Anthropic SDK `v1.27.1` `anthropic.Usage` exposes no `ThinkingTokens` or `OutputTokensDetails` field; it exposes only input/output/cache and related metadata in `message.go:8042-8080`.
- Anthropic's official extended-thinking documentation states that thinking tokens are part of billed output tokens and can be monitored through `usage.output_tokens_details.thinking_tokens` on the API response. The current SDK model does not expose that breakdown to this code.
- OpenAI conversion maps `CompletionTokens` to domain `OutputTokens` and separately maps `CompletionTokensDetails.ReasoningTokens` to domain `ReasoningTokens`: `talk-backend/talk/internal/llm/openai/converter.go:87-91`.
- Turn aggregation adds `Usage` fields independently, including reasoning: `talk-backend/talk/internal/domain/conversation.go:156-158` and `message_event_handlers.go:52-62`.
- Both normal completion and max-iteration/interrupted paths emit one `TurnEvent` with `TotalUsage`: `talk-backend/talk/internal/domain/conversation.go:168-186` and `203-218`.
- Focused backend tests pass: OpenAI, Anthropic, domain, and AG-UI packages.

### Additional Findings

#### Finding 4: The current Anthropic path loses the reasoning-token breakdown

**Evidence:** `anthropic/converter.go:135-140`; Anthropic SDK `v1.27.1` `message.go:8042-8080`.

**Detail:** Anthropic thinking content is parsed into `Message.Thinking` (`converter.go:114-123`), but the API usage response is converted without a reasoning-token field. Therefore `domain.Usage.ReasoningTokens` remains zero for Anthropic calls. This is not folded into `InputTokens` by the application; it is simply unavailable in the current conversion path.

#### Finding 5: OpenAI reasoning tokens are separate metadata but part of completion/output accounting

**Evidence:** `openai/converter.go:87-91`; domain `Usage` definition and `Usage.Add`.

**Detail:** The application keeps `ReasoningTokens` separate for observability while taking the provider's aggregate `CompletionTokens` as `OutputTokens`. Thus reasoning tokens are not added to `InputTokens` and are not added again to `OutputTokens` by this code. The provider's `CompletionTokens` is the authoritative output total; `ReasoningTokens` is its breakdown where available.

#### Finding 6: Anthropic output ratio is a final-call output-capacity ratio, not turn output consumption

**Evidence:** `domain/token_usage.go:36-39`; `conversation.go:156-186`; Anthropic converter.

**Detail:** `output_ratio` is computed per `token_usage` from one call's `OutputTokens / ProviderMaxOutputTokens`. A tool-loop turn can have several such calls, while `turn_usage.OutputTokens` is their sum. Therefore the last call's output ratio cannot represent the whole-turn output consumption and is a poor compact indicator for the user's stated goal. It may still be meaningful as a provider-call diagnostic, but not as a primary turn indicator.

### Updated Conclusion

**Confidence:** High for current-code behavior; medium for provider API semantics beyond the exposed SDK fields.

1. `output_ratio` should be removed from the compact `ctx/out` indicator under the revised UX. The frontend may retain raw per-call output data in details only if a diagnostic use case is desired; otherwise it can be omitted from the user-facing indicator entirely. Whole-turn output counts remain available from authoritative `turn_usage`.
2. OpenAI reasoning tokens are preserved separately, not included in input by application code, and are already included in the provider's aggregate completion/output token count. They are emitted in both usage events.
3. Anthropic reasoning tokens are currently not captured as a numeric domain field. Thinking text is retained, but the token breakdown is absent from `anthropic.Usage` v1.27.1 as used here. According to Anthropic's documentation, thinking tokens are part of billed output tokens and the API exposes a `usage.output_tokens_details.thinking_tokens` breakdown, but the current SDK struct does not expose it. Capturing it would require an SDK upgrade that adds the field or explicit parsing of the raw JSON response; it should not be inferred from input tokens.

### Recommended Story 10.3 Adjustment

- Buffer the latest valid `token_usage` during a turn and publish it only when `turn_usage` arrives.
- Remove `output_ratio` and the compact `out` percentage from the primary indicator; retain turn-level `output_tokens` in cumulative/details views if desired.
- Keep `reasoning_tokens` as an optional field. OpenAI can populate it; Anthropic remains omitted until the SDK/raw-response path is deliberately extended.
- Add a separate follow-up backend story if Anthropic reasoning-token breakdown is required, because it is outside the frontend-only scope of Story 10.3.
