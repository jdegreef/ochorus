/**
 * Emblems — a library of small multicolour SVG illustrations, one per topic,
 * reading plan and sermon, so every shelf item wears art of its own instead of
 * a shared line glyph. Each emblem is hand-drawn on a 48×48 canvas in a flat,
 * warm style (a shared palette below keeps them looking like one family), and
 * is themed to its subject: the prayer topic gets folded hands under morning
 * light, "The Ravens' Cry" gets Elijah's raven with bread, and so on.
 *
 * Kept on the client (not the API) because this is presentation, not content,
 * and the catalogues are small and stable. A slug that has no curated emblem
 * falls back to a stable hash-pick from a small generic pool, so new content
 * ships looking finished and a given slug always wears the same art.
 *
 * This module is the ONE home for catalogue visual identity: art, curated
 * slug→emblem maps and accent hues all live here, read through topicMeta /
 * planMeta / emblemForSermon.
 *
 * The art strings are static, author-controlled markup rendered by
 * Emblem.svelte — never user input.
 *
 * DELIBERATELY IMPORT-FREE, and that includes re-exports. Two build scripts
 * (`generate-sermon-og.mjs`, `generate-emblem-hues.mjs`) load this module
 * directly under Node's type stripping, and bare Node resolves neither the
 * `$lib` alias nor an extensionless `./emblemNames`, while naming the
 * extension instead fails `svelte-check` (`allowImportingTsExtensions`). A
 * convenience `export … from './emblemNames'` here therefore does not
 * inconvenience anyone — it stops both generators dead. `nodeLoadable.test.ts`
 * now fails instead of leaving that to be discovered by hand.
 *
 * So the catalogue has two doors, by necessity: this module for the ART, and
 * `./emblemNames` for WHICH emblem a slug wears. The few lines of colour
 * arithmetic below are duplicated from `coverArt.ts` for the same reason; the
 * scripts, being plain `.mjs`, can name the extension and import it properly.
 */

// ── Shared palette ──────────────────────────────────────────────────────────
// Mid-tone hues that hold up on the tinted badge chips in both themes.
//
// hex-ok-file: illustration ink. These are the colours OF the drawings (the
// raven, the reed, the key), the way a book cover has colours — not chrome that
// should restyle with the theme.
const G = '#d9a441'; // gold
const GD = '#a97a24'; // deep gold
const T = '#2f8f85'; // teal
const TD = '#1e6b63'; // deep teal
const R = '#d95f43'; // coral red
const RD = '#a83a25'; // deep red
const B = '#4a6fb5'; // blue
const BD = '#2d4a80'; // navy
const GR = '#5a9e4d'; // leaf green
const GRD = '#3d7434'; // deep green
const P = '#8a5fbf'; // purple
const PD = '#5f3f8a'; // deep purple
const RO = '#cf5c85'; // rose
const CR = '#f3e2c4'; // cream / parchment
const CRD = '#e0c69a'; // shaded cream
const BR = '#8a6440'; // brown
const BRD = '#5f4227'; // dark brown
const SK = '#a7c9e8'; // sky
const SL = '#6b7f8f'; // slate
const SLD = '#465866'; // dark slate
const W = '#fdfaf3'; // warm white

