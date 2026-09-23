import { lang } from './lang.svelte';
import { localizeHref } from './href';
import { MODERN_EDITION, baseEdition } from './reading-schema';
import type { EntrySource } from './journal';

/** The locale union `localizeHref` accepts; `lang.isAvailable` is its runtime check. */
type UiLocale = NonNullable<Parameters<typeof localizeHref>[1]>['locale'];

/**
 * A link into the EDITION a highlight or note was made in, not the page's.
 *
 * Without this the Notebook sends the reader to a text their mark is not in —
 * the modern edition needs its query flag, and a mark made in another language
 * belongs to that language's pages. An edition whose language the UI does not
 * carry falls back to the current locale rather than building a URL for a
 * locale that does not route.
 */
export function editionHref(path: string, edition: string): string {
	const modern = edition === MODERN_EDITION;
	const withEdition = modern ? `${path}${path.includes('?') ? '&' : '?'}edition=modern` : path;
	const locale = modern ? 'en' : baseEdition(edition);
	// `isAvailable` IS the check the type wants; a content language can be
	// added in the admin without a frontend deploy, so the set of editions is
	// wider than the compiled locales and this cannot be proven statically.
	return lang.isAvailable(locale)
		? localizeHref(withEdition, { locale: locale as UiLocale })
		: localizeHref(withEdition);
}

/** Where a Notebook entry's source passage lives — built from its parts only. */
export function sourceHref(s: EntrySource): string {
	const path =
		s.kind === 'book'
			? `/books/${s.slug}/${s.order}?p=${s.p}`
			: s.kind === 'sermon'
				? `/sermons/${s.slug}?p=${s.p}`
				: `/authors/${s.slug}?p=${s.p}`;
	return editionHref(path, s.edition);
}
