# Story 4.2: Connexion CopilotKit + AG-UI backend

Status: review

## Story

As a developer,
I want the app to connect to the `talk serve` backend via CopilotKit's AG-UI integration,
So that messages can flow between frontend and backend.

## Acceptance Criteria (BDD)

1. **Given** the app is running with `VITE_AGENT_URL=http://localhost:8090` **When** the CopilotKit provider is initialized **Then** an `HttpAgent` is created pointing at the configured URL.
2. **Given** the CopilotKit provider is initialized **When** the app renders **Then** the agent is registered via `agents__unsafe_dev_only` with key `"default"` (required by CopilotKit for hooks without explicit `agentId`).
3. **Given** the app starts **When** `VITE_AGENT_URL` is read **Then** it is validated with Zod `z.url()` and an error is thrown at module load time if the value is not a valid URL.
4. **Given** the connection configuration **When** inspected in the code **Then** there are no `any` types — all configuration is fully typed.
5. **Given** all of the above **When** I run `pnpm build && pnpm lint && pnpm test` **Then** everything passes with no errors.

## Tasks / Subtasks

- [x] Task 1: Install CopilotKit + AG-UI + Zod dependencies (AC: #1, #2)
  - [x] `pnpm add @copilotkit/react-core @ag-ui/client zod`
  - [x] Verify no peer dependency conflicts
- [x] Task 2: Create agent configuration module with Zod validation (AC: #3, #4)
  - [x] Create `src/config/env.ts` — Zod schema for `VITE_AGENT_URL`, parse at import time
  - [x] Export typed `config` object with validated `agentUrl`
  - [x] Throw descriptive error if validation fails (developer-facing)
- [x] Task 3: Create CopilotKit agent setup (AC: #1, #4)
  - [x] Create `src/config/agent.ts` — instantiate `HttpAgent` using validated `config.agentUrl`
  - [x] Export a typed `agents` map: `Record<string, AbstractAgent>`
  - [x] Agent key must be `"talk"`
- [x] Task 4: Wrap app with CopilotKit provider (AC: #2)
  - [x] Update `src/routes/__root.tsx` to wrap `<Outlet />` with `<CopilotKit agents__unsafe_dev_only={agents}>`
  - [x] Import from `@copilotkit/react-core/v2`
  - [x] No `runtimeUrl` or `publicApiKey` needed (dev mode)
- [x] Task 5: Write tests (AC: #5)
  - [x] Test `src/config/env.ts` — valid URL passes, invalid URL throws
  - [x] Test `src/config/agent.ts` — returns HttpAgent with correct URL
  - [x] Test CopilotKit provider renders without crashing
  - [x] Verify mocking strategy for `import.meta.env`
- [x] Task 6: Update README (AC: #5)
  - [x] Document `VITE_AGENT_URL` as required env var
  - [x] Add "Running with backend" section
  - [x] Note that `talk serve` must be running for full functionality

### Review Findings

- [x] [Review][Patch] Normalize `VITE_AGENT_URL` before appending `/agent` to avoid double-slash URLs when env includes trailing `/` [src/config/agent.ts:4]
- [x] [Review][Defer] Duplicate error paths between `CopilotKit onError` and `copilotkit.subscribe({ onError })` can overwrite messages [src/routes/__root.tsx:30] — deferred, pre-existing

## Dev Notes

### Architecture Pattern (from PRD Section 8)

```
@ag-ui/client → HttpAgent({ url: VITE_AGENT_URL })
   ↓
<CopilotKit agents__unsafe_dev_only={{ "talk": agent }}>
   ↓
useAgent() / useCopilotChat() hooks (used in Story 4.3+)
```

### CopilotKit Integration Details (Verified June 2026)

**Package versions:**

- `@copilotkit/react-core` v1.61.2 — **import from `@copilotkit/react-core/v2`** (new API surface)
- `@ag-ui/client` v0.0.57 — provides `HttpAgent` and `AbstractAgent`
- `zod` — latest stable (for env validation)

**Key APIs:**

```typescript
// @ag-ui/client
import { HttpAgent } from "@ag-ui/client";
const agent = new HttpAgent({ url: "http://localhost:8090" });

// @copilotkit/react-core/v2
import { CopilotKit } from "@copilotkit/react-core/v2";
<CopilotKit agents__unsafe_dev_only={{ "talk": agent }}>
  {children}
</CopilotKit>

// useAgent hook (for future stories)
import { useAgent } from "@copilotkit/react-core/v2";
const { agent } = useAgent(); // or useAgent({ agentId: "talk" })
// agent.messages, agent.isRunning, agent.subscribe({...})
```

**Critical notes:**

- `agents__unsafe_dev_only` satisfies the provider's config check — no `runtimeUrl` or `publicApiKey` needed
- The prop accepts `Record<string, AbstractAgent>` — key is the `agentId` used by `useAgent()`
- `HttpAgent` handles POST + SSE natively — sends POST to URL, reads SSE response
- No CopilotKit runtime server needed (no `copilotkit/runtime` package)
- The `useAgent()` hook is used in Story 4.3, NOT in this story

### File Structure (Changes from Story 4.1)

```
src/
├── config/
│   ├── env.ts              # NEW — Zod env validation
│   └── agent.ts            # NEW — HttpAgent instantiation
├── routes/
│   ├── __root.tsx          # UPDATE — wrap with CopilotKit provider
│   └── index.tsx           # unchanged
├── __tests__/
│   ├── app.test.tsx        # unchanged
│   ├── env.test.ts         # NEW — env validation tests
│   └── agent.test.ts       # NEW — agent setup tests
├── App.tsx                 # unchanged
├── main.tsx                # unchanged
├── index.css               # unchanged
└── test-setup.ts           # unchanged
```

### Current State of Modified Files

**`src/routes/__root.tsx` (current):**

```tsx
import { createRootRoute, Outlet } from "@tanstack/react-router";

function RootLayout() {
  return <Outlet />;
}

export const Route = createRootRoute({
  component: RootLayout,
});
```

**After this story:**

```tsx
import { createRootRoute, Outlet } from "@tanstack/react-router";
import { CopilotKit } from "@copilotkit/react-core/v2";
import { agents } from "../config/agent";

function RootLayout() {
  return (
    <CopilotKit agents__unsafe_dev_only={agents}>
      <Outlet />
    </CopilotKit>
  );
}

export const Route = createRootRoute({
  component: RootLayout,
});
```

### Zod Env Validation Pattern

```typescript
// src/config/env.ts
import { z } from "zod";

const envSchema = z.object({
  VITE_AGENT_URL: z.string().url("VITE_AGENT_URL must be a valid URL"),
});

const parsed = envSchema.safeParse({
  VITE_AGENT_URL: import.meta.env.VITE_AGENT_URL ?? "http://localhost:8090",
});

if (!parsed.success) {
  throw new Error(
    `Environment validation failed:\n${parsed.error.issues.map((i) => `  - ${i.message}`).join("\n")}`,
  );
}

export const config = parsed.data;
```

### Testing Strategy

**Env validation tests (`src/__tests__/env.test.ts`):**

- Mock `import.meta.env` to test different VITE_AGENT_URL values
- Test: valid URL → config exported successfully
- Test: invalid URL (not a URL) → throws with descriptive message
- Test: missing URL → falls back to default `http://localhost:8090`

**Agent setup tests (`src/__tests__/agent.test.ts`):**

- Mock the config module
- Test: `agents` map has key `"talk"`
- Test: agent is an instance of `HttpAgent`
- Test: agent URL matches config

**Integration test (provider renders):**

- Render `RootLayout` wrapped in router context
- Assert no crash
- Note: actual AG-UI communication tested manually with backend running

**Vitest env mocking:** Use `vi.stubEnv()` or `vi.mock()` for `import.meta.env`. Vitest supports `import.meta.env` out of the box with `define` config.

### NFR Compliance

- **NFR-1 (Zod):** `VITE_AGENT_URL` validated at boundary with Zod schema. No `any` types.
- **NFR-2 (strict TS):** All configuration typed, `AbstractAgent` type from `@ag-ui/client`.
- **NFR-6 (Vitest):** Tests cover env validation and agent instantiation.
- **NFR-8 (CI):** Tests run automatically in CI (no new CI config needed).

### Common Pitfalls to Avoid

1. **Do NOT import from `@copilotkit/react-core`** — use `@copilotkit/react-core/v2` (new API).
2. **Do NOT install `@copilotkit/runtime`** — no server-side runtime needed (we use direct HttpAgent).
3. **Do NOT use `runtimeUrl` prop** — `agents__unsafe_dev_only` skips the runtime entirely.
4. **Do NOT add `useCopilotChat()` or `useAgent()` calls yet** — those are for Story 4.3.
5. **Do NOT create UI components** — this story is pure wiring/infrastructure.
6. **Do NOT hardcode the URL** — always go through Zod-validated config.
7. **Do NOT install `@copilotkit/react-ui` yet** — evaluate in Story 4.3 whether headless or prebuilt is used.
8. **The default fallback `http://localhost:8090` must match `.env.example`**.

### Previous Story Intelligence (4.1)

- TypeScript 6.0.3 (strict mode enabled in `tsconfig.app.json`)
- ESLint 10.6.0 with `typescript-eslint/strict` — catches any `any` types
- Vitest 4.1.9 with jsdom environment, `@testing-library/jest-dom` setup
- TanStack Router with file-based routes in `src/routes/`
- ESLint ignores `src/routeTree.gen.ts` and `src/routes/**` (react-refresh rule)
- All formatting via Prettier with semi + double quotes
- Tailwind v4 via `@tailwindcss/vite` plugin (CSS-based config)

### References

- [Source: PRD section 8 - Integration Pattern (Verified)](../../planning-artifacts/prds/prd-talk-frontend-2026-06-28/prd.md#8)
- [Source: PRD section 5 - Technical Constraints](../../planning-artifacts/prds/prd-talk-frontend-2026-06-28/prd.md#5)
- [Source: CopilotKit Self-managed agents](https://docs.copilotkit.ai/backend/self-managed-agents)
- [Source: CopilotKit Connect AG-UI agents](https://docs.copilotkit.ai/backend/ag-ui)
- [Source: @ag-ui/client npm](https://www.npmjs.com/package/@ag-ui/client)
- [Source: @copilotkit/react-core npm v1.61.2](https://www.npmjs.com/package/@copilotkit/react-core)

## Change Log

- 2026-06-28: Story created — CopilotKit AG-UI integration with full API details and testing strategy.
