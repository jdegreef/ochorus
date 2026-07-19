<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { listSermons, type Sermon, type SermonSummary } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { readingTime, readingMinutes } from '$lib/reading';
	import { getSermonAnchor, saveSermonAnchor } from '$lib/sermonProgress';
	import { getLang } from '$lib/lang.svelte';
	import { listen } from '$lib/listen.svelte';
	import { scripture } from '$lib/scripture.svelte';
	import { localizeHref, locales } from '$lib/paraglide/runtime';
	import ReaderControls from '$lib/components/ReaderControls.svelte';
	import ScripturePopover from '$lib/components/ScripturePopover.svelte';
	import ListenBar from '$lib/components/ListenBar.svelte';

	let { data } = $props();
	const sermon = $derived(data.sermon as Sermon);
	const t = i18n.t;

	let body = $state<HTMLElement | undefined>();
	// Other sermons on the same Bible book, fetched client-side (page is
	// prerendered; the list is small and cached by the browser).
	let related = $state<SermonSummary[]>([]);

	// --- Reading progress ------------------------------------------------------
	// Long sermons need orientation: a scroll-progress bar, an estimate of the
	// time remaining, and a resume point. Anchored to the top-visible paragraph
	// so it survives text-size / width changes (mirrors the chapter reader).
	const HEADER_OFFSET = 64;
	let frac = $state(0);
	let saveTimer: ReturnType<typeof setTimeout> | undefined;
	const minutesLeft = $derived(
		Math.max(1, Math.ceil(readingMinutes(sermon.word_count) * (1 - frac)))
	);

	function topVisibleIndex(): number {
		if (!body) return 0;
		const kids = body.children;
		for (let i = 0; i < kids.length; i++) {
			if (kids[i].getBoundingClientRect().bottom > HEADER_OFFSET) return i;
		}
		return Math.max(0, kids.length - 1);
	}

	function updateFraction() {
		if (!body) return;
		const rect = body.getBoundingClientRect();
		if (rect.height <= 0) return;
		const seen = Math.min(Math.max(window.innerHeight - rect.top, 0), rect.height);
		frac = Math.min(1, Math.max(0, seen / rect.height));
	}

	function onScroll() {
		clearTimeout(saveTimer);
		saveTimer = setTimeout(() => {
			updateFraction();
			saveSermonAnchor(sermon.slug, topVisibleIndex());
		}, 250);
	}

	// Restore the saved spot on open (and once the body has rendered).
	onMount(() => {
		(async () => {
			await tick();
			const idx = getSermonAnchor(sermon.slug);
			if (idx > 0 && body?.children[idx]) {
				body.children[idx].scrollIntoView({ block: 'start' });
				window.scrollBy(0, -HEADER_OFFSET);
			}
			updateFraction();
		})();
	});

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

	/** Tap a server-wrapped Bible reference → open the scripture popover. */
	function onBodyClick(e: MouseEvent) {
		const a = (e.target as HTMLElement).closest?.('a.scripture-ref') as HTMLElement | null;
		if (!a?.dataset.ref) return;
		e.preventDefault();
		const r = a.getBoundingClientRect();
		scripture.show(a.dataset.ref, r.bottom + window.scrollY, r.left + window.scrollX + r.width / 2);
	}

	/** Read the sermon aloud from the top. */
	function startListening() {
		if (!body) return;
		const paragraphs = [...body.children].map((el) => (el as HTMLElement).innerText);
		listen.start(paragraphs, 0, getLang(), { title: sermon.title, artist: sermon.author_name });
	}

	// Self-referential canonical + hreflang per locale (mirrors authors/[slug]) —
	// an English canonical here would deindex the translated sermon pages.
	const path = $derived(`/sermons/${sermon.slug}/`);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const alternates = $derived(
		locales.map((loc) => ({ loc, href: `${SITE_URL}${localizeHref(path, { locale: loc })}` }))
	);
	const preachedYear = $derived(sermon.preached_on ? sermon.preached_on.slice(0, 4) : '');
</script>

