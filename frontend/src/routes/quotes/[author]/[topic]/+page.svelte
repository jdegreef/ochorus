<script lang="ts">
	import type { QuoteAuthorTopicPage } from '$lib/library-public';
	import { groupQuotes, onPhrase, citeChapter, quoteCollectionLd } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { hueForBirthYear } from '$lib/eras';
	import { jsonLd, breadcrumbLd, hreflangFor, absUrl } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import QuoteCard from '$lib/components/QuoteCard.svelte';
	import ScriptureEpigraph from '$lib/components/ScriptureEpigraph.svelte';
	import AccountCta from '$lib/components/AccountCta.svelte';
	import { initials, portraitPosition } from '$lib/portraits';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;

	// English-only, and written in English literals for the same reason the
	// author page is: these quotations are lifted from the English works.
	let { data } = $props();
	const page = $derived<QuoteAuthorTopicPage>(data.page);
	const topic = $derived(page.topic);
	const phrase = $derived(onPhrase(topic.title));

	// Grouped by work, which is what earns the colour (STYLE_GUIDE §5) — the same
	// grouping the author page uses. groupQuotes reads only `quotes`, so a
	// synthesised page (topics unused here) is enough.
	const eraHue = $derived(hueForBirthYear(page.author.birth_year));
	const groups = $derived(
		groupQuotes({ author: page.author, topics: [], quotes: page.quotes }, eraHue)
	);

	const path = $derived(`/quotes/${page.author.slug}/${topic.slug}/`);
	const canonical = $derived(`${SITE_URL}${path}`);
	const hreflang = $derived(hreflangFor(path, ['en']));

	const title = $derived(`${page.author.name} quotes on ${phrase} — Ochorus`);
	const description = $derived(
		`${page.quotes.length} quotations from ${page.author.name} on ${phrase}, each traced to the ` +
			'book, chapter and paragraph it comes from — and linked to the full text, free to read.'
	);

	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.quotes'), href: '/quotes/' },
		{ name: page.author.name, href: `/quotes/${page.author.slug}/` },
		{ name: topic.title, href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));

	const ogImage = $derived(
		page.author.photo_url ? absUrl(page.author.photo_url) : absUrl('/og/quotes.png')
	);

	// The same CollectionPage → ItemList the author page carries, scoped to the
	// theme (see quoteCollectionLd).
	const quotesLd = $derived(
		jsonLd(
			quoteCollectionLd({
				name: `${page.author.name} quotes on ${phrase}`,
				description,
				url: canonical,
				authorSlug: page.author.slug,
				authorName: page.author.name,
				quotes: page.quotes
			})
		)
	);
</script>

<Seo {title} {description} {canonical} {hreflang} {ogImage} structuredData={[crumbsLd, quotesLd]} />

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />

	<header class="mb-6">
		<div class="mb-1 flex items-center gap-4">
			{#if page.author.photo_url}
				<img
					src={page.author.photo_url}
					alt="Portrait of {page.author.name}"
					loading="lazy"
					width="112"
					height="112"
					class="h-20 w-20 shrink-0 rounded-full border border-border object-cover grayscale sm:h-24 sm:w-24"
					style="object-position: {portraitPosition(page.author.slug)}"
				/>
			{:else}
				<span
					class="font-display text-h2 flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-accent-soft font-semibold text-accent sm:h-24 sm:w-24"
				>
					{initials(page.author.name)}
				</span>
			{/if}
			<h1 class="text-h1">{t('quotes.authorTopicH1').replace('%name%', page.author.name).replace('%phrase%', phrase)}</h1>
		</div>
		<ScriptureEpigraph text={topic.scripture_text} reference={topic.scripture_ref} />
		<p class="mt-3 max-w-2xl text-small text-muted">
			{(page.quotes.length === 1 ? t('quotes.authorTopicIntroOne') : t('quotes.authorTopicIntroMany'))
				.replace('%count%', String(page.quotes.length))
				.replace('%name%', page.author.name)
				.replace('%phrase%', phrase)}
		</p>
	</header>

	{#each groups as g (g.id)}
		<section class="group" id={g.id} style={`--hue: ${g.hue}`}>
			<h2 class="work">
				{#if g.slug}
					<a href={`/books/${g.slug}/`}>{g.work}</a>
				{:else}
					{g.work}
				{/if}
				<span class="count text-small font-normal">{g.quotes.length}</span>
			</h2>
			<ol class="quotes">
				{#each g.quotes as q (q.slug)}
					<QuoteCard quote={q} authorName={page.author.name} cite={citeChapter(q)} />
				{/each}
			</ol>
		</section>
	{/each}

	<!-- The three ways out of this leaf: the same theme's other writers, the same
	     author's other themes, and the life behind the quotations. This is what
	     makes the theme grid a mesh rather than a set of dead ends. -->
	<nav class="more">
		<a href={`/quotes/topics/${topic.slug}/`}>{t('quotes.moreOn').replace('%phrase%', phrase)}</a>
		<a href={`/quotes/${page.author.slug}/`}>{t('quotes.allAuthor').replace('%name%', page.author.name)}</a>
		<a href={`/authors/${page.author.slug}/`}>{t('quotes.authorBio').replace('%name%', page.author.name)}</a>
	</nav>

	<AccountCta />
</div>

<style>
	.group {
		margin-bottom: 2.5rem;
		scroll-margin-top: 5rem;
	}
	.work {
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
		margin: 0 0 0.9rem;
		padding-inline-start: 0.7rem;
		border-inline-start: 3px solid color-mix(in srgb, var(--hue) 55%, var(--color-border));
		font-size: var(--fs-h3);
		font-weight: 600;
	}
	.work a {
		color: inherit;
		text-decoration: none;
	}
	.work a:hover {
		text-decoration: underline;
	}

	.quotes {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.75rem;
	}

	.more {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem 1.5rem;
		margin-top: 1rem;
		padding-top: 1.25rem;
		border-top: 1px solid var(--color-border);
		font-size: var(--fs-small);
	}
	.more a {
		color: var(--color-accent);
		text-decoration: none;
	}
	.more a:hover {
		text-decoration: underline;
	}
</style>
