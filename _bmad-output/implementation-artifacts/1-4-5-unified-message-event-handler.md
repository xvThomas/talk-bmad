---
baseline_commit: null
---

# Story 1.4.5: Unification MessageEventHandler et AGUIEmitter

Status: not-started

## Story

As a developer,
I want a single `MessageEventHandler` interface that handles all conversation lifecycle events (messages, turns, tool calls),
so that the AG-UI serve path can use a single `AGUIEmitter` for all SSE content events and the architecture is symmetric between CLI and serve.

## Context

- Actuellement deux interfaces : `MessageEventHandler` (2 méthodes) et `ToolCallEventHandler` (2 méthodes).
- `ToolCallEventHandler` est dispatché via type assertion dans `MessageEventHandlers.HandleToolCallStart/End`.
- Le handler HTTP émet `TEXT_MESSAGE_*` après le retour de `chatFn` — c'est asymétrique avec les tool call events émis pendant `Chat()`.
- `ToolCallEmitter` (agui) implémente uniquement `ToolCallEventHandler` et est passé via `ConversationManagerConfig.ToolCallHandler`.
- `ConsoleUsageReporter` implémente déjà les deux interfaces.
- Le CLI ne passe PAS de `ToolCallHandler` — les tool call events ne sont actuellement pas émis dans le CLI (le `ToolExecutor` reçoit nil). Après ce refactoring, le `ConsoleUsageReporter` (déjà dans le pipeline) recevra naturellement les tool call events.
- Après ce refactoring, un seul `AGUIEmitter` implémentant `MessageEventHandler` gère TOUT le contenu SSE (text + tool calls). Le handler HTTP ne conserve que le lifecycle du run (`RUN_STARTED`/`RUN_FINISHED`/`RUN_ERROR`).

## Acceptance Criteria

1. **Given** la suppression de `ToolCallEventHandler`, **when** un tool call est exécuté par le `ToolExecutor`, **then** les events `HandleToolCallStart`/`HandleToolCallEnd` sont dispatched via `MessageEventHandler` (plus de type assertion).

2. **Given** le champ `ConversationManagerConfig.ToolCallHandler` supprimé, **when** un `ConversationManager` est créé, **then** le `ToolExecutor` utilise le même `MessageEventHandler` que celui passé dans `EventHandlers`.

3. **Given** un `AGUIEmitter` enregistré comme `MessageEventHandler` dans le pipeline, **when** le LLM retourne une réponse finale (sans tool calls), **then** l'emitter émet `TEXT_MESSAGE_START` → `TEXT_MESSAGE_CONTENT` → `TEXT_MESSAGE_END` via SSE.

4. **Given** un `AGUIEmitter` enregistré dans le pipeline, **when** un tool call est exécuté, **then** l'emitter émet `TOOL_CALL_START` → `TOOL_CALL_ARGS` → `TOOL_CALL_END` via SSE (même comportement que l'ancien `ToolCallEmitter`).

5. **Given** le handler HTTP, **when** `chatFn` retourne avec succès, **then** le handler n'émet plus de `TEXT_MESSAGE_*` — seuls `RUN_STARTED`/`RUN_FINISHED`/`RUN_ERROR` restent dans le handler.

6. **Given** le CLI avec `ConsoleUsageReporter`, **when** un turn avec tool calls s'exécute, **then** le `ConsoleUsageReporter` reçoit les tool call events via le pipeline (nouveau comportement : les tool calls sont désormais loggées dans le CLI).

7. **Given** un client qui se déconnecte pendant l'émission d'events, **when** le contexte est annulé, **then** l'`AGUIEmitter` retourne nil sans écrire et `Chat()` détecte la cancellation au prochain appel LLM.

8. **Given** la boucle tool atteint `maxToolCalls`, **when** `Chat()` retourne `ErrMaxToolIterations`, **then** les tool call events intermédiaires ont déjà été émis via SSE, et le handler émet `RUN_ERROR` avec le message user-friendly.

## Acceptance Criteria Additionnels

9. **Given** la règle projet limite les interfaces à 1-3 méthodes (cf. `_bmad-output/planning-artifacts/epics.md`), **when** la story 1.4.5 finalise les interfaces de handlers, **then** une dérogation formelle est appliquée: `MessageEventHandler` conserve 4 méthodes car elle représente un lifecycle conversationnel complet et cohérent (messages, turns, tool calls). Garde-fous: aucune méthode supplémentaire ne peut être ajoutée sans ADR explicite.

