<script lang="ts">
	import { onMount } from 'svelte';
	import { type Sermon, type SermonSummary, listSermons } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import {
		contentLang,
		readingTime,
		readingMinutes,
		preachedYear,
		HEADER_OFFSET
	} from '$lib/reading';
	import { getLang } from '$lib/lang.svelte';
	import { listen } from '$lib/listen.svelte';
	import { type ScriptureResult } from '$lib/scripture.svelte';
	import { apiFetch } from '$lib/api';
	import { page } from '$app/stores';
	import { buildOutline, type OutlineEntry } from '$lib/sermonOutline';
	import { absUrl, jsonLd, breadcrumb, hreflangFor } from '$lib/seo';
	import { focusTrap } from '$lib/actions/focusTrap';
	import { localizeHref } from '$lib/href';
	import { portraitPosition } from '$lib/portraits';
	import Reader from '$lib/components/Reader.svelte';
	import ReaderControls from '$lib/components/ReaderControls.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let { data } = $props();
	const sermon = $derived(data.sermon as Sermon);
	const t = i18n.t;

	/**
	 * Escape leaves focus (immersive) mode. readerUi.exitFocus() existed and
	 * nothing on this page called it, so the only way out was finding the
	 * floating "Exit focus" pill. The outline drawer runs its own focus trap
	 * with an onEscape, so it keeps handling its own key.
	 */
	function onKeydown(e: KeyboardEvent) {
		if (e.key !== 'Escape' || e.metaKey || e.ctrlKey || e.altKey) return;
		if (outlineOpen || !readerUi.focus) return;
		e.preventDefault();
		readerUi.exitFocus();
	}

	// The reader owns the prose and everything that reads it; this page owns its
	// own chrome. `body` comes back out for the outline, `frac` for the progress
	// bar, and the instance for the Listen button.
	let reader = $state<Reader | undefined>();
	let body = $state<HTMLElement | undefined>();
	let frac = $state(0);
	const minutesLeft = $derived(
		Math.max(1, Math.ceil(readingMinutes(sermon.word_count) * (1 - frac)))
	);

	// Other sermons on the same Bible book, fetched client-side (page is
	// prerendered; the list is small and cached by the browser).
	let related = $state<SermonSummary[]>([]);

	// --- Jump-to-section outline ----------------------------------------------
	// Built from the rendered body once it's in the page (headings + the classic
	// "I. / II. / III." homiletic points). Shown only when there's real structure
	// to navigate.
	let outline = $state<OutlineEntry[]>([]);
	let outlineOpen = $state(false);
	// The section the reader is currently in — for the desktop rail's highlight.
	let activeSection = $state('');
	$effect(() => {
		void sermon.slug; // rebuild when navigating between sermons
		outline = body ? buildOutline(body) : [];
		// Off the reactive graph: reading `outline` here would re-trigger this
		// effect (which writes it) — an update-depth loop.
		if (typeof requestAnimationFrame !== 'undefined') requestAnimationFrame(updateActiveSection);
	});

	/** The last outline section whose heading has scrolled up past the top bar. */
	function updateActiveSection() {
		let current = '';
		for (const s of outline) {
			const el = document.getElementById(s.id);
			if (!el) continue;
			if (el.getBoundingClientRect().top <= HEADER_OFFSET + 40) current = s.id;
			else break; // outline is in document order — nothing below can be active
		}
		activeSection = current;
	}

	function scrollToSection(id: string) {
		const el = document.getElementById(id);
		if (el) {
			const y = el.getBoundingClientRect().top + window.scrollY - HEADER_OFFSET - 8;
			window.scrollTo({ top: y, behavior: 'smooth' });
		}
		outlineOpen = false;
	}

	const initials = (name: string) =>
		name
			.split(' ')
			.filter(Boolean)
			.map((w) => w[0])
			.slice(0, 2)
			.join('')
			.toUpperCase();

	// The sermon's preaching text — the verse(s) it's built on — for the header
	// card. Fetched client-side (the page is prerendered); absent = card shows
	// just the reference.
	let preachingText = $state<ScriptureResult | null>(null);
	$effect(() => {
		const ref = sermon.scripture_ref;
		preachingText = null;
		if (!ref) return;
		apiFetch<ScriptureResult>(`/api/library/scripture/?ref=${encodeURIComponent(ref)}`)
			.then((v) => (preachingText = v))
			.catch(() => (preachingText = null));
	});

	/** "1 Peter 2:7" -> "1 Peter"; "Matthew 11:28" -> "Matthew". */
	const refBook = (ref: string) => ref.match(/^(\d?\s?[A-Za-z]+)/)?.[1]?.trim() ?? '';
	const book = $derived(refBook(sermon.scripture_ref || ''));

	// onMount, not $effect: `listSermons` fetches the whole catalogue with no
	// memo, and an effect keyed on `book` would re-issue it on every
	// sermon→sermon navigation just to fill a footer list. (That also means the
	// list doesn't refresh on client-side nav — pre-existing, and a fair thing to
	// fix once `listSermons` is memoised.)
	onMount(() => {
		readerPrefs.init();
		if (!book) return;
		listSermons(getLang())
			.then((all) => {
				related = all.filter(
					(s) => s.slug !== sermon.slug && refBook(s.scripture_ref || '') === book
				);
			})
			.catch(() => (related = []));
	});

	// Self-referential canonical + hreflang — an English canonical here would
	// deindex the translated sermon pages. Sermons are per-language rows with no
	// English fallback, so hreflang lists only the locales this sermon exists in.
	const path = $derived(`/sermons/${sermon.slug}/`);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const hreflang = $derived(hreflangFor(path, sermon.available_languages));
	const year = $derived(preachedYear(sermon.preached_on));

	// --- SEO -------------------------------------------------------------------
	// A real description from the opening prose (beats the generic template) and
	// structured data: an Article for the sermon (its preaching text as `about`)
	// plus a breadcrumb. og:image is the author portrait when present (raster).
	const metaDescription = $derived(
		(sermon.body_html || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 155) ||
			t('sermon.metaFallback')
				.replace('%title%', sermon.title)
				.replace('%name%', sermon.author_name)
	);
	const ogImage = $derived(sermon.author_photo ? absUrl(sermon.author_photo) : '');
	const sermonLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'Article',
			headline: sermon.title,
			author: {
				'@type': 'Person',
				name: sermon.author_name,
				url: absUrl(`/authors/${sermon.author_slug}`)
			},
			inLanguage: sermon.language,
			url: canonical,
			isAccessibleForFree: true,
			datePublished: sermon.preached_on || undefined,
			image: ogImage || undefined,
			about: sermon.scripture_ref ? { '@type': 'Thing', name: sermon.scripture_ref } : undefined,
			publisher: { '@type': 'Organization', name: 'Ochorus' }
		})
	);
	const crumbsLd = $derived(
		jsonLd(
			breadcrumb([
				{ name: t('common.home'), url: '/' },
				{ name: t('nav.sermons'), url: '/sermons' },
				{ name: sermon.title, url: `/sermons/${sermon.slug}` }
			])
		)
	);

	// Selecting text offers copy-quote / share (with attribution), highlight and
	// note; a single word opens the dictionary — same as the chapter reader.
	const cite = $derived({
		author: sermon.author_name,
		book: sermon.title,
		chapter: '',
		url: $page.url.href
	});
