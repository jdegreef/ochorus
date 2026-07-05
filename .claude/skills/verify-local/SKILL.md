---
name: verify-local
description: Run and verify Ochorus locally — dev server vs production-build preview, browser verification via Chrome MCP, offline/PWA testing, and the automation gotchas (stale vite preview, hidden-tab user activation). Use before committing any user-visible change, when asked to verify/test/screenshot the app, or when testing service-worker, TTS, or offline behaviour. This is a living playbook — append new automation gotchas as we hit them.
---

# Verifying Ochorus locally

Two ways to serve the frontend — pick by what you're testing:

| Mode | Command | Use for |
|---|---|---|
| dev | `npm run dev -- --port 5180` | fast iteration, HMR |
| preview | `npm run build && npm run preview -- --port 4173` | anything involving the SERVICE WORKER, PWA install, prerender output, or "as-deployed" behaviour (SW is disabled in dev) |

Backend: `cd backend && DJANGO_DEBUG=true uv run python manage.py runserver 8000`
(seeded per the dev-setup skill; CORS must include the frontend port).

## THE stale-preview trap (bites every time)

`vite preview` snapshots the build directory AT STARTUP. Rebuilding does
NOT change what it serves. After every `npm run build`:

```bash
pkill -f "vite preview"; (cd frontend && nohup npm run preview -- --port 4173 --strictPort >/tmp/preview.log 2>&1 &)
# Confirm served == disk before trusting ANY browser observation:
curl -s http://localhost:4173/ | grep -o "entry/app\.[A-Za-z0-9_-]*\.js"
ls frontend/build/_app/immutable/entry/app.*.js   # hashes must match
```

If a change "isn't taking effect", check this FIRST.

## Browser verification (Chrome MCP)

The MCP tab is hidden/automated — three consequences:

1. **No user activation**: `speechSynthesis.speak()` returns `not-allowed`,
   autoplay is blocked. Verify TTS logic by stubbing the engine:
   `speechSynthesis.speak = (u)=>{ setTimeout(()=>u.onend?.(new Event('end')),400) }`
   then drive the UI — state machine, highlights and bars all run for real.
2. **Coordinate clicks are unreliable** (hidden tab, rAF throttled). Prefer
   `javascript_tool` with precise dispatch:
   `[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='X').click()`
   — and match by exact text/aria-label, NEVER `.find()` on a broad container
   (an outer div's first button may be the header search).
3. Programmatic `scrollTo()` does NOT emit a `scroll` event in the hidden
   tab — scroll-driven logic (anchor saving) looks broken. After scrollTo,
   `window.dispatchEvent(new Event('scroll'))` to exercise the handler.
4. To fill inputs use the native setter + input event:
   `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,'q'); el.dispatchEvent(new Event('input',{bubbles:true}))`

## Offline / PWA test procedure

1. Load the preview build, wait ~2s, confirm SW:
   `(await navigator.serviceWorker.getRegistrations()).length === 1` and
   `await caches.keys()` → one `ochorus-cache-<version>` with shell+chunks.
2. Open a chapter → its `/api/library/...` URL appears in the cache (SWR).
3. Kill BOTH servers (`pkill -f "vite preview"; pkill -f runserver`), reload
   the chapter URL → the full page and chapter text must render from cache.
4. Restart servers afterwards. To observe the app's own registration flow,
   first clean slate: unregister all SWs + delete all caches, then reload.
5. Update prompt: rebuild+restart preview while an old SW is registered →
   the "A new version is available — Refresh" toast appears on next load.

## Sign-off checklist before committing a user-visible change

- `npm run check` — 0 errors; backend `manage.py test` if backend touched.
- Feature exercised in the browser with evidence (snapshot/screenshot/JS probe).
- If reader-adjacent: chapter loads, prev/next works, position restores.
- If SW-adjacent: offline procedure above.
