// hex-ok-file: illustration ink, as in emblems.ts — the colours OF the
// drawings, not chrome. Every one is a colour of emblems.ts' shared palette
// (sectionEmblems.test.ts checks), so these sit with the topic and plan art.

import type { NavSection } from '$lib/contentNav';

/**
 * Each library section's own emblem, drawn for it — not borrowed from the
 * topic / plan / sermon catalogue, whose emblems are one per slug, so a
 * section's mark never looks like one of its own entries.
 *
 * Kept OUT of emblems.ts on purpose: EMBLEM_ART is a lazily split chunk
 * (emblemNames.ts explains the critical-path cost that bought), and the page
 * header that draws these is on nearly every page. Five drawings here cost a
 * fraction of importing all of them. Inner markup for a 48×48 viewBox, at
 * least three colours each, static author-controlled strings.
 */
const G = '#d9a441'; // gold
const GD = '#a97a24'; // deep gold
const T = '#2f8f85'; // teal
const R = '#d95f43'; // coral red
const RD = '#a83a25'; // deep red
const B = '#4a6fb5'; // blue
const BD = '#2d4a80'; // navy
const GR = '#5a9e4d'; // leaf green
const GRD = '#3d7434'; // deep green
const CR = '#f3e2c4'; // cream
const CRD = '#e0c69a'; // shaded cream
const BR = '#8a6440'; // brown
const BRD = '#5f4227'; // dark brown
const SK = '#a7c9e8'; // sky
const SL = '#6b7f8f'; // slate
const W = '#fdfaf3'; // warm white

export const SECTION_EMBLEMS: Record<NavSection, string> = {
	// Books — a stack of three bound volumes, a ribbon marking the top one.
	books: `
		<rect x="7" y="33" width="34" height="8" rx="1.6" fill="${BD}"/>
		<rect x="36.5" y="34.4" width="3.2" height="5.2" fill="${CR}"/>
		<rect x="7" y="35.6" width="29" height="1.5" fill="${G}"/>
		<rect x="10" y="24.6" width="30" height="8" rx="1.6" fill="${RD}"/>
		<rect x="10.8" y="26" width="3.2" height="5.2" fill="${CR}"/>
		<rect x="14" y="27.3" width="26" height="1.5" fill="${G}"/>
		<rect x="8" y="16.2" width="31" height="8" rx="1.6" fill="${GRD}"/>
		<rect x="34.4" y="17.6" width="3.2" height="5.2" fill="${CR}"/>
		<rect x="8" y="18.9" width="26" height="1.5" fill="${G}"/>
		<path d="M27 16.2V7.5l2.4 2 2.4-2v8.7z" fill="${R}"/>`,
	// Topics — three tags on a gold ring: the themes the library is sorted by.
	topics: `
		<circle cx="13" cy="13" r="5" fill="none" stroke="${G}" stroke-width="2.4"/>
		<path d="M15.5 17.5 26 11l14 8.6-6.4 10.4-14-8.6z" fill="${B}"/>
		<path d="M14.5 18.5 20 30.5l15.8 4.4-3.2 11.8-15.8-4.4z" fill="${R}" transform="rotate(-8 24 32)"/>
		<path d="M14 18.8 10.5 31l6 13.5 10.8-5.4-6-13.5z" fill="${GR}"/>
		<circle cx="27" cy="16" r="1.6" fill="${W}"/>
		<circle cx="20.5" cy="33" r="1.6" fill="${W}"/>
		<circle cx="16" cy="33.6" r="1.6" fill="${W}"/>`,
	// Plans — a day torn off a calendar: a ring-bound page, its date ticked.
	plans: `
		<rect x="8" y="10" width="32" height="32" rx="3" fill="${W}"/>
		<rect x="8" y="10" width="32" height="9" rx="3" fill="${T}"/>
		<rect x="8" y="16" width="32" height="3" fill="${T}"/>
		<rect x="14" y="6" width="3" height="8" rx="1.5" fill="${SL}"/>
		<rect x="31" y="6" width="3" height="8" rx="1.5" fill="${SL}"/>
		<path d="M14 24h20M14 29h20M14 34h11" stroke="${CRD}" stroke-width="2" stroke-linecap="round"/>
		<path d="M27.5 33.5l3.2 3.2 6.3-7" fill="none" stroke="${GR}" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>`,
	// Sermons — a pulpit: the open Bible on its desk, the fall cloth below.
	sermons: `
		<path d="M10 20h28l-3 22H13z" fill="${BR}"/>
		<rect x="8" y="17.5" width="32" height="4" rx="1.2" fill="${BRD}"/>
		<path d="M24 16.5c-4-2.6-9-3-13-1.6v3.3c4-1.2 9-.8 13 1.6zM24 16.5c4-2.6 9-3 13-1.6v3.3c-4-1.2-9-.8-13 1.6z" fill="${CR}"/>
		<path d="M18 22h12v14l-6-3.4-6 3.4z" fill="${R}"/>
		<path d="M24 24.5v6.5M21.3 27h5.4" stroke="${G}" stroke-width="1.8" stroke-linecap="round"/>
		<path d="M24 6.5v4M18 8l1.6 3M30 8l-1.6 3" stroke="${GD}" stroke-width="1.8" stroke-linecap="round"/>`,
	// Biographies — a portrait cameo in a gilt oval: a life, remembered.
	biographies: `
		<ellipse cx="24" cy="24" rx="15.5" ry="19" fill="${G}"/>
		<ellipse cx="24" cy="24" rx="12" ry="15.5" fill="${SK}"/>
		<circle cx="24" cy="20" r="5.2" fill="${BD}"/>
		<path d="M14.2 34.5c1.6-6 5.4-8.8 9.8-8.8s8.2 2.8 9.8 8.8c-2.6 3-6 4.8-9.8 4.8s-7.2-1.8-9.8-4.8z" fill="${BD}"/>
		<path d="M24 3.2l1.2 2.4 2.6.4-1.9 1.8.5 2.6-2.4-1.3-2.4 1.3.5-2.6-1.9-1.8 2.6-.4z" fill="${GD}"/>
		<path d="M18.5 31.5 24 36l5.5-4.5" fill="none" stroke="${W}" stroke-width="1.4" stroke-linecap="round"/>`
};
