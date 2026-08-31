---
title: "talk-ui — Map Visualization of Itineraries"
status: draft
created: 2026-08-31
updated: 2026-08-31
---

# PRD: talk-ui — Map Visualization of Itineraries

## 0. Document Purpose

This PRD defines the frontend requirements for Epic 8: a map panel in `talk-ui` that visualizes itineraries returned by the `route` MCP tool. It is a targeted amendment to the `talk-ui` V1 baseline PRD (`prd-talk-frontend-2026-06-28`), which explicitly anticipated *"domain-specific UI panels (maps, charts) alongside the conversation"*.

The architecture governing this feature is documented in `adr/adr-001-map-visualization-architecture.md` (MapLibre GL JS, decoupled `MapProvider` / `ToolResultMapper` pattern). This PRD does not re-derive those decisions — it references them.

**Related documents:**

- Backend PRD: `prds/prd-map-backend-2026-08-31/prd.md`
- Architecture decision: `adr/adr-001-map-visualization-architecture.md`
- Frontend baseline PRD: `prds/prd-talk-frontend-2026-06-28/prd.md`

## 1. Vision

When a user asks for an itinerary, the assistant calls the `route` tool and narrates the result in prose. The information is accurate but ephemeral — the user cannot spatially orient themselves. Epic 8 adds a persistent, session-scoped map panel that appears automatically alongside the conversation, plots every itinerary returned during the session, and lets the user switch focus between routes with a single click.

Critically, the map infrastructure is **not coupled to navigation data**. The `MapProvider` is a generic host for any GeoJSON feature set; `ToolResultMapper` adapters mediate between specific tool outputs and the map layer. Future features (POI search, geofencing, coverage areas) plug in by registering a new adapter — zero changes to existing chat components.

## 2. Target User

### 2.1 Jobs To Be Done

- **End user (non-technical):** When I ask for directions, I want to see the route on a map without switching applications — and keep all routes from our conversation visible at once.
- **End user:** When I have several itineraries (e.g., car vs. pedestrian, or different destinations), I want to identify each one at a glance and click to focus the map on it.
- **Developer (maintainer):** I want to add map support for a new MCP tool without touching any existing chat component — just register an adapter.

### 2.2 Non-Users (Epic 8)

- Users on mobile-first form factors (responsive layout is not in scope for this epic).
- Users requiring offline map support or tile caching.

### 2.3 Key User Journeys

- **UJ-1. Alex sees his Paris → Lyon route appear on the map automatically.**
  Alex asks "What's the fastest route from Paris to Lyon by car?". The assistant calls `route`, returns the result, and narrates the answer. Simultaneously, the map panel — previously hidden — slides open to the right of the chat. It shows the route as a colored LineString with a start marker (Paris) and an end marker (Lyon). The legend panel on the right of the map shows one entry: *"Paris → Lyon (voiture, le plus rapide) — 461 km, 2h28"*. Alex has not clicked anything.

- **UJ-2. Alex compares two routes.**
  Alex follows up: "And the pedestrian route?". A second `route` call is made. The map adds a second LineString in a different color (dimmer than the first, which is currently selected). The legend now has two entries. Alex clicks the second entry; the second route brightens, the first dims, and the map re-fits to the pedestrian route's bounding box.

- **UJ-3. Alex checks turn-by-turn steps.**
  Alex clicks the "Étapes" tab in the legend panel. He sees the ordered list of navigation steps for the selected route. He clicks "Turn right onto D952" — the map re-centers on that step's coordinates.

- **UJ-4. Alex starts a new conversation.**
  Alex clicks "Nouvelle conversation". The chat resets. The map panel closes and disappears. No itineraries remain. The next route query will re-open the map.

## 3. Functional Requirements

### 3.1 Layout — Collapsible Map Panel

- **FR-1:** The application layout is split: chat on the left, collapsible map panel on the right. The split is implemented by wrapping the existing `ChatView` in a layout container — `ChatView` itself is not modified.
- **FR-2:** The map panel is hidden by default at session start.
- **FR-3:** When a new itinerary is received, the map panel opens automatically if currently closed.
- **FR-4:** The user can manually toggle the map panel open or closed at any time via a visible control.
- **FR-5:** Closing the map panel does not discard itinerary state — reopening restores the last view.

### 3.2 MapProvider — Generic Architecture

