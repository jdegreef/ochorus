import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

/**
 * i18n completeness guard. Keeps the four locales honest so a missing key or a
 * left-behind English string can't ship silently:
 *  1. every locale defines exactly the same keys (parity),
 *  2. every `t('…')` key used in the app exists in the base locale,
 *  3. no non-English value is identical to English (i.e. actually translated),
 *     apart from a small allowlist of borrowed / proper-noun terms.
 */

const LOCALES = ['en', 'es', 'sw', 'lg', 'pt', 'ar', 'hi', 'uk', 'fr'] as const;
const BASE = 'en';
const MSG_DIR = path.resolve('messages');

const load = (l: string): Record<string, string> =>
	JSON.parse(fs.readFileSync(path.join(MSG_DIR, `${l}.json`), 'utf8'));
const data = Object.fromEntries(LOCALES.map((l) => [l, load(l)])) as Record<
	string,
	Record<string, string>
>;
const keysOf = (l: string) => Object.keys(data[l]).filter((k) => k !== '$schema');

// Terms deliberately identical to English across locales: typography names and
// (in Spanish) "Normal". Anything else identical to English is untranslated.
// The settings page repeats several of these under `settings_*` keys.
const SAME_AS_ENGLISH_OK = new Set([
	'font_serif',
	'font_sans',
	'font_dyslexic',
	'spacing_normal',
	'width_normal',
	'settings_font_serif',
	'settings_font_sans',
	'settings_width_normal',
	'common_min',
	'login_email',
	// "Original" is the same word in Spanish — a legitimate borrowed term.
	'reader_original',
	// "A–Z" is the same alphabetical-sort label in every language we support.
	'search_sort_title',
	// "Sepia" is the borrowed colour-tone name, unchanged across our locales.
	'settings_theme_sepia',
	// The About page's ministry partner is a proper-noun organisation name, kept
	// in its registered English form in every locale.
	'about_partner_name',
	// "Menu" is the natural UI term in Portuguese too (Spanish keeps its accent,
	// "Menú", so this only exempts the pt collision).
	'a11y_menu',
	// The mid length label is a bare "10–30 min" range — every word-bearing
	// sibling (short/long) IS translated, but "min" is the standard minute
	// abbreviation in both Spanish and Portuguese, so the range reads identically.
	'sermons_length_mid',
	// French shares a large Latinate vocabulary with English, so a run of
	// single-word UI labels is spelled identically in both and is correctly
	// translated by being unchanged — not debt. These collide on `fr` only
	// (es/pt render them differently, e.g. "Sermones"/"Sermões"), the same
	// per-locale exemption `a11y_menu` already makes for pt.
	'author_portrait_credit', // Portrait
	'notebook_daily_amen', // Amen.
	'bios_eyebrow', // Biographies
	'bios_sermons_many', // sermons
	'bios_sermons_one', // sermon
	'common_article_many', // articles
	'common_article_one', // article
	'common_sermon_many', // sermons
	'common_sermon_one', // sermon
	'fav_group_articles', // Articles
	'fav_group_plans', // Plans
	'fav_group_sermons', // Sermons
	'nav_articles', // Articles
	'nav_biographies', // Biographies
	'nav_contact', // Contact
	'nav_plans', // Plans
	'nav_sermons', // Sermons
	'plans_length_long', // Long
	'progress_page', // Page
	'reader_difficulty_accessible', // Accessible
	'reader_hl_rose', // Rose
	'reader_layout_page', // Page
	'reader_note', // Note
	'reader_pause', // Pause
	'scripture_passages_count', // %count% passages
	'search_group_articles', // Articles
	'search_group_passages', // Passages
	'search_group_sermons', // Sermons
	'search_palette_pages', // Page
	'search_type_article', // Article
	'search_type_chapter', // Passage
	'search_type_sermon', // Sermon
	'sermons_label', // Sermon
	'settings_stat_notes', // Notes
	'spacing_compact', // Compact
	'topics_articles', // Articles
	'topics_sermons' // Sermons
]);

/**
 * Strings a locale has NOT translated yet — declared, rather than hidden.
 *
 * Different in kind from SAME_AS_ENGLISH_OK above, which is "identical to
 * English forever, and correctly so". This is debt, with a reason and a way out.
 *
 * Asserted EXACTLY, in both directions: a fifth untranslated string fails, and
 * so does fixing one of these four without deleting it from here. A pending
 * list that only ever grows is how "temporary" becomes permanent — same
 * two-way ratchet the English-audit baseline uses, for the same reason.
 */
// The book page's "more like this" reason labels. The keys ship to every
// catalogue for parity, but only en/es/pt/fr are translated and reviewed; the
// book page renders these only in those locales (its REVIEWED_LOCALES set), so
// the English placeholders below never reach a reader. Awaiting native review —
// when a locale's are translated, delete it here and add it to REVIEWED_LOCALES.
// (The old derived-FAQ keys were removed when books went editorial-only.)
const BOOK_EXTRAS_PENDING = ['book_more_by', 'book_also_on'] as const;

