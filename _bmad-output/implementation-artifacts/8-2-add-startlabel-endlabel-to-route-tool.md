---
baseline_commit: 29476975da6bab568ce6a7d12e35df1b1b192236
---

# Story 8.2: Add `StartLabel`/`EndLabel` to route tool input and output

Status: done

## Story

As an LLM agent,
I want to pass the human-readable place names I already know into the `route` tool call,
so that the frontend can display a meaningful legend label without performing reverse geocoding.

## Acceptance Criteria

1. `RouteToolInput` has two new optional fields: `StartLabel string` (json tag `"startLabel,omitempty"`) and `EndLabel string` (json tag `"endLabel,omitempty"`).
2. Both fields have `description` struct tags instructing the LLM to populate them with the human-readable origin and destination names resolved during prior geocoding.
3. Both fields are optional — calls without them continue to work (existing tests pass unchanged).
4. `RouteToolOutput` has two new fields: `StartLabel string` (json tag `"startLabel,omitempty"`) and `EndLabel string` (json tag `"endLabel,omitempty"`).
5. `Call()` echoes input `StartLabel`/`EndLabel` verbatim to the output — no processing or validation.
6. If input fields are empty, output fields are also empty.
7. `DistanceTimeToolInput` and `DistanceTimeToolOutput` are **not** modified — labels are only meaningful when geometry is present.
8. A test asserts that non-empty input labels are echoed in the output.
9. A test asserts that empty input labels produce empty output labels.
10. All existing tests continue to pass — `go test ./...` in `mcp-ign-nav` passes with no failures.

## Tasks / Subtasks

- [ ] Add `StartLabel`/`EndLabel` fields to `RouteToolInput` (AC: 1, 2, 3)
  - [ ] Add `StartLabel string` with json tag `"startLabel,omitempty"` and a `description` tag
  - [ ] Add `EndLabel string` with json tag `"endLabel,omitempty"` and a `description` tag
- [ ] Add `StartLabel`/`EndLabel` fields to `RouteToolOutput` (AC: 4)
  - [ ] Add `StartLabel string` with json tag `"startLabel,omitempty"`
  - [ ] Add `EndLabel string` with json tag `"endLabel,omitempty"`
- [ ] Echo labels in `Call()` method (AC: 5, 6)
  - [ ] Set `StartLabel: input.StartLabel` in the returned `RouteToolOutput`
  - [ ] Set `EndLabel: input.EndLabel` in the returned `RouteToolOutput`
- [ ] Add test: labels echoed when provided (AC: 8)
  - [ ] `TestRouteTool_Call_WithLabels` — supply `StartLabel: "Paris"` and `EndLabel: "Lyon"`, assert both appear verbatim in output
- [ ] Add test: labels empty when omitted (AC: 9)
  - [ ] `TestRouteTool_Call_WithoutLabels` — call without labels, assert `StartLabel == ""` and `EndLabel == ""` in output
- [ ] Verify `DistanceTimeToolInput`/`DistanceTimeToolOutput` are untouched (AC: 7)
- [x] Run `go test ./...` in `mcp-ign-nav` — all green (AC: 10)

### Review Findings

✅ Clean review — 0 findings (5 dismissed as noise). All ACs satisfied.

## Dev Notes

### Summary of Change

Pure additive: two optional passthrough fields on input, echoed to output. No new logic, no new API calls, no behavioral change for existing callers. The IGN Navigation API is not involved — labels are a client-side passthrough for frontend display.

### Files Being Modified

| File | Action | What changes |
|------|--------|-------------|
| `mcp-ign-nav/internal/tools/route_tool.go` | UPDATE | Add `StartLabel`/`EndLabel` to `RouteToolInput` and `RouteToolOutput`; echo in `Call()` return |
| `mcp-ign-nav/internal/tools/route_tool_test.go` | UPDATE | Add `TestRouteTool_Call_WithLabels` and `TestRouteTool_Call_WithoutLabels` |

No files are created. No files are deleted. `DistanceTimeTool` and its tests are **not touched**.

