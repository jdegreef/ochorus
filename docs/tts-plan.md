# Ochorus TTS — implementation plan & spike checklist

Goal: the best **free** listening experience for all Ochorus content (chapters,
sermons, long author bios), with a **user-selectable voice** stored in personal
settings and synced across devices.

Constraint: **no recurring cost.** Cloud TTS (Google/Polly/Azure/ElevenLabs/
OpenAI) is ruled out for the default path — free tiers become paid at library
scale. The free options that remain are the device's Web Speech voices and
**on-device neural TTS** (open models run in the browser via WASM/WebGPU, model
files fetched from a free CDN and cached client-side, so hosting/runtime cost
stays ~$0).

## Where we are today

`src/lib/listen.svelte.ts` is a solid **Web Speech API** engine: paragraph-per-
utterance (highlight-as-you-read, instant rate/voice changes, avoids Chrome's
long-utterance stall), rate + voice persisted to `localStorage`, voices filtered
to the content language. Wired into chapters (`books/[slug]/[order]`) and sermons
(`sermons/[slug]`) via `ListenBar.svelte`, but **not** author bios, and prefs are
device-local (not synced to the account).

Ceiling: device voices are inconsistent (great on iOS, robotic on desktop Chrome/
Linux) and can't be guaranteed.

## Architecture (linchpin)

Turn `listen.svelte.ts` into a **backend-agnostic orchestrator** with a pluggable
engine interface, so the reader UI never knows which engine is speaking.

```
src/lib/tts/engine.ts     // TtsBackend interface + TtsVoice type
src/lib/tts/webSpeech.ts  // current SpeechSynthesis logic, extracted
src/lib/tts/neural.ts     // Phase 1: Kokoro/Piper via ONNX (WebGPU→WASM)
src/lib/listen.svelte.ts  // orchestrator: paragraph queue, highlight, state,
                          //   media session — delegates to the active backend
```

`TtsBackend`: `id`, `label`, `isSupported()`, `listVoices(lang)`, `preview(voice)`,
`speak(text, {voice, rate, onBoundary, onEnd, onError})`, `pause/resume/cancel`.
`TtsVoice`: `{ id, label, lang, engine, quality: 'device' | 'neural', downloadMB? }`.
`listen.svelte.ts` keeps its public API (`start/toggle/stop/skip/setRate/setVoice`)
so the reader and `ListenBar` barely change.

---

## Spike (do FIRST — gates Phase 1)

Neural-in-browser is the only high-uncertainty piece. Validate in a throwaway
branch before the refactor.

Setup
- [ ] Minimal page: text → Kokoro-82M via `kokoro-js`/transformers.js, WebGPU with
      WASM fallback, model from the Hugging Face CDN.
- [ ] Quantizations: int8 (~80–90 MB) and fp16 (~160 MB); note Piper `en_US-*`
      (~25–60 MB) as a lighter alternative.

Device matrix: recent iPhone (Safari), mid-range Android (Chrome), desktop Chrome
(WebGPU), desktop Safari, Firefox.

Measure per device
- [ ] Model download size; cold load (CDN) vs warm load (cache)
- [ ] Time-to-first-audio (warm model)
- [ ] Real-time factor (RTF = synth time ÷ audio length)
- [ ] Peak memory; stability over a full chapter
- [ ] WebGPU available? RTF on the WASM fallback path
- [ ] Subjective quality (1–5) vs the device Web Speech voice, same passage
- [ ] Offline: model cached, works with network off

Go/no-go gates (all pass → neural default; some fail → opt-in or desktop-first)
- [ ] Quality clearly beats device voices (≈ +1 MOS)
- [ ] Warm time-to-first-audio < ~1.5 s on mid Android; WASM RTF < ~0.6
- [ ] Quantized model ≤ ~120 MB
- [ ] Runs on iOS Safari (WASM) without crashing; peak memory < ~500 MB mid Android
- [ ] Fallback: if Kokoro fails mobile gates → re-run with Piper; decide Piper-as-
      neural or neural-desktop-only + Web Speech mobile

