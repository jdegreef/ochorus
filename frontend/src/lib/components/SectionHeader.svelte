<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { sectionDest, type NavSection } from '$lib/contentNav';
	/**
	 * A section title with an optional "see all" link beside it.
	 *
	 * Five places wrote this row by hand — three on the home page, plus
	 * Recommended and Your plans — with `mb-6` on four of them and `mb-4` on the
	 * fifth, and none of them allowed to wrap. On a phone that meant the link
	 * broke across three lines beside a two-line heading ("All / books / →"),
	 * because `justify-between` on a nowrap flex row squeezes the shorter child
	 * until it has nowhere left to go.
	 *
	 * Wrapping is the whole point of having this in one place: the link drops to
	 * its own line when the title needs the width, and sits beside it when it
	 * doesn't. The bottom margin is fixed rather than a prop — mb-4 on one of
	 * the five was the drift, not a requirement.
	 *
	 * A shelf that belongs to a library section passes `section`, and its title
	 * wears that section's nav icon in the section's hue — so "Continue
	 * reading" reads as Books and "Your plans" as Plans at a glance, the way
	 * the top nav already colours them.
	 */
	let {
		title,
		href = '',
		linkText = '',
		subtitle = '',
		section
	}: {
		title: string;
		/** Optional one-line standfirst under the title (kept with it when the link wraps). */
		subtitle?: string;
		/** Omit for a heading with no link. */
		href?: string;
		/** Link label; the arrow is added here so every one of them matches. */
		linkText?: string;
		/** The library section this shelf belongs to, if any. */
		section?: NavSection;
	} = $props();
</script>

{#snippet heading()}
	<h2 class={section ? 'text-h2 section-header-title flex items-start gap-3' : 'text-h2'} data-section={section}>
		{#if section}<Icon name={sectionDest(section).icon} size={22} />{/if}{title}
	</h2>
{/snippet}

<div class="mb-6 flex flex-wrap items-end justify-between gap-x-4 gap-y-1">
	{#if subtitle}
		<div>
			{@render heading()}
			<p class="mt-1 text-small text-muted">{subtitle}</p>
		</div>
	{:else}
		{@render heading()}
	{/if}
	{#if href && linkText}
		<a {href} class="whitespace-nowrap text-small font-semibold text-accent">{linkText} <Arrow /></a>
	{/if}
</div>

<style>
	/* The icon sits centred on the title's FIRST line, however many lines a
	   long title (a Luganda shelf name, say) wraps to: one line-height (lh)
	   less the icon's 22px, halved. */
	.section-header-title :global(svg) {
		flex-shrink: 0;
		margin-top: calc((1lh - 22px) / 2);
	}
</style>