10. **Given** `AGUIEmitter` émet des events SSE, **when** une erreur d'écriture survient (annulation, déconnexion ou erreur inattendue), **then** `AGUIEmitter` journalise l'erreur avec contexte structuré (niveau warn pour erreur inattendue, debug pour annulation/déconnexion) et retourne nil dans tous les cas. Le run continue en best effort sans interruption du pipeline.

11. **Given** un run est proche de sa fin, **when** le contexte est annulé avant la terminalisation, **then** le système applique une politique terminale déterministe et n'émet pas d'events terminaux contradictoires.

12. **Given** l'émission SSE et la persistence s'exécutent en parallèle, **when** l'émission SSE échoue mais la persistence réussit (ou inversement), **then** le run se termine en best effort: `RUN_FINISHED` est émis si `chatFn` retourne sans erreur, indépendamment du succès de livraison SSE. Un échec de persistence remonte via le pipeline et déclenche `RUN_ERROR`.

13. **Given** les signatures `ChatFunc` et `ConversationManager` évoluent, **when** la migration est implémentée, **then** le déploiement est réalisé par étapes avec checklist d'impact complète (call sites, mocks, tests), **and** aucune régression de contrat d'events n'est introduite sur les parcours serve et CLI.

14. **Given** la story 1.4.5 est implémentée, **when** la validation est exécutée, **then** elle couvre au minimum: (1) erreur SSE liée à annulation versus erreur SSE inattendue, (2) déconnexion client juste avant émission de l'event terminal, (3) stream réussi avec persistence en échec, (4) persistence réussie avec stream partiellement en échec, (5) vérification bout en bout du contrat d'events pour scénario sans outil et scénario avec outils.

## Tasks / Subtasks

