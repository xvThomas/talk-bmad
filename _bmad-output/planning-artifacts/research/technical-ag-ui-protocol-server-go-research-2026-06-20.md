---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: []
workflowType: "research"
lastStep: 1
research_type: "technical"
research_topic: "AG-UI Protocol - HTTP Server Implementation in Go"
research_goals: "Wire existing agentic conversation harness to ag-ui server for LLM streaming to frontend; expose conversation sessions with history for frontend consumption"
user_name: "Xavierthomas"
date: "2026-06-20"
web_research_enabled: true
source_verification: true
---

# Research Report: Technical

**Date:** 2026-06-20
**Author:** Xavierthomas
**Research Type:** technical

---

## Research Overview

Technical research on the AG-UI (Agent User Interaction Protocol) to evaluate implementation of an ag-ui compliant HTTP server in Go within the talk-backend monorepo. Focus on streaming LLM messages to a frontend and managing conversation sessions with history.

---

## Technology Stack Analysis

### AG-UI Protocol Overview

AG-UI (Agent-User Interaction Protocol) est un protocole open-source, léger et basé sur des événements qui standardise la communication entre les backends d'agents IA et les applications utilisateur (frontends). Il est complémentaire aux deux autres protocoles agentiques :

- **MCP** (Model Context Protocol) — donne des outils aux agents
- **A2A** (Agent to Agent) — communication inter-agents
- **AG-UI** — connecte les agents aux applications utilisateur

_Source: https://docs.ag-ui.com/introduction_
_Source: https://github.com/ag-ui-protocol/ag-ui (14.3k stars, MIT license, release 2026-06-19)_

### Transport et Architecture

**Modèle de communication :**

- Le client envoie un `POST` avec un body `RunAgentInput` vers l'endpoint du serveur
- Le serveur répond avec un flux d'événements SSE (`text/event-stream`) ou un protocole binaire HTTP
- Transport agnostique : SSE, WebSockets, webhooks supportés

**Contrat serveur (endpoint unique) :**

```
POST /  (ou chemin personnalisé)
Content-Type: application/json
Accept: text/event-stream

Body: RunAgentInput {
  threadId: string       // identifiant de la conversation
  runId: string          // identifiant du run
  parentRunId?: string   // pour branching/time-travel
  state: any             // état partagé
  messages: Message[]    // historique des messages
  tools: Tool[]          // outils disponibles (définis par le frontend)
  context: Context[]     // contexte additionnel
  forwardedProps: any    // props arbitraires
  resume?: ResumeEntry[] // reprise après interrupt
}

Response: Stream<BaseEvent> (SSE)
```

_Source: https://docs.ag-ui.com/concepts/architecture_

### Event Types (~16 types standardisés)

| Catégorie        | Événements                                                                                  | Usage                  |
| ---------------- | ------------------------------------------------------------------------------------------- | ---------------------- |
| **Lifecycle**    | `RUN_STARTED`, `RUN_FINISHED`, `RUN_ERROR`, `STEP_STARTED`, `STEP_FINISHED`                 | Cycle de vie d'un run  |
| **Text Message** | `TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT`, `TEXT_MESSAGE_END`, `TEXT_MESSAGE_CHUNK`      | Streaming de texte     |
| **Tool Call**    | `TOOL_CALL_START`, `TOOL_CALL_ARGS`, `TOOL_CALL_END`, `TOOL_CALL_RESULT`, `TOOL_CALL_CHUNK` | Appels d'outils        |
| **State**        | `STATE_SNAPSHOT`, `STATE_DELTA`, `MESSAGES_SNAPSHOT`                                        | Synchronisation d'état |
| **Activity**     | `ACTIVITY_SNAPSHOT`, `ACTIVITY_DELTA`                                                       | Progression            |
| **Reasoning**    | `REASONING_START`, `REASONING_MESSAGE_*`, `REASONING_END`, `REASONING_ENCRYPTED_VALUE`      | Chain-of-thought       |
| **Special**      | `RAW`, `CUSTOM`                                                                             | Extensibilité          |

**Patterns d'événements :**

1. **Start-Content-End** : pour le streaming (text messages, tool calls)
2. **Snapshot-Delta** : pour la synchronisation d'état (RFC 6902 JSON Patch)
3. **Lifecycle** : pour le monitoring des runs