// ── The art ─────────────────────────────────────────────────────────────────
// Inner markup for a 48×48 viewBox. Composed of a few flat shapes each; every
// emblem uses at least three colours so it reads as an illustration, not an
// icon.
export const EMBLEM_ART = {
	// ── Topics ──
	'praying-hands': `
		<circle cx="24" cy="24" r="15" fill="${G}" fill-opacity=".22"/>
		<path d="M24 3.5v4.5M13.5 6.5l2.5 4M34.5 6.5l-2.5 4" stroke="${G}" stroke-width="2.4" stroke-linecap="round"/>
		<path d="M23.3 12c-4.6 5.7-6.9 12-6.9 18.9 0 3.5 1.5 6.2 3.9 7.5 1.5.8 3-.2 3-1.9V13.7c0-1.9-.8-2.9-2-1.7z" fill="${CR}"/>
		<path d="M24.7 12c4.6 5.7 6.9 12 6.9 18.9 0 3.5-1.5 6.2-3.9 7.5-1.5.8-3-.2-3-1.9V13.7c0-1.9.8-2.9 2-1.7z" fill="${CRD}"/>
		<path d="M17 37h14l2.4 6.5H14.6z" fill="${BD}"/>`,
	'dove-descending': `
		<circle cx="24" cy="18" r="14.5" fill="${SK}" fill-opacity=".3"/>
		<path d="M22.5 20.5c-1.6-6.6.8-11.6 6.6-14.2-1 3.9-.5 7.1 1.4 10z" fill="${CRD}"/>
		<ellipse cx="25" cy="22.5" rx="9" ry="5.4" fill="${W}" transform="rotate(-16 25 22.5)"/>
		<circle cx="33.6" cy="18.5" r="3.2" fill="${W}"/>
		<circle cx="34.5" cy="17.8" r=".7" fill="${SLD}"/>
		<path d="M36.7 17.8l3.6 1.2-3.4 1.4z" fill="${G}"/>
		<path d="M17.5 25L8.5 30l4-7.4z" fill="${CRD}"/>
		<path d="M15 33.5c2.3 3 3.5 4.7 3.5 7a3.5 3.5 0 1 1-7 0c0-2.3 1.2-4 3.5-7z" fill="${R}"/>
		<path d="M24 35c2.3 3 3.5 4.7 3.5 7a3.5 3.5 0 1 1-7 0c0-2.3 1.2-4 3.5-7z" fill="${G}"/>
		<path d="M33 33.5c2.3 3 3.5 4.7 3.5 7a3.5 3.5 0 1 1-7 0c0-2.3 1.2-4 3.5-7z" fill="${R}"/>`,
	'mountain-dawn': `
		<circle cx="35" cy="12" r="5" fill="${G}"/>
		<path d="M35 3.5v2M28.6 6.1l1.4 1.4M41.4 6.1L40 7.5" stroke="${G}" stroke-width="2" stroke-linecap="round"/>
		<path d="M7 38L19.5 13.5 30 34z" fill="${TD}"/>
		<path d="M19.5 13.5l3.6 7.1-2.2-1.3-2.4 1.9-2.4-1.6z" fill="${W}"/>
		<path d="M17 38l12.5-19L42 38z" fill="${T}"/>
		<path d="M29.5 19l4 6.1-2.4-1.1-2.2 1.8-2.3-1.4z" fill="${W}"/>
		<rect x="5" y="37.4" width="38" height="4.2" rx="2.1" fill="${GR}"/>`,
	'overflowing-cup': `
		<path d="M13.5 21c-4.2 3-6.5 7.2-6.5 12.5" stroke="${B}" stroke-width="2.6" stroke-linecap="round" fill="none"/>
		<path d="M34.5 21c4.2 3 6.5 7.2 6.5 12.5" stroke="${B}" stroke-width="2.6" stroke-linecap="round" fill="none"/>
		<path d="M12.5 13h23c0 8.6-4.8 14-11.5 14s-11.5-5.4-11.5-14z" fill="${G}"/>
		<path d="M24 23.2s-4.6-2.7-4.6-6a2.5 2.5 0 0 1 4.6-1.3 2.5 2.5 0 0 1 4.6 1.3c0 3.3-4.6 6-4.6 6z" fill="${RO}"/>
		<circle cx="16.5" cy="16.5" r="1.5" fill="${W}" fill-opacity=".8"/>
		<rect x="22.4" y="26.5" width="3.2" height="7" fill="${GD}"/>
		<rect x="16.5" y="33.5" width="15" height="3.4" rx="1.7" fill="${GD}"/>
		<path d="M9 40.5h30" stroke="${CRD}" stroke-width="2.4" stroke-linecap="round"/>`,
	'torch-globe': `
		<circle cx="24" cy="30" r="12" fill="${B}"/>
		<path d="M15 24c3.4-1.6 6.4-1 8 1.4 1.4 2.2.2 4.6-2.4 5.4-2.8.9-5.4-.4-6.6-3.2z" fill="${GR}"/>
		<path d="M29 32c2.8-.8 5.2.2 6.2 2.6-1.4 2.8-3.8 4.8-6.8 5.6-1.4-2.8-1.2-6 .6-8.2z" fill="${GR}"/>
		<ellipse cx="24" cy="30" rx="12" ry="4.6" fill="none" stroke="${BD}" stroke-width="1.4"/>
		<path d="M24 3.5c1.9 3.7 5.2 5.3 5.2 9.4a5.2 5.2 0 0 1-10.4 0c0-2.2 1-3.7 2.3-4.9.2 1.6 1.1 2.6 2.2 2.6 1.4 0 2.1-1.4 1.8-3-.5-1.3-1.1-2.6-1.1-4.1z" fill="${R}"/>
		<path d="M24 9.5c.9 1.6 2.1 2.5 2.1 4.1a2.1 2.1 0 1 1-4.2 0c0-1.6 1.2-2.5 2.1-4.1z" fill="${G}"/>`,
	'compass-rose': `
		<circle cx="24" cy="24" r="17" fill="${W}" stroke="${BD}" stroke-width="2.6"/>
		<path d="M24 9v3M24 36v3M9 24h3M36 24h3" stroke="${BD}" stroke-width="2" stroke-linecap="round"/>
		<path d="M24 12.5l4.6 11.5h-9.2z" fill="${R}"/>
		<path d="M19.4 24h9.2L24 35.5z" fill="${SL}"/>
		<circle cx="24" cy="24" r="2.6" fill="${G}"/>
		<path d="M33.5 12l1 2.4 2.4 1-2.4 1-1 2.4-1-2.4-2.4-1 2.4-1z" fill="${G}"/>`,
	'herald-trumpet': `
		<rect x="3.5" y="16.6" width="4.6" height="5.8" rx="2.3" fill="${GD}"/>
		<path d="M7 19.5h17" stroke="${G}" stroke-width="3.2" stroke-linecap="round"/>
		<rect x="13.2" y="16" width="2.8" height="7" rx="1.4" fill="${GD}"/>
		<path d="M23 12.5c6.6 1.6 11.8 4 15.6 7-3.8 3-9 5.4-15.6 7 1.3-4.6 1.3-9.4 0-14z" fill="${G}"/>
		<ellipse cx="38.8" cy="19.5" rx="2.1" ry="7.2" fill="${GD}"/>
		<path d="M19.5 22.5v3M31 25v2.5" stroke="${RD}" stroke-width="1.6" stroke-linecap="round"/>
		<path d="M17.5 27.5h15.5v10l-7.75-3-7.75 3z" fill="${R}"/>
		<path d="M25.25 29.5v4.4M22.9 31.7h4.7" stroke="${W}" stroke-width="1.8" stroke-linecap="round"/>
		<path d="M43 11.5l2.4-2M44.5 19.5h3.2M43 27.5l2.4 2" stroke="${SL}" stroke-width="1.8" stroke-linecap="round"/>`,
	'laurel-tome': `
		<path d="M9 34c-3.4-3.4-4.8-8.4-3.8-14" stroke="${GRD}" stroke-width="2" stroke-linecap="round" fill="none"/>
		<ellipse cx="5.6" cy="24" rx="1.9" ry="3.4" fill="${GR}" transform="rotate(20 5.6 24)"/>
		<ellipse cx="6.8" cy="30" rx="1.9" ry="3.4" fill="${GR}" transform="rotate(45 6.8 30)"/>
		<ellipse cx="10" cy="34.6" rx="1.9" ry="3.4" fill="${GR}" transform="rotate(70 10 34.6)"/>
		<path d="M39 34c3.4-3.4 4.8-8.4 3.8-14" stroke="${GRD}" stroke-width="2" stroke-linecap="round" fill="none"/>
		<ellipse cx="42.4" cy="24" rx="1.9" ry="3.4" fill="${GR}" transform="rotate(-20 42.4 24)"/>
		<ellipse cx="41.2" cy="30" rx="1.9" ry="3.4" fill="${GR}" transform="rotate(-45 41.2 30)"/>
		<ellipse cx="38" cy="34.6" rx="1.9" ry="3.4" fill="${GR}" transform="rotate(-70 38 34.6)"/>
		<rect x="14" y="10" width="20" height="28" rx="2.4" fill="${BR}"/>
		<rect x="17" y="10" width="17" height="28" rx="2.4" fill="${BRD}"/>
		<rect x="18.5" y="12.5" width="14" height="23" rx="1.4" fill="${CR}"/>
		<path d="M25.5 18l1.7 4.2 4.3.3-3.3 2.9 1 4.3-3.7-2.3-3.7 2.3 1-4.3-3.3-2.9 4.3-.3z" fill="${G}"/>`,
	'narrow-gate': `
		<path d="M16.5 39L24 14l7.5 25z" fill="${G}" fill-opacity=".75"/>
		<rect x="9" y="13" width="6.5" height="26" rx="2" fill="${SL}"/>
		<rect x="32.5" y="13" width="6.5" height="26" rx="2" fill="${SL}"/>
		<path d="M9 15.5c1.5-5 6-8.5 15-8.5s13.5 3.5 15 8.5" stroke="${SLD}" stroke-width="4" stroke-linecap="round" fill="none"/>
		<ellipse cx="24" cy="42.5" rx="3.4" ry="1.6" fill="${CRD}"/>
		<ellipse cx="17" cy="45" rx="2.6" ry="1.3" fill="${CRD}"/>
		<ellipse cx="31" cy="45" rx="2.6" ry="1.3" fill="${CRD}"/>`,
	'open-word': `
		<path d="M8 20c-1.8 2.2-3 4.8-3.4 7.6M40 20c1.8 2.2 3 4.8 3.4 7.6" stroke="${G}" stroke-width="2.2" stroke-linecap="round" fill="none"/>
		<path d="M24 13c-2.8-2.4-7.6-3-11.5-2v11c3.9-1 8.7-.4 11.5 2z" fill="${W}"/>
		<path d="M24 13c2.8-2.4 7.6-3 11.5-2v11c-3.9-1-8.7-.4-11.5 2z" fill="${CRD}"/>
		<path d="M23 25.5l1-1.5 1 1.5v5l-1-1-1 1z" fill="${R}"/>
		<path d="M18.5 27h11l3.5 13h-18z" fill="${BR}"/>
		<path d="M24 27v13" stroke="${BRD}" stroke-width="1.6"/>
		<rect x="12" y="40" width="24" height="3.6" rx="1.8" fill="${BRD}"/>`,

	// ── Plans ──
	'rising-incense': `
		<path d="M19 5c-2.6 2.8 2.6 4.6 0 7.8" stroke="${T}" stroke-width="2.2" stroke-linecap="round" fill="none"/>
		<path d="M28 3c-2.6 2.8 2.6 4.6 0 7.8" stroke="${T}" stroke-width="2.2" stroke-linecap="round" fill="none"/>
		<path d="M23.5 9.5c-2.6 2.8 2.6 4.6 0 7.8" stroke="${SK}" stroke-width="2.2" stroke-linecap="round" fill="none"/>
		<path d="M16 21.5c0-4.6 3.4-7.5 8-7.5s8 2.9 8 7.5z" fill="${GD}"/>
		<circle cx="20.5" cy="18.5" r="1.1" fill="${BRD}"/><circle cx="27.5" cy="18.5" r="1.1" fill="${BRD}"/><circle cx="24" cy="16.5" r="1.1" fill="${BRD}"/>
		<path d="M13 22h22c0 7.4-4.6 12.5-11 12.5S13 29.4 13 22z" fill="${G}"/>
		<path d="M24 34.5v5" stroke="${GD}" stroke-width="2.2"/>
		<rect x="16.5" y="39.5" width="15" height="3.4" rx="1.7" fill="${GD}"/>`,
	'basin-towel': `
		<ellipse cx="22" cy="21.5" rx="14" ry="3.5" fill="${SK}"/>
		<path d="M8 21.5h28c0 8.5-5.9 14.2-14 14.2S8 30 8 21.5z" fill="${T}"/>
		<path d="M8 21.5h28c0 1.6-.3 3.1-.7 4.5H8.7A16.6 16.6 0 0 1 8 21.5z" fill="${TD}" fill-opacity=".45"/>
		<path d="M31.5 16c4.6-.9 7.8.7 9 4.4v13.4c0 2.2-1.5 3.7-3.5 3.7s-3.4-1.4-3.4-3.5V22.6c0-2.8-.7-4.9-2.1-6.6z" fill="${CR}"/>
		<path d="M36.6 23.5v10.5" stroke="${CRD}" stroke-width="1.8" stroke-linecap="round"/>
		<path d="M12 8.5c1.5 2 2.3 3.1 2.3 4.6a2.3 2.3 0 1 1-4.6 0c0-1.5.8-2.6 2.3-4.6z" fill="${SK}"/>
		<path d="M19 5.5c1.5 2 2.3 3.1 2.3 4.6a2.3 2.3 0 1 1-4.6 0c0-1.5.8-2.6 2.3-4.6z" fill="${B}"/>
		<path d="M13 41.5c2.9-2.4 6.3-3.6 10-3.6M35 41.5c-1.6-1.3-3.3-2.3-5.2-2.9" stroke="${SL}" stroke-width="2" stroke-linecap="round" fill="none"/>`,
	'door-ajar': `
		<path d="M13 42V16.5C13 9.6 17.9 5 24 5s11 4.6 11 11.5V42z" fill="${BD}"/>
		<path d="M16.5 42V17c0-4.9 3.2-8.3 7.5-8.3s7.5 3.4 7.5 8.3v25z" fill="${G}"/>
		<path d="M24.5 8.9c4.1.2 7 3.5 7 8.1v25h-7z" fill="${W}" fill-opacity=".35"/>
		<path d="M24.5 8.8l9 2.8V42h-9z" fill="${BR}"/>
		<path d="M24.5 8.8l9 2.8V42" fill="none" stroke="${BRD}" stroke-width="1.4"/>
		<circle cx="27" cy="27" r="1.5" fill="${G}"/>
		<path d="M16.5 42l8-2.5 8 2.5z" fill="${G}" fill-opacity=".7"/>
		<rect x="9" y="41.5" width="30" height="3" rx="1.5" fill="${SLD}"/>`,
	'true-vine': `
		<path d="M24 45V9" stroke="${BR}" stroke-width="3" stroke-linecap="round"/>
		<path d="M23.5 22c-3.9-.5-6.5-2.7-7.8-6.6M24.5 16c3.9-.5 6.5-2.7 7.8-6.6M24.5 31c3.2-.4 5.5-1.9 6.9-4.5" stroke="${BR}" stroke-width="2.3" stroke-linecap="round" fill="none"/>
		<ellipse cx="13.5" cy="13.5" rx="4.4" ry="2.7" fill="${GR}" transform="rotate(-38 13.5 13.5)"/>
		<ellipse cx="34.5" cy="7.5" rx="4.4" ry="2.7" fill="${GR}" transform="rotate(38 34.5 7.5)"/>
		<ellipse cx="33.5" cy="24.5" rx="4" ry="2.5" fill="${GRD}" transform="rotate(30 33.5 24.5)"/>
		<circle cx="12" cy="21" r="2.6" fill="${P}"/><circle cx="17.5" cy="21" r="2.6" fill="${PD}"/>
		<circle cx="10.8" cy="26" r="2.6" fill="${PD}"/><circle cx="16.2" cy="26" r="2.6" fill="${P}"/>
		<circle cx="13.5" cy="30.6" r="2.6" fill="${P}"/>
		<circle cx="13.5" cy="35" r="2.3" fill="${PD}"/>`,
	'shepherd-crook': `
		<path d="M32.5 43V13.5a7 7 0 0 0-13.5-2.6" stroke="${BR}" stroke-width="3.4" stroke-linecap="round" fill="none"/>
		<ellipse cx="17" cy="34.5" rx="8.6" ry="6" fill="${W}" stroke="#cdb98f" stroke-width="1.5"/>
		<circle cx="12.8" cy="33.5" r="1.8" fill="${W}"/><circle cx="16" cy="30" r="2" fill="${W}"/><circle cx="20.5" cy="30" r="1.9" fill="${W}"/>
		<circle cx="24.5" cy="32.5" r="3" fill="${SLD}"/>
		<path d="M26.5 30.2l2-1.8.2 2.4z" fill="${SLD}"/>
		<circle cx="25.4" cy="32" r=".6" fill="${W}"/>
		<path d="M13 40v3.4M21 40v3.4" stroke="${SLD}" stroke-width="2" stroke-linecap="round"/>
		<path d="M6 44c1.4-1.6 1.6-2.8 1-4.6 1.8.4 2.8 1.5 3.4 3.4M38 44.5c1.4-1.6 1.6-2.8 1-4.6 1.8.4 2.8 1.5 3.4 3.4" fill="none" stroke="${GR}" stroke-width="1.8" stroke-linecap="round"/>`,
	'refiners-crucible': `
		<path d="M12 13h24l-2.6 9.4c-1.2 4.3-4.8 7.1-9.4 7.1s-8.2-2.8-9.4-7.1z" fill="${GD}"/>
		<ellipse cx="24" cy="13" rx="12" ry="3.4" fill="${G}"/>
		<ellipse cx="24" cy="13" rx="8" ry="2.1" fill="${R}"/>
		<ellipse cx="24" cy="13" rx="4" ry="1.2" fill="${W}"/>
		<path d="M16 30.5c1.9 2.5 2.9 3.9 2.9 5.9a2.9 2.9 0 1 1-5.8 0c0-2 1-3.4 2.9-5.9z" fill="${R}"/>
		<path d="M32 30.5c1.9 2.5 2.9 3.9 2.9 5.9a2.9 2.9 0 1 1-5.8 0c0-2 1-3.4 2.9-5.9z" fill="${R}"/>
		<path d="M24 27c3 3.9 4.5 6 4.5 9a4.5 4.5 0 1 1-9 0c0-3 1.5-5.1 4.5-9z" fill="${RD}"/>
		<path d="M24 32.5c1.5 2 2.2 3.1 2.2 4.6a2.2 2.2 0 1 1-4.4 0c0-1.5.7-2.6 2.2-4.6z" fill="${G}"/>
		<path d="M24 3.5v3.2M17.5 5.5l1.6 2.8M30.5 5.5l-1.6 2.8" stroke="${G}" stroke-width="2" stroke-linecap="round"/>`,
	'pentecost-fire': `
		<path d="M13.5 13.5c2.9 3.7 4.4 5.9 4.4 8.8a4.4 4.4 0 1 1-8.8 0c0-2.9 1.5-5.1 4.4-8.8z" fill="${R}"/>
		<path d="M13.5 18.5c1.4 1.9 2.1 2.9 2.1 4.3a2.1 2.1 0 1 1-4.2 0c0-1.4.7-2.4 2.1-4.3z" fill="${G}"/>
		<path d="M24 6c3.6 4.7 5.4 7.3 5.4 10.9a5.4 5.4 0 1 1-10.8 0C18.6 13.3 20.4 10.7 24 6z" fill="${RD}"/>
		<path d="M24 12.5c1.7 2.3 2.6 3.6 2.6 5.3a2.6 2.6 0 1 1-5.2 0c0-1.7.9-3 2.6-5.3z" fill="${G}"/>
		<path d="M34.5 13.5c2.9 3.7 4.4 5.9 4.4 8.8a4.4 4.4 0 1 1-8.8 0c0-2.9 1.5-5.1 4.4-8.8z" fill="${R}"/>
		<path d="M34.5 18.5c1.4 1.9 2.1 2.9 2.1 4.3a2.1 2.1 0 1 1-4.2 0c0-1.4.7-2.4 2.1-4.3z" fill="${G}"/>
		<path d="M7 43c3.8-6.4 10-9.8 17-9.8s13.2 3.4 17 9.8" stroke="${SL}" stroke-width="2.8" stroke-linecap="round" fill="none"/>
		<circle cx="13" cy="38.5" r="1.4" fill="${SK}"/><circle cx="24" cy="36.5" r="1.4" fill="${SK}"/><circle cx="35" cy="38.5" r="1.4" fill="${SK}"/>`,
	'poured-out': `
		<g transform="rotate(-38 17 15)">
			<path d="M11 8.5h12v11c0 3.9-2.7 6.5-6 6.5s-6-2.6-6-6.5z" fill="#b0623f"/>
			<path d="M11 8.5h12v3.5H11z" fill="#8a4a2e"/>
			<ellipse cx="17" cy="8.5" rx="6" ry="2" fill="#c97a55"/>
		</g>
		<path d="M27.5 17.5c3.6 5.4 5.2 11.4 5 18.5" stroke="${G}" stroke-width="3" stroke-linecap="round" fill="none"/>
		<ellipse cx="31.5" cy="40" rx="9" ry="3.2" fill="${G}"/>
		<ellipse cx="29" cy="39.4" rx="3.4" ry="1.2" fill="${W}" fill-opacity=".7"/>
		<path d="M40 12l1 2.4 2.4 1-2.4 1-1 2.4-1-2.4-2.4-1 2.4-1z" fill="${G}"/>`,

	// ── Sermons ──
	'chi-rho': `
		<circle cx="24" cy="24" r="17.5" fill="${PD}"/>
		<circle cx="24" cy="24" r="17.5" fill="none" stroke="${G}" stroke-width="2"/>
		<circle cx="24" cy="24" r="13.5" fill="none" stroke="${G}" stroke-width=".9" stroke-opacity=".55"/>
		<path d="M16 32.5l16-17M32 32.5l-16-17" stroke="${W}" stroke-width="2.6" stroke-linecap="round"/>
		<path d="M24 36.5v-25" stroke="${G}" stroke-width="2.8" stroke-linecap="round"/>
		<path d="M24 11.5c4.6.2 6.6 2 6.6 4.6s-2 4.4-6.6 4.6" stroke="${G}" stroke-width="2.8" stroke-linecap="round" fill="none"/>`,
	'still-waters': `
		<circle cx="24" cy="19" r="14" fill="${SK}" fill-opacity=".32"/>
		<circle cx="31" cy="12.5" r="4" fill="${CR}"/>
		<path d="M14 15.5a3.4 3.4 0 1 1 3.4 3.4" stroke="${G}" stroke-width="1.9" stroke-linecap="round" fill="none"/>
		<path d="M7 30q4.3-2.6 8.5 0t8.5 0 8.5 0 8.5 0" stroke="${T}" stroke-width="2.6" stroke-linecap="round" fill="none"/>
		<path d="M9 36q4.3-2.6 8.5 0t8.5 0 8.5 0 8.5 0" stroke="${TD}" stroke-width="2.6" stroke-linecap="round" fill="none" opacity=".8"/>
		<path d="M12 42q4.3-2.6 8.5 0t8.5 0 8.5 0" stroke="${T}" stroke-width="2.6" stroke-linecap="round" fill="none" opacity=".55"/>`,
	'mustard-tree': `
		<circle cx="24" cy="43" r="2.2" fill="${GD}"/>
		<path d="M18.5 45.5h11" stroke="${BRD}" stroke-width="1.8" stroke-linecap="round"/>
		<path d="M24 41V26c-.4-3.8 1-6.8 3.2-9" stroke="${BR}" stroke-width="2.6" stroke-linecap="round" fill="none"/>
		<path d="M24 32c-2.4-.8-4-2.4-4.8-4.8" stroke="${BR}" stroke-width="2" stroke-linecap="round" fill="none"/>
		<circle cx="18" cy="18" r="6.4" fill="${GR}"/>
		<circle cx="28.5" cy="12.5" r="7.4" fill="${GRD}"/>
		<circle cx="32" cy="21.5" r="5.4" fill="${GR}"/>
		<circle cx="23" cy="20.5" r="4.6" fill="${GR}"/>
		<path d="M10 10c1-.9 2-.9 3 0-1 .9-2 .9-3 0zM38 6.5c1-.9 2-.9 3 0-1 .9-2 .9-3 0z" fill="${BD}"/>`,
	'joyful-harp': `
		<path d="M24 2.5v4M13 5.5l2 3.4M35 5.5l-2 3.4M6.5 13l3 2.2M41.5 13l-3 2.2" stroke="${G}" stroke-width="2.2" stroke-linecap="round"/>
		<path d="M15.5 14c-2.2 9.6-1 17.6 4 23.5h9c5-5.9 6.2-13.9 4-23.5" stroke="${G}" stroke-width="3" stroke-linecap="round" fill="none"/>
		<path d="M14.5 14h19" stroke="${GD}" stroke-width="3" stroke-linecap="round"/>
		<path d="M19.5 16.5v18M24 16.5v19.5M28.5 16.5v18" stroke="${RO}" stroke-width="1.7" stroke-linecap="round"/>
		<rect x="17" y="37.5" width="14" height="3.6" rx="1.8" fill="${GD}"/>`,
	'gospel-banner': `
		<path d="M14 5.5V43" stroke="${GD}" stroke-width="3" stroke-linecap="round"/>
		<circle cx="14" cy="5" r="2.2" fill="${G}"/>
		<path d="M16.5 9c6.4 3 12.6-1.2 19 1.8v13.4c-6.4-3-12.6 1.2-19-1.8z" fill="${R}"/>
		<path d="M26.5 12.2v7.6M23 15.4c2.4-.6 4.6-.6 7 .2" stroke="${W}" stroke-width="2" stroke-linecap="round" fill="none"/>
		<path d="M40 24c2-2 3.2-4.2 3.8-6.8M38.5 30c3.2-2.6 5.2-6 6.2-10" stroke="${SL}" stroke-width="1.8" stroke-linecap="round" fill="none"/>
		<path d="M9.5 43h9" stroke="${GD}" stroke-width="2.6" stroke-linecap="round"/>`,
	'olive-press': `
		<path d="M8 10c8-4.5 24-4.5 32 0" stroke="${GRD}" stroke-width="2.2" stroke-linecap="round" fill="none"/>
		<ellipse cx="12" cy="9" rx="3.6" ry="1.9" fill="${GR}" transform="rotate(-18 12 9)"/>
		<ellipse cx="24" cy="6.7" rx="3.6" ry="1.9" fill="${GR}"/>
		<ellipse cx="36" cy="9" rx="3.6" ry="1.9" fill="${GR}" transform="rotate(18 36 9)"/>
		<circle cx="18" cy="11.5" r="2.4" fill="${GRD}"/><circle cx="30" cy="11.5" r="2.4" fill="${SLD}"/>
		<path d="M24 17.5c1.7 2.1 2.6 3.4 2.6 5a2.6 2.6 0 1 1-5.2 0c0-1.6.9-2.9 2.6-5z" fill="${G}"/>
		<path d="M24 27c1.4 1.7 2.1 2.8 2.1 4.1a2.1 2.1 0 1 1-4.2 0c0-1.3.7-2.4 2.1-4.1z" fill="${GD}"/>
		<path d="M16 38.5c0-3.1 3.3-5 8-5s8 1.9 8 5v2.4c0 2-1.4 3.1-3.4 3.1H19.4c-2 0-3.4-1.1-3.4-3.1z" fill="${GD}"/>
		<path d="M17.5 34.6h13" stroke="${G}" stroke-width="2.2" stroke-linecap="round"/>`,
	'alpha-omega': `
		<circle cx="24" cy="24" r="17.5" fill="${CR}"/>
		<circle cx="24" cy="24" r="17.5" fill="none" stroke="${G}" stroke-width="2.4"/>
		<path d="M11.5 30.5L16 17.5l4.5 13M13.2 26.3h5.6" stroke="${BD}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
		<path d="M27.5 30.5h3.4l-1.3-3.2a5.6 5.6 0 1 1 8.8 0l-1.3 3.2h3.4" stroke="${RD}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
		<path d="M24 8.5l.8 1.9 1.9.8-1.9.8-.8 1.9-.8-1.9-1.9-.8 1.9-.8z" fill="${GD}"/>`,
	'cross-sunrise': `
		<circle cx="24" cy="21" r="13.5" fill="${R}" fill-opacity=".35"/>
		<circle cx="24" cy="21" r="9.5" fill="${G}"/>
		<path d="M24 4v3.4M11 8.5l2.3 2.3M37 8.5l-2.3 2.3M6.5 21h3.4M38.1 21h3.4" stroke="${G}" stroke-width="2.2" stroke-linecap="round"/>
		<rect x="22.3" y="10.5" width="3.4" height="22" rx="1" fill="${BRD}"/>
		<rect x="16" y="16.2" width="16" height="3.4" rx="1" fill="${BRD}"/>
		<path d="M3.5 42c6.2-7.7 13.6-11.5 20.5-11.5S38.3 34.3 44.5 42z" fill="${GR}"/>
		<path d="M14 37.8c3.2-2.4 6.6-3.8 10-4.3" stroke="${GRD}" stroke-width="1.8" stroke-linecap="round" fill="none"/>`,
	'pearl-of-price': `
		<path d="M10 27c0-8.8 6-14.5 14-14.5S38 18.2 38 27z" fill="${TD}" fill-opacity=".4"/>
		<path d="M10 27h28c0 8-6 13.5-14 13.5S10 35 10 27z" fill="${T}"/>
		<path d="M13 30.5c7.2 3.4 14.8 3.4 22 0M15.5 35c5.5 2.2 11.5 2.2 17 0" stroke="${TD}" stroke-width="1.7" stroke-linecap="round" fill="none"/>
		<circle cx="24" cy="25" r="7" fill="${W}"/>
		<path d="M20 22.7a5 5 0 0 1 3-2.4" stroke="#f2cfe0" stroke-width="2" stroke-linecap="round" fill="none"/>
		<path d="M35 11l1.1 2.7 2.7 1.1-2.7 1.1-1.1 2.7-1.1-2.7-2.7-1.1 2.7-1.1z" fill="${G}"/>`,
	'sheltering-wings': `
		<path d="M23 10.5C13.5 11 6.6 17.2 4 27.5c5.6-2.6 11.9-2.2 16.7 1z" fill="${G}"/>
		<path d="M8 24c3.4-4.7 7.7-7.7 12.8-9.1" stroke="${GD}" stroke-width="1.8" stroke-linecap="round" fill="none"/>
		<path d="M25 10.5c9.5.5 16.4 6.7 19 17-5.6-2.6-11.9-2.2-16.7 1z" fill="${GD}"/>
		<path d="M40 24c-3.4-4.7-7.7-7.7-12.8-9.1" stroke="${G}" stroke-width="1.8" stroke-linecap="round" fill="none"/>
		<path d="M24 24.4s-3.6-2.1-3.6-4.7a2 2 0 0 1 3.6-1 2 2 0 0 1 3.6 1c0 2.6-3.6 4.7-3.6 4.7z" fill="${RO}"/>
		<circle cx="14.5" cy="37.5" r="3.5" fill="${CR}"/><circle cx="24" cy="39.5" r="3.5" fill="${CRD}"/><circle cx="33.5" cy="37.5" r="3.5" fill="${CR}"/>
		<path d="M10.5 38.2l-2.2.7M24 43.7v1M37.5 38.2l2.2.7" stroke="${GD}" stroke-width="1.6" stroke-linecap="round"/>
		<circle cx="13.4" cy="36.7" r=".7" fill="${SLD}"/><circle cx="22.9" cy="38.7" r=".7" fill="${SLD}"/><circle cx="32.4" cy="36.7" r=".7" fill="${SLD}"/>`,
	'ark-rainbow': `
		<path d="M8 21a16 16 0 0 1 32 0" stroke="${R}" stroke-width="2.6" fill="none" stroke-linecap="round"/>
		<path d="M11.5 21a12.5 12.5 0 0 1 25 0" stroke="${G}" stroke-width="2.6" fill="none" stroke-linecap="round"/>
		<path d="M15 21a9 9 0 0 1 18 0" stroke="${B}" stroke-width="2.6" fill="none" stroke-linecap="round"/>
		<rect x="19" y="20" width="10" height="7" rx="1.2" fill="${BRD}"/>
		<rect x="22.4" y="22.3" width="3.2" height="2.6" fill="${G}"/>
		<path d="M11 26.5h26l-3.4 8.5H14.4z" fill="${BR}"/>
		<path d="M6 39q4.5-2.8 9 0t9 0 9 0 9 0" stroke="${B}" stroke-width="2.6" stroke-linecap="round" fill="none"/>
		<path d="M10 44q4.5-2.8 9 0t9 0 9 0" stroke="${SK}" stroke-width="2.4" stroke-linecap="round" fill="none"/>`,
	'jar-of-balm': `
		<rect x="15" y="18" width="18" height="21" rx="5" fill="${B}"/>
		<rect x="17.5" y="13.5" width="13" height="5.5" rx="2" fill="${BD}"/>
		<rect x="19" y="23.5" width="10" height="8.5" rx="1.5" fill="${CR}"/>
		<path d="M24 30.4s-2.9-1.7-2.9-3.8a1.6 1.6 0 0 1 2.9-.8 1.6 1.6 0 0 1 2.9.8c0 2.1-2.9 3.8-2.9 3.8z" fill="${RO}"/>
		<path d="M33 13c2.4-2.6 5.2-3.9 8.4-3.8-1.2 3-3.3 5.1-6.4 6.2" fill="${GR}"/>
		<path d="M36.5 11.5c-1.6 1.2-2.7 2.6-3.4 4.3" stroke="${GRD}" stroke-width="1.5" stroke-linecap="round" fill="none"/>
		<path d="M9 27c1.3 1.6 2 2.7 2 3.9a2 2 0 1 1-4 0c0-1.2.7-2.3 2-3.9z" fill="${SK}"/>
		<path d="M10.5 36c1 1.2 1.5 2 1.5 2.9a1.5 1.5 0 1 1-3 0c0-.9.5-1.7 1.5-2.9z" fill="${SK}"/>`,
	'feast-table': `
		<circle cx="24" cy="8" r="2.8" fill="${G}"/>
		<path d="M24 12.5v2.6M18.7 11.2l1.4 2.4M29.3 11.2l-1.4 2.4M15.5 7.5l2.5 1.4M32.5 7.5L30 8.9" stroke="${G}" stroke-width="1.9" stroke-linecap="round"/>
		<path d="M17.8 25c0-3.6 2.6-6 6.2-6s6.2 2.4 6.2 6z" fill="${RO}"/>
		<circle cx="24" cy="17.5" r="1.3" fill="${W}"/>
		<rect x="15.5" y="24.7" width="17" height="2" rx="1" fill="${W}"/>
		<path d="M11.5 20.5c1.7 1.8 2.5 3.2 2.5 4.7h-5c0-1.5.8-2.9 2.5-4.7zM36.5 20.5c1.7 1.8 2.5 3.2 2.5 4.7h-5c0-1.5.8-2.9 2.5-4.7z" fill="${GD}"/>
		<path d="M7 27h34l-2.2 5H9.2z" fill="${CR}"/>
		<path d="M9.2 32h29.6l-.6 1.6H9.8z" fill="${CRD}"/>
		<path d="M11.5 33.5l-1 10.5M36.5 33.5l1 10.5" stroke="${BRD}" stroke-width="2.4" stroke-linecap="round"/>`,
	'fourth-in-fire': `
		<path d="M10.5 44V25c0-8.3 5.7-14 13.5-14s13.5 5.7 13.5 14v19z" fill="${SLD}"/>
		<path d="M14.5 44V26c0-6.3 3.9-10.5 9.5-10.5s9.5 4.2 9.5 10.5v18z" fill="${RD}"/>
		<path d="M17 44c0-4.5 2.4-5.8 2.4-9.2 2.2 1.5 3.8 4.4 3.8 7.4 0 .6-.1 1.2-.3 1.8zM26 44c-.2-3.6 1.8-4.7 1.8-7.5 1.9 1.3 3.2 3.7 3.2 6.2 0 .5 0 .9-.2 1.3z" fill="${R}"/>
		<path d="M21.5 44c0-2.6 1.4-3.3 1.4-5.3 1.3.9 2.2 2.6 2.2 4.4l-.1.9z" fill="${G}"/>
		<circle cx="24" cy="23.5" r="2.7" fill="${W}"/>
		<path d="M24 26.8v7M24 28.5l-3.6 2.8M24 28.5l3.6 2.8" stroke="${W}" stroke-width="2.2" stroke-linecap="round"/>
		<circle cx="14" cy="14" r="1.2" fill="${G}"/><circle cx="34.5" cy="12.5" r="1.2" fill="${G}"/>`,
	'sealed-scroll': `
		<rect x="8.5" y="12" width="5.5" height="24" rx="2.7" fill="${CRD}"/>
		<rect x="34" y="12" width="5.5" height="24" rx="2.7" fill="${CRD}"/>
		<rect x="13" y="13.5" width="22" height="21" fill="${CR}"/>
		<path d="M17 19h14M17 23.5h14M17 28h8" stroke="${SL}" stroke-width="1.9" stroke-linecap="round"/>
		<path d="M28.5 33.5l-2 6 3.6-1.8 1.6 3.4 2-6.2z" fill="${R}"/>
		<path d="M33.5 33.5l2 6-3.6-1.8-1.6 3.4-2-6.2z" fill="${RD}"/>
		<circle cx="31" cy="32.5" r="4.6" fill="${R}"/>
		<circle cx="31" cy="32.5" r="4.6" fill="none" stroke="${RD}" stroke-width="1.2"/>
		<path d="M31 30.4v4.2M28.9 32.5h4.2" stroke="${G}" stroke-width="1.4" stroke-linecap="round"/>`,
	'grace-fountain': `
		<path d="M24 4.5c1.7 2.2 2.5 3.5 2.5 5.1a2.5 2.5 0 1 1-5 0c0-1.6.8-2.9 2.5-5.1z" fill="${SK}"/>
		<path d="M18 9.5c1-1.6 2.3-2.7 4-3.4M30 9.5c-1-1.6-2.3-2.7-4-3.4" stroke="${SK}" stroke-width="1.8" stroke-linecap="round" fill="none"/>
		<ellipse cx="24" cy="15.5" rx="8" ry="2.2" fill="${SL}"/>
		<path d="M16 15.5h16c0 3.8-3.2 6.3-8 6.3s-8-2.5-8-6.3z" fill="${SLD}"/>
		<rect x="22.4" y="21.5" width="3.2" height="8.5" fill="${SL}"/>
		<path d="M15 17.5c-1.7 4.5-4.4 7.7-8.2 9.8M33 17.5c1.7 4.5 4.4 7.7 8.2 9.8" stroke="${SK}" stroke-width="2.4" stroke-linecap="round" fill="none"/>
		<path d="M18.5 19.5c-1.2 3.2-3 5.6-5.5 7.3M29.5 19.5c1.2 3.2 3 5.6 5.5 7.3" stroke="${B}" stroke-width="2.2" stroke-linecap="round" fill="none"/>
		<ellipse cx="24" cy="37.5" rx="17" ry="5.4" fill="${B}"/>
		<ellipse cx="24" cy="36.4" rx="11.5" ry="3" fill="${SK}"/>
		<circle cx="10" cy="34" r="1" fill="${W}"/><circle cx="37.5" cy="34.5" r="1" fill="${W}"/>`,
	'heavens-ladder': `
		<circle cx="24" cy="9.5" r="5" fill="${CR}"/>
		<circle cx="18" cy="11.5" r="4" fill="${CRD}"/><circle cx="30" cy="11.5" r="4" fill="${CRD}"/>
		<path d="M8 15l.9 2.2 2.2.9-2.2.9-.9 2.2-.9-2.2-2.2-.9 2.2-.9zM40 20l.9 2.2 2.2.9-2.2.9-.9 2.2-.9-2.2-2.2-.9 2.2-.9z" fill="${G}"/>
		<path d="M16 45L21.5 13M32 45L26.5 13" stroke="${G}" stroke-width="2.8" stroke-linecap="round"/>
		<path d="M18.5 38.5h11.4M19.8 31h9M20.9 24h7M21.8 18h5.2" stroke="${GD}" stroke-width="2.4" stroke-linecap="round"/>
		<circle cx="10" cy="34" r="1.3" fill="${SK}"/><circle cx="38.5" cy="32" r="1.3" fill="${SK}"/>`,
	'kneeling-light': `
		<path d="M46 2L14.5 23.5 30 34z" fill="${G}" fill-opacity=".4"/>
		<path d="M46 2L20 25l8.6 5.8z" fill="${G}" fill-opacity=".55"/>
		<circle cx="15" cy="26" r="3.7" fill="${BD}"/>
		<path d="M17 31c-4.4 1.4-6.7 4.7-6.9 10l-.1 2.5h10v-4c3-.4 4.7-2.3 4.9-5.2z" fill="${BD}"/>
		<path d="M18 30l7.5-3.4M20.5 33l7-2" stroke="${BD}" stroke-width="2.4" stroke-linecap="round"/>
		<path d="M6 43.5h28" stroke="${SL}" stroke-width="2.4" stroke-linecap="round"/>`,
	'easy-yoke': `
		<circle cx="24" cy="17" r="8" fill="${G}"/>
		<path d="M24 4.5v3.2M13.5 8.8l2.3 2.3M34.5 8.8l-2.3 2.3M9.5 17h3.2M35.3 17h3.2" stroke="${G}" stroke-width="2.1" stroke-linecap="round"/>
		<path d="M7 27c5-6 12-6 17 0 5-6 12-6 17 0" stroke="${BR}" stroke-width="3.6" stroke-linecap="round" fill="none"/>
		<path d="M24 27v6" stroke="${BRD}" stroke-width="2.8" stroke-linecap="round"/>
		<circle cx="24" cy="35" r="2" fill="${BRD}"/>
		<path d="M5 41.5h38" stroke="${GR}" stroke-width="3" stroke-linecap="round"/>
		<path d="M12 41.5v-3.4M19 41.5v-4.4M29 41.5v-4.4M36 41.5v-3.4" stroke="${GRD}" stroke-width="1.9" stroke-linecap="round"/>`,
	'shield-of-faith': `
		<path d="M24 4.5l15.5 5.4v12.3c0 10.5-6.3 17.2-15.5 20.8-9.2-3.6-15.5-10.3-15.5-20.8V9.9z" fill="${B}"/>
		<path d="M24 4.5l15.5 5.4v12.3c0 10.5-6.3 17.2-15.5 20.8z" fill="${BD}"/>
		<rect x="22.2" y="12" width="3.6" height="17" rx="1.2" fill="${G}"/>
		<rect x="16.5" y="16.8" width="15" height="3.6" rx="1.2" fill="${G}"/>
		<path d="M6.5 14.5c1.9.4 3.2 1.5 3.9 3.3M5 22.5c1.4.3 2.4 1.1 2.9 2.4" stroke="${R}" stroke-width="1.9" stroke-linecap="round" fill="none"/>
		<circle cx="10.5" cy="10.5" r="1.5" fill="${R}"/>`,
	'bruised-reed': `
		<circle cx="36" cy="10" r="4.4" fill="${G}" fill-opacity=".55"/>
		<path d="M20.3 41c-.5-8.2-.4-16 .3-23.4" stroke="${GR}" stroke-width="2.6" stroke-linecap="round" fill="none"/>
		<path d="M20.6 17.6c.4-4 2.4-5.7 5.8-5.2" stroke="${GR}" stroke-width="2.6" stroke-linecap="round" fill="none"/>
		<ellipse cx="27.8" cy="16.5" rx="2.2" ry="4.6" fill="${BR}" transform="rotate(-14 27.8 16.5)"/>
		<path d="M20.5 33c-3.6-1-5.8-3.3-6.6-7" stroke="${GRD}" stroke-width="2.2" stroke-linecap="round" fill="none"/>
		<path d="M31.5 41V27" stroke="${GRD}" stroke-width="2.2" stroke-linecap="round"/>
		<ellipse cx="31.5" cy="23.5" rx="1.8" ry="3.8" fill="${BRD}"/>
		<path d="M8 41q4-2.4 8 0t8 0 8 0 8 0" stroke="${B}" stroke-width="2.4" stroke-linecap="round" fill="none"/>
		<path d="M12 45.5q4-2.4 8 0t8 0 8 0" stroke="${SK}" stroke-width="2.2" stroke-linecap="round" fill="none"/>`,
	'paradise-palms': `
		<path d="M17 43V23a7 7 0 0 1 14 0v20" stroke="${G}" stroke-width="3" fill="${W}" fill-opacity=".55"/>
		<path d="M24 19.5v4M24 27.5v4M24 35.5v4" stroke="${GD}" stroke-width="1.7" stroke-linecap="round"/>
		<path d="M9.5 43c-1-8 .3-14.6 4-20-5 1.4-8.3 4.4-10 9" fill="${GR}"/>
		<path d="M13.5 23c-4.3-.5-7.7.5-10.3 3.2" fill="none" stroke="${GRD}" stroke-width="1.8" stroke-linecap="round"/>
		<path d="M38.5 43c1-8-.3-14.6-4-20 5 1.4 8.3 4.4 10 9" fill="${GR}"/>
		<path d="M34.5 23c4.3-.5 7.7.5 10.3 3.2" fill="none" stroke="${GRD}" stroke-width="1.8" stroke-linecap="round"/>
		<path d="M24 6l.9 2.2 2.2.9-2.2.9-.9 2.2-.9-2.2-2.2-.9 2.2-.9z" fill="${G}"/>
		<path d="M6 44.5h36" stroke="${CRD}" stroke-width="2.6" stroke-linecap="round"/>`,
	'golden-key': `
		<circle cx="33.5" cy="13" r="9" fill="${BD}"/>
		<circle cx="33.5" cy="11" r="2.6" fill="${W}"/>
		<path d="M32 12.5h3l1 5h-5z" fill="${W}"/>
		<path d="M13.5 34.5L28 19" stroke="${G}" stroke-width="3.6" stroke-linecap="round"/>
		<circle cx="12" cy="36" r="6" fill="none" stroke="${G}" stroke-width="3.2"/>
		<path d="M22 26.5l3.6 3.4M25.8 22.5l3.6 3.4" stroke="${G}" stroke-width="3" stroke-linecap="round"/>
		<path d="M8 18l.9 2.2 2.2.9-2.2.9-.9 2.2-.9-2.2-2.2-.9 2.2-.9zM41 30l.8 1.9 1.9.8-1.9.8-.8 1.9-.8-1.9-1.9-.8 1.9-.8z" fill="${GD}"/>`,
	'rock-unmoved': `
		<path d="M35 5.5l1.1 2.7 2.7 1.1-2.7 1.1-1.1 2.7-1.1-2.7-2.7-1.1 2.7-1.1z" fill="${G}"/>
		<path d="M8.5 39l4.2-15.5L23 15l12.5 5.5L40 39z" fill="${SL}"/>
		<path d="M23 15l12.5 5.5L40 39H26.5L23.8 22z" fill="${SLD}"/>
		<path d="M12.7 23.5L23.8 22" stroke="${SLD}" stroke-width="1.5" stroke-linecap="round"/>
		<path d="M4 40q4.5-2.8 9 0t9 0 9 0 9 0" stroke="${B}" stroke-width="2.8" stroke-linecap="round" fill="none"/>
		<path d="M8 45q4.5-2.8 9 0t9 0 9 0" stroke="${SK}" stroke-width="2.4" stroke-linecap="round" fill="none"/>
		<circle cx="7" cy="34.5" r="1.3" fill="${SK}"/><circle cx="42" cy="33.5" r="1.3" fill="${SK}"/>`,
	'new-sprout': `
		<circle cx="36" cy="10" r="4.4" fill="${G}"/>
		<path d="M36 2.5v2.2M29.8 6.2l1.6 1.6M42.2 6.2l-1.6 1.6M28 10h2.2M41.8 10H44" stroke="${G}" stroke-width="1.9" stroke-linecap="round"/>
		<path d="M7 43c4.4-4.2 10.4-6.3 17-6.3S36.6 38.8 41 43z" fill="${BRD}"/>
		<path d="M24 37V24" stroke="${GR}" stroke-width="2.8" stroke-linecap="round"/>
		<path d="M24 28c-6.4.6-10.4-2.2-12-8.5 6.4-.6 10.4 2.2 12 8.5z" fill="${GR}"/>
		<path d="M24 25c6.4.6 10.4-2.2 12-8.5-6.4-.6-10.4 2.2-12 8.5z" fill="${GRD}"/>
		<path d="M11 16.5c1.2 1.5 1.8 2.6 1.8 3.7a1.9 1.9 0 1 1-3.7 0c0-1.1.7-2.2 1.9-3.7z" fill="${SK}"/>`,
	'ravens-bread': `
		<path d="M6 17a19 19 0 0 1 36 0" stroke="${T}" stroke-width="2" stroke-linecap="round" fill="none" opacity=".45"/>
		<path d="M21.5 23.5c-2.3-6.6.5-11.9 7.5-14.5-1.8 3.9-1.8 7.5 0 10.9z" fill="#2e3740"/>
		<ellipse cx="24" cy="26" rx="10" ry="4.9" fill="#3f4a55"/>
		<path d="M15.2 24.5L6 28.5l4.3-6.7z" fill="#2e3740"/>
		<circle cx="33.4" cy="23.4" r="3.4" fill="#3f4a55"/>
		<circle cx="34.6" cy="22.5" r=".8" fill="${W}"/>
		<path d="M36.5 24l4.3-.5-3.7 2.5z" fill="${GD}"/>
		<ellipse cx="40.2" cy="28.7" rx="3.2" ry="2.4" fill="${CR}"/>
		<path d="M38.8 28.2h2.8" stroke="${CRD}" stroke-width="1.1" stroke-linecap="round"/>
		<path d="M17 42c2.8-1.4 4.4-3.3 4.9-5.9M25.5 43.5c2-1 3.1-2.4 3.5-4.3" stroke="${SL}" stroke-width="1.8" stroke-linecap="round" fill="none"/>`,
	'rose-among-thorns': `
		<path d="M24 45V22" stroke="${GRD}" stroke-width="2.6" stroke-linecap="round"/>
		<path d="M24 32l-4.5-2.7.6-2.3 3.9 1.6zM24 38l4.5-2.7-.6-2.3-3.9 1.6z" fill="${GRD}"/>
		<path d="M24 28.5c-5.4.4-8.8-1.9-10.2-7 5.4-.4 8.8 1.9 10.2 7z" fill="${GR}"/>
		<circle cx="24" cy="13.5" r="8.5" fill="${RO}"/>
		<path d="M24 5c4.7 0 8.5 3.8 8.5 8.5S28.7 22 24 22z" fill="#b23a68"/>
		<circle cx="24" cy="13.5" r="4.2" fill="#8e2a52"/>
		<path d="M24 10.5a3 3 0 0 1 3 3" stroke="${W}" stroke-width="1.4" stroke-linecap="round" fill="none" opacity=".8"/>`,
	'pilgrim-road': `
		<circle cx="31" cy="11" r="7" fill="${G}" fill-opacity=".38"/>
		<rect x="29.9" y="5" width="2.2" height="11" rx=".9" fill="${GD}"/>
		<rect x="26.4" y="8.1" width="9.2" height="2.2" rx=".9" fill="${GD}"/>
		<path d="M1 44c3.2-7.4 9-11.8 17.5-13.2 3.7-.6 7-2 10-4.2V44z" fill="${GR}"/>
		<path d="M47 44c-2.4-6.4-6.6-10.4-12.6-12V44z" fill="${GRD}"/>
		<path d="M12 44c5.2-4.6 6.6-9.3 11.8-13.6 2.6-2.2 4.2-4.4 4.7-7.2l2.5.7c-.9 3.2-.7 6-.1 9.3 1 5 .1 8.3 2.1 10.8z" fill="${CR}"/>
		<path d="M21.5 41.5c2.6-3.4 3.9-6.9 5.6-10.3" stroke="${CRD}" stroke-width="1.5" stroke-linecap="round" stroke-dasharray="1.5 4" fill="none"/>`,
	'desert-spring': `
		<path d="M35 43c2-9-.2-16.4-5-22 6.2 1 10.4 4.6 12.6 10.4" fill="${GR}"/>
		<path d="M30.5 21.5c5-1 9 .2 12 3.6" fill="none" stroke="${GRD}" stroke-width="1.8" stroke-linecap="round"/>
		<path d="M33.8 26.5c1.6 5 1.8 10.4.7 16" stroke="${BR}" stroke-width="2.8" stroke-linecap="round" fill="none"/>
		<path d="M3 42c3.6-3.4 8-5 13-5" stroke="#d9b26a" stroke-width="4" stroke-linecap="round" fill="none"/>
		<ellipse cx="17" cy="41" rx="11" ry="3.8" fill="${B}"/>
		<ellipse cx="17" cy="40.4" rx="6.5" ry="2" fill="${SK}"/>
		<path d="M17 37.5c-2.6-3-3.4-6.2-2.4-9.7M17 37.5c2.6-3 3.4-6.2 2.4-9.7M17 37V27" stroke="${SK}" stroke-width="2" stroke-linecap="round" fill="none"/>
		<circle cx="12" cy="25" r="1.2" fill="${SK}"/><circle cx="22" cy="25" r="1.2" fill="${SK}"/><circle cx="17" cy="22.5" r="1.2" fill="${SK}"/>`,

	// ── Fallback pool (unmapped future slugs) ──
	'oil-lamp': `
		<path d="M33 13.5c.9 1.9 2 3 3.8 3.9-1.9.9-3 2-3.8 3.9-.9-1.9-2-3-3.8-3.9 1.8-.9 2.9-2 3.8-3.9z" fill="${G}"/>
		<path d="M11.5 30c1.7 2.1 2.5 3.4 2.5 5a2.5 2.5 0 1 1-5 0c0-1.6.8-2.9 2.5-5z" fill="${R}"/>
		<path d="M11.5 33.5c.8 1 1.2 1.7 1.2 2.5a1.2 1.2 0 1 1-2.4 0c0-.8.4-1.5 1.2-2.5z" fill="${G}"/>
		<path d="M10 38.5h20c-1 4-4.6 6.5-10 6.5-3.4 0-6.3-1-8.2-2.9z" fill="${GD}"/>
		<path d="M8 38.5h24" stroke="${BRD}" stroke-width="2" stroke-linecap="round"/>
		<path d="M30 41.5c3.6-.4 6.2-2 7.8-5" stroke="${GD}" stroke-width="2.4" stroke-linecap="round" fill="none"/>`,
	'wheat-sheaf': `
		<path d="M24 44V12M15.5 44c1.5-10.5 4-18.5 8.5-26M32.5 44c-1.5-10.5-4-18.5-8.5-26" stroke="${GD}" stroke-width="2.4" stroke-linecap="round" fill="none"/>
		<ellipse cx="24" cy="8.5" rx="3" ry="5" fill="${G}"/>
		<ellipse cx="14" cy="14" rx="2.8" ry="4.6" fill="${G}" transform="rotate(-24 14 14)"/>
		<ellipse cx="34" cy="14" rx="2.8" ry="4.6" fill="${G}" transform="rotate(24 34 14)"/>
		<ellipse cx="18.6" cy="10.5" rx="2.6" ry="4.2" fill="${GD}" transform="rotate(-12 18.6 10.5)"/>
		<ellipse cx="29.4" cy="10.5" rx="2.6" ry="4.2" fill="${GD}" transform="rotate(12 29.4 10.5)"/>
		<path d="M18 32c3.8 1.8 8.2 1.8 12 0l1.4 4.6c-4.6 2.2-10.2 2.2-14.8 0z" fill="${BR}"/>
		<path d="M9 44.5h30" stroke="${GR}" stroke-width="2.6" stroke-linecap="round"/>`,
	'morning-star': `
		<circle cx="24" cy="24" r="15" fill="none" stroke="${SK}" stroke-width="1.6" stroke-opacity=".7"/>
		<path d="M24 6l3.6 14.4L42 24l-14.4 3.6L24 42l-3.6-14.4L6 24l14.4-3.6z" fill="${G}"/>
		<path d="M24 17.5l1.7 4.8 4.8 1.7-4.8 1.7-1.7 4.8-1.7-4.8-4.8-1.7 4.8-1.7z" fill="${W}"/>
		<circle cx="9" cy="9.5" r="1.4" fill="${B}"/>
		<circle cx="39.5" cy="38" r="1.4" fill="${B}"/>
		<path d="M38 8l.8 1.9 1.9.8-1.9.8-.8 1.9-.8-1.9-1.9-.8 1.9-.8z" fill="${RO}"/>`,
	'watchmans-bell': `
		<path d="M24 5.5a2.6 2.6 0 0 1 2.6 2.6v1.4h-5.2V8.1A2.6 2.6 0 0 1 24 5.5z" fill="${GD}"/>
		<path d="M24 9c7.7 0 12 5.7 12 13.6v5.2l3.6 5.7H8.4L12 27.8v-5.2C12 14.7 16.3 9 24 9z" fill="${G}"/>
		<path d="M24 9c7.7 0 12 5.7 12 13.6v5.2l3.6 5.7H24z" fill="${GD}"/>
		<circle cx="24" cy="37.5" r="3.4" fill="${BRD}"/>
		<path d="M5.5 20c.7-3 2-5.4 4-7.4M42.5 20c-.7-3-2-5.4-4-7.4" stroke="${SL}" stroke-width="2" stroke-linecap="round" fill="none"/>
		<path d="M3 27.5c.3-1.7.8-3.2 1.6-4.6M45 27.5c-.3-1.7-.8-3.2-1.6-4.6" stroke="${SK}" stroke-width="2" stroke-linecap="round" fill="none"/>`,
	// ── topic emblems (batch 1) ──────────────────────────────────────────────
	'dawn-over-hills': `
		<circle cx="24" cy="17" r="6.5" fill="${G}"/>
		<path d="M24 5v3.5M12.5 9.5l2 2M35.5 9.5l-2 2M6.5 19h3.5M38 19h3.5" stroke="${G}" stroke-width="1.8" stroke-linecap="round"/>
		<path d="M2 41c9-11 16-7 22-4 5 2.5 12 1 22-1v11H2z" fill="${GRD}"/>
		<path d="M0 44c8-7 15-4 22-2 6 1.7 12 .5 26-2v8H0z" fill="${GR}"/>
		<path d="M24 41c-2.3-2.8-1.4-5.6.7-7.1-.3 1.8.5 2.7 1.4 3.3 1 .7 1.7 1.8 1.7 3A3.8 3.8 0 0 1 24 41z" fill="${R}"/>
		<path d="M24 40c-1.2-1.5-.7-3 .4-3.9-.2 1 .3 1.5.8 1.8.5.4.9 1 .9 1.6A2 2 0 0 1 24 40z" fill="${G}"/>`,
	'candle-and-book': `
		<rect x="6" y="31" width="20" height="11" rx="1.5" fill="${BRD}"/>
		<rect x="6" y="31" width="20" height="3.2" fill="${BR}"/>
		<rect x="8.5" y="34.5" width="15" height="6" fill="${CR}"/>
		<path d="M16 34.5v6" stroke="${CRD}" stroke-width="1"/>
		<rect x="30" y="20" width="6.5" height="19" rx="1" fill="${CR}"/>
		<rect x="30" y="20" width="2.4" height="19" fill="${CRD}"/>
		<rect x="28.5" y="38.5" width="9.5" height="3.5" rx="1.2" fill="${GD}"/>
		<path d="M33.2 20v-4" stroke="${BRD}" stroke-width="1.3"/>
		<path d="M33.2 8c1.7 2 2.4 3.3 2.4 5a2.4 2.4 0 0 1-4.8 0c0-1.7.7-3 2.4-5z" fill="${R}"/>
		<path d="M33.2 12c.8 1 1.1 1.7 1.1 2.6a1.1 1.1 0 0 1-2.2 0c0-.9.3-1.6 1.1-2.6z" fill="${G}"/>`,
	'mission-ship': `
		<path d="M37 8l1 3 3 1-3 1-1 3-1-3-3-1 3-1z" fill="${G}"/>
		<path d="M24 8v22" stroke="${BRD}" stroke-width="1.6"/>
		<path d="M24 10c6 1.5 9 4 10 7H24z" fill="${W}"/>
		<path d="M24 19c5 .8 8 2.2 9 4H24z" fill="${CRD}"/>
		<path d="M24 10c-6 1.5-9 4-10 7h10z" fill="${CR}"/>
		<path d="M9 30h30l-4 7c-1 1.6-2.6 2.2-4.5 2.2H17.5c-1.9 0-3.5-.6-4.5-2.2z" fill="${BR}"/>
		<path d="M9 30h30l-1.3 2.3H10.3z" fill="${BRD}"/>
		<path d="M5 40c3 0 3 1.8 6 1.8s3-1.8 6-1.8 3 1.8 6 1.8 3-1.8 6-1.8 3 1.8 6 1.8 3-1.8 6-1.8" stroke="${B}" stroke-width="1.8" fill="none" stroke-linecap="round"/>`,
	'paschal-lamb': `
		<circle cx="20" cy="19" r="8.5" fill="none" stroke="${G}" stroke-width="1.6"/>
		<ellipse cx="21" cy="30" rx="11" ry="7.5" fill="${W}"/>
		<circle cx="12" cy="26" r="2.2" fill="${CR}"/>
		<circle cx="16" cy="23.5" r="2.4" fill="${CR}"/>
		<circle cx="26" cy="24" r="2.4" fill="${CR}"/>
		<circle cx="30" cy="27" r="2.2" fill="${CR}"/>
		<ellipse cx="19" cy="19.5" rx="4.2" ry="5" fill="${CRD}"/>
		<circle cx="17.6" cy="18.8" r=".9" fill="${BRD}"/>
		<rect x="15" y="36" width="2.2" height="6" rx="1" fill="${CRD}"/>
		<rect x="25" y="36" width="2.2" height="6" rx="1" fill="${CRD}"/>
		<path d="M33 7v29" stroke="${BRD}" stroke-width="1.6"/>
		<path d="M33 9h8v6l-4-2-4 2z" fill="${R}"/>
		<path d="M37 10.2v3.2M35.5 11.5h3" stroke="${W}" stroke-width="1.2"/>`,
	'alabaster-jar': `
		<path d="M15 18h18l-2 16c-.4 3.2-3 5-7 5s-6.6-1.8-7-5z" fill="${CR}"/>
		<path d="M15 18h18l-.6 5H15.6z" fill="${CRD}"/>
		<rect x="20" y="11" width="8" height="7" rx="1" fill="${CRD}"/>
		<ellipse cx="24" cy="11" rx="5" ry="2.2" fill="${G}"/>
		<rect x="19" y="26" width="2.2" height="9" rx="1.1" fill="${W}"/>
		<path d="M17 29.5h14" stroke="${RO}" stroke-width="1.5"/>
		<path d="M24 40c-1.6 2-2.4 3.3-2.4 4.8a2.4 2.4 0 0 0 4.8 0c0-1.5-.8-2.8-2.4-4.8z" fill="${RO}"/>`,
	// ── topic emblems (batch 2) ──────────────────────────────────────────────
	'grafted-branch': `
		<path d="M8 40c6-4 10-10 12-18" stroke="${BR}" stroke-width="2.6" stroke-linecap="round" fill="none"/>
		<path d="M20 22c3-2 6-1 8 1-3 1-6 1-8-1z" fill="${GR}"/>
		<path d="M14 30c3-2 6-2 9 0-3 2-6 2-9 0z" fill="${GRD}"/>
		<path d="M30 18c2-3 5-4 8-3" stroke="${BR}" stroke-width="1.4" fill="none" stroke-linecap="round"/>
		<circle cx="30" cy="22" r="3.2" fill="${P}"/>
		<circle cx="35" cy="22" r="3.2" fill="${PD}"/>
		<circle cx="32.5" cy="27" r="3.2" fill="${P}"/>
		<circle cx="37" cy="27" r="3.2" fill="${PD}"/>
		<circle cx="34.5" cy="32" r="3.2" fill="${P}"/>`,
	'ichthys-fish': `
		<path d="M8 24c6-7 18-7 24 0-6 7-18 7-24 0z" fill="${T}"/>
		<path d="M31 24l9-5v10z" fill="${TD}"/>
		<circle cx="15" cy="22" r="1.7" fill="${W}"/>
		<path d="M8 24c6 3 18 3 24 0" stroke="${W}" stroke-width="1.1" fill="none" opacity=".45"/>
		<path d="M6 34c3 0 3 2 6 2s3-2 6-2 3 2 6 2 3-2 6-2 3 2 6 2" stroke="${B}" stroke-width="1.7" fill="none" stroke-linecap="round"/>`,
	'sun-and-moon': `
		<circle cx="15" cy="19" r="7" fill="${G}"/>
		<path d="M15 7v-2M5 11l-1.5-1.5M25 11l1.5-1.5M5 27l-1.5 1.5" stroke="${G}" stroke-width="1.6" stroke-linecap="round"/>
		<path d="M41 30a8.5 8.5 0 1 1-9-9.5 6.8 6.8 0 0 0 9 9.5z" fill="${SK}"/>
		<path d="M35 15l.9 2.2 2.2.9-2.2.9-.9 2.2-.9-2.2-2.2-.9 2.2-.9z" fill="${CR}"/>
		<path d="M4 41h40" stroke="${BR}" stroke-width="2" stroke-linecap="round"/>`,
	'waymark': `
		<path d="M22.5 12h3v30h-3z" fill="${BRD}"/>
		<path d="M25 15h13l4 4-4 4H25z" fill="${B}"/>
		<path d="M23 25H12l-4 4 4 4h11z" fill="${GR}"/>
		<path d="M14 44l7-9h6l7 9z" fill="${CRD}"/>
		<path d="M23.5 44l.5-9h0l.5 9z" fill="${W}" opacity=".55"/>`,
	'sheltered-lamp': `
		<path d="M12 40h24v3.4H12z" fill="${BRD}"/>
		<path d="M14 40c0-11 5-18 10-18s10 7 10 18" fill="none" stroke="${SK}" stroke-width="2"/>
		<ellipse cx="24" cy="36" rx="5.4" ry="2.5" fill="${GD}"/>
		<path d="M24 36c-2-2.6-1.2-5.1.6-6.5-.3 1.6.5 2.4 1.3 3 .9.6 1.5 1.6 1.5 2.7A3.4 3.4 0 0 1 24 36z" fill="${R}"/>
		<path d="M24 35c-1-1.3-.6-2.6.3-3.4-.1 1 .3 1.4.7 1.6.4.3.7.8.7 1.4A1.7 1.7 0 0 1 24 35z" fill="${G}"/>`,
	'field-sunrise': `
		<path d="M0 33h48v2H0z" fill="${R}" opacity=".45"/>
		<circle cx="24" cy="26" r="9" fill="${G}"/>
		<path d="M24 9v6M10 13l3 5M38 13l-3 5M4 23l6 2M44 23l-6 2" stroke="${G}" stroke-width="1.8" stroke-linecap="round"/>
		<path d="M0 34c8-2 16-2 24 0s16 2 24 0v10H0z" fill="${GRD}"/>
		<path d="M4 39h40M4 42.5h40" stroke="${GR}" stroke-width="1.4"/>`,
	'loaf-and-cup': `
		<ellipse cx="15" cy="30" rx="10" ry="6" fill="${BR}"/>
		<path d="M6 29c3-2 15-2 18 0" stroke="${BRD}" stroke-width="1.2" fill="none"/>
		<path d="M11 26l1.5 8M15 25v9M19 26l-1.5 8" stroke="${CRD}" stroke-width="1" opacity=".7"/>
		<path d="M26 19h12l-1.5 8c-.4 2.3-2.2 3.7-4.5 3.7s-4.1-1.4-4.5-3.7z" fill="${R}"/>
		<path d="M26 19h12l-.4 2.2H26.4z" fill="${RD}"/>
		<rect x="31" y="30.5" width="2" height="6" fill="${GD}"/>
		<rect x="27.5" y="36.5" width="9" height="2.4" rx="1" fill="${GD}"/>`,
	'raised-lantern': `
		<path d="M20 11c0-2.2 8-2.2 8 0" stroke="${GD}" stroke-width="1.6" fill="none"/>
		<path d="M18 13h12l-1 3H19z" fill="${GD}"/>
		<rect x="18" y="16" width="12" height="16" rx="1" fill="${SLD}"/>
		<rect x="20.5" y="18.5" width="7" height="11" rx="1" fill="${G}" opacity=".4"/>
		<path d="M24 29c-1.6-2-1-4 .5-5.2-.2 1.3.4 1.9 1 2.3.7.5 1.1 1.2 1.1 2A2.6 2.6 0 0 1 24 29z" fill="${R}"/>
		<rect x="17" y="32" width="14" height="3" rx="1" fill="${GD}"/>
		<path d="M13 39l-3 4M35 39l3 4M24 40v4" stroke="${G}" stroke-width="1.6" stroke-linecap="round" opacity=".8"/>`,
	'warmed-heart': `
		<path d="M24 40C10 30 8 20 14 15c4-3.4 8-1.5 10 2 2-3.5 6-5.4 10-2 6 5 4 15-10 25z" fill="${R}"/>
		<path d="M24 40C10 30 8 20 14 15" stroke="${RD}" stroke-width="1.2" fill="none" opacity=".5"/>
		<path d="M24 33c-2.4-3-1.5-6 .7-7.6-.3 1.9.6 2.9 1.5 3.5 1 .7 1.8 1.9 1.8 3.2A4 4 0 0 1 24 33z" fill="${G}"/>
		<path d="M24 32c-1.2-1.6-.7-3.2.4-4.1-.2 1 .3 1.5.8 1.9.5.3.9 1 .9 1.7A2 2 0 0 1 24 32z" fill="${CR}"/>`,
	'cornerstone': `
		<rect x="8" y="13" width="14" height="7" rx="1" fill="${SL}"/>
		<rect x="24" y="13" width="16" height="7" rx="1" fill="${SL}"/>
		<rect x="8" y="22" width="18" height="7" rx="1" fill="${SL}"/>
		<rect x="13" y="31" width="23" height="11" rx="1" fill="${G}"/>
		<path d="M13 31h23v3H13z" fill="${GD}"/>
		<path d="M24.5 34v8" stroke="${GD}" stroke-width="1" opacity=".6"/>
		<path d="M18 38h4M20 36v3.5" stroke="${W}" stroke-width="1.1"/>`,
	'river-sunrise': `
		<circle cx="26" cy="18" r="7" fill="${G}"/>
		<path d="M26 6v-2M15 10l1.4 1.4M37 10l-1.4 1.4" stroke="${G}" stroke-width="1.6" stroke-linecap="round"/>
		<path d="M0 28h48v14H0z" fill="${B}"/>
		<path d="M0 28h48v3H0z" fill="${SK}"/>
		<rect x="23" y="28" width="6" height="13" fill="${G}" opacity=".5"/>
		<path d="M6 35h8M20 38h8M34 34h8" stroke="${SK}" stroke-width="1.2" opacity=".85"/>
		<path d="M8 28v-6" stroke="${BRD}" stroke-width="1.5"/>
		<path d="M8 22c3-2 5-2 7-1M8 22c-3-2-4-1-6-1M8 23c0-4 2-6 4-7M8 23c0-4-2-5-4-6" stroke="${GRD}" stroke-width="1.4" fill="none" stroke-linecap="round"/>`,
	'open-hands': `
		<path d="M24 7v6M17 9l2 4.5M31 9l-2 4.5" stroke="${G}" stroke-width="1.6" stroke-linecap="round"/>
		<circle cx="24" cy="18" r="3.4" fill="${G}"/>
		<circle cx="24" cy="24.5" r="1.9" fill="${RO}"/>
		<path d="M8 26c2 6.5 7 11 16 11s14-4.5 16-11c-1.6-1.1-3.6-.7-5 1-2-3-5-3-7-.6-2-2.6-5-2.6-7 0-1.4-1.7-3.4-2.1-5-1z" fill="${CRD}"/>
		<path d="M12 27.5c3 5 7 8 12 8s9-3 12-8" stroke="${BR}" stroke-width="1" fill="none" opacity=".5"/>`,
	'broken-chain': `
		<rect x="7" y="19.5" width="15" height="9" rx="4.5" fill="none" stroke="${SL}" stroke-width="3"/>
		<path d="M27 19.5h3.5a4.5 4.5 0 0 1 0 9H29" fill="none" stroke="${SLD}" stroke-width="3"/>
		<path d="M41 19.5h-4" stroke="${SLD}" stroke-width="3" stroke-linecap="round" fill="none"/>
		<circle cx="24.5" cy="24" r="2.2" fill="${R}"/>
		<path d="M24.5 24l2.5-3.5M24.5 24l3.5 1M24.5 24l-1 3.5M24.5 24l2.5 3.2" stroke="${G}" stroke-width="1.5" stroke-linecap="round"/>`,
	'mountain-into-sea': `
		<path d="M14 34L26 11l13 23z" fill="${SLD}"/>
		<path d="M26 11l4.6 8.6-2.3-1.3-2.3 1.9-2.4-1.5z" fill="${W}"/>
		<path d="M0 34h48v10H0z" fill="${B}"/>
		<path d="M4 34c3 0 3 2 6 2s3-2 6-2 3 2 6 2 3-2 6-2 3 2 6 2 3-2 6-2" stroke="${SK}" stroke-width="1.6" fill="none" stroke-linecap="round"/>
		<path d="M12 33c-1-3-3-4-5.5-3M36 33c1-3 3-4 5.5-3" stroke="${SK}" stroke-width="1.4" fill="none" stroke-linecap="round"/>`,
	'sword-and-shield': `
		<path d="M34 11L15 39" stroke="${SL}" stroke-width="2.4" stroke-linecap="round"/>
		<path d="M31.5 12.5l4 4" stroke="${GD}" stroke-width="2.6" stroke-linecap="round"/>
		<circle cx="36" cy="10" r="1.8" fill="${GD}"/>
		<path d="M22 9l11 3.6v9.4c0 7.4-4.6 12-11 15-6.4-3-11-7.6-11-15v-9.4z" fill="${B}"/>
		<path d="M22 9l11 3.6v9.4c0 7.4-4.6 12-11 15z" fill="${BD}"/>
		<path d="M22 15.5v13M16.5 21h11" stroke="${G}" stroke-width="2.1" stroke-linecap="round"/>`,
	'rooted-sapling': `
		<circle cx="24" cy="21" r="15" fill="${GR}" fill-opacity=".2"/>
		<circle cx="36.5" cy="10.5" r="3.3" fill="${G}"/>
		<path d="M36.5 4.9v1.9M32 6.5l1 1.3M41 6.5l-1 1.3" stroke="${G}" stroke-width="1.7" stroke-linecap="round"/>
		<path d="M22.6 38V18.5h2.8V38z" fill="${BR}"/>
		<path d="M24 27.5c-3.7-.8-6.1-3.1-6.9-6.9 3.9 0 6.5 1.8 6.9 5.1z" fill="${GRD}"/>
		<path d="M24 27.5c3.7-.8 6.1-3.1 6.9-6.9-3.9 0-6.5 1.8-6.9 5.1z" fill="${GRD}"/>
		<path d="M24 21.8c-1.7-3.5-1.1-7 1.8-10.3 1.4 3 1.2 6-1.8 10.3z" fill="${GR}"/>
		<path d="M24 21.8c1.7-3.5 1.1-7-1.8-10.3-1.4 3-1.2 6 1.8 10.3z" fill="${GR}"/>
		<path d="M19.4 23.2c-3-.3-5.1-2.1-6.2-5 3.2-.5 5.5.5 6.7 3.3z" fill="${GR}"/>
		<path d="M28.6 23.2c3-.3 5.1-2.1 6.2-5-3.2-.5-5.5.5-6.7 3.3z" fill="${GR}"/>
		<path d="M24 38c-1.8-1.6-3.8-2.4-6-2.6M24 38c1.8-1.6 3.8-2.4 6-2.6" stroke="${BRD}" stroke-width="1.5" stroke-linecap="round" fill="none"/>
		<path d="M8.5 40.5h31" stroke="${B}" stroke-width="2.4" stroke-linecap="round"/>
		<path d="M11.5 43.4c1.9-1.3 3.8-1.3 5.7 0M19 43.4c1.9-1.3 3.8-1.3 5.7 0M26.5 43.4c1.9-1.3 3.8-1.3 5.7 0" stroke="${SK}" stroke-width="1.5" stroke-linecap="round" fill="none"/>`,
	'eagles-wings': `
		<circle cx="24" cy="23" r="16" fill="${SK}" fill-opacity=".3"/>
		<path d="M24 22 L5.5 10 C10 15 11 19 10 22 C14.5 20 18.5 21 21 26 Z" fill="${G}"/>
		<path d="M24 22 L42.5 10 C38 15 37 19 38 22 C33.5 20 29.5 21 27 26 Z" fill="${G}"/>
		<path d="M23 24 L11.5 17.5 C13.5 20.5 14 22.5 13 24.5 C16 23.5 18 24.5 20.5 27 Z" fill="${GD}"/>
		<path d="M25 24 L36.5 17.5 C34.5 20.5 34 22.5 35 24.5 C32 23.5 30 24.5 27.5 27 Z" fill="${GD}"/>
		<path d="M24 19 C21.4 21 21 25 21.7 30 C22.2 34.2 23 37.2 24 39.8 C25 37.2 25.8 34.2 26.3 30 C27 25 26.6 21 24 19 Z" fill="${BR}"/>
		<path d="M21 37 L24 42 L27 37 Z" fill="${GD}"/>
		<circle cx="24" cy="16" r="3.4" fill="${CR}"/>
		<path d="M22.7 17.4 L24 20.2 L25.3 17.4 Z" fill="${GD}"/>`,
	'guiding-star': `
		<circle cx="24" cy="19" r="15" fill="${SK}" fill-opacity=".35"/>
		<path d="M33 5l1.9 4.6 4.9.5-3.7 3.3 1.1 4.8L33 15.9l-4.3 2.3 1.1-4.8-3.7-3.3 4.9-.5z" fill="${G}"/>
		<path d="M23 6.5l.9 2 2 .9-2 .9-.9 2-.9-2-2-.9 2-.9z" fill="${G}" fill-opacity=".85"/>
		<path d="M6 41h36v3H6z" fill="${GRD}"/>
		<path d="M6 41c6-9 14-9 19-3 4 4.8 9 5 11 2v4H6z" fill="${GR}"/>
		<path d="M20 43c1-6 8-8 6-15-1.5-5 3-7 5-10" stroke="${CRD}" stroke-width="3" fill="none" stroke-linecap="round"/>
		<path d="M20 43c1-6 8-8 6-15-1.5-5 3-7 5-10" stroke="${W}" stroke-width="1.1" fill="none" stroke-linecap="round"/>`
} as const;