Output: a one-page findings note with numbers + recommendation.

---

## Phase 0 — Web Speech polish (no new tech)

Cheap, high-value, near-zero risk. Ships independently of the spike.

Core (PR 1)
- [ ] Refactor to the engine interface (`tts/webSpeech.ts` + orchestrator). Chapters
      + sermons behave identically.
- [ ] Add Listen to author bios (`/authors/[slug]`): reuse `ListenBar` +
      `bio_html`→paragraphs extractor.
- [ ] Sync voice/rate/engine prefs to the account via the `readerPrefs` +
      `readingSync` local-cache→profile pattern; migrate the legacy
      `ochorus:listen` key.
- [ ] Voice picker upgrade in `/account` + the `ListenBar` popover: group by
      language, list device voices, preview button.

Polish (PR 2)
- [ ] Media Session API: title/author/cover metadata + play/pause/next/prev →
      lock-screen/background/car controls.
- [ ] Sentence-level highlighting via SpeechSynthesis `boundary` events; fall back
      to paragraph highlight where unsupported.
- [ ] Auto-advance to next chapter + resume position + optional sleep timer.

---

## Phase 1 — neural backend (the quality leap; gated by the spike)

- [ ] `tts/neural.ts`: Kokoro (or Piper per spike) via ONNX; WebGPU→WASM detection;
      model from HF CDN; cache in Cache Storage / OPFS; synth text→PCM→WebAudio,
      reusing the orchestrator's queue + highlight + media session.
- [ ] Lazy-load all neural code + model via dynamic `import()` — base bundle
      unchanged for users who don't enable HD.
- [ ] Opt-in download UX in `/account`: "Enable high-quality voices (~NN MB)" with
      progress, storage estimate, delete; offline-capable afterward.
- [ ] Engine registry + capability detection: neural when supported + downloaded,
      else Web Speech; picker lists neural ("HD") + device voices, grouped by lang.
- [ ] Graceful fallback: neural error/unsupported → Web Speech + notice.
- [ ] Default to neural only where spike gates passed; opt-in elsewhere.

## Phase 2 — breadth + polish

- [ ] Piper backend for smaller/multilingual voices (es; sw where available);
      offline voice manager (list/sizes/delete).
- [ ] Per-language voice defaults: content lang → best engine (en/es neural;
      **sw/lg → Web Speech**, since quality neural voices for Luganda don't exist).
- [ ] Optional pre-generated flagship audio for top-N books per language (open
      model, one-time, $0), served as static files; player prefers static audio
      when present for instant playback on any device.
- [ ] Privacy-safe telemetry (engine/voice used, fallback rate — no PII).

---

## Settings / sync data model

Extend the synced profile prefs:

```
ttsEngine: 'auto' | 'neural' | 'device'        // 'auto' = best available
ttsVoiceByLang: { en: string, es: string, … }  // voice id per content language
ttsRate: number
```

`localStorage` stays the instant-load cache; account sync follows the existing
`readerPrefs`/`readingSync` flow. Keep reading the legacy `ochorus:listen` key for
a migration window.

## Risks & mitigations

- iOS Safari WebGPU limited → WASM fallback (validate in spike).
- First-load size/bandwidth → opt-in + HF CDN + client cache.
- Mobile memory → smaller quantization / Piper / neural-desktop-first.
- Multilingual gaps (sw/lg) → Web Speech fallback + honest UI labeling.
- Autoplay/user-activation → synthesis starts on the existing user gesture.
- Voice licensing → verify each voice (Kokoro/Piper permissive; avoid non-
  commercial voices such as XTTS/Coqui).

## Sequencing

1. Spike (~1–2 days) → decision note.
2. Phase 0 (~a few days) — big UX jump on existing tech; ship independently.
3. Phase 1 (~1–2 weeks incl. device testing) — gated by the spike.
4. Phase 2 — incremental.

Each phase is an independent PR; Phase 0 alone materially improves the experience.
