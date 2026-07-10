<script lang="ts">
	import { onMount } from 'svelte';
	import { listSermons, type Sermon, type SermonSummary } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { readingTime } from '$lib/reading';
	import { getLang } from '$lib/lang.svelte';
	import { listen } from '$lib/listen.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import ReaderControls from '$lib/components/ReaderControls.svelte';
	import ListenBar from '$lib/components/ListenBar.svelte';

	let { data } = $props();
	const sermon = $derived(data.sermon as Sermon);
	const t = i18n.t;

	let body = $state<HTMLElement | undefined>();
	// Other sermons on the same Bible book, fetched client-side (page is
	// prerendered; the list is small and cached by the browser).
	let related = $state<SermonSummary[]>([]);

	/** "1 Peter 2:7" -> "1 Peter"; "Matthew 11:28" -> "Matthew". */
	const refBook = (ref: string) => ref.match(/^(\d?\s?[A-Za-z]+)/)?.[1]?.trim() ?? '';
	const book = $derived(refBook(sermon.scripture_ref || ''));

	onMount(() => {
		readerPrefs.init();
		if (book) {
			listSermons(getLang())
				.then((all) => {
					related = all.filter(
						(s) => s.slug !== sermon.slug && refBook(s.scripture_ref || '') === book
					);
				})
				.catch(() => (related = []));
		}
	});

	/** Read the sermon aloud from the top. */
	function startListening() {
		if (!body) return;
		const paragraphs = [...body.children].map((el) => (el as HTMLElement).innerText);
		listen.start(paragraphs, 0, getLang());
	}

	const canonical = $derived(`${SITE_URL}/sermons/${sermon.slug}`);
	const preachedYear = $derived(sermon.preached_on ? sermon.preached_on.slice(0, 4) : '');
</script>

<svelte:head>
	<title>{sermon.title} — {sermon.author_name} — Ochorus</title>
	<meta name="description" content="{sermon.title} — a sermon by {sermon.author_name}." />
	<link rel="canonical" href={canonical} />
</svelte:head>

<!-- Reader top bar -->
{#if !readerUi.focus}
	<div class="sticky top-0 z-10 border-b border-border bg-bg/90 backdrop-blur">
		<div class="mx-auto flex max-w-3xl items-center justify-between gap-3 px-5 py-2.5">
			<a href={localizeHref('/sermons')} class="text-small text-muted hover:text-text">← {t('nav.sermons')}</a>
			<div class="flex shrink-0 items-center gap-1">
				{#if listen.supported}
					<button
						class="btn btn-ghost !px-2.5 !py-1"
						class:!text-accent={listen.status !== 'idle'}
						onclick={() => (listen.status === 'idle' ? startListening() : listen.stop())}
						aria-label={t('reader.listen')}
						title={t('reader.listen')}>▶</button
					>
				{/if}
				<ReaderControls />
				<button
					class="btn btn-ghost !px-3 !py-1"
					onclick={() => readerUi.toggleFocus()}
					aria-label={t('reader.focus')}
					title={t('reader.focus')}>☾</button
				>
			</div>
		</div>
	</div>
{/if}

{#if readerUi.focus}
	<button
		class="fixed right-4 top-4 z-30 rounded-full border border-border bg-surface/90 px-3 py-1.5 text-small text-muted shadow-md backdrop-blur hover:text-text"
		onclick={() => readerUi.exitFocus()}>✕ {t('reader.exitFocus')}</button
	>
{/if}

<article class="mx-auto px-5 py-10" style="{readerPrefs.style}; max-width: var(--reading-measure)" dir="auto">
	<!-- Breadcrumb -->
	<nav class="mb-5 flex flex-wrap items-center gap-1.5 text-small text-muted" aria-label="Breadcrumb">
		<a href={localizeHref('/sermons')} class="hover:text-text">{t('nav.sermons')}</a>
		<span>›</span>
		<a href={localizeHref(`/authors/${sermon.author_slug}`)} class="hover:text-text">{sermon.author_name}</a>
	</nav>

	<p class="mb-1 text-small uppercase tracking-wider text-muted">
		Sermon · {readingTime(sermon.word_count)}{#if preachedYear} · {preachedYear}{/if}
	</p>
	<h1 class="text-h1 mb-2">{sermon.title}</h1>
	{#if sermon.scripture_ref}
		<p class="mb-8 text-h3 text-accent" style="font-family: var(--font-display)">{sermon.scripture_ref}</p>
	{/if}

	<!-- Body HTML is cleaned server-side to a safe tag subset on ingest. -->
	<div class="reading" bind:this={body}>{@html sermon.body_html}</div>

	{#if related.length}
		<section class="mt-12 border-t border-border pt-6">
			<h2 class="text-h3 mb-3">More sermons on {book}</h2>
			<ul class="space-y-2">
				{#each related as r (r.slug)}
					<li>
						<a href={localizeHref(`/sermons/${r.slug}`)} class="text-body font-medium">{r.title}</a>
						<span class="text-small text-muted"> · {r.scripture_ref} · {r.author.name}</span>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if sermon.source_url}
		<p class="mt-12 border-t border-border pt-5 text-[0.8rem] text-muted">
			Public domain. Source text from
			<a href={sermon.source_url} target="_blank" rel="noreferrer">the original edition</a>.
		</p>
	{/if}

	<nav class="mt-8">
		<a href={localizeHref(`/authors/${sermon.author_slug}`)} class="btn btn-ghost">← More from {sermon.author_name}</a>
	</nav>
</article>

<ListenBar />
