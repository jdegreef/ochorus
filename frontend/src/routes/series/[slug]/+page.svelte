<script lang="ts">
	import { onMount } from 'svelte';
	import * as m from '$lib/paraglide/messages.js';
	import { toBookTile, type SeriesDetail } from '$lib/library-public';
	import { bookProgressReader, getProgressRecord } from '$lib/progress';
	import { furthestOf } from '$lib/reading-schema';
	import { chapterCount, contentLang, readingTime } from '$lib/reading';
	import {
		nextInSeries,
		seriesAges,
		seriesCountLabel,
		seriesProgress,
		seriesProgressLabel,
		volumeName,
		volumesToCome,
		numeral,
		volumeLabel,
		resumePoint,
		dailyProgress
	} from '$lib/series';
	import { assetUrl } from '$lib/assetUrl';
	import { localeName } from '$lib/lang.svelte';
	import { seriesMeta } from '$lib/emblemNames';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd, breadcrumbLd, hreflangFor, pickQa, toQa } from '$lib/seo';
	import { LANDSCAPE_HEIGHT, LANDSCAPE_WIDTH } from '$lib/coverArt';
	import { seriesCardUrl } from '$lib/seriesCard';
	import { localizeHref } from '$lib/href';
	import BookCard from '$lib/components/BookCard.svelte';
	import SubjectFaces from '$lib/components/SubjectFaces.svelte';
	import { subjectSlug } from '$lib/keyTeachings';
	import TonightStory from '$lib/components/TonightStory.svelte';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import SeriesCard from '$lib/components/SeriesCard.svelte';
	import SeriesVolumes from '$lib/components/SeriesVolumes.svelte';
	import SeriesPeople from '$lib/components/SeriesPeople.svelte';
	import SeriesMap from '$lib/components/SeriesMap.svelte';
	import SeriesPlates from '$lib/components/SeriesPlates.svelte';
	import SeriesDay from '$lib/components/SeriesDay.svelte';
	import SeriesSegments from '$lib/components/SeriesSegments.svelte';
	import QandA from '$lib/components/QandA.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';

	/**
	 * A series page: the volumes of one series in reading order (Brave for God,
	 * Rooted), or the books of a collection (The Key Teachings). A leaf page on
	 * the plan page's anatomy — a plan is the other ordered run of books — with
	 * one action that knows where the reader is in the series.
	 *
	 * Since 2026-11 it also tells and sells the series: art behind the head
	 * (`hero`), a promise line and the series' verse, one facts line, volume
	 * rows that pitch each book, the first page of volume one, and — where a
	 * series has them — the faces of the lives it tells and a map of its world.
	 * Every one is optional data; a series without it draws the plain page.
	 */
	let { data } = $props();
	const t = i18n.t;
	const series = $derived(data.series as SeriesDetail);
	const manyAuthors = $derived(new Set(series.books.map((b) => b.author.slug)).size > 1);
	const lang = $derived(contentLang(getLang()));

	// Where the reader is, read after mount: progress lives in localStorage, and
	// the prerendered HTML must not bake one visitor's place into every page.
	// Until then the action is the plain "start with the first book".
	let progressed = $state(false);
	onMount(() => {
		progressed = true;
	});
	// One reader of the progress map, shared by the action, the meter and the rows.
	const progressOf = $derived(progressed ? bookProgressReader() : null);
	const next = $derived(
		progressOf
			? nextInSeries(series.books, progressOf)
			: series.books.length
				? { book: series.books[0], resume: false }
				: null
	);
	const progress = $derived(
		progressOf ? seriesProgress(series.books.map((b) => b.slug), progressOf) : null
	);
	const readCount = $derived(progress?.done ?? 0);

	const path = $derived(`/series/${series.slug}/`);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const hreflang = $derived(hreflangFor(path, series.available_languages));
	// The series' own card, drawn into the build in this page's language
	// (scripts/build-series-cards.mjs): its name, promise, count and covers.
	const ogImage = $derived(absUrl(seriesCardUrl(series.slug, getLang())));
	const description = $derived(
		series.description || m.series_meta_default({ series: series.title })
	);
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.books'), href: '/books' },
		{ name: t('nav.series'), href: '/series/' },
		{ name: series.title, href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));
	// schema.org's own type for this: a BookSeries whose parts are its volumes.
	const seriesLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'BookSeries',
			name: series.title,
			description,
			url: canonical,
			inLanguage: getLang(),
			hasPart: series.books.map((b) => ({
				'@type': 'Book',
				name: b.title,
				author: { '@type': 'Person', name: b.author.name },
				url: `${SITE_URL}${localizeHref(`/books/${b.slug}`)}`,
				...(b.series_position ? { position: b.series_position } : {})
			}))
		})
	);
	const count = $derived(series.books.length);
	const ages = $derived(seriesAges(series));

	// The selling head. `--series-accent` is the series' own colour (its emblem
	// accent), which the rows, faces and map pick up.
	const accent = $derived(seriesMeta(series.slug).accent);
	const hero = $derived(series.hero ?? null);
	const verse = $derived(series.verse ?? null);
	const people = $derived(series.people ?? []);
	// The plan only means something in an order; a collection has no "of 6".
	const planned = $derived(series.ordered ? (series.planned_count ?? null) : null);
	const toCome = $derived(volumesToCome(count, planned));
	const totalChapters = $derived(series.books.reduce((n, b) => n + (b.chapter_count || 0), 0));
	const totalWords = $derived(series.books.reduce((n, b) => n + (b.word_count || 0), 0));
	const otherLanguages = $derived(series.available_languages.filter((l) => l !== getLang()));
	const alsoIn = $derived(
		otherLanguages.length === 1
			? t('book.alsoInOne').replace('%lang%', localeName(otherLanguages[0]))
			: otherLanguages.length > 1
				? t('book.alsoInCount').replace('%n%', String(otherLanguages.length))
				: ''
	);
	const facts = $derived(
		[
			totalChapters ? chapterCount(totalChapters) : '',
			totalWords ? readingTime(totalWords) : '',
			t('book.freeToRead'),
			alsoIn
		].filter(Boolean)
	);

	// The one button, short: "Start with Book 1 · Called", "Continue · Book 2 ·
	// The Black Stair" — the volume's own name, never the series' again. A
	// collection keeps "Start with <title>".
	const action = $derived.by(() => {
		if (!next) return '';
		const pos = next.book.series_position;
		const name = volumeName(next.book, series.title);
		if (!series.ordered || !pos) {
			return `${next.resume ? t('plans.continue') : t('author.startWith')} ${next.book.title}`;
		}
		const head = next.resume
			? `${t('plans.continue')} · ${volumeLabel(pos, lang)}`
			: t('originals.startSeries').replace('%n%', numeral(pos, lang));
		return name ? `${head} · ${name}` : head;
	});
	const opening = $derived(series.opening ?? null);
	const current = $derived(next?.resume ? (next.book.series_position ?? null) : null);

	// A returning reader: the head greets them with where they are — the
	// chapter, what is left of the book, a segment per volume — and the button
	// opens that chapter rather than the book page.
	// The volume in focus: the one the head's button opens (being read, else
	// the first unfinished), else Book 1; and the reader's record of it, read
	// once for the welcome and the days.
	const focus = $derived(next?.book ?? series.books[0]);
	const focusRec = $derived(progressed && focus ? getProgressRecord(focus.slug) : null);
	const resume = $derived(next?.resume ? resumePoint(next.book, focusRec) : null);
	const stages = $derived(next?.resume ? (progress?.stages ?? []) : []);
	const primaryHref = $derived(
		next ? localizeHref(`/books/${next.book.slug}${resume ? `/${resume.order}` : ''}`) : ''
	);

	// Questions readers ask, answered from Book 1 (its own Q&A). Parents'
	// wording for the young series. No FAQPage here: Book 1's own page already
	// marks up these same questions, and one URL should carry them.
	const qa = $derived(pickQa(toQa(series.qa), []).items);
	const forParents = $derived(series.audience === 'young_readers' || series.audience === 'teens');

	// A daily devotional's month, for the volume the reader is in (Book 1
	// before they start).
	const daily = $derived(series.daily ?? null);
	const days = $derived(
		daily && focus
			? dailyProgress(
					focusRec ? furthestOf(focusRec) : null,
					daily.days,
					!!progressOf?.(focus.slug).finished
				)
			: { read: 0, next: 1 }
	);
	const plates = $derived(series.plates ?? []);
