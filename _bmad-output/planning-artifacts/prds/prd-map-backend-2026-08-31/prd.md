---
title: "mcp-ign-nav — Map Visualization Support"
status: draft
created: 2026-08-31
updated: 2026-08-31
---

# PRD: mcp-ign-nav — Map Visualization Support

## 0. Document Purpose

This PRD defines the backend changes required in `mcp-ign-nav` to support map visualization of itineraries in `talk-ui`. It is a targeted amendment to the existing `mcp-ign-nav` MCP server — not a standalone product. Downstream consumers are the Epic 8 frontend stories and any future tool adapter registered in `MapProvider`.

**Related documents:**

- Frontend PRD: `prds/prd-map-frontend-2026-08-31/prd.md`
- Architecture decision: `adr/adr-001-map-visualization-architecture.md`
- Backend baseline PRD: `prds/prd-talk-bmad-2026-06-21/prd.md`

## 1. Vision

The `route` MCP tool currently returns distance, duration, and navigation steps — but geometry is gated behind an environment variable (`GET_GEOJSON_GEOMETRY`) that defaults to `false`. This creates an operational risk (geometry silently absent in production), a conceptual mismatch (the `distance_time` tool already covers the no-geometry use case), and unnecessary complexity.

This PRD removes that ambiguity: the `route` tool unconditionally returns GeoJSON geometry and optionally carries human-readable place-name labels that the LLM can supply, enabling rich legend display in the frontend without any additional API call.

## 2. Target User

### 2.1 Jobs To Be Done

- **LLM agent:** When I calculate a route, I want to pass the place names I already know (from prior geocoding) so the frontend can display a meaningful legend label without reverse-geocoding.
- **Frontend (MapProvider):** When I receive a `route` tool result, I want to reliably find a GeoJSON geometry and, optionally, human-readable labels — with no conditional checks on environment configuration.
- **Operator/deployer:** I want fewer environment variables to manage. Geometry is always present for the tool that semantically requires it.

### 2.2 Non-Users

- Users who only need travel time — they use `distance_time`, which is unaffected.

## 3. Functional Requirements

### 3.1 Remove Geometry Flag

- **FR-1:** The `getGeometry bool` field is removed from `RouteTool`. The tool unconditionally sets `GetGeometry: true` when calling the IGN Navigation API.
- **FR-2:** `GetGeoJSONGeometry bool` is removed from `ServerEnv`. The `GET_GEOJSON_GEOMETRY` environment variable is no longer read or documented.
- **FR-3:** The `DistanceTimeTool` is unchanged — it continues to request no geometry.
- **FR-4:** All existing tests that construct `NewRouteTool(limiter, false)` are updated to `NewRouteTool(limiter)`. Tests asserting the absence of geometry are removed or updated to assert its presence.

### 3.2 Human-Readable Place Labels

- **FR-5:** `RouteToolInput` gains two optional fields: `StartLabel string` and `EndLabel string`. Description strings instruct the LLM to populate them with the human-readable origin and destination names it already resolved (e.g., `"Paris"`, `"Lyon"`). Both fields are `omitempty`.
- **FR-6:** `RouteToolOutput` gains corresponding `StartLabel string` and `EndLabel string` fields, echoing the input values verbatim. If the input fields were empty, the output fields are also empty. No processing or validation is applied.
- **FR-7:** The `DistanceTimeToolInput` and `DistanceTimeToolOutput` are **not** extended — place labels are only meaningful when geometry is present.

## 4. Non-Functional Requirements

- **NFR-1:** The changes introduce no new external API calls.
- **NFR-2:** Existing integration tests (`route_tool_test.go`) continue to pass after updating constructor signatures.
- **NFR-3:** The `GET_GEOJSON_GEOMETRY` entry is removed from `.env.example` (if present) and any README documentation.

## 5. Out of Scope

- Reverse geocoding of snapped start/end coordinates.
- `IntermediateLabels` for waypoints (deferred — no frontend requirement in Epic 8).
- Changes to `distance_time`, `geocode`, or `reverse_geocode` tools.
