<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';

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
		class: klass = ''
	}: {
		shown: number;
		total: number;
		/** The localized sentence, with `%shown%` and `%total%` placeholders. */
		template: string;
		/** Omit when there is nothing to clear (the page decides what "filtered" means). */
		onClear?: () => void;
		/** Added to the layout classes — the biographies bar positions its copy. */
		class?: string;
	} = $props();

	const t = i18n.t;
	const text = $derived(
		template.replace('%shown%', String(shown)).replace('%total%', String(total))
	);
</script>

<div class="flex flex-wrap items-baseline gap-x-3 gap-y-1 {klass}">
	<p class="text-small text-muted" aria-live="polite">{text}</p>
	{#if onClear}
		<button class="text-small font-semibold text-accent hover:underline" onclick={onClear}>
			{t('common.clearFilters')}
		</button>
	{/if}
</div>