</script>

<Seo
	title="{series.title} — Ochorus"
	{description}
	{canonical}
	{hreflang}
	{ogImage}
	ogImageWidth={LANDSCAPE_WIDTH}
	ogImageHeight={LANDSCAPE_HEIGHT}
	ogImageAlt={series.title}
	structuredData={[seriesLd, crumbsLd]}
/>

<div class="page-col px-5 py-10" style="--series-accent: {accent}">
	<Breadcrumb items={crumbs} />

	<header class="series-head" class:with-art={!!hero} data-tone={hero?.tone ?? 'plain'}>
		{#if hero}
			<div class="series-art" aria-hidden="true" style="background-image: url('{assetUrl(hero.image)}')"></div>
		{/if}
		<div class="series-head-in">
			<div class="min-w-0">
				<p class="eyebrow series-eyebrow mb-1">
					{t('nav.series')} · {seriesCountLabel(count, planned, lang)}
					{#if ages}· {ages}{/if}
				</p>
				<h1 class="text-h1 mb-2" dir="auto">{series.title}</h1>
				{#if series.tagline}
					<p class="promise" dir="auto">{series.tagline}</p>
				{/if}
				{#if verse}
					<p class="verse" dir="auto">
						<q lang={lang}>{verse.text}</q>
						<cite>{verse.ref}</cite>
					</p>
				{/if}
				{#if resume && next}
					<div class="welcome">
						<p class="eyebrow welcome-eyebrow">{t('series.welcomeBack')}</p>
						<p class="welcome-where" dir="auto">
							{volumeLabel(next.book.series_position, lang) || next.book.title}
							· {t('book.chapterOf')
								.replace('%n%', numeral(resume.order, lang))
								.replace('%t%', numeral(resume.total, lang))}
							{#if resume.title}· <span class="welcome-chapter">{resume.title}</span>{/if}
						</p>
						<p class="text-small text-muted">
							{i18n.tn(resume.left, 'series.chaptersLeftOne', 'series.chaptersLeftMany').replace('%n%', numeral(resume.left, lang))}
						</p>
						{#if stages.length > 1}
							<div class="welcome-segments">
								<SeriesSegments {stages} label={seriesProgressLabel(readCount, count, lang)} />
							</div>
						{/if}
					</div>
				{:else if series.description}
					<p class="series-desc" dir="auto">{series.description}</p>
				{/if}
				<p class="series-facts">{facts.join(' · ')}</p>
				<div class="mt-5 flex flex-wrap items-center gap-3">
					{#if next}
						<a href={primaryHref} class="btn btn-primary btn-solid">
							<span dir="auto">{action}</span>
						</a>
					{:else}
						<!-- A status line, not a control: nothing is left to start. -->
						<p class="text-small font-medium">{t('series.allRead')}</p>
					{/if}
					{#if opening}
						<a href="#first-page" class="btn btn-ghost">{t('series.firstPage')}</a>
					{/if}
					<ShareButton url={canonical} title={series.title} showLabel />
					{#if readCount && next}
						<span class="text-small series-progress">
							{seriesProgressLabel(readCount, count, lang)}
						</span>
					{/if}
				</div>
			</div>
			<div class="series-fan hidden shrink-0 sm:block">
				<CoverStrip covers={series.books.map(toBookTile)} max={5} size="fan" />
			</div>
		</div>
	</header>

	{#if opening}
		<!-- The first page of volume one: the thing itself sells a series better
		     than anything written about it (library/opening.py picks it). -->
		<section id="first-page" class="mt-12 scroll-mt-24">
			<h2 class="section-label mb-4">{t('series.firstPage')}</h2>
			<figure class="first-page">
				<!-- .has-initial: the reader's own drop cap, script-gated in app.css. -->
				<blockquote {lang} dir="auto" class="has-initial"><p>{opening.text}</p></blockquote>
				<figcaption>
					<span dir="auto">{opening.chapter}</span>
					<a href={localizeHref(`/books/${series.books[0].slug}/${opening.order}`)} class="btn btn-primary">
						{t('series.keepReading')}
					</a>
				</figcaption>
			</figure>
		</section>
	{/if}

	<!-- A series for children whose volumes tell real lives (Brave for God):
	     one of them for tonight, above the volumes. -->
	{#if series.audience === 'young_readers' && people.length}
		<TonightStory {people} class="mt-12" />
	{/if}

	<section class="mt-12">
		<h2 class="section-label mb-4">
			{t('nav.books')}{#if series.ordered}{' · '}{t('series.inOrder')}{/if}
		</h2>
		{#if series.pitched}
			<SeriesVolumes books={series.books} seriesTitle={series.title} {lang} {progressOf} />
			{#if toCome}
				<div class="to-come">
					<span class="to-come-n" aria-hidden="true">{numeral(count + 1, lang)}</span>
					<div>
						<p class="font-display font-semibold">
							{i18n.tn(toCome, 'series.toComeOne', 'series.toComeMany').replace('%n%', numeral(toCome, lang))}
						</p>
						<p class="text-small text-muted">
							{t('series.toComeLine').replace('%n%', numeral(planned ?? count, lang))}
						</p>
					</div>
				</div>
			{/if}
		{:else if data.subjects.length}
			<!-- The Key Teachings: every volume is about a person, so the shelf
			     is the people (SubjectFaces), not thirty-six covers that all
			     read "Key Teachings". Only when the writers list arrived. -->
			<SubjectFaces books={series.books} authors={data.subjects} subjectOf={(b) => subjectSlug(b.slug)} />
		{:else}
			<!-- The cover grid the shelves use. The author rides the card only when
			     the books have more than one — The Key Teachings is a collection,
			     but every volume is by Ochorus Originals, and thirty cards saying
			     so would be noise. -->
			<div class="book-grid">
				{#each series.books as book (book.slug)}
					<BookCard {book} showAuthor={manyAuthors} showSeries={false} />
				{/each}
			</div>
		{/if}
	</section>

	{#if daily && focus}
		<SeriesDay
			sample={daily.sample}
			days={daily.days}
			book={focus}
			firstSlug={series.books[0].slug}
			{lang}
			read={days.read}
			next={days.next}
		/>
	{/if}

	{#if plates.length}
		<section class="mt-12">
			<h2 class="section-label mb-2">{t('series.platesHeading')}</h2>
			<p class="mb-4 text-small text-muted">{t('series.platesNote')}</p>
			<SeriesPlates {plates} books={series.books} {lang} />
		</section>
	{/if}

	{#if series.map && series.ordered}
		<section class="mt-12">
			<h2 class="section-label mb-2">{t('series.mapHeading')}</h2>
			<p class="mb-4 text-small text-muted">{t('series.mapNote')}</p>
			<SeriesMap
				image={series.map.image}
				markers={series.map.markers}
				books={series.books}
				seriesTitle={series.title}
				{lang}
				{current}
			/>
		</section>
	{/if}

	{#if people.length}
		<section class="mt-12">
			<h2 class="section-label mb-2">{t('series.peopleHeading')}</h2>
			<p class="mb-4 text-small text-muted">{t('series.peopleNote')}</p>
			<SeriesPeople {people} books={series.books} seriesTitle={series.title} {lang} />
		</section>
	{/if}

	{#if qa.length}
		<QandA
			items={qa}
			title={forParents ? t('series.parentsHeading') : t('series.questionsHeading')}
			headingClass="section-label"
			hint={t('series.parentsNote')}
		/>
	{/if}

	{#if data.others.length}
		<!-- The way on to the next series, and up to the index: the leaf page's
		     capped "More …" block, in the index's own (compact) card. -->
		<section class="mt-12">
			<div class="mb-4 flex items-baseline justify-between gap-3">
				<h2 class="section-label">{t('series.more')}</h2>
				<a href={localizeHref('/series/')} class="shrink-0 text-small font-medium">
					{t('series.seeAll')}
				</a>
			</div>
			<div class="grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-4">
				{#each data.others as s (s.slug)}
					<SeriesCard series={s} compact />
				{/each}
			</div>
		</section>
	{/if}
</div>

<style>
	/* The head: a plain block, or — with `hero` — a band over the series' own
	   art. A DARK band keeps its night colours in every theme (the art is
	   night); a LIGHT one follows the page's surface, its art softened in the
	   dark theme. */
	.series-head {
		position: relative;
		margin-top: 0.5rem;
	}
	.series-head.with-art {
		overflow: hidden;
		border-radius: var(--radius-card);
		padding: 2rem 2.25rem 2.25rem;
		isolation: isolate;
	}
	.series-head[data-tone='dark'] {
		/* hex-ok: a night band over night art keeps its colours in every theme */
		background: color-mix(in srgb, var(--series-accent) 10%, #101218); /* hex-ok: night band */
		color: #f3ead6; /* hex-ok: night band */
		--text: #fbf3e2; /* hex-ok: night band */
		--muted: #cfc4ae; /* hex-ok: night band */
	}
	.series-head[data-tone='light'] {
		background: color-mix(in srgb, var(--series-accent) 7%, var(--surface));
		border: 1px solid var(--border);
	}
	.series-art {
		position: absolute;
		inset: 0;
		z-index: -1;
		background-size: cover;
		background-position: center;
	}
	/* Dark art lies on the end side, fading out under the type. */
	.series-head[data-tone='dark'] .series-art {
		inset-inline-start: 35%;
		opacity: 0.6;
		mask-image: linear-gradient(to right, transparent, black 55%);
	}
	:global([dir='rtl']) .series-head[data-tone='dark'] .series-art {
		mask-image: linear-gradient(to left, transparent, black 55%);
	}
	/* Light art (a border of flowers) grows on the end side only, beside the
	   covers, so nothing grows through the type. */
	.series-head[data-tone='light'] .series-art {
		opacity: 0.22;
		mask-image: linear-gradient(to right, transparent 50%, black 85%);
	}
	:global([dir='rtl']) .series-head[data-tone='light'] .series-art {
		mask-image: linear-gradient(to left, transparent 50%, black 85%);
	}
	:global(:root:is([data-theme='light'], [data-theme='sepia'])) .series-head[data-tone='light'] .series-art {
		opacity: 0.45;
	}
	.series-head-in {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 2rem;
	}
	.series-head h1 {
		color: var(--text);
	}
	.series-eyebrow {
		color: var(--muted);
	}
	.series-head[data-tone='dark'] .series-eyebrow {
		color: color-mix(in srgb, var(--series-accent) 45%, #f3d9a8); /* hex-ok: night band */
	}
	.promise {
		font-family: var(--font-display);
		font-style: italic;
		font-size: var(--fs-h3);
		line-height: 1.4;
		max-width: 48ch;
		margin: 0 0 0.5rem;
		color: color-mix(in srgb, var(--series-accent) 70%, var(--text));
	}
	.series-head[data-tone='dark'] .promise {
		color: color-mix(in srgb, var(--series-accent) 35%, #f6d9a0); /* hex-ok: night band */
	}
	.verse {
		margin: 0 0 0.75rem;
		font-family: var(--font-display);
		color: var(--text);
	}
	.verse cite {
		font-family: var(--font-sans);
		font-style: normal;
		font-size: var(--fs-eyebrow);
		letter-spacing: 0.08em;
		color: var(--muted);
		margin-inline-start: 0.5rem;
	}
	.series-desc {
		max-width: 36rem;
		color: var(--muted);
		margin: 0 0 0.75rem;
	}
	.series-facts {
		color: var(--muted);
		font-size: var(--fs-small);
		margin: 0;
	}
	.welcome {
		display: grid;
		gap: 0.25rem;
		max-width: 36rem;
		margin: 0 0 0.75rem;
	}
	.welcome p {
		margin: 0;
	}
	.welcome-eyebrow {
		color: var(--series-accent, var(--accent));
	}
	.series-head[data-tone='dark'] .welcome-eyebrow {
		color: color-mix(in srgb, var(--series-accent) 45%, #f3d9a8); /* hex-ok: night band */
	}
	.welcome-where {
		font-family: var(--font-display);
		font-size: var(--fs-body);
		color: var(--text);
	}
	.welcome-chapter {
		font-style: italic;
	}
	.welcome-segments {
		max-width: 18rem;
		margin-top: 0.375rem;
	}
	.series-progress {
		color: var(--muted);
	}
	.series-fan {
		width: 15rem;
	}
	.series-head[data-tone='dark'] :global(.btn-ghost) {
		color: #f3ead6; /* hex-ok: night band */
		border-color: rgba(255, 255, 255, 0.3);
	}
	@media (max-width: 639.98px) {
		.series-head.with-art {
			padding: 1.5rem 1.25rem 1.5rem;
			margin-inline: -0.5rem;
		}
		.series-head[data-tone='dark'] .series-art {
			inset-inline-start: 0;
			opacity: 0.35;
			mask-image: none;
		}
	}

	/* The first page: a page of the book, set as the reader sets it. */
	.first-page {
		margin: 0;
		padding: 1.5rem 1.75rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		display: grid;
		gap: 1rem;
	}
	.first-page blockquote {
		margin: 0;
		font-family: var(--font-reading, var(--font-display));
		font-size: var(--fs-body);
		line-height: 1.75;
		max-width: 62ch;
		color: var(--text);
	}
	.first-page blockquote p {
		margin: 0;
	}
	.first-page figcaption {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		font-size: var(--fs-small);
		color: var(--muted);
	}

	/* Volumes still to come: a dashed row after the published ones. */
	.to-come {
		display: flex;
		align-items: center;
		gap: 1.25rem;
		margin-top: 0.875rem;
		padding: 1rem;
		border: 1px dashed var(--border-strong, var(--border));
		border-radius: var(--radius-card);
	}
	.to-come-n {
		display: grid;
		place-items: center;
		width: 6.5rem;
		aspect-ratio: 3 / 4;
		border: 1px dashed var(--border-strong, var(--border));
		border-radius: 0.375rem;
		font-family: var(--font-display);
		font-size: var(--fs-h2);
		color: var(--muted);
		flex: none;
	}
	@media (max-width: 639.98px) {
		.to-come-n {
			width: 5rem;
		}
	}
</style>
