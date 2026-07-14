# Story 6.2: Messages AG-UI type-safe (Zod) et suppression des casts

Status: done

## Story

As a frontend developer,
I want to parse and normalize AG-UI messages through explicit Zod schemas,
so that message handling is fully type-safe and no runtime casts are needed in the UI flow.

## Acceptance Criteria (BDD)

1. **Given** AG-UI messages arrive from CopilotKit/agent stream
   **When** they are consumed by frontend normalization
   **Then** each supported message shape is validated/parsé via Zod schemas
   **And** malformed/unsupported payloads are safely ignored or downgraded without crash.

2. **Given** the frontend renders normalized messages
   **When** TypeScript compiles under strict mode
   **Then** application code in the AG-UI handling path contains no `as` type assertions
   **And** no `any` usage is introduced.

3. **Given** reasoning, user/assistant text, tool-call containers and tool results
   **When** normalization runs
   **Then** ordering and reconciliation behavior from Story 6.1 remain unchanged
   **And** tool-call start/result matching still works for in-order and out-of-order events.

4. **Given** message content may be non-text or partially structured
   **When** the UI renders bubbles and blocks
   **Then** rendering relies on discriminated types/type guards produced by normalized models
   **And** no cast is needed in presentation components.

5. **Given** existing tests and CI gates
   **When** `pnpm lint && pnpm test && pnpm build` are executed
   **Then** all pass
   **And** new tests cover schema parsing success/failure and edge cases.

## Tasks / Subtasks

