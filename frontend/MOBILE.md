# The Ochorus app (iOS + Android)

The phone apps are the same SvelteKit reader as the website, wrapped by
[Capacitor](https://capacitorjs.com) 8. One codebase, two build targets:

| | Website (`npm run build`) | App (`npm run app:build`) |
|---|---|---|
| Output | `build/` — every public page prerendered for SEO, plus a `200.html` shell | `build-app/` — one `index.html` shell, nothing prerendered |
| Content | baked in at build + live API | live API (`https://api.ochorus.com`) |
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

`ci.yml`'s `native-app` job builds the app bundle on every frontend PR, and
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
4. **Lighter bundle:** the app bundles every cover and portrait from
   `static/` (~165 MB, most of it the PNG share-card twins under `covers/`).
   Images should load from ochorus.com instead.
5. **Store release:** TestFlight and Play internal testing uploads from CI
   (fastlane), privacy labels, store listings, screenshots.
