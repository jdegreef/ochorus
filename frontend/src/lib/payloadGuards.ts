/**
 * Checking that the API sent what the reader is about to render.
 *
 * Every `apiFetch<T>` is a blind `as T`. TypeScript checks that the code agrees
 * with the interface; nothing checks that the SERVER does. The API and the
 * reader deploy as separate Render services, so there is always a window where
 * one is ahead of the other, and inside it a renamed DRF field ships a page that
 * renders `undefined` — no error, no console warning, no report. Just a chapter
 * with no prose in it, live, until a person happens to look.
 *
 * WHAT IS GUARDED, AND WHAT IS NOT. Only the fields that make the page worth
 * loading: the prose, the title, the identity. Not `available_languages`, not
 * `artwork_credit`, not `topics` — those degrade to a missing hreflang or an
 * absent credit line, and taking a working chapter down over a cosmetic loss
 * would be a worse trade than the silence this replaces. The rule is: if the
 * page would be a lie without it, guard it.
 *
 * A failure throws, and that is the point. `orNotFound` re-throws anything that
 * is not a 404, so SvelteKit renders the error page rather than a half-page, and
 * `hooks.client.ts` reports it — with the release it came from, now that
 * releases are tagged. Loud and dated beats silent.
 */

/** The kinds a guarded field may be. Deliberately coarse: this is a shape
 *  check against a renamed or dropped field, not a validator. */
export type FieldKind = 'string' | 'number' | 'boolean' | 'array';

/** A payload that does not carry what the page needs. */
export class PayloadError extends Error {
	constructor(
		/** What was being fetched, for the report: "chapter humility/3". */
		readonly what: string,
		/** The fields that were missing or the wrong kind. */
		readonly fields: string[]
	) {
		super(
			`The API sent a ${what} without ${fields.join(', ')}. ` +
				'This usually means the API and the reader are on different releases.'
		);
		this.name = 'PayloadError';
	}
}

function kindOf(value: unknown): FieldKind | 'other' {
	if (Array.isArray(value)) return 'array';
	const t = typeof value;
	return t === 'string' || t === 'number' || t === 'boolean' ? t : 'other';
}

/**
 * Return `value` as `T`, or throw naming every field that failed.
 *
 * Every failing field at once, not the first: a version skew usually renames
 * several at a time, and one report that lists them all is one deploy to fix
 * rather than three.
 */
export function requireFields<T>(
	what: string,
	value: unknown,
	required: Record<string, FieldKind>
): T {
	if (!value || typeof value !== 'object' || Array.isArray(value)) {
		throw new PayloadError(what, ['a JSON object']);
	}
	const row = value as Record<string, unknown>;
	const bad = Object.entries(required)
		.filter(([field, kind]) => kindOf(row[field]) !== kind)
		.map(([field, kind]) => `${field} (${kind})`);
	if (bad.length) throw new PayloadError(what, bad);
	return value as T;
}

/**
 * A chapter with no `body_html` is a blank page where the book should be —
 * the single most valuable thing this catches. The rest identify it: without
 * them the reader cannot tell which chapter of which book they are looking at,
 * and the resume anchor is keyed on `order`.
 *
 * `title` is checked for TYPE, not content: a chapter legitimately has an empty
 * title (the content audit flags those as a quality finding, not a defect), so
 * requiring a non-empty string here would reject prose that reads fine.
 */
export const CHAPTER_FIELDS: Record<string, FieldKind> = {
	order: 'number',
	title: 'string',
	body_html: 'string',
	book_title: 'string',
	book_slug: 'string',
	author_name: 'string'
};

/**
 * A book detail page is its identity plus its table of contents. Without
 * `chapters` there is nothing to open, which reads as a published book nobody
 * can get into.
 */
export const BOOK_FIELDS: Record<string, FieldKind> = {
	slug: 'string',
	title: 'string',
	language: 'string',
	chapters: 'array'
};

/** A sermon is its prose and the line that says whose it is. */
export const SERMON_FIELDS: Record<string, FieldKind> = {
	slug: 'string',
	title: 'string',
	language: 'string',
	body_html: 'string',
	author_name: 'string'
};
