---
baseline_commit: 4489ad464f9a4e5ff6bf7f7ebd1ddcfdbbdaa311
---

# Story 4.5: Rendu markdown des messages assistant

Status: review

## Story

As an end user,
I want the assistant's messages to be rendered as rich markdown,
so that headings, lists, code blocks, and other formatting are readable and visually structured.

## Acceptance Criteria (BDD)

1. **Given** the assistant sends a response containing markdown syntax (headings, bold, italic, lists, links, inline code, fenced code blocks) **When** the message is displayed **Then** it is rendered as rich HTML — not raw markdown text **And** fenced code blocks include syntax highlighting (language-aware) **And** links are clickable and open in a new tab (`target="_blank"`, `rel="noopener noreferrer"`).
2. **Given** the assistant's response is streaming **When** partial markdown arrives (e.g., an incomplete code block) **Then** the rendering updates progressively without visual glitches **And** incomplete blocks are displayed as plain text until the closing fence arrives.
3. **Given** the message contains no markdown **When** the message is displayed **Then** it renders as plain text (no blank wrapper elements).
4. **Given** the assistant sends a response with GFM extensions (tables, strikethrough, task lists) **When** the message is displayed **Then** they are rendered correctly.
5. **Given** all of the above **When** I run `pnpm build && pnpm lint && pnpm test` **Then** everything passes.

## Tasks / Subtasks

