<script lang="ts">
	import type { Chapter } from '$lib/library';
	import { saveProgress, getReadingScale, saveReadingScale } from '$lib/progress';

	let { data } = $props();
	const chapter = $derived(data.chapter as Chapter);
	const slug = $derived(data.slug as string);

	let scale = $state(1);
	$effect(() => {
		scale = getReadingScale();
	});

	// Persist reading position whenever the chapter changes, and scroll to top.
	$effect(() => {
		saveProgress(slug, chapter.order);
		if (typeof window !== 'undefined') window.scrollTo(0, 0);
	});

	function setScale(next: number) {
		scale = Math.min(1.6, Math.max(0.8, Math.round(next * 10) / 10));
		saveReadingScale(scale);
	}
</script>

<svelte:head><title>{chapter.title} — {chapter.book_title} — Ochorus</title></svelte:head>

<!-- Reader top bar: back to book, font controls -->
<div class="sticky top-0 z-10 border-b border-border bg-bg/90 backdrop-blur">
	<div class="mx-auto flex max-w-2xl items-center justify-between px-5 py-2.5">
		<a href="/books/{slug}" class="text-small text-muted hover:text-text">
			← {chapter.book_title}
		</a>
		<div class="flex items-center gap-1">
			<button class="btn btn-ghost !px-2.5 !py-1" onclick={() => setScale(scale - 0.1)} aria-label="Smaller text">A−</button>
			<button class="btn btn-ghost !px-2.5 !py-1 !text-base" onclick={() => setScale(scale + 0.1)} aria-label="Larger text">A+</button>
		</div>
	</div>
</div>

<article class="mx-auto max-w-2xl px-5 py-10" style="--reading-scale: {scale}">
	<p class="mb-1 text-small uppercase tracking-wider text-muted">Chapter {chapter.order}</p>
	<h1 class="text-h1 mb-8">{chapter.title}</h1>

	<!-- Body HTML is cleaned server-side to a safe tag subset on ingest. -->
	<div class="reading">{@html chapter.body_html}</div>

	<nav class="mt-14 flex items-stretch justify-between gap-3 border-t border-border pt-6">
		{#if chapter.prev}
			<a href="/books/{slug}/{chapter.prev.order}" class="btn btn-ghost flex-1 !flex-col !items-start gap-0.5 text-left">
				<span class="text-[0.7rem] uppercase tracking-wider text-muted">Previous</span>
				<span class="text-small">{chapter.prev.title}</span>
			</a>
		{:else}
			<span class="flex-1"></span>
		{/if}
		{#if chapter.next}
			<a href="/books/{slug}/{chapter.next.order}" class="btn btn-primary flex-1 !flex-col !items-end gap-0.5 text-right">
				<span class="text-[0.7rem] uppercase tracking-wider opacity-75">Next</span>
				<span class="text-small">{chapter.next.title}</span>
			</a>
		{:else}
			<a href="/books/{slug}" class="btn btn-ghost flex-1 text-center">Back to contents</a>
		{/if}
	</nav>
</article>
