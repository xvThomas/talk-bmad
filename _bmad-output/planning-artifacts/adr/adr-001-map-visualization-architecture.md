# ADR-001 — Map Visualization Architecture

| Field       | Value                    |
| ----------- | ------------------------ |
| Status      | Accepted                 |
| Date        | 2026-08-31               |
| Epic        | Epic 8 — Map Visualization of Itineraries |
| Deciders    | Xavierthomas             |

---

## Context

Epic 8 introduces a map panel in `talk-ui` that visualizes itineraries returned by the `mcp-ign-nav` `route` MCP tool. Two architectural decisions were made during requirements analysis that have lasting consequences on the codebase structure and future extensibility.

The original `talk-ui` PRD (2026-06-28) explicitly anticipated *"domain-specific UI panels (maps, charts) alongside the conversation"* and described the application as *"an extensible shell"*. The architecture must honour this intent:

- Chat components must remain **tool-agnostic** and reusable outside this project (potential future component library).
- The map panel must be **generic**: it should be able to display geo data produced by any MCP tool, not only itineraries from `mcp-ign-nav`.

---

## Decision 1 — Decouple `MapContext` from `ChatUIContext`

### Chosen approach

A standalone `MapProvider` / `MapContext` is introduced alongside `ChatUIProvider`. The two contexts are **completely independent** and composed at the application root:

```
App
├── MapProvider        ← generic, knows nothing about chat or IGN
│   └── MapPanel, MapLegend
└── ChatUIProvider     ← unchanged; knows nothing about maps
    └── ChatView, MessageBubble, ToolCallItem, …
```

`MapContext` exposes a generic `MapFeature` interface:

```typescript
interface MapFeature {
  id: string;
  label: string;            // e.g. "Paris → Lyon (voiture, le plus rapide)"
  geometry: GeoJSON.Geometry;
  bbox: [number, number, number, number]; // [minLon, minLat, maxLon, maxLat]
  properties?: Record<string, unknown>;   // distance, duration, steps, etc.
}
```

The bridge between tool results and `MapFeature` objects is a **`ToolResultMapper`** interface declared at the application level, not inside any core component:

```typescript
interface ToolResultMapper {
  toolName: string;
  toMapFeatures: (toolResult: unknown) => MapFeature[];
}
```

`MapProvider` accepts an array of mappers as a prop. It inspects `agent.messages` tool-call results and applies the matching mapper, if any. Adding support for a new tool requires registering a new mapper — zero changes to existing components.

Example for the `route` tool (Epic 8):

```typescript
const routeMapper: ToolResultMapper = {
  toolName: "route",
  toMapFeatures: (result) => [ /* RouteToolOutput → MapFeature */ ],
};

<MapProvider mappers={[routeMapper]}>
  <ChatUIProvider>…</ChatUIProvider>
  <MapPanel />
</MapProvider>
```

### Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Extend `ChatUIContextValue` with map state | Permanently couples chat components to map concepts; blocks future component library extraction |
| Global state store (Zustand / Redux) | Heavier dependency; pattern not established in the project; overkill for this scope |
| Inline detection of `route` tool in `ChatView` | Worst option — hard-codes a specific tool name inside a generic UI component |

### Consequences

- `ChatView`, `MessageBubble`, `ToolCallItem` and all existing chat components are **unmodified**.
- Adding a map for any future tool (POI search, area coverage, geofencing…) requires only a new `ToolResultMapper` — no changes to chat or map core components.
- The `MapProvider` depends on `agent.messages` from `@copilotkit/react-core`; this coupling is isolated to one file.
- Session reset (`clearSession`) must be signalled to both `ChatUIProvider` and `MapProvider`; coordination happens at the app level, not inside the providers.

---

## Decision 2 — MapLibre GL JS over Leaflet

### Chosen approach

The map rendering library is **MapLibre GL JS**, consumed via the `react-map-gl` React wrapper (which supports MapLibre as its rendering backend).

### Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Leaflet + react-leaflet | Raster-tile-only by default; no vector tile support; lower performance for many simultaneous features; no WebGL renderer |
| OpenLayers | Comprehensive but heavy; complex API; steeper learning curve; no first-class React integration |
| Mapbox GL JS | Commercial licence required for production use above a free tier; MapLibre is the open-source fork with identical API |

### Rationale

- **IGN Geopf** exposes both raster WMTS tiles and **vector tiles** (TileJSON/MVT). MapLibre can consume both; Leaflet requires plugins for vector tiles.
- MapLibre uses a **WebGL renderer**: smooth animation, better performance when rendering multiple simultaneous route LineStrings.
- **Identical API to Mapbox GL JS** — all IGN documentation and community examples targeting Mapbox GL JS are directly usable.
- `react-map-gl` provides a first-class typed React API (`<Map>`, `<Source>`, `<Layer>`) that aligns with the project's React + TypeScript conventions.
- **Future-proof**: 3D terrain, building extrusion, and globe projection are available without switching libraries.

### Consequences

- Bundle adds ≈ 220 KB gzip (MapLibre GL JS + react-map-gl). Lazy-loading the `MapPanel` component mitigates impact on initial load.
- A MapLibre **style object** (or style URL) is required to initialise the map; the IGN Geopf WMTS raster tile URL is used as the base layer source.
- IGN Geopf raster tiles (WMTS) do not require an API key for standard public layers — no authentication configuration needed for the base map.
- The `MapFeature.geometry` field is **GeoJSON-native**, which MapLibre consumes directly as a `<Source type="geojson">` — no coordinate transformation required.

---

## Related decisions (not in scope of this ADR)

- IGN tile layer selection (Plan IGN v2 vs Ortho vs Carte) — deferred to implementation story 8-FE-2.
- Auto-generated color palette for multiple simultaneous routes — deferred to implementation story 8-FE-2.
- Step-level click → map re-center interaction — deferred to implementation story 8-FE-3.
