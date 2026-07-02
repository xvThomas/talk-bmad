## Deferred from: code review of 2-2-tool-call-agui-events.md (2026-06-25)

- ConversationManager explicit ToolCallHandler overrides EventHandlers ToolCallEventHandler instead of composing both. This appears pre-existing in design direction and not required to satisfy current story acceptance criteria.

## Deferred from: code review of 6-1-5-ui-context-facade-copilotkit-presentation (2026-06-30)

- W1: Race condition between `agent.isRunning` guard and async `runAgent` completion — double-send theoretically possible in same React frame. Pre-existing pattern, window is near-zero with React 19 batching.
- W2: `copilotkit.runAgent().catch()` swallows non-Error rejections (e.g. string throws) with only a generic "unexpected error" message and no console.error. Pre-existing behavior.
- W3: `formatJson` in ToolCallItem renders arbitrarily large JSON payloads without truncation — potential DOM performance issue for very large tool results. Pre-existing.
