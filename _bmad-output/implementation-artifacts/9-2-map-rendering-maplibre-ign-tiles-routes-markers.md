---
baseline_commit: 9d59e56
---

# Story 9.2: Map rendering — MapLibre GL JS, IGN tiles, routes and markers

Status: done

## Story

As an end user,
I want to see my itinerary drawn on an interactive map with clear start and end markers,
So that I can spatially understand the route.

## Acceptance Criteria (BDD)

**AC#1** — MapLibre GL JS with IGN Geopf base layer
**Given** `MapPanel` is rendered for the first time
**When** the map initializes
**Then** it uses MapLibre GL JS via `react-map-gl/maplibre`
**And** the base layer is the IGN Geopf Plan IGN v2 raster WMTS tile layer loaded from `https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2&STYLE=normal&FORMAT=image/png&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}`
**And** no API key is required to load the tiles
**And** `MapPanel` is lazy-loaded in `App.tsx` via React `lazy` + `Suspense`

**AC#1b** — Default viewport is metropolitan France
**Given** `MapPanel` initializes with no itineraries
**When** the map first renders
**Then** the viewport fits the metropolitan France bounding box `[-5.14, 41.33, 9.56, 51.09]` (minLon, minLat, maxLon, maxLat) via `initialViewState={{ bounds: FRANCE_BOUNDS, fitBoundsOptions: { padding: 20 } }}`
**And** this ensures the full France territory is visible regardless of the container's aspect ratio

