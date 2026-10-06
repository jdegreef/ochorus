<script lang="ts">
	// One topic pill — a theme's title and how many items it holds. Shared by the
	// home page's topic row (TopicChips) and the /quotes index's theme chips.
	// `class` adds to the pill's own classes (the home row's responsive caps).
	//
	// A library topic with curated art (TOPIC_META) also wears its emblem and a
	// wash of its accent, so the row reads as thirteen shelves rather than
	// thirteen grey buttons. The emblem is a static file (static/emblems/, the
	// one `npm run emblem:art` writes), not <Emblem>: that would pull all of
	// EMBLEM_ART into the prerendered home for thirteen 18px marks. The accent
	// only tints the ground and edge (via color-mix), never the text, so the
	// title keeps --text's contrast in every theme.
	import type { ClassValue } from 'svelte/elements';
	import { hydrateSrc } from '$lib/hydrateSrc';

	let {
		href,
		title,
		count,
		emblem,
		accent,
		class: extra
	}: {
		href: string;
		title: string;
		count: number;
		/** The topic's emblem name; it must be one `emblem:art` exports. */
		emblem?: string;
		accent?: string;
		class?: ClassValue;
	} = $props();
</script>

<a
	{href}
	class={[
		'topic-pill inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-4 py-2 text-small font-medium text-text hover:border-accent hover:text-accent hover:no-underline',
		emblem && 'has-emblem',
		extra
	]}
	style:--topic-accent={accent}
>
	{#if emblem}
		<img
			src="/emblems/{emblem}.svg"
			alt=""
			width="20"
			height="20"
			loading="lazy"
			use:hydrateSrc={{ src: `/emblems/${emblem}.svg` }}
		/>
	{/if}
	{title}
	<span class="text-eyebrow font-normal text-muted">{count}</span>
</a>

<style>
	/* Unlayered beats Tailwind's layered bg-surface / border-border, so the
	   wash wins on a pill with art and the plain pill keeps its utilities. */
	.has-emblem {
		padding-inline-start: 0.6rem;
		background: color-mix(in srgb, var(--topic-accent) 9%, var(--surface));
		border-color: color-mix(in srgb, var(--topic-accent) 28%, var(--border));
	}
	.has-emblem:hover {
		border-color: var(--accent);
	}
	img {
		flex: none;
	}
</style>
