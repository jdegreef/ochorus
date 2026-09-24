<script lang="ts">
	import type { BookSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumbLd, hreflangFor, absUrl } from '$lib/seo';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { lang, localeName } from '$lib/lang.svelte';
	import { readingTime } from '$lib/reading';
	import { ORIGINALS_PATH, SHELF_META, STARTERS, shelveOriginals } from '$lib/originals';
	import { volumeNumeral } from '$lib/coverStyles';
	import Seo from '$lib/components/Seo.svelte';
	import BookCard from '$lib/components/BookCard.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';

	// Ochorus Originals is the house imprint — a publisher's shelf, not a person,
	// so it gets this page instead of an author page (see $lib/originals).
	let { data } = $props();
	const shelf = $derived(data.shelf);
	const loadError = $derived(data.loadError);
	const t = i18n.t;

	const canonical = $derived(`${SITE_URL}${localizeHref(ORIGINALS_PATH)}`);
	// Alternates only where the imprint has books: no English fallback, so a
	// locale without any would be an empty shelf.
	// (A build that could not reach the API advertises no alternates for its
	// error panel, rather than hreflangFor's every-locale fallback.)
	const hreflang = $derived(
		shelf.languages.length
			? hreflangFor(ORIGINALS_PATH, shelf.languages.map((l) => l.code))
			: { alternates: [], xDefault: canonical }
	);

	const shelved = $derived(shelveOriginals(shelf.books, shelf.series));
	const bySlug = $derived(new Map(shelf.books.map((b) => [b.slug, b])));
	const totalWords = $derived(shelf.books.reduce((n, b) => n + (b.word_count ?? 0), 0));
	const count = (n: number, one: string, many: string) => `${n} ${n === 1 ? t(one) : t(many)}`;

	// Three covers fanned in the hero: one from each kind of Original, falling
	// back to whatever this language has.
	const fan = $derived.by(() => {
		const picks = ['brave-for-god', 'tukutendereza', 'men-of-prayer-2']
			.map((s) => bySlug.get(s))
			.filter((b): b is BookSummary => !!b);
		for (const b of shelf.books) {
			if (picks.length >= 3) break;
			if (!picks.includes(b)) picks.push(b);
		}
		return picks;
	});
	const starters = $derived(
		STARTERS.flatMap((s) => {
			const book = bySlug.get(s.slug);
			return book ? [{ ...s, book }] : [];
		})
	);
	// Other languages this shelf exists in: the page's own hreflang alternates
	// (already limited to advertised locales), minus the one being read.
	const counts = $derived(new Map(shelf.languages.map((l) => [l.code, l.count])));
	const otherLangs = $derived(hreflang.alternates.filter((a) => a.loc !== lang.current));

	const title = $derived(t('originals.metaTitle'));
	const description = $derived(t('originals.metaDescription'));
	const crumbsLd = $derived(
		breadcrumbLd([
			{ name: t('common.home'), href: localizeHref('/') },
			{ name: t('originals.eyebrow'), href: localizeHref(ORIGINALS_PATH) }
		])
	);
	const listLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'CollectionPage',
			name: t('originals.eyebrow'),
			description,
			url: canonical,
			publisher: { '@type': 'Organization', name: 'Ochorus', url: SITE_URL },
			hasPart: shelf.books.map((b) => ({
				'@type': 'Book',
				name: b.title,
				url: absUrl(localizeHref(`/books/${b.slug}`))
			}))
		})
	);
</script>

