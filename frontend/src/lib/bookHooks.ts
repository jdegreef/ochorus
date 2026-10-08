import { i18n } from './i18n.svelte';

/**
 * A book's one-line hook — an editor's line that sells the story rather than
 * the cover ("Amy Carmichael refused to make missions sound nice…"), shown on
 * the book cards of a hub with `hooks` (`$lib/audienceHub`). One catalogue key
 * per book slug, `audience_hook_<slug>`, in every catalogue (message parity
 * keeps them level); a book without one shows no line.
 */
export function hookFor(slug: string): string {
	const key = `audience.hook_${slug.replace(/-/g, '_')}`;
	return i18n.has(key) ? i18n.t(key) : '';
}
