# Design: Floating counselor chat launcher

Status: Approved (shipped in PR #11, doc backfilled 2026-05-03)
Last updated: 2026-05-03
Related PRD: [docs/prd/floating-counselor-chat.md](../prd/floating-counselor-chat.md)

## Components

```
RoadmapPage
├── ... tab content ...
└── FloatingCounselorChat
        ├── ChatLauncher       (bottom-right circular button)
        └── ChatPanel          (fixed overlay, conditionally rendered)
                └── ChatThread (lifted unchanged from /counselor)
```

`frontend/src/components/roadmap/FloatingCounselorChat.jsx` is the orchestrating component. The `ChatThread` itself is the existing chat UI from the pre-consolidation `/counselor` sidebar — moved, not rewritten.

## State

```js
const [isOpen, setIsOpen] = useState(() => {
  return localStorage.getItem('roadmap_counselor_chat_open') === '1';
});

useEffect(() => {
  localStorage.setItem('roadmap_counselor_chat_open', isOpen ? '1' : '0');
}, [isOpen]);
```

State key: `roadmap_counselor_chat_open` (string `'0'` or `'1'`). Survives reload. Cleared (treated as closed) if storage is unavailable.

## Layout

```
                                  ┌──────────────────────┐
                                  │ Counselor Chat   [✕] │  ← header with close button
                                  ├──────────────────────┤
                                  │                      │
                                  │ <ChatThread>         │
                                  │                      │
                                  │                      │  ← scrollable
                                  │                      │
                                  ├──────────────────────┤
                                  │ [textarea]    [Send] │
                                  └──────────────────────┘
                                       380 × 600 px

                                                 ┌─────┐
                                                 │ 💬 │  ← circular launcher when closed
                                                 └─────┘
```

Both pieces use `position: fixed`. The launcher is at `bottom: 24px; right: 24px`. The panel sits at `bottom: 24px; right: 24px; width: 380px; height: 600px` — same anchor, larger footprint.

## Tab-strip / sticky-header collisions

Because the panel is fixed, it can intercept clicks on the page underneath. Notably:
- The "Add task" pill near the top of the Plan tab can be visually behind the chat panel.
- The sticky page nav can interact with click handling.

Mitigation: the panel uses `pointer-events: auto` on itself; the launcher button uses `pointer-events: auto` and `z-index` above the page. Inside the page, click handlers that need to fire even when the panel might cover them use `force: true` in tests (matching the production scenario where the user has closed the chat).

## Accessibility

- Launcher is `<button aria-label="Open counselor chat">`.
- Panel is `<div role="dialog" aria-label="Counselor chat">`.
- Esc closes the panel.
- Focus trap inside the panel when open (so Tab cycles within the chat textarea + send button).

## Animation

CSS `transform: translateY(…)` + `opacity` for open/close. Uses `framer-motion` (already a dep) for smoother springs. Animation duration: 200ms.

## Backend

No new backend. The chat thread continues to call the existing `/chat` endpoint on `counselor_agent` exactly as it did before consolidation.

## Testing strategy

- **Vitest**: launcher click toggles open state; localStorage round-trips correctly; close button closes; Esc closes.
- **Playwright**: the launcher is visible; clicking it opens a `dialog` element with the right `aria-label`. Open/close state survives a page reload (clear localStorage between assertions).

## Risks

- **z-index wars** with future overlays (modals, toasts). Mitigation: the chat panel is at `z-index: 40`; standard modals should sit above (e.g., `z-index: 50`) and toast hosts above that.
- **Scroll trap inside the panel** — verified that overflow scrolls within the panel without bubbling.
- **localStorage-disabled browsers**: state simply doesn't persist; the panel defaults to closed every load. Acceptable.

## Alternatives considered

- **Keep chat as a tab.** Rejected: chat is a cross-cutting tool, not one of the four main work surfaces. A tab equals it visually with the others, which is wrong.
- **Modal dialog.** Rejected: modals block the underlying page. Students often want to read a task or essay while asking the counselor about it.
- **Bottom-of-page inline section.** Rejected: scrolling competition with the page content; "where did the chat go?" confusion.
