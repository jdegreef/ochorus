import { SITE_URL } from './config';

/** Make a path absolute against the site origin (pass-through for full URLs). */
export function absUrl(path: string): string {
	if (!path) return SITE_URL;
	if (/^https?:\/\//.test(path)) return path;
	return SITE_URL + (path.startsWith('/') ? path : `/${path}`);
}

/**
 * A ready-to-inject <script type="application/ld+json"> string for use inside
 * <svelte:head> via {@html …}. `<` is escaped so book/author text can never
 * break out of the script tag.
 */
export function jsonLd(data: unknown): string {
	const json = JSON.stringify(data).replace(/</g, '\\u003c');
	return `<script type="application/ld+json">${json}</script>`;
}

/** schema.org BreadcrumbList from [name, url] pairs (urls made absolute). */
export function breadcrumb(items: { name: string; url: string }[]) {
	return {
		'@context': 'https://schema.org',
		'@type': 'BreadcrumbList',
		itemListElement: items.map((it, i) => ({
			'@type': 'ListItem',
			position: i + 1,
			name: it.name,
			item: absUrl(it.url)
		}))
	};
}
