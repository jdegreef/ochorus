<script lang="ts">
	import type { Snippet } from 'svelte';
	import { mediaFlag } from '$lib/mediaFlag.svelte';
	import { SHORT_TOUCH } from '$lib/breakpoints';

	/**
	 * A shelf's controls, pinned under the app nav so they come WITH you down a
	 * long list — Books, Sermons, Biographies and the A–Z. One copy of the sticky
	 * offset, the bottom rule and the height measurement each of them used to
	 * hand-roll.
	 *
	 * `pinned` is the height jump targets have to clear: the measured bar while
	 * it pins, 0 while it doesn't. The page adds it to the nav for its
	 * `--pinned-offset` (`calc(var(--appnav-h, 0px) + {pinned}px)`), which group
	 * headings, sticky era headings and every `scroll-margin-top` read.
	 *
	 * `pin="compact"` is for a row of many controls (Books, Sermons): it pins
	 * below sm (one line — search + Filters) and from md, and scrolls away
	 * between sm and md, where the inline row wraps too tall to pin.
	 *
	 * On a SHORT touch screen (under 500px tall — a phone held sideways; the
	 * same test as the tab bar's) no bar pins,
	 * whatever `pin` says: with the nav above it, a ~90px bar left a 390px-tall
	 * landscape phone about half its height to read in.
	 */
	let {
		pinned = $bindable(0),
		el = $bindable(),
		pin = 'always',
		class: cls = '',
		children
	}: {
		pinned?: number;
		el?: HTMLElement;
		pin?: 'always' | 'compact';
		class?: string;
		children: Snippet;
	} = $props();

	let height = $state(0);
	// Read after hydration: the page is prerendered, so the static HTML
	// assumes the bar pins (the common case at both ends of the range). The
	// queries match the stylesheet's below.
	const unpinQ = mediaFlag(() =>
		pin === 'compact' ? `(min-width: 640px) and (max-width: 767.98px), ${SHORT_TOUCH}` : SHORT_TOUCH
	);
	$effect(() => {
		pinned = unpinQ.matches ? 0 : height;
	});
</script>

<div
	bind:this={el}
	bind:clientHeight={height}
	class="filter-bar z-(--z-pinned) -mx-5 border-b border-border bg-bg px-5 pb-2.5 pt-3 {cls}"
	class:filter-bar--compact={pin === 'compact'}
>
	{@render children()}
</div>

<style>
	.filter-bar {
		position: sticky;
		top: var(--appnav-h, 0px);
	}
	@media (min-width: 640px) and (max-width: 767.98px) {
		.filter-bar--compact {
			position: static;
		}
	}
	@media (max-height: 499.98px) and (pointer: coarse) {
		.filter-bar {
			position: static;
		}
	}
</style>
