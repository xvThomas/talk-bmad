# Story 4.1: Scaffold projet et CI

Status: ready-for-dev

## Story

As a developer,
I want a working project scaffold with Vite, React, TypeScript, Tailwind, TanStack Router, pnpm, and CI,
So that I have a solid foundation to build features on.

## Acceptance Criteria (BDD)

1. **Given** a fresh clone of the `talk-ui` repo **When** I run `pnpm install && pnpm build` **Then** the project compiles without errors.
2. **Given** the project is set up **When** I check `tsconfig.json` **Then** TypeScript strict mode is enabled (`"strict": true`).
3. **Given** the project is set up **When** I run `pnpm lint` **Then** ESLint flat config with `typescript-eslint/strict` + React plugin runs with 0 errors.
4. **Given** the project is set up **When** I run `pnpm format` **Then** Prettier formats all files consistently (no conflicts with ESLint).
5. **Given** the project is set up **When** I run `pnpm lint:fix` and `pnpm format:fix` **Then** auto-fixable issues are resolved.
6. **Given** the project is set up **When** I run `pnpm test` **Then** Vitest + Testing Library run with at least one passing placeholder test.
7. **Given** the project is set up **When** I inspect routing **Then** TanStack Router is configured with a single route (`/`).
8. **Given** the project is set up **When** I inspect Tailwind config **Then** dark mode is the only theme (no light/dark toggle).
9. **Given** a push or PR to `main` **When** GitHub Actions runs **Then** the CI workflow executes build + lint + test and reports pass/fail.
10. **Given** the project is set up **When** I read `README.md` **Then** it documents: prerequisites (Node 22+, pnpm), install, build, dev, lint, test commands.

## Tasks / Subtasks

