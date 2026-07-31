## Deferred from: code review of 4-1-scaffold-projet-et-ci.md (2026-07-30)

- D1: `eslint.config.js` utilisait `.strict` au lieu de `.strictTypeChecked` — déjà corrigé en commit ultérieur
- D2: `tsconfig.app.json` manquait `exactOptionalPropertyTypes` — déjà corrigé en commit ultérieur
- D3: CI steps non pinnés à des SHA de commit — best practice sécurité, hors AC, choix délibéré
- D4: CI sans bloc `permissions` — amélioration sécurité, hors AC
- D5: CI build avant lint/format — préférence d'ordre, non bloquant
- D6: `package.json` sans `engines.pnpm` — hors AC
- D7: Pas de seuils de coverage dans vitest — hors AC
- D8: `.nvmrc` "22" vs engines `>=22.12.0` — incohérence mineure, intentionnelle
- D9: TanStack Router plugin Vite manquant — routes pré-générées et committées, intentionnel

## Deferred from: code review of 2-5-mcp-connection-resilience.md (2026-07-02)

- W1: `ConnectAll` leaks existing sessions when called a second time — pre-existing architecture limitation; `ConnectAll` is a bootstrap operation not designed for repeated calls.
- W2: `ConnectAll` briefly exposes empty tool/status state during re-bootstrap — would require atomic swap of full manager state to fix; larger refactor.
- W3: `rebuildToolsExcluding` has redundant O(n×m) inner loop — pre-existing; condition `adapter.serverID == excludeID` is sufficient without the `m.statuses` scan.
- W4: Reconnect orchestration (error detection + retry decision) lives in tool adapter instead of manager — pragmatic tradeoff per dev notes; `Reconnect()` is a manager method so the spirit is preserved.
- W5: `EnsureConnected` returns stale non-nil session without liveness check — intentional pragmatic design per dev notes ("MCP session object may still need explicit session recreation"); AC1 is satisfied since reconnect fires after the stale session's `CallTool` fails.

## Deferred from: code review of 2-2-tool-call-agui-events.md (2026-06-25)

- ConversationManager explicit ToolCallHandler overrides EventHandlers ToolCallEventHandler instead of composing both. This appears pre-existing in design direction and not required to satisfy current story acceptance criteria.

## Deferred from: code review of 6-1-5-ui-context-facade-copilotkit-presentation (2026-06-30)

- W1: Race condition between `agent.isRunning` guard and async `runAgent` completion — double-send theoretically possible in same React frame. Pre-existing pattern, window is near-zero with React 19 batching.
- W2: `copilotkit.runAgent().catch()` swallows non-Error rejections (e.g. string throws) with only a generic "unexpected error" message and no console.error. Pre-existing behavior.
- W3: `formatJson` in ToolCallItem renders arbitrarily large JSON payloads without truncation — potential DOM performance issue for very large tool results. Pre-existing.

## Deferred from: code review of 6-3-interrupt-max-iterations-continue (2026-07-30)

- If `agent.pendingInterrupts` only ever contains interrupts whose `reason` isn't `talk:max_iterations`, `pendingInterrupt` stays `null` forever and no UI ever appears — the agent would be left blocked with no affordance to unblock it. Deferred because only the `talk:max_iterations` reason exists in the product today; revisit once a second interrupt reason is introduced.