### Current State of `route_tool.go`

The `RouteToolInput` struct currently has these fields:
```go
type RouteToolInput struct {
    Start         string   `json:"start" description:"..."`
    End           string   `json:"end" description:"..."`
    Resource      string   `json:"resource,omitempty" description:"..."`
    Profile       string   `json:"profile,omitempty" description:"..."`
    Optimization  string   `json:"optimization,omitempty" description:"..."`
    Intermediates []string `json:"intermediates,omitempty" description:"..."`
    AvoidHighways string   `json:"avoidHighways,omitempty" description:"..."`
}
```

Add after `AvoidHighways`:
```go
    StartLabel    string   `json:"startLabel,omitempty" description:"Human-readable name of the starting point (e.g. 'Paris'). Populate with the place name resolved during prior geocoding."`
    EndLabel      string   `json:"endLabel,omitempty" description:"Human-readable name of the destination (e.g. 'Lyon'). Populate with the place name resolved during prior geocoding."`
```

The `RouteToolOutput` struct currently has these fields:
```go
type RouteToolOutput struct {
    Start        string           `json:"start" description:"Snapped start point"`
    End          string           `json:"end" description:"Snapped end point"`
    Profile      string           `json:"profile" description:"Routing profile used"`
    Optimization string           `json:"optimization" description:"Optimization criterion used"`
    Distance     float64          `json:"distance" description:"Total route distance in meters"`
    Duration     float64          `json:"duration" description:"Total route duration in seconds"`
    Bbox         [4]float64       `json:"bbox" description:"Bounding box [minLon, minLat, maxLon, maxLat]"`
    Geometry     *GeoJSONGeometry `json:"geometry" description:"Route geometry as a GeoJSON LineString"`
    Portions     []RoutePortion   `json:"portions" description:"Route portions between waypoints"`
}
```

Add after `Portions`:
```go
    StartLabel   string           `json:"startLabel,omitempty" description:"Human-readable name of the starting point, echoed from input"`
    EndLabel     string           `json:"endLabel,omitempty" description:"Human-readable name of the destination, echoed from input"`
```

In `Call()`, the return statement currently looks like:
```go
return RouteToolOutput{
    Start:        result.Start,
    End:          result.End,
    Profile:      result.Profile,
    Optimization: result.Optimization,
    Distance:     result.Distance,
    Duration:     result.Duration,
    Bbox:         bbox,
    Geometry:     result.Geometry,
    Portions:     portions,
}, nil
```

Add two lines before the closing `}, nil`:
```go
    StartLabel:   input.StartLabel,
    EndLabel:     input.EndLabel,
```

### Test Pattern

Both new tests can reuse the existing mock HTTP server pattern from `TestRouteTool_Call_Defaults`. The mock returns a valid `routeAPIResponse` with geometry; the test asserts on label values in the output.

```go
func TestRouteTool_Call_WithLabels(t *testing.T) {
    // Setup mock server returning valid route response with geometry
    // Call with StartLabel: "Paris", EndLabel: "Lyon"
    // Assert result.StartLabel == "Paris" and result.EndLabel == "Lyon"
}

func TestRouteTool_Call_WithoutLabels(t *testing.T) {
    // Use existing TestRouteTool_Call_Defaults or TestRouteTool_Call_Success flow
    // (no labels in input)
    // Assert result.StartLabel == "" and result.EndLabel == ""
}
```

### What NOT to Change

- `DistanceTimeTool`, `DistanceTimeToolInput`, `DistanceTimeToolOutput` — labels are only meaningful when geometry is present.
- `GeocodingTool`, `ReverseGeocodingTool` — unrelated.
- `route_api.go` — no IGN API change; labels are a client-side passthrough, not sent to the API.
- `config.go` — no new environment variables.
- `cmd/main.go` — no wiring change; the `RouteTool` constructor signature is unchanged.
- `.env.example`, `README.md` — no documentation change (the tool description already auto-generates from struct tags via `mcpserver`).
