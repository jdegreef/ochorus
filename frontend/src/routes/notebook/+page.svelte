<script lang="ts">
	import { onMount } from 'svelte';
	import { getBook, getChapter, getSermon, getAuthor, type BookDetail } from '$lib/library-public';
	import { getLang, lang as langStore, localeName } from '$lib/lang.svelte';
	import { bookmarks, byPosition } from '$lib/bookmarks.svelte';
	import { marks } from '$lib/marks.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { chapterLabel } from '$lib/reading';
	import {
		HIGHLIGHT_COLORS,
		DEFAULT_HIGHLIGHT,
		MODERN_EDITION,
		baseEdition,
		type Bookmark,
		type Mark,
		type WorkKind
	} from '$lib/reading-schema';
	import { createLimiter, NOTEBOOK_CONCURRENCY } from '$lib/limiter';
	import EmptyState from '$lib/components/EmptyState.svelte';

	const t = i18n.t;

	// `edition` rides along so a highlight can be linked back into the text it
	// was made on, and named when that is not the edition the page is in.
	/** The locale union `localizeHref` accepts; `isAvailable` is its runtime check. */
	type UiLocale = NonNullable<Parameters<typeof localizeHref>[1]>['locale'];

	type HL = {
		id: string;
		p: number;
		text: string;
		note?: string;
		color: string;
		edition: string;
	};
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

	let loading = $state(true);
	let books = $state<BookBlock[]>([]);
	let sermons = $state<SermonBlock[]>([]);
	let bios = $state<BioBlock[]>([]);
	const isEmpty = $derived(
		!loading && books.length === 0 && sermons.length === 0 && bios.length === 0
	);

	// Live search across every book, chapter title, highlight, note and bookmark,
	// plus an optional filter to one highlight colour.
	let query = $state('');
	let colorFilter = $state(''); // '' = all colours
	const q = $derived(query.trim().toLowerCase());
	const active = $derived(q.length > 0 || colorFilter !== '');
	const filtered = $derived.by(() => {
		if (!active) return books;
		const hit = (s: string) => s.toLowerCase().includes(q);
		return books
			.map((bk) => {
				const bookHit = !q || hit(bk.title) || hit(bk.author);
				// Bookmarks aren't coloured, so a colour filter hides them.
				const bookmarks = colorFilter
					? []
					: bookHit
						? bk.bookmarks
						: bk.bookmarks.filter((b) => hit(b.snippet) || hit(b.title));
				const chapters = bk.chapters
					.map((ch) => ({
						...ch,
						highlights: ch.highlights.filter(
							(h) =>
								(!colorFilter || h.color === colorFilter) &&
								(bookHit || hit(h.text) || hit(h.note ?? '') || hit(ch.title))
						)
					}))
					.filter((ch) => ch.highlights.length);
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
		// Bookmarks aren't coloured, so a colour filter hides them.
		colorFilter ? [] : workHit ? list : list.filter((b) => hit(b.snippet) || hit(b.title));

	const filteredSermons = $derived.by(() => {
		if (!active) return sermons;
		const hit = (s: string) => s.toLowerCase().includes(q);
		return sermons
			.map((sm) => {
				const sermonHit = !q || hit(sm.title) || hit(sm.author);
				const highlights = sm.highlights.filter(
					(h) =>
						(!colorFilter || h.color === colorFilter) &&
						(sermonHit || hit(h.text) || hit(h.note ?? ''))
				);
				return { ...sm, bookmarks: matchingBookmarks(sm.bookmarks, sermonHit, hit), highlights };
			})
			.filter((sm) => sm.bookmarks.length || sm.highlights.length);
	});
	const filteredBios = $derived.by(() => {
		if (!active) return bios;
		const hit = (s: string) => s.toLowerCase().includes(q);
		return bios
			.map((b) => {
				const bioHit = !q || hit(b.name);
				const highlights = b.highlights.filter(
					(h) =>
						(!colorFilter || h.color === colorFilter) &&
						(bioHit || hit(h.text) || hit(h.note ?? ''))
				);
				return { ...b, bookmarks: matchingBookmarks(b.bookmarks, bioHit, hit), highlights };
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

	// Split a chapter's cleaned HTML into its top-level blocks' text — the same
	// blocks the reader indexes marks against (p = block, s/e = chars in it).
	function paragraphs(bodyHtml: string): string[] {
		const div = document.createElement('div');
		div.innerHTML = bodyHtml;
		return [...div.children].map((el) => el.textContent ?? '');
	}
	function segText(paras: string[], m: Mark): string {
		const tx = paras[m.p] ?? '';
		return tx.slice(m.s, m.e === -1 ? undefined : m.e).trim();
	}
	// One selection can be several segments (multi-paragraph) sharing an id; join
	// them and carry the note (which lives on the first segment).
	function groupMarks(paras: string[], ms: Mark[], edition: string): HL[] {
		const byId = new Map<string, Mark[]>();
		for (const m of ms) {
			const arr = byId.get(m.id) ?? [];
			arr.push(m);
			byId.set(m.id, arr);
		}
		return [...byId.values()].map((segs) => {
			segs.sort((a, b) => a.p - b.p || a.s - b.s);
			return {
				id: segs[0].id,
				p: segs[0].p,
				text: segs.map((s) => segText(paras, s)).filter(Boolean).join(' … '),
				note: segs.find((s) => s.note)?.note,
				color: segs.find((s) => s.color)?.color ?? DEFAULT_HIGHLIGHT,
				edition
			};
		});
	}

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

	/**
	 * A link into the EDITION the highlight was made in, not the page's.
	 *
	 * Without this the notebook sends the reader to a text their highlight is
	 * not in — the modern edition needs its query flag, and a highlight made in
	 * another language belongs to that language's pages. An edition whose
	 * language the UI does not carry falls back to the current locale rather
	 * than building a URL for a locale that does not route.
	 */
	function editionHref(path: string, edition: string): string {
		const modern = edition === MODERN_EDITION;
		const withEdition = modern ? `${path}${path.includes('?') ? '&' : '?'}edition=modern` : path;
		const locale = modern ? 'en' : baseEdition(edition);
		// `isAvailable` IS the check the type wants; a content language can be
		// added in the admin without a frontend deploy, so the set of editions is
		// wider than the compiled locales and this cannot be proven statically.
		return langStore.isAvailable(locale)
			? localizeHref(withEdition, { locale: locale as UiLocale })
			: localizeHref(withEdition);
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

<svelte:head><title>{t('notebook.title')} — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

{#snippet browseLibrary()}
	<a class="btn btn-primary inline-block" href={localizeHref('/books')}>{t('notebook.browse')}</a>
{/snippet}

<div class="page-col px-5 py-10">
	<header class="mb-8">
		<p class="eyebrow mb-2 text-accent">Ochorus</p>
		<h1 class="text-h1">{t('notebook.title')}</h1>
		<p class="mt-2 text-body text-muted">{t('notebook.subtitle')}</p>
	</header>

	{#if loading}
		<p class="text-body text-muted">…</p>
	{:else if isEmpty}
		<!-- The empty Notebook is the one place a reader has nothing to act on, so
		     it is the one place that most needs a way back to the books. -->
		<EmptyState message={t('notebook.empty')} action={browseLibrary} />
	{:else}
		<div class="mb-6 flex flex-wrap items-center gap-3">
			<input
				type="search"
				bind:value={query}
				placeholder={t('notebook.search')}
				aria-label={t('notebook.search')}
				class="field grow"
			/>
			<div class="flex items-center gap-2" role="group" aria-label={t('notebook.filterColor')}>
				<button
					class="rounded-full border px-2.5 py-1 text-small"
					class:border-accent={colorFilter === ''}
					class:text-accent={colorFilter === ''}
					class:border-border={colorFilter !== ''}
					class:text-muted={colorFilter !== ''}
					onclick={() => (colorFilter = '')}
					aria-pressed={colorFilter === ''}
				>
					{t('notebook.allColors')}
				</button>
				{#each HIGHLIGHT_COLORS as color (color)}
					<button
						class="hl-swatch"
						data-color={color}
						class:active={colorFilter === color}
						onclick={() => (colorFilter = colorFilter === color ? '' : color)}
						aria-pressed={colorFilter === color}
						aria-label="{t('notebook.filterColor')}: {t(`reader.hl_${color}`)}"
						title={t(`reader.hl_${color}`)}
					></button>
				{/each}
			</div>
		</div>

		{#if noMatches}
			<EmptyState message={t('notebook.no_matches')} />
		{/if}

		{#each filtered as bk (bk.slug)}
			<section class="mb-10">
				<h2 class="text-h2">
					<a href={localizeHref(`/books/${bk.slug}`)} class="hover:text-accent">{bk.title}</a>
				</h2>
				{#if bk.author}<p class="mb-3 text-small text-muted">{bk.author}</p>{/if}

				{#if bk.bookmarks.length}
					<h3 class="section-label mt-4">
						🔖 {t('reader.bookmarks')}
					</h3>
					<ul class="space-y-2">
						{#each bk.bookmarks as bm (bm.id)}
							<li>
								<a
									href={localizeHref(`/books/${bk.slug}/${bm.order}?p=${bm.p}`)}
									class="block rounded-sm border border-border bg-surface px-4 py-2.5 hover:border-accent hover:no-underline"
								>
									<span class="block text-body text-text">{bm.snippet}</span>
									<span class="block text-small text-muted">{bm.title}</span>
								</a>
							</li>
						{/each}
					</ul>
				{/if}

				<!-- Keyed per (chapter, edition): `ch.order` alone is a duplicate key
				     the moment one chapter carries highlights in two editions. -->
				{#each bk.chapters as ch (`${ch.order}:${ch.edition}`)}
					{#if ch.highlights.length}
						{@const label = editionLabel(ch.edition)}
						<h3 class="mb-2 mt-5 text-small font-semibold text-text">
							{chapterLabel(ch.order, ch.title)}{#if label}<span class="ms-2 font-normal text-muted"
									>· {label}</span
								>{/if}
						</h3>
						<ul class="space-y-2">
							{#each ch.highlights as hl (hl.id)}
								<li>
									<a
										href={editionHref(`/books/${bk.slug}/${ch.order}?p=${hl.p}`, ch.edition)}
										class="block rounded-sm border-s-2 bg-surface px-4 py-2.5 hover:no-underline"
										style="border-inline-start-color: var(--hl-{hl.color})"
									>
										{#if hl.text}
											<span class="block text-body italic text-text">“{hl.text}”</span>
										{/if}
										{#if hl.note}
											<span class="mt-1 block text-small text-muted">📝 {hl.note}</span>
										{/if}
									</a>
								</li>
							{/each}
						</ul>
					{/if}
				{/each}
			</section>
		{/each}

		{#each filteredSermons as sm (sm.slug)}
			<section class="mb-10">
				<p class="eyebrow mb-1 text-accent">
					{t('search.typeSermon')}
				</p>
				<h2 class="text-h2">
					<a href={localizeHref(`/sermons/${sm.slug}`)} class="hover:text-accent">{sm.title}</a>
				</h2>
				{#if sm.author}<p class="mb-3 text-small text-muted">{sm.author}</p>{/if}

				{#if sm.bookmarks.length}
					<h3 class="section-label mt-4">
						🔖 {t('reader.bookmarks')}
					</h3>
					<ul class="mb-4 space-y-2">
						{#each sm.bookmarks as bm (bm.id)}
							<li>
								<a
									href={localizeHref(`/sermons/${sm.slug}?p=${bm.p}`)}
									class="block rounded-sm border border-border bg-surface px-4 py-2.5 hover:border-accent hover:no-underline"
								>
									<span class="block text-body text-text">{bm.snippet}</span>
									<span class="block text-small text-muted">{bm.title}</span>
								</a>
							</li>
						{/each}
					</ul>
				{/if}

				<ul class="space-y-2">
					<!-- Keyed with the edition, and labelled below: two editions'
					     highlights share this one list. -->
					{#each sm.highlights as hl (`${hl.edition}:${hl.id}`)}
						{@const label = editionLabel(hl.edition)}
						<li>
							<a
								href={editionHref(`/sermons/${sm.slug}?p=${hl.p}`, hl.edition)}
								class="block rounded-sm border-s-2 bg-surface px-4 py-2.5 hover:no-underline"
								style="border-inline-start-color: var(--hl-{hl.color})"
							>
								{#if hl.text}
									<span class="block text-body italic text-text">“{hl.text}”</span>
								{/if}
								{#if hl.note}
									<span class="mt-1 block text-small text-muted">📝 {hl.note}</span>
								{/if}
								{#if label}
									<span class="mt-1 block text-micro text-muted">{label}</span>
								{/if}
							</a>
						</li>
					{/each}
				</ul>
			</section>
		{/each}

		{#each filteredBios as b (b.slug)}
			<section class="mb-10">
				<p class="eyebrow mb-1 text-accent">
					{t('bios.eyebrow')}
				</p>
				<h2 class="text-h2">
					<a href={localizeHref(`/authors/${b.slug}`)} class="hover:text-accent">{b.name}</a>
				</h2>

				{#if b.bookmarks.length}
					<h3 class="section-label mt-4">
						🔖 {t('reader.bookmarks')}
					</h3>
					<ul class="mb-4 space-y-2">
						{#each b.bookmarks as bm (bm.id)}
							<li>
								<a
									href={localizeHref(`/authors/${b.slug}?p=${bm.p}`)}
									class="block rounded-sm border border-border bg-surface px-4 py-2.5 hover:border-accent hover:no-underline"
								>
									<span class="block text-body text-text">{bm.snippet}</span>
									<span class="block text-small text-muted">{bm.title}</span>
								</a>
							</li>
						{/each}
					</ul>
				{/if}

				<ul class="mt-3 space-y-2">
					<!-- Keyed with the edition, and labelled below: two editions'
					     highlights share this one list. -->
					{#each b.highlights as hl (`${hl.edition}:${hl.id}`)}
						{@const label = editionLabel(hl.edition)}
						<li>
							<!-- ?p= like the book and sermon highlights above: the biography
							     renders through the same Reader, which already jumps to the
							     paragraph on arrival. Without it a biography highlight was the
							     one kind that dropped the reader at the top of the page. -->
							<a
								href={editionHref(`/authors/${b.slug}?p=${hl.p}`, hl.edition)}
								class="block rounded-sm border-s-2 bg-surface px-4 py-2.5 hover:no-underline"
								style="border-inline-start-color: var(--hl-{hl.color})"
							>
								{#if hl.text}
									<span class="block text-body italic text-text">“{hl.text}”</span>
								{/if}
								{#if hl.note}
									<span class="mt-1 block text-small text-muted">📝 {hl.note}</span>
								{/if}
								{#if label}
									<span class="mt-1 block text-micro text-muted">{label}</span>
								{/if}
							</a>
						</li>
					{/each}
				</ul>
			</section>
		{/each}
	{/if}
</div>