_Source: https://docs.ag-ui.com/concepts/events_

### SDK Go (Community)

**Module :** `github.com/ag-ui-protocol/ag-ui/sdks/community/go` (Go 1.24.4)

**Structure du SDK :**

```
pkg/
  client/sse/     — Client SSE
  core/
    events/       — Types d'événements (EventType, BaseEvent, etc.)
    types/        — Types de données (RunAgentInput, Message, Tool, etc.)
  encoding/
    encoder/      — Encodeur d'événements
    json/         — Sérialisation JSON
    negotiation/  — Content negotiation
    sse/          — Encodage SSE
  errors/         — Types d'erreurs
```

**Types clés Go :**

- `RunAgentInput` — payload d'entrée (ThreadID, RunID, Messages, Tools, State, Context)
- `Message` — message avec Role, Content, ToolCalls, ToolCallID
- `Event` interface — Type(), Timestamp(), Validate(), ToJSON()
- `BaseEvent` struct — EventType, TimestampMs, RawEvent
- `EventFromJSON(data []byte)` — parsing polymorphe des événements

**Dépendances :** `google/uuid`, `sirupsen/logrus`, `stretchr/testify`

_Source: https://github.com/ag-ui-protocol/ag-ui/tree/main/sdks/community/go_
_Source: https://raw.githubusercontent.com/ag-ui-protocol/ag-ui/main/sdks/community/go/go.mod_
_Source: https://raw.githubusercontent.com/ag-ui-protocol/ag-ui/main/sdks/community/go/pkg/core/types/types.go_
_Source: https://raw.githubusercontent.com/ag-ui-protocol/ag-ui/main/sdks/community/go/pkg/core/events/events.go_

### Exemple de serveur Go

L'exemple officiel utilise **gofiber/fiber v3** avec une route `POST /agentic` et support CORS + SSE :

- Configuration-driven (host, port, timeouts, SSE keepalive, chunk delay)
- Graceful shutdown avec signal handling
- MCP server co-localisé (optionnel)

_Source: https://raw.githubusercontent.com/ag-ui-protocol/ag-ui/main/sdks/community/go/example/server/cmd/main.go_

### Clients AG-UI compatibles

| Client                 | Statut                             |
| ---------------------- | ---------------------------------- |
| **CopilotKit** (React) | ✅ 1st Party — le client principal |
| Terminal + Agent       | ✅ Community                       |
| React Native           | 🛠️ Help Wanted                     |

Le client principal est **CopilotKit** qui fournit des composants React plug-and-play (`HttpAgent` + hooks React). Il suffit de pointer vers l'URL du serveur AG-UI.

_Source: https://docs.ag-ui.com/introduction#supported-integrations_

### Pertinence pour talk-backend

**Mapping avec l'architecture existante :**

| Concept AG-UI            | Équivalent talk-backend                          |
| ------------------------ | ------------------------------------------------ |
| `RunAgentInput.messages` | Historique de conversation (`memory` module)     |
| `TEXT_MESSAGE_*` events  | Streaming du LLM (Anthropic/OpenAI `Complete()`) |
| `TOOL_CALL_*` events     | Exécution d'outils MCP                           |
| `threadId`               | Session/conversation ID                          |
| `MESSAGES_SNAPSHOT`      | Chargement d'historique de session existante     |
| `STATE_SNAPSHOT/DELTA`   | État de la conversation (config, context)        |
| `RUN_STARTED/FINISHED`   | Lifecycle d'un "turn" de conversation            |
| `REASONING_*` events     | Thinking blocks (Anthropic extended thinking)    |

_Analyse basée sur: project-context.md et architecture talk-backend_

---

## Integration Patterns Analysis

### Pattern d'intégration principal : MessageEventHandler → SSE Stream

L'architecture actuelle de talk-backend utilise un pattern **event handler phasé** (`MessageEventHandler`) qui reçoit chaque message et chaque fin de tour via des callbacks. C'est le **point d'injection naturel** pour émettre les événements AG-UI en temps réel.

**Architecture existante (talk/internal/domain) :**

