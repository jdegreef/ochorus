<script lang="ts">
	/**
	 * "From my reading" — the Notebook's clippings: every highlight, margin note
	 * and bookmark the reader made in a book, sermon or biography, quoted from
	 * the text it was made on. Lifted out of the Notebook page when the page
	 * grew its own writing (the journal); the loading and filtering are unchanged.
	 */
	import { onMount } from 'svelte';
	import { getBook, getChapter, getSermon, getAuthor, type BookDetail } from '$lib/library-public';
	import { getLang, localeName } from '$lib/lang.svelte';
	import { editionHref } from '$lib/editionHref';
	import { bookmarks, byPosition } from '$lib/bookmarks.svelte';
	import { marks } from '$lib/marks.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { chapterLabel } from '$lib/reading';
	import {
		MODERN_EDITION,
		baseEdition,
		type Bookmark,
		type Mark,
		type WorkKind
	} from '$lib/reading-schema';
	import { createLimiter, NOTEBOOK_CONCURRENCY } from '$lib/limiter';
	import { paragraphs, groupMarks, type Highlight as HL } from '$lib/markText';

	const t = i18n.t;

	// `edition` rides along so a highlight can be linked back into the text it
	// was made on, and named when that is not the edition the page is in.

	// One block per (chapter, EDITION). A chapter highlighted in both the
	// original and the Modern English text is two blocks, because the quoted
	// passages come from two different texts and only their own offsets index
	// them — see `editionLabel` for how the second one is named.
	type ChapterBlock = {
		order: number;
		edition: string;
		title: string;
		highlights: HL[];
	};
	type BookBlock = {
		slug: string;
		title: string;
		author: string;
		bookmarks: Bookmark[];
		chapters: ChapterBlock[];
	};

	type SermonBlock = {
		slug: string;
		title: string;
		author: string;
		bookmarks: Bookmark[];
		highlights: HL[];
	};
	// A biography block: the slug is the author's; the "title" is their name.
	type BioBlock = { slug: string; name: string; bookmarks: Bookmark[]; highlights: HL[] };

	let {
		view,
		query,
		colorFilter
	}: {
		/** Which lanes show: 'notes' keeps only highlights with a margin note. */
		view: 'all' | 'highlights' | 'notes' | 'bookmarks';
		query: string;
		/** '' = every colour. */
		colorFilter: string;
	} = $props();

	let loading = $state(true);
	let books = $state<BookBlock[]>([]);
	let sermons = $state<SermonBlock[]>([]);
	let bios = $state<BioBlock[]>([]);

	const q = $derived(query.trim().toLowerCase());
	const active = $derived(q.length > 0 || colorFilter !== '' || view !== 'all');

	// Each view decides which lanes show. Bookmarks aren't highlights and carry no
	// colour, so a colour filter hides them; the notes view keeps only highlights
	// that carry a note.
	const showBookmarks = $derived(view === 'all' || view === 'bookmarks');
	const showHighlights = $derived(view !== 'bookmarks');
	const notesOnly = $derived(view === 'notes');

	const filtered = $derived.by(() => {
		if (!active) return books;
		const hit = (s: string) => s.toLowerCase().includes(q);
		return books
			.map((bk) => {
				const bookHit = !q || hit(bk.title) || hit(bk.author);
				// Bookmarks aren't coloured, so a colour filter hides them; a view
				// that isn't showing bookmarks hides them too.
				const bookmarks =
					!showBookmarks || colorFilter
						? []
						: bookHit
							? bk.bookmarks
							: bk.bookmarks.filter((b) => hit(b.snippet) || hit(b.title));
				const chapters = showHighlights
					? bk.chapters
							.map((ch) => ({
								...ch,
								highlights: ch.highlights.filter(
									(h) =>
										(!colorFilter || h.color === colorFilter) &&
										(!notesOnly || !!h.note) &&
										(bookHit || hit(h.text) || hit(h.note ?? '') || hit(ch.title))
								)
							}))
							.filter((ch) => ch.highlights.length)
						: [];
				return { ...bk, bookmarks, chapters };
			})
			.filter((bk) => bk.bookmarks.length || bk.chapters.length);
	});
	/** Bookmarks surviving the query — same rule the books lane uses. */
	const matchingBookmarks = (
		list: Bookmark[],
		workHit: boolean,
		hit: (s: string) => boolean
	) =>
		// Bookmarks aren't coloured, so a colour filter hides them; a view that
		// isn't showing bookmarks hides them too.
		!showBookmarks || colorFilter
			? []
			: workHit
				? list
				: list.filter((b) => hit(b.snippet) || hit(b.title));

	/** Highlights surviving the colour / notes / query filters — the sermon and
	 * biography lanes share it (their highlights are a flat list, unlike a book's
	 * per-chapter ones, which stay inline). */
	const matchingHighlights = (list: HL[], workHit: boolean, hit: (s: string) => boolean) =>
		showHighlights
			? list.filter(
					(h) =>
						(!colorFilter || h.color === colorFilter) &&
						(!notesOnly || !!h.note) &&
						(workHit || hit(h.text) || hit(h.note ?? ''))
				)
			: [];

	const filteredSermons = $derived.by(() => {
		if (!active) return sermons;
		const hit = (s: string) => s.toLowerCase().includes(q);
		return sermons
			.map((sm) => {
				const sermonHit = !q || hit(sm.title) || hit(sm.author);
				return {
					...sm,
					bookmarks: matchingBookmarks(sm.bookmarks, sermonHit, hit),
					highlights: matchingHighlights(sm.highlights, sermonHit, hit)
				};
			})
			.filter((sm) => sm.bookmarks.length || sm.highlights.length);
	});
	const filteredBios = $derived.by(() => {
		if (!active) return bios;
		const hit = (s: string) => s.toLowerCase().includes(q);
		return bios
			.map((b) => {
				const bioHit = !q || hit(b.name);
				return {
					...b,
					bookmarks: matchingBookmarks(b.bookmarks, bioHit, hit),
					highlights: matchingHighlights(b.highlights, bioHit, hit)
				};
			})
			.filter((b) => b.bookmarks.length || b.highlights.length);
	});
	const hasContent = $derived(books.length > 0 || sermons.length > 0 || bios.length > 0);
	const noMatches = $derived(
		!loading &&
			hasContent &&
			active &&
			filtered.length === 0 &&
			filteredSermons.length === 0 &&
			filteredBios.length === 0
	);

	// paragraphs() / groupMarks() (and the HL type) are shared with the in-reader
	// notes drawer via $lib/markText.

	/**
	 * How a block's edition is named, or '' for the one the page is already in.
	 *
	 * A chapter highlighted in two editions is two blocks with the same number
	 * and title, so without this they read as a duplicate rather than as the
	 * original and the modern text.
	 */
	function editionLabel(edition: string): string {
		if (edition === getLang()) return '';
		if (edition === MODERN_EDITION) return t('reader.modernEdition');
		return localeName(baseEdition(edition));
	}

	// Every fetch below is wrapped in its own try/catch and every failure is the
	// same one: the reader is offline. A highlight still links through to where
	// it was made, it just can't show its own text — so one unreachable chapter
	// degrades that card, never the page. That per-item tolerance is also what
	// makes the concurrency below safe: nothing here rejects.
	onMount(async () => {
		const lang = getLang();
		const bms = bookmarks.all();
		// Split by EDITION, and every edition is shown. The page used to ask for
		// `lang` alone, which meant a highlight made on the Modern English text
		// simply had no entry here — and before editions were tagged at all it
		// was worse: the passage was sliced out of the ORIGINAL text, quoting the
		// reader words they never highlighted. Each group is fetched in its own
		// edition below, so every quotation comes from the text it was made on.
		const allMarks = marks.allByEdition(lang);
		type MarkEntry = (typeof allMarks)[number];
		const mks = allMarks.filter((m) => m.kind === 'book');
		// Bookmarks now exist on all three kinds, so each lane takes its own —
		// and each lane's membership is the UNION of what was highlighted and
		// what was bookmarked. Keying a lane on highlights alone would drop a
		// sermon someone bookmarked and never highlighted, which is the whole
		// point of a bookmark: the place you meant to come back to.
		const bmOf = (kind: WorkKind) => bms.filter((b) => b.kind === kind);
		const bookBms = bmOf('book');
		const sermonBms = bmOf('sermon');
		const bioBms = bmOf('bio');
		const slugs = [...new Set([...bookBms.map((b) => b.slug), ...mks.map((m) => m.slug)])];

		// The whole page used to load one request at a time, nested two deep:
		// every book, then every highlighted chapter within it, then every
		// sermon, then every biography. A reader with highlights across ten
		// books waited out fifty sequential round-trips staring at an ellipsis,
		// and the wait grew with exactly the history the page exists to show.
		// Now the three sections load together under ONE ceiling for the page.
		// The gate wraps each FETCH, never the per-book work that awaits one:
		// a task holding a slot while it waits for a slot deadlocks, and the
		// books lane is exactly that shape (a book, then its chapters). Bounding
		// each lane separately instead would bound every call correctly and the
		// page not at all — three lanes of six, one of them fanning out six
		// chapters apiece, is forty-eight requests in flight.
		const gate = createLimiter(NOTEBOOK_CONCURRENCY);

		// A bookmark carries the title FROZEN at the moment it was saved, so a
		// title corrected since then left it quoting text that appears nowhere
		// else on the page. `live` reads the current one — per chapter for books,
		// the work's own for sermons and biographies, which are single documents.
		// It returns undefined when the fetch failed, and offline the snapshot is
		// the only title there is.
		const bookmarksFor = (
			list: (Bookmark & { slug: string })[],
			slug: string,
			live: (b: Bookmark) => string | undefined
		) =>
			list
				.filter((b) => b.slug === slug)
				.sort(byPosition)
				.map((b) => ({ ...b, title: live(b) || b.title }));

		const loadBook = async (slug: string): Promise<BookBlock> => {
			let book: BookDetail | null = null;
			try {
				book = await gate(() => getBook(slug, lang));
			} catch {
				/* offline — fall back to slug/order labels */
			}
			const chapterTitle = (order: number) => book?.chapters.find((c) => c.order === order)?.title;

			const chapters = await Promise.all(
				mks
					.filter((m) => m.slug === slug)
					.sort((a, b) => a.order - b.order || a.edition.localeCompare(b.edition))
					.map(async ({ order, edition, marks: ms }): Promise<ChapterBlock> => {
						let paras: string[] = [];
						try {
							// The chapter in THIS group's edition, not the page's. That is
							// the whole fix: `getChapter(slug, order, 'en-modern')` is how
							// the reader loads the modern text, and its characters are the
							// ones these offsets index.
							const chapter = await gate(() => getChapter(slug, order, edition));
							paras = paragraphs(chapter.body_html);
						} catch {
							/* offline — the highlight still links through, just without its text */
						}
						return {
							order,
							edition,
							title: chapterTitle(order) || `${order}`,
							highlights: groupMarks(paras, ms, edition)
						};
					})
			);

			return {
				slug,
				title: book?.title || slug,
				author: book?.author.name || '',
				bookmarks: bookmarksFor(bookBms, slug, (b) => chapterTitle(b.order)),
				chapters
			};
		};

		/** Every slug of `kind` that was highlighted or bookmarked, once each. */
		const slugsOf = (kind: WorkKind, bookmarked: (Bookmark & { slug: string })[]) => [
			...new Set([
				...allMarks.filter((m) => m.kind === kind).map((m) => m.slug),
				...bookmarked.map((b) => b.slug)
			])
		];
		/** Every edition this work was highlighted in, each with its own marks. */
		const editionsFor = (kind: WorkKind, slug: string): MarkEntry[] =>
			allMarks
				.filter((m) => m.kind === kind && m.slug === slug)
				.sort((a, b) => a.edition.localeCompare(b.edition));

		// Sermon marks and bookmarks (device-local, keyed by sermon slug — no chapters).
		//
		// One fetch per EDITION highlighted, so each passage is sliced from the
		// text it was measured on. A work read in one edition — nearly all of
		// them — is one fetch, exactly as before; the metadata is taken from the
		// page's own edition when that is among them, else from whichever
		// response arrived, so a title is still shown.
		const loadSermon = async (slug: string): Promise<SermonBlock> => {
			const editions = editionsFor('sermon', slug);
			const wanted = editions.length ? editions : [{ edition: lang, marks: [] as Mark[] }];
			const parts = await Promise.all(
				wanted.map(async ({ edition, marks: ms }) => {
					try {
						const sermon = await gate(() => getSermon(slug, edition));
						return {
							edition,
							title: sermon.title,
							author: sermon.author_name,
							highlights: groupMarks(paragraphs(sermon.body_html), ms, edition)
						};
					} catch {
						/* offline — the saved place still links through, just without its text */
						return { edition, title: '', author: '', highlights: groupMarks([], ms, edition) };
					}
				})
			);
			const named = parts.find((p) => p.edition === lang && p.title) ?? parts.find((p) => p.title);
			return {
				slug,
				title: named?.title || slug,
				author: named?.author || '',
				bookmarks: bookmarksFor(sermonBms, slug, () => named?.title),
				highlights: parts.flatMap((p) => p.highlights)
			};
		};

		// Biographies (kind 'bio'; the slug names the author). Per edition, for
		// the same reason as sermons above.
		const loadBio = async (slug: string): Promise<BioBlock> => {
			const editions = editionsFor('bio', slug);
			const wanted = editions.length ? editions : [{ edition: lang, marks: [] as Mark[] }];
			const parts = await Promise.all(
				wanted.map(async ({ edition, marks: ms }) => {
					try {
						const a = await gate(() => getAuthor(slug, edition));
						return { edition, name: a.name, highlights: groupMarks(paragraphs(a.bio_html), ms, edition) };
					} catch {
						/* offline — the saved place still links through, just without its text */
						return { edition, name: '', highlights: groupMarks([], ms, edition) };
					}
				})
			);
			const named = parts.find((p) => p.edition === lang && p.name) ?? parts.find((p) => p.name);
			return {
				slug,
				name: named?.name || slug,
				bookmarks: bookmarksFor(bioBms, slug, () => named?.name),
				highlights: parts.flatMap((p) => p.highlights)
			};
		};

		const [bookBlocks, sermonBlocks, bioBlocks] = await Promise.all([
			Promise.all(slugs.map(loadBook)),
			Promise.all(slugsOf('sermon', sermonBms).map(loadSermon)),
			Promise.all(slugsOf('bio', bioBms).map(loadBio))
		]);

		books = bookBlocks.sort((a, b) => a.title.localeCompare(b.title));
		sermons = sermonBlocks.sort((a, b) => a.title.localeCompare(b.title));
		bios = bioBlocks.sort((a, b) => a.name.localeCompare(b.name));

		loading = false;
	});