- [ ] Task 1: Fusionner `ToolCallEventHandler` dans `MessageEventHandler` (AC: #1, #9)
  - [ ] Dans `talk/internal/domain/usage.go`, ajouter `HandleToolCallStart(ctx context.Context, event ToolCallEvent) error` et `HandleToolCallEnd(ctx context.Context, event ToolCallEndEvent) error` à l'interface `MessageEventHandler`
  - [ ] Supprimer l'interface `ToolCallEventHandler`
  - [ ] Mettre à jour `NoOpMessageEventHandler` avec les 2 nouvelles no-op
  - [ ] Simplifier `MessageEventHandlers` : remplacer les dispatch par type assertion par des appels directs aux méthodes

- [ ] Task 2: Adapter les implémenteurs existants (AC: #1, #6)
  - [ ] `ConsoleUsageReporter` : supprimer `var _ ToolCallEventHandler`, les méthodes existent déjà — elles seront désormais appelées via le pipeline
  - [ ] `MessageRepository` (inmemory + sqlite) : ajouter `HandleToolCallStart`/`HandleToolCallEnd` no-op
  - [ ] `LangfuseUsageReporter` : ajouter `HandleToolCallStart`/`HandleToolCallEnd` no-op
  - [ ] Mettre à jour les mocks/recorders dans les tests

- [ ] Task 3: Modifier `ToolExecutor` pour utiliser `MessageEventHandler` (AC: #2)
  - [ ] Changer le champ `toolHandler ToolCallEventHandler` → `eventHandler MessageEventHandler`
  - [ ] Mettre à jour `NewToolExecutor` signature
  - [ ] Les appels `e.toolHandler.HandleToolCallStart/End` deviennent `e.eventHandler.HandleToolCallStart/End`

- [ ] Task 4: Supprimer `ToolCallHandler` de `ConversationManagerConfig` (AC: #2)
  - [ ] Supprimer le champ `ToolCallHandler ToolCallEventHandler`
  - [ ] Dans `NewConversationManager`, passer `messageHandler` directement au `ToolExecutor`
  - [ ] Supprimer la logique de fallback (`if cfg.ToolCallHandler != nil ... else if h, ok := messageHandler.(ToolCallEventHandler)`)
  - [ ] Dans `serve.go`, supprimer le passage de `ToolCallHandler: toolHandler`

- [ ] Task 5: Créer `AGUIEmitter` (AC: #3, #4, #5, #7, #10, #11)
  - [ ] Dans `talk/internal/agui/emitter.go`, créer `AGUIEmitter` struct avec `sse *SSEWriter`, `log *slog.Logger`
  - [ ] Implémenter `var _ domain.MessageEventHandler = (*AGUIEmitter)(nil)`
  - [ ] `HandleToolCallStart` : émet `TOOL_CALL_START` + `TOOL_CALL_ARGS` (reprise du code de `ToolCallEmitter`)
  - [ ] `HandleToolCallEnd` : émet `TOOL_CALL_END`
  - [ ] `HandleMessageEvent` : si `Role == RoleAssistant && len(ToolCalls) == 0 && Content != ""` → émet `TEXT_MESSAGE_START` → `TEXT_MESSAGE_CONTENT` → `TEXT_MESSAGE_END`
  - [ ] `HandleTurnEvent` : no-op
  - [ ] Sur erreur d'écriture SSE : retourner nil (ne pas remonter l'erreur — le stream est mort, `ctx.Err()` sera détecté au prochain point de contrôle dans `Chat()`)
  - [ ] Vérifier `ctx.Err()` avant chaque écriture SSE — si annulé, retourner nil immédiatement
  - [ ] Supprimer `tool_events.go` et `tool_events_test.go` (`ToolCallEmitter`)

- [ ] Task 6: Refactorer `serve.go` pour utiliser le pipeline (AC: #3, #4, #5, #12)
  - [ ] Instancier `AGUIEmitter` dans `chatFn` (accès au `SSEWriter` via `ChatOptions`)
  - [ ] Construire `NewMessageEventHandlers([][]MessageEventHandler{{aguiEmitter, messages}})` — même phase, exécution parallèle (le storage ne doit PAS dépendre du succès de l'écriture SSE)
  - [ ] Passer ce pipeline comme `EventHandlers` dans `ConversationManagerConfig`

- [ ] Task 7: Refactorer `ChatFunc` et le handler HTTP (AC: #5, #11, #13)
  - [ ] Nouvelle signature : `type ChatFunc func(ctx context.Context, threadID string, modelAlias string, messages []types.Message, opts ChatOptions) error`
  - [ ] `ChatOptions` : `struct { SSEWriter *SSEWriter }` — pas de `ThinkingEffort` ici (story 1.5)
  - [ ] Dans le handler HTTP, supprimer l'émission de `TEXT_MESSAGE_*` après `chatFn`
  - [ ] Le handler ne conserve que : `RUN_STARTED` → `chatFn()` → `RUN_FINISHED` / `RUN_ERROR`
  - [ ] Supprimer le retour `string` de `ChatFunc` — le handler n'utilise plus la réponse textuelle pour le SSE
  - [ ] Ajouter une checklist de migration API (call sites, mocks, tests) et exécuter la migration par étapes
  - [ ] Mettre à jour tous les tests du handler et migrer ceux de `tool_events_test.go` vers les tests de `AGUIEmitter`

- [ ] Task 8: Vérifier le CLI (AC: #6)
  - [ ] Le CLI (`main.go`) ne passe déjà pas de `ToolCallHandler` — la suppression du champ n'impacte pas la config CLI
  - [ ] Le `ToolExecutor` du CLI reçoit désormais le pipeline `handlers` (store + reporters) → le `ConsoleUsageReporter` recevra les `HandleToolCallStart/End` — c'est un nouveau comportement (les tool calls sont maintenant loggées dans le CLI)
  - [ ] Vérifier que le format console des tool call events est acceptable (il l'est déjà — `ConsoleUsageReporter.HandleToolCallStart` imprime le nom et les args)
  - [ ] Exécuter les tests CLI existants — aucune régression attendue

- [ ] Task 9: Unit tests `AGUIEmitter` (AC: #3, #4, #7, #8, #10, #11, #14)
  - [ ] Test `HandleMessageEvent` avec message assistant final → vérifie séquence `TEXT_MESSAGE_*`
  - [ ] Test `HandleMessageEvent` avec message assistant + tool calls → vérifie aucun event TEXT émis
  - [ ] Test `HandleMessageEvent` avec message user → vérifie no-op
  - [ ] Test `HandleToolCallStart` → vérifie `TOOL_CALL_START` + `TOOL_CALL_ARGS`
  - [ ] Test `HandleToolCallEnd` → vérifie `TOOL_CALL_END`
  - [ ] Test contexte annulé → vérifie no-op sans erreur
  - [ ] Test erreur écriture SSE → vérifie retour nil (pas de remontée d'erreur)

- [ ] Task 10: Tests d'intégration handler (AC: #3, #4, #5, #8, #12, #14)
  - [ ] Test full SSE avec tool calls : `RUN_STARTED` → `TOOL_CALL_START/ARGS/END` → `TEXT_MESSAGE_*` → `RUN_FINISHED`
  - [ ] Test sans tool calls : `RUN_STARTED` → `TEXT_MESSAGE_*` → `RUN_FINISHED`
  - [ ] Test erreur chatFn : `RUN_STARTED` → `RUN_ERROR`
  - [ ] Test max tool iterations : `RUN_STARTED` → `TOOL_CALL_*` (n fois) → `RUN_ERROR` (user-friendly message)
  - [ ] Test déconnexion client pendant émission
  - [ ] Test stream réussi avec persistence en échec (arbitrage terminal documenté)
  - [ ] Test persistence réussie avec stream partiellement en échec (arbitrage terminal documenté)

## Technical Notes

- **Pas de nouveau type** : les structs `MessageEvent`, `TurnEvent`, `ToolCallEvent`, `ToolCallEndEvent` restent inchangées.
- **Interface à 4 méthodes (dérogation formelle)** : dépasse la règle projet 1-3 méthodes mais représente un lifecycle conversationnel complet et indivisible. Garde-fou: aucune 5ème méthode sans ADR. Justification: découper en sous-interfaces créerait un couplage implicite et une composition artificielle sans gain de testabilité.
- **`NoOpMessageEventHandler`** (ou embed struct) permet aux implémenteurs de ne surcharger que les méthodes pertinentes.
- **Ordering garanti** : `HandleMessageEvent` est appelé dans `Chat()` pour le message final (Role=Assistant, ToolCalls vide) → l'`AGUIEmitter` émet `TEXT_MESSAGE_*` à ce moment. Le handler HTTP écrit `RUN_FINISHED` uniquement après retour de `chatFn`, donc l'ordering est : contenu → run_finished.
- **Même phase (parallèle) pour SSE + storage — politique best effort** : l'`AGUIEmitter` et le store s'exécutent en parallèle dans la même phase. L'`AGUIEmitter` retourne toujours nil (log + nil), donc ne bloque jamais la persistence ni le pipeline. Un échec SSE (déconnexion ou erreur inattendue) est journalisé mais n'impacte pas le statut du run. En revanche, un échec de persistence remonte normalement via le pipeline et cause `RUN_ERROR`. La détection de déconnexion côté flow se fait via `ctx.Err()` au prochain point de contrôle dans `Chat()`.
- **Thread-safety SSEWriter** : `SSEWriter` est déjà protégé par un mutex (`sync.Mutex`) dans `talk/internal/agui/sse.go` et sérialise les écritures dans `WriteEvent`. En exécution parallèle, aucun mutex additionnel n'est requis autour du writer; le principal risque devient la cohérence fonctionnelle (doublons/ordering d'events) si plusieurs emitters écrivent les mêmes types d'events.
- **`ChatFunc` retourne `error` seul** : le handler n'utilise plus le texte de la réponse. Le texte est émis directement par l'`AGUIEmitter` via le pipeline d'events.
- **Le `SSEWriter` est passé via `ChatOptions`** — `chatFn` dans serve.go instancie l'`AGUIEmitter` avec le writer.
- **Nouveau comportement CLI** : les tool call events seront désormais visibles dans le terminal (via `ConsoleUsageReporter` qui les implémente déjà). C'est une amélioration, pas une régression.
- **Pas de `ThinkingEffort` dans `ChatOptions`** — cela sera ajouté par la story 1.5.

## Dependencies

- Story 1.2 (handler + SSE writer) — done
- Story 1.4 (context cancellation) — done
- Story 2.1 (tool execution loop) — done
- Story 2.2 (tool call events) — done (sera refactoré par cette story)