```
ConversationManager.Chat(ctx, userInput)
  ├── HandleMessageEvent(MessageEvent{Role: User, ...})       ← user message stored
  ├── llmClient.Complete(ctx, systemPrompt, messages, tools)  ← LLM call
  ├── HandleMessageEvent(MessageEvent{Role: Assistant, ...})  ← assistant response
  ├── [si tool calls] toolExecutor.Execute(ctx, toolCalls)
  │   └── HandleMessageEvent(MessageEvent{Role: Tool, ...})   ← tool results
  ├── [boucle tool calls, max 5 iterations]
  └── HandleTurnEvent(TurnEvent{...})                         ← turn complete
```

**Mapping vers AG-UI events :**

```
ConversationManager events          →  AG-UI SSE events
─────────────────────────────────────────────────────────────────────
Chat() appelé                       →  RUN_STARTED
HandleMessageEvent(Role: User)      →  (pas d'événement, déjà dans l'input)
LLM streaming (à adapter)          →  TEXT_MESSAGE_START + TEXT_MESSAGE_CONTENT* + TEXT_MESSAGE_END
HandleMessageEvent(Role: Assistant) →  (post-fact, pour stockage)
ToolCallEvent                       →  TOOL_CALL_START + TOOL_CALL_ARGS + TOOL_CALL_END
HandleMessageEvent(Role: Tool)      →  TOOL_CALL_RESULT
HandleTurnEvent                     →  RUN_FINISHED
Erreur                              →  RUN_ERROR
```

### Problème clé : Streaming granulaire des tokens

**Situation actuelle :** `LlmClient.Complete()` est **synchrone** — il retourne un `*Message` complet après que tout le contenu soit généré. Il n'y a pas de callback token-par-token.

**Solution pour le streaming AG-UI :**

| Option                        | Description                                                                                      | Impact                                              |
| ----------------------------- | ------------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| **A. Streaming LlmClient**    | Ajouter une interface `StreamingLlmClient` avec callback par chunk                               | Modification des clients Anthropic/OpenAI existants |
| **B. Wrapper avec channel**   | Le serveur AG-UI observe un channel Go alimenté par le LLM                                       | Nouvelle couche d'abstraction                       |
| **C. Adapter au niveau HTTP** | Le SDK Anthropic/OpenAI supporte déjà le streaming nativement — l'intercepter avant `Complete()` | Plus intrusif mais optimal                          |

**Recommandation : Option A** — Introduire une interface streaming :

```go
// StreamingLlmClient étend LlmClient avec un support streaming token-par-token.
type StreamingLlmClient interface {
    LlmClient
    // CompleteStream envoie chaque chunk de texte au callback en temps réel.
    CompleteStream(ctx context.Context, systemPrompt string, messages []Message,
        tools []Tool, opts CompletionOptions, onChunk func(chunk string)) (*Message, Usage, error)
}
```

