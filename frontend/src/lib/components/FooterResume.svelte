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

<div>
	<p class="eyebrow mb-2 text-accent">{i18n.t('continue.title')}</p>
	<WorkCard {item} />
</div>
