/**
 * Escape the five XML predefined entities, for text and attribute values.
 *
 * Shared by the two XML documents the site emits — the feed and the sitemap —
 * which each had, or were about to have, their own copy with a different idea
 * of which characters mattered.
 */
export function xmlEscape(s: string): string {
	return s
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&apos;');
}
