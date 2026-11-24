<script lang="ts">
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, hreflangExact, jsonLd, publisherLd } from '$lib/seo';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { BIBLE_LOCALES, BIBLE_PATH, bibleText, testamentKey } from '$lib/bible';
	import { getLang } from '$lib/lang.svelte';
	import {
		BIBLE_STORY,
		BIBLE_STORY_PATH,
		STORY_BOOK,
		STORY_PLAN_SLUG,
		STORY_TAGLINE,
		storyBooks,
		storyEras,
		storyKeys,
		storyText,
		type StorySection
	} from '$lib/bibleStory';
	import Seo from '$lib/components/Seo.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import Arrow from '$lib/components/Arrow.svelte';

	/**
	 * The Story of the Bible: the whole Bible in story order, one short section
	 * per era, each with the books that tell it and a key chapter or two
	 * ($lib/bibleStory). A timeline from the tablet up — a rule down the start
	 * margin with each era's number on it — and a plain stack on a phone. CSS
	 * only, so the prerendered HTML is one layout at every width.
	 *
	 * The prose is the page's own, in each hub locale (the page exists only in
	 * BIBLE_LOCALES); the headings and labels around it are chrome, through
	 * the catalogue.
	 */
	const t = i18n.t;
	const lang = getLang();
	const tagline = bibleText(STORY_TAGLINE, lang);
	const ABOUT = { en: 'The Bible', es: 'La Biblia' };

	const eras = storyEras();
	// Numbered through both testaments, so the New Testament list starts where
	// the Old one stopped.
	const number = new Map(eras.map((s, i) => [s.id, i + 1]));
	const oldEras = eras.filter((s) => s.testament === 'old');
	const newEras = eras.filter((s) => s.testament === 'new');
	const interludes = BIBLE_STORY.filter((s) => s.interlude);

	const path = `${BIBLE_STORY_PATH}/`;
	const canonical = `${SITE_URL}${localizeHref(path)}`;
	// Every hub locale has the page, in its own words (the sitemap's set).
	const hreflang = hreflangExact(path, [...BIBLE_LOCALES]);
	const title = `${t('bible.storyTitle')} — Ochorus`;
	const crumbsLd = breadcrumbLd([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.bible'), href: `${BIBLE_PATH}/` },
		{ name: t('bible.storyTitle'), href: path }
	]);
	// A house-written page about the Bible: an Article by the house, as the
	// articles are, about the Bible as a whole.
	const articleLd = jsonLd({
		'@context': 'https://schema.org',
		'@type': 'Article',
		headline: t('bible.storyTitle'),
		description: tagline,
		inLanguage: lang,
		url: canonical,
		mainEntityOfPage: canonical,
		articleSection: t('nav.bible'),
		about: { '@type': 'Book', name: bibleText(ABOUT, lang) },
		isAccessibleForFree: true,
		author: publisherLd(),
		publisher: publisherLd()
	});
	/** Which "Read on" links this language has (+page.ts). */
	let { data } = $props();
</script>

