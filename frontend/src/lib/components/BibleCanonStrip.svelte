<script lang="ts">
	import type { BookSummary } from '$lib/library-public';
	import { onMount } from 'svelte';
	import {
		CANON_FILTERS,
		bibleChapterOrder,
		bibleChapters,
		canonReading,
		matchesCanonFilter,
		type CanonFilter,
		canonStrip,
		divisionKey,
		spineLabel,
		testamentKey,
		type BiblePlace,
		type CanonSlot
	} from '$lib/bible';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/href';
	import { scrollEdges } from '$lib/actions/scrollEdges';
	import Arrow from '$lib/components/Arrow.svelte';
	import { chapterCount, readingMinutes, readingTime } from '$lib/reading';
	import { pickDailyChapter, type DailyChapter } from '$lib/dailyChapter';
	import { bookChapterPath } from '$lib/reading-schema';

	/**
	 * The /bible hub's canon strip: all 66 books as a shelf of slim spines, one
	 * row per testament, grouped by division, each linking to its book. Pure
	 * CSS — no cover images, so 66 books cost no requests: a spine wears its
	 * book's `cover_color` and is as thick as the book is long (`weight`). A
	 * book the language lacks keeps its place as a pale, unlinked outline, so
	 * the canon's shape stays whole however much of it has shipped.
	 *
	 * The spine names are the canon's short names in the page's language
	 * ($lib/bibleNames, via `canonStrip`).
	 * On a phone each row scrolls sideways, snapping to a division.
	 *
	 * A spine's two kinds of length both show: its thickness is the book's
	 * words, its height its chapters (`tall`), so Psalms stands tallest and
	 * Obadiah stays a sliver. A thin spine shows the book's abbreviation, set
	 * whole (`spineLabel`). Where the reader has read (`placeOf`, the page's
	 * own reading of their progress): a finished book carries a tick, a book
	 * under way fills from the shelf up as far as they have read, and a line
	 * above counts them. Nothing personal before mount — the prerender and a
	 * first visit draw the plain shelf.
	 *
	 * Each division is bracketed under its spines with its name, its books and
	 * its reading time; each testament heads its row with its books and
	 * chapters. Pointing at a spine, or reaching it from the keyboard, raises a
	 * card beside it — the book's division, title and subtitle, its chapters
	 * and time, where the reader is, and a way straight in (Begin / Continue).
	 * The card adds nothing a screen reader lacks (the spine's own link and
	 * label carry the book), so it is aria-hidden and its links take no tab
	 * stop. Below 40rem of width (a container query: the strip, not the
	 * window) the spines become wrapped colour tiles under their division's
	 * name: the whole canon in one short scroll, nothing off to the side.
	 *
	 * Each row fills the column: a spine grows from its own width in
	 * proportion to it (`--g`), so the New Testament no longer stops two-thirds
	 * across, and a row too wide for the column still scrolls. The card holds
	 * the book's chapters as a grid — Psalm 23 two moves from the hub — the
	 * read ones quieter, the reader's own marked. The book holding today's
	 * chapter of the day ($lib/dailyChapter, the home page's Today card) wears
	 * a ribbon, with a line over the strip leading to the chapter. Quick
	 * filters (`matchesCanonFilter`) dim the books that don't match rather than
	 * remove them, so the canon keeps its shape.
	 */
	let {
		books,
		placeOf
	}: { books: readonly BookSummary[]; placeOf?: (book: BookSummary) => BiblePlace | null } = $props();
	const t = i18n.t;
	const lang = getLang();
	const testaments = $derived(canonStrip(books, lang));
	const reading = $derived(placeOf ? canonReading(books, placeOf) : null);
	/** A spine's reading: finished, or the share of its chapters behind the reader. */
	function readOf(book: BookSummary, chapters: number): { done: boolean; fill: number } | null {
		const place = placeOf?.(book);
		if (!place) return null;
		if (place.finished) return { done: true, fill: 1 };
		return place.behind > 0 && chapters ? { done: false, fill: place.behind / chapters } : null;
	}

	/** A division's or testament's books present, their words and chapters. */
	function totals(slots: readonly CanonSlot<BookSummary>[]) {
		const here = slots.filter((s) => s.book);
		return {
			books: here.length,
			words: here.reduce((n, s) => n + (s.book!.word_count ?? 0), 0),
			chapters: here.reduce((n, s) => n + s.chapters, 0)
		};
	}
	const booksLabel = (n: number) => `${n} ${i18n.tn(n, 'common.bookOne', 'common.bookMany')}`;

	// --- The card: one, beside whichever spine is pointed at or focused. ---
	let nav = $state<HTMLElement | null>(null);
	let card = $state<{
		slot: CanonSlot<BookSummary>;
		division: string;
		left: number;
		top: number;
	} | null>(null);
	let hideTimer: ReturnType<typeof setTimeout> | undefined;
	/** The card's width (rem) — kept in step with `.canon-card` below. */
	const CARD_REM = 17;
	/** Under this strip width the spines are tiles, with no room for a card. */
	const TILES_PX = 640;

	function show(e: Event, slot: CanonSlot<BookSummary>, division: string) {
		if (!nav) return;
		// The card belongs to a mouse or a keyboard: a touch opens the book.
		const el = e.currentTarget as HTMLElement;
		if (e.type === 'mouseenter' && !matchMedia('(hover: hover) and (pointer: fine)').matches) return;
		if (e.type === 'focus' && !el.matches(':focus-visible')) return;
		if (nav.clientWidth < TILES_PX) return;
		clearTimeout(hideTimer);
		const r = el.getBoundingClientRect();
		const n = nav.getBoundingClientRect();
		const w = CARD_REM * parseFloat(getComputedStyle(document.documentElement).fontSize);
		const left = Math.min(Math.max(r.left - n.left + r.width / 2 - w / 2, 0), Math.max(0, n.width - w));
		card = { slot, division, left, top: r.bottom - n.top + 10 };
	}
	/** Hidden a beat after the pointer leaves, so it can cross to the card. */
	function hideSoon() {
		clearTimeout(hideTimer);
		hideTimer = setTimeout(() => (card = null), 140);
	}
	function keep() {
		clearTimeout(hideTimer);
	}
	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') card = null;
	}
	const cardPlace = $derived(card?.slot.book ? (placeOf?.(card.slot.book) ?? null) : null);
	const cardChapters = $derived(card?.slot.book ? bibleChapters(card.slot.book, lang) : []);

	// --- Today's chapter: by the reader's local date, so only after mount. ---
	let today = $state<DailyChapter | null>(null);
	onMount(() => {
		today = pickDailyChapter(new Date(), lang);
	});
	const todayBook = $derived(today ? books.find((b) => b.slug === today!.slug) : undefined);

	// --- Quick filters: dim what doesn't match. ---
	let filter = $state<CanonFilter | null>(null);
	const filterLabel = (f: CanonFilter) =>
		f === 'short'
			? t('bible.filterShort')
			: f === 'gospels'
				? t('bible.division_gospels')
				: f === 'poetry'
					? t('bible.filterPoetry')
					: f === 'letters'
						? t('bible.filterLetters')
						: t('bible.filterUnread');
	/** Whether `slot` matches filter `f`. */
	function matches(f: CanonFilter, slot: CanonSlot<BookSummary>, divisionId: string): boolean {
		const b = slot.book;
		if (!b) return false;
		return matchesCanonFilter(
			f,
			divisionId,
			b.word_count ? readingMinutes(b.word_count) : null,
			placeOf?.(b) ?? null
		);
	}
	/** Each filter on offer with how many books it keeps. "Not started" only
	 *  once the reader has started one — before that it would keep them all. */
	const filters = $derived(
		CANON_FILTERS.filter((f) => f !== 'unread' || !!(reading && (reading.finished || reading.started))).map(
			(f) => ({
				f,
				count: testaments.reduce(
					(n, tm) =>
						n +
						tm.divisions.reduce(
							(m, d) => m + d.slots.filter((sl) => matches(f, sl, d.division.id)).length,
							0
						),
					0
				)
			})
		)
	);
	/** A spine's grow factor: its own width, in rem, as a unitless number. */
	const grow = (slot: CanonSlot<BookSummary>) => (slot.book ? 1.0625 + slot.weight * 1.125 : 1.0625);
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<nav class="canon" aria-label={t('bible.canonLabel')} bind:this={nav} onkeydown={onKey}>
	{#if reading && (reading.finished || reading.started)}
		<!-- The reader's Bible at a glance: what the ticks and fills below add up to. -->
		<div class="canon-meter">
			<span class="font-display font-semibold"
				>{t('bible.canonRead').replace('%n%', String(reading.finished)).replace('%total%', String(reading.total))}</span
			>
			{#if reading.started}
				<span class="text-small text-muted">{t('bible.canonUnderWay').replace('%n%', String(reading.started))}</span>
			{/if}
			<span class="canon-bar" aria-hidden="true"
				><i style:width="{(reading.finished / Math.max(1, reading.total)) * 100}%"></i></span
			>
		</div>
	{/if}
	{#if today && todayBook}
		<!-- Today's chapter (the home page's Today card): its book wears the
		     ribbon below. -->
		<a class="canon-today" href={localizeHref(today.href)}
			><span class="canon-today-mark" aria-hidden="true"></span>{t('home.todayChapter')}
			<span class="font-semibold">{today.title}</span> <Arrow /></a
		>
	{/if}
	<div class="canon-filters" role="group" aria-label={t('bible.filterLabel')}>
		{#each filters as { f, count } (f)}
			<button
				type="button"
				class="canon-chip"
				aria-pressed={filter === f}
				onclick={() => (filter = filter === f ? null : f)}>{filterLabel(f)} <span class="canon-chip-n">{count}</span></button
			>
		{/each}
	</div>
	{#each testaments as testament (testament.testament)}
		{@const all = totals(testament.divisions.flatMap((d) => d.slots))}
		<div class="canon-row">
			<p class="canon-testament">
				<span class="eyebrow-micro text-muted">{t(testamentKey(testament.testament))}</span>
				{#if all.books}
					<span class="canon-totals">{booksLabel(all.books)} · {chapterCount(all.chapters)}</span>
				{/if}
			</p>
			<ol class="canon-shelf cover-rail" use:scrollEdges>
				{#each testament.divisions as group (group.division.id)}
					{@const sum = totals(group.slots)}
					{@const divisionName = t(divisionKey(group.division.id))}
					<li
						class="canon-division"
						style:--dg={group.slots.reduce((n, sl) => n + grow(sl), 0) + (group.slots.length - 1) * 0.125}
					>
						<ol class="canon-spines" aria-label={t(divisionKey(group.division.id))}>
							{#each group.slots as slot (slot.position)}
								<!-- An absent book has nothing to open, so nothing to announce:
								     a screen reader hears the books that are here. -->
								<li
									aria-hidden={slot.book ? undefined : 'true'}
									style:--g={grow(slot)}
									class:dim={filter && !matches(filter, slot, group.division.id)}
								>
									{#if slot.book}
										{@const read = readOf(slot.book, slot.chapters)}
										<a
											class="spine"
											class:done={read?.done}
											class:today={todayBook?.slug === slot.book.slug}
											href={localizeHref(`/books/${slot.book.slug}`)}
											title={slot.book.title}
											aria-label={read?.done
												? `${slot.book.title} · ${t('bible.canonFinished')}`
												: slot.book.title}
											onmouseenter={(e) => show(e, slot, divisionName)}
											onmouseleave={hideSoon}
											onfocus={(e) => show(e, slot, divisionName)}
											onblur={hideSoon}
											style:--spine-w={slot.weight}
											style:--spine-t={slot.tall}
											style:--spine-c={slot.book.cover_color || null}
											>{#if todayBook?.slug === slot.book.slug}<span class="spine-ribbon" aria-hidden="true"
												></span>{/if}{#if read && !read.done}<span class="spine-fill" style:height="{read.fill * 100}%" style:--fill-w="{read.fill * 100}%"
												></span>{/if}<span class="spine-name long">{spineLabel(slot)}</span><span
												class="spine-name short">{slot.abbr}</span
											></a
										>
									{:else}
										<span class="spine absent" title={slot.name}><span class="spine-name">{slot.abbr}</span></span>
									{/if}
								</li>
							{/each}
						</ol>
						<!-- The division, bracketed: its name, then its books and time. A
						     one-book division (Acts, Revelation) is named by its spine, so
						     on the shelf its label keeps only its height (its spine still
						     stands on the row's one shelf line); the phone's tiles name it.
						     Visual only: the list's aria-label names it for a screen reader. -->
						<span class="canon-label" class:single={group.slots.length === 1} aria-hidden="true">
							<span class="canon-label-name">{divisionName}</span>
							<span class="canon-label-meta"
								>{#if sum.books > 1}{booksLabel(sum.books)}{#if sum.words}{` · ${readingTime(sum.words)}`}{/if}{:else}&nbsp;{/if}</span
							>
						</span>
					</li>
				{/each}
			</ol>
		</div>
	{/each}
	{#if card?.slot.book}
		{@const b = card.slot.book}
		{@const into = cardPlace?.current != null ? bibleChapterOrder(cardPlace.current) : 1}
		<!-- Beside the spine: what a reader decides by, and a way in. aria-hidden,
		     no tab stops: the spine's own link already carries the book. -->
		<div
			class="canon-card"
			style:left="{card.left}px"
			style:top="{card.top}px"
			aria-hidden="true"
			role="presentation"
			onmouseenter={keep}
			onmouseleave={hideSoon}
		>
			<span class="eyebrow-micro text-muted">{card.division}</span>
			<a class="canon-card-title" href={localizeHref(`/books/${b.slug}`)} tabindex="-1">{b.title}</a>
			{#if b.subtitle}<span class="canon-card-sub">{b.subtitle}</span>{/if}
			<span class="text-small text-muted"
				>{chapterCount(card.slot.chapters)}{#if b.word_count}{` · ${readingTime(b.word_count)}`}{/if}</span
			>
			{#if cardPlace?.finished}
				<span class="text-small font-semibold text-accent">{t('bible.canonFinished')}</span>
			{:else if cardPlace?.current != null}
				<span class="text-small font-semibold text-accent"
					>{t('book.chapterOf').replace('%n%', String(cardPlace.current)).replace('%t%', String(card.slot.chapters))}</span
				>
			{/if}
			{#if cardChapters.length > 1}
				<!-- Straight to a chapter: the read ones quieter, the reader's own marked. -->
				<span class="canon-card-chapters">
					{#each cardChapters as ch (ch.n)}
						<a
							href={localizeHref(ch.href)}
							tabindex="-1"
							title={ch.name}
							class:read={cardPlace?.finished || ch.n <= (cardPlace?.behind ?? 0)}
							class:current={cardPlace?.current === ch.n}>{ch.n}</a
						>
					{/each}
				</span>
			{/if}
			<a class="btn btn-primary btn-solid mt-2" href={localizeHref(bookChapterPath(b.slug, into, false))} tabindex="-1"
				>{cardPlace?.current != null ? t('book.continue') : t('book.beginReading')}</a
			>
		</div>
	{/if}
</nav>

<style>
	.canon {
		position: relative;
		margin-bottom: 3rem;
		/* The phone layout keys off the strip's own width (see the end). */
		container-type: inline-size;
	}
	.canon-row + .canon-row {
		margin-top: 1.25rem;
	}
	.canon-testament {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.15rem 0.6rem;
		margin-bottom: 0.5rem;
	}
	.canon-totals {
		font-size: var(--fs-micro);
		color: var(--muted);
	}
	.canon-shelf {
		display: flex;
		/* One shelf line for the whole row: spines are as tall as their book's
		   chapters, so each division is a different height, and its label sits
		   under the line. */
		align-items: flex-end;
		gap: 0.75rem;
		/* Room for a spine's hover rise inside the scroller's clip. */
		padding-top: 0.375rem;
		padding-bottom: 0.25rem;
		scroll-snap-type: x proximity;
		scroll-padding-inline: 0;
	}
	.canon-division {
		display: flex;
		flex-direction: column;
		/* Fills the row: grows by its spines' summed widths, never below them. */
		flex: var(--dg, 1) 0 auto;
		scroll-snap-align: start;
	}
	.canon-spines > li {
		display: flex;
		flex: var(--g, 1) 0 auto;
		align-items: flex-end;
		transition: opacity 0.15s ease;
	}
	/* Not what the quick filter asks for: still there, set back. */
	.canon-spines > li.dim {
		opacity: 0.22;
	}
	.canon-spines {
		display: flex;
		align-items: flex-end;
		gap: 2px;
		/* The shelf the spines stand on. */
		border-bottom: 1px solid var(--border-strong);
		padding-bottom: 1px;
	}
	/* The division's bracket: short ticks down from the shelf line at both
	   ends, then its name and, under it, its books and time — set within the
	   division's own width (`width: 0; min-width: 100%`), never widening it. */
	.canon-label {
		position: relative;
		display: flex;
		flex-direction: column;
		width: 0;
		min-width: 100%;
		margin-top: 0.3rem;
		padding: 0.45rem 0.3rem 0;
		font-size: var(--fs-micro);
		line-height: 1.3;
		color: var(--muted);
	}
	.canon-label::before,
	.canon-label::after {
		content: '';
		position: absolute;
		top: 0;
		width: 1px;
		height: 0.4rem;
		background: var(--border-strong);
	}
	.canon-label::before {
		inset-inline-start: 0;
	}
	.canon-label::after {
		inset-inline-end: 0;
	}
	.canon-label-name {
		font-weight: 600;
		color: var(--text);
		white-space: nowrap;
	}
	.canon-label-meta {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	/* A one-book division: no bracket or name on the shelf (its spine names
	   it), only the label's height, so the spine stands on the shelf line. */
	.canon-label.single::before,
	.canon-label.single::after {
		display: none;
	}
	.canon-label.single {
		/* Its hidden name keeps the label's height but must not widen the row. */
		overflow: hidden;
	}
	.canon-label.single .canon-label-name {
		visibility: hidden;
	}
	.spine-name.short {
		display: none;
	}
	/* The card beside a spine. */
	.canon-card {
		position: absolute;
		z-index: 5;
		display: grid;
		gap: 0.2rem;
		width: 17rem;
		padding: 0.8rem 0.95rem 0.9rem;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-popover);
	}
	.canon-card-title {
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		font-weight: 600;
		line-height: 1.2;
		color: var(--text);
		text-decoration: none;
	}
	.canon-card-title:hover {
		color: var(--accent);
	}
	.canon-card-sub {
		font-family: var(--font-display);
		font-style: italic;
		font-size: var(--fs-small);
		color: var(--muted);
	}
	.canon-card .btn {
		justify-self: start;
	}
	.canon-card-chapters {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(1.85rem, 1fr));
		gap: 3px;
		max-height: 8.25rem;
		margin-top: 0.4rem;
		overflow-y: auto;
		overscroll-behavior: contain;
	}
	.canon-card-chapters a {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 1.7rem;
		border-radius: 4px;
		background: var(--surface-2, var(--bg));
		font-size: var(--fs-micro);
		font-variant-numeric: tabular-nums;
		color: var(--text);
		text-decoration: none;
	}
	.canon-card-chapters a:hover {
		background: var(--accent);
		color: var(--bg);
	}
	.canon-card-chapters a.read {
		color: var(--muted);
		opacity: 0.6;
	}
	.canon-card-chapters a.current {
		outline: 1.5px solid var(--accent);
		color: var(--accent);
		opacity: 1;
		font-weight: 600;
	}
	/* Today's chapter, over the strip. */
	.canon-today {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		margin-bottom: 0.75rem;
		font-size: var(--fs-small);
		color: var(--accent);
		text-decoration: none;
	}
	.canon-today:hover {
		text-decoration: underline;
	}
	.canon-today-mark {
		width: 0.45rem;
		height: 0.8rem;
		/* hex-ok: the ribbon's gilt, the same in both themes */
		background: #c9973a;
		clip-path: polygon(0 0, 100% 0, 100% 100%, 50% 75%, 0 100%);
	}
	/* The quick filters: a row of small chips. */
	.canon-filters {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		margin-bottom: 1rem;
	}
	.canon-chip {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.2rem 0.7rem;
		border: 1px solid var(--border-strong);
		border-radius: var(--radius-pill);
		background: transparent;
		font-size: var(--fs-small);
		color: var(--text);
		cursor: pointer;
	}
	.canon-chip:hover {
		border-color: var(--accent);
	}
	.canon-chip[aria-pressed='true'] {
		background: var(--accent);
		border-color: var(--accent);
		color: var(--bg);
	}
	.canon-chip-n {
		font-size: var(--fs-micro);
		opacity: 0.7;
	}
	/* Today's book: a gilt ribbon hanging from its head. In the spine's
	   vertical writing the block axis is the horizontal one, so inset-block
	   with auto margins centres it across the spine. */
	.spine-ribbon {
		position: absolute;
		top: 0;
		inset-block: 0;
		margin-block: auto;
		width: 0.45rem;
		height: 1.3rem;
		/* hex-ok: the ribbon's gilt, the same in both themes */
		background: #c9973a;
		clip-path: polygon(0 0, 100% 0, 100% 100%, 50% 78%, 0 100%);
		z-index: 1;
	}
	.spine {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		box-sizing: border-box;
		/* 17px for the shortest book, 35px for the longest: both testaments
		   fit a desktop column, and scroll on anything narrower. */
		/* The spine's own width is its floor; the row's spare room widens it
		   in proportion (`--g` on its item). */
		min-width: calc(1.0625rem + var(--spine-w, 0) * 1.125rem);
		width: 100%;
		/* Chapters set the height (`tall`): 5rem for one, 8.5rem for Psalms'
		   150. The spines stand on one shelf line, so only the tops vary. */
		height: calc(5rem + var(--spine-t, 0.4) * 3.5rem);
		/* Physical sides: in vertical writing, padding-block is left and right,
		   and would floor every spine's width at the padding. */
		padding: 0.9rem 0;
		writing-mode: vertical-rl;
		border-radius: 2px 2px 1px 1px;
		/* hex-ok: a cover colour, not a theme colour — the book's own cloth, dark in both themes */
		background: var(--spine-c, #4a3a2a);
		/* A little roundness; the gilt bands are the ::before / ::after rules,
		   at the very ends, clear of the name. */
		background-image: linear-gradient(to right, rgb(255 255 255 / 0.1), transparent 40%, rgb(0 0 0 / 0.18));
		/* hex-ok: light ink on that dark cloth, as a cover sets its title */
		color: #f3ead9;
		/* The interface face, upright weight: a name read sideways at this size
		   needs the sans's open shapes more than the serif's character. */
		font-family: var(--font-sans);
		font-size: var(--fs-eyebrow);
		font-weight: 600;
		letter-spacing: 0.02em;
		line-height: 1;
		white-space: nowrap;
		overflow: hidden;
		text-decoration: none;
		transition: transform 0.15s ease;
	}
	.spine::before,
	.spine::after {
		content: '';
		position: absolute;
		/* Across the spine: in its vertical writing the block axis is the
		   horizontal one (inset-inline would run top to bottom). */
		inset-block: 0 0;
		height: 1px;
		background: rgb(224 180 92 / 0.6);
	}
	.spine::before {
		top: 0.45rem;
	}
	.spine::after {
		bottom: 0.45rem;
	}
	.spine-name {
		position: relative;
	}
	/* A book under way: lighter cloth from the shelf up, as far as the reader
	   has read, under a gilt line. */
	.spine-fill {
		position: absolute;
		/* Across the spine: in its vertical writing the block axis is the
		   horizontal one (inset-inline would run top to bottom). */
		inset-block: 0 0;
		bottom: 0;
		background: rgb(255 255 255 / 0.2);
		border-top: 1px solid rgb(224 180 92 / 0.85);
	}
	/* A finished book: a gilt tick at its foot, set upright. */
	.spine.done::after {
		content: '✓';
		height: auto;
		/* In the tick's OWN writing (horizontal), where block is top and bottom:
		   the shared rule's inset-block would pin it to the top as well. */
		inset-block: auto 0.3rem;
		inset-inline: 0;
		background: none;
		writing-mode: horizontal-tb;
		text-align: center;
		font-size: var(--fs-micro);
		line-height: 1;
		color: rgb(240 200 110);
	}
	.spine.done {
		padding-bottom: 1.3rem;
	}
	/* The reader's count over the strip, and a bar of the canon read. */
	.canon-meter {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.35rem 0.9rem;
		margin-bottom: 1rem;
	}
	.canon-bar {
		flex: 1 1 12rem;
		max-width: 22rem;
		height: 6px;
		border-radius: var(--radius-pill);
		background: var(--border);
		overflow: hidden;
	}
	.canon-bar i {
		display: block;
		height: 100%;
		background: var(--accent);
	}
	a.spine:hover,
	a.spine:focus-visible {
		transform: translateY(-0.375rem);
	}
	a.spine:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}
	.spine.absent {
		width: 1.0625rem;
		height: 6rem;
		background: none;
		border: 1px dashed var(--border-strong);
		color: var(--muted);
		opacity: 0.6;
	}
	.spine.absent::before,
	.spine.absent::after {
		display: none;
	}
	@media (prefers-reduced-motion: reduce) {
		.spine {
			transition: none;
		}
	}

	/* --- Phone: wrapped colour tiles, grouped by division. ---
	   Under 40rem of strip the side-scrolling shelf hid most of the canon off
	   to the side. Here every division is a block — its name, its books and
	   time, then its books as tiles that wrap — so all 66 fit one short
	   scroll. The same links, restyled: a tile is a spine laid flat. */
	@container (max-width: 40rem) {
		.canon-shelf {
			display: grid;
			grid-template-columns: 1fr 1fr;
			align-items: start;
			gap: 1rem 0.9rem;
			overflow: visible;
			padding: 0;
		}
		.canon-division {
			min-width: 0;
		}
		/* A division of more than five books takes the row. */
		.canon-division:has(.canon-spines > li:nth-child(6)) {
			grid-column: 1 / -1;
		}
		.canon-label {
			order: -1;
			width: auto;
			min-width: 0;
			margin: 0 0 0.35rem;
			padding: 0;
		}
		.canon-label::before,
		.canon-label::after {
			display: none;
		}
		.canon-label.single {
			overflow: visible;
		}
		.canon-label.single .canon-label-name {
			visibility: visible;
		}
		.canon-label.single .canon-label-meta {
			display: none;
		}
		.canon-spines {
			flex-wrap: wrap;
			align-items: stretch;
			gap: 4px;
			border: 0;
			padding: 0;
		}
		.spine {
			writing-mode: horizontal-tb;
			width: auto;
			min-width: 2.9rem;
			height: 2.1rem;
			padding: 0 0.5rem;
			border-radius: 4px;
		}
		.spine.done {
			padding: 0 1.1rem 0 0.5rem;
		}
		.spine::before,
		.spine:not(.done)::after {
			display: none;
		}
		.spine.done::after {
			top: 50%;
			bottom: auto;
			inset-inline: auto 0.3rem;
			transform: translateY(-50%);
		}
		/* Read so far: from the tile's start, as far as the reader has read. */
		.spine-fill {
			inset-block: 0;
			inset-inline-start: 0;
			width: var(--fill-w);
			height: auto !important;
			border-top: 0;
			border-inline-end: 1px solid rgb(224 180 92 / 0.85);
		}
		.spine-name.long {
			display: none;
		}
		.spine-name.short {
			display: inline;
		}
		a.spine:hover,
		a.spine:focus-visible {
			transform: none;
		}
		.spine.absent {
			width: auto;
			height: 2.1rem;
		}
		/* Tiles keep their own widths: no growing to fill a row. */
		.canon-division {
			flex: none;
		}
		.canon-spines > li {
			flex: none;
		}
		.spine {
			min-width: 2.9rem;
		}
		/* The ribbon on a tile: from its top edge, near its end. */
		.spine-ribbon {
			inset-block: 0 auto;
			inset-inline: auto 0.35rem;
			margin: 0;
			height: 0.95rem;
		}
	}
</style>
