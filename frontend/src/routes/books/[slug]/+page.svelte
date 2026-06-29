<script lang="ts">
	import type { BookDetail } from '$lib/library';
	import { getProgress } from '$lib/progress';
	import { readingMinutes, readingTime } from '$lib/reading';

	let { data } = $props();
	const book = $derived<BookDetail>(data.book);

	let resumeOrder = $state<number | null>(null);
	$effect(() => {
		resumeOrder = getProgress(book.slug);
	});

	const years = $derived(
		book.author.birth_year ? `${book.author.birth_year}–${book.author.death_year ?? ''}` : ''
	);

	const totalWords = $derived(book.chapters.reduce((sum, c) => sum + c.word_count, 0));
</script>

<svelte:head><title>{book.title} — {book.author.name} — Ochorus</title></svelte:head>

<div class="mx-auto max-w-3xl px-5 py-8">
	<a href="/" class="text-small text-muted">← Library</a>

	<header class="mt-5 flex flex-col gap-5 sm:flex-row sm:items-start">
		{#if book.cover_url}
			<img
				src={book.cover_url}
				alt="Cover of {book.title}"
				class="aspect-[3/4] w-32 shrink-0 rounded-card object-cover shadow-md"
			/>
		{:else}
			<div
				class="flex aspect-[3/4] w-32 shrink-0 items-end rounded-card p-3 shadow-md"
				style="background: linear-gradient(150deg, {book.cover_color || '#3b5bdb'}, #0008)"
			>
				<span style="font-family: var(--font-display)" class="text-base font-semibold text-white">
					{book.title}
				</span>
			</div>
		{/if}

		<div class="flex-1">
			<h1 class="text-h1">{book.title}</h1>
			{#if book.subtitle}<p class="mt-1 text-h3 text-muted">{book.subtitle}</p>{/if}
			<p class="mt-2 text-body">
				{book.author.name}{#if years}<span class="text-muted"> · {years}</span>{/if}
			</p>

			<div class="mt-5 flex flex-wrap items-center gap-3">
				{#if resumeOrder && resumeOrder > 1}
					<a href="/books/{book.slug}/{resumeOrder}" class="btn btn-primary">
						Continue · ch. {resumeOrder}
					</a>
					<a href="/books/{book.slug}/1" class="btn btn-ghost">Start over</a>
				{:else}
					<a href="/books/{book.slug}/1" class="btn btn-primary">Begin reading</a>
				{/if}
				{#if book.pdf_url}
					<a href={book.pdf_url} class="btn btn-ghost" target="_blank" rel="noreferrer">
						Download PDF
					</a>
				{/if}
				<span class="text-small text-muted">
					{book.chapter_count} chapters · {readingTime(totalWords)}
				</span>
			</div>
		</div>
	</header>

	{#if book.author.bio}
		<p class="mt-7 max-w-xl text-body text-muted">{book.author.bio}</p>
	{/if}

	<section class="mt-9">
		<h2 class="mb-3 text-h3">Contents</h2>
		<ol class="divide-y divide-border">
			{#each book.chapters as ch (ch.order)}
				<li>
					<a
						href="/books/{book.slug}/{ch.order}"
						class="flex items-baseline gap-3 py-2.5 hover:no-underline"
					>
						<span class="w-6 shrink-0 text-small text-muted">{ch.order}</span>
						<span class="flex-1 text-body text-text">{ch.title}</span>
						<span class="text-[0.8rem] text-muted">{readingMinutes(ch.word_count)} min</span>
					</a>
				</li>
			{/each}
		</ol>
	</section>

	{#if book.source_url}
		<p class="mt-8 text-[0.8rem] text-muted">
			Public domain. Source text from
			<a href={book.source_url} target="_blank" rel="noreferrer">the original edition</a>.
		</p>
	{/if}
</div>
