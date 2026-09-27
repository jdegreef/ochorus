/**
 * Where the home page's share card for one interface locale lives.
 *
 * One card per locale, because a card with words in it serves one language:
 * `scripts/generate-home-og.mjs` draws each from that locale's own copy and its
 * own editions' covers, and writes it here. Said once so the page that names a
 * card and the script that draws it cannot disagree about the path.
 */
export function homeShareCardUrl(locale: string): string {
	return `/og/home/${locale}.jpg`;
}