export type EmblemName = keyof typeof EMBLEM_ART;

/**
 * The dominant ink of an emblem — its own accent, read back off the drawing.
 *
 * Topics and plans carry a hand-tuned `accent` in their META tables because
 * there are ten and eight of them. Sermons are a growing catalogue with a new
 * one every import, and a hue nobody remembers to set is a hue that ends up
 * wrong; deriving it means a sermon's card is coloured the moment its emblem
 * is chosen, with nothing else to author.
 *
 * Scored `count × (0.35 + saturation)`, discounting inks outside a usable
 * lightness band, then floored to a minimum saturation — the same two moves
 * `covers.py:palette_from_artwork` makes to pull a cover colour out of a
 * book's artwork, and for the same reasons. Counting alone hands the accent to
 * whichever neutral the drawing happens to shade with: the raven emblem came
 * out slate grey, which is honestly its most-used ink and a thoroughly drab
 * thing to letter a share card in. Scoring by saturation separates "the colour
 * this drawing IS" from "the colour it is shaded with"; the floor then keeps
 * an emblem that really is drawn in slate (the raven, the rock) from lettering
 * its card in something indistinguishable from muted body text.
 *
 * The cream/white papers are excluded outright rather than left to the score:
 * they highlight nearly every emblem, and the lightness discount alone still
 * let warm white carry the shepherd's-crook. A card lettered in #fdfaf3 has no
 * accent at all, only two shades of white.
 *
 * The LIGHTNESS is left alone: what a hue needs in order to carry type depends
 * on the surface it lands on, and this module does not know that. Callers
 * floor it themselves — `scripts/og-card.mjs:liftToContrast` for the near-black
 * share card, `color-mix` tints for the app's chips.
 */