// The sermon page's "Questions for reflection" heading. Same story as
// BOOK_EXTRAS_PENDING: en/es/pt/fr are translated and reviewed (the sermon
// page's REVIEWED_LOCALES), the rest hold the English source as a gated-off
// placeholder that never reaches a reader. Delete a locale's entry and add it to
// REVIEWED_LOCALES once a native speaker checks the heading.
const SERMON_EXTRAS_PENDING = ['sermon_questions_title'] as const;

// The book/topic Q&A section heading ("Questions and Answers"). Same story again:
// en/es/pt/fr are translated and reviewed, the rest hold the English source as a
// placeholder until a native speaker checks it. Delete a locale's entry once its
// heading is translated. (The Q&A section only renders where per-row Q&A content
// exists for the locale, so today the placeholder never reaches a reader anyway.)
const QA_EXTRAS_PENDING = ['qa_section_title'] as const;

// The reader-feedback button + modal strings. en/es/pt/fr are translated and
// reviewed; the placeholder locales below hold the English source until a native
// speaker checks them. Delete these once a locale's feedback strings are
// translated (they share one pending list across the placeholder locales).
const FEEDBACK_EXTRAS_PENDING = [
	'feedback_send',
	'feedback_title',
	'feedback_intro',
	'feedback_type',
	'feedback_type_language',
	'feedback_type_content',
	'feedback_type_feature',
	'feedback_type_bug',
	'feedback_type_other',
	'feedback_placeholder',
	'feedback_about',
	'feedback_submit',
	'feedback_sending',
	'feedback_thanks_title',
	'feedback_thanks_body',
	'feedback_error'
] as const;

const UI_EXTRAS_PENDING = [
	...BOOK_EXTRAS_PENDING,
	...SERMON_EXTRAS_PENDING,
	...QA_EXTRAS_PENDING,
	...FEEDBACK_EXTRAS_PENDING
];

const PENDING_TRANSLATION: Record<string, readonly string[]> = {
	// A blocked/awaiting-review string is declared here and ratcheted (asserted
	// exactly, both directions) rather than quietly allowlisted forever. uk's four
	// Scripture strings once lived here until the Kulish text could be sourced.
	sw: UI_EXTRAS_PENDING,
	lg: UI_EXTRAS_PENDING,
	hi: UI_EXTRAS_PENDING,
	ar: UI_EXTRAS_PENDING,
	uk: UI_EXTRAS_PENDING
};

const toSnake = (key: string) =>
	key
		.replace(/([a-z0-9])([A-Z])/g, '$1_$2')
		.replace(/\./g, '_')
		.toLowerCase();

function usedKeys(): Set<string> {
	const out = new Set<string>();
	const re = /\bt\(\s*['"`]([a-zA-Z0-9_.]+)['"`]\s*\)/g;
	const walk = (dir: string) => {
		for (const name of fs.readdirSync(dir)) {
			const p = path.join(dir, name);
			const stat = fs.statSync(p);
			if (stat.isDirectory()) {
				if (!p.includes('paraglide')) walk(p);
			} else if (/\.(svelte|ts)$/.test(name) && !name.endsWith('.test.ts')) {
				const src = fs.readFileSync(p, 'utf8');
				for (let m; (m = re.exec(src)); ) out.add(toSnake(m[1]));
			}
		}
	};
	walk(path.resolve('src'));
	return out;
}

describe('i18n messages', () => {
	it('all locales define the same keys (parity)', () => {
		const base = new Set(keysOf(BASE));
		for (const l of LOCALES.filter((x) => x !== BASE)) {
			const here = new Set(keysOf(l));
			const missing = [...base].filter((k) => !here.has(k));
			const extra = [...here].filter((k) => !base.has(k));
			expect({ locale: l, missing, extra }).toEqual({ locale: l, missing: [], extra: [] });
		}
	});

	it('every t() key used in the app exists in the base locale', () => {
		const base = new Set(keysOf(BASE));
		const missing = [...usedKeys()].filter((k) => !base.has(k)).sort();
		expect(missing).toEqual([]);
	});

	it('non-English strings are actually translated (or declared pending)', () => {
		// DERIVED from LOCALES, not a second hardcoded list. This check used to
		// carry its own copy of the locale array, which meant every new locale had
		// to be remembered in two places to be covered — and href.test.ts already
		// records what that costs: its locale list was literal, pt was wired in,
		// and the guard silently stopped covering /pt/. One list, one place.
		for (const l of LOCALES.filter((x) => x !== BASE)) {
			const untranslated = keysOf(BASE)
				.filter((k) => !SAME_AS_ENGLISH_OK.has(k) && data[l][k] === data[BASE][k])
				.sort();
			expect(
				{ locale: l, untranslated },
				`${l} has untranslated strings that are not declared in PENDING_TRANSLATION. ` +
					'Translate them, or — if they are blocked on something (a Bible text, a ' +
					'reviewer) — add them there with the reason. If a listed key is now ' +
					'translated, delete it from PENDING_TRANSLATION.'
			).toEqual({ locale: l, untranslated: [...(PENDING_TRANSLATION[l] ?? [])].sort() });
		}
	});
});
