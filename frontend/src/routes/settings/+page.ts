// Settings is device- and account-specific (sign-in, theme, reader prefs, the
// device's TTS voices) — none of it is prerenderable, so render it client-side.
export const ssr = false;
export const prerender = false;
