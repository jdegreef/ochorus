# The Ochorus app (iOS + Android)

The phone apps are the same SvelteKit reader as the website, wrapped by
[Capacitor](https://capacitorjs.com) 8. One codebase, two build targets:

| | Website (`npm run build`) | App (`npm run app:build`) |
|---|---|---|
| Output | `build/` — every public page prerendered for SEO, plus a `200.html` shell | `build-app/` — one `index.html` shell, nothing prerendered |
| Content | baked in at build + live API | live API (`https://api.ochorus.com`) |
| Images | served by the site itself | loaded from `https://ochorus.com`, not bundled (see below) |
| Size | everything under `static/` | ~20 MB, capped at 24 MB (`bundle-budget.json` `appBundle`) |
| Offline | service worker + Cache API | not yet: no service worker in iOS app web views (see roadmap) |
| Sign-in | Supabase | off for now (see roadmap); the app reads signed-out |
| Needs the API to build | yes (prerender) | no |

The app bundle is copied into two native projects, which are committed:
`ios/` (Xcode, Swift Package Manager) and `android/` (Gradle). The app's id,
`com.ochorus.app`, is **permanent** once uploaded to either store.

## How the code tells them apart

- `IS_APP` from `$lib/platform` is `true` only in the app bundle. It is a
  build-time constant, so the website ships none of the app-only branches.
- `$lib/platform/` is the one place that talks to Capacitor. ESLint rejects a
  `@capacitor/*` import anywhere else, so new native features (share sheet,
  deep links, offline files, native sign-in) get a function there with a web
  and a native implementation, and the rest of the app calls that function.
- The app bundle keeps the website's paths (`/books/humility/`,
  `/es/books`), so a link to ochorus.com can open the same page in the app
  once Universal Links / App Links are set up.
- The API allows the app's origins (`capacitor://localhost` on iOS,
  `https://localhost` on Android) in `backend/config/settings.py`, whatever
  production's `CORS_ALLOWED_ORIGINS` says.

## How the app loads images

The app bundle holds the reader's shell and nothing it can fetch instead: JS,
CSS, the woff2 webfonts, icons, and the small marks, emblems and paper
textures the chrome paints before any network (a few hundred KB). Everything
heavy stays on the website:

- `app-assets.js` lists the `static/` folders the app does not bundle
  (`REMOTE_DIRS`: `covers/`, `portraits/`, `illustrations/`, `about/`, `og/`,
  `pdfs/`) and the few files under them it keeps anyway (`KEEP_LOCAL`:
  `covers/art/credits.json`, which is `fetch`ed — a cross-origin fetch would
  need CORS headers the static site does not send; an `<img>` needs none).
- `scripts/build-app.mjs` deletes those folders from `build-app/` (helpers in
  `scripts/app-bundle.mjs`), plus the website's service worker and the legacy
  `.woff` twin of every font that also ships a `.woff2` (every app web view
  takes woff2).
- `$lib/assetUrl` is the one helper that points a path under those folders at
  `PUBLIC_SITE_URL` (`app-env/.env`): `assetUrl` for a `src`, `assetSrcset`
  for a `srcset`, `assetHtml` for a chapter or sermon body's illustrations. On
  the website `IS_APP` is false and each returns its input. Use it wherever an
  `<img>`'s `src`/`srcset` is built — not inside the pure helpers (`coverArt`,
  `portraits`) that also feed scripts, share cards and the offline cache,
  which want the site path. `assetUrl.test.ts` fails the build on a
  data-driven `<img>` that skips it.
- The origin is read once, at build time, by `appAssetOrigin()`
  (`app-target.js`): vite.config.ts bakes it into the bundle
  (`APP_ASSET_ORIGIN` in `$lib/platform`) and svelte.config.js adds exactly
  that origin to the app's CSP `img-src`, so the two cannot disagree. An app
  build without a valid `PUBLIC_SITE_URL` fails. The website's `img-src` stays
  `self`.
- `bundle-budget.json`'s `appBundle` caps the whole `build-app/` folder, and
  the app build fails above it. A new heavy folder under `static/` belongs in
  `REMOTE_DIRS`, not in a bigger budget.