export const MIN_ACCENT_SATURATION = 0.3;
const PAPER_INKS: ReadonlySet<string> = new Set([CR, CRD, W]);

/** HSL saturation and lightness of a #rrggbb colour. Hue is never needed. */
const satLightness = (hex: string): [number, number] => {
	const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
	const max = Math.max(r, g, b);
	const min = Math.min(r, g, b);
	const lightness = (max + min) / 2;
	if (max === min) return [0, lightness];
	const d = max - min;
	return [lightness > 0.5 ? d / (2 - max - min) : d / (max + min), lightness];
};

export const emblemHue = (name: EmblemName): string => {
	const inks = (EMBLEM_ART[name].match(/#[0-9a-f]{6}/gi) ?? []).map((ink) => ink.toLowerCase());
	// An emblem drawn ENTIRELY in the papers has no other ink to prefer, so it
	// gets its most-used one rather than a brand default standing in for art.
	const usable = inks.filter((hex) => !PAPER_INKS.has(hex));
	const counts = new Map<string, number>();
	for (const hex of usable.length ? usable : inks) {
		counts.set(hex, (counts.get(hex) ?? 0) + 1);
	}
	let best = '';
	let winner: [number, number] = [0, 0];
	let bestScore = 0;
	for (const [hex, count] of counts) {
		const [saturation, lightness] = satLightness(hex);
		const usable = lightness > 0.12 && lightness < 0.62 ? 1 : 0.35;
		const score = count * (0.35 + saturation) * usable;
		if (score > bestScore) [best, winner, bestScore] = [hex, [saturation, lightness], score];
	}
	const [saturation, lightness] = winner;
	if (saturation >= MIN_ACCENT_SATURATION) return best;
	// Saturating at fixed hue and lightness is just a spread of the channels away
	// from their midpoint — HSL is affine in saturation once h and l are pinned,
	// so a round trip through it would be thirty lines to reach the same bytes
	// (checked against all 51 emblems). It is also better behaved at the edge: a
	// pure grey has no hue to restore, and this leaves it grey where fromHsl
	// would have read its hue as 0 and handed back a red.
	const mid = lightness * 255;
	const spread = saturation === 0 ? 0 : MIN_ACCENT_SATURATION / saturation;
	return `#${[1, 3, 5]
		.map((i) => {
			const c = mid + (parseInt(best.slice(i, i + 2), 16) - mid) * spread;
			return Math.max(0, Math.min(255, Math.round(c)))
				.toString(16)
				.padStart(2, '0');
		})
		.join('')}`;
};
