---
baseline_commit: dc45780740b4e7108362da78b2a51dbb0f7530d2
---

# Story 8.1: Remove `getGeometry` flag — `route` always returns GeoJSON geometry

Status: in-progress

## Story

As a platform operator,
I want the `route` tool to always return GeoJSON geometry without any environment configuration,
so that map visualization works reliably in all deployments and the codebase is simpler.

## Acceptance Criteria

1. `NewRouteTool(limiter *rate.Limiter)` takes no `getGeometry` parameter — the `bool` arg is gone.
2. The tool unconditionally sets `GetGeometry: true` in every IGN API request.
3. `RouteToolOutput.Geometry` is always populated (never nil) for a successful `Call()`.
4. `GetGeoJSONGeometry bool` field is removed from `ServerEnv`.
5. `GET_GEOJSON_GEOMETRY` is no longer read from the environment.
6. The field and its comment are removed from `.env.example`.
7. All README references to "optionally GeoJSON geometry (when `GET_GEOJSON_GEOMETRY=true`)" are updated to state geometry is always returned.
8. `DistanceTimeTool`, `GeocodingTool`, `ReverseGeocodingTool` are untouched.
9. All call sites of `NewRouteTool` and `newRouteToolWithBaseURL` are updated to drop the `getGeometry` argument.
10. Tests that assert the *absence* of geometry are removed; at least one test asserts geometry is always present in a successful response.
11. `go test ./...` in `mcp-ign-nav` passes with no failures.

## Tasks / Subtasks

- [ ] Remove `getGeometry bool` field from `RouteTool` struct (AC: 1, 2, 3)
  - [ ] Remove field from struct definition in `route_tool.go`
  - [ ] Remove `getGeometry` parameter from `NewRouteTool` signature
  - [ ] Remove `getGeometry` parameter from `newRouteToolWithBaseURL` signature
  - [ ] Replace `GetGeometry: t.getGeometry` with `GetGeometry: true` in `Call()`
  - [ ] Remove the conditional `if t.getGeometry { geometry = result.Geometry }` block — always assign `result.Geometry`
- [ ] Remove `GetGeoJSONGeometry` from config (AC: 4, 5)
  - [ ] Delete field from `ServerEnv` struct in `config.go`
  - [ ] Delete `GET_GEOJSON_GEOMETRY` env var load in `LoadServerEnv`
- [ ] Update `cmd/main.go` (AC: 9)
  - [ ] Change `NewRouteTool(navLimiter, env.GetGeoJSONGeometry)` → `NewRouteTool(navLimiter)`
- [ ] Update `.env.example` (AC: 6)
  - [ ] Remove `GET_GEOJSON_GEOMETRY` line and its preceding comment block
- [ ] Update `README.md` (AC: 7)
  - [ ] Change route tool description to say geometry is always returned (remove "optionally" / `GET_GEOJSON_GEOMETRY` reference)
- [ ] Update tests (AC: 9, 10, 11)
  - [ ] `route_tool_test.go`: update all `NewRouteTool(limiter, ...)` → `NewRouteTool(limiter)` and all `newRouteToolWithBaseURL(..., true/false)` → drop bool arg
  - [ ] `route_tool_test.go`: assert `result.Geometry != nil` in `TestRouteTool_Call_Success`
  - [ ] `cmd/main_test.go`: remove `TestBuildApp_WithGeoJSONGeometry` (tests a param that no longer exists)
  - [ ] `internal/config/config_test.go`: remove `TestLoadServerEnv_GetGeoJSONGeometry` and remove `GetGeoJSONGeometry` assertion from `TestLoadServerEnv_NoFileNoVars`

## Dev Notes

### Summary of Change

This is a **pure simplification**: delete a feature flag, hardcode the formerly optional behavior as always-on. No new logic is introduced. The IGN route API already supports geometry — the only change is making it unconditional.

### Files Being Modified

| File | Action | What changes |
|------|--------|-------------|
| `mcp-ign-nav/internal/tools/route_tool.go` | UPDATE | Remove `getGeometry bool` from struct + constructors; unconditional `GetGeometry: true`; unconditional geometry assignment |
| `mcp-ign-nav/internal/config/config.go` | UPDATE | Remove `GetGeoJSONGeometry bool` field and its env load |
| `mcp-ign-nav/cmd/main.go` | UPDATE | Drop `env.GetGeoJSONGeometry` arg from `NewRouteTool` call |
| `mcp-ign-nav/cmd/main_test.go` | UPDATE | Remove `TestBuildApp_WithGeoJSONGeometry` |
| `mcp-ign-nav/internal/config/config_test.go` | UPDATE | Remove `GetGeoJSONGeometry` test and assertion |
| `mcp-ign-nav/internal/tools/route_tool_test.go` | UPDATE | Update call signatures; add geometry-always-present assertion |
| `mcp-ign-nav/.env.example` | UPDATE | Remove `GET_GEOJSON_GEOMETRY` entry |
| `mcp-ign-nav/README.md` | UPDATE | Remove "optionally" language from route output description |

