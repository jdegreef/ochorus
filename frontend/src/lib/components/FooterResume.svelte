<script lang="ts">
	/**
	 * The footer's "Continue reading" card: the reader's current book as the
	 * same WorkCard the home strip draws, under its eyebrow. Its own component
	 * so the root layout can import it lazily — WorkCard pulls in the whole
	 * cover stack, which no page should pay for until a signed-in reader
	 * scrolls near the footer with a book open.
	 */
	import WorkCard from '$lib/components/WorkCard.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import type { ResumeBook } from '$lib/resumeItems';

	let { item }: { item: ResumeBook } = $props();
</script>

<div class="footer-resume">
	<p class="eyebrow mb-2 text-accent">{i18n.t('continue.title')}</p>
	<WorkCard {item} />
</div>

<style>
	/* Sit on the page ground like the footer's other cards: WorkCard has no
	   fill and hovers to surface-2, which IS the footer's tint, so without this
	   it would read as a hole in the row and give no hover feedback. */
	.footer-resume :global(a) {
		background: var(--surface);
	}
	.footer-resume :global(a:hover) {
		background: var(--surface-2);
	}
</style>
