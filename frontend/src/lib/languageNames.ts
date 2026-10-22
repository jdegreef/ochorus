/**
 * A language's name in another language, as a word for mid-sentence use:
 * "inglés" in Spanish, "anglais" in French. Pure (no Paraglide, no Svelte), so
 * the /for/ page builders and the reader's notices share one namer.
 */

const NAMERS = new Map<string, Intl.DisplayNames | null>();

function namer(locale: string): Intl.DisplayNames | null {
	if (!NAMERS.has(locale)) {
		let n: Intl.DisplayNames | null = null;
		try {
			// No data for the locale → ICU would answer in the DEFAULT locale's
			// words, an English name in a foreign sentence; say "no name" instead.
			if (Intl.DisplayNames.supportedLocalesOf([locale]).length)
				n = new Intl.DisplayNames([locale], { type: 'language', fallback: 'none' });
		} catch {
			// An invalid tag throws.
		}
		NAMERS.set(locale, n);
	}
	return NAMERS.get(locale) ?? null;
}

/** `code`'s name in `locale`, or null where the runtime has none. ICU calls
 *  Luganda "Ganda"; Ochorus uses the name its readers use, in the locale's
 *  case ("luganda" mid-sentence in French). */
export function nameOfLanguage(code: string, locale: string): string | null {
	let name: string | null = null;
	try {
		name = namer(locale)?.of(code) ?? null;
	} catch {
		// An invalid code throws.
	}
	if (code === 'lg' && name && /^ganda$/i.test(name)) return name[0] === 'g' ? 'luganda' : 'Luganda';
	return name;
}