<Seo
	{title}
	description={tagline}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og/bible.png`}
	structuredData={[articleLd, crumbsLd]}
/>

{#snippet era(s: StorySection)}
	{@const books = storyBooks(s, lang)}
	{@const keys = storyKeys(s, lang)}
	{@const words = storyText(s, lang)}
	<li class="era" id={s.id}>
		<span class="marker" aria-hidden="true">{number.get(s.id)}</span>
		<div class="era-body">
			<p class="eyebrow text-gold-ink">{words.period}</p>
			<h3 class="era-title mt-1 font-display text-h3 font-semibold">{words.title}</h3>
			<p class="prose-line mt-2 text-muted">{words.prose}</p>
			<dl class="links mt-4 text-small">
				<div>
					<dt>{t('bible.storyToldIn')}</dt>
					<dd>
						<ul class="book-links">
							{#each books as b (b.href)}
								<li><a href={localizeHref(b.href)} class="text-accent hover:underline">{b.label}</a></li>
							{/each}
						</ul>
					</dd>
				</div>
				<div>
					<dt>{t('bible.storyKeyChapters')}</dt>
					<dd>
						<ul class="key-links">
							{#each keys as k (k.href)}
								<li><a class="chip" href={localizeHref(k.href)}>{k.label}</a></li>
							{/each}
						</ul>
					</dd>
				</div>
			</dl>
		</div>
	</li>
{/snippet}

<div class="page-col px-5 py-10">
	<PageHeader eyebrow={t('nav.bible')} title={t('bible.storyTitle')} {tagline} />

	<section class="testament" aria-labelledby="story-old">
		<h2 id="story-old" class="section-label">{t(testamentKey('old'))}</h2>
		<ol class="timeline">
			{#each oldEras as s (s.id)}
				{@render era(s)}
			{/each}
		</ol>
	</section>

	<!-- The pause between the testaments: a line, not an era. -->
	{#each interludes as s (s.id)}
		{@const words = storyText(s, lang)}
		<div class="interlude" id={s.id}>
			<p class="eyebrow text-muted">{words.title} · {words.period}</p>
			<p class="mt-1 text-small text-muted">{words.prose}</p>
		</div>
	{/each}

	<section class="testament" aria-labelledby="story-new">
		<h2 id="story-new" class="section-label">{t(testamentKey('new'))}</h2>
		<ol class="timeline" start={number.get(newEras[0].id)}>
			{#each newEras as s (s.id)}
				{@render era(s)}
			{/each}
		</ol>
	</section>

	<!-- The same story read a chapter a day, and told for teens: each only
	     where the API serves it (+page.ts). -->
	<section class="mt-14" aria-labelledby="story-read-on">
		<h2 id="story-read-on" class="section-label mb-5">{t('bible.storyReadOn')}</h2>
		{#if data.plan || data.book}
		<ul class="read-on">
			{#if data.plan}
			<li>
				<a class="read-card card-lift" href={localizeHref(`/plans/${STORY_PLAN_SLUG}`)}>
					<span class="font-display text-body font-semibold text-text">{t('bible.storyTitle')}</span>
					<span class="mt-1 block text-small text-muted">{t('bible.storyPlan')}</span>
					<span class="mt-2 block text-small font-semibold text-accent">{t('plans.title')} <Arrow /></span>
				</a>
			</li>
			{/if}
			{#if data.book}
			<li>
				<a class="read-card card-lift" href={localizeHref(`/books/${STORY_BOOK.slug}`)}>
					<span class="font-display text-body font-semibold text-text">{data.book}</span>
					<span class="mt-1 block text-small text-muted">{t('bible.storyForTeens')}</span>
					<span class="mt-2 block text-small font-semibold text-accent">{t('home.startReading')} <Arrow /></span>
				</a>
			</li>
			{/if}
		</ul>
		{/if}
		<p class="mt-8 text-small">
			<a href={localizeHref(`${BIBLE_PATH}/`)} class="font-medium text-accent hover:underline"
				><Arrow back /> {t('nav.bible')}</a
			>
		</p>
	</section>
</div>

<style>
	.testament {
		margin-top: 0.5rem;
	}
	.timeline {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.era {
		padding-block: 1.5rem;
		border-top: 1px solid var(--border);
	}
	.era:first-child {
		border-top: 0;
		padding-top: 0.5rem;
	}
	/* On a phone the number rides in the stack's flow, small, before the period. */
	.marker {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 1.75rem;
		height: 1.75rem;
		margin-bottom: 0.5rem;
		border: 1px solid var(--gold);
		border-radius: var(--radius-pill);
		background: var(--surface);
		color: var(--gold);
		font-size: var(--fs-eyebrow);
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}
	.prose-line {
		max-width: 62ch;
		line-height: 1.65;
	}
	.links {
		display: grid;
		gap: 0.75rem;
	}
	.links dt {
		margin-bottom: 0.3rem;
		font-size: var(--fs-eyebrow);
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--muted);
	}
	.book-links,
	.key-links {
		display: flex;
		flex-wrap: wrap;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.book-links {
		gap: 0.25rem 0;
	}
	/* A middle dot after each book name but the last, kept out of the links'
	   own text; after, not before, so a wrapped line never opens on a dot. */
	.book-links li:not(:last-child)::after {
		content: '·';
		margin-inline: 0.45rem;
		color: var(--muted);
	}
	.key-links {
		gap: 0.5rem;
	}
	.interlude {
		margin: 1.5rem 0 2.5rem;
		padding: 1rem 1.25rem;
		border-radius: var(--radius-card);
		background: var(--surface-2);
		max-width: 48rem;
	}
	.read-on {
		display: grid;
		gap: 0.875rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.read-card {
		display: block;
		height: 100%;
		padding: 1.1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	@media (min-width: 640px) {
		.read-on {
			grid-template-columns: repeat(2, minmax(0, 1fr));
			max-width: 48rem;
		}
	}
	/* From the tablet up, a timeline: a rule down the start margin, each era's
	   number a medallion on it, the text beside. */
	@media (min-width: 768px) {
		.timeline {
			position: relative;
			padding-inline-start: 4rem;
		}
		.timeline::before {
			content: '';
			position: absolute;
			inset-block: 0.5rem 0.5rem;
			inset-inline-start: 1.25rem;
			width: 2px;
			background: var(--border);
		}
		.era {
			position: relative;
			border-top: 0;
			padding-block: 1.25rem 1.75rem;
		}
		.era:first-child {
			padding-top: 0.75rem;
		}
		.marker {
			position: absolute;
			inset-inline-start: -4rem;
			top: 1.1rem;
			width: 2.6rem;
			height: 2.6rem;
			margin: 0;
			font-size: var(--fs-small);
			box-shadow: 0 0 0 4px var(--bg);
		}
		.era:first-child .marker {
			top: 0.6rem;
		}
		.links {
			grid-template-columns: minmax(0, 1fr) minmax(0, 15rem);
			align-items: start;
			gap: 2rem;
			max-width: 40rem;
		}
		.interlude {
			margin-inline-start: 4rem;
		}
	}
</style>