No files are created. `DistanceTimeTool` and its tests are **not touched**.

### Current State of `route_tool.go` (what to remove/change)

```go
// RouteTool struct — REMOVE getGeometry field
type RouteTool struct {
    client      *routeClient
    getGeometry bool          // DELETE THIS
}

// NewRouteTool — REMOVE getGeometry parameter
func NewRouteTool(limiter *rate.Limiter, getGeometry bool) *RouteTool {
    return &RouteTool{
        client:      newRouteClient(navigationBaseURL, &http.Client{Timeout: httpClientTimeout}, limiter),
        getGeometry: getGeometry,   // DELETE THIS
    }
}

// newRouteToolWithBaseURL — REMOVE getGeometry parameter
func newRouteToolWithBaseURL(baseURL string, httpClient *http.Client, getGeometry bool) *RouteTool {
    return &RouteTool{
        client:      newRouteClient(baseURL, httpClient, rate.NewLimiter(rate.Inf, 0)),
        getGeometry: getGeometry,   // DELETE THIS
    }
}

// In Call() — CHANGE to always-on
// FROM:
result, err := t.client.callRouteAPI(ctx, routeParams{
    ...
    GetGeometry:   t.getGeometry,   // CHANGE TO: GetGeometry: true
})
// AND REMOVE:
var geometry *GeoJSONGeometry
if t.getGeometry {
    geometry = result.Geometry
}
// REPLACE WITH:
geometry := result.Geometry

// In RouteToolOutput construction:
Geometry: geometry,  // unchanged, but now geometry is always result.Geometry
```

### Current State of `config.go` (what to remove)

```go
type ServerEnv struct {
    mcpserver.BaseEnv
    GetGeoJSONGeometry bool   // DELETE THIS FIELD
}

func LoadServerEnv(envFiles ...string) (*ServerEnv, error) {
    _ = godotenv.Load(envFiles...)
    env := &ServerEnv{
        BaseEnv:            mcpserver.LoadBaseEnv(),
        GetGeoJSONGeometry: strings.EqualFold(os.Getenv("GET_GEOJSON_GEOMETRY"), "true"),  // DELETE
    }
    return env, nil
}
```
After removing the field, the `strings` import may become unused — remove it if so.

### Current State of `cmd/main.go` (what to change)

```go
// FROM:
mcpserver.RegisterTool(tools.NewRouteTool(navLimiter, env.GetGeoJSONGeometry)),
// TO:
mcpserver.RegisterTool(tools.NewRouteTool(navLimiter)),
```

### Tests in `route_tool_test.go` — All Call Sites

Every occurrence of `NewRouteTool` and `newRouteToolWithBaseURL` with a bool must be updated:

| Test | Current call | New call |
|------|-------------|---------|
| `TestRouteTool_Metadata` | `NewRouteTool(rate.NewLimiter(rate.Inf, 0), false)` | `NewRouteTool(rate.NewLimiter(rate.Inf, 0))` |
| `TestRouteTool_Call_Success` | `newRouteToolWithBaseURL(srv.URL, srv.Client(), true)` | `newRouteToolWithBaseURL(srv.URL, srv.Client())` |
| `TestRouteTool_Call_WithIntermediates` | `newRouteToolWithBaseURL(srv.URL, srv.Client(), false)` | `newRouteToolWithBaseURL(srv.URL, srv.Client())` |
| `TestRouteTool_Call_MissingStart` | `NewRouteTool(rate.NewLimiter(rate.Inf, 0), false)` | `NewRouteTool(rate.NewLimiter(rate.Inf, 0))` |
| `TestRouteTool_Call_MissingEnd` | `NewRouteTool(rate.NewLimiter(rate.Inf, 0), false)` | `NewRouteTool(rate.NewLimiter(rate.Inf, 0))` |
| `TestRouteTool_Call_APIError` | `newRouteToolWithBaseURL(srv.URL, srv.Client(), false)` | `newRouteToolWithBaseURL(srv.URL, srv.Client())` |
| `TestRouteTool_Call_Defaults` | `newRouteToolWithBaseURL(srv.URL, srv.Client(), false)` | `newRouteToolWithBaseURL(srv.URL, srv.Client())` |
| `TestRouteTool_Call_AvoidHighways` | `newRouteToolWithBaseURL(srv.URL, srv.Client(), false)` | `newRouteToolWithBaseURL(srv.URL, srv.Client())` |
| `TestRouteTool_Call_NoAvoidHighways` | `newRouteToolWithBaseURL(srv.URL, srv.Client(), false)` | `newRouteToolWithBaseURL(srv.URL, srv.Client())` |

