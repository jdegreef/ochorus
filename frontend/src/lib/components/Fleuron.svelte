<script lang="ts">
	import type { Ornament } from '$lib/contentNav';

	/**
	 * A printer's ornament: a small device between two hairlines, in gold. Book
	 * pages mark a title or a break this way; the site used empty space for both.
	 *
	 * The house leaf is drawn inline. A library section's own device (its
	 * `ornament` in PRIMARY_NAV) is a static file, `/marks/ornament-<name>.svg`,
	 * painted in gold through a CSS mask — so only the five section pages that
	 * show one ever fetch it, and the home hero carries none of their paths.
	 *
	 * Gold here is what STYLE_GUIDE §1 says gold is for — ornament, never a
	 * message — so it carries no meaning and is hidden from assistive tech.
	 * Every device is symmetric, so none needs mirroring in a right-to-left locale.
	 */
	let { ornament = 'leaf' }: { ornament?: Ornament } = $props();
</script>

<div class="fleuron" aria-hidden="true">
	<span></span>
	{#if ornament === 'leaf'}
		<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round">
			<path d="M12 2.5c-4.5 4.5-4.5 14.5 0 19 4.5-4.5 4.5-14.5 0-19z" />
			<path d="M12 6v12" />
		</svg>
	{:else}
		<i class="fleuron-device" style:--device="url('/marks/ornament-{ornament}.svg')"></i>
	{/if}
	<span></span>
</div>

<style>
	.fleuron {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		width: 10rem;
		color: var(--gold);
	}
	/* The device file is black line art; the mask lets currentColor (gold,
	   per theme) show through its strokes. */
	.fleuron-device {
		width: 22px;
		height: 22px;
		flex-shrink: 0;
		background: currentColor;
		-webkit-mask: var(--device) center / contain no-repeat;
		mask: var(--device) center / contain no-repeat;
	}
	.fleuron span {
		flex: 1;
		height: 1px;
		background: currentColor;
		opacity: 0.45;
	}
</style>
