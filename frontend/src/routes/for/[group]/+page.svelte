<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import BookCard from '$lib/components/BookCard.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import Emblem from '$lib/components/Emblem.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import PlanShelfCard from '$lib/components/PlanShelfCard.svelte';
	import QandA from '$lib/components/QandA.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import ShelfDownloadControl from '$lib/components/ShelfDownloadControl.svelte';
	import { scrollEdges } from '$lib/actions/scrollEdges';
	import { API_BASE_URL, SITE_URL } from '$lib/config';
	import { FOR_INDEX, FOR_LINKS, forPath } from '$lib/forLinks';
	import { FOR_META } from '$lib/forMeta';
	import { localizeHref } from '$lib/href';
	import { guideCardLink, toBookTile } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';
	import { hreflangFor, jsonLd, pickQa } from '$lib/seo';

	/**
	 * An "Ochorus for …" page ($lib/forPages) — a landing page for one group of
	 * readers: why Ochorus is worth their while, plans to read together, ways to
	 * use it, themed shelves, printable leader's guides and an offline pack where
	 * the group needs them, their questions, and a way in. English-only, like the
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
	structuredData={[pageLd, ...(qa.ld ? [qa.ld] : [])]}
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
				<a class="btn btn-primary" href={localizeHref(page.primary.href)}>{page.primary.label}</a>
				<a class="btn btn-ghost" href={localizeHref(page.secondary.href)}>{page.secondary.label}</a>
			</div>
		</div>
		{#if fan.length}
			<div class="fan">
				<CoverStrip covers={fan.map(toBookTile)} size="fan" priority />
			</div>
		{/if}
	</section>

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
							<a class="text-accent hover:underline" href={localizeHref(p.link.href)}>{p.link.label} <Arrow /></a>
						</p>
					{/if}
				</li>
			{/each}
		</ul>
	</section>

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
					<GroupHeading name={s.title} as="h3" />
					<p class="-mt-2 mb-5 max-w-2xl text-small text-muted">{s.note}</p>
					<div class="book-grid">
						{#each s.books as book (book.slug)}
							<BookCard {book} showAuthor />
						{/each}
					</div>
				</div>
			{/each}
		</section>
	{/if}

	{#if shelf.guides.length}
		<!-- For the adult running a group: each card opens the book's printable
		     leader's guide, not the book (the young-reader hubs' recipe). -->
		<section id="guides" class="jump-anchor mt-14" aria-labelledby="guides-heading">
			<h2 id="guides-heading" class="text-h2">Printable leader’s guides</h2>
			<p class="mt-2 max-w-2xl text-body text-muted">
				A week-by-week guide to each of these books for children: a summary for the leader, a memory verse,
				questions with their answers and a simple activity, one chapter a week. Print it, or lead from the
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

	<QandA items={qa.items} title="Questions" headingClass="text-h2" />

	<section class="group-wash mt-14 flex flex-col items-center rounded-card px-6 py-10 text-center sm:px-10">
		<span class="badge emblem-chip group-chip"><Emblem name={meta.emblem} /></span>
		<h2 class="mt-4 max-w-[22ch] text-h2">{page.closeHeading}</h2>
		<p class="mt-3 max-w-xl text-body text-muted">{page.closeBody}</p>
		<div class="mt-6 flex flex-wrap justify-center gap-3">
			<a class="btn btn-primary" href={localizeHref(page.primary.href)}>{page.primary.label}</a>
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
		.offline {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
