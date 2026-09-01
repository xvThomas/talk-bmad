---
baseline_commit: 2ad8908
---

# Story 9.1: Split layout + `MapProvider` + session itinerary state

Status: ready-for-dev

## Story

As an end user,
I want a map panel to appear automatically alongside my conversation when a route is returned,
So that I can immediately see the itinerary without any manual action.

## Acceptance Criteria (BDD)

**AC#1** — Split layout without modifying `ChatView`
**Given** the existing `ChatView` component
**When** story 9.1 is implemented
**Then** `ChatView` is wrapped in a `SplitLayout` container that places the map panel area to its right
**And** `ChatView` itself is not modified — no new props, no new imports, no new hook calls
**And** `SplitLayout` accepts a `mapPanelOpen: boolean` prop that controls whether the right panel area is rendered (not merely hidden)

**AC#2** — Initial state: panel closed, no itineraries
**Given** the application starts with no conversation
**When** `MapProvider` state is initialized
**Then** `isMapPanelOpen` is `false` and `itineraries` is an empty array
**And** the map panel area is not rendered in the DOM (not merely invisible — the node is absent)

**AC#3** — Auto-open when a route result arrives
**Given** the `route` tool returns a result in the message stream
**When** `MapProvider` processes `agent.messages`
**Then** the result is passed through `routeToolMapper` (registered at app root)
**And** a new `MapFeature` is appended to `itineraries`
**And** if `isMapPanelOpen` was `false`, it is set to `true`

**AC#4** — Manual toggle preserves state
**Given** the user clicks the map panel toggle control
**When** it is currently open
**Then** `isMapPanelOpen` becomes `false` and the panel area collapses (DOM node removed)
**And** the itinerary state is preserved (itineraries array unchanged)

**AC#5** — Reopen restores itineraries
**Given** the user closes then re-opens the panel
**When** the panel reopens
**Then** the previously accumulated `itineraries` are still present (state not discarded)

**AC#6** — Type isolation: `MapFeature` / `ToolResultMapper` in `src/map/types.ts`
**Given** the `MapProvider` internal implementation
**When** story 9.1 is implemented
**Then** `ToolResultMapper` and `MapFeature` interfaces live exclusively in `src/map/types.ts`
**And** `src/map/types.ts` has zero imports from any chat component, context, or hook
**And** `MapProvider` depends on `agent.messages` from `@copilotkit/react-core/v2` but not on `ChatUIContext`

**AC#7** — Session reset clears map state
**Given** the user resets the conversation (new session / `agent.messages` cleared)
**When** `agent.messages.length` drops to zero
**Then** `itineraries` becomes an empty array
**And** `isMapPanelOpen` is set to `false`
**And** the map panel area is removed from the DOM

**AC#8** — Idempotent feature derivation
**Given** `MapProvider` re-renders with the same `agent.messages` array
**When** no new tool results have arrived
**Then** `itineraries` contains the same `MapFeature` objects (no duplicates)
**And** each feature's `id` equals the AG-UI `toolCallId` of the `route` result that produced it

**AC#9** — CI gates
**Given** the implementation is complete
**When** `pnpm lint && pnpm test && pnpm build` are executed
**Then** all pass with zero regressions and zero new type errors

## Tasks / Subtasks

