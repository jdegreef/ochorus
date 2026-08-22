import { emblemForSermon } from '$lib/emblemNames';
import { EMBLEM_HUES } from '$lib/emblemHues';
import { tintable } from '$lib/coverArt';
import type { EmblemName } from '$lib/emblems';

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