**Never rename or delete a public asset path that a shipped app might still
ask for.** An installed app keeps asking for the paths it was built with — the
season paintings (`heroArt.ts`), the home quote's paintings, the About photos,
the `-320`/`-640` cover and `-96`/`-224` portrait variant names — for as long
as people keep that version, which can be years. Add the new file and keep the
old one.

So covers and portraits need the network in the app (the web view's HTTP
cache keeps the ones already seen). Offline books on the phone's storage
(roadmap 2) should save a book's cover and illustrations with its text.

## One-time setup on the Mac

1. **Xcode** from the App Store (the current release), opened once to install
   its components. Then `xcode-select --install` for the command-line tools.
2. **Android Studio** (it bundles JDK 21, which Capacitor 8 needs). In its SDK
   Manager install the Android SDK Platform 36.
3. **Node 22** (`frontend/.nvmrc`), then `cd frontend && npm ci`.

The app's settings live in `app-env/.env` (committed, all public) and nowhere
else — the build never reads the website's `frontend/.env`. Put local
overrides in `app-env/.env.local` (git-ignored).

## Run it on your iPhone

```sh
cd frontend
npm run app:ios        # builds build-app/, syncs it into ios/, opens Xcode
```

In Xcode:

1. Select the **App** target → **Signing & Capabilities** → choose your
   **Team**. A free Apple ID works for running on your own phone (it re-signs
   every 7 days). TestFlight and the App Store need the paid Apple Developer
   Program.
2. Plug in the iPhone, trust the Mac, and turn on **Settings → Privacy &
   Security → Developer Mode** on the phone (it restarts).
3. Pick the iPhone as the run destination and press **Run** (⌘R). Or pick an
   iOS Simulator.

## Run it on Android

```sh
cd frontend
npm run app:android    # builds build-app/, syncs it into android/, opens Android Studio
```

Press **Run** with an emulator or a USB-debugging phone selected.

## Day to day

- After changing frontend code: `npm run app:build` (rebuilds and runs
  `cap sync`), then Run again from Xcode / Android Studio.
- `npm run app:build -- --no-sync` builds only `build-app/` (what CI does).
- To try the app against a local API, in the **iOS Simulator** only:
  `PUBLIC_API_BASE_URL=http://localhost:8000 npm run app:build` (a real
  environment variable beats `app-env/`). The API already allows the app's
  origins (`NATIVE_APP_ORIGINS`). A physical phone can't reach the Mac's
  `localhost`, and Android's `https://localhost` page refuses an `http://` API.
- Upgrading Capacitor: bump every `@capacitor/*` package to the same version
  together, then `npx cap sync`.
- App icon / splash: `node scripts/generate-icons.mjs`, then the
  `@capacitor/assets` command in that file's header.
- Version numbers: iOS `MARKETING_VERSION` / `CURRENT_PROJECT_VERSION` in Xcode;
  Android `versionName` / `versionCode` in `android/app/build.gradle`. Each
  store upload needs a higher build number than the last.

## CI

`ci.yml`'s frontend checks build the app bundle on every frontend PR (and fail
it over the `appBundle` size budget), and
the Android debug build when `android/`, `ios/`, `resources/`, the Capacitor
config or the npm lockfile change (and always on `main`). iOS builds need macOS
and happen on the Mac for now.

## What the app does not do yet (the roadmap)

1. **Native shell polish:** safe areas around the notch and home bar, status
   bar colour, Android's back button, outside links (and the website-only
   files: the RSS feed, sitemaps) in the system browser, the
   native share sheet, PDF/EPUB downloads through the system.
2. **Offline books on the phone's own storage.** The "Download for offline"
   option is hidden in the app (`offlineBooks.supported`) until then.
3. **Sign-in:** the website's flows return to `window.location.origin`, which
   in the app is not a web address. Needs Universal Links / App Links (with
   `/.well-known/apple-app-site-association` and `assetlinks.json` on
   ochorus.com), email one-time codes, native Google sign-in and Sign in with
   Apple. Until then `authEnabled` is off in the app (`$lib/supabase`), so it
   shows no sign-in UI and reads signed-out.
4. ~~**Lighter bundle**~~ — done (Oct 2026): `build-app/` went from 245 MB
   to ~20 MB. Covers, portraits and illustrations load from ochorus.com; see
   "How the app loads images".
5. **Store release:** TestFlight and Play internal testing uploads from CI
   (fastlane), privacy labels, store listings, screenshots.
