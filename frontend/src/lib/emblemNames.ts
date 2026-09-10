/**
 * WHICH emblem each catalogue entry wears — and nothing about how it is drawn.
 *
 * Split out of `emblems.ts` for one concrete reason: that module also holds
 * `EMBLEM_ART`, 51 SVG drawings that Rollup bundles as a single shared chunk
 * (37 KB raw, 9.8 KB gzip). Importing one lookup from it pulled all of them, so
 * the sermon plate — which needs a slug's emblem NAME to load the drawing
 * lazily — put every emblem on the critical path of the home page and of every
 * sermon page. Measured, before and after; this is not a hypothetical.
 *
 * `emblems.ts` re-exports everything here, so it stays the front door and no
 * existing caller had to move. Import from THIS module only when you need an
 * assignment without a drawing.
 *
 * Slugs match the backend seeds (seed_topics / seed_plans / fixtures).
 *
 * hex-ok-file: the curated topic and plan accents. These are catalogue
 * identity — the colour that entry IS, like a book's cover_color — not chrome
 * that should restyle with the theme, and they reach the pixel only through
 * color-mix (STYLE_GUIDE §Cards).
 */
import type { EmblemName } from './emblems';

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
	'the-preached-word': { accent: '#946b4a', emblem: 'open-word' }, // great preaching on the page
	// ── batch 1 ──────────────────────────────────────────────────────────────
	'the-east-african-revival': { accent: '#cf5a4a', emblem: 'dawn-over-hills' }, // the walk in the light
	'the-puritans': { accent: '#3f4d80', emblem: 'candle-and-book' }, // plain, searching divinity
	'to-the-ends-of-the-earth': { accent: '#3a6ea5', emblem: 'mission-ship' }, // the gospel carried at any cost
	'christ-and-the-cross': { accent: '#b3474f', emblem: 'paschal-lamb' }, // the Lamb slain (Agnus Dei)
	'women-of-faith': { accent: '#b5628f', emblem: 'alabaster-jar' } // the costly ointment
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
 * topic slug → emblem name, sorted, for the COVER GENERATOR.
 *
 * `covers.py` draws the emblem a book's topic wears, and cannot read anything
 * under `frontend/` (the API image has rootDir `backend/`), so
 * `npm run emblem:art` exports this map beside the drawings and
 * `emblemArt.test.ts` fails if the committed copy has drifted. It lives here,
 * beside TOPIC_META, so that the exporter and its gate call ONE function: a
 * gate that re-derives what it is checking is a second opinion, not a drift
 * test — the two agree right up until the day one of them changes.
 */
export const topicEmblems = (): Record<string, EmblemName> =>
	Object.fromEntries(
		Object.entries(TOPIC_META)
			.map(([slug, meta]) => [slug, meta.emblem])
			.sort(([a], [b]) => a.localeCompare(b))
	);

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
