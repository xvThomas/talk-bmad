## Deferred from: code review of 2-2-tool-call-agui-events.md (2026-06-25)

- ConversationManager explicit ToolCallHandler overrides EventHandlers ToolCallEventHandler instead of composing both. This appears pre-existing in design direction and not required to satisfy current story acceptance criteria.
