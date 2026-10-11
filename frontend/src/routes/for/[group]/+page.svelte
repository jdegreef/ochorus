<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import BookCard from '$lib/components/BookCard.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import Emblem from '$lib/components/Emblem.svelte';
	import ForInvite from '$lib/components/ForInvite.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import PersonCard from '$lib/components/PersonCard.svelte';
	import PlanShelfCard from '$lib/components/PlanShelfCard.svelte';
	import QandA from '$lib/components/QandA.svelte';
	import QuoteText from '$lib/components/QuoteText.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import ShelfDownloadControl from '$lib/components/ShelfDownloadControl.svelte';
	import { scrollEdges } from '$lib/actions/scrollEdges';
	import { API_BASE_URL, SITE_URL } from '$lib/config';
	import { FOR_INDEX, FOR_LINKS, forPath } from '$lib/forLinks';
	import { FOR_META } from '$lib/forMeta';
	import { localizeHref } from '$lib/href';
	import { countsLine, forHref, inviteMessage } from '$lib/forPages';
	import { RUNG_LABEL } from '$lib/audienceHub';
	import { hrefInLocale } from '$lib/editionHref';
	import { readingTime } from '$lib/reading';
	import { LIVE_LOCALES } from '$lib/live-locales.generated';
	import { citeLine, guideCardLink, quoteHref, toBookTile } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';
	import { hreflangFor, itemList, jsonLd, pickQa } from '$lib/seo';

	/**
	 * An "Ochorus for …" page ($lib/forPages) — a landing page for one group of
	 * readers: the library's numbers, why Ochorus is worth their while, a line
	 * from one of its writers, plans to read together, ways to use it, themed
	 * shelves, the writers themselves, printable leader's guides and an offline
	 * pack where the group needs them, a message to pass on, their questions,
	 * and a way in. English-only, like the
	 * footer row that links here, so the copy is content from the data module
	 * rather than catalogue keys.
	 *
	 * Each group wears its own accent and emblem (FOR_META) — the topic hero's
	 * wash and chip — so nine pages built from one template don't read as copies.
	 * The bands below borrow About's eyebrow-and-heading rhythm, inside the page
	 * column.
	 */
	let { data } = $props();

	const page = $derived(data.page);
	const shelf = $derived(data.shelf);
	// forCards.test.ts pins one entry per page, so the lookup cannot miss.
	const meta = $derived(FOR_META[page.slug]);
	const path = $derived(forPath(page.slug));
	const canonical = $derived(`${SITE_URL}${path}`);
	const fan = $derived(shelf.shelves[0]?.books ?? []);
	const qa = $derived(pickQa(page.questions, []));
	const invite = $derived(inviteMessage(page.invite, SITE_URL));
	/** The numbers strip: the library in English, and every language it serves. */
	const counts = $derived(
		shelf.counts && [
			{ value: shelf.counts.books, name: 'books' },
			{ value: shelf.counts.sermons, name: 'sermons' },
			{ value: shelf.counts.plans, name: 'reading plans' },
			{ value: LIVE_LOCALES.length, name: 'languages' }
		].filter((c) => c.value > 0)
	);
	// Each shelf as a schema.org ItemList: an ordered roster of the works, where
	// the grid alone is opaque to a search engine.
	const shelvesLd = $derived(
		shelf.shelves.map((s) =>
			itemList(
				s.title,
				s.books.map((b) => ({ name: b.title, url: `/books/${b.slug}/` }))
			)
		)
	);
	const pageLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'WebPage',
			name: page.title,
			description: page.seoDescription,
			url: canonical,
			inLanguage: 'en',
			isPartOf: { '@type': 'WebSite', name: 'Ochorus', url: SITE_URL },
			isAccessibleForFree: true
		})
	);
</script>

<Seo
	title="{page.seoTitle} — Ochorus"
	description={page.seoDescription}
	{canonical}
	hreflang={hreflangFor(path, ['en'])}
	ogImage="{SITE_URL}/og/for/{page.slug}.png"
	ogImageAlt="Ochorus for {meta.phrase}"
	ogImageWidth={1200}
	ogImageHeight={630}
	structuredData={[pageLd, ...shelvesLd, ...(qa.ld ? [qa.ld] : [])]}
