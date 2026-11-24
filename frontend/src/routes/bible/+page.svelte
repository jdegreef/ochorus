<script lang="ts">
	import { onMount } from 'svelte';
	import type { BookSummary, PlanSummary, SeriesDetail } from '$lib/library-public';
	import { allProgress } from '$lib/progress';
	import { planProgress } from '$lib/planProgress.svelte';
	import { planMeta } from '$lib/emblemNames';
	import { chapterPath } from '$lib/editionHref';
	import { workPercent } from '$lib/reading';
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, hreflangExact, itemList } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { getLang } from '$lib/lang.svelte';
	import {
		BIBLE_PATH,
		BIBLE_SERIES,
		BIBLE_STORY_PATH,
		bibleChapterCount,
		bibleIn,
		biblePlace,
		bibleToContinue,
		bibleContinueRows,
		bibleStarts,
		BIBLE_PATHS,
		biblePathSteps,
		bibleText,
		type BibleText,
		divisionKey,
		groupBible,
		mayBePassage,
		passageHref,
		testamentKey
	} from '$lib/bible';
	import { goto } from '$app/navigation';
	import { lookupScripture } from '$lib/scripture.svelte';
	import { passageSuggestions, quickPassages } from '$lib/biblePassage';
	import { searchHref } from '$lib/searchState';
	import BookCover from '$lib/components/BookCover.svelte';
	import { OWB_PATH } from '$lib/openWordBible';
	import Seo from '$lib/components/Seo.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import BibleCoverGrid from '$lib/components/BibleCoverGrid.svelte';
	import BibleCanonStrip from '$lib/components/BibleCanonStrip.svelte';
	import BibleTodayHero from '$lib/components/BibleTodayHero.svelte';
	import BibleBookList from '$lib/components/BibleBookList.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import PlanShelfCard from '$lib/components/PlanShelfCard.svelte';
	import Arrow from '$lib/components/Arrow.svelte';
	import ContinueShelf from '$lib/components/ContinueShelf.svelte';
	import ContinueRow from '$lib/components/ContinueRow.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';

	/**
	 * The Bible hub: the Open Word Bible's books in the library, in canonical
	 * order, under Old Testament / New Testament and then their divisions — a
	 * grouped browse shelf on the Topics model. Only the divisions that have a
	 * book are drawn (`groupBible`), so it reads well with any part of the 66.
	 * The books are the `the-bible` series. The Bible-only plans and the series
	 * page (reading straight through, with the reader's place kept) come right
	 * after "Where to start", where a reader choosing a way in still is.
	 *
	 * The divisions draw as a compact index (`BibleBookList`: a row per book, its
	 * chapters a tap away) — 66 full covers made a phone page ~14,000px tall. The
	 * covers stay one tap away, as the book page's contents keep their list.
	 */
	let { data } = $props();
	const series = $derived<SeriesDetail | null>(data.series);
	const plans = $derived<PlanSummary[]>(data.plans);
	// Each book's sermons and classics, by its place in the canon.
	const linksAt = $derived(new Map(data.links.map((l) => [l.position, l])));
	const linksOf = (book: BookSummary) =>
		book.series_position != null ? linksAt.get(book.series_position) : undefined;
	const loadError = $derived<boolean>(data.loadError);
	const t = i18n.t;
	const lang = getLang();

	/**
	 * The hub's own words beyond the catalogue's: only this page uses them,
	 * and it exists only in BIBLE_LOCALES, so they live here, one per hub
	 * locale (`BibleText`), rather than as 14-locale catalogue keys.
	 */
	const COPY = {
		balanced: { en: 'Balanced', es: 'Equilibrado' },
		freeToShare: { en: 'Free to share', es: 'Libre para compartir' },
		noteWhat: {
			en: "A new translation of the Bible from the Hebrew and Greek, in today's English. Every sentence is translated three ways, from word-for-word to plain; Ochorus prints the Balanced one, faithful to the original and easy to read.",
			es: 'Una nueva traducción de la Biblia hecha directamente del hebreo y el griego, en el español de hoy. Ochorus imprime su nivel Equilibrado: fiel al original y fácil de leer.'
		},
		noteFree: {
			en: 'It is given to the public domain, so anyone may read, copy, print and share it, free.',
			es: 'Está cedida al dominio público, así que cualquiera puede leerla, copiarla, imprimirla y compartirla, gratis.'
		},
		moreAbout: { en: 'More about the translation', es: 'Más sobre la traducción' },
		passagesOn: { en: 'Passages on', es: 'Pasajes sobre' },
		chooseWay: { en: 'Choose a way in', es: 'Elegir por dónde entrar' },
		newToBible: { en: 'New to the Bible', es: 'Nuevo en la Biblia' },
		showCovers: { en: 'Show covers', es: 'Ver portadas' },
		aboutOwb: { en: 'About the Open Word Bible', es: 'Acerca de la Open Word Bible' }
	} satisfies Record<string, BibleText>;
	const say = (text: BibleText) => bibleText(text, lang);

	const groups = $derived(groupBible<BookSummary>(series?.books ?? []));
	// In the page's order, so the count, the cards and the JSON-LD agree.
	const books = $derived(groups.flatMap((g) => g.divisions.flatMap((d) => d.books)));
	const chapters = $derived(bibleChapterCount(books));
	const starts = $derived(bibleStarts(series?.books ?? [], lang));
	// "Where to start": the first reader's five books by default, or a path
	// for what brought them (BIBLE_PATHS), one switch away. The prerender
	// draws the default.
	let pathId = $state('first');
	const startPath = $derived(BIBLE_PATHS.find((p) => p.id === pathId) ?? null);
	const steps = $derived(
		startPath
			? biblePathSteps(startPath.steps, series?.books ?? [], lang)
			: starts.map(({ book, why }) => ({ book, title: book.title, href: `/books/${book.slug}`, why }))
	);
	// The reader's place in the Bible: device-local progress (synced when signed
	// in), read after mount and again on `ochorus:sync`, as the hubs' Continue
	// rows are. The prerender, and a first visit, have none: no Continue shelf,
	// no marked chapters.
	let ticks = $state(0);
	onMount(() => {
		const bump = () => ticks++;
		bump();
		window.addEventListener('ochorus:sync', bump);
		return () => window.removeEventListener('ochorus:sync', bump);
	});
	const records = $derived(ticks ? allProgress().filter((r) => r.kind === 'book') : []);
	// The Bible plans the reader has started and not finished, most recently
	// started first (the /plans page's "Continue your plans", read the same way).
	const openPlans = $derived.by(() => {
		if (!ticks) return [];
		void planProgress.ticks;
		const bySlug = new Map(plans.map((p) => [p.slug, p]));
		return planProgress
			.started()
			.map((s) => bySlug.get(s.slug))
			.filter((p): p is PlanSummary => !!p && planProgress.nextDay(p.slug, p.day_count) !== null);
	});
	const continues = $derived(bibleContinueRows(openPlans, bibleToContinue(books, records)));
	const placeOf = $derived.by(() => {
		if (!records.length) return undefined;
		const bySlug = new Map(records.map((r) => [r.slug, r]));
		return (book: BookSummary) => biblePlace(book, bySlug.get(book.slug));
	});

	// Covers where there is room for them: the painted grounds are finished
	// art, and on a wide screen six to a row keep the page a sensible length.
	// A phone keeps the compact index (66 covers there ran ~14,000px). Chosen
	// after mount, so the prerender — and a phone — draw the list.
	let asCovers = $state(false);
	onMount(() => {
		if (matchMedia('(min-width: 1024px)').matches) asCovers = true;
	});
	// The one book whose chapters are open, across the whole index.
	let openBook = $state<string | null>(null);

	// "Go to a passage": the API parses the reference (names, abbreviations,
	// ranges) and says which reader chapter prints it (`passageHref`); a book
	// named alone opens its page (`mayBePassage`). Anything
	// that is not a passage the library prints goes to search, as the Scripture
	// hub's own finder does — so a query never dead-ends here.
	let jumpQ = $state('');
	let jumping = $state(false);
	let jumpSeq = 0;
	// Suggestions as the reader types (`passageSuggestions`: the hub's own books,
	// so each is a chapter the library prints), a combobox's listbox under the
	// box. `active` is the one the arrow keys are on (-1: none).
	const suggestions = $derived(passageSuggestions(jumpQ, series?.books ?? [], lang));
	const quick = $derived(quickPassages(series?.books ?? [], lang));
	const topics = $derived(data.topics);
	let listOpen = $state(false);
	let active = $state(-1);
	const showList = $derived(listOpen && suggestions.length > 0);
	function onJumpKey(e: KeyboardEvent) {
		if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
			if (!suggestions.length) return;
			e.preventDefault();
			listOpen = true;
			const step = e.key === 'ArrowDown' ? 1 : -1;
			active = (active + step + suggestions.length + 1) % (suggestions.length + 1);
			if (active === suggestions.length) active = -1;
		} else if (e.key === 'Escape' && showList) {
			e.preventDefault();
			listOpen = false;
			active = -1;
		}
	}
	async function jump(e: SubmitEvent) {
		e.preventDefault();
		// A suggestion the arrow keys are on is what Enter means.
		const picked = showList && active >= 0 ? suggestions[active] : null;
		if (picked) {
			listOpen = false;
			await goto(localizeHref(picked.href));
			return;
		}
		const q = jumpQ.trim();
		if (q.length < 2) return;
		const seq = ++jumpSeq;
		jumping = true;
		// The resolver reads English names alone; a Spanish name ("Juan 3:16")
		// is the suggestions' to read, so it is asked only where they found none.
		const own = lang !== 'en' ? (suggestions[0]?.href ?? null) : null;
		const found = !own && mayBePassage(q) ? await lookupScripture(q) : null;
		if (seq !== jumpSeq) return;
		// The resolver's reading first; then the best suggestion (a typo the
		// resolver refused, "Roamns 8"); then search, so nothing dead-ends.
		const href = own ?? (found ? passageHref(found) : null) ?? suggestions[0]?.href ?? null;
		// Kept busy until the navigation lands, so Read can't fire it twice.
		await goto(localizeHref(href ?? searchHref(q)));
		if (seq === jumpSeq) jumping = false;
	}

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
		{i18n.tn(books.length, 'common.bookOne', 'common.bookMany')}
		{#if chapters}
			· {chapters.toLocaleString(lang)}
			{i18n.tn(chapters, 'book.chapterOne', 'book.chaptersMany')}
		{/if}
	{/snippet}
	<!-- What the translation is, where a reader first wonders: who made it, what
	     "Balanced" means, that it is free. Its words are the /open-word-bible
	     page's own, and a native <details>, so it opens without script and
	     announces its state. -->
	<details class="owb-note">
		<summary>
			<span>Open Word Bible</span><span class="sep" aria-hidden="true">·</span><span
				>{say(COPY.balanced)}</span
			><span class="sep" aria-hidden="true">·</span><span>{say(COPY.freeToShare)}</span>
			<span class="owb-chev" aria-hidden="true"><Icon name="chevron-right" size={14} /></span>
		</summary>
		<div class="owb-note-body">
			<p>{say(COPY.noteWhat)}</p>
			<p>{say(COPY.noteFree)}</p>
			<p>
				<a href={localizeHref(`${OWB_PATH}/`)} class="font-medium text-accent hover:underline"
					>{say(COPY.moreAbout)} <Arrow /></a
				>
			</p>
		</div>
	</details>

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if !books.length}
		<!-- Loaded, and nothing to show: a retry could never help (the series
		     page's own split between a failure and an empty shelf). -->
		<EmptyState message={t('bible.none')} />
	{:else}
		<!-- Scripture first: the day's verse, and today's chapter on its art. -->
		<BibleTodayHero books={series?.books ?? []} />

		<!-- Straight to a passage: method/action make it a site search before
		     hydration (and for anything not a passage), `jump` opens the chapter. -->
		<form class="jump" method="get" action={localizeHref('/search')} role="search" onsubmit={jump}>
			<label for="bible-jump" class="jump-label">{t('bible.jumpLabel')}</label>
			<div class="jump-row">
				<input
					id="bible-jump"
					name="q"
					type="search"
					class="field"
					autocomplete="off"
					required
					minlength={2}
					enterkeyhint="go"
					placeholder={t('bible.jumpPlaceholder')}
					bind:value={jumpQ}
					role="combobox"
					aria-autocomplete="list"
					aria-expanded={showList}
					aria-controls="bible-jump-list"
					aria-activedescendant={showList && active >= 0 ? `bible-jump-opt-${active}` : undefined}
					oninput={() => {
						jumpSeq++;
						jumping = false;
						listOpen = true;
						active = -1;
					}}
					onkeydown={onJumpKey}
					onfocus={() => (listOpen = true)}
					onblur={() => (listOpen = false)}
				/>
				<button type="submit" class="btn btn-primary" disabled={jumping} aria-busy={jumping}>
					{t('bible.jumpGo')}
				</button>
			</div>
			<!-- Always in the DOM (empty when closed), so aria-controls names it. The
			     options are links: a click is a plain navigation, and mousedown keeps
			     the box's focus so the list isn't torn down before the click lands. -->
			<ul id="bible-jump-list" class="jump-list" role="listbox" aria-label={t('bible.jumpLabel')} hidden={!showList}>
				{#if showList}
					{#each suggestions as s, i (s.href)}
						<li id="bible-jump-opt-{i}" role="option" aria-selected={i === active}>
							<a
								href={localizeHref(s.href)}
								class="jump-opt"
								class:active={i === active}
								tabindex="-1"
								onmousedown={(e) => e.preventDefault()}
								onclick={() => (listOpen = false)}>{s.label}</a
							>
						</li>
					{/each}
				{/if}
			</ul>

		</form>
		<div class="jump-extras">
			{#if quick.length}
				<!-- One tap to the chapters most looked for: the placeholder's own
				     examples first, so they also show what the box takes. -->
				<ul class="quick" aria-label={t('bible.jumpLabel')}>
					{#each quick as p (p.href)}
						<li><a class="chip quick-chip" href={localizeHref(p.href)}>{p.label}</a></li>
					{/each}
				</ul>
			{/if}
			{#if topics.length}
				<!-- For a reader who comes with a subject, not a reference: each opens
				     its topic shelf at "In the Bible", the chapters that shelf's
				     classics and sermons return to most. -->
				<nav class="topics-row" aria-labelledby="topics-row-label">
					<span id="topics-row-label" class="topics-row-label">{say(COPY.passagesOn)}</span>
					<ul class="quick">
						{#each topics as tp (tp.slug)}
							<li>
								<a class="chip quick-chip" href={localizeHref(`/topics/${tp.slug}/#topic-in-bible`)}
									>{tp.label}</a
								>
							</li>
						{/each}
					</ul>
				</nav>
			{/if}
		</div>

		{#if continues.plans.length || continues.books.length}
			<!-- A returning reader's way back in: the books they are partway
			     through, the chapter Continue opens named in the Bible's numbers. -->
			<div class="mb-11">
				<ContinueShelf heading={t('books.continue')}>
					{#each continues.plans as plan (plan.slug)}
						{@const done = planProgress.doneDays(plan.slug).length}
						{@const next = planProgress.nextDay(plan.slug, plan.day_count)}
						{@const meta = planMeta(plan.slug)}
						{@const caption = `${t('plans.day')} ${next} ${t('plans.of')} ${plan.day_count}`}
						<ContinueRow
							href={localizeHref(`/plans/${plan.slug}`)}
							title={plan.title}
							{caption}
							verb={t('plans.continue')}
							hue={meta.accent}
							emblem={meta.emblem}
						>
							{#snippet progress()}
								<ProgressBar
									percent={(done / plan.day_count) * 100}
									label={`${plan.title}: ${done} ${t('plans.of')} ${plan.day_count} ${t('plans.days')}`}
								/>
							{/snippet}
						</ContinueRow>
					{/each}
					{#each continues.books as row (row.book.slug)}
						{@const caption = `${t('continue.chapter')} ${row.chapter} ${t('plans.of')} ${row.count}`}
						<ContinueRow
							href={localizeHref(chapterPath(row.book.slug, row.order, row.book.has_modern_edition))}
							title={row.book.title}
							{caption}
							verb={t('plans.continue')}
						>
							{#snippet visual()}
								<span class="w-10 shrink-0"><BookCover book={row.book} /></span>
							{/snippet}
							{#snippet progress()}
								<ProgressBar
									percent={workPercent(row.record, row.book.chapter_count)}
									label={`${row.book.title}: ${caption}`}
								/>
							{/snippet}
						</ContinueRow>
					{/each}
				</ContinueShelf>
			</div>
		{/if}

		{#if starts.length}
			<!-- For a first reader: a short path in, each step a book and why. -->
			<section class="starts" aria-labelledby="starts-heading">
				<div class="starts-head">
					<h2 id="starts-heading" class="section-label">{t('bible.startHeading')}</h2>
					<!-- The whole Bible in story order, for a reader who wants the shape first. -->
					<a href={localizeHref(`${BIBLE_STORY_PATH}/`)} class="text-small font-medium text-accent hover:underline"
						>{t('bible.storyTitle')} <Arrow /></a
					>
				</div>
				<!-- What brought them: one press shows that path's chapters below. -->
				<div class="start-paths" role="group" aria-label={say(COPY.chooseWay)}>
					<button type="button" class="chip" class:active={!startPath} aria-pressed={!startPath} onclick={() => (pathId = 'first')}
						>{say(COPY.newToBible)}</button
					>
					{#each BIBLE_PATHS as p (p.id)}
						<button
							type="button"
							class="chip"
							class:active={pathId === p.id}
							aria-pressed={pathId === p.id}
							onclick={() => (pathId = p.id)}>{say(p.label)}</button
						>
					{/each}
				</div>
				<p class="mb-4 text-small text-muted" aria-live="polite">{startPath ? say(startPath.lede) : t('bible.startLede')}</p>
				<ol class="start-list" style:--steps={steps.length}>
					{#each steps as { book, title, href, why }, i (href)}
						<li>
							<a class="start card-tint" href={localizeHref(href)}>
								<span class="start-cover"><BookCover {book} rounded="rounded-sm" /></span>
								<span class="start-text">
									<span class="start-step">{i + 1}</span>
									<span class="start-title">{title}</span>
									<span class="start-why">{why}</span>
								</span>
							</a>
						</li>
					{/each}
				</ol>
			</section>
		{/if}

		<!-- The ways to read the whole of it, or a book of it, a day at a time:
		     the Bible-only plans, then the series page, which reads Genesis to
		     Revelation and keeps the reader's place. -->
		<section class="mb-12" aria-labelledby="read-along-heading">
			<h2 id="read-along-heading" class="section-label mb-5">{t('bible.readAlong')}</h2>
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
		</section>

		<!-- The whole canon at a glance, each spine a link to its book page; the
		     grouped index below is the shelf proper. -->
		<BibleCanonStrip books={series?.books ?? []} {placeOf} />
		{#each groups as testament, ti (testament.testament)}
			<!-- A testament is the section; its divisions are the groups under it,
			     so their headings are h3s (the topic page's nested-group recipe). -->
			<section class="bible-testament">
				<div class="testament-head mb-5">
					<h2 class="section-label">{t(testamentKey(testament.testament))}</h2>
					{#if ti === 0}
						<!-- Covers or the compact index, for the whole list: on the first
						     heading's row, where the list begins. Not the book page's "Show as
						     a grid", which here would read as the chapters. -->
						<button type="button" class="btn btn-sm btn-ghost" onclick={() => (asCovers = !asCovers)}>
							<Icon name={asCovers ? 'list' : 'grid'} size={16} />{asCovers
								? t('bible.contentsAsList')
								: say(COPY.showCovers)}
						</button>
					{/if}
				</div>
				{#each testament.divisions as group (group.division.id)}
					<section class="bible-division">
						<GroupHeading as="h3" name={t(divisionKey(group.division.id))} count={group.books.length} />
						{#if asCovers}
							<BibleCoverGrid books={group.books} bind:open={openBook} {placeOf} {linksOf} />
						{:else}
							<BibleBookList books={group.books} bind:open={openBook} {placeOf} {linksOf} />
						{/if}
					</section>
				{/each}
			</section>
		{/each}

		<!-- What the translation is, and its home (it exists wherever the hub does). -->
		<p class="mt-12 text-small">
			<a href={localizeHref(`${OWB_PATH}/`)} class="font-medium text-accent hover:underline"
				>{say(COPY.aboutOwb)} <Arrow /></a
			>
		</p>
	{/if}
</div>

<style>
	.owb-note {
		margin: -0.5rem 0 1.5rem;
		max-width: 40rem;
		font-size: var(--fs-small);
	}
	.owb-note summary {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		min-height: 2.25rem;
		padding: 0.3rem 0.75rem;
		border: 1px solid var(--border-strong);
		border-radius: var(--radius-pill);
		background: var(--surface);
		color: var(--muted);
		cursor: pointer;
		list-style: none;
	}
	.owb-note summary::-webkit-details-marker {
		display: none;
	}
	/* The row's chapter-button chevron, a quarter turn when open. */
	.owb-chev {
		display: inline-flex;
		margin-inline-start: 0.15rem;
		transition: transform var(--duration-base) ease;
	}
	.owb-note[open] .owb-chev {
		transform: rotate(90deg);
	}
	@media (prefers-reduced-motion: reduce) {
		.owb-chev {
			transition: none;
		}
	}
	.owb-note summary:hover {
		color: var(--text);
	}
	.owb-note-body {
		display: grid;
		gap: 0.5rem;
		margin-top: 0.75rem;
		padding-inline-start: 0.75rem;
		border-inline-start: 2px solid var(--border-strong);
		color: var(--muted);
		line-height: 1.55;
	}
	.owb-note-body p {
		margin: 0;
	}
	.jump {
		position: relative;
		margin: 0.25rem 0 0.75rem;
		max-width: 32rem;
	}
	.jump-list {
		position: absolute;
		inset-inline: 0;
		top: 100%;
		z-index: var(--z-popover);
		margin: 0.25rem 0 0;
		padding: 0.25rem;
		list-style: none;
		border: 1px solid var(--border-strong);
		border-radius: var(--radius-sm);
		background: var(--surface);
		box-shadow: var(--shadow-card);
	}
	.jump-opt {
		display: block;
		padding: 0.5rem 0.75rem;
		border-radius: var(--radius-sm);
		color: var(--text);
		text-decoration: none;
	}
	.jump-opt:hover,
	.jump-opt.active {
		background: var(--accent-soft);
		color: var(--accent);
	}
	/* The one-tap passages and the "Passages on…" subjects, one block under
	   the box: it owns the space before what follows. */
	.jump-extras {
		display: grid;
		gap: 0.75rem;
		margin-bottom: 2.25rem;
	}
	.quick {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.topics-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 0.75rem;
	}
	.topics-row-label {
		font-size: var(--fs-small);
		font-weight: 600;
		color: var(--muted);
	}
	.jump-label {
		display: block;
		margin-bottom: 0.4rem;
		font-size: var(--fs-small);
		font-weight: 600;
	}
	.jump-row {
		display: flex;
		gap: 0.5rem;
	}
	.jump-row .field {
		flex: 1;
		min-width: 0;
	}
	.starts {
		margin-bottom: 2.75rem;
	}
	.start-paths {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin-bottom: 0.75rem;
	}
	.start-paths .chip {
		min-height: 2.25rem;
	}
	.starts-head {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.25rem 1rem;
	}
	/* Five steps: a column on a phone, a row of five from the desktop up. */
	.start-list {
		display: grid;
		gap: 0.75rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.start {
		display: flex;
		gap: 0.9rem;
		align-items: center;
		height: 100%;
		padding: 0.6rem;
		border-radius: var(--radius-card);
		color: inherit;
		text-decoration: none;
	}
	.start-cover {
		display: block;
		flex: none;
		width: 3.5rem;
	}
	.start-text {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		min-width: 0;
	}
	.start-step {
		font-size: var(--fs-eyebrow);
		font-weight: 600;
		letter-spacing: 0.08em;
		color: var(--accent);
	}
	.start-title {
		font-family: var(--font-display);
		font-weight: 600;
		color: var(--text);
	}
	.start-why {
		font-size: var(--fs-small);
		color: var(--muted);
		line-height: 1.45;
	}
	/* After the phone rules, so it overrides them. */
	@media (min-width: 1024px) {
		.start-list {
			grid-template-columns: repeat(var(--steps, 5), minmax(0, 1fr));
		}
		.start {
			flex-direction: column;
			align-items: flex-start;
		}
		.start-cover {
			width: 5.5rem;
		}
	}
	.testament-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
	}
	.testament-head h2 {
		margin-bottom: 0;
	}
	.bible-testament + .bible-testament {
		margin-top: 3rem;
	}
	.bible-division + .bible-division {
		margin-top: 2.25rem;
	}
</style>
