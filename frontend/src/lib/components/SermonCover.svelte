<script lang="ts">
	import { coverGradient } from '$lib/coverArt';
	import { isLongTitle } from '$lib/coverCardMarkup';
	import { coverStyleFor, scriptOf } from '$lib/coverStyles';
	import { contentLang } from '$lib/reading';
	import { eraOf } from '$lib/eras';
	import { sermonArt } from '$lib/sermonArt';
	import type { SermonSummary } from '$lib/library-public';
	import './cover-type.css';
	import BrandMark from './BrandMark.svelte';

	/**
	 * A sermon set as a book cover, for the 3:4 slot of a resume card — the one
	 * surface where a sermon is given a cover (STYLE_GUIDE §Cards says why).
	 *
	 * It is BookCover's own plate, not a second drawing of one: the same
	 * `.cover-plate` / `.cover-type` classes from `cover-type.css`, the same
	 * house style for the preacher's century, the same long-title step and the
	 * same mark. Only the ground and the subtitle differ. The ground is
	 * `coverGradient` of the sermon's `sermonArt` hue, so it keeps the colour
	 * its plate and share card wear, and the passage sits where a subtitle
	 * would. No "Sermon" eyebrow: the card's caption already says so, and the
	 * one slot above the title (`.volume`) is drawn as a series numeral.
	 *
	 * Decorative (`aria-hidden`): the card beside it carries the title, the
	 * preacher and the passage as text.
	 */
	let { sermon }: { sermon: SermonSummary } = $props();

	const style = $derived(
		coverStyleFor(eraOf(sermon.author.birth_year), sermon.author.slug, sermon.slug)
	);
	const lang = $derived(contentLang(sermon.language));
	const script = $derived(scriptOf(lang));
	const blockDir = $derived(script === 'arabic' ? { dir: 'rtl' as const } : {});
</script>

<div
	class="relative aspect-[3/4] w-full overflow-hidden rounded-sm shadow-sm"
	aria-hidden="true"
	data-testid="sermon-cover"
>
	<div class="cover-plate" style="--plate: {coverGradient(sermonArt(sermon.slug).hue)}">
		<div
			class={[
				'cover-type',
				`style-${style}`,
				script && `script-${script}`,
				isLongTitle(sermon.title) && 'long-title'
			]}
			{...blockDir}
		>
			<div class="byline" dir="auto">{sermon.author.name}</div>
			<div class="middle">
				<div class="title" {lang} dir="auto">{sermon.title}</div>
				<div class="rule"></div>
				{#if sermon.scripture_ref}<div class="subtitle" {lang} dir="auto">
						{sermon.scripture_ref}
					</div>{/if}
			</div>
			<BrandMark height="13.7cqw" />
		</div>
	</div>
</div>