- [x] Task 1: Install dependencies (AC: #1, #4)
  - [x] `pnpm add react-markdown remark-gfm rehype-highlight`
  - [x] `pnpm add -D @tailwindcss/typography`
  - [x] Add `highlight.js` CSS theme import for syntax highlighting (dark theme)
- [x] Task 2: Configure `@tailwindcss/typography` plugin (AC: #1)
  - [x] Add `@plugin "@tailwindcss/typography"` to `src/index.css`
  - [x] Add `prose-invert` overrides for dark theme compatibility with existing color scheme
- [x] Task 3: Create `MarkdownContent` component (AC: #1, #2, #3, #4)
  - [x] Create `src/components/MarkdownContent.tsx`
  - [x] Wrap `react-markdown` with `remarkGfm` + `rehypeHighlight` plugins
  - [x] Override `a` component to add `target="_blank"` and `rel="noopener noreferrer"`
  - [x] Apply `prose prose-invert prose-sm max-w-none` classes
  - [x] Handle empty/whitespace-only content (render nothing)
- [x] Task 4: Update `MessageBubble` to use `MarkdownContent` (AC: #1, #2, #3)
  - [x] Replace `<p className="whitespace-pre-wrap break-words">{content}</p>` with `<MarkdownContent content={content} />` for assistant messages
  - [x] Keep user messages as plain text (`whitespace-pre-wrap`)
  - [x] Update `MessageBubbleProps` if needed
- [x] Task 5: Write tests (AC: #5)
  - [x] Test `MarkdownContent`: renders headings, bold, italic, lists, code blocks, links, tables
  - [x] Test `MarkdownContent`: links have `target="_blank"` and `rel="noopener noreferrer"`
  - [x] Test `MarkdownContent`: empty content renders nothing
  - [x] Test `MessageBubble`: assistant messages use markdown rendering
  - [x] Test `MessageBubble`: user messages remain plain text
- [x] Task 6: Update README if needed (AC: #5) — no content change needed

### Review Findings

- No findings mapped to this story from the cross-story code review.

## Dev Notes

### Library Versions & Rationale

| Package | Version | Purpose |
|---------|---------|---------|
| `react-markdown` | `^10.1.0` | Safe markdown → React rendering (no `dangerouslySetInnerHTML`) |
| `remark-gfm` | latest | GFM extensions: tables, strikethrough, task lists, autolinks |
| `rehype-highlight` | `^7.0.2` | Syntax highlighting via `lowlight` (bundles 37 common languages) |
| `@tailwindcss/typography` | `^0.5.20` | `prose` classes for beautiful typographic defaults on rendered HTML |

**Why `react-markdown`?** Safe by default (no XSS), builds a virtual DOM so React only replaces changed nodes, plugin ecosystem via unified/remark/rehype. Actively maintained (10.1.0), 25M+ weekly downloads.

**Why NOT `dangerouslySetInnerHTML`?** Security risk (XSS), defeats React's virtual DOM diffing, no component override capability.

**Why `rehype-highlight` over `react-syntax-highlighter`?** `rehype-highlight` integrates directly as a rehype plugin — no custom component wiring needed. Smaller bundle. Uses `lowlight` (virtual `highlight.js`).

### Tailwind Typography v4 Integration

In Tailwind v4 with `@tailwindcss/vite`, the typography plugin is registered in CSS, NOT in a JavaScript config:

```css
/* src/index.css */
@import "tailwindcss";
@plugin "@tailwindcss/typography";
```

For dark mode, use `prose-invert` class. Since the app is dark-only (`bg-background: #0f172a`), always apply `prose-invert`.

### highlight.js CSS Theme

`rehype-highlight` generates `hljs-*` classes. A highlight.js CSS theme must be imported to style them. Use a dark theme that harmonizes with the app's slate-dark palette:

```typescript
// In MarkdownContent.tsx or index.css
import "highlight.js/styles/github-dark.min.css";
```

Alternative: import in `src/index.css` via `@import "highlight.js/styles/github-dark.min.css";` — either approach works with Vite.

### MarkdownContent Component Design

```typescript
// src/components/MarkdownContent.tsx
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import type { Components } from "react-markdown";

const components: Components = {
  a: ({ node, ...props }) => (
    <a {...props} target="_blank" rel="noopener noreferrer" />
  ),
};

interface MarkdownContentProps {
  content: string;
}

export function MarkdownContent({ content }: MarkdownContentProps) {
  if (!content.trim()) return null;

  return (
    <div className="prose prose-invert prose-sm max-w-none">
      <Markdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={components}
      >
        {content}
      </Markdown>
    </div>
  );
}
```

**Key design decisions:**
- `max-w-none` — overrides the prose plugin's default max-width so content fills the bubble
- `prose-sm` — keeps markdown typography proportional to chat bubble text size
- `prose-invert` — dark theme (always, since app is dark-only)
- `components` is defined outside the component to avoid re-creation on every render
- Empty content returns `null` — no empty wrapper divs

### Streaming Compatibility (AC #2)

`react-markdown` re-renders cleanly when `content` changes (React diffing). During streaming:
- The content string grows as `TEXT_MESSAGE_CONTENT` deltas arrive
- `react-markdown` re-parses the growing string each render
- Incomplete markdown (e.g., unclosed `` ``` ``) is rendered as text by the parser — no crash
- This is the standard behavior of `react-markdown` with streaming and requires no special handling

**No memoization needed** — `react-markdown` is synchronous and fast enough for streaming. Premature `useMemo` would break streaming updates.

### MessageBubble Update

The key change is conditional rendering: assistant messages use `MarkdownContent`, user messages stay as plain text.

```typescript
// Before (current):
<p className="whitespace-pre-wrap break-words">{content}</p>

// After (assistant only):
{isUser ? (
  <p className="whitespace-pre-wrap break-words">{content}</p>
) : (
  <MarkdownContent content={content} />
)}
```

### Reusability Note

The `MarkdownContent` component is designed to be reusable for:
- **Story 5.3** (Epic 5): Reasoning/thinking display — same markdown rendering with different wrapper styling
- **Story 6.1** (Epic 6): Tool call result display — render tool output as markdown when expanded

### Current State of Modified Files

**`src/components/MessageBubble.tsx` (current):**
```typescript
interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
}

export function MessageBubble({ role, content }: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[75%] rounded-lg px-4 py-2 ${
          isUser ? "bg-accent/20 text-foreground" : "bg-white/5 text-foreground"
        }`}
      >
        <p className="whitespace-pre-wrap break-words">{content}</p>
      </div>
    </div>
  );
}
```

**`src/index.css` (current):**
```css
@import "tailwindcss";

@theme {
  --color-background: #0f172a;
  --color-foreground: #e2e8f0;
  --color-muted: #64748b;
  --color-accent: #38bdf8;
}

html {
  @apply bg-background text-foreground antialiased;
}
```

### File Structure (Changes from Story 4.3)

```
src/
├── components/
│   ├── ChatView.tsx           # unchanged
│   ├── ChatInput.tsx          # unchanged
│   ├── MessageBubble.tsx      # UPDATE — use MarkdownContent for assistant role
│   ├── MarkdownContent.tsx    # NEW — reusable markdown renderer
│   └── ActivityIndicator.tsx  # unchanged
├── __tests__/
│   ├── markdown-content.test.tsx # NEW
│   ├── message-bubble.test.tsx   # UPDATE — add test for markdown rendering
│   ├── chat-input.test.tsx       # unchanged
│   ├── chat-view.test.tsx        # unchanged
│   ├── agent.test.ts             # unchanged
│   ├── app.test.tsx              # unchanged
│   └── env.test.ts               # unchanged
├── index.css                     # UPDATE — add typography plugin + hljs theme
└── ...                           # everything else unchanged
```

### Testing Strategy

**MarkdownContent tests** (`src/__tests__/markdown-content.test.tsx`):
- Renders heading: `# Hello` → `<h1>` element present
- Renders bold/italic: `**bold** *italic*` → `<strong>`, `<em>` elements
- Renders code block: `` ```js\nconsole.log(1)\n``` `` → `<pre><code>` with `hljs` classes
- Renders list: `- item 1\n- item 2` → `<li>` elements
- Renders link with security attrs: `[text](https://example.com)` → `<a target="_blank" rel="noopener noreferrer">`
- Renders table (GFM): `| a | b |\n|---|---|\n| 1 | 2 |` → `<table>` element
- Empty content returns null: `render(<MarkdownContent content="  " />)` → container is empty
- Plain text renders normally: `"Hello world"` → text visible, no empty wrappers

**MessageBubble test updates** (`src/__tests__/message-bubble.test.tsx`):
- Assistant message renders markdown (e.g., bold text renders `<strong>`)
- User message does NOT render markdown (e.g., `**bold**` appears literally)

**Note:** Tests will need to mock or configure `rehype-highlight` if it causes jsdom issues. If highlight.js fails in jsdom, mock `rehype-highlight` as a passthrough in tests:
```typescript
vi.mock("rehype-highlight", () => ({ default: () => {} }));
```

### Previous Story Intelligence

From Story 4.3:
- Components use Tailwind utility classes directly — no CSS modules, no styled-components
- Tests mock CopilotKit hooks via `vi.mock`
- Test files live in `src/__tests__/` (not colocated)
- `MessageBubble` is a simple presentational component — keep it that way
- Error handling via `useAgentError` context — not relevant here

### Potential Pitfalls

1. **`prose` color conflicts**: The `prose-invert` defaults may clash with the custom `--color-foreground` theme. If colors look wrong, override specific prose CSS variables in `index.css`.
2. **Code block overflow**: Long code lines in `<pre>` blocks may overflow the bubble. Add `prose-pre:overflow-x-auto` to handle horizontal scrolling.
3. **`@tailwindcss/typography` as devDependency**: It's a Tailwind plugin that runs at build time — install as `devDependency` (`pnpm add -D`), not a runtime dependency.
4. **ESM imports**: `react-markdown`, `remark-gfm`, `rehype-highlight` are ESM-only packages. This is fine with Vite + `"type": "module"` in `package.json`.
5. **TypeScript `node` prop**: The `components` override for `a` receives a `node` prop from react-markdown. Destructure it out to avoid passing it to the DOM element (`({ node, ...props })`).

### Project Structure Notes

- New component follows existing pattern: `src/components/MarkdownContent.tsx`
- New test follows existing pattern: `src/__tests__/markdown-content.test.tsx`
- No new routes, no new config files
- CSS changes are minimal (2 lines in `index.css`)

### References

- [Source: epics.md — Story 4.5 definition]
- [Source: PRD prd-talk-frontend-2026-06-28/prd.md — FR-25]
- [Source: react-markdown npm — v10.1.0 API, Components, plugins]
- [Source: @tailwindcss/typography npm — v0.5.20, prose-invert, Tailwind v4 @plugin syntax]
- [Source: rehype-highlight npm — v7.0.2, CSS theming, Options]
- [Source: Story 4.3 — component patterns, test structure, Tailwind theme variables]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (copilot)

### Debug Log References

### Completion Notes List

- Installed `react-markdown@10.1.0`, `remark-gfm@4.0.1`, `rehype-highlight@7.0.2` as runtime deps
- Installed `@tailwindcss/typography@0.5.20` and `highlight.js@11.11.1` as dev deps
- Configured `@tailwindcss/typography` via `@plugin` directive in index.css (Tailwind v4 pattern)
- Imported `highlight.js/styles/github-dark.min.css` for syntax highlighting theme
- Created `MarkdownContent` component: wraps `react-markdown` with `remarkGfm` + `rehypeHighlight`, applies `prose prose-invert prose-sm max-w-none prose-pre:overflow-x-auto`
- Links rendered with `target="_blank"` and `rel="noopener noreferrer"` via components override
- Updated `MessageBubble`: assistant messages render via `MarkdownContent`, user messages stay plain text
- Created 10 tests in `markdown-content.test.tsx` covering: headings, bold/italic, code blocks, lists, links (with security attrs), GFM tables, inline code, empty content, plain text, strikethrough
- Added 2 tests to `message-bubble.test.tsx`: assistant markdown rendering + user plain text
- Fixed pre-existing mock issue: added `subscribe` to `mockCopilotKit` in `chat-view.test.tsx` and `app.test.tsx`
- Fixed `message-bubble.test.tsx` "muted background" test to account for MarkdownContent DOM wrapper
- All 37 tests pass, build OK, lint OK
- `pnpm format` has pre-existing warnings on ALL files (not caused by this story)
- `rehype-highlight` mocked in tests (`vi.mock`) since `lowlight` doesn't run well in jsdom

### Change Log

- 2026-06-29: Story 4.5 implemented — markdown rendering for assistant messages

### File List

- src/components/MarkdownContent.tsx (NEW)
- src/components/MessageBubble.tsx (UPDATE)
- src/index.css (UPDATE)
- src/__tests__/markdown-content.test.tsx (NEW)
- src/__tests__/message-bubble.test.tsx (UPDATE)
- src/__tests__/chat-view.test.tsx (UPDATE — fix pre-existing mock)
- src/__tests__/app.test.tsx (UPDATE — fix pre-existing mock)
- package.json (UPDATE — new dependencies)
- pnpm-lock.yaml (UPDATE)