- **FR-6:** A `MapProvider` React context is introduced, independent of `ChatUIContext`. It maintains session-scoped itinerary state: `MapFeature[]`, `selectedFeatureId`, `isMapPanelOpen`.
- **FR-7:** `MapProvider` accepts a `mappers: ToolResultMapper[]` prop. It inspects `agent.messages` for tool-call results and applies the matching mapper to extract `MapFeature` objects.
- **FR-8:** The `ToolResultMapper` and `MapFeature` interfaces are defined in a dedicated file (`src/map/types.ts`) with no import dependency on any chat component.
- **FR-9:** When the user resets the session (new conversation), `MapProvider` clears all features and sets `isMapPanelOpen` to `false`.

### 3.3 Map Rendering — MapLibre GL JS

- **FR-10:** The map renders using **MapLibre GL JS** via `react-map-gl`. The base layer uses IGN Geopf raster WMTS tiles (Plan IGN v2). No API key is required.
- **FR-11:** Each itinerary geometry (GeoJSON `LineString`) is rendered as a map layer with an auto-generated color. The `MapPanel` component is **lazy-loaded** to avoid impacting initial bundle size.
- **FR-12:** Unselected itineraries are rendered at reduced opacity (≈ 40%). The selected itinerary is rendered at full opacity and a slightly increased line weight.
- **FR-13:** The route **start point** is rendered as a prominent marker (e.g., green circle).
- **FR-14:** The route **end point** is rendered as a prominent marker (e.g., red circle), visually distinct from the start.
- **FR-15:** **Intermediate waypoints** (if any) are rendered as markers that are visually distinct from start/end but smaller and more discreet (e.g., smaller neutral-color dot).
- **FR-16:** When a new itinerary is added, the map viewport auto-fits to its bounding box (`bbox`). When no itinerary is selected, the viewport fits all itineraries' combined bounding box.

### 3.4 Legend Panel

- **FR-17:** The legend panel is embedded within the map view on the right side. It lists all session itineraries.
- **FR-18:** Each legend entry displays: `StartLabel → EndLabel (profile, optimization)`, formatted distance, formatted duration. If `StartLabel`/`EndLabel` are absent, the snapped coordinate strings are shown as fallback.
- **FR-19:** The legend panel has two tabs: **Résumé** (one entry per itinerary, as per FR-18) and **Étapes** (turn-by-turn steps for the currently selected itinerary).
- **FR-20:** The **Étapes** tab lists each `RouteStep` for the selected itinerary: instruction type, modifier, road name/number, formatted distance and duration per step.
- **FR-21:** Clicking a legend entry (Résumé tab): (a) selects that itinerary, (b) re-fits the map to its bbox, (c) applies full-opacity rendering, (d) dims all others.
- **FR-22:** Clicking a step (Étapes tab): re-centers the map on that step's start coordinates without changing zoom level.
- **FR-23:** The selected legend entry is visually marked as active (e.g., highlighted background, bold label).

### 3.5 IGN Route Adapter

- **FR-24:** A `routeToolMapper` adapter (`src/map/adapters/route-tool-mapper.ts`) implements `ToolResultMapper` for `toolName: "route"`. It transforms a `RouteToolOutput` into one `MapFeature` with: id, label (from `StartLabel`/`EndLabel` + profile/optimization), geometry, bbox, and properties (distance, duration, profile, optimization, portions/steps).
- **FR-25:** The `routeToolMapper` is registered in `MapProvider` at the application root (`App.tsx` or equivalent). No chat component imports or references it.

## 4. Non-Functional Requirements

- **NFR-1:** `MapPanel` is lazy-loaded (React `lazy` + `Suspense`) — MapLibre GL JS does not appear in the initial bundle.
- **NFR-2:** Adding support for a new tool's geo data requires only a new `ToolResultMapper` implementation and one line of registration — no changes to `ChatView`, `ChatUIContext`, `MapPanel`, or `MapLegend`.
- **NFR-3:** All new types (`MapFeature`, `ToolResultMapper`) are strictly typed; no `any` in the public interfaces.
- **NFR-4:** The auto-generated color palette ensures sufficient visual contrast between simultaneous routes (minimum 4 visually distinct colors before cycling).

## 5. Out of Scope (Epic 8)

- Mobile / responsive layout for the split view.
- Route export or sharing.
- Turn-by-turn step markers on the map (clicking a step re-centers, but no pin is added to the map layer).
- Map style switcher (ortho vs. plan IGN vs. vector).
- Offline tile caching.
- `IntermediateLabels` in the legend (waypoints appear on the map as markers but have no legend entry).
