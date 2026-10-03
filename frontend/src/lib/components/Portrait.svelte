<script lang="ts">
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { i18n } from '$lib/i18n.svelte';
	import { initials, portraitPosition, portraitSrcset } from '$lib/portraits';

	/**
	 * A writer's round portrait, or their initials in an accent-soft circle when
	 * there is no free image. One recipe — the srcset, the hydrate-time src swap
	 * (`hydrateSrc`), the per-writer crop (`portraitPosition`), the alt text and
	 * the fallback — where every card used to carry its own copy of all of it.
	 *
	 * The caller owns the box: pass its size (and any responsive size) in
	 * `class`, which lands on whichever element renders, and `px` for the
	 * largest rendered size so the browser picks the right srcset candidate.
	 */
	let {
		slug,
		name,
		url,
		px,
		class: klass = '',
		initialsClass = 'text-small',
		tone = 'gray',
		decorative = false,
		loading = 'lazy',
		fallback = true,
		position
	}: {
		/** Picks the writer's crop (portraitPosition). */
		slug: string;
		/** For the alt text and the initials. */
		name: string;
		url?: string | null;
		/** Largest rendered size in CSS px — `sizes`, `width`, `height`. */
		px: number;
		/** Size and placement classes, applied to the image or the initials. */
		class?: string;
		/** Text size of the initials fallback. */
		initialsClass?: string;
		/** 'gray' always grayscale; 'hover' warms to colour on a parent `.group`
		 *  hover; 'color' untouched. */
		tone?: 'gray' | 'hover' | 'color';
		/** Beside the writer's name already: empty alt, initials hidden from AT. */
		decorative?: boolean;
		loading?: 'lazy' | 'eager';
		/** Render nothing (rather than initials) when there is no image. */
		fallback?: boolean;
		/** An explicit object-position, overriding the slug's crop. */
		position?: string;
	} = $props();

	const t = i18n.t;
	const TONE = {
		gray: 'grayscale',
		hover: 'grayscale transition-[filter] duration-[var(--duration-base)] group-hover:grayscale-0',
		color: ''
	};
</script>

{#if url}
	{@const source = { src: url, srcset: portraitSrcset(url) }}
	<img
		src={source.src}
		srcset={source.srcset}
		use:hydrateSrc={source}
		sizes="{px}px"
		width={px}
		height={px}
		alt={decorative ? '' : `${t('a11y.portraitOf')} ${name}`}
		{loading}
		class="shrink-0 rounded-full border border-border object-cover {TONE[tone]} {klass}"
		style="object-position: {position ?? portraitPosition(slug)}"
	/>
{:else if fallback}
	<span
		class="font-display flex shrink-0 items-center justify-center rounded-full bg-accent-soft font-semibold text-accent {initialsClass} {klass}"
		aria-hidden={decorative || undefined}>{initials(name)}</span
	>
{/if}
