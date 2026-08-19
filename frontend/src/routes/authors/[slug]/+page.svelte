<script lang="ts">
	import { type AuthorDetail, type AuthorBio, listAuthors, formatLifespan } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { cssString } from '$lib/cssString';
	import { absUrl, jsonLd, breadcrumb, hreflangAll } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { readingTime, readingMinutes } from '$lib/reading';
	import { localizeHref } from '$lib/href';
	import { scopedSearchHref } from '$lib/searchState';
	import { portraitPosition } from '$lib/portraits';
	import { listen } from '$lib/listen.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { page } from '$app/stores';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { BIO_CHAPTER_ORDER } from '$lib/reading-schema';
	import BookCard from '$lib/components/BookCard.svelte';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import LifeTimeline from '$lib/components/LifeTimeline.svelte';
	import Reader from '$lib/components/Reader.svelte';
	import ReaderControls from '$lib/components/ReaderControls.svelte';
	import { onMount } from 'svelte';

	const t = i18n.t;

	let { data } = $props();
	const author = $derived<AuthorDetail>(data.author);

	// The biography reads like any other long-form work here: <Reader> owns the
	// prose and everything that has to know about it (resume point, highlights
	// and notes, read-aloud, the dictionary and scripture popovers). This page
	// keeps its own shell, because a bio's prose is one band inside a much wider
	// page — the portrait, timeline, book grid and contemporaries must NOT
	// inherit the reading column's width.
	let reader = $state<Reader | undefined>();
	let bioEl = $state<HTMLElement | undefined>();
	/** How far through the biography itself, 0–1 — not through the page. */
	let frac = $state(0);

	onMount(() => readerPrefs.init());

	// Counted from the rendered bio rather than a word_count field: the API does
	// not expose one for biographies, and this is the only place that needs it.
	const bioWords = $derived(
		(author.bio_html || '').replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length
	);
	const minutesLeft = $derived(Math.max(1, Math.ceil(readingMinutes(bioWords) * (1 - frac))));

	const cite = $derived({
		author: author.name,
		book: t('bios.eyebrow'),
		chapter: '',
		url: $page.url.href
	});

	const initials = (name: string) =>
		name.split(' ').filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase();

	const years = $derived(
		formatLifespan(author.birth_year, author.death_year, t('common.bornPrefix'))
	);

	// A one-line "what's here" summary under the name: era + work counts.
	const summaryBits = $derived(
		[
			years,
			author.books.length
				? `${author.books.length} ${author.books.length === 1 ? t('common.bookOne') : t('common.bookMany')}`
				: '',
			author.sermons.length
				? `${author.sermons.length} ${author.sermons.length === 1 ? t('common.sermonOne') : t('common.sermonMany')}`
				: ''
		].filter(Boolean)
	);

	// "More lives to explore": nearest contemporaries by birth year (loaded after
	// mount; the page is prerendered). Falls back to any other authors when this
	// one has no dated birth year.
	let contemporaries = $state<AuthorBio[]>([]);
	onMount(async () => {
		try {
			const all = await listAuthors(getLang());
			const by = author.birth_year;
			const dist = (a: AuthorBio) =>
				by == null || a.birth_year == null ? Infinity : Math.abs(a.birth_year - by);
			contemporaries = all
				.filter((a) => a.slug !== author.slug && (a.book_count > 0 || !!a.bio))
				.sort((a, b) => dist(a) - dist(b) || a.name.localeCompare(b.name))
				.slice(0, 6);
		} catch {
			contemporaries = [];
		}
	});
	// Self-referential canonical + hreflang: this page is prerendered per locale,
	// so each localized copy points at ITSELF (not the English URL) and links its
	// siblings, instead of every locale canonicalizing to /authors/<slug> (which
	// deindexes the translations). Mirrors the /biographies list page.
	const path = $derived(`/authors/${author.slug}/`);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	// An author page exists in every locale — the person, their dates and their
	// works are language-independent — so all locales are real hreflang
	// alternates, unlike books/sermons which list only the locales they exist in.
	// (The bio itself no longer falls back to English: an untranslated bio is
	// absent, and the page renders the works without it.)
	const hreflang = $derived(hreflangAll(path));
	// Localized, because the bio may legitimately be missing in this language and
	// a hardcoded English sentence would then become the page's meta description.
	const description = $derived(
		(author.bio || t('author.metaFallback').replace('%name%', author.name)).slice(0, 300)
	);
	const ogImage = $derived(
		author.photo_url
			? absUrl(author.photo_url)
			: author.books[0]?.cover_url
				? absUrl(author.books[0].cover_url)
				: ''
	);

	const personLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'Person',
			name: author.name,
			description: author.bio || undefined,
			image: ogImage || undefined,
			birthDate: author.birth_year ? String(author.birth_year) : undefined,
			deathDate: author.death_year ? String(author.death_year) : undefined,
			url: canonical
		})
	);
	const crumbsLd = $derived(
		jsonLd(
			breadcrumb([
				{ name: t('common.home'), url: '/' },
				{ name: t('bios.eyebrow'), url: '/biographies' },
				{ name: author.name, url: `/authors/${author.slug}` }
			])
		)
	);
	// Prayer-callout labels are rendered by CSS ::before content; pass the
	// localized strings in as custom properties so they follow the locale.
	// Quoted through cssString: an apostrophe in any translation would close the
	// CSS string early and take the rest of the declaration with it, silently
	// and only in that locale.
	const bioLabels = $derived(
		`--label-in-prayer: ${cssString(t('bios.inPrayer'))}; ` +
			`--label-answered: ${cssString(t('bios.answerToPrayer'))}`
	);

	// Where to start + how much there is to read: the first book (the API's
	// featured order) and the total reading time across every work.
	const startWork = $derived(author.books[0] ?? null);
	const totalWords = $derived(
		author.books.reduce((n, b) => n + (b.word_count ?? 0), 0) +
			author.sermons.reduce((n, s) => n + (s.word_count ?? 0), 0)
	);

	// A featured pull-quote for the header: the first <blockquote> in the bio,
	// tag-stripped (drop the <cite> attribution). Regex, not the DOM, so it works
	// during prerender too. Absent / too-short quotes just don't show.
	const featuredQuote = $derived.by(() => {
		const m = (author.bio_html || '').match(/<blockquote[^>]*>([\s\S]*?)<\/blockquote>/i);
		if (!m) return '';
		const text = m[1]
			.replace(/<cite[\s\S]*?<\/cite>/i, '')
			.replace(/<[^>]+>/g, ' ')
			.replace(/\s+/g, ' ')
			.trim();
		if (text.length < 20) return '';
		return text.length > 220 ? text.slice(0, 217).trimEnd() + '…' : text;
	});
