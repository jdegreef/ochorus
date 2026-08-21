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
		<path d="M3 27.5c.3-1.7.8-3.2 1.6-4.6M45 27.5c-.3-1.7-.8-3.2-1.6-4.6" stroke="${SK}" stroke-width="2" stroke-linecap="round" fill="none"/>`
} as const;

export type EmblemName = keyof typeof EMBLEM_ART;

// ── Curated assignments ─────────────────────────────────────────────────────
// One emblem per slug, unique across all three catalogues (a test enforces
// this). Slugs match the backend seeds (seed_topics / seed_plans / fixtures).

/**
 * Per-topic visual identity: accent hue + emblem, so each shelf reads as its
 * own thing rather than one more identical card. The accent is used for tints
 * (via color-mix), never as body text, so it stays legible in both themes.
 */
export const TOPIC_META: Record<string, { accent: string; emblem: EmblemName }> = {
	prayer: { accent: '#5257c9', emblem: 'praying-hands' }, // the secret place
	'holy-spirit': { accent: '#d98324', emblem: 'dove-descending' }, // the dove, the rushing wind (Acts 2)
	'deeper-life': { accent: '#149e93', emblem: 'mountain-dawn' }, // going further in
	'grace-and-comfort': { accent: '#d1567b', emblem: 'overflowing-cup' }, // my cup runneth over
	'revival-and-missions': { accent: '#df552f', emblem: 'torch-globe' }, // a light to the nations
	'faith-and-guidance': { accent: '#4f9a3e', emblem: 'compass-rose' }, // walking by faith
	'the-gospel-call': { accent: '#b8912f', emblem: 'herald-trumpet' }, // the oldest invitation there is
	'enduring-classics': { accent: '#8a5bbf', emblem: 'laurel-tome' }, // the old paths, still good
	'the-way-of-holiness': { accent: '#3e7cb8', emblem: 'narrow-gate' }, // strait is the gate
	'the-preached-word': { accent: '#946b4a', emblem: 'open-word' } // great preaching on the page
};

/** Per-plan visual identity: accent hue + emblem (same shape as TOPIC_META). */
export const PLAN_META: Record<string, { accent: string; emblem: EmblemName }> = {
	'school-of-prayer': { accent: '#6a5ecf', emblem: 'rising-incense' }, // prayer as incense
	'humility-12-days': { accent: '#2f8f85', emblem: 'basin-towel' }, // the servant's basin
	'the-inner-chamber-month': { accent: '#b8912f', emblem: 'door-ajar' }, // shut thy door
	'deeper-life-in-christ': { accent: '#5a9e4d', emblem: 'true-vine' }, // abide in me
	'grace-for-every-sinner': { accent: '#d1567b', emblem: 'shepherd-crook' }, // the seeking shepherd
	'faith-in-the-fire': { accent: '#b3474f', emblem: 'refiners-crucible' }, // tried as gold
	'power-from-on-high': { accent: '#d98324', emblem: 'pentecost-fire' }, // tongues as of fire
	'everything-for-christ': { accent: '#8a5bbf', emblem: 'poured-out' } // a life poured out
};

export const SERMON_EMBLEMS: Record<string, EmblemName> = {
	himself: 'chi-rho', // now it is the Lord
	'the-power-of-stillness': 'still-waters', // a still small voice
	'the-possibilities-of-faith': 'mustard-tree', // faith as a grain of mustard seed
	'the-joy-of-the-lord': 'joyful-harp', // the joy of the Lord is your strength
	'aggressive-christianity': 'gospel-banner', // a banner for the truth
	'blessed-adversity': 'olive-press', // oil comes from pressing
	'christ-all-in-all': 'alpha-omega', // the beginning and the end
	'christ-crucified': 'cross-sunrise', // we preach Christ crucified
	'christ-precious-to-believers': 'pearl-of-price', // the pearl of great price
	'christs-boundless-compassion': 'sheltering-wings', // as a hen gathers her brood
	'come-thou-into-the-ark': 'ark-rainbow', // the door was shut, the bow was set
	'comfort-for-the-desponding': 'jar-of-balm', // balm in Gilead
	'compel-them-to-come-in': 'feast-table', // that my house may be filled
	'consolation-in-the-furnace': 'fourth-in-fire', // the fourth is like the Son of God
	'eight-i-wills-of-christ': 'sealed-scroll', // promises signed and sealed
	'free-grace': 'grace-fountain', // whosoever will, freely
	'order-and-argument-in-prayer': 'heavens-ladder', // ordering our cause before Him
	'pauls-first-prayer': 'kneeling-light', // behold, he prayeth
	rest: 'easy-yoke', // my yoke is easy
	'salvation-by-faith': 'shield-of-faith', // above all, taking the shield of faith
	'sweet-comfort-for-feeble-saints': 'bruised-reed', // a bruised reed he will not break
	'the-dying-thief': 'paradise-palms', // today, in paradise
	'the-golden-key-of-prayer': 'golden-key', // call unto me, and I will answer
	'the-immutability-of-god': 'rock-unmoved', // I am the Lord, I change not
	'the-new-birth': 'new-sprout', // ye must be born again
	'the-ravens-cry': 'ravens-bread', // he feedeth the young ravens
	'the-sweet-uses-of-adversity': 'rose-among-thorns', // sweet are the uses of adversity
	'the-way-of-salvation': 'pilgrim-road', // the road home
	'unfailing-springs': 'desert-spring' // springs in the desert
};

// ── Fallbacks ───────────────────────────────────────────────────────────────
// New content lands before anyone curates art for it; a stable hash-pick from
// a small generic pool keeps it looking finished until someone does.

export const FALLBACK_POOL: EmblemName[] = [
	'oil-lamp',
	'wheat-sheaf',
	'morning-star',
	'watchmans-bell'
];

/** FNV-1a — stable across sessions, so a slug always wears the same art. */
const fnv = (s: string): number => {
	let h = 0x811c9dc5;
	for (let i = 0; i < s.length; i++) {
		h ^= s.charCodeAt(i);
		h = Math.imul(h, 0x01000193) >>> 0;
	}
	return h;
};

export const fallbackEmblem = (slug: string): EmblemName =>
	FALLBACK_POOL[fnv(slug) % FALLBACK_POOL.length];

export const emblemForSermon = (slug: string): EmblemName =>
	SERMON_EMBLEMS[slug] ?? fallbackEmblem(slug);

export const topicMeta = (slug: string): { accent: string; emblem: EmblemName } =>
	TOPIC_META[slug] ?? { accent: '#3b5bdb', emblem: fallbackEmblem(slug) };

/**
 * The curated plan accents, cycled by slug hash for plans that ship without
 * curated art yet — same reasoning as the topic-accent fallback: covers are
 * mostly dark navy, so deriving a hue from them made every card the same
 * muted blue.
 */
const PLAN_ACCENTS = Object.values(PLAN_META).map((m) => m.accent);

export const planMeta = (slug: string): { accent: string; emblem: EmblemName } =>
	PLAN_META[slug] ?? {
		accent: PLAN_ACCENTS[fnv(slug) % PLAN_ACCENTS.length],
		emblem: fallbackEmblem(slug)
	};
