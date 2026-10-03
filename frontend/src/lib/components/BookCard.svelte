<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import { type CoverBook } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { readingTime } from '$lib/reading';
	import { splitEdition } from '$lib/edition';
	import { cardSeriesLine } from '$lib/series';
	import BookCover from './BookCover.svelte';
	import { cardTint } from '$lib/coverArt';

	let {
		book,
		showAuthor = false,
		/**
		 * Above the fold: load eagerly with an intrinsic size and high fetch
		 * priority. The LCP element on the two most-linked pages was
		 * `loading="lazy"` and started at opacity-0, which defers the preload
		 * scanner and makes some LCP implementations discount it entirely.
		 */
		priority = false,
		/**
		 * When set, this card is the first of its author's run in the by-author
		 * shelf and carries the `#author-<slug>` target the quick-nav jumps to.
		 */
		anchor,
		/**
		 * The series line ("Book 2 of 6 in Rooted"). Off where the page already
		 * says which series every card is in — the series page, a by-series group.
		 */
		showSeries = true
	}: {
		book: CoverBook;
		showAuthor?: boolean;
		priority?: boolean;
		anchor?: string;
		showSeries?: boolean;
	} = $props();
	const t = i18n.t;

	const chapters = $derived(
		`${book.chapter_count} ${book.chapter_count === 1 ? t('book.chapterOne') : t('book.chaptersMany')}`
	);
	// A young-reader edition's "(For Teens)" / "(For Children)" can be clamped off
	// the title on a narrow card; pull it onto its own line so the two editions
	// don't look identical. Null for ordinary books.
	const edition = $derived(splitEdition(book.slug, book.title));
	const seriesLine = $derived(
		showSeries ? cardSeriesLine(book) : ''
	);
	// The card's tint (app.css, .book-card), from the book's own cover colour.
	const tint = $derived(cardTint(book.cover_color));
</script>

<a
	href={localizeHref(`/books/${book.slug}`)}
	id={anchor ? `author-${anchor}` : undefined}
	class="book-card card-lift group"
	style:scroll-margin-top={anchor ? 'calc(var(--pinned-offset, 5rem) + 0.5rem)' : undefined}
	style:--cover-tint={tint || undefined}
	data-testid="book-card"
	aria-label={showAuthor ? `${book.title} — ${book.author.name}` : book.title}
>
	<!-- The whole cover block (the cover, its hover overlay and the ribbon)
	     tips together on hover, so the overlay stays on the cover. -->
	<div class="book-card-cover relative">
		<BookCover {book} {priority} />
		{#if edition}
			<!-- The audience as a ribbon on the cover, so a teens or children's
			     edition is told apart at a glance across a shelf. Its words are the
			     book's own translated title suffix (edition.ts): no new strings.
			     Hidden from assistive tech: the card's label is the full title,
			     "(For Teens)" and all. -->
			<span class="edition-ribbon" data-kind={edition.kind} aria-hidden="true">{edition.audience}</span>
		{/if}
		<span
			class="pointer-events-none absolute inset-x-0 bottom-0 flex items-center justify-end gap-1 rounded-b-card bg-gradient-to-t from-black/60 to-transparent px-3 pb-2 pt-6 text-small font-semibold text-white opacity-0 transition-opacity group-hover:opacity-100"
		>
			{t('book.beginReading')} <Arrow />
		</span>
	</div>

	<div class="mt-2 flex flex-1 flex-col px-0.5">
		<div class="line-clamp-2 text-small font-medium leading-snug text-text" title={book.title}>
			{edition ? edition.base : book.title}
		</div>
		{#if showAuthor}
			<div class="truncate text-small text-muted" title={book.author.name}>{book.author.name}</div>
		{/if}
		{#if seriesLine}
			<!-- Text, not a link: the whole card is already one. The series page is
			     a tap away on the book page's own series line. -->
			<div class="truncate text-eyebrow font-medium text-accent" title={seriesLine}>{seriesLine}</div>
		{/if}
		<!-- mt-auto pins the meta to the card's bottom, so a one-line title and a
		     two-line title still bottom out level across a grid row. -->
		<!-- Two unbreakable halves with a real break between them: on a narrow
		     card (the library's seven-across) the meta wraps after the dot, not
		     as "3 hr 15 min / read". The separator is an expression so its
		     spaces survive — as literal text they were collapsed, leaving no
		     break opportunity after the dot at all. -->
		<div class="mt-auto pt-0.5 text-eyebrow text-muted">
			<span class="whitespace-nowrap">{chapters}</span>{#if book.word_count}<span
					class="opacity-50">{' · '}</span
				><span class="whitespace-nowrap">{readingTime(book.word_count)}</span>{/if}
		</div>
	</div>
</a>

<style>
	/* A young-reader edition's ribbon across the cover's lower corner: the top
	   carries the author's name on the designed covers, the foot only a small
	   centred mark. Teens in cypress, children in ochre, ink in the surface
	   colour (each hue clears 4.5:1 against --surface in every theme). A long
	   translated audience truncates rather than wrapping over the cover, and
	   the ribbon steps aside on hover for the "Begin reading" label. */
	.edition-ribbon {
		position: absolute;
		bottom: 1.6rem;
		inset-inline-end: -0.25rem;
		max-width: 85%;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
		padding: 0.15rem 0.5rem;
		border-start-start-radius: 3px;
		border-end-start-radius: 3px;
		font-size: var(--fs-micro);
		font-weight: 700;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--surface);
		background: var(--hue-cypress);
		box-shadow: 0 3px 6px -3px rgb(0 0 0 / 0.45);
		pointer-events: none;
		transition: opacity var(--duration-fast);
	}
	.edition-ribbon[data-kind='children'] {
		background: var(--hue-ochre);
	}
	.book-card:hover .edition-ribbon {
		opacity: 0;
	}
	@media print {
		.edition-ribbon {
			color: var(--text);
			background: none;
			border: 1px solid currentColor;
			box-shadow: none;
		}
	}

	/* Hovering tips the cover a little toward the reader, as if being taken off
	   the shelf — on the card lift's own beat (.card-lift), only where there is
	   a real hover (a tap would leave it stuck), mirrored right-to-left, and
	   not at all under reduced motion. */
	@media (hover: hover) and (prefers-reduced-motion: no-preference) {
		.book-card-cover {
			transition: transform var(--duration-fast) ease;
			transform-origin: center bottom;
		}
		.book-card:hover .book-card-cover {
			transform: perspective(700px) rotateY(-9deg);
		}
		:global([dir='rtl']) .book-card:hover .book-card-cover {
			transform: perspective(700px) rotateY(9deg);
		}
	}
</style>