<Seo
	{title}
	{description}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og/books.png`}
	structuredData={[crumbsLd, listLd]}
/>

<div class="page-col px-5 py-10">
	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if shelf.books.length === 0}
		<EmptyState message={t('originals.empty')} />
	{:else}
		<!-- No visible breadcrumb: a top-level page's trail is Home > this, which
		     the logo and the H1 already say. The BreadcrumbList stays in the head. -->
		<section class="hero">
			<div>
				<p class="eyebrow text-gold">{t('originals.eyebrow')}</p>
				<h1 class="mt-2 text-balance font-display text-h1 font-semibold leading-tight">{t('originals.title')}</h1>
				<p class="lede mt-4 text-muted">{t('originals.lede')}</p>
				<p class="facts mt-5 text-small text-muted">
					<span>{count(shelf.books.length, 'common.bookOne', 'common.bookMany')}</span>
					{#if shelved.series.length}
						<span aria-hidden="true">·</span>
						<span>
							{count(shelved.series.length, 'originals.seriesOne', 'originals.seriesMany')}
						</span>
					{/if}
					{#if totalWords}
						<span aria-hidden="true">·</span>
						<span>{readingTime(totalWords)}</span>
					{/if}
				</p>
				<a class="btn btn-primary mt-6" href="#shelves">{t('originals.browse')}</a>
			</div>
			<div class="fan" aria-hidden="true">
				{#each fan as book, i (book.slug)}
					<div class="fan-cover" data-i={i}><BookCover {book} priority={i === 1} /></div>
				{/each}
			</div>
		</section>

		{#if starters.length >= 2}
			<section class="mt-4" aria-labelledby="begin-heading">
				<h2 id="begin-heading" class="text-h3 font-display font-semibold">{t('originals.begin')}</h2>
				<ul class="starters mt-3">
					{#each starters as s (s.slug)}
						<li>
							<a class="starter card-lift" href={localizeHref(`/books/${s.book.slug}`)}>
								<span class="starter-cover"><BookCover book={s.book} /></span>
								<span class="min-w-0">
									<span class="eyebrow block text-muted">
										{t(s.labelKey)}
									</span>
									<span class="mt-0.5 block font-display text-body font-semibold text-text">
										{s.book.title}
									</span>
									{#if s.book.word_count}
										<span class="block text-small text-accent">
											{readingTime(s.book.word_count)} →
										</span>
									{/if}
								</span>
							</a>
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		<div id="shelves" class="jump-anchor">
			{#if shelved.series.length}
				<section class="mt-14" aria-labelledby="series-heading">
					<h2 id="series-heading" class="section-heading">
						{t('originals.seriesHeading')}
						<span class="meta">· {shelved.series.length}</span>
					</h2>
					{#each shelved.series as s (s.slug)}
						<div class="series-row">
							<div>
								<h3 class="text-h3 font-display font-semibold text-balance">
									<a class="hover:text-accent" href={localizeHref(`/series/${s.slug}`)}>{s.title}</a>
								</h3>
								{#if s.description}
									<p class="mt-1 text-small text-muted">{s.description}</p>
								{/if}
								<p class="mt-2 text-eyebrow text-muted">
									<!-- Separator as an expression: a literal space at an {#if}
									     boundary is compiler-trimmed ("2 books· 2 hr"). -->
									{count(s.books.length, 'common.bookOne', 'common.bookMany')}{#if s.words}{` · ${readingTime(s.words)}`}{/if}
								</p>
								<a class="mt-2 inline-block text-small font-semibold text-accent" href={localizeHref(`/books/${s.books[0].slug}`)}>
									{t('originals.startSeries').replace(
										'%n%',
										volumeNumeral(s.books[0].series_position, lang.current) ?? '1'
									)} →
								</a>
							</div>
							<ol class="series-covers">
								{#each s.books as book (book.slug)}
									<li>
										<a href={localizeHref(`/books/${book.slug}`)} class="card-lift block" aria-label={book.title}>
											<BookCover {book} />
										</a>
										{#if book.series_position}
											<p class="mt-1.5 text-center text-eyebrow text-muted">
												{t('originals.volume').replace('%n%', volumeNumeral(book.series_position, lang.current) ?? '')}
											</p>
										{/if}
									</li>
								{/each}
							</ol>
						</div>
					{/each}
				</section>
			{/if}

			{#each shelved.shelves as group (group.key)}
				<section class="mt-14" aria-labelledby="shelf-{group.key}">
					<h2 id="shelf-{group.key}" class="section-heading">
						{t(SHELF_META[group.key].label)}
						<span class="meta">· {group.books.length}</span>
					</h2>
					{#if SHELF_META[group.key].note}
						<p class="-mt-2 mb-5 text-small text-muted">{t(SHELF_META[group.key].note ?? '')}</p>
					{/if}
					<div class="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-5">
						{#each group.books as book (book.slug)}
							<BookCard {book} />
						{/each}
					</div>
				</section>
			{/each}
		</div>

		<section class="colophon mt-16">
			<div>
				<p class="eyebrow text-gold">{t('originals.whyEyebrow')}</p>
				<h2 class="mt-1 text-h2 font-display font-semibold">{t('originals.whyTitle')}</h2>
				<p class="mt-2 text-small text-muted">{t('originals.whyBody')}</p>
			</div>
			{#if otherLangs.length}
				<div>
					<p class="eyebrow text-gold">{t('originals.langsEyebrow')}</p>
					<p class="mt-2 text-small text-muted">{t('originals.langsBody')}</p>
					<ul class="mt-3 flex flex-wrap gap-2">
						{#each otherLangs as l (l.loc)}
							<li>
								<a
									class="tag"
									href={l.href}
									hreflang={l.loc}
									lang={l.loc}
									data-sveltekit-reload
								>
									{localeName(l.loc)} <span class="count">{counts.get(l.loc)}</span>
								</a>
							</li>
						{/each}
					</ul>
				</div>
			{/if}
		</section>
	{/if}
</div>

<style>
	.hero {
		display: grid;
		grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
		gap: 2.5rem;
		align-items: center;
		padding-block: 1rem 2.5rem;
	}
	.lede {
		max-width: 52ch;
		font-size: var(--fs-body);
		line-height: 1.65;
	}
	.facts {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 0.6rem;
		font-variant-numeric: tabular-nums;
	}
	/* Three covers fanned from a shared bottom edge. Symmetric, so it needs no
	   RTL flip. */
	.fan {
		position: relative;
		height: 22rem;
	}
	.fan-cover {
		position: absolute;
		inset-inline-start: 25%;
		top: 1.5rem;
		width: 50%;
		transform-origin: bottom center;
	}
	.fan-cover[data-i='0'] {
		transform: rotate(-10deg) translateX(-36%);
	}
	.fan-cover[data-i='1'] {
		z-index: 1;
		top: 0.5rem;
	}
	.fan-cover[data-i='2'] {
		transform: rotate(10deg) translateX(36%);
	}
	.starters {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 0.875rem;
	}
	.starter {
		display: grid;
		grid-template-columns: 4rem minmax(0, 1fr);
		gap: 0.875rem;
		align-items: center;
		height: 100%;
		padding: 0.875rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.series-row {
		display: grid;
		grid-template-columns: 14rem minmax(0, 1fr);
		gap: 1.5rem;
		padding-block: 1.25rem;
		border-bottom: 1px solid var(--border);
	}
	.series-row:last-child {
		border-bottom: 0;
	}
	.series-covers {
		display: grid;
		grid-template-columns: repeat(6, minmax(0, 1fr));
		gap: 0.875rem;
		align-content: start;
	}
	.colophon {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 2rem;
		padding: 1.75rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.colophon p {
		max-width: 56ch;
	}
	@media (max-width: 900px) {
		.starters {
			grid-template-columns: minmax(0, 1fr);
		}
		.series-row {
			grid-template-columns: minmax(0, 1fr);
			gap: 0.75rem;
		}
	}
	@media (max-width: 640px) {
		.hero {
			grid-template-columns: minmax(0, 1fr);
			gap: 0.5rem;
			padding-block: 0 1.5rem;
		}
		.fan {
			order: -1;
			height: 15rem;
		}
		.fan-cover {
			inset-inline-start: 29%;
			width: 42%;
		}
		/* A six-volume series scrolls sideways rather than shrinking to stamps. */
		.series-covers {
			grid-template-columns: none;
			grid-auto-flow: column;
			grid-auto-columns: 38%;
			overflow-x: auto;
			padding-bottom: 0.5rem;
			scroll-snap-type: x mandatory;
		}
		.series-covers > li {
			scroll-snap-align: start;
		}
		.colophon {
			grid-template-columns: minmax(0, 1fr);
			padding: 1.25rem;
		}
	}
</style>