</script>

<Seo
	title="{author.name} — Ochorus"
	{description}
	{canonical}
	{hreflang}
	ogType="profile"
	{ogImage}
	structuredData={[personLd, crumbsLd]}
/>

<div class="mx-auto max-w-3xl px-5 py-10">
	<!-- Focus mode strips the page back to the life itself. Everything here is
	     context around the biography — portrait, timeline, epigraph, shelves,
	     contemporaries — and it is exactly what someone reading eleven minutes
	     of prose wants out of the way. -->
	{#if !readerUi.focus}
	<!-- Breadcrumb -->
	<nav class="mb-6 flex flex-wrap items-center gap-1.5 text-small text-muted" aria-label={t('a11y.breadcrumb')}>
		<a href={localizeHref('/')} class="hover:text-text">{t('common.home')}</a>
		<span>›</span>
		<a href={localizeHref('/biographies')} class="hover:text-text">{t('bios.eyebrow')}</a>
		<span>›</span>
		<span class="text-text">{author.name}</span>
	</nav>

	<!-- Wraps on a phone. The action row was already overflowing the viewport by
	     ~99px with three buttons (it is `shrink-0` beside a name that can be two
	     lines long); text settings and focus would have pushed it further. -->
	<header class="flex flex-wrap items-center gap-x-5 gap-y-4">
		{#if author.photo_url}
			<img
				src={author.photo_url}
				alt="{t('a11y.portraitOf')} {author.name}"
				class="h-24 w-24 shrink-0 rounded-full border border-border object-cover shadow-sm"
				style="filter: grayscale(1); object-position: {portraitPosition(author.slug)}"
			/>
		{:else}
			<span
				class="font-display flex h-24 w-24 shrink-0 items-center justify-center rounded-full bg-accent-soft text-h1 font-semibold text-accent"
			>
				{initials(author.name)}
			</span>
		{/if}
		<div class="min-w-0">
			<h1 class="text-h1" dir="auto">{author.name}</h1>
			{#if summaryBits.length}
				<p class="mt-1 text-body text-muted">
					{#each summaryBits as bit, i (i)}{#if i > 0}<span class="opacity-50"> · </span>{/if}{bit}{/each}
				</p>
			{/if}
		</div>
		<div class="ms-auto flex flex-wrap items-center gap-2">
			<!-- Search this author's works. A reader who has read one Murray book
			     and half-remembers a phrase from another is on this page, and
			     until now their only option was the whole library. -->
			<a
				href={localizeHref(scopedSearchHref('author', author.slug))}
				class="btn btn-ghost shrink-0 !px-2.5 !py-1">{t('search.inAuthor')}</a
			>
			<FavoriteButton kind="author" slug={author.slug} showLabel />
			{#if listen.supported && author.bio_html}
				<button
					class="btn btn-ghost shrink-0 !px-2.5 !py-1"
					class:!text-accent={listen.status !== 'idle'}
					onclick={() => (listen.status === 'idle' ? reader?.startListening() : listen.stop())}
					aria-label={t('reader.listen')}
					title={t('reader.listen')}>▶ {t('reader.listen')}</button
				>
			{/if}
			<!-- Reader affordances, shown only when there is a long-form biography to
			     read: text settings, and focus mode to strip the page back to prose. -->
			{#if author.bio_html}
				<ReaderControls />
				<button
					class="btn btn-ghost shrink-0 !px-2.5 !py-1"
					onclick={() => readerUi.toggleFocus()}
					aria-label={t('reader.focus')}
					title={t('reader.focus')}>☾</button
				>
			{/if}
		</div>
	</header>

	<!-- Lifespan timeline: places the author in history at a glance. -->
	<LifeTimeline birthYear={author.birth_year} deathYear={author.death_year} />

	<!-- Featured pull-quote: a hook above the biography. -->
	{#if featuredQuote}
		<blockquote class="author-quote mx-auto mt-8 max-w-[40rem]">{featuredQuote}</blockquote>
	{/if}

	<!-- Where to start + total reading time. -->
	{#if startWork || totalWords}
		<div
			class="mx-auto mt-6 flex max-w-[40rem] flex-wrap items-center gap-x-5 gap-y-1.5 rounded-card border border-border bg-surface px-4 py-3 text-small"
		>
			{#if startWork}
				<span class="text-muted">
					{t('author.startWith')}
					<a
						href={localizeHref(`/books/${startWork.slug}`)}
						class="font-semibold text-accent hover:underline">{startWork.title}</a
					>
				</span>
			{/if}
			{#if totalWords}
				<span class="text-muted sm:ms-auto">{t('author.allWorks')} · {readingTime(totalWords)}</span>
			{/if}
		</div>
	{/if}
	{/if}

	<!-- Biography. The band — not the page — carries the reader's CSS variables,
	     so the width/size/typeface controls govern the prose while the portrait,
	     book grid and contemporaries keep the page's own layout. `bioLabels`
	     rides along on the same element: custom properties inherit, so the
	     prayer-callout ::before labels reach the injected HTML. -->
	{#if author.bio_html}
		<div
			class="mx-auto mt-8"
			style="{readerPrefs.style}; {bioLabels}; max-width: var(--reading-measure)"
		>
			<Reader
				bind:this={reader}
				kind="bio"
				slug={author.slug}
				order={BIO_CHAPTER_ORDER}
				language={getLang()}
				html={author.bio_html}
				class="bio"
				{cite}
				listenTitle={author.name}
				listenArtist={t('bios.eyebrow')}
				bind:body={bioEl}
				bind:frac
				headerOffset={0}
			/>
		</div>
	{:else if author.bio}
		<p class="mt-6 text-body leading-relaxed text-muted">{author.bio}</p>
	{/if}

	{#if !readerUi.focus}
	<!-- Topical shelves this author appears in: cross-navigation into browse. -->
	{#if author.topics.length}
		<div class="mx-auto mt-8 flex max-w-[40rem] flex-wrap items-center gap-2">
			<span class="text-small font-semibold uppercase tracking-wide text-muted">
				{t('author.themes')}
			</span>
			{#each author.topics as topic (topic.slug)}
				<a
					href={localizeHref(`/topics/${topic.slug}`)}
					class="rounded-full border border-border px-3 py-1 text-small text-text hover:border-accent hover:text-accent hover:no-underline"
				>
					{topic.title}
				</a>
			{/each}
		</div>
	{/if}

	<!-- Books -->
	{#if author.books.length}
		<section class="mt-14">
			<h2 class="mb-4 text-h3">
				{t('author.booksBy')} {author.name}
				<span class="text-small font-normal text-muted">({author.books.length})</span>
			</h2>
			<div class="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4">
				{#each author.books as book (book.slug)}
					<BookCard {book} />
				{/each}
			</div>
		</section>
	{/if}

	<!-- Sermons -->
	{#if author.sermons.length}
		<section class="mt-14">
			<h2 class="mb-4 text-h3">
				{t('author.sermonsBy')} {author.name}
				<span class="text-small font-normal text-muted">({author.sermons.length})</span>
			</h2>
			<ul class="divide-y divide-border">
				{#each author.sermons as sermon (sermon.slug)}
					<li>
						<a
							href={localizeHref(`/sermons/${sermon.slug}`)}
							class="flex items-baseline justify-between gap-3 py-3 hover:no-underline"
						>
							<span class="flex-1">
								<span class="block text-body font-medium text-text">{sermon.title}</span>
								{#if sermon.scripture_ref}
									<span class="text-small text-accent">{sermon.scripture_ref}</span>
								{/if}
							</span>
							<span class="shrink-0 text-[0.8rem] text-muted">
								{Math.max(1, Math.round(sermon.word_count / 200))} {t('common.min')}
							</span>
						</a>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if !author.books.length && !author.sermons.length}
		<p class="mt-10 text-body text-muted">{t('author.empty')}</p>
	{/if}

	<!-- More lives to explore: nearest contemporaries by era. -->
	{#if contemporaries.length}
		<section class="mt-16 border-t border-border pt-8">
			<h2 class="mb-4 text-h3">{t('author.moreLives')}</h2>
			<div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
				{#each contemporaries as c (c.slug)}
					<a
						href={localizeHref(`/authors/${c.slug}`)}
						class="flex items-center gap-3 rounded-card border border-border p-3 hover:border-accent hover:no-underline"
					>
						{#if c.photo_url}
							<img
								src={c.photo_url}
								alt="{t('a11y.portraitOf')} {c.name}"
								loading="lazy"
								class="h-11 w-11 shrink-0 rounded-full border border-border object-cover"
								style="filter: grayscale(1); object-position: {portraitPosition(c.slug)}"
							/>
						{:else}
							<span
								class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-accent-soft text-small font-semibold text-accent"
							>
								{initials(c.name)}
							</span>
						{/if}
						<span class="min-w-0">
							<span class="block truncate text-body font-medium text-text">{c.name}</span>
							{#if c.birth_year}
								<span class="block whitespace-nowrap text-small text-muted"
									>{formatLifespan(c.birth_year, c.death_year, t('common.bornPrefix'))}</span
								>
							{/if}
						</span>
					</a>
				{/each}
			</div>
		</section>
	{/if}
	{/if}
</div>

{#if readerUi.focus}
	<button
		class="fixed end-4 top-4 z-30 rounded-full border border-border bg-surface/90 px-3 py-1.5 text-small text-muted shadow-md backdrop-blur hover:text-text"
		onclick={() => readerUi.exitFocus()}>✕ {t('reader.exitFocus')}</button
	>
{/if}

<!-- Time remaining in the biography. Gated on the prose actually being in
     view: this is a page with a book grid and contemporaries below, so a pill
     claiming "N min left" while scrolling those would be measuring the wrong
     thing. <Reader> supplies `frac` for the prose alone. -->
{#if !readerUi.focus && listen.status === 'idle' && frac > 0.01 && frac < 0.99}
	<div class="min-left" aria-hidden="true">{minutesLeft} {t('sermon.minLeft')}</div>
{/if}

<style>
	/* Featured header pull-quote — a hook above the biography. */
	.author-quote {
		font-family: var(--font-display);
		font-style: italic;
		font-size: 1.5rem;
		line-height: 1.4;
		color: var(--text);
		border-inline-start: 3px solid var(--gold);
		padding-block: 0.1em;
		padding-inline: 1.25rem 0;
	}
	.author-quote::before {
		content: '“';
	}
	.author-quote::after {
		content: '”';
	}

	/* Long-form biography styling. Targets the injected {@html} via :global.
	   Pull-quotes and prayer callouts stand out.

	   Type is NOT set here any more: the element is `.reading.bio`, so size,
	   leading, typeface and colour come from the reader's CSS variables and the
	   text-settings control moves them. Re-declaring them here would silently
	   win over the reader on this one surface. */
	:global(.bio p) {
		margin: 0 0 1.15em;
	}
	:global(.bio h2) {
		font-family: var(--font-display);
		font-size: var(--fs-h2);
		font-weight: 600;
		line-height: 1.25;
		margin: 1.9em 0 0.55em;
	}
	:global(.bio a) {
		color: var(--accent);
	}

	/* Pull-quote: a called-out saying, visually distinct. */
	:global(.bio blockquote) {
		margin: 1.7em 0;
		padding-block: 0.1em;
		padding-inline: 1.25rem 0;
		border-inline-start: 3px solid var(--gold);
		font-size: 1.45rem;
		line-height: 1.45;
		font-style: italic;
		color: var(--text);
	}
	:global(.bio blockquote p) {
		margin: 0;
	}
	:global(.bio blockquote cite) {
		display: block;
		margin-top: 0.55em;
		font-size: 0.9rem;
		font-style: normal;
		color: var(--muted);
	}

	/* Prayer callout: highlights a key time of prayer. `.answered` marks an
	   answer to prayer with the indigo accent instead of gold. */
	:global(.bio .prayer) {
		margin: 1.7em 0;
		padding: 1rem 1.2rem;
		border-radius: var(--radius-card);
		background: color-mix(in srgb, var(--gold) 12%, transparent);
		border: 1px solid color-mix(in srgb, var(--gold) 32%, transparent);
	}
	:global(.bio .prayer > *:last-child) {
		margin-bottom: 0;
	}
	:global(.bio .prayer)::before {
		content: '✦ ' var(--label-in-prayer, 'In prayer');
		display: block;
		margin-bottom: 0.5rem;
		font-family: var(--font-sans);
		font-size: 0.72rem;
		font-weight: 700;
		letter-spacing: 0.09em;
		text-transform: uppercase;
		color: var(--gold);
	}
	:global(.bio .prayer.answered) {
		background: var(--accent-soft);
		border-color: var(--accent-soft-border);
	}
	:global(.bio .prayer.answered)::before {
		content: '✦ ' var(--label-answered, 'Answer to prayer');
		color: var(--accent);
	}
</style>