</script>

{#snippet bookmarkList(list: Bookmark[], hrefFor: (bm: Bookmark) => string)}
	<ul class="clips">
		{#each list as bm (bm.id)}
			<li>
				<a href={hrefFor(bm)} class="clip clip-bookmark">
					<span class="clip-flag" aria-hidden="true"></span>
					<span class="block text-body text-text">{bm.snippet}</span>
					<span class="mt-1 block text-small text-muted">{bm.title}</span>
				</a>
			</li>
		{/each}
	</ul>
{/snippet}

{#snippet highlightItem(hl: HL, href: string, label: string)}
	<li>
		<a {href} class="clip" style="--clip-hue: var(--hl-{hl.color})">
			{#if hl.text}
				<span class="clip-quote block text-body text-text">“{hl.text}”</span>
			{/if}
			{#if hl.note}
				<span class="margin-note mt-2 block text-small">{hl.note}</span>
			{/if}
			{#if label}
				<span class="mt-1 block text-micro text-muted">{label}</span>
			{/if}
		</a>
	</li>
{/snippet}

{#if loading}
	<p class="text-small text-muted" role="status">{t('notebook.loading')}</p>
{:else if !hasContent}
	<p class="text-body text-muted">
		{t('notebook.empty')}
		<a href={localizeHref('/books')} class="ms-1 font-semibold">{t('notebook.browse')} →</a>
	</p>
{:else if noMatches}
	<p class="text-body text-muted">{t('notebook.no_matches')}</p>
{:else}
	{#each filtered as bk (bk.slug)}
		<section class="work">
			<p class="eyebrow text-muted">{t('search.typeBook')}</p>
			<h3 class="text-h3">
				<a href={localizeHref(`/books/${bk.slug}`)} class="text-text hover:text-accent">{bk.title}</a>
			</h3>
			{#if bk.author}<p class="text-small text-muted">{bk.author}</p>{/if}

			{#if bk.bookmarks.length}
				{@render bookmarkList(bk.bookmarks, (bm) => localizeHref(`/books/${bk.slug}/${bm.order}?p=${bm.p}`))}
			{/if}

			<!-- Keyed per (chapter, edition): `ch.order` alone is a duplicate key
			     the moment one chapter carries highlights in two editions. -->
			{#each bk.chapters as ch (`${ch.order}:${ch.edition}`)}
				{#if ch.highlights.length}
					{@const label = editionLabel(ch.edition)}
					<h4 class="chapter text-small font-semibold text-muted">
						{chapterLabel(ch.order, ch.title)}{#if label}<span class="ms-2 font-normal">· {label}</span>{/if}
					</h4>
					<ul class="clips">
						{#each ch.highlights as hl (hl.id)}
							{@render highlightItem(hl, editionHref(`/books/${bk.slug}/${ch.order}?p=${hl.p}`, ch.edition), '')}
						{/each}
					</ul>
				{/if}
			{/each}
		</section>
	{/each}

	{#each filteredSermons as sm (sm.slug)}
		<section class="work">
			<p class="eyebrow text-muted">{t('search.typeSermon')}</p>
			<h3 class="text-h3">
				<a href={localizeHref(`/sermons/${sm.slug}`)} class="text-text hover:text-accent">{sm.title}</a>
			</h3>
			{#if sm.author}<p class="text-small text-muted">{sm.author}</p>{/if}
			{#if sm.bookmarks.length}
				{@render bookmarkList(sm.bookmarks, (bm) => localizeHref(`/sermons/${sm.slug}?p=${bm.p}`))}
			{/if}
			<ul class="clips">
				<!-- Keyed with the edition, and labelled: two editions' highlights
				     share this one list. -->
				{#each sm.highlights as hl (`${hl.edition}:${hl.id}`)}
					{@render highlightItem(hl, editionHref(`/sermons/${sm.slug}?p=${hl.p}`, hl.edition), editionLabel(hl.edition))}
				{/each}
			</ul>
		</section>
	{/each}

	{#each filteredBios as b (b.slug)}
		<section class="work">
			<p class="eyebrow text-muted">{t('bios.eyebrow')}</p>
			<h3 class="text-h3">
				<a href={localizeHref(`/authors/${b.slug}`)} class="text-text hover:text-accent">{b.name}</a>
			</h3>
			{#if b.bookmarks.length}
				{@render bookmarkList(b.bookmarks, (bm) => localizeHref(`/authors/${b.slug}?p=${bm.p}`))}
			{/if}
			<ul class="clips">
				<!-- ?p= like the book and sermon highlights: the biography renders
				     through the same Reader, which jumps to the paragraph on arrival. -->
				{#each b.highlights as hl (`${hl.edition}:${hl.id}`)}
					{@render highlightItem(hl, editionHref(`/authors/${b.slug}?p=${hl.p}`, hl.edition), editionLabel(hl.edition))}
				{/each}
			</ul>
		</section>
	{/each}
{/if}

<style>
	.work + .work {
		margin-top: 2.25rem;
	}
	.chapter {
		margin-top: 1.25rem;
	}
	.clips {
		display: grid;
		gap: 0.75rem;
		margin-top: 0.75rem;
	}
	/* A clipping: a strip of the page pasted into the notebook, a little askew,
	   held by a piece of tape. The strip's edge takes the highlight's colour. */
	.clip {
		position: relative;
		display: block;
		padding: 0.9rem 1.1rem 0.8rem;
		background: var(--surface-2);
		border-inline-start: 3px solid var(--clip-hue, var(--border-strong));
		border-radius: 2px;
		box-shadow: var(--shadow-card);
		transform: rotate(-0.35deg);
		transition:
			transform var(--duration-fast) ease,
			box-shadow var(--duration-fast) ease;
	}
	.clips li:nth-child(even) .clip {
		transform: rotate(0.3deg);
	}
	.clip::before {
		content: '';
		position: absolute;
		top: -0.45rem;
		inset-inline-end: 1.25rem;
		width: 3.25rem;
		height: 0.9rem;
		background: color-mix(in srgb, var(--gold) 28%, transparent);
		transform: rotate(3deg);
	}
	.clip:hover {
		text-decoration: none;
		transform: rotate(0deg) translateY(-1px);
	}
	.clip-quote {
		font-family: var(--font-display);
		font-style: italic;
		line-height: 1.6;
	}
	/* A margin note — the reader's own words beside the passage. */
	.margin-note {
		color: var(--accent);
		font-family: var(--font-display);
		font-style: italic;
	}
	.margin-note::before {
		content: '✎ ';
		font-style: normal;
	}
	.clip-bookmark {
		padding-inline-end: 2.5rem;
	}
	.clip-flag {
		position: absolute;
		top: -2px;
		inset-inline-end: 0.9rem;
		width: 0.85rem;
		height: 1.6rem;
		background: var(--accent);
		clip-path: polygon(0 0, 100% 0, 100% 100%, 50% 72%, 0 100%);
	}
	.clip-bookmark::before {
		display: none;
	}
	@media (prefers-reduced-motion: reduce) {
		.clip,
		.clips li:nth-child(even) .clip {
			transform: none;
			transition: none;
		}
	}
</style>
