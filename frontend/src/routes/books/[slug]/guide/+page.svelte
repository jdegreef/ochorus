<script lang="ts">
	import type { BookGuide } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, hreflangExact } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { contentLang } from '$lib/reading';
	import { authorPath } from '$lib/originals';
	import { guideWeekHeading } from '$lib/leaderGuide';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Arrow from '$lib/components/Arrow.svelte';

	/**
	 * A young-reader edition's leader's guide: one printable session per
	 * chapter for a church group or a homeschool. The leader's text (summary,
	 * memory verse, activity) comes from the guide file; the chapter's own
	 * verse, answered questions and prayer come from the book, so the two never
	 * disagree. A leaf page on screen; on paper, one week per page.
	 */
	let { data }: { data: { guide: BookGuide } } = $props();
	const t = i18n.t;
	const guide = $derived(data.guide);
	const book = $derived(guide.book);
	const lang = $derived(contentLang(book.language));

	const pageTitle = $derived(t('guide.title').replace('%t%', book.title));
	const path = $derived(`/books/${book.slug}/guide/`);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const hreflang = $derived(hreflangExact(path, guide.available_languages));
	const description = $derived(t('guide.description').replace('%t%', book.title));

	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.books'), href: '/books' },
		{ name: book.title, href: `/books/${book.slug}` },
		{ name: t('guide.label'), href: `/books/${book.slug}/guide` }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));

	const weeksLabel = $derived(t('guide.weeks').replace('%n%', String(guide.weeks.length)));
</script>

<Seo
	title={`${pageTitle} — Ochorus`}
	{description}
	{canonical}
	{hreflang}
	structuredData={[crumbsLd]}
/>

<div class="page-col guide px-5 py-10">
	<div class="screen-only">
		<Breadcrumb items={crumbs} />
	</div>

	<header class="guide-head mt-5">
		<div class="min-w-0">
			<p class="eyebrow mb-1 text-muted">
				<span class="whitespace-nowrap">{t('guide.label')}</span> · <span class="whitespace-nowrap"
					>{weeksLabel}</span
				>
			</p>
			<h1 class="text-h1" {lang} dir="auto">{pageTitle}</h1>
			<p class="mt-1 text-muted">
				<a href={localizeHref(authorPath(book.author.slug))} class="hover:text-accent hover:underline"
					>{book.author.name}</a
				>
			</p>
			<div class="screen-only mt-4 flex flex-wrap gap-2">
				<button type="button" class="btn btn-primary btn-sm" onclick={() => window.print()}>
					<Icon name="download" size={16} />
					{t('guide.print')}
				</button>
				<a href={localizeHref(`/books/${book.slug}`)} class="btn btn-ghost btn-sm">
					{t('guide.backToBook')}
				</a>
			</div>
		</div>
		<div class="guide-cover screen-only">
			<BookCover {book} />
		</div>
	</header>

	<section class="guide-intro mt-8 max-w-2xl space-y-3" {lang}>
		{#each guide.intro as para, i (i)}
			<p>{para}</p>
		{/each}
	</section>

	{#each guide.weeks as week (week.chapter)}
		<section
			class="guide-week mt-12 border-t border-border pt-8"
			id="week-{week.chapter}"
			aria-labelledby="week-{week.chapter}-heading"
			{lang}
		>
			<h2 id="week-{week.chapter}-heading" class="text-h2" dir="auto">
				{guideWeekHeading(t('guide.week'), week.chapter, week.title)}
			</h2>

			<p class="mt-3 max-w-2xl">{week.summary}</p>

			{#if week.verse}
				<blockquote class="guide-verse mt-4 max-w-2xl border-s-2 border-border ps-4 italic text-muted">
					{week.verse}
				</blockquote>
			{/if}

			<div class="guide-box mt-6">
				<h3 class="section-label">{t('guide.memoryVerse')}</h3>
				<p class="mt-2 font-display text-h3 leading-snug">{week.memory_verse.text}</p>
				<p class="mt-1 text-small text-muted">{week.memory_verse.reference}</p>
			</div>

			{#if week.questions.length}
				<div class="mt-6">
					<h3 class="section-label">{t('guide.talk')}</h3>
					<ol class="guide-questions mt-3 space-y-3">
						{#each week.questions as q, i (i)}
							<li>
								<p class="font-medium">{q.question}</p>
								<p class="guide-answer mt-1 text-small text-muted">{q.answer}</p>
							</li>
						{/each}
					</ol>
				</div>
			{/if}

			<div class="guide-box mt-6">
				<h3 class="section-label">{t('guide.activity')}</h3>
				<p class="mt-2 font-semibold">{week.activity.title}</p>
				<p class="mt-1 text-small">
					<span class="text-muted">{t('guide.materials')}</span>
					{week.activity.materials}
				</p>
				<ol class="guide-steps mt-3 space-y-1.5 ps-5">
					{#each week.activity.steps as step, i (i)}
						<li>{step}</li>
					{/each}
				</ol>
			</div>

			{#if week.prayer}
				<div class="mt-6">
					<h3 class="section-label">{t('guide.pray')}</h3>
					<p class="mt-2 max-w-2xl italic">{week.prayer}</p>
				</div>
			{/if}

			<p class="screen-only mt-6 text-small">
				<a
					href={localizeHref(`/books/${book.slug}/${week.chapter}`)}
					class="text-accent hover:underline"
					>{t('guide.readChapter').replace('%n%', String(week.chapter))} <Arrow /></a
				>
			</p>
		</section>
	{/each}
</div>

<style>
	.guide-head {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 1.5rem;
		align-items: start;
	}
	.guide-cover {
		width: 6rem;
	}
	@media (min-width: 640px) {
		.guide-cover {
			width: 8rem;
		}
	}
	.guide-box {
		max-width: 42rem;
		padding: 1rem 1.25rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.guide-questions {
		list-style: decimal;
		padding-inline-start: 1.25rem;
	}
	.guide-steps {
		list-style: decimal;
	}
	.guide-week {
		scroll-margin-top: calc(var(--appnav-h, 0px) + 1rem);
	}

	/* On paper: the guide alone, one week to a page. app.css's print block
	   already takes the site nav and footer off and sets every colour token
	   to black on white, so the tokens below print as ink; the rest of the
	   screen's furniture comes off here. */
	@media print {
		@page {
			margin: 16mm 18mm;
		}
		.screen-only,
		:global(.tabbar),
		:global(.fb-fab),
		:global(.pwa-stack) {
			display: none !important;
		}
		.guide {
			max-width: none;
			padding: 0;
			font-size: 12pt;
			line-height: 1.5;
			color: var(--text);
		}
		.guide-head {
			display: block;
			margin-top: 0;
		}
		.guide-week {
			break-before: page;
			margin-top: 0;
			padding-top: 0;
			border-top: none;
		}
		.guide-box {
			border-color: var(--border-strong);
			background: var(--surface);
			break-inside: avoid;
		}
		.guide-questions li {
			break-inside: avoid;
		}
		h2,
		h3 {
			break-after: avoid;
			color: var(--text);
		}
		.guide-answer {
			color: var(--muted);
		}
	}
</style>
