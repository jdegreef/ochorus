<script lang="ts">
	import { type AuthorDetail, type AuthorBio, listAuthors } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd, breadcrumb } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref, locales } from '$lib/paraglide/runtime';
	import { listen } from '$lib/listen.svelte';
	import { getLang } from '$lib/lang.svelte';
	import BookCard from '$lib/components/BookCard.svelte';
	import ListenBar from '$lib/components/ListenBar.svelte';
	import { onDestroy, onMount } from 'svelte';

	const t = i18n.t;

	let { data } = $props();
	const author = $derived<AuthorDetail>(data.author);

	// Read the long-form biography aloud (device Text-to-Speech), same engine as
	// the chapter/sermon reader. Each top-level block is one utterance.
	let bioEl = $state<HTMLElement | undefined>();
	function startListening() {
		if (!bioEl) return;
		const paragraphs = [...bioEl.children].map((el) => (el as HTMLElement).innerText);
		listen.start(paragraphs, 0, getLang(), { title: author.name, artist: t('bios.eyebrow') });
	}
	onDestroy(() => listen.stop());

	const initials = (name: string) =>
		name.split(' ').filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase();

	const years = $derived(
		author.birth_year ? `${author.birth_year}–${author.death_year ?? ''}` : ''
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
	const alternates = $derived(
		locales.map((loc) => ({ loc, href: `${SITE_URL}${localizeHref(path, { locale: loc })}` }))
	);
	const description = $derived(
		(author.bio || `${author.name} on Ochorus — free classic Christian books.`).slice(0, 300)
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
	const bioLabels = $derived(
		`--label-in-prayer: '${t('bios.inPrayer')}'; --label-answered: '${t('bios.answerToPrayer')}'`
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

<svelte:head>
	<title>{author.name} — Ochorus</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={canonical} />
	{#each alternates as a (a.loc)}
		<link rel="alternate" hreflang={a.loc} href={a.href} />
	{/each}
	<link rel="alternate" hreflang="x-default" href="{SITE_URL}{localizeHref(path, { locale: 'en' })}" />
	<meta property="og:type" content="profile" />
	<meta property="og:title" content="{author.name} — Ochorus" />
	<meta property="og:description" content={description} />
	<meta property="og:url" content={canonical} />
	{#if ogImage}<meta property="og:image" content={ogImage} />{/if}
	<meta name="twitter:card" content={ogImage ? 'summary_large_image' : 'summary'} />
	{@html personLd}
	{@html crumbsLd}
</svelte:head>

<div class="mx-auto max-w-3xl px-5 py-10">
	<!-- Breadcrumb -->
	<nav class="mb-6 flex flex-wrap items-center gap-1.5 text-small text-muted" aria-label={t('a11y.breadcrumb')}>
		<a href={localizeHref('/')} class="hover:text-text">{t('common.home')}</a>
		<span>›</span>
		<a href={localizeHref('/biographies')} class="hover:text-text">{t('bios.eyebrow')}</a>
		<span>›</span>
		<span class="text-text">{author.name}</span>
	</nav>

	<header class="flex items-center gap-5">
		{#if author.photo_url}
			<img
				src={author.photo_url}
				alt="{t('a11y.portraitOf')} {author.name}"
				class="h-24 w-24 shrink-0 rounded-full border border-border object-cover shadow-sm"
				style="filter: grayscale(1)"
			/>
		{:else}
			<span
				class="flex h-24 w-24 shrink-0 items-center justify-center rounded-full bg-accent-soft text-h1 font-semibold text-accent"
				style="font-family: var(--font-display)"
			>
				{initials(author.name)}
			</span>
		{/if}
		<div class="min-w-0">
			<h1 class="text-h1">{author.name}</h1>
			{#if summaryBits.length}
				<p class="mt-1 text-body text-muted">
					{#each summaryBits as bit, i (i)}{#if i > 0}<span class="opacity-50"> · </span>{/if}{bit}{/each}
				</p>
			{/if}
		</div>
		{#if listen.supported && author.bio_html}
			<button
				class="btn btn-ghost ml-auto shrink-0 !px-2.5 !py-1"
				class:!text-accent={listen.status !== 'idle'}
				onclick={() => (listen.status === 'idle' ? startListening() : listen.stop())}
				aria-label={t('reader.listen')}
				title={t('reader.listen')}>▶ {t('reader.listen')}</button
			>
		{/if}
	</header>

	<!-- Featured pull-quote: a hook above the biography. -->
	{#if featuredQuote}
		<blockquote class="author-quote mx-auto mt-8 max-w-[40rem]">{featuredQuote}</blockquote>
	{/if}

	<!-- Biography -->
	{#if author.bio_html}
		<div class="bio mx-auto mt-8 max-w-[40rem]" style={bioLabels} bind:this={bioEl}>
			<!-- Long-form biography; cleaned HTML with pull-quotes + prayer callouts. -->
			{@html author.bio_html}
		</div>
	{:else if author.bio}
		<p class="mt-6 text-body leading-relaxed text-muted">{author.bio}</p>
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
								style="filter: grayscale(1)"
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
								<span class="block text-small text-muted">{c.birth_year}–{c.death_year ?? ''}</span>
							{/if}
						</span>
					</a>
				{/each}
			</div>
		</section>
	{/if}
</div>

<ListenBar />

<style>
	/* Featured header pull-quote — a hook above the biography. */
	.author-quote {
		font-family: var(--font-display);
		font-style: italic;
		font-size: 1.5rem;
		line-height: 1.4;
		color: var(--text);
		border-left: 3px solid var(--gold);
		padding: 0.1em 0 0.1em 1.25rem;
	}
	.author-quote::before {
		content: '“';
	}
	.author-quote::after {
		content: '”';
	}

	/* Long-form biography styling. Targets the injected {@html} via :global.
	   Prose in the reading serif; pull-quotes and prayer callouts stand out. */
	:global(.bio) {
		font-family: var(--font-display);
		font-size: 1.12rem;
		line-height: 1.8;
		color: var(--text);
	}
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
		padding: 0.1em 0 0.1em 1.25rem;
		border-left: 3px solid var(--gold);
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
