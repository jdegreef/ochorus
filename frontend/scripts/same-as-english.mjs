/**
 * Message keys whose value is correctly identical to English — typography
 * names, borrowed terms, proper nouns, and French/Latinate words spelled the
 * same. Anything else identical to English is an untranslated placeholder.
 *
 * Shared by `src/lib/messages.test.ts` (which fails an undeclared placeholder)
 * and `sync-ui-catalogues.mjs` (which hands each locale's placeholders to the
 * API's readiness report), so the two can never disagree about what counts as
 * untranslated.
 */

/** @type {ReadonlySet<string>} */
export const SAME_AS_ENGLISH_OK = new Set([
	// The settings page repeats several of these under `settings_*` keys.
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
	'nav_originals', // Originals — the imprint's name, kept as-is in sw/lg
	'originals_eyebrow', // Ochorus Originals — the imprint, a proper noun
	'originals_series_heading', // Series (es)
	'originals_series_many', // series (es)
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
