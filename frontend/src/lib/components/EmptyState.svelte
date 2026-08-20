<script lang="ts">
	import type { Snippet } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import { i18n } from '$lib/i18n.svelte';

	/**
	 * The one "nothing here" panel for a browse surface.
	 *
	 * The five browse pages each drew their own: Books a bordered card with a
	 * button, Biographies a bare centred block, Sermons and Topics and Plans a
	 * single line of muted body text with no affordance at all. The same
	 * situation therefore looked like a designed state on one page and like a
	 * rendering failure on another.
	 *
	 * `onRetry` rather than a snippet for the commonest case: four callers were
	 * about to write out the same three lines of `invalidateAll()` button, and
	 * import `invalidateAll` to do it.
	 */
	let {
		message,
		onRetry,
		action
	}: {
		/** What is (not) here, in the reader's language. */
		message: string;
		/** Show a Try again that re-runs the page's load — for a failed fetch. */
		onRetry?: boolean;
		/**
		 * Anything else: a link to the English library, a clear-filters button.
		 * Pass `undefined` rather than a snippet that renders nothing, or the
		 * panel keeps the space the action would have taken.
		 */
		action?: Snippet;
	} = $props();

	const t = i18n.t;
</script>

<div class="rounded-card border border-border bg-surface p-8 text-center">
	<p class="text-body text-text">{message}</p>
	{#if onRetry}
		<button class="btn btn-primary mt-4" onclick={() => invalidateAll()}>{t('error.tryAgain')}</button>
	{:else if action}
		<div class="mt-4">{@render action()}</div>
	{/if}
</div>
