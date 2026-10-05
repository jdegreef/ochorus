import { emblemForSermon } from '$lib/emblemNames';
import { EMBLEM_HUES } from '$lib/emblemHues';
import { inkSafe, tintable } from '$lib/coverArt';
import type { EmblemName } from '$lib/emblems';
import type { CoverFace, SermonSummary } from '$lib/library-public';

/**
 * A sermon's art, from its slug: which emblem it wears and the hue to tint with.
 *
 * The pairing is the point. `EMBLEM_HUES` holds the raw ink of each drawing, and
 * a caller that tints with it directly ships the bug `coverArt.tintable`
 * documents — the raven's slate at lightness 0.22 reads as untinted through a 9%
 * wash. That rule is stated once here rather than re-derived at each surface;
 * STYLE_GUIDE §Cards treats it as the rule for a sermon standing on its own.
 *
 * Its own module, not `emblemNames.ts`, which is deliberately import-free so the
 * card generators can load it under bare Node (`nodeLoadable.test.ts`) — a
 * runtime import of `./coverArt` there would stop them dead.
 */
export function sermonArt(slug: string): { emblem: EmblemName; hue: string } {
	const emblem = emblemForSermon(slug);
	return { emblem, hue: tintable(EMBLEM_HUES[emblem]) };
}

/**
 * A sermon as a `CoverFace`, so `<BookCover>` sets it on its own plate — the
 * resume card's 3:4 slot, the one place a sermon wears a cover (STYLE_GUIDE
 * §Cards). Through BookCover rather than a copy of its markup, so the plate,
 * the preacher's house style and the parity gate all hold for it unchanged.
 *
 * - No `cover_url`, so BookCover takes its no-file branch: `coverGradient` of
 *   `cover_color`, with the type drawn over it.
 * - `cover_color` is the sermon's own hue through `inkSafe`: `sermonArt` lifts
 *   it for a wash, and white type needs it floored the other way.
 * - The passage is the subtitle.
 * - The slug is namespaced (`sermon:`), because BookCover keys tables by BOOK
 *   slug — `BOOK_STYLE` among them — and a sermon sharing a book's slug must
 *   not wear that book's style.
 */
export function sermonCoverFace(sermon: SermonSummary): CoverFace {
	return {
		slug: `sermon:${sermon.slug}`,
		language: sermon.language,
		title: sermon.title,
		subtitle: sermon.scripture_ref,
		cover_title: '',
		cover_byline: '',
		cover_color: inkSafe(sermonArt(sermon.slug).hue),
		cover_url: '',
		series_position: null,
		author: {
			slug: sermon.author.slug,
			name: sermon.author.name,
			birth_year: sermon.author.birth_year
		}
	};
}
