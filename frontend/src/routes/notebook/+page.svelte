<script lang="ts">
	import { onMount } from 'svelte';
	import { getBook, getChapter, type BookDetail } from '$lib/library';
	import { getLang } from '$lib/lang.svelte';
	import { bookmarks } from '$lib/bookmarks.svelte';
	import { marks } from '$lib/marks.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import type { Bookmark, Mark } from '$lib/reading-schema';

	const t = i18n.t;

	type HL = { id: string; p: number; text: string; note?: string };
	type ChapterBlock = { order: number; title: string; highlights: HL[] };
	type BookBlock = {
		slug: string;
		title: string;
		author: string;
		bookmarks: Bookmark[];
		chapters: ChapterBlock[];
	};

	let loading = $state(true);
	let books = $state<BookBlock[]>([]);
	const isEmpty = $derived(!loading && books.length === 0);

	// Live search across every book, chapter title, highlight, note and bookmark.
	let query = $state('');
	const q = $derived(query.trim().toLowerCase());
	const filtered = $derived.by(() => {
		if (!q) return books;
		const hit = (s: string) => s.toLowerCase().includes(q);
		return books
			.map((bk) => {
				const bookHit = hit(bk.title) || hit(bk.author);
				const bookmarks = bookHit
					? bk.bookmarks
					: bk.bookmarks.filter((b) => hit(b.snippet) || hit(b.title));
				const chapters = bk.chapters
					.map((ch) => ({
						...ch,
						highlights: bookHit
							? ch.highlights
							: ch.highlights.filter((h) => hit(h.text) || hit(h.note ?? '') || hit(ch.title))
					}))
					.filter((ch) => ch.highlights.length);
				return { ...bk, bookmarks, chapters };
			})
			.filter((bk) => bk.bookmarks.length || bk.chapters.length);
	});
	const noMatches = $derived(!loading && books.length > 0 && q.length > 0 && filtered.length === 0);

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
				note: segs.find((s) => s.note)?.note
			};
		});
	}

	onMount(async () => {
		const lang = getLang();
		const bms = bookmarks.all();
		const mks = marks.all();
		const slugs = [...new Set([...bms.map((b) => b.slug), ...mks.map((m) => m.slug)])];

		const out: BookBlock[] = [];
		for (const slug of slugs) {
			let book: BookDetail | null = null;
			try {
				book = await getBook(slug, lang);
			} catch {
				/* offline — fall back to slug/order labels */
			}
			const titleFor = (order: number) =>
				book?.chapters.find((c) => c.order === order)?.title || `${order}`;

			const chapters: ChapterBlock[] = [];
			for (const { order, marks: ms } of mks
				.filter((m) => m.slug === slug)
				.sort((a, b) => a.order - b.order)) {
				let paras: string[] = [];
				try {
					paras = paragraphs((await getChapter(slug, order, lang)).body_html);
				} catch {
					/* offline — the highlight still links through, just without its text */
				}
				chapters.push({ order, title: titleFor(order), highlights: groupMarks(paras, ms) });
			}

			out.push({
				slug,
				title: book?.title || slug,
				author: book?.author.name || '',
				bookmarks: bms
					.filter((b) => b.slug === slug)
					.sort((a, b) => a.order - b.order || a.p - b.p),
				chapters
			});
		}
		books = out.sort((a, b) => a.title.localeCompare(b.title));
		loading = false;
	});
</script>

<svelte:head><title>{t('notebook.title')} — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-2xl px-5 py-10">
	<header class="mb-8">
		<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">Ochorus</p>
		<h1 class="text-display">{t('notebook.title')}</h1>
		<p class="mt-2 text-body text-muted">{t('notebook.subtitle')}</p>
	</header>

	{#if loading}
		<p class="text-body text-muted">…</p>
	{:else if isEmpty}
		<div class="rounded-2xl border border-border bg-surface p-8 text-center">
			<p class="text-body text-muted">{t('notebook.empty')}</p>
		</div>
	{:else}
		<div class="mb-6">
			<input
				type="search"
				bind:value={query}
				placeholder={t('notebook.search')}
				aria-label={t('notebook.search')}
				class="w-full rounded-xl border border-border bg-surface px-4 py-2.5 text-body text-text placeholder:text-muted focus:border-accent focus:outline-none"
			/>
		</div>

		{#if noMatches}
			<div class="rounded-2xl border border-border bg-surface p-8 text-center">
				<p class="text-body text-muted">{t('notebook.no_matches')}</p>
			</div>
		{/if}

		{#each filtered as bk (bk.slug)}
			<section class="mb-10">
				<h2 class="text-h2">
					<a href={localizeHref(`/books/${bk.slug}`)} class="hover:text-accent">{bk.title}</a>
				</h2>
				{#if bk.author}<p class="mb-3 text-small text-muted">{bk.author}</p>{/if}

				{#if bk.bookmarks.length}
					<h3 class="mb-2 mt-4 text-small font-semibold uppercase tracking-wide text-muted">
						🔖 {t('reader.bookmarks')}
					</h3>
					<ul class="space-y-2">
						{#each bk.bookmarks as bm (bm.id)}
							<li>
								<a
									href={localizeHref(`/books/${bk.slug}/${bm.order}?p=${bm.p}`)}
									class="block rounded-lg border border-border bg-surface px-4 py-2.5 hover:border-accent hover:no-underline"
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
										class="block rounded-lg border-l-2 border-gold bg-surface px-4 py-2.5 hover:no-underline"
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
	{/if}
</div>