</script>

<Seo
	title="{sermon.title} — {sermon.author_name} — Ochorus"
	description={metaDescription}
	{canonical}
	{hreflang}
	ogType="article"
	ogTitle="{sermon.title} — {sermon.author_name}"
	{ogImage}
	structuredData={[sermonLd, crumbsLd]}
/>

<svelte:window onscroll={updateActiveSection} onkeydown={onKeydown} />

<!-- Scroll-progress bar, pinned to the very top of the viewport. -->
<div class="read-progress" style="transform: scaleX({frac})" aria-hidden="true"></div>

<!-- Reader top bar -->
{#if !readerUi.focus}
	<div class="reader-chrome sticky top-0 z-10 border-b border-border bg-bg/90 backdrop-blur">
		<div class="mx-auto flex max-w-3xl items-center justify-between gap-3 px-5 py-2.5">
			<a href={localizeHref('/sermons')} class="text-small text-muted hover:text-text"
				>← {t('nav.sermons')}</a
			>
			<div class="flex shrink-0 items-center gap-1">
				{#if outline.length >= 2}
					<button
						class="outline-toggle-btn btn btn-icon btn-ghost"
						class:text-accent={outlineOpen}
						onclick={() => (outlineOpen = !outlineOpen)}
						aria-label={t('sermon.outline')}
						title={t('sermon.outline')}
						aria-expanded={outlineOpen}><Icon name="list" size={18} /></button
					>
				{/if}
				{#if listen.supported}
					<button
						class="btn btn-icon btn-ghost"
						class:text-accent={listen.status !== 'idle'}
						onclick={() => (listen.status === 'idle' ? reader?.startListening() : listen.stop())}
						aria-label={t('reader.listen')}
						title={t('reader.listen')}>▶</button
					>
				{/if}
				<ReaderControls />
				<button
					class="btn btn-icon btn-ghost"
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
		class="fixed end-4 top-4 z-30 rounded-full border border-border bg-surface/90 px-3 py-1.5 text-small text-muted shadow-md backdrop-blur hover:text-text"
		onclick={() => readerUi.exitFocus()}>✕ {t('reader.exitFocus')}</button
	>
{/if}

<!-- Jump-to-section outline panel (opened from the top bar). -->
{#if outlineOpen}
	<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
	<div class="outline-backdrop" onclick={() => (outlineOpen = false)}></div>
	<nav
		class="outline-panel"
		aria-label={t('sermon.outline')}
		use:focusTrap={{ onEscape: () => (outlineOpen = false) }}
	>
		<p class="outline-title eyebrow">{t('sermon.outline')}</p>
		<ul>
			{#each outline as s (s.id)}
				<li>
					<button
						class="outline-item"
						class:point={s.kind === 'point'}
						onclick={() => scrollToSection(s.id)}
					>
						{s.label}
					</button>
				</li>
			{/each}
		</ul>
	</nav>
{/if}

<!-- Persistent outline rail (wide screens): mirrors the popover, highlighting
     the section you're reading. The top-bar toggle takes over below 1200px. -->
{#if outline.length >= 2 && !readerUi.focus}
	<nav class="outline-rail" aria-label={t('sermon.outline')}>
		<p class="outline-rail-title eyebrow">{t('sermon.outline')}</p>
		<ul>
			{#each outline as s (s.id)}
				<li>
					<button
						class="outline-rail-item"
						class:point={s.kind === 'point'}
						class:active={activeSection === s.id}
						onclick={() => scrollToSection(s.id)}
					>
						{s.label}
					</button>
				</li>
			{/each}
		</ul>
	</nav>
{/if}

<article class="mx-auto px-5 py-10" style="{readerPrefs.style}; max-width: var(--reading-measure)">
	<!-- Breadcrumb -->
	<nav
		class="mb-5 flex flex-wrap items-center gap-1.5 text-small text-muted"
		aria-label={t('a11y.breadcrumb')}
	>
		<a href={localizeHref('/sermons')} class="hover:text-text">{t('nav.sermons')}</a>
		<span>›</span>
		<a href={localizeHref(`/authors/${sermon.author_slug}`)} class="hover:text-text"
			>{sermon.author_name}</a
		>
	</nav>

	<p class="eyebrow mb-1 text-muted">
		{t('search.typeSermon')} · {readingTime(sermon.word_count)}{#if year} · {year}{/if}{#if sermon.difficulty}&nbsp;·
			<span title={t('reader.difficulty')}>{t(`reader.difficulty_${sermon.difficulty}`)}</span>{/if}
	</p>
	<h1 class="text-h1 mb-3" dir="auto" lang={contentLang(sermon.language)}>{sermon.title}</h1>

	<!-- Author row: portrait + name -->
	<a
		href={localizeHref(`/authors/${sermon.author_slug}`)}
		class="group mb-5 inline-flex items-center gap-2.5 hover:no-underline"
	>
		{#if sermon.author_photo}
			<img
				src={sermon.author_photo}
				alt="{t('a11y.portraitOf')} {sermon.author_name}"
				class="h-9 w-9 shrink-0 rounded-full border border-border object-cover"
				style="filter: grayscale(1); object-position: {portraitPosition(sermon.author_slug)}"
				loading="lazy"
			/>
		{:else}
			<span
				class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent-soft text-small font-semibold text-accent"
			>
				{initials(sermon.author_name)}
			</span>
		{/if}
		<span class="text-body font-medium text-text group-hover:text-accent">{sermon.author_name}</span>
	</a>

	<!-- Preaching text: the reference, and its verse(s) when available -->
	{#if sermon.scripture_ref}
		<div class="text-card">
			<p class="text-card-eyebrow eyebrow">{t('sermon.text')}</p>
			<p class="text-card-ref">{sermon.scripture_ref}</p>
			{#if preachingText?.verses?.length}
				<p class="text-card-verse">
					{#each preachingText.verses as v (v.number)}{v.text}{' '}{/each}
				</p>
				<p class="text-card-version eyebrow">{preachingText.version}</p>
			{/if}
		</div>
	{/if}

	{#if sermon.source_type === 'ai_unreviewed'}
		<p
			class="mb-8 inline-flex items-center gap-1.5 rounded-full border border-warning/40 bg-warning/10 px-3 py-1 text-small text-warning"
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

	<!-- "In brief": an AI-drafted TL;DR so a reader knows in ten seconds
	     whether this sermon is the one they need right now. -->
	{#if sermon.summary}
		<div class="mb-8 rounded-card border border-border bg-surface p-4">
			<p class="eyebrow mb-1.5 text-accent">
				{t('sermon.inBrief')}
			</p>
			<p class="text-small leading-relaxed text-muted">{sermon.summary}</p>
		</div>
	{/if}

	<Reader
		bind:this={reader}
		kind="sermon"
		slug={sermon.slug}
		language={sermon.language}
		html={sermon.body_html}
		{cite}
		listenTitle={sermon.title}
		listenArtist={sermon.author_name}
		bind:body
		bind:frac
	/>

	<!-- Scripture index: the passages this sermon engages, each a jump into
	     scripture search — so scripture is a navigation surface, not just text. -->
	{#if sermon.scripture_refs?.length}
		<div class="mt-10 flex flex-wrap items-center gap-2 border-t border-border pt-5">
			<span class="eyebrow text-muted">
				{t('sermon.scriptureIndex')}
			</span>
			{#each sermon.scripture_refs as ref (ref)}
				<a
					href={localizeHref(`/search?q=${encodeURIComponent(ref)}`)}
					class="rounded-full border border-border px-3 py-1 text-small text-text hover:border-accent hover:text-accent hover:no-underline"
				>
					{ref}
				</a>
			{/each}
		</div>
	{/if}

	<!-- Topical shelves this sermon appears on — the same membership the author
	     and topic pages surface; a reader moved by it can find kindred works. -->
	{#if sermon.topics?.length}
		<div class="mt-4 flex flex-wrap items-center gap-2">
			<span class="eyebrow text-muted">
				{t('sermon.topics')}
			</span>
			{#each sermon.topics as topic (topic.slug)}
				<a
					href={localizeHref(`/topics/${topic.slug}`)}
					class="rounded-full bg-surface-2 px-3 py-1 text-small text-text hover:text-accent hover:no-underline"
				>
					{topic.title}
				</a>
			{/each}
		</div>
	{/if}

	<!-- Sequential prev/next through this author's sermons, so a reader who
	     finishes one keeps going instead of dead-ending at the bottom. -->
	{#if sermon.prev || sermon.next}
		<nav class="mt-12 flex gap-3 border-t border-border pt-6" aria-label={t('sermon.sequentialNav')}>
			{#if sermon.prev}
				<a
					href={localizeHref(`/sermons/${sermon.prev.slug}`)}
					class="group flex-1 rounded-card border border-border p-3 hover:border-accent hover:no-underline"
				>
					<div class="eyebrow text-muted">← {t('reader.previous')}</div>
					<div class="mt-0.5 text-small font-semibold text-text group-hover:text-accent">
						{sermon.prev.title}
					</div>
				</a>
			{/if}
			{#if sermon.next}
				<a
					href={localizeHref(`/sermons/${sermon.next.slug}`)}
					class="group flex-1 rounded-card border border-border p-3 text-end hover:border-accent hover:no-underline"
				>
					<div class="eyebrow text-muted">{t('reader.next')} →</div>
					<div class="mt-0.5 text-small font-semibold text-text group-hover:text-accent">
						{sermon.next.title}
					</div>
				</a>
			{/if}
		</nav>
	{/if}

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
		<p class="mt-12 border-t border-border pt-5 text-small text-muted">
			{t('book.publicDomain')}
			<a href={sermon.source_url} target="_blank" rel="noreferrer">{t('book.originalEdition')}</a>.
		</p>
	{/if}

	<nav class="mt-8">
		<a href={localizeHref(`/authors/${sermon.author_slug}`)} class="btn btn-ghost"
			>← {t('sermon.moreFrom')} {sermon.author_name}</a
		>
	</nav>
</article>

<!-- Time-remaining pill; hidden in focus and while listening. -->
{#if !readerUi.focus && listen.status === 'idle' && frac < 0.99}
	<div class="min-left" aria-hidden="true">{minutesLeft} {t('sermon.minLeft')}</div>
{/if}

<style>
	/* Scroll-progress bar: a thin accent line scaled by reading fraction. */
	/* `.min-left` lives in app.css — the biography page shows the same pill, and
	   a second copy here is how the two would drift apart. */

	/* Preaching-text card: the sermon's reference + verse(s) as an epigraph. */
	.text-card {
		margin: 0 0 2rem;
		padding: 0.85rem 1.1rem;
		border-inline-start: 3px solid var(--accent);
		border-start-end-radius: var(--radius-card);
		border-end-end-radius: var(--radius-card);
		background: var(--accent-soft);
	}
	.text-card-eyebrow {
		font-size: var(--fs-micro);
		color: var(--accent);
	}
	.text-card-ref {
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		color: var(--accent);
		margin-top: 0.1rem;
	}
	.text-card-verse {
		margin-top: 0.5rem;
		font-family: var(--font-display);
		font-style: italic;
		line-height: 1.6;
		color: var(--text);
	}
	.text-card-version {
		margin-top: 0.45rem;
		font-size: var(--fs-micro);
		color: var(--muted);
	}

	/* Jump-to-section outline: a light popover under the reader bar. */
	.outline-backdrop {
		position: fixed;
		inset: 0;
		z-index: 20;
	}
	.outline-panel {
		position: fixed;
		top: 3.4rem;
		inset-inline-end: max(0.75rem, calc((100vw - 48rem) / 2));
		z-index: 21;
		width: min(20rem, calc(100vw - 1.5rem));
		max-height: 70vh;
		overflow-y: auto;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		box-shadow: var(--shadow-popover);
		padding: 0.5rem;
	}
	.outline-title {
		padding: 0.35rem 0.6rem;
		font-size: var(--fs-micro);
		color: var(--muted);
	}
	.outline-item {
		display: block;
		width: 100%;
		text-align: start;
		padding: 0.45rem 0.6rem;
		border-radius: var(--radius-sm);
		font-size: var(--fs-small);
		color: var(--text);
		line-height: 1.35;
	}
	.outline-item:hover {
		background: var(--surface-2);
		color: var(--accent);
	}
	/* Real headings sit flush; homiletic points get a subtle indent + accent. */
	.outline-item.point {
		color: var(--muted);
	}
	.outline-item.point:hover {
		color: var(--accent);
	}

	/* Persistent outline rail — hidden until there's room beside the article. */
	.outline-rail {
		display: none;
	}
	@media (min-width: 1280px) {
		.outline-rail {
			display: block;
			position: fixed;
			top: 5rem;
			inset-inline-end: max(1rem, calc((100vw - var(--reading-measure, 46rem)) / 2 - 15rem));
			width: 14rem;
			max-height: calc(100vh - 7rem);
			overflow-y: auto;
			z-index: 5;
		}
		/* The top-bar toggle is redundant once the rail is visible. */
		.outline-toggle-btn {
			display: none;
		}
	}
	.outline-rail-title {
		padding: 0 0.6rem 0.4rem;
		font-size: var(--fs-micro);
		color: var(--muted);
	}
	.outline-rail-item {
		display: block;
		width: 100%;
		text-align: start;
		padding: 0.3rem 0.6rem;
		border-inline-start: 2px solid transparent;
		font-size: var(--fs-small);
		line-height: 1.35;
		color: var(--muted);
		transition: color var(--duration-fast) ease;
	}
	.outline-rail-item:hover {
		color: var(--accent);
	}
	.outline-rail-item.point {
		padding-inline-start: 1.1rem;
	}
	.outline-rail-item.active {
		color: var(--accent);
		border-inline-start-color: var(--accent);
		font-weight: 600;
	}
</style>
