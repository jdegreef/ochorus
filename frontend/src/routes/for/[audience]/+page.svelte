<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import BookCard from '$lib/components/BookCard.svelte';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import QandA from '$lib/components/QandA.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { SITE_URL } from '$lib/config';
	import { FOR_LINKS, forPath } from '$lib/forLinks';
	import { localizeHref } from '$lib/href';
	import { toBookTile } from '$lib/library-public';
	import { hreflangFor, jsonLd, pickQa } from '$lib/seo';

	/**
	 * An "Ochorus for …" page ($lib/forPages) — a short landing page for one
	 * group of readers: why Ochorus is worth their while, ways to use it, books
	 * to start with, their questions, and a way in. English-only, like the
	 * footer row that links here, so the copy is content from the data module
	 * rather than catalogue keys.
	 *
	 * The head is the /originals hero (text beside a fan of covers); the bands
	 * below borrow About's eyebrow-and-heading rhythm, inside the page column.
	 */
	let { data } = $props();

	const page = $derived(data.page);
	// Six fill one row of the desktop grid; the list runs longer so an
	// unpublished pick leaves a backup in its place rather than a gap.
	const books = $derived(data.books.slice(0, 6));
	const path = $derived(forPath(page.slug));
	const canonical = $derived(`${SITE_URL}${path}`);
	const others = $derived(FOR_LINKS.filter((l) => l.slug !== page.slug));
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
	structuredData={[pageLd, ...(qa.ld ? [qa.ld] : [])]}
/>

<div class="page-col px-5 py-10" lang="en">
	<section class="hero">
		<div>
			<p class="eyebrow text-gold">{page.eyebrow}</p>
			<h1 class="mt-2 text-balance font-display text-h1 font-semibold leading-tight">{page.title}</h1>
			<p class="lede mt-4 text-muted">{page.lead}</p>
			<div class="mt-6 flex flex-wrap gap-3">
				<a class="btn btn-primary" href={localizeHref(page.primary.href)}>{page.primary.label}</a>
				<a class="btn btn-ghost" href={localizeHref(page.secondary.href)}>{page.secondary.label}</a>
			</div>
		</div>
		{#if books.length}
			<div class="fan">
				<CoverStrip covers={books.map(toBookTile)} size="fan" priority />
			</div>
		{/if}
	</section>

	<section class="mt-12" aria-labelledby="why-heading">
		<h2 id="why-heading" class="text-h2">{page.pointsHeading}</h2>
		<ul class="points mt-6">
			{#each page.points as p (p.title)}
				<li class="point rounded-card border border-border bg-surface p-5">
					<span class="point-icon rounded-full text-accent"><Icon name={p.icon} size={22} /></span>
					<h3 class="mt-3 text-h3">{p.title}</h3>
					<p class="mt-2 text-body text-muted">{p.body}</p>
					{#if p.link}
						<p class="mt-3 text-small">
							<a class="text-accent hover:underline" href={localizeHref(p.link.href)}
								>{p.link.label} <Arrow /></a
							>
						</p>
					{/if}
				</li>
			{/each}
		</ul>
	</section>

	<section class="mt-14" aria-labelledby="ideas-heading">
		<h2 id="ideas-heading" class="text-h2">{page.ideasHeading}</h2>
		<ol class="ideas mt-6">
			{#each page.ideas as idea, i (idea.title)}
				<li class="idea">
					<span class="idea-num font-display text-h2 text-gold" aria-hidden="true">{i + 1}</span>
					<div>
						<h3 class="text-h3">{idea.title}</h3>
						<p class="mt-1 text-body text-muted">{idea.body}</p>
					</div>
				</li>
			{/each}
		</ol>
	</section>

	{#if books.length}
		<section class="mt-14" aria-labelledby="picks-heading">
			<h2 id="picks-heading" class="section-label">{page.picksHeading}</h2>
			<p class="-mt-2 mb-5 max-w-2xl text-small text-muted">{page.picksNote}</p>
			<div class="book-grid">
				{#each books as book (book.slug)}
					<BookCard {book} showAuthor />
				{/each}
			</div>
		</section>
	{/if}

	<QandA items={qa.items} title="Questions" headingClass="text-h2" />

	<section class="close mt-14 rounded-card border border-border bg-surface-2 px-6 py-10 text-center sm:px-10">
		<h2 class="mx-auto max-w-[22ch] text-h2">{page.closeHeading}</h2>
		<p class="mx-auto mt-3 max-w-xl text-body text-muted">{page.closeBody}</p>
		<div class="mt-6 flex flex-wrap justify-center gap-3">
			<a class="btn btn-primary" href={localizeHref(page.primary.href)}>{page.primary.label}</a>
			<a class="btn btn-ghost" href={localizeHref('/contact')}>Contact us</a>
		</div>
	</section>

	<nav class="mt-10 text-small text-muted" aria-label="Ochorus for">
		Ochorus is also for:
		{#each others as o, i (o.slug)}
			{#if i}{' '}<span aria-hidden="true">·</span>{' '}{/if}<a
				class="text-accent hover:underline"
				href={forPath(o.slug)}>{o.label.toLowerCase()}</a
			>{/each}
	</nav>
</div>

<style>
	.hero {
		display: grid;
		grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
		gap: 2.5rem;
		align-items: center;
		padding-block: 1rem 1rem;
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
	.point-icon {
		display: inline-grid;
		place-items: center;
		width: 2.5rem;
		height: 2.5rem;
		background: var(--accent-soft);
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
	@media (max-width: 639.98px) {
		.hero {
			grid-template-columns: minmax(0, 1fr);
			gap: 0.5rem;
			padding-block: 0;
		}
		/* The fan sizes off its own width; on a phone it leads, as on /originals. */
		.fan {
			order: -1;
			margin-bottom: 0.75rem;
		}
		.points,
		.ideas {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