- [ ] Task 1: Scaffold Vite React-TS project (AC: #1, #2)
  - [ ] Run `pnpm create vite@latest . --template react-ts`
  - [ ] Set `"strict": true` in tsconfig.json (should be default)
  - [ ] Set `"target": "ES2022"`, `"module": "ESNext"`, `"moduleResolution": "bundler"`
  - [ ] Add `.nvmrc` with `22`
  - [ ] Add `"engines": { "node": ">=22.12.0" }` in package.json
  - [ ] Verify `pnpm build` succeeds
- [ ] Task 2: Configure Tailwind CSS dark-only (AC: #8)
  - [ ] Install `tailwindcss @tailwindcss/vite`
  - [ ] Add Tailwind Vite plugin to `vite.config.ts`
  - [ ] Create `src/index.css` with `@import "tailwindcss"`
  - [ ] Set dark theme as default (use `darkMode: "class"` or CSS variables scoped to dark)
  - [ ] Add `class="dark"` on root `<html>` element
  - [ ] Set dark background + text color as base styles
- [ ] Task 3: Configure ESLint flat config (AC: #3, #5)
  - [ ] Install `eslint`, `typescript-eslint`, `eslint-plugin-react`, `eslint-plugin-react-hooks`, `eslint-config-prettier`
  - [ ] Create `eslint.config.ts` with:
    - `tseslint.configs.strict` (type-checked)
    - React + React Hooks plugins
    - `eslint-config-prettier` to disable formatting rules
    - Parser pointed at `tsconfig.json`
  - [ ] Add `"lint": "eslint ."` and `"lint:fix": "eslint . --fix"` scripts
  - [ ] Verify `pnpm lint` passes on scaffold code
- [ ] Task 4: Configure Prettier (AC: #4, #5)
  - [ ] Install `prettier`
  - [ ] Create `.prettierrc` (or `prettier.config.js`) with project conventions (semi, singleQuote, trailingComma, printWidth)
  - [ ] Create `.prettierignore` (dist, coverage, pnpm-lock.yaml)
  - [ ] Add `"format": "prettier --check ."` and `"format:fix": "prettier --write ."` scripts
  - [ ] Verify no ESLint/Prettier conflicts
- [ ] Task 5: Configure Vitest + Testing Library (AC: #6)
  - [ ] Install `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `jsdom`
  - [ ] Add Vitest config in `vite.config.ts` (or `vitest.config.ts`)
  - [ ] Configure jsdom environment, setup file for `@testing-library/jest-dom`
  - [ ] Create `src/__tests__/app.test.tsx` placeholder test
  - [ ] Add `"test": "vitest run"`, `"test:watch": "vitest"`, `"test:coverage": "vitest run --coverage"` scripts
  - [ ] Verify `pnpm test` passes
- [ ] Task 6: Configure TanStack Router (AC: #7)
  - [ ] Install `@tanstack/react-router`, `@tanstack/router-devtools` (dev)
  - [ ] Create file-based route structure: `src/routes/__root.tsx`, `src/routes/index.tsx`
  - [ ] Configure router in `src/main.tsx`
  - [ ] Single route `/` renders a placeholder App component
- [ ] Task 7: GitHub Actions CI (AC: #9)
  - [ ] Create `.github/workflows/ci.yml`
  - [ ] Trigger: push + PR to `main`
  - [ ] Steps: checkout → setup Node 22 → pnpm install → `pnpm build` → `pnpm lint` → `pnpm test`
  - [ ] Use `pnpm/action-setup` for pnpm
  - [ ] Cache pnpm store for speed
- [ ] Task 8: README.md (AC: #10)
  - [ ] Write prerequisites section (Node 22+, pnpm 9+)
  - [ ] Document: `pnpm install`, `pnpm dev`, `pnpm build`, `pnpm lint`, `pnpm test`
  - [ ] Include `VITE_AGENT_URL` env var documentation (for next story)
  - [ ] Keep it concise — getting started in < 1 minute

## Dev Notes

### Technical Decisions

- **Vite 8.1.0** (latest stable June 2026). Uses Rolldown for production builds. Scaffold with `react-ts` template.
- **Tailwind CSS v4** — uses the new `@tailwindcss/vite` plugin (not PostCSS). Import via `@import "tailwindcss"` in CSS.
- **ESLint 9+ flat config** — uses `eslint.config.ts` (not `.eslintrc`). `typescript-eslint` provides `tseslint.configs.strict` preset.
- **TanStack Router** — file-based routing with `@tanstack/react-router`. Single route for now but architecture supports future pages.
- **pnpm** — strict by default, no phantom dependencies. Use `pnpm-lock.yaml` in version control.
- **No TanStack Query yet** — will be added in Story 4.2 when CopilotKit integration needs it. Don't install prematurely.
- **No CopilotKit yet** — pure scaffold in this story. CopilotKit comes in Story 4.2.

### Project Structure

```
talk-ui/
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/
│   ├── routes/
│   │   ├── __root.tsx       # Root layout (dark bg, centered)
│   │   └── index.tsx        # Home route (placeholder)
│   ├── __tests__/
│   │   └── app.test.tsx     # Placeholder test
│   ├── index.css            # Tailwind imports + dark base styles
│   ├── main.tsx             # Router setup + React entry
│   └── vite-env.d.ts        # Vite types
├── index.html
├── vite.config.ts
├── tsconfig.json
├── eslint.config.ts
├── .prettierrc
├── .prettierignore
├── .nvmrc
├── .gitignore
├── .env.example             # VITE_AGENT_URL=http://localhost:8090
├── package.json
├── pnpm-lock.yaml
└── README.md
```

### NFR Compliance

- **NFR-1 (Zod):** Not applicable yet in this story (no incoming data). Zod installed in Story 4.2.
- **NFR-2 (strict TS):** Enforced via `tsconfig.json`.
- **NFR-3 (ESLint):** Flat config with `typescript-eslint/strict`.
- **NFR-4 (Prettier):** Configured and enforced in CI.
- **NFR-5 (scripts):** All four scripts present.
- **NFR-6 (Vitest):** Configured with placeholder test.
- **NFR-11 (WCAG):** Root `<html>` has `lang` attribute. Semantic HTML from the start.
- **NFR-15 (CI):** GitHub Actions workflow covers build + lint + test.

### Package Versions (Pin in package.json)

| Package                | Version | Notes                          |
| ---------------------- | ------- | ------------------------------ |
| vite                   | ^8.1.0  | Latest stable                  |
| react                  | ^19.x   | Current stable                 |
| react-dom              | ^19.x   | Match react                    |
| typescript             | ^5.8+   | Latest 5.x                     |
| tailwindcss            | ^4.x    | v4 with @tailwindcss/vite      |
| @tailwindcss/vite      | ^4.x    | Vite plugin (replaces PostCSS) |
| @tanstack/react-router | ^1.x    | File-based routing             |
| eslint                 | ^9.x    | Flat config only               |
| typescript-eslint      | ^8.x    | Strict preset                  |
| prettier               | ^3.x    | Latest                         |
| vitest                 | ^3.x    | Latest                         |
| @testing-library/react | ^16.x   | React 19 support               |

### CI Workflow Key Points

- Use `pnpm/action-setup@v4` for pnpm setup
- Use `actions/setup-node@v4` with `node-version-file: '.nvmrc'`
- Cache pnpm store: `actions/cache` with `~/.local/share/pnpm/store`
- Run steps sequentially: install → build → lint → test
- Fail fast on any step failure

### Common Pitfalls to Avoid

1. **Do NOT use PostCSS for Tailwind v4** — use `@tailwindcss/vite` plugin instead.
2. **Do NOT use `.eslintrc`** — ESLint 9 flat config only (`eslint.config.ts`).
3. **Do NOT install CopilotKit, Zod, or TanStack Query** — those come in Story 4.2.
4. **Do NOT create complex component structure** — minimal placeholder, real components come in 4.3.
5. **Do NOT add `tailwind.config.js`** — Tailwind v4 uses CSS-based config (`@theme` directive in CSS).
6. **Ensure `type: "module"` in package.json** — required for ESM + Vite 8.

### References

- [Source: PRD section 5 - Technical Constraints](prds/prd-talk-frontend-2026-06-28/prd.md#5)
- [Source: PRD section 4.2 - Code Quality NFRs](prds/prd-talk-frontend-2026-06-28/prd.md#4.2)
- [Source: PRD section 4.7 - CI/CD](prds/prd-talk-frontend-2026-06-28/prd.md#4.7)
- [Source: Vite docs - Getting Started](https://vite.dev/guide/)
- [Source: Tailwind v4 - Vite plugin](https://tailwindcss.com/docs/installation/vite)
- [Source: typescript-eslint - Flat config](https://typescript-eslint.io/getting-started/)
- [Source: TanStack Router - File-based routing](https://tanstack.com/router/latest/docs/framework/react/guide/file-based-routing)

## Change Log

- 2026-06-28: Story created — comprehensive scaffold context for dev agent.
