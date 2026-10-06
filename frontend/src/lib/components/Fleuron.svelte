<script lang="ts">
	import type { Ornament } from '$lib/sections';

	/**
	 * A printer's ornament: a small device between two hairlines, in gold. Book
	 * pages mark a title or a break this way; the site used empty space for both.
	 * Each library section has its own device ($lib/sections SECTION_MARKS) — the
	 * leaf is the house one, for every page that is not a section's.
	 *
	 * Gold here is what STYLE_GUIDE §1 says gold is for — ornament, never a
	 * message — so it carries no meaning and is hidden from assistive tech.
	 * Every device is symmetric, so none needs mirroring in a right-to-left locale.
	 */
	let { ornament = 'leaf' }: { ornament?: Ornament } = $props();
</script>

<div class="fleuron" aria-hidden="true">
	<span></span>
	<!-- Round joins for the sections' devices; the house leaf keeps its sharp tips. -->
	<svg
		viewBox="0 0 24 24"
		width="22"
		height="22"
		fill="none"
		stroke="currentColor"
		stroke-width="1.4"
		stroke-linecap="round"
		stroke-linejoin={ornament === 'leaf' ? undefined : 'round'}
	>
		{#if ornament === 'lamp'}
			<path d="M12 2.5c-1.6 2-2.2 3.6-2.2 5a2.2 2.2 0 0 0 4.4 0c0-1.4-.6-3-2.2-5z" />
			<path d="M12 9.7v2.8" />
			<path d="M4.5 12.5h15c0 3-3.4 5-7.5 5s-7.5-2-7.5-5z" />
			<path d="M9 21h6M12 17.5V21" />
		{:else if ornament === 'anchor'}
			<circle cx="12" cy="4.2" r="1.7" />
			<path d="M12 5.9V20.5M8.3 9h7.4" />
			<path d="M5 14.5c0 3.5 3 6 7 6s7-2.5 7-6" />
			<path d="M3.4 16l1.6-1.5 1.6 1.5M17.4 16l1.6-1.5 1.6 1.5" />
		{:else if ornament === 'vine'}
			<path d="M12 21.5V3" />
			<path d="M12 8.5C10 6 7 5.8 5.8 7.3 7 9.6 10 10.2 12 8.5zM12 8.5c2-2.5 5-2.7 6.2-1.2-1.2 2.3-4.2 2.9-6.2 1.2z" />
			<path d="M12 15c-2.3-2.3-5.4-2-6.6-.4 1.4 2.1 4.5 2.6 6.6.4zM12 15c2.3-2.3 5.4-2 6.6-.4-1.4 2.1-4.5 2.6-6.6.4z" />
		{:else if ornament === 'dove'}
			<circle cx="12" cy="19.2" r="1.5" />
			<path d="M12 17.7c-1.3-1.8-1.6-5-1-7.6.3-1.3 1.7-1.3 2 0 .6 2.6.3 5.8-1 7.6z" />
			<path d="M11.1 11C8.8 9 5.4 8.5 2.3 9.8c1.6 1.5 3.7 2.3 5.6 2.3-1 1-1.6 2.1-1.6 3.3 2-.2 3.7-1.3 4.8-3" />
			<path d="M12.9 11c2.3-2 5.7-2.5 8.8-1.2-1.6 1.5-3.7 2.3-5.6 2.3 1 1 1.6 2.1 1.6 3.3-2-.2-3.7-1.3-4.8-3" />
			<path d="M11.3 8.6 10 4.3l2 1.2 2-1.2-1.3 4.3" />
		{:else if ornament === 'laurel'}
			<path d="M11 20.5C6.5 19 4.5 14 5.5 8 M5.5 8c-1.6-.8-2.2-2.2-1.8-3.6 1.4.4 2.2 1.8 1.8 3.6z M5.2 11.5c-1.8-.2-2.8-1.3-2.9-2.8 1.6 0 2.7 1.1 2.9 2.8z M6.2 15c-1.8.3-3-.5-3.5-1.9 1.6-.4 2.9.4 3.5 1.9z M8.2 18c-1.6.8-3 .4-3.8-.8 1.4-.8 2.9-.5 3.8.8z M5.6 10.5c1.4-1 2.8-1 3.8-.1-1.2 1-2.6 1.1-3.8.1z M7 14.2c1.5-.8 2.9-.6 3.7.4-1.3.8-2.7.7-3.7-.4z" />
			<path d="M 13 20.5 C 17.5 19 19.5 14 18.5 8 M 18.5 8 c 1.6 -0.8 2.2 -2.2 1.8 -3.6 -1.4 0.4 -2.2 1.8 -1.8 3.6 z M 18.8 11.5 c 1.8 -0.2 2.8 -1.3 2.9 -2.8 -1.6 0 -2.7 1.1 -2.9 2.8 z M 17.8 15 c 1.8 0.3 3 -0.5 3.5 -1.9 -1.6 -0.4 -2.9 0.4 -3.5 1.9 z M 15.8 18 c 1.6 0.8 3 0.4 3.8 -0.8 -1.4 -0.8 -2.9 -0.5 -3.8 0.8 z M 18.4 10.5 c -1.4 -1 -2.8 -1 -3.8 -0.1 1.2 1 2.6 1.1 3.8 0.1 z M 17 14.2 c -1.5 -0.8 -2.9 -0.6 -3.7 0.4 1.3 0.8 2.7 0.7 3.7 -0.4 z" />
		{:else}
			<path d="M12 2.5c-4.5 4.5-4.5 14.5 0 19 4.5-4.5 4.5-14.5 0-19z" />
			<path d="M12 6v12" />
		{/if}
	</svg>
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
	.fleuron span {
		flex: 1;
		height: 1px;
		background: currentColor;
		opacity: 0.45;
	}
</style>
