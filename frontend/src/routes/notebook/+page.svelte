<script lang="ts">
	import { onMount } from 'svelte';
	import { getBook, getChapter, getSermon, getAuthor, type BookDetail } from '$lib/library';
	import { getLang } from '$lib/lang.svelte';
	import { bookmarks } from '$lib/bookmarks.svelte';
	import { marks } from '$lib/marks.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { HIGHLIGHT_COLORS, DEFAULT_HIGHLIGHT, type Bookmark, type Mark } from '$lib/reading-schema';
	import { createLimiter, NOTEBOOK_CONCURRENCY } from '$lib/limiter';
	import EmptyState from '$lib/components/EmptyState.svelte';

	const t = i18n.t;

	type HL = { id: string; p: number; text: string; note?: string; color: string };
	type ChapterBlock = { order: number; title: string; highlights: HL[] };
	type BookBlock = {
		slug: string;
		title: string;
		author: string;
		bookmarks: Bookmark[];
		chapters: ChapterBlock[];
	};

	type SermonBlock = { slug: string; title: string; author: string; highlights: HL[] };
	// A biography block: the slug is the author's; the "title" is their name.
	type BioBlock = { slug: string; name: string; highlights: HL[] };

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
				return { ...sm, highlights };
			})
			.filter((sm) => sm.highlights.length);
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
				return { ...b, highlights };
			})
			.filter((b) => b.highlights.length);
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
	function groupMarks(paras: string[], ms: Mark[]): HL[] {
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
				color: segs.find((s) => s.color)?.color ?? DEFAULT_HIGHLIGHT
			};
		});
	}

	// Every fetch below is wrapped in its own try/catch and every failure is the
	// same one: the reader is offline. A highlight still links through to where
	// it was made, it just can't show its own text — so one unreachable chapter
	// degrades that card, never the page. That per-item tolerance is also what
	// makes the concurrency below safe: nothing here rejects.
	onMount(async () => {
		const lang = getLang();
		const bms = bookmarks.all();
		const allMarks = marks.all();
		type MarkEntry = (typeof allMarks)[number];
		const mks = allMarks.filter((m) => m.kind === 'book');
		const slugs = [...new Set([...bms.map((b) => b.slug), ...mks.map((m) => m.slug)])];

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

		const loadBook = async (slug: string): Promise<BookBlock> => {
			let book: BookDetail | null = null;
			try {
				book = await gate(() => getBook(slug, lang));
			} catch {
				/* offline — fall back to slug/order labels */
			}
			const titleFor = (order: number) =>
				book?.chapters.find((c) => c.order === order)?.title || `${order}`;

			const chapters = await Promise.all(
				mks
					.filter((m) => m.slug === slug)
					.sort((a, b) => a.order - b.order)
					.map(async ({ order, marks: ms }): Promise<ChapterBlock> => {
						let paras: string[] = [];
						try {
							const chapter = await gate(() => getChapter(slug, order, lang));
							paras = paragraphs(chapter.body_html);
						} catch {
							/* offline — the highlight still links through, just without its text */
						}
						return { order, title: titleFor(order), highlights: groupMarks(paras, ms) };
					})
			);

			return {
				slug,
				title: book?.title || slug,
				author: book?.author.name || '',
				bookmarks: bms
					.filter((b) => b.slug === slug)
					.sort((a, b) => a.order - b.order || a.p - b.p),
				chapters
			};
		};

		// Sermon highlights (device-local, keyed by sermon slug — no chapters).
		const loadSermon = async ({ slug, marks: ms }: MarkEntry): Promise<SermonBlock> => {
			let paras: string[] = [];
			let title = slug;
			let author = '';
			try {
				const sermon = await gate(() => getSermon(slug, lang));
				paras = paragraphs(sermon.body_html);
				title = sermon.title;
				author = sermon.author_name;
			} catch {
				/* offline — the highlight still links through, just without its text */
			}
			return { slug, title, author, highlights: groupMarks(paras, ms) };
		};

		// Biography highlights (kind 'bio'; the slug names the author).
		const loadBio = async ({ slug, marks: ms }: MarkEntry): Promise<BioBlock> => {
			let paras: string[] = [];
			let name = slug;
			try {
				const a = await gate(() => getAuthor(slug, lang));
				paras = paragraphs(a.bio_html);
				name = a.name;
			} catch {
				/* offline — the highlight still links through, just without its text */
			}
			return { slug, name, highlights: groupMarks(paras, ms) };
		};

		const [bookBlocks, sermonBlocks, bioBlocks] = await Promise.all([
			Promise.all(slugs.map(loadBook)),
			Promise.all(allMarks.filter((m) => m.kind === 'sermon').map(loadSermon)),
			Promise.all(allMarks.filter((m) => m.kind === 'bio').map(loadBio))
		]);

		books = bookBlocks.sort((a, b) => a.title.localeCompare(b.title));
		sermons = sermonBlocks.sort((a, b) => a.title.localeCompare(b.title));
		bios = bioBlocks.sort((a, b) => a.name.localeCompare(b.name));

		loading = false;
	});
</script>

<svelte:head><title>{t('notebook.title')} — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-2xl px-5 py-10">
	<header class="mb-8">
		<p class="eyebrow mb-2 text-accent">Ochorus</p>
		<h1 class="text-h1">{t('notebook.title')}</h1>
		<p class="mt-2 text-body text-muted">{t('notebook.subtitle')}</p>
	</header>

	{#if loading}
		<p class="text-body text-muted">…</p>
	{:else if isEmpty}
		<EmptyState message={t('notebook.empty')} />
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

				{#each bk.chapters as ch (ch.order)}
					{#if ch.highlights.length}
						<h3 class="mb-2 mt-5 text-small font-semibold text-text">{ch.order}. {ch.title}</h3>
						<ul class="space-y-2">
							{#each ch.highlights as hl (hl.id)}
								<li>
									<a
										href={localizeHref(`/books/${bk.slug}/${ch.order}?p=${hl.p}`)}
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
				<ul class="space-y-2">
					{#each sm.highlights as hl (hl.id)}
						<li>
							<a
								href={localizeHref(`/sermons/${sm.slug}?p=${hl.p}`)}
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
				<ul class="mt-3 space-y-2">
					{#each b.highlights as hl (hl.id)}
						<li>
							<!-- ?p= like the book and sermon highlights above: the biography
							     renders through the same Reader, which already jumps to the
							     paragraph on arrival. Without it a biography highlight was the
							     one kind that dropped the reader at the top of the page. -->
							<a
								href={localizeHref(`/authors/${b.slug}?p=${hl.p}`)}
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
			</section>
		{/each}
	{/if}
</div>