- [ ] Task 1: Introduce AG-UI schema layer with Zod (AC: #1, #3)
  - [ ] 1.1 Create `src/config/agui-schemas.ts` with Zod schemas for consumed message variants:
    - user/assistant/reasoning messages with content
    - assistant tool-call container messages (`toolCalls[]`)
    - tool result messages (`role: "tool"`, optional `toolCallId`)
  - [ ] 1.2 Create a typed parser API returning discriminated unions for normalization boundary.
  - [ ] 1.3 Encode tolerant parsing strategy:
    - hard reject malformed core fields
    - gracefully skip unsupported message variants
    - keep parser pure and deterministic.

- [ ] Task 2: Refactor normalization to parser-first flow (AC: #1, #2, #3)
  - [ ] 2.1 Update `src/config/normalize-messages.ts` to consume parser outputs instead of structural casts.
  - [ ] 2.2 Remove all `as` assertions in this file, including tool-call array assertions.
  - [ ] 2.3 Preserve existing reconciliation logic:
    - pending tool results map
    - oldest unmatched fallback
    - unresolved completion on assistant final content.
  - [ ] 2.4 Keep output contract `ChatMessageViewModel` stable for current consumers.

- [ ] Task 3: Remove casts from presentation path (AC: #2, #4)
  - [ ] 3.1 Update `src/components/ChatView.tsx` to avoid `content as string` by using narrowed message types.
  - [ ] 3.2 Update `src/components/MessageBubble.tsx` to avoid structural cast when reading non-text content type.
  - [ ] 3.3 If needed, introduce dedicated type guards/helpers in `src/config/` to keep components simple.

- [ ] Task 4: Strengthen lint/static guardrails for no-cast policy (AC: #2, #5)
  - [ ] 4.1 Add/adjust ESLint rule set to block unsafe assertions in app code (excluding generated files/tests where justified).
  - [ ] 4.2 Keep `src/routeTree.gen.ts` excluded as generated code.
  - [ ] 4.3 Ensure rule changes do not create noise in unrelated code.

- [ ] Task 5: Tests for parser, normalization, and rendering invariants (AC: #1, #3, #4, #5)
  - [ ] 5.1 Add parser tests in `src/__tests__/agui-schemas.test.ts`:
    - valid payloads parse successfully
    - malformed payloads fail predictably
    - unknown roles/shapes are safely handled.
  - [ ] 5.2 Extend `src/__tests__/normalize-messages.test.ts` to assert unchanged behavior for:
    - mixed tool-call/tool-result ordering
    - reasoning chronology
    - assistant content + toolCalls coexistence.
  - [ ] 5.3 Update `src/__tests__/chat-view.test.tsx` and/or `src/__tests__/message-bubble.test.tsx` to confirm no behavior drift in rendering with typed content.
  - [ ] 5.4 Run full gates: lint, tests, build.

## Dev Notes

### Scope boundaries

- In scope: `talk-ui` frontend only.
- Out of scope: backend AG-UI event format changes, CopilotKit transport internals, UI redesign.

### Files targeted

- `src/config/normalize-messages.ts` (primary)
- `src/config/agui-schemas.ts` (new)
- `src/components/ChatView.tsx`
- `src/components/MessageBubble.tsx`
- `src/__tests__/normalize-messages.test.ts`
- `src/__tests__/chat-view.test.tsx`
- `src/__tests__/message-bubble.test.tsx`
- `src/__tests__/agui-schemas.test.ts` (new)
- `eslint.config.js` (if rule hardening required)

### Architecture guardrails

1. Keep parser boundary centralized in `src/config/`.
2. Normalize once, render many: components do not parse protocol-level payloads.
3. Prefer discriminated unions and type guards over assertions.
4. Preserve current UX behavior exactly (layout, ordering, labels, tool visibility).

### Suggested implementation sequence

1. Add Zod schemas + typed parser.
2. Switch normalization to parsed union inputs.
3. Remove casts in `ChatView` and `MessageBubble` via narrowed models.
4. Add/update tests.
5. Tighten lint rule if needed, then run gates.

### Definition of Done

- No `as` assertions in AG-UI message pipeline and related presentation path.
- No new `any` introduced.
- Zod parser covers all message variants currently consumed by the app.
- Existing behavior is preserved (verified by tests).
- `pnpm lint && pnpm test && pnpm build` all green.

## Risks / Mitigations

- Risk: Over-strict schemas reject legitimate variants from upstream.
  - Mitigation: Use explicit tolerant union strategy + fallback handling for unknown variants.
- Risk: Refactor alters tool-call reconciliation behavior.
  - Mitigation: Lock existing behavior with regression tests before/after parser switch.
- Risk: Lint hardening creates churn in non-targeted files.
  - Mitigation: Scope lint rules to source folders and keep generated/test exceptions explicit.

## Review Findings

- [x] [Review][Patch] P1: `ChatView.tsx` fallback silencieux `""` pour reasoning — `typeof msg.content === "string" ? msg.content : ""` masque une invariant garantie par `handleTextMessage`; si celle-ci est cassée à l'avenir, un bloc vide s'affiche sans log ni erreur [src/components/ChatView.tsx]
- [x] [Review][Patch] P2: `ChatMessageViewModel.content` reste `unknown` pour tous les rôles texte — `handleTextMessage` garantit à l'exécution que `reasoning.content` est un `string`, mais le type statique ne le reflète pas, forçant une garde runtime dans `ChatView` [src/config/normalize-messages.ts]
- [x] [Review][Patch] P4: Task 4 (ESLint guardrail) non implémentée — aucune règle `@typescript-eslint/consistent-type-assertions` dans `eslint.config.js`; la conformité "zéro cast dans le pipeline AG-UI" repose sur la vigilance humaine, pas sur le linter [eslint.config.js]
- [ ] [Review][Defer] P3: `toolCallContainerSchema` rejette toute la liste si un seul toolCall est malformé — si le LLM retourne un assistant message avec 3 outil calls dont 1 sans `function.name`, les 2 valides disparaissent silencieusement; `z.array(toolCallSchema).catch(...)` serait plus tolérant mais ajoute de la complexité [src/config/agui-schemas.ts]
- [ ] [Review][Defer] W1: `e.target as Node` dans `ModelSelector` et `ThinkingEffortSelector` — pattern DOM standard hors scope AG-UI de la story; pas d'alternative type-safe simple [src/components/ModelSelector.tsx, src/components/ThinkingEffortSelector.tsx]
- [ ] [Review][Defer] W2: `toolCallContainerSchema` accepte `toolCalls: []` (array vide) — produit 0 VM sans erreur; cas théorique inoffensif, non couvert par les tests [src/config/agui-schemas.ts]
- [ ] [Review][Decision] D1: `content: z.unknown()` pour tous les rôles texte — conforme à la spec AG-UI multi-modal; restreindre à `z.string()` casserait le test "keeps assistant messages with non-string content"; choix délibéré, dette gérée via P2
- [ ] [Review][Decision] D2: `normalizeMessages` accepte `ReadonlyArray<Record<string, unknown>>` au lieu de `Message[]` — supprime le couplage au SDK AG-UI dans la couche normalisation; la compatibilité structurelle avec `Message` est vérifiée au build; acceptable

### Acceptance Criteria Coverage (post-review)

| AC                                             | Statut     | Note                                                                                                              |
| ---------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------- |
| AC#1 — Zod parser pour tous les variants       | ✅         | `agui-schemas.ts` couvre user/assistant/reasoning/tool-call/tool-result                                           |
| AC#2 — Zéro `as` dans le pipeline AG-UI        | ✅ sauf P4 | Supprimé de `normalize-messages`, `MessageBubble`; garde runtime en `ChatView` (P1); pas de lint enforcement (P4) |
| AC#3 — Comportement de réconciliation inchangé | ✅         | Tests couvrent in-order, out-of-order, unresolved finalization                                                    |
| AC#4 — Rendu basé sur types discriminés        | ✅ partiel | `MessageBubble` utilise `isWithType` guard; `ChatView` reasoning: fallback runtime (P2)                           |
| AC#5 — Gates CI passent + tests parser         | ✅         | 122 tests verts; `agui-schemas.test.ts` couvre happy path et malformed inputs                                     |

## Dev Agent Record

### Completion Notes

- Implementation substantially complete at story creation time (2026-07-05): `agui-schemas.ts`, parser-first `normalize-messages.ts`, `isWithType` guard in `MessageBubble`, `agui-schemas.test.ts` all in place.
- Remaining open items: P1 (fallback invariant), P2 (content type narrowing), P4 (ESLint rule).

## Change Log

- 2026-07-05: Story created for frontend AG-UI type-safety alignment with local TypeScript skill (Zod boundary + no cast policy).
- 2026-07-06: Review findings added (P1, P2, P3/defer, P4, W1/defer, W2/defer, D1, D2) — implementation largely done, 3 patches remain open.
- 2026-07-06: P1, P2, P4 applied — `TextMessage` split into discriminated union (reasoning: `content: string`), `ChatMessageViewModel` replaced by `ContentMessageVM | ReasoningMessageVM | ToolCallMessageVM`, `ChatView` guard removed, `consistent-type-assertions` rule added. 142 tests pass.