Les deux SDK (Anthropic et OpenAI) supportent nativement le streaming — il suffit de l'exposer via une nouvelle méthode sans casser l'interface existante (la CLI continue d'utiliser `Complete()`).

### Pattern du serveur HTTP AG-UI

**Endpoint principal :**

```go
// POST /ag-ui (ou POST /agent)
// Accept: text/event-stream
// Body: RunAgentInput (threadId, runId, messages, tools, state)
// Response: SSE stream d'événements AG-UI
func (s *Server) handleAgentRun(w http.ResponseWriter, r *http.Request) {
    // 1. Décoder RunAgentInput
    // 2. Résoudre threadId → SessionScope
    // 3. Injecter messages dans le context builder (ou utiliser ceux du body)
    // 4. Configurer SSE flusher
    // 5. Émettre RUN_STARTED
    // 6. Appeler ConversationManager.ChatStream(ctx, input, eventEmitter)
    // 7. Émettre RUN_FINISHED ou RUN_ERROR
}
```

**Format SSE :**

```
data: {"type":"RUN_STARTED","threadId":"thread_123","runId":"run_456","timestamp":1718884800000}

data: {"type":"TEXT_MESSAGE_START","messageId":"msg_789","role":"assistant","timestamp":1718884800001}

data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"msg_789","delta":"Bonjour","timestamp":1718884800002}

data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"msg_789","delta":" ! Comment","timestamp":1718884800003}

data: {"type":"TEXT_MESSAGE_END","messageId":"msg_789","timestamp":1718884800100}

data: {"type":"RUN_FINISHED","threadId":"thread_123","runId":"run_456","timestamp":1718884800101}

```

### Intégration avec le système de sessions existant

**Objectif 2 : Consulter et reprendre des conversations existantes**

L'architecture existante fournit déjà les briques nécessaires :

| Besoin frontend            | Interface existante                                                    | Endpoint AG-UI/REST                               |
| -------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------- |
| Lister les sessions        | `SessionBrowser.ListSessions(ctx, userID)`                             | `GET /sessions`                                   |
| Charger l'historique       | `SessionBrowser.LoadHistoryTurnsFromSession(ctx, sessionID)`           | `GET /sessions/{id}/history`                      |
| Reprendre une conversation | `MessageStore.AllMessages(ctx, sessionID)` + `MESSAGES_SNAPSHOT` event | `POST /agent` avec `threadId` = session existante |
| Supprimer une session      | `SessionBrowser.DeleteSession(ctx, sessionID)`                         | `DELETE /sessions/{id}`                           |

**Pattern de reprise de session avec AG-UI :**

```
Client POST /agent { threadId: "existing-session-id", messages: [...], ... }
  ↓
Serveur:
  1. RUN_STARTED { threadId, runId }
  2. MESSAGES_SNAPSHOT { messages: store.AllMessages(threadId) }  ← historique complet
  3. TEXT_MESSAGE_START/CONTENT/END  ← nouvelle réponse streamée
  4. RUN_FINISHED
```

### Architecture du nouveau module

**Proposition de structure dans le monorepo :**

```
talk-backend/
  ag-ui-server/           ← nouveau module
    go.mod                  (replace ../talk-libs, ../talk)
    Dockerfile
    Makefile
    cmd/
      main.go              ← HTTP server, routes, graceful shutdown
      main_test.go         ← wiring smoke test
    internal/
      config/
        config.go          ← env vars (PORT, AUTH, DB_PATH, etc.)
      handler/
        agent.go           ← POST /agent (AG-UI endpoint principal)
        sessions.go        ← GET/DELETE /sessions (REST endpoints)
      agui/
        emitter.go         ← SSE event encoder, flusher
        events.go          ← types AG-UI (ou import du SDK community Go)
        converter.go       ← domain.Message → AG-UI Message
      streaming/
        client.go          ← StreamingLlmClient adapter
```

**Ou alternative intégrée au module `talk/` :**

Le serveur AG-UI pourrait être un mode d'exécution alternatif de `talk` lui-même (via `talk serve`), partageant le même `ConversationManager`, `MessageStore`, et `SessionBrowser`. Cela évite la duplication de dépendances.

### Flux de données complet

```
┌─────────────┐    POST /agent     ┌──────────────────┐
│  Frontend   │───────────────────▶│  AG-UI Server    │
│ (CopilotKit)│◀───────────────────│  (net/http + SSE)│
│             │    SSE events      │                  │
└─────────────┘                    └───────┬──────────┘
                                           │
                              ┌─────────────┼────────────────┐
                              │             │                │
                    ┌─────────▼───┐  ┌──────▼──────┐  ┌─────▼──────┐
                    │Conversation │  │ SQLite      │  │ Session    │
                    │Manager      │  │ MessageStore│  │ Browser    │
                    │(streaming)  │  │             │  │            │
                    └──────┬──────┘  └─────────────┘  └────────────┘
                           │
                    ┌──────▼──────┐
                    │ LLM Client  │
                    │(Anthropic/  │
                    │ OpenAI)     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ MCP Tools   │
                    │(via tool    │
                    │ executor)   │
                    └─────────────┘
```

### Considérations de concurrence

| Aspect              | CLI (actuel)                          | Serveur AG-UI                                      |
| ------------------- | ------------------------------------- | -------------------------------------------------- |
| Clients simultanés  | 1                                     | N                                                  |
| SQLite accès        | `MaxOpenConns(1)` + `sync.RWMutex` OK | Idem, WAL mode suffisant pour reads concurrents    |
| ConversationManager | 1 instance                            | 1 instance par session active (pool ou factory)    |
| Streaming           | Non nécessaire                        | SSE flusher par requête, isolation totale          |
| Annulation          | `ctx.Done()` via CLI signal           | `r.Context().Done()` quand le client se déconnecte |

### Authentification

Le serveur AG-UI nécessite une authentification pour protéger l'accès aux sessions. Options compatibles avec le monorepo :

- **JWT Bearer token** (cohérent avec `talk-libs/mcpserver/auth.go` existant)
- Le `userID` est extrait du token et utilisé pour `SessionScope`
- `threadId` du body AG-UI mappé vers le `sessionID` interne

_Sources : analyse de talk/internal/domain/\*.go, talk/internal/memory/sqlite/store.go, docs.ag-ui.com/concepts/architecture_

---

## Performance et Considérations Opérationnelles

### SSE Streaming en Go — Bonnes pratiques

**Pattern SSE standard avec `net/http` :**

```go
func handleSSE(w http.ResponseWriter, r *http.Request) {
    // Headers SSE obligatoires
    w.Header().Set("Content-Type", "text/event-stream")
    w.Header().Set("Cache-Control", "no-cache")
    w.Header().Set("Connection", "keep-alive")

    // ResponseController (Go 1.20+) — plus robuste que le cast Flusher
    rc := http.NewResponseController(w)

    // Émettre un événement
    fmt.Fprintf(w, "data: %s\n\n", jsonPayload)
    rc.Flush()

    // Détection de déconnexion client
    <-r.Context().Done()
}
```

**Points critiques :**

- `WriteTimeout` du serveur doit être **désactivé** (0) ou très long pour les streams SSE, sinon Go coupe la connexion
- Utiliser `ResponseController.SetWriteDeadline()` par-requête pour étendre le deadline avant chaque write
- HTTP/2 supporte nativement le full-duplex, pas besoin de `EnableFullDuplex()` pour SSE

_Source: https://pkg.go.dev/net/http#Flusher, https://pkg.go.dev/net/http#ResponseController_

### Latence et Buffer

| Facteur                            | Impact                             | Mitigation                                                                 |
| ---------------------------------- | ---------------------------------- | -------------------------------------------------------------------------- |
| Buffering proxy (nginx/cloudflare) | Bloque le flush SSE côté client    | `X-Accel-Buffering: no` header                                             |
| Taille chunk LLM                   | 1 token = 1 event peut être chatty | Batcher 5-10 tokens par event ou utiliser `TEXT_MESSAGE_CHUNK`             |
| JSON encoding par event            | Allocation/GC pressure             | Pré-allouer buffer, utiliser `json.NewEncoder` sur un `bytes.Buffer` poolé |
| CORS preflight                     | +1 RTT au premier call             | Preflight cache `Access-Control-Max-Age: 86400`                            |

### Persistence — Note sur la migration SQLite → PostgreSQL

La couche `MessageStore` et `SessionBrowser` sont des interfaces Go pures. La migration SQLite → PostgreSQL est transparente :

- Implémenter `MessageStore` et `SessionBrowser` avec `pgx` ou `database/sql` + driver pg
- Pour le serveur AG-UI multi-clients, PostgreSQL est recommandé (pas de single-writer limitation)
- Connection pooling (`pgxpool`) nécessaire pour N sessions concurrentes
- Le schéma existant (sessions, messages, history_turns) est directement transposable en PG

### Scalabilité

| Charge                  | Architecture                        | Notes                                           |
| ----------------------- | ----------------------------------- | ----------------------------------------------- |
| 1-10 clients simultanés | Single instance, PostgreSQL         | Suffisant pour usage équipe                     |
| 10-100 clients          | Single instance + connection pool   | Go gère aisément 100 goroutines SSE             |
| 100+ clients            | Load balancer + instances multiples | SSE stateless ↔ chaque requête est indépendante |

Le serveur AG-UI est **naturellement stateless par requête** : chaque `POST /agent` crée un `ConversationManager` éphémère, charge l'historique depuis la DB, stream la réponse, et ferme. Pas de state en mémoire à partager entre instances.

---

## Synthèse et Recommandations Stratégiques

### Résumé exécutif

AG-UI est le protocole standard émergent pour connecter des agents IA à des interfaces utilisateur. Avec 14.3k stars GitHub et le backing de CopilotKit, il offre un modèle simple (1 endpoint POST → flux SSE d'événements typés) parfaitement adapté à l'architecture existante de talk-backend.

L'intégration est **faisable avec un effort modéré** car :

1. Les interfaces `MessageEventHandler`, `MessageStore`, `SessionBrowser` sont déjà les bonnes abstractions
2. Le SDK Go community fournit les types et l'encodage
3. Le pattern SSE est natif en Go via `net/http` + `Flusher`

### Plan d'implémentation recommandé

| Phase                              | Livrable                                                                                        | Effort estimé |
| ---------------------------------- | ----------------------------------------------------------------------------------------------- | ------------- |
| **1. Serveur AG-UI minimal**       | Endpoint `POST /agent` → réponse complète via SSE (utilise `Complete()` synchrone)              | Moyen         |
| **2. Sessions REST**               | `GET/DELETE /sessions`, `MESSAGES_SNAPSHOT`                                                     | Faible        |
| **3. Tool calls**                  | `TOOL_CALL_*` events pendant l'exécution d'outils                                               | Moyen         |
| **4. Auth + CORS**                 | JWT Bearer (Auth0/Keycloak), CORS pour CopilotKit — _non requis pour le fonctionnement initial_ | Faible        |
| **5. Reasoning**                   | `REASONING_*` events (thinking blocks Anthropic)                                                | Faible        |
| **6. Token streaming (optionnel)** | Interface `StreamingLlmClient` + `TEXT_MESSAGE_CONTENT` delta par token                         | Moyen         |

> **Note :** La phase 1 n'exige pas de modifier `LlmClient`. Le serveur appelle `ConversationManager.Chat()`, puis émet le résultat complet dans un seul event `TEXT_MESSAGE_CONTENT`. Le token streaming (phase 6) est une optimisation UX pour réduire le time-to-first-byte sur les réponses longues.

### Décisions techniques clés

| Décision        | Choix recommandé                        | Justification                                                                                                                                                                |
| --------------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Module          | `talk serve` (sous-commande)            | Réutilise tout le wiring existant                                                                                                                                            |
| HTTP framework  | `net/http` stdlib (Go 1.22+ `ServeMux`) | Cohérence monorepo, zéro dépendance, SSE natif via `ResponseController.Flush()`. Fiber n'apporte pas de gain perf significatif (bottleneck = appel LLM, pas le parsing HTTP) |
| AG-UI types     | Import du SDK community Go              | Évite de redéfinir les 30+ types                                                                                                                                             |
| Persistence     | PostgreSQL (futur)                      | Multi-client, pas de single-writer                                                                                                                                           |
| Client frontend | CopilotKit `HttpAgent`                  | 1st-party AG-UI client, plug-and-play                                                                                                                                        |
| Serveurs MCP    | Restent sur `net/http`                  | Contrainte du SDK `modelcontextprotocol/go-sdk` qui expose des `http.Handler`                                                                                                |

### Risques identifiés

| Risque                                                   | Probabilité       | Impact           | Mitigation                                            |
| -------------------------------------------------------- | ----------------- | ---------------- | ----------------------------------------------------- |
| SDK Go community instable (0.x)                          | Moyenne           | Moyen            | Vendorer ou fork minimal des types                    |
| Token streaming (phase 6) nécessite refactor `LlmClient` | Certaine          | Faible (reporté) | Interface opt-in, ne casse pas le CLI                 |
| WriteTimeout tue les streams SSE                         | Haute si non géré | Élevé            | Désactiver ou utiliser `SetWriteDeadline` per-request |
| CORS mal configuré bloque le frontend                    | Basse             | Faible           | Tests E2E avec CopilotKit dès la phase 2              |

---

## Technical Research Scope Confirmation

**Research Topic:** AG-UI Protocol - HTTP Server Implementation in Go
**Research Goals:** Wire existing agentic conversation harness to ag-ui server for LLM streaming to frontend; expose conversation sessions with history for frontend consumption

**Technical Research Scope:**

- Architecture Analysis - design patterns, frameworks, system architecture
- Implementation Approaches - development methodologies, coding patterns
- Technology Stack - languages, frameworks, tools, platforms
- Integration Patterns - APIs, protocols, interoperability
- Performance Considerations - scalability, optimization, patterns
