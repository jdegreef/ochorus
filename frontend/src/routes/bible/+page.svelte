<script lang="ts">
	import type { BookSummary, PlanSummary, SeriesDetail } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, hreflangExact, itemList } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { BIBLE_PATH, BIBLE_SERIES, bibleIn, divisionKey, groupBible, testamentKey } from '$lib/bible';
	import { OWB_PATH } from '$lib/openWordBible';
	import Seo from '$lib/components/Seo.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import BookCard from '$lib/components/BookCard.svelte';
	import BibleCanonStrip from '$lib/components/BibleCanonStrip.svelte';
	import PlanShelfCard from '$lib/components/PlanShelfCard.svelte';
	import Arrow from '$lib/components/Arrow.svelte';

	/**
	 * The Bible hub: the Open Word Bible's books in the library, in canonical
	 * order, under Old Testament / New Testament and then their divisions — a
	 * grouped browse shelf on the Topics model. Only the divisions that have a
	 * book are drawn (`groupBible`), so it reads well with any part of the 66.
	 * The books are the `the-bible` series; its page (reading straight through,
	 * with the reader's place kept) and the Bible-only plans close the list.
	 */
	let { data } = $props();
	const series = $derived<SeriesDetail | null>(data.series);
	const plans = $derived<PlanSummary[]>(data.plans);
	const loadError = $derived<boolean>(data.loadError);
	const t = i18n.t;

	const groups = $derived(groupBible<BookSummary>(series?.books ?? []));
	// In the page's order, so the count, the cards and the JSON-LD agree.
	const books = $derived(groups.flatMap((g) => g.divisions.flatMap((d) => d.books)));

	const path = `${BIBLE_PATH}/`;
	const canonical = `${SITE_URL}${localizeHref(path)}`;
	// Exactly the languages the series has a page in (the sitemap lists the
	// same set): no English fallback, and an error panel claims no alternates.
	// Only where the chrome links the hub too (`bibleIn`), as the sitemap does.
	const hreflang = $derived(
		series ? hreflangExact(path, series.available_languages.filter(bibleIn)) : null
	);
	const booksLd = $derived(
		itemList(
			t('nav.bible'),
			books.map((b) => ({ name: b.title, url: localizeHref(`/books/${b.slug}`) }))
		)
	);
	const crumbsLd = breadcrumbLd([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.bible'), href: path }
	]);
</script>

<Seo
	title={`${t('nav.bible')} — Ochorus`}
	description={t('bible.tagline')}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og/bible.png`}
	structuredData={books.length ? [booksLd, crumbsLd] : [crumbsLd]}
/>

<svelte:head>
	{#if !books.length}
		<meta name="robots" content="noindex" />
	{/if}
</svelte:head>

<div class="page-col px-5 py-10">
	<PageHeader
		title={t('nav.bible')}
		tagline={t('bible.tagline')}
		meta={books.length ? counts : undefined}
	/>
	{#snippet counts()}
		{books.length}
		{books.length === 1 ? t('common.bookOne') : t('common.bookMany')}
	{/snippet}

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if !books.length}
		<!-- Loaded, and nothing to show: a retry could never help (the series
		     page's own split between a failure and an empty shelf). -->
		<EmptyState message={t('bible.none')} />
	{:else}
		<!-- The whole canon at a glance, each spine a link to its book page; the
		     grouped cards below are the shelf proper. -->
		<BibleCanonStrip books={series?.books ?? []} />
		{#each groups as testament (testament.testament)}
			<!-- A testament is the section; its divisions are the groups under it,
			     so their headings are h3s (the topic page's nested-group recipe). -->
			<section class="bible-testament">
				<h2 class="section-label mb-5">{t(testamentKey(testament.testament))}</h2>
				{#each testament.divisions as group (group.division.id)}
					<section class="bible-division">
						<GroupHeading as="h3" name={t(divisionKey(group.division.id))} count={group.books.length} />
						<!-- No author line: every book is the Open Word Bible's. No series
						     line: every book is in the one series this page is. -->
						<div class="book-grid">
							{#each group.books as book (book.slug)}
								<BookCard {book} showSeries={false} />
							{/each}
						</div>
					</section>
				{/each}
			</section>
		{/each}

		<!-- The cross-links at the end of the list, as other shelves keep them:
		     the plans that read only these books, then the series page, which
		     reads Genesis to Revelation and keeps the reader's place. -->
		<section class="bible-testament">
			<h2 class="section-label mb-5">{t('bible.readAlong')}</h2>
			{#if plans.length}
				<div class="mb-6 grid items-stretch gap-x-6 gap-y-7 sm:grid-cols-2 lg:grid-cols-3">
					{#each plans as plan (plan.slug)}
						<PlanShelfCard {plan} headingLevel={3} />
					{/each}
				</div>
			{/if}
			<p class="text-small">
				<a href={localizeHref(`/series/${BIBLE_SERIES}/`)} class="font-medium text-accent hover:underline"
					>{t('bible.inOrder')} <Arrow /></a
				>
			</p>
			<!-- What the translation is, and its home: English prose, like the
			     page it opens (it exists only where the hub does). -->
			<p class="mt-2 text-small">
				<a href={localizeHref(`${OWB_PATH}/`)} class="font-medium text-accent hover:underline"
					>About the Open Word Bible <Arrow /></a
				>
			</p>
		</section>
	{/if}
</div>

<style>
	.bible-testament + .bible-testament {
		margin-top: 3rem;
	}
	.bible-division + .bible-division {
		margin-top: 2.25rem;
	}
</style>
