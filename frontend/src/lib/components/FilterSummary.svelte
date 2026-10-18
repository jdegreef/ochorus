<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import type { FilterChip } from '$lib/filterChips';

	/**
	 * "You are looking at 12 of 30 — clear the filters."
	 *
	 * The three filterable shelves each answered this differently, and one of
	 * them not at all: Books showed no count once you filtered it, so a search
	 * that matched nine of fifty-nine looked exactly like a library of nine.
	 * Sermons showed "9 sermons match" but offered no way back. Biographies had
	 * the full sentence, tucked under the Show-more button at the very bottom of
	 * the page, where you would only find it after scrolling past everything the
	 * filter had left.
	 *
	 * `aria-live="polite"` because the whole point is that it changes as you
	 * type, and a reader who cannot see the shelf shrink needs to be told.
	 */
	let {
		shown,
		total,
		template,
		onClear,
		chips = [],
		class: klass = ''
	}: {
		shown: number;
		total: number;
		/** The localized sentence, with `%shown%` and `%total%` placeholders. */
		template: string;
		/** Omit when there is nothing to clear (the page decides what "filtered" means). */
		onClear?: () => void;
		/**
		 * The filters currently narrowing the shelf, each removable on its own.
		 * The free-text query and topic don't show their value anywhere else (a
		 * <select> does), so they'd otherwise be applied but invisible. Empty on
		 * shelves that surface their active filters inline (Plans' length row).
		 */
		chips?: FilterChip[];
		/** Added to the layout classes — the biographies bar positions its copy. */
		class?: string;
	} = $props();

	const t = i18n.t;
	const text = $derived(
		template.replace('%shown%', String(shown)).replace('%total%', String(total))
	);
</script>

<div class="flex flex-wrap items-center gap-x-3 gap-y-1.5 {klass}">
	<p class="text-small text-muted" aria-live="polite">{text}</p>
	{#if chips.length}
		<span class="flex flex-wrap gap-1.5">
			{#each chips as chip (chip.kind)}
				<span class="active-filter">
					{chip.label}
					<button type="button" onclick={chip.onRemove} aria-label={t('common.removeFilter')}
						>&times;</button
					>
				</span>
			{/each}
		</span>
	{/if}
	{#if onClear}
		<button class="text-small font-semibold text-accent hover:underline" onclick={onClear}>
			{t('common.clearFilters')}
		</button>
	{/if}
</div>

<style>
	/* Moved out of app.css (only this component uses it), so the site-wide
	   sheet stays smaller (INP). :global keeps the selector as it was. */
	:global {
		/* A currently-applied filter, surfaced so it can be seen and lifted one at a
		   time — the book scope and length live in <select>s that show their own value,
		   but the free-text query and the topic did not read back anywhere. Tinted like
		   an active .chip; the × removes just this one, while "Clear filters" still
		   drops them all. */
		.active-filter {
			display: inline-flex;
			align-items: center;
			gap: 0.15rem;
			border: 1px solid var(--accent-soft-border);
			border-radius: 999px;
			background: var(--accent-soft);
			padding-block: 0.2rem;
			padding-inline: 0.7rem 0.35rem;
			font-size: var(--fs-small);
			line-height: 1.4;
			color: var(--accent);
		}
		.active-filter button {
			display: inline-flex;
			align-items: center;
			justify-content: center;
			width: 1.35rem;
			height: 1.35rem;
			border: none;
			border-radius: 999px;
			background: none;
			color: inherit;
			font-size: var(--fs-body);
			line-height: 1;
			cursor: pointer;
			opacity: 0.65;
		}
		.active-filter button:hover {
			opacity: 1;
			background: color-mix(in srgb, var(--accent) 16%, transparent);
		}
	}
</style>
