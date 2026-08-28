<script lang="ts">
	import type { ScripturePageEntry } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumb, hreflangFor } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';

	// English-only; see the note on the chapter page.
	let { data } = $props();
	const pages = $derived<ScripturePageEntry[]>(data.pages);

	// Grouped into the books of the Bible, in canonical order, each carrying its
	// chapter pages. This is what makes the graph navigable rather than a list
	// of URLs only a crawler ever sees: from here every chapter page is one
	// click and every verse page two.
	const books = $derived.by(() => {
		const by = new Map<string, { title: string; order: number; chapters: ScripturePageEntry[] }>();
		for (const p of pages) {
			if (p.verse !== null) continue;
			let b = by.get(p.book);
			if (!b) by.set(p.book, (b = { title: p.book_title, order: p.book_order, chapters: [] }));
			b.chapters.push(p);
		}
		return [...by.entries()]
			.map(([slug, b]) => ({ slug, ...b }))
			.sort((a, b) => a.order - b.order);
	});
	const verseCount = $derived(pages.filter((p) => p.verse !== null).length);

	const path = '/scripture/';
	const canonical = `${SITE_URL}${path}`;
	const hreflang = hreflangFor(path, ['en']);
	const title = 'Scripture in the Christian classics · Ochorus';
	const description = $derived(
		`Browse ${pages.length - verseCount} chapters of the Bible and see which passages ` +
			'in the classics treat them — every citation quoted and linked to its source.'
	);
	const crumbs = [
		{ name: 'Home', href: '/' },
		{ name: 'Scripture', href: path }
	];
	const crumbsLd = jsonLd(breadcrumb(crumbs.map((c) => ({ name: c.name, url: c.href }))));
</script>

<Seo {title} {description} {canonical} {hreflang} structuredData={[crumbsLd]} />

<div class="page-col px-5 py-6">
	<Breadcrumb items={crumbs} />

	<header class="mb-8">
		<h1 class="text-h1">Scripture in the Christian classics</h1>
		<p class="mt-2 max-w-2xl text-small text-muted">
			Every Bible reference in the library is indexed. These are the chapters the writers
			return to — open one to see who preached it, and what they said.
		</p>
	</header>

	{#if !books.length}
		<EmptyState message="The scripture index is still being built." />
	{/if}

	{#each books as book (book.slug)}
		<section class="book">
			<h2 class="bname">{book.title}</h2>
			<ul class="chapters">
				{#each book.chapters as c (c.chapter)}
					<li>
						<a href={`/scripture/${book.slug}/${c.chapter}/`} title={`${c.citing_count} passages`}
							>{c.chapter}</a
						>
					</li>
				{/each}
			</ul>
		</section>
	{/each}
</div>

<style>
	.book {
		display: grid;
		grid-template-columns: minmax(8rem, 11rem) 1fr;
		gap: 0.75rem;
		align-items: baseline;
		padding: 0.6rem 0;
		border-top: 1px solid var(--color-border);
	}
	@media (max-width: 34rem) {
		.book {
			grid-template-columns: 1fr;
			gap: 0.35rem;
		}
	}
	.bname {
		margin: 0;
		font-size: var(--fs-body);
		font-weight: 600;
	}
	.chapters {
		list-style: none;
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
		margin: 0;
		padding: 0;
	}
	.chapters a {
		display: inline-block;
		min-width: 2rem;
		padding: 0.15rem 0.45rem;
		text-align: center;
		font-variant-numeric: tabular-nums;
		font-size: var(--fs-small);
		border-radius: var(--radius-chip, 0.4rem);
		background: var(--color-surface-2);
		color: var(--color-text);
		text-decoration: none;
	}
	.chapters a:hover {
		background: color-mix(in srgb, var(--color-accent) 18%, var(--color-surface-2));
	}
</style>
