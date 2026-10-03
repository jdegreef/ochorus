<script lang="ts">
	/**
	 * Jump to a letter on an alphabetical list — the A–Z index and Biographies
	 * sorted by name. The whole alphabet always shows, so the rail's shape never
	 * changes with the filter; letters with nobody under them are dimmed.
	 *
	 * Two ways to land, one look:
	 * - `href` — real anchors, for a list whose every section is in the HTML
	 *   (the A–Z: complete by design, so each `#letter-` target always exists);
	 * - `onjump` — buttons, for a PAGED list where a late letter's row may not
	 *   be painted yet (Biographies: reveal its page first, then scroll — an
	 *   anchor there was a dangling fragment the prerender crawler caught).
	 *
	 * `active` lights the letter the reader is in. On a phone the rail is one
	 * row that swipes sideways; from sm up it wraps.
	 */
	let {
		letters,
		present,
		active = '',
		href,
		onjump,
		label,
		el = $bindable(),
		class: cls = ''
	}: {
		letters: string[];
		/** Letters that have someone under them. */
		present: (letter: string) => boolean;
		active?: string;
		href?: (letter: string) => string;
		onjump?: (letter: string) => void;
		label: string;
		el?: HTMLElement;
		class?: string;
	} = $props();
</script>

<nav
	bind:this={el}
	class="az-rail flex max-w-full gap-x-0.5 gap-y-0.5 overflow-x-auto text-small [scrollbar-width:none] sm:flex-wrap sm:overflow-visible {cls}"
	aria-label={label}
>
	{#each letters as letter (letter)}
		{#if !present(letter)}
			<span class="az-letter text-muted opacity-40" aria-hidden="true">{letter}</span>
		{:else if href}
			<a
				href={href(letter)}
				class="az-letter az-live"
				class:az-current={active === letter}
				aria-current={active === letter ? 'location' : undefined}>{letter}</a
			>
		{:else}
			<button
				type="button"
				class="az-letter az-live"
				class:az-current={active === letter}
				onclick={() => onjump?.(letter)}>{letter}</button
			>
		{/if}
	{/each}
</nav>

<style>
	.az-letter {
		flex-shrink: 0;
		padding: 0.125rem 0.375rem;
		border: 0;
		border-radius: var(--radius-sm);
		background: none;
		font: inherit;
		line-height: inherit;
	}
	.az-live {
		font-weight: 600;
		color: var(--accent);
		cursor: pointer;
		text-decoration: none;
	}
	.az-live:hover {
		background: var(--accent-soft);
	}
	/* The letter you are scrolled into. */
	.az-current,
	.az-current:hover {
		background: var(--accent);
		color: var(--accent-contrast);
	}
	/* On a touch phone the letters take a full-height target; the strip scrolls
	   sideways there, so width stays letter-sized. Not on a touch tablet: from
	   sm the strip wraps, and 44px rows would swell the pinned bar. */
	@media (pointer: coarse) and (max-width: 639.98px) {
		.az-live {
			display: inline-flex;
			align-items: center;
			justify-content: center;
			min-width: 2.25rem;
			min-height: 2.75rem;
		}
	}
</style>
