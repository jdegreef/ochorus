<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import BookCard from '$lib/components/BookCard.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { writerCount } from '$lib/bookHubs';
	import { SITE_URL } from '$lib/config';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import type { BookSummary } from '$lib/library-public';
	import { breadcrumbLd, collectionPage, hreflangFor } from '$lib/seo';

	const t = i18n.t;

	/**
	 * A book hub — the library's books of one tradition or era ($lib/bookHubs).
	 * The biography hubs' anatomy (breadcrumb, eyebrow, h1, counts, lede) over
	 * a book grid, then the hub's biography twin and its sibling hubs. Both
	 * book-hub routes render this.
	 */
	let {
		label,
		path,
		lede,
		books,
		biosHref,
		others,
		othersHeading
	}: {
		/** The hub's short name ("Puritans", "The Early Church"). */
		label: string;
		path: string;
		/** The hub's own intro, when it has one; else the counts sentence. */
		lede?: string;
		books: BookSummary[];
		/** The biography hub of the same writers. */
		biosHref: string;
		others: { href: string; label: string }[];
		othersHeading: string;
	} = $props();

	const writers = $derived(writerCount(books));
	const title = $derived(t('books.hubTitle').replace('%label%', label));
	const description = $derived(
		t('books.hubDescription')
			.replace('%count%', String(books.length))
			.replace('%writers%', String(writers))
	);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.books'), href: '/books' },
		{ name: label, href: path }
	]);
	const listLd = $derived(
		collectionPage({
			name: title,
			description,
			url: canonical,
			items: books.map((b) => ({ name: b.title, url: localizeHref(`/books/${b.slug}/`) }))
		})
	);
</script>

<Seo
	title={`${title} — Ochorus`}
	{description}
	{canonical}
	hreflang={hreflangFor(path, [getLang()])}
	structuredData={[listLd, breadcrumbLd(crumbs)]}
/>

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />

	<header class="mb-8">
		<p class="eyebrow mb-2 text-accent">{t('nav.books')}</p>
		<h1 class="text-h1 mb-2">{title}</h1>
		<p class="mb-3 text-small text-muted">
			<span class="whitespace-nowrap">
				{books.length}
				{i18n.tn(books.length, 'common.bookOne', 'common.bookMany')}
			</span>{' · '}<span class="whitespace-nowrap">
				{writers}
				{i18n.tn(writers, 'common.authorOne', 'common.authorMany')}
			</span>
		</p>
		<p class="max-w-2xl text-body text-muted">{lede || description}</p>
		<p class="mt-4">
			<a href={localizeHref(biosHref)} class="text-small font-semibold text-accent hover:underline">
				{t('books.hubTheirLives')}
				<Arrow />
			</a>
		</p>
	</header>

	<div class="book-grid">
		{#each books as book (book.slug)}
			<BookCard {book} showAuthor />
		{/each}
	</div>

	{#if others.length}
		<section class="mt-12" aria-labelledby="hub-others">
			<h2 id="hub-others" class="section-label mb-3">{othersHeading}</h2>
			<ul class="flex flex-wrap gap-2">
				{#each others as o (o.href)}
					<li><a class="tag" href={localizeHref(o.href)}>{o.label}</a></li>
				{/each}
			</ul>
		</section>
	{/if}
</div>