<svelte:head>
	<title>{sermon.title} — {sermon.author_name} — Ochorus</title>
	<meta name="description" content="{sermon.title} — a sermon by {sermon.author_name}." />
	<link rel="canonical" href={canonical} />
	{#each alternates as a (a.loc)}
		<link rel="alternate" hreflang={a.loc} href={a.href} />
	{/each}
	<link rel="alternate" hreflang="x-default" href="{SITE_URL}{localizeHref(path, { locale: 'en' })}" />
</svelte:head>

<svelte:window onscroll={onScroll} />

<!-- Scroll-progress bar, pinned to the very top of the viewport. -->
<div class="read-progress" style="transform: scaleX({frac})" aria-hidden="true"></div>

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
	<nav class="mb-5 flex flex-wrap items-center gap-1.5 text-small text-muted" aria-label={t('a11y.breadcrumb')}>
		<a href={localizeHref('/sermons')} class="hover:text-text">{t('nav.sermons')}</a>
		<span>›</span>
		<a href={localizeHref(`/authors/${sermon.author_slug}`)} class="hover:text-text">{sermon.author_name}</a>
	</nav>

	<p class="mb-1 text-small uppercase tracking-wider text-muted">
		{t('search.typeSermon')} · {readingTime(sermon.word_count)}{#if preachedYear} · {preachedYear}{/if}
	</p>
	<h1 class="text-h1 mb-2">{sermon.title}</h1>
	{#if sermon.scripture_ref}
		<p class="mb-3 text-h3 text-accent" style="font-family: var(--font-display)">{sermon.scripture_ref}</p>
	{/if}
	{#if sermon.source_type === 'ai_unreviewed'}
		<p
			class="mb-8 inline-flex items-center gap-1.5 rounded-full border border-gold/40 bg-gold/10 px-3 py-1 text-small text-gold"
		>
			{t('book.aiUnreviewed')}
		</p>
	{:else if sermon.source_type === 'ai_reviewed'}
		<p
			class="mb-8 inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-2 px-3 py-1 text-small text-muted"
		>
			{t('book.aiReviewed')}
		</p>
	{:else}
		<div class="mb-8"></div>
	{/if}

	<!-- Body HTML is cleaned server-side to a safe tag subset on ingest;
	     Bible references are wrapped as tappable spans (scripture popover). -->
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events -->
	<div class="reading" bind:this={body} onclick={onBodyClick}>{@html sermon.body_html}</div>

	{#if related.length}
		<section class="mt-12 border-t border-border pt-6">
			<h2 class="text-h3 mb-3">{t('sermon.moreOn')} {book}</h2>
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
			{t('book.publicDomain')}
			<a href={sermon.source_url} target="_blank" rel="noreferrer">{t('book.originalEdition')}</a>.
		</p>
	{/if}

	<nav class="mt-8">
		<a href={localizeHref(`/authors/${sermon.author_slug}`)} class="btn btn-ghost">← {t('sermon.moreFrom')} {sermon.author_name}</a>
	</nav>
</article>

<!-- Time-remaining pill; hidden in focus and while listening. -->
{#if !readerUi.focus && listen.status === 'idle' && frac < 0.99}
	<div class="min-left" aria-hidden="true">{minutesLeft} {t('sermon.minLeft')}</div>
{/if}

<ScripturePopover />
<ListenBar />

<style>
	/* Scroll-progress bar: a thin accent line scaled by reading fraction. */
	.read-progress {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		height: 2px;
		z-index: 40;
		background: var(--accent);
		transform-origin: left center;
		transition: transform 0.1s linear;
		pointer-events: none;
	}
	.min-left {
		position: fixed;
		bottom: 1rem;
		left: 50%;
		transform: translateX(-50%);
		z-index: 30;
		border-radius: 9999px;
		border: 1px solid var(--border);
		background: color-mix(in srgb, var(--bg) 85%, transparent);
		backdrop-filter: blur(6px);
		padding: 0.25rem 0.8rem;
		font-size: 0.72rem;
		color: var(--muted);
		pointer-events: none;
	}
</style>
