<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import SermonCard from '$lib/components/SermonCard.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { canonName, chapterLabel } from '$lib/bibleNames';
	import { bibleIn } from '$lib/bibleLocales';
	import { SITE_URL } from '$lib/config';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import type { SermonSummary } from '$lib/library-public';
	import { bookChapterPath } from '$lib/reading-schema';
	import { breadcrumbLd, collectionPage, hreflangFor } from '$lib/seo';
	import { bibleBookSlug, sermonsOnGroups, sermonsOnPath } from '$lib/sermonsOn';

	const t = i18n.t;

	/**
	 * Sermons on one book of the Bible (/sermons/on/<book>/, $lib/sermonsOn):
	 * the sermons shelf's book facet as a page of its own, grouped by chapter,
	 * with a way into the book's text and to the other books' pages. A leaf
	 * page in the hub pages' anatomy (breadcrumb, eyebrow, h1, counts, lede).
	 */
	let {
		data
	}: {
		data: {
			position: number;
			sermons: SermonSummary[];
			books: { position: number; name: string }[];
		};
	} = $props();

	const lang = getLang();
	const nameOf = (position: number, fallback: string) => canonName(position, lang) ?? fallback;
	const book = $derived(nameOf(data.position, data.sermons[0]?.scripture_book ?? ''));
	const groups = $derived(sermonsOnGroups(data.sermons, data.position));
	const preachers = $derived(new Set(data.sermons.map((s) => s.author.slug)).size);
	const others = $derived(data.books.filter((b) => b.position !== data.position));
	// The text itself, where this language has the Bible.
	const bibleSlug = $derived(bibleIn(lang) ? bibleBookSlug(data.position) : null);
	const chapterHref = (n: number) =>
		bibleSlug ? localizeHref(bookChapterPath(bibleSlug, n + 1, false)) : null;

	const fill = (key: string) =>
		t(key).replace('%book%', book).replace('%count%', String(data.sermons.length));
	const title = $derived(fill('sermons.onTitle'));
	const description = $derived(fill('sermons.onDescription'));
	const path = $derived(sermonsOnPath(data.position) ?? '/sermons');
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.sermons'), href: '/sermons' },
		{ name: title, href: path }
	]);
	const listLd = $derived(
		collectionPage({
			name: title,
			description,
			url: canonical,
			items: groups.flatMap((g) =>
				g.sermons.map((s) => ({ name: s.title, url: localizeHref(`/sermons/${s.slug}`) }))
			)
		})
	);
</script>

<Seo
	title={`${title} — Ochorus`}
	{description}
	{canonical}
	hreflang={hreflangFor(path, [lang])}
	ogImage="{SITE_URL}/og/sermons.png"
	structuredData={[listLd, breadcrumbLd(crumbs)]}
/>

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />

	<header class="mb-8">
		<p class="eyebrow mb-2 text-accent">{t('nav.sermons')}</p>
		<h1 class="text-h1 mb-2">{title}</h1>
		<p class="mb-3 text-small text-muted">
			<span class="whitespace-nowrap">
				{i18n.count(data.sermons.length, 'common.sermonOne', 'common.sermonMany')}
			</span>{' · '}<span class="whitespace-nowrap">
				{i18n.count(preachers, 'common.authorOne', 'common.authorMany')}
			</span>
		</p>
		<p class="max-w-2xl text-body text-muted">{description}</p>
		{#if bibleSlug}
			<p class="mt-4">
				<a
					href={localizeHref(`/books/${bibleSlug}/`)}
					class="text-small font-semibold text-accent hover:underline"
				>
					{t('sermons.onReadBook').replace('%book%', book)}
					<Arrow />
				</a>
			</p>
		{/if}
	</header>

	{#each groups as g (g.chapter)}
		{@const label =
			g.chapter == null
				? book
				: (chapterLabel(data.position, g.chapter, lang) ?? `${book} ${g.chapter}`)}
		{@const href = g.chapter == null ? null : chapterHref(g.chapter)}
		<section class="mb-8" aria-label={label}>
			<h2 class="section-label mb-2">
				{#if href}<a {href} class="hover:underline">{label}</a>{:else}{label}{/if}
			</h2>
			<div class="sermon-list">
				{#each g.sermons as sermon (sermon.slug)}
					<SermonCard {sermon} showAuthor />
				{/each}
			</div>
		</section>
	{/each}

	{#if others.length}
		<section class="mt-12" aria-labelledby="other-books">
			<h2 id="other-books" class="section-heading no-rule">{t('sermons.onOtherBooks')}</h2>
			<ul class="flex flex-wrap gap-2">
				{#each others as b (b.position)}
					{@const href = sermonsOnPath(b.position)}
					{#if href}
						<li><a class="chip" href={localizeHref(href)}>{nameOf(b.position, b.name)}</a></li>
					{/if}
				{/each}
			</ul>
		</section>
	{/if}
</div>