/>

<div class="page-col px-5 py-10" lang="en" style="--group: {meta.accent}; --pinned-offset: var(--appnav-h, 4rem)">
	<!-- Every group, one tap apart: a reader who is both a parent and a youth
	     leader, or who landed on the wrong page, moves sideways from here. -->
	<nav class="chip-scroller mb-6" use:scrollEdges aria-label="Who Ochorus is for">
		<a class="chip" href={FOR_INDEX}>All</a>
		{#each FOR_LINKS as l (l.slug)}
			<a
				class="chip"
				class:active={l.slug === page.slug}
				aria-current={l.slug === page.slug ? 'page' : undefined}
				href={forPath(l.slug)}>{l.label}</a
			>
		{/each}
	</nav>

	<section class="hero group-wash">
		<div class="min-w-0">
			<div class="flex items-center gap-3">
				<span class="badge emblem-chip group-chip"><Emblem name={meta.emblem} /></span>
				<p class="eyebrow group-ink">Ochorus for {meta.phrase}</p>
			</div>
			<h1 class="mt-3 text-balance font-display text-h1 font-semibold leading-tight">{page.title}</h1>
			<p class="lede mt-4 text-muted">{page.lead}</p>
			<div class="mt-6 flex flex-wrap gap-3">
				<a class="btn btn-primary" href={localizeHref(forHref(page.primary.href, shelf))}>{page.primary.label}</a>
				<a class="btn btn-ghost" href={localizeHref(forHref(page.secondary.href, shelf))}>{page.secondary.label}</a>
			</div>
		</div>
		{#if fan.length}
			<div class="fan">
				<CoverStrip covers={fan.map(toBookTile)} size="fan" priority />
			</div>
		{/if}
	</section>

	{#if counts}
		<!-- What "a free library" amounts to, counted at build time. -->
		<dl class="counts mt-6">
			{#each counts as c (c.name)}
				<div class="count-tile rounded-card border border-border bg-surface px-4 py-3">
					<dt class="text-small text-muted">{c.name}</dt>
					<dd class="font-display text-h2 group-ink">{c.value.toLocaleString('en')}</dd>
				</div>
			{/each}
		</dl>
	{/if}

	<section class="mt-12" aria-labelledby="why-heading">
		<h2 id="why-heading" class="text-h2">{page.pointsHeading}</h2>
		<ul class="points mt-6">
			{#each page.points as p (p.title)}
				<li class="point rounded-card border border-border bg-surface p-5">
					<span class="point-icon group-ink flex h-10 w-10 items-center justify-center rounded-full"
						><Icon name={p.icon} size={22} /></span
					>
					<h3 class="mt-3 text-h3">{p.title}</h3>
					<p class="mt-2 text-body text-muted">{p.body}</p>
					{#if p.link}
						<p class="mt-3 text-small">
							<a class="text-accent hover:underline" href={localizeHref(forHref(p.link.href, shelf))}>{p.link.label} <Arrow /></a>
						</p>
					{/if}
				</li>
			{/each}
		</ul>
	</section>

	{#if shelf.quote}
		<figure class="quote-band group-wash mt-14 rounded-card px-6 py-8 sm:px-10">
			<blockquote class="font-display text-h2 leading-snug">
				<a class="quote-link" href={localizeHref(quoteHref(shelf.quote))}>“<QuoteText text={shelf.quote.text} />”</a>
			</blockquote>
			<figcaption class="mt-3 text-small text-muted">
				<a class="group-ink font-semibold hover:underline" href={localizeHref(`/quotes/${shelf.quote.author.slug}`)}
					>{shelf.quote.author.name}</a
				>, <cite>{citeLine(shelf.quote)}</cite>
			</figcaption>
		</figure>
	{/if}

	{#if shelf.plans.length}
		<section id="plans" class="jump-anchor mt-14" aria-labelledby="plans-heading">
			<h2 id="plans-heading" class="text-h2">Plans to read together</h2>
			<p class="mt-2 max-w-2xl text-body text-muted">
				One short reading a day. Start on the same day and everyone reaches the same chapter together, each
				reader ticking off their own progress as they go.
			</p>
			<div class="mt-6 grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-3">
				{#each shelf.plans as plan (plan.slug)}
					<PlanShelfCard {plan} headingLevel={3} />
				{/each}
			</div>
			<p class="mt-4 text-small">
				<a class="text-accent hover:underline" href={localizeHref('/plans')}>See every reading plan <Arrow /></a>
			</p>
		</section>
	{/if}

	{#if shelf.series.length}
		<!-- A sermon a week, each with the study questions its page answers:
		     a term's evenings for a group, ready-made. -->
		<section id="series" class="jump-anchor mt-14" aria-labelledby="series-heading">
			<h2 id="series-heading" class="text-h2">A sermon series for your group</h2>
			<p class="mt-2 max-w-2xl text-body text-muted">
				Read one sermon at home each week, then talk it through together. Every sermon here comes with study
				questions and their answers, at the foot of the sermon.
			</p>
			{#each shelf.series as s (s.title)}
				<div class="mt-8">
					<GroupHeading name={s.title} as="h3" blurb={s.note} />
					<ol class="weeks">
						{#each s.sermons as w, i (w.slug)}
							<li class="week rounded-card border border-border bg-surface p-4">
								<p class="text-eyebrow group-ink">Week {i + 1}</p>
								<a class="mt-1 block font-semibold text-text hover:underline" href={localizeHref(`/sermons/${w.slug}`)}
									>{w.title}</a
								>
								<p class="mt-1 text-small text-muted">
									{w.author.name}{#if w.scripture_ref},{' '}{w.scripture_ref}{/if}
								</p>
								<p class="mt-2 text-small text-muted">
									{w.questions} study {w.questions === 1 ? 'question' : 'questions'}{' '}<span class="opacity-50" aria-hidden="true">·</span>{' '}{readingTime(w.word_count)}
								</p>
							</li>
						{/each}
					</ol>
				</div>
			{/each}
		</section>
	{/if}

	<section class="mt-14" aria-labelledby="ideas-heading">
		<h2 id="ideas-heading" class="text-h2">{page.ideasHeading}</h2>
		<ol class="ideas mt-6">
			{#each page.ideas as idea, i (idea.title)}
				<li class="idea">
					<span class="idea-num font-display text-h2 group-ink" aria-hidden="true">{i + 1}</span>
					<div>
						<h3 class="text-h3">{idea.title}</h3>
						<p class="mt-1 text-body text-muted">{idea.body}</p>
					</div>
				</li>
			{/each}
		</ol>
	</section>

	{#if shelf.shelves.length}
		<section id="shelves" class="jump-anchor mt-14" aria-labelledby="shelves-heading">
			<h2 id="shelves-heading" class="text-h2">Good places to start</h2>
			{#each shelf.shelves as s (s.title)}
				<div class="mt-8">
					<GroupHeading name={s.title} as="h3" blurb={s.note} />
					<div class="book-grid">
						{#each s.books as book (book.slug)}
							<BookCard {book} showAuthor />
						{/each}
					</div>
				</div>
			{/each}
		</section>
	{/if}

	{#if shelf.levels.length}
		<!-- The edition family side by side (the slug convention is the link —
		     root CLAUDE.md): one work, read at seven, at fourteen and in full. -->
		<section class="mt-14" aria-labelledby="levels-heading">
			<h2 id="levels-heading" class="text-h2">One story, three reading levels</h2>
			<p class="mt-2 max-w-2xl text-body text-muted">
				Many classics come as a children’s edition, a teens edition and the full text, so readers of every age
				can read the same book, and a child can grow into the original.
			</p>
			<div class="families mt-6">
				{#each shelf.levels as family (family[0].book.slug)}
					<ol class="levels" aria-label={family.at(-1)?.book.title}>
						{#each family as { rung, book } (book.slug)}
							<li>
								<p class="mb-2 text-eyebrow group-ink">{i18n.t(RUNG_LABEL[rung])}</p>
								<BookCard {book} showAuthor showSeries={false} />
							</li>
						{/each}
					</ol>
				{/each}
			</div>
		</section>
	{/if}

	{#if shelf.authors.length}
		<section class="mt-14" aria-labelledby="writers-heading">
			<h2 id="writers-heading" class="text-h2">Meet the writers</h2>
			<p class="mt-2 max-w-2xl text-body text-muted">
				The lives behind the books: each one has a full biography, with the books and sermons they left.
			</p>
			<ul class="writers mt-6">
				{#each shelf.authors as person (person.slug)}
					<li><PersonCard {person} /></li>
				{/each}
			</ul>
			<p class="mt-4 text-small">
				<a class="text-accent hover:underline" href={localizeHref('/biographies')}>See every biography <Arrow /></a>
			</p>
		</section>
	{/if}

	{#if shelf.guides.length}
		<!-- For the adult running a group: each card opens the book's printable
		     leader's guide, not the book (the young-reader hubs' recipe). -->
		<section id="guides" class="jump-anchor mt-14" aria-labelledby="guides-heading">
			<h2 id="guides-heading" class="text-h2">Printable leader’s guides</h2>
			<p class="mt-2 max-w-2xl text-body text-muted">
				A week-by-week guide to each of these books for children and teens: a summary for the leader, a memory
				verse, questions with their answers and an activity, one chapter a week. Print it, or lead from the
				screen.
			</p>
			<div class="book-grid mt-6">
				{#each shelf.guides as book (book.slug)}
					<BookCard
						{book}
						showAuthor
						showSeries={false}
						link={guideCardLink(book, i18n.t)}
					/>
				{/each}
			</div>
		</section>
	{/if}

	{#if shelf.offline.length}
		<section id="offline" class="jump-anchor mt-14" aria-labelledby="offline-heading">
			<div class="flex flex-wrap items-baseline gap-x-4 gap-y-2">
				<h2 id="offline-heading" class="text-h2">Take them offline</h2>
				<ShelfDownloadControl
					shelf="for-{page.slug}"
					label="Save all to this device"
					books={shelf.offline.map((o) => ({ slug: o.book.slug, language: o.book.language }))}
				/>
			</div>
			<p class="mt-2 max-w-2xl text-body text-muted">{page.offline?.note}</p>
			<ul class="offline mt-6">
				{#each shelf.offline as o (o.book.slug)}
					{@const href = localizeHref(`/books/${o.book.slug}`)}
					<li class="offline-row rounded-card border border-border bg-surface p-3">
						<a class="offline-cover" {href} tabindex="-1" aria-hidden="true"
							><BookCover book={o.book} rounded="rounded" /></a
						>
						<div class="min-w-0">
							<a class="font-semibold text-text hover:underline" {href}
								>{o.book.title}</a
							>
							<p class="text-small text-muted">{o.book.author.name}</p>
							<p class="mt-2 flex flex-wrap gap-2">
								{#if o.pdf_url}
									<a class="btn btn-sm" href={o.pdf_url} download
										><Icon name="download" size={14} /> PDF<span class="sr-only"> of {o.book.title}</span></a
									>
								{/if}
								{#if o.epub_url}
									<a class="btn btn-sm" href="{API_BASE_URL}{o.epub_url}" download rel="nofollow"
										><Icon name="book" size={14} /> EPUB<span class="sr-only"> of {o.book.title}</span></a
									>
								{/if}
							</p>
						</div>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if shelf.languages.length}
		<!-- What each live language holds, from its own lists (no English
		     fallback): the honest answer to "what can I hand a Swahili speaker?" -->
		<section id="languages" class="jump-anchor mt-14" aria-labelledby="languages-heading">
			<h2 id="languages-heading" class="text-h2">In the languages you serve</h2>
			<p class="mt-2 max-w-2xl text-body text-muted">
				Each language has its own library of full editions. Send someone straight to theirs, and the whole site
				reads in that language.
			</p>
			<ul class="languages mt-6">
				{#each shelf.languages as l (l.code)}
					<li class="language rounded-card border border-border bg-surface p-4">
						<h3 class="text-h3"><span lang={l.code}>{l.native}</span></h3>
						{#if l.native !== l.name}<p class="text-small text-muted">{l.name}</p>{/if}
						<p class="mt-2 text-small text-muted">
							{countsLine(l.counts)}
						</p>
						{#if l.covers.length}
							<ul class="language-covers mt-3" lang={l.code}>
								{#each l.covers as book (book.slug)}
									<li>
										<a href={hrefInLocale(`/books/${book.slug}`, l.code)} title={book.title}
											><BookCover {book} rounded="rounded" /><span class="sr-only">{book.title}</span></a
										>
									</li>
								{/each}
							</ul>
						{/if}
						<p class="mt-3 text-small">
							<a class="text-accent hover:underline" href={hrefInLocale('/books', l.code)}>Open the {l.name} library <Arrow /></a>
						</p>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	<section class="mt-14" aria-labelledby="invite-heading">
		<h2 id="invite-heading" class="text-h2">Pass it on</h2>
		<p class="mt-2 max-w-2xl text-body text-muted">
			A message ready for a bulletin, a group chat or an email. Copy it as it is, or make it your own.
		</p>
		<div class="mt-6 max-w-2xl">
			<ForInvite message={invite} subject="Free Christian classics on Ochorus" />
		</div>
	</section>

	<QandA items={qa.items} title="Questions" headingClass="text-h2" />

	<section class="group-wash mt-14 flex flex-col items-center rounded-card px-6 py-10 text-center sm:px-10">
		<span class="badge emblem-chip group-chip"><Emblem name={meta.emblem} /></span>
		<h2 class="mt-4 max-w-[22ch] text-h2">{page.closeHeading}</h2>
		<p class="mt-3 max-w-xl text-body text-muted">{page.closeBody}</p>
		<div class="mt-6 flex flex-wrap justify-center gap-3">
			<a class="btn btn-primary" href={localizeHref(forHref(page.primary.href, shelf))}>{page.primary.label}</a>
			<a class="btn btn-ghost" href={localizeHref('/contact')}>Contact us</a>
		</div>
	</section>
</div>

<style>
	.hero {
		display: grid;
		grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
		gap: 2.5rem;
		align-items: center;
		padding: 2rem;
		border-radius: var(--radius-card);
	}
	/* The hero's buttons jump to these; clear the pinned header on arrival. */
	.jump-anchor {
		scroll-margin-top: calc(var(--pinned-offset) + 0.5rem);
	}
	.badge {
		--chip-size: 3.5rem;
	}
	.point-icon {
		background: color-mix(in srgb, var(--group) 14%, var(--color-surface));
	}
	/* As many columns as there are tiles (a zero count drops its tile), two to a
	   row on a phone. */
	.counts {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
		gap: 0.75rem;
	}
	.count-tile dd {
		line-height: 1.1;
		font-variant-numeric: tabular-nums;
	}
	.quote-link {
		color: var(--color-text);
		text-decoration: none;
	}
	.quote-link:hover {
		text-decoration: underline;
		text-decoration-thickness: 1px;
	}
	.writers {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 0.75rem;
	}
	.lede {
		max-width: 52ch;
		font-size: var(--fs-body);
		line-height: 1.65;
	}
	.points {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 1rem;
	}
	.ideas {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 1.75rem 2.5rem;
	}
	.idea {
		display: grid;
		grid-template-columns: 2rem minmax(0, 1fr);
		gap: 0.75rem;
		align-items: baseline;
	}
	.idea-num {
		line-height: 1;
	}
	.offline {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.75rem;
	}
	.offline-row {
		display: grid;
		grid-template-columns: 3.5rem minmax(0, 1fr);
		gap: 0.875rem;
		align-items: start;
	}
	.offline-cover {
		display: block;
	}
	.weeks,
	.levels {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 0.75rem;
	}
	/* Two works side by side where there is room, each its own row of three. */
	.families {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 26rem), 1fr));
		gap: 2rem 2.5rem;
	}
	.languages {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.75rem;
	}
	.language-covers {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 4.5rem));
		gap: 0.5rem;
	}
	@media (max-width: 1023.98px) {
		.weeks,
		.writers {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (max-width: 639.98px) {
		.hero {
			grid-template-columns: minmax(0, 1fr);
			gap: 0.5rem;
			padding: 1.25rem;
		}
		/* The fan sizes off its own width; on a phone it leads, as on /originals. */
		.fan {
			order: -1;
			margin-bottom: 0.75rem;
		}
		.points,
		.ideas,
		.offline,
		.writers,
		.weeks,
		.languages {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