- [ ] Task 1: Add `@types/geojson` dev dependency (AC: #6, #8)
  - [ ] 1.1 Run `pnpm add -D @types/geojson` in `talk-ui`
  - [ ] 1.2 Verify `tsconfig.app.json` picks it up automatically (no `types` list to update)

- [ ] Task 2: Create `src/map/types.ts` — core interfaces (AC: #6, #8)
  - [ ] 2.1 Export `MapFeature` interface:
    ```typescript
    export interface MapFeature {
      id: string;                                    // equals toolCallId — ensures idempotency
      label: string;                                 // e.g. "Paris → Lyon (car, fastest)"
      geometry: GeoJSON.Geometry;
      bbox: [number, number, number, number];        // [minLon, minLat, maxLon, maxLat]
      properties?: Record<string, unknown>;          // distance, duration, profile, portions, …
    }
    ```
  - [ ] 2.2 Export `ToolResultMapper` interface:
    ```typescript
    export interface ToolResultMapper {
      toolName: string;
      toMapFeatures: (toolResult: unknown) => MapFeature[];
    }
    ```
  - [ ] 2.3 Export `MapContextValue` interface:
    ```typescript
    export interface MapContextValue {
      itineraries: MapFeature[];
      selectedFeatureId: string | null;
      isMapPanelOpen: boolean;
      toggleMapPanel: () => void;
      selectFeature: (id: string | null) => void;
    }
    ```
  - [ ] 2.4 Verify `src/map/types.ts` imports only from `geojson` — zero imports from `../context/`, `../components/`, or `../config/`

- [ ] Task 3: Create `src/map/map-context.ts` — React context (AC: #6)
  - [ ] 3.1 Create the context with `null` default:
    ```typescript
    import { createContext } from "react";
    import type { MapContextValue } from "./types";
    export const MapContext = createContext<MapContextValue | null>(null);
    ```
  - [ ] 3.2 Export `useMapContext` hook that throws if used outside `MapProvider`

- [ ] Task 4: Create `src/map/MapProvider.tsx` — context provider (AC: #2, #3, #4, #5, #6, #7, #8)
  - [ ] 4.1 Import `useAgent` from `@copilotkit/react-core/v2`; read `agent.messages` — no `ChatUIContext` import
  - [ ] 4.2 Accept `mappers: ToolResultMapper[]` and `children: ReactNode` as props
  - [ ] 4.3 Implement `itineraries: MapFeature[]` via `useMemo` over `agent.messages`:
    - Build a `Map<string, string>` of `toolCallId → toolName` by iterating assistant messages with `toolCalls`
    - For each tool-result message (`role === "tool"`), look up `toolCallId` in the map, find the matching mapper, call `mapper.toMapFeatures(content)`, and prepend the toolCallId as the feature `id`
    - Return the flat list of all features derived from all tool results
    - Reuse `parseAguiMessage` from `../config/agui-schemas` to parse messages safely
  - [ ] 4.4 Manage `isMapPanelOpen: boolean` via `useState(false)`
  - [ ] 4.5 Auto-open effect: use `useRef` to track previous `itineraries.length`; when count increases, call `setIsMapPanelOpen(true)` (AC: #3)
  - [ ] 4.6 Session-reset effect: when `agent.messages.length` drops to `0`, call `setIsMapPanelOpen(false)` (AC: #7) — itineraries auto-reset because they derive from messages via `useMemo`
  - [ ] 4.7 Implement `toggleMapPanel = useCallback(() => setIsMapPanelOpen(v => !v), [])`
  - [ ] 4.8 Manage `selectedFeatureId: string | null` via `useState(null)`; implement `selectFeature = useCallback((id) => setSelectedFeatureId(id), [])`
  - [ ] 4.9 Build `value` with `useMemo`; provide it via `<MapContext.Provider value={value}>`

- [ ] Task 5: Create `src/map/adapters/route-tool-mapper.ts` — IGN route adapter (AC: #3, #8)
  - [ ] 5.1 Define a Zod schema `routeToolOutputSchema` covering only the fields needed for `MapFeature`:
    - `start: z.string()`, `end: z.string()`
    - `profile: z.string()`, `optimization: z.string()`
    - `distance: z.number()`, `duration: z.number()`
    - `bbox: z.tuple([z.number(), z.number(), z.number(), z.number()])`
    - `geometry: z.object({ type: z.string(), coordinates: z.array(z.array(z.number())) })`
    - `portions: z.array(z.unknown())`
    - `startLabel: z.string().optional()`, `endLabel: z.string().optional()`
  - [ ] 5.2 Implement `toMapFeatures(toolResult: unknown): MapFeature[]`:
    - If `toolResult` is a string, attempt `JSON.parse`; catch and return `[]`
    - Validate with `routeToolOutputSchema.safeParse`; if fails, return `[]`
    - Build `label`: `${data.startLabel ?? data.start} → ${data.endLabel ?? data.end} (${data.profile}, ${data.optimization})`
    - Return one `MapFeature` (`id` will be overridden by `MapProvider` with `toolCallId`):
      ```typescript
      {
        id: "",   // placeholder; MapProvider sets this to toolCallId
        label,
        geometry: data.geometry as GeoJSON.Geometry,
        bbox: data.bbox,
        properties: {
          distance: data.distance,
          duration: data.duration,
          profile: data.profile,
          optimization: data.optimization,
          portions: data.portions,
        },
      }
      ```
  - [ ] 5.3 Export `routeToolMapper: ToolResultMapper = { toolName: "route", toMapFeatures }`

- [ ] Task 6: Create `src/components/SplitLayout.tsx` — layout wrapper (AC: #1, #2, #4)
  - [ ] 6.1 Props: `{ mapPanelOpen: boolean; mapPanel: ReactNode; children: ReactNode }`
  - [ ] 6.2 Render a full-screen `flex` row container:
    - Left: `children` fills available width (`flex-1 min-w-0`)
    - Right: when `mapPanelOpen` is `true`, render `<div className="w-1/2 ...">` containing `mapPanel`; when `false`, render nothing (conditional, not `hidden`)
  - [ ] 6.3 No logic, no context reads — purely a presentation container

- [ ] Task 7: Update `src/App.tsx` — wire providers and layout (AC: #1, #2, #3)
  - [ ] 7.1 Import `MapProvider` from `./map/MapProvider`
  - [ ] 7.2 Import `routeToolMapper` from `./map/adapters/route-tool-mapper`
  - [ ] 7.3 Import `SplitLayout` from `./components/SplitLayout`
  - [ ] 7.4 Import `useMapContext` from `./map/map-context`
  - [ ] 7.5 Create an inner component `AppLayout` (inside App) that:
    - Reads `isMapPanelOpen` and `toggleMapPanel` from `useMapContext()`
    - Renders `<SplitLayout mapPanelOpen={isMapPanelOpen} mapPanel={<div>Map placeholder</div>}>`
    - Wraps the whole thing in `<ChatUIProvider>`
  - [ ] 7.6 `App` renders `<MapProvider mappers={[routeToolMapper]}><AppLayout /></MapProvider>`
  - [ ] 7.7 Add a temporary visible toggle button (e.g., a `<button>` in the top-right of `SplitLayout`) connected to `toggleMapPanel` — will be replaced in story 9.2 with proper UI; must be accessible with an aria-label

- [ ] Task 8: Tests (AC: #2, #3, #4, #5, #7, #8, #9)
  - [ ] 8.1 Create `src/__tests__/map-provider.test.tsx`:
    - Mock `useAgent` the same way `chat-ui-context.test.tsx` does — a mutable `mockAgent` object with `messages: []`
    - **Test: initial state** — render `MapProvider` with a `TestConsumer` that reads `isMapPanelOpen` and `itineraries.length`; assert both are falsy/zero
    - **Test: route result auto-opens panel** — seed `mockAgent.messages` with a `ToolCallContainer` message (role `"assistant"`, `toolCalls: [{ id: "tc-1", type: "function", function: { name: "route", arguments: "" } }]`) and a tool-result message (role `"tool"`, `toolCallId: "tc-1"`, `content: validRouteOutput`); re-render; assert `isMapPanelOpen === true` and `itineraries.length === 1`
    - **Test: feature id equals toolCallId** — from the above render, assert `itineraries[0].id === "tc-1"`
    - **Test: idempotency** — render the same messages twice (re-render with identical array); assert `itineraries.length` is still `1` (not doubled)
    - **Test: session reset** — render with messages set, then update `mockAgent.messages = []` and re-render; assert `itineraries.length === 0` and `isMapPanelOpen === false`
    - **Test: toggleMapPanel** — open panel, call `toggleMapPanel`; assert `isMapPanelOpen` becomes `false`; call again; assert `true`
    - **Test: close preserves itineraries** — open panel with one itinerary, call `toggleMapPanel`; assert `itineraries.length === 1`
  - [ ] 8.2 Create `src/__tests__/route-tool-mapper.test.ts`:
    - **Test: valid output** — call `routeToolMapper.toMapFeatures(routeOutput)` with a full valid output object; assert returns one feature with correct `label`, `bbox`, `geometry`, and properties
    - **Test: labels from startLabel/endLabel** — with `startLabel: "Paris"` and `endLabel: "Lyon"`, assert `label` starts with `"Paris → Lyon"`
    - **Test: fallback to coordinates** — omit `startLabel`/`endLabel`; assert `label` starts with `data.start`
    - **Test: string content** — pass `JSON.stringify(routeOutput)`; assert returns one feature
    - **Test: invalid content** — pass `null`; assert returns `[]`
    - **Test: malformed JSON string** — pass `"{bad json"`; assert returns `[]`
    - **Test: toolName** — assert `routeToolMapper.toolName === "route"`
  - [ ] 8.3 Update `src/__tests__/app.test.tsx`:
    - The `App` now uses `MapProvider` which calls `useAgent`; the existing mock for `@copilotkit/react-core/v2` already covers this
    - Verify the existing "renders the chat input" test still passes
    - Add a smoke test: `render(<App />)` does not throw

- [ ] Task 9: Run CI gates (AC: #9)
  - [ ] 9.1 Run `pnpm lint` — 0 errors
  - [ ] 9.2 Run `pnpm test` — 0 failures
  - [ ] 9.3 Run `pnpm build` — 0 type errors

## Dev Notes

### Component tree after story 9.1

```
CopilotKit (in __root.tsx — unchanged)
└── App
    └── MapProvider (mappers=[routeToolMapper])  ← NEW: reads agent.messages
        └── AppLayout (inner component)
            ├── ChatUIProvider
            │   └── SplitLayout (mapPanelOpen, mapPanel=placeholder)  ← NEW
            │       ├── ChatView (UNCHANGED)
            │       └── <div>Map placeholder</div>  (story 9.2 will replace with <MapPanel />)
            └── [toggle button]
```

`MapProvider` and `ChatUIProvider` are siblings in the React tree. `MapProvider` wraps the tree so its context is accessible to all layout consumers (including the future `MapPanel`).

### How `MapProvider` derives itineraries from `agent.messages`

```typescript
const itineraries = useMemo<MapFeature[]>(() => {
  // Step 1: index all tool calls by id → toolName
  const toolCallNames = new Map<string, string>();
  for (const msg of agent.messages) {
    const parsed = parseAguiMessage(msg);
    if (!parsed || parsed.kind !== "tool-call-container") continue;
    for (const tc of parsed.toolCalls) {
      if (tc.id) toolCallNames.set(tc.id, tc.function.name);
    }
  }

  // Step 2: for each tool result, find matching mapper and extract features
  const features: MapFeature[] = [];
  for (const msg of agent.messages) {
    const parsed = parseAguiMessage(msg);
    if (!parsed || parsed.kind !== "tool-result") continue;
    const toolCallId = parsed.toolCallId;
    if (!toolCallId) continue;
    const toolName = toolCallNames.get(toolCallId);
    if (!toolName) continue;
    const mapper = mappers.find((m) => m.toolName === toolName);
    if (!mapper) continue;
    const extracted = mapper.toMapFeatures(parsed.content);
    // Override id with toolCallId for idempotency (AC#8)
    features.push(
      ...extracted.map((f, idx) => ({
        ...f,
        id: extracted.length === 1 ? toolCallId : `${toolCallId}-${idx}`,
      })),
    );
  }
  return features;
}, [agent.messages, mappers]);
```

### Auto-open + session-reset effects

```typescript
const prevCountRef = useRef(0);
useEffect(() => {
  const prev = prevCountRef.current;
  const next = itineraries.length;
  if (next > prev) {
    setIsMapPanelOpen(true);      // AC#3: new itinerary → auto-open
  } else if (next === 0 && prev > 0) {
    setIsMapPanelOpen(false);     // AC#7: session reset → close
  }
  prevCountRef.current = next;
}, [itineraries.length]);
```

Do NOT use `itineraries` as the dependency — its identity changes on every `agent.messages` update. Use `itineraries.length` to detect meaningful count changes.

### `agent.messages` type (from `@ag-ui/client`)

```typescript
// agent.messages elements are typed as unknown[] from the mutable agent
// — use parseAguiMessage(msg) from src/config/agui-schemas.ts to narrow safely
```

`parseAguiMessage` already handles all message shapes and returns `undefined` for unrecognized shapes. No direct type casting needed.

### `SplitLayout` sizing

The layout must not break the existing `ChatView` (which has its own internal flex column). Suggested approach:

```tsx
<div className="flex h-screen w-full overflow-hidden">
  <div className="flex-1 min-w-0 overflow-hidden">
    {children}
  </div>
  {mapPanelOpen && (
    <div className="w-1/2 min-w-0 border-l border-border overflow-hidden">
      {mapPanel}
    </div>
  )}
</div>
```

Story 9.2 will refine sizing and add transitions. No animation or transition required in 9.1.

### `routeToolMapper` — RouteToolOutput shape (from `mcp-ign-nav` Go structs)

JSON field names (lowercase, camelCase as per Go `json` tags):

```
start (string)       end (string)
profile (string)     optimization (string)
distance (number)    duration (number)
bbox ([number, number, number, number])
geometry.type (string)   geometry.coordinates (number[][])
portions (array of RoutePortion objects)
startLabel (string, omitempty)
endLabel (string, omitempty)
```

The `bbox` field is `[minLon, minLat, maxLon, maxLat]` — matches `MapFeature.bbox` directly.

The tool result `content` in `agent.messages` may be:
- A plain JavaScript object (CopilotKit deserializes it) — most common in practice
- A JSON string (backend may return stringified) — the mapper must handle both

### Avoiding `mappers` prop identity churn

In `App.tsx`, declare the mappers array **outside** the component or with `useMemo` to avoid re-creating it on every render and thrashing `MapProvider`'s `useMemo`:

```typescript
const MAP_MAPPERS: ToolResultMapper[] = [routeToolMapper];

export function App() {
  return (
    <MapProvider mappers={MAP_MAPPERS}>
      <AppLayout />
    </MapProvider>
  );
}
```

### Test helper for `map-provider.test.tsx`

Model after `chat-ui-context.test.tsx`: define a mutable `mockAgent` object, mock `@copilotkit/react-core/v2` at the module level, and mutate `mockAgent.messages` between test cases (use `beforeEach` to reset).

```typescript
const mockAgent = {
  messages: [] as unknown[],
  isRunning: false,
  pendingInterrupts: [],
  addMessage: vi.fn(),
  agentId: "default",
  threadId: "thread-1",
  state: {},
  setState: vi.fn(),
};

vi.mock("@copilotkit/react-core/v2", () => ({
  useAgent: () => ({ agent: mockAgent }),
}));
```

Wrap `MapProvider` renders in a minimal `AgentErrorContext.Provider` if needed (but `MapProvider` does not use `useAgentError` — no wrapper required).

### Files created / updated

| File | Action | What changes |
|------|--------|--------------|
| `src/map/types.ts` | CREATE | `MapFeature`, `ToolResultMapper`, `MapContextValue` interfaces |
| `src/map/map-context.ts` | CREATE | `MapContext`, `useMapContext` hook |
| `src/map/MapProvider.tsx` | CREATE | Context provider: derives `itineraries` from `agent.messages`, manages `isMapPanelOpen` |
| `src/map/adapters/route-tool-mapper.ts` | CREATE | `routeToolMapper` — transforms `RouteToolOutput` → `MapFeature` |
| `src/components/SplitLayout.tsx` | CREATE | Presentation layout: left=chat, right=map panel (conditional) |
| `src/App.tsx` | UPDATE | Add `MapProvider`, `SplitLayout`, `routeToolMapper`; extract inner `AppLayout` |
| `src/__tests__/map-provider.test.tsx` | CREATE | Unit tests for `MapProvider` state machine |
| `src/__tests__/route-tool-mapper.test.ts` | CREATE | Unit tests for `routeToolMapper` adapter |
| `src/__tests__/app.test.tsx` | UPDATE | Smoke test with new layout structure (existing test must still pass) |
| `package.json` / `pnpm-lock.yaml` | UPDATE | Add `@types/geojson` dev dependency |

No changes to `ChatView`, `ChatUIProvider`, `ChatUIContext`, `normalizeMessages`, or any existing chat component.