In `TestRouteTool_Call_Success`, the mock server returns a `routeAPIResponse` with no `Geometry` field set. Update the response to include a `Geometry` field, and then add an assertion `if result.Geometry == nil { t.Fatal("expected geometry to be non-nil") }`.

The mock server response in `TestRouteTool_Call_Success` needs to include a geometry:
```go
resp := routeAPIResponse{
    ...
    Geometry: &GeoJSONGeometry{
        Type:        "LineString",
        Coordinates: [][]float64{{2.337325, 48.84932}, {2.367842, 48.85278}},
    },
    ...
}
```
Note: `GeoJSONGeometry` is defined in `route_tool.go` and is accessible from the test (same package).

### Tests to Delete

- `cmd/main_test.go`: delete `TestBuildApp_WithGeoJSONGeometry` entirely (it constructs `ServerEnv{GetGeoJSONGeometry: true}` which will no longer compile).
- `internal/config/config_test.go`: delete `TestLoadServerEnv_GetGeoJSONGeometry` entirely. Also remove the assertion `if env.GetGeoJSONGeometry { t.Error(...) }` from `TestLoadServerEnv_NoFileNoVars`.

### README Change

In the `route` tool's **Output** section, change:

> Returns: start, end, profile, optimization, total distance (m), total duration (s), bounding box, route portions with turn-by-turn steps (instruction, modifier, road name, road number, distance, duration), and optionally GeoJSON LineString geometry (when `GET_GEOJSON_GEOMETRY=true`).

To:

> Returns: start, end, profile, optimization, total distance (m), total duration (s), bounding box, GeoJSON LineString geometry, and route portions with turn-by-turn steps (instruction, modifier, road name, road number, distance, duration).

Also remove `GET_GEOJSON_GEOMETRY` from the environment variable table if it appears there.

### `.env.example` Change

Remove these lines entirely:
```
# Return GeoJSON geometry in route tool responses.
# Set to "true" to include the full route LineString geometry. Defaults to "false".
GET_GEOJSON_GEOMETRY=false
```

### Project Conventions to Follow

- **CGO_ENABLED=0** — no CGO in this module; this change doesn't affect that.
- **No new imports** — `strings` import in `config.go` may become unused after removing `strings.EqualFold(...)`. Remove it.
- **`os` import in `config.go`** — `os.Getenv("GET_GEOJSON_GEOMETRY")` is the only `os` call. Check if `os` is still used elsewhere in that file (it is not — `os` was only used for `Getenv`). Remove it if unused.
- **Test style**: table-driven tests are not required for this module; existing test style uses plain `t.Errorf`/`t.Fatalf` — keep that style.
- **No doc comments on changed functions** unless existing ones need updating for correctness.

### Unused Import Check After Edit

After removing `GET_GEOJSON_GEOMETRY` from `config.go`, verify:
- `strings` package: used only for `strings.EqualFold` on that line → **remove import**
- `os` package: used only for `os.Getenv("GET_GEOJSON_GEOMETRY")` → **remove import**

Run `go build ./...` in `mcp-ign-nav` to catch any remaining import or type errors.

### `routeAPIResponse` Type Note

The `Geometry` field on `routeAPIResponse` (defined in `route_api.go`) is of type `*GeoJSONGeometry`. The assignment `geometry := result.Geometry` is safe — `result.Geometry` is whatever the API returns (a pointer). The IGN API always returns a geometry when `getGeometry: "true"` is sent, so `result.Geometry` will be non-nil for a well-formed successful response.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.1] — acceptance criteria, FRs
- [Source: mcp-ign-nav/internal/tools/route_tool.go] — RouteTool struct, NewRouteTool, newRouteToolWithBaseURL, Call()
- [Source: mcp-ign-nav/internal/config/config.go] — ServerEnv, LoadServerEnv
- [Source: mcp-ign-nav/cmd/main.go] — buildApp, NewRouteTool call site
- [Source: mcp-ign-nav/internal/tools/route_tool_test.go] — all test call sites
- [Source: mcp-ign-nav/cmd/main_test.go] — TestBuildApp_WithGeoJSONGeometry
- [Source: mcp-ign-nav/internal/config/config_test.go] — GetGeoJSONGeometry tests
- [Source: mcp-ign-nav/.env.example] — GET_GEOJSON_GEOMETRY entry
- [Source: mcp-ign-nav/README.md] — route tool output description

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

### Completion Notes List

### File List