**AC#1c** — Viewport resets to France after session reset
**Given** itineraries were present and the session is reset (`itineraries` becomes empty)
**When** `MapPanel` detects the reset
**Then** the viewport fits back to the France bounding box (same bbox and padding as AC#1b)

**AC#2** — LineString layers per itinerary
**Given** one or more `MapFeature` objects in `MapProvider` state
**When** `MapPanel` renders
**Then** each feature's `geometry` (GeoJSON `LineString`) is rendered as a `<Source type="geojson">` + `<Layer type="line">`
**And** each feature has an auto-generated color from the palette `["#2196F3", "#FF5722", "#4CAF50", "#9C27B0", "#FF9800"]`, indexed by feature position in `itineraries` (cycling after 5)
**And** unselected features are rendered at ≈40% opacity (`line-opacity: 0.4`, `line-width: 3`)
**And** the selected feature is rendered at 100% opacity (`line-opacity: 1`, `line-width: 5`)

**AC#3** — Viewport auto-fit to new itinerary
**Given** a new `MapFeature` is added to `itineraries`
**When** the map updates
**Then** the viewport fits to that feature's `bbox` via `mapRef.current.fitBounds(feature.bbox, { padding: 40, duration: 500 })`

**AC#4** — Viewport fits all features when none is selected
**Given** no feature is selected (`selectedFeatureId === null`) and multiple features exist
**When** the map renders
**Then** the viewport fits the union bounding box of all features (merged `bbox` of all `itineraries`)
**Note** this is the initial fit on first render only (when `selectedFeatureId` has never been set); user panning after that is not overridden

**AC#5** — Start marker (green)
**Given** a `MapFeature` with `geometry.type === "LineString"` and at least one coordinate
**When** the feature is rendered
**Then** the first coordinate (`geometry.coordinates[0]`) is rendered as a prominent start marker: a green circle, larger than waypoint markers
**And** the marker is distinct from other markers by color (green) and size (diameter ≈ 16 px)

**AC#6** — End marker (red)
**Given** a `MapFeature` with `geometry.type === "LineString"` and at least two coordinates
**When** the feature is rendered
**Then** the last coordinate (`geometry.coordinates[coordinates.length - 1]`) is rendered as a prominent end marker: a red circle, same size as the start marker
**And** the end marker is visually distinct from the start marker by color (red vs green)

**AC#7** — Intermediate waypoint markers
**Given** a `MapFeature` with `properties.portions` containing more than one portion
**When** the feature is rendered
**Then** the `start` coordinate of each portion after the first (i.e., `portions[1].start`, `portions[2].start`, …) is rendered as a smaller, neutral-color dot marker (diameter ≈ 10 px, slate/grey color)
**And** waypoint markers are visually smaller and more discreet than start/end markers
**Note** `portions[i].start` is a string in `"longitude,latitude"` format; parse it before use; skip silently on parse failure

**AC#8** — Map resize on panel open
**Given** the map container uses a CSS `transition-[width]` (300 ms) in `SplitLayout`
**When** `isMapPanelOpen` transitions from `false` to `true`
**Then** `map.resize()` is called after the transition completes (≥ 310 ms delay) so MapLibre recomputes the canvas dimensions
**And** the map renders correctly at its full `w-1/2` width with no blank area

**AC#9** — `aria-hidden` on collapsed panel
**Given** the map panel container has `w-0` when closed
**When** `isMapPanelOpen` is `false`
**Then** the container has `aria-hidden="true"` (added to `SplitLayout`'s right div)
**And** when `isMapPanelOpen` is `true`, `aria-hidden` is absent or `"false"`

**AC#10** — CI gates
**Given** the implementation is complete
**When** `pnpm lint && pnpm test && pnpm build` are executed
**Then** all pass with zero regressions and zero new type errors

## Tasks / Subtasks

- [x] Task 1: Install `maplibre-gl` and `react-map-gl` (AC: #1, #1b, #1c)
  - [x] 1.1 Run `pnpm add maplibre-gl react-map-gl` in `talk-ui`
  - [x] 1.2 Verify both packages appear in `dependencies` in `package.json`
  - [x] 1.3 Verify TypeScript picks up `maplibre-gl` types (bundled in `maplibre-gl`) and `react-map-gl` types (bundled in `react-map-gl`)

- [x] Task 2: Create `src/map/MapPanel.tsx` — core map component (AC: #1–#8)
  - [ ] 2.1 Import the MapLibre CSS at the top of the file (Vite handles CSS-in-TS imports):
    ```typescript
    import 'maplibre-gl/dist/maplibre-gl.css';
    ```
  - [ ] 2.2 Import `Map`, `Source`, `Layer`, `Marker` and the `MapRef` type from `react-map-gl/maplibre`
  - [ ] 2.3 Define constants outside the component:
    ```typescript
    const ROUTE_COLORS = ["#2196F3", "#FF5722", "#4CAF50", "#9C27B0", "#FF9800"] as const;

    const IGN_TILE_URL =
      "https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0" +
      "&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2&STYLE=normal&FORMAT=image/png" +
      "&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}";

    // Metropolitan France [minLon, minLat, maxLon, maxLat]
    const FRANCE_BOUNDS: [number, number, number, number] = [-5.14, 41.33, 9.56, 51.09];

    const MAP_STYLE = {
      version: 8 as const,
      sources: {
        'ign-plan': {
          type: 'raster' as const,
          tiles: [IGN_TILE_URL],
          tileSize: 256,
          maxzoom: 18,
          attribution: '© IGN',
        },
      },
      layers: [{ id: 'ign-plan-layer', type: 'raster' as const, source: 'ign-plan' }],
    };
    ```
  - [ ] 2.4 Define a Zod schema to safely parse `portions` items when extracting intermediate waypoints:
    ```typescript
    import { z } from 'zod/v4';
    const portionStartSchema = z.object({ start: z.string() });

    function parseWaypoints(portions: unknown[]): [number, number][] {
      return portions
        .slice(1)
        .flatMap((p) => {
          const r = portionStartSchema.safeParse(p);
          if (!r.success) return [];
          const parts = r.data.start.split(',');
          if (parts.length < 2) return [];
          const lon = parseFloat(parts[0] ?? '');
          const lat = parseFloat(parts[1] ?? '');
          return isNaN(lon) || isNaN(lat) ? [] : [[lon, lat] as [number, number]];
        });
    }
    ```
  - [ ] 2.5 Implement auto-fit effect for new features and session reset (AC: #3, #1c):
    - Use `useRef<number>(0)` to track the previous `itineraries.length`
    - In `useEffect([itineraries])`: when `itineraries.length > prevCountRef.current`, call `mapRef.current?.fitBounds(newest.bbox, { padding: 40, duration: 500 })`; always update `prevCountRef.current = itineraries.length`
    - The `newest` feature is `itineraries[itineraries.length - 1]`
    - When `itineraries.length` drops back to `0` (session reset), call `mapRef.current?.fitBounds(FRANCE_BOUNDS, { padding: 20, duration: 500 })`
    - `bbox` shape `[minLon, minLat, maxLon, maxLat]` is directly accepted by MapLibre `fitBounds` as `LngLatBoundsLike`
  - [ ] 2.6 Implement fit-to-selected effect (AC: #4 steady state):
    - In `useEffect([selectedFeatureId])`: when `selectedFeatureId` is non-null, find the feature and call `fitBounds`
    - This handles "click legend entry → fit bbox" (story 9.3 will trigger it by changing `selectedFeatureId`)
  - [ ] 2.7 Implement resize effect on panel open (AC: #8):
    ```typescript
    useEffect(() => {
      if (!isMapPanelOpen) return;
      const tid = setTimeout(() => {
        mapRef.current?.getMap().resize();
      }, 310);
      return () => { clearTimeout(tid); };
    }, [isMapPanelOpen]);
    ```
  - [ ] 2.8 Render the `<Map>` component (AC: #1, #1b):
    - `ref={mapRef}`
    - `initialViewState={{ bounds: FRANCE_BOUNDS, fitBoundsOptions: { padding: 20 } }}`
    - `style={{ width: '100%', height: '100%' }}`
    - `mapStyle={MAP_STYLE}`
    - No `onLoad` prop needed — `initialViewState.bounds` is processed by react-map-gl at init time
  - [ ] 2.9 Inside `<Map>`, iterate `itineraries.map((feature, idx) => ...)` and for each feature render (AC: #2, #5, #6, #7):
    - A `<Source id={\`route-${feature.id}\`} type="geojson" data={geoJsonData}>` wrapping:
      - A `<Layer id={\`line-${feature.id}\`} type="line" paint={...} layout={{ 'line-cap': 'round', 'line-join': 'round' }} />`
      - `line-color`: `ROUTE_COLORS[idx % ROUTE_COLORS.length]`
      - `line-width`: `isSelected ? 5 : 3`
      - `line-opacity`: `isSelected ? 1 : 0.4`
    - A start `<Marker>` at `coordinates[0]` with a green circle div (16 × 16 px, `rounded-full bg-green-500 border-2 border-white shadow`)
    - An end `<Marker>` at `coordinates[coordinates.length - 1]` with a red circle div (16 × 16 px, `rounded-full bg-red-500 border-2 border-white shadow`)
    - One `<Marker>` per intermediate waypoint from `parseWaypoints(portions)` with a smaller neutral circle div (10 × 10 px, `rounded-full bg-slate-400 border-2 border-white shadow`)
    - Wrap each feature's group in `<Fragment key={feature.id}>`
  - [ ] 2.10 The `geoJsonData` for each source is a GeoJSON FeatureCollection:
    ```typescript
    const geoJsonData = {
      type: 'FeatureCollection' as const,
      features: [{ type: 'Feature' as const, geometry: feature.geometry, properties: {} }],
    };
    ```
  - [ ] 2.11 TypeScript: `feature.geometry` is `GeoJSON.Geometry`; cast to `GeoJSON.LineString` to access `.coordinates` — this is safe given the mapper always produces a LineString; guard with `feature.geometry.type === 'LineString'` before accessing `.coordinates`
  - [ ] 2.12 Export `MapPanel` as a **named export** (not default, consistent with project conventions)

- [x] Task 3: Update `src/components/SplitLayout.tsx` — add `aria-hidden` (AC: #9)
  - [ ] 3.1 Add `aria-hidden={!mapPanelOpen || undefined}` to the right panel `<div>` (MapLibre aria)
    - When closed: `aria-hidden="true"`
    - When open: attribute absent (do not set `aria-hidden="false"`)

- [x] Task 4: Update `src/App.tsx` — lazy-load `MapPanel` (AC: #1)
  - [ ] 4.1 Add lazy import at the top of the file:
    ```typescript
    import { lazy, Suspense } from 'react';
    const LazyMapPanel = lazy(() =>
      import('./map/MapPanel').then((m) => ({ default: m.MapPanel }))
    );
    ```
  - [ ] 4.2 Replace the placeholder div in `AppLayout`'s `mapPanel` prop with:
    ```tsx
    mapPanel={
      <Suspense fallback={<div className="flex h-full items-center justify-center text-sm text-muted">Chargement…</div>}>
        <LazyMapPanel />
      </Suspense>
    }
    ```
  - [ ] 4.3 Remove the old placeholder div (`<div className="flex h-full items-center justify-center text-sm text-muted">Map — story 9.2</div>`)

- [x] Task 5: Tests — `src/__tests__/map-panel.test.tsx` (AC: #1–#9, #10)
  - [ ] 5.1 Mock `react-map-gl/maplibre` entirely (WebGL is not available in jsdom):
    ```typescript
    const mockFitBounds = vi.fn();
    const mockResize = vi.fn();
    const mockGetMap = vi.fn(() => ({ resize: mockResize }));
    const mockMapRef = { fitBounds: mockFitBounds, getMap: mockGetMap };

    vi.mock('react-map-gl/maplibre', () => ({
      Map: vi.fn(({ children, mapRef: _mapRef }: { children?: React.ReactNode; mapRef?: unknown }) => (
        <div data-testid="maplibre-map">{children}</div>
      )),
      Source: vi.fn(({ children }: { children?: React.ReactNode }) => <div>{children}</div>),
      Layer: vi.fn(() => null),
      Marker: vi.fn(({ children }: { children?: React.ReactNode }) => (
        <div data-testid="marker">{children}</div>
      )),
    }));
    ```
    - **Important**: `useRef` in `MapPanel` will not point to the mock; instead spy on `useRef` to inject `mockMapRef`, or test the effect triggers via callbacks exposed through the mock.
    - Simpler approach: capture the `ref` prop forwarded to the mock `Map` and assign it manually in the test setup.
  - [ ] 5.2 Mock `maplibre-gl/dist/maplibre-gl.css` in `vitest.config.ts` or via a `moduleNameMapper` if CSS imports fail:
    - In `vite.config.ts` (already configured for tests), add: `css: false` under `test` options, or handle CSS via existing setup
  - [ ] 5.3 **Test: IGN tile URL in mapStyle** — render `<MapPanel />` inside a minimal `MapProvider`-like wrapper that provides a mock `MapContextValue`; assert the `Map` mock was called with `mapStyle` containing the IGN tile URL in `mapStyle.sources['ign-plan'].tiles[0]`
  - [ ] 5.4 **Test: one Source per feature** — provide 2 features in context; assert 2 `Source` components are rendered with distinct ids
  - [ ] 5.5 **Test: opacity differentiation** — provide 2 features, set `selectedFeatureId` to feature[0].id; assert `Layer` for feature[0] is called with `line-opacity: 1` and `line-width: 5`; assert `Layer` for feature[1] is called with `line-opacity: 0.4` and `line-width: 3`
  - [ ] 5.6 **Test: start and end markers** — provide 1 feature with a 3-coordinate LineString; assert exactly 2 `Marker` components are rendered (one green, one red) plus 0 intermediate markers (no portions beyond 1)
  - [ ] 5.7 **Test: intermediate waypoints** — provide 1 feature with `properties.portions` containing 3 portions (`[{ start: "2.0,48.0" }, { start: "2.5,48.5" }, { start: "3.0,49.0" }]`); assert 2 intermediate `Marker` components are rendered (portions[1].start and portions[2].start)
  - [ ] 5.8 **Test: invalid portion start skipped** — provide a feature with `properties.portions = [{ start: "2.0,48.0" }, { start: "not,a,valid,coord" }, { start: "3.0,49.0" }]`; assert only 1 intermediate marker rendered (the one with valid coordinate)
  - [ ] 5.9 **Test: auto-color cycling** — provide 6 features; assert the 6th feature (index 5) gets color `"#2196F3"` (index 0 cycling)
  - [ ] 5.10 **Test: resize on panel open** — use `vi.useFakeTimers()`; render with `isMapPanelOpen: false`; update context to `isMapPanelOpen: true`; advance timers by 310 ms; assert `mockResize` was called
  - [ ] 5.11 **Test: France bbox on session reset** — render with 1 feature, then update context to `itineraries: []`; assert `mockFitBounds` was called with `[-5.14, 41.33, 9.56, 51.09]`
  - [ ] 5.12 **Test: initialViewState uses FRANCE_BOUNDS** — assert the `Map` mock was called with `initialViewState` containing `bounds: [-5.14, 41.33, 9.56, 51.09]`

- [x] Task 6: Run CI gates (AC: #10)
  - [x] 6.1 Run `pnpm lint` — 0 errors
  - [x] 6.2 Run `pnpm test` — 0 failures (189/189)
  - [x] 6.3 Run `pnpm build` — 0 type errors

## Dev Notes

### Component tree after story 9.2

```
CopilotKit (in __root.tsx — unchanged)
└── App
    └── MapProvider (mappers=[routeToolMapper])
        └── AppLayout (inner component)
            ├── ChatUIProvider
            │   └── SplitLayout (mapPanelOpen, mapPanel=<Suspense><LazyMapPanel /></Suspense>)
            │       ├── ChatView (UNCHANGED)
            │       └── <Suspense fallback=…>
            │           └── MapPanel  ← NEW (lazy-loaded on first open)
            └── [toggle button — already in SplitLayout]
```

### `react-map-gl` import path for MapLibre

Always import from `react-map-gl/maplibre` (not from `react-map-gl` directly). This entry point pre-configures MapLibre GL JS as the rendering engine without requiring `mapLib` prop injection.

```typescript
import { Map, Source, Layer, Marker } from 'react-map-gl/maplibre';
import type { MapRef } from 'react-map-gl/maplibre';
```

Do **not** import from `maplibre-gl` directly in `MapPanel.tsx` (except via the CSS import which Vite handles as a side-effect).

### Map style object type

`react-map-gl/maplibre` accepts `mapStyle` typed as `maplibregl.StyleSpecification | string`. The inline object literal above satisfies `StyleSpecification` structurally — no explicit import of the type is needed unless TypeScript complains.

### `fitBounds` signature

```typescript
mapRef.current?.fitBounds(
  feature.bbox,                          // [minLon, minLat, maxLon, maxLat] — accepted as LngLatBoundsLike
  { padding: 40, duration: 500 }
);
```

MapLibre's `LngLatBoundsLike` accepts a flat 4-tuple `[w, s, e, n]` in addition to the `[[sw], [ne]]` form. `MapFeature.bbox` is `[minLon, minLat, maxLon, maxLat]` = `[w, s, e, n]` — direct pass-through, no conversion needed.

### Default France extent and auto-fit implementation

```typescript
const FRANCE_BOUNDS: [number, number, number, number] = [-5.14, 41.33, 9.56, 51.09];
```

`initialViewState={{ bounds: FRANCE_BOUNDS, fitBoundsOptions: { padding: 20 } }}` handles the initial render correctly regardless of the container's aspect ratio — unlike a fixed `longitude/latitude/zoom` triple which does not adapt to container size.

Track `itineraries.length` across renders with a ref to react on count changes:

```typescript
const prevCountRef = useRef(0);

useEffect(() => {
  const current = itineraries.length;
  if (current > prevCountRef.current && current > 0) {
    const newest = itineraries[current - 1];
    if (newest) {
      mapRef.current?.fitBounds(newest.bbox, { padding: 40, duration: 500 });
    }
  } else if (current === 0 && prevCountRef.current > 0) {
    // Session reset: return to France
    mapRef.current?.fitBounds(FRANCE_BOUNDS, { padding: 20, duration: 500 });
  }
  prevCountRef.current = current;
}, [itineraries]);
```

Do **not** use `itineraries` identity as the trigger for `fitBounds` on every re-render — only trigger when the count changes.

### Resize on panel open

`SplitLayout` transitions `width` over 300 ms. MapLibre needs its container to have reached its final size before `resize()`. Wait at least 310 ms:

```typescript
useEffect(() => {
  if (!isMapPanelOpen) return;
  const tid = window.setTimeout(() => {
    mapRef.current?.getMap().resize();
  }, 310);
  return () => { window.clearTimeout(tid); };
}, [isMapPanelOpen]);
```

### `GeoJSON.LineString` narrowing

`MapFeature.geometry` is `GeoJSON.Geometry` (union type). Before accessing `.coordinates`, narrow the type:

```typescript
if (feature.geometry.type !== 'LineString') return null;
const coordinates = feature.geometry.coordinates; // now typed as number[][]
```

You can do this narrowing inside the `itineraries.map(...)` render function and return `null` for non-LineString geometries (to support future feature types without breaking).

### Auto-color palette

```typescript
const ROUTE_COLORS = ["#2196F3", "#FF5722", "#4CAF50", "#9C27B0", "#FF9800"] as const;
// Usage: ROUTE_COLORS[idx % ROUTE_COLORS.length]
```

The index `idx` comes from `itineraries.map((feature, idx) => ...)` — it is the feature's position in the current `itineraries` array. This means feature colors can shift if the session is reset and new features are added. This is acceptable; story 9.3 adds a legend that uses labels for identification.

### Testing MapLibre in jsdom

jsdom has no WebGL. Mocking `react-map-gl/maplibre` is the only viable approach. Use `vi.mock` at the module level.

To test `fitBounds` and `resize` calls, you need access to the mocked `MapRef`. The cleanest approach: in the mock, expose a callback that captures the ref:

```typescript
let capturedRef: React.RefObject<unknown> | null = null;

vi.mock('react-map-gl/maplibre', () => ({
  Map: vi.fn(
    ({ ref, children }: { ref?: React.RefObject<unknown>; children?: ReactNode }) => {
      if (ref) capturedRef = ref;
      return <div data-testid="maplibre-map">{children}</div>;
    }
  ),
  // …
}));
```

Then, before tests that check `fitBounds`, manually assign the mock to the captured ref:
```typescript
if (capturedRef) {
  (capturedRef as React.MutableRefObject<unknown>).current = mockMapRef;
}
```

Alternatively, mock `useRef` via `vi.spyOn(React, 'useRef')` — but this is fragile as it intercepts all `useRef` calls. The ref-capture approach above is safer.

### CSS import for MapLibre

Vite handles `import 'maplibre-gl/dist/maplibre-gl.css'` natively. In the test environment (jsdom via Vitest), CSS imports are ignored by default — no additional configuration needed if `css: false` is not set.

If the test runner throws on CSS imports, add to `vite.config.ts` test section:
```typescript
css: { modules: { classNameStrategy: 'non-scoped' } }
```
Or simply add `'maplibre-gl/dist/maplibre-gl.css'` to `server.fs.deny` exclusion. Check existing test config first.

### `SplitLayout` `aria-hidden` update

In `SplitLayout.tsx`, the right panel `<div>` currently has no aria attributes. Add:

```tsx
<div
  aria-hidden={!mapPanelOpen || undefined}
  className={`min-w-0 overflow-hidden transition-[width] duration-300 ease-in-out ${
    mapPanelOpen ? "w-1/2 border-l border-white/10" : "w-0"
  }`}
>
```

`undefined` removes the attribute from the DOM when `mapPanelOpen` is `true` (React drops attributes that are `undefined`), which is cleaner than `aria-hidden="false"`.

### Files created / updated

| File | Action | What changes |
|------|--------|--------------|
| `package.json` | UPDATE | Add `maplibre-gl` and `react-map-gl` to `dependencies` |
| `pnpm-lock.yaml` | UPDATE | Lockfile regenerated by pnpm |
| `src/map/MapPanel.tsx` | CREATE | MapLibre map component — IGN base layer, LineString layers, markers |
| `src/App.tsx` | UPDATE | Lazy-load `MapPanel` via `React.lazy` + `Suspense`; replace placeholder |
| `src/components/SplitLayout.tsx` | UPDATE | Add `aria-hidden` to right panel div |
| `src/__tests__/map-panel.test.tsx` | CREATE | Unit tests for `MapPanel` rendering and effects |

No changes to `MapProvider`, `map-context.ts`, `types.ts`, `route-tool-mapper.ts`, `ChatView`, or any existing chat component.
