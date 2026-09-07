<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { getAdminAudit, type AdminAudit, type AuditChapterFinding } from '$lib/library-admin';
	import { localizeHref } from '$lib/href';
	import { locales } from '$lib/paraglide/runtime';

	const auditRes = adminResource(getAdminAudit, 'Something went wrong running the audit.');
	const audit = $derived(auditRes.data);

	// Quality checks are advisory book-qa heuristics, ordered by reader impact.
	const QUALITY: { key: keyof AdminAudit['quality']; label: string; desc: string }[] = [
		{ key: 'mid_sentence_splits', label: 'Mid-sentence splits', desc: "Chapter body doesn't end in sentence punctuation" },
		{ key: 'generic_titles', label: 'Generic / missing titles', desc: 'Empty title, or a bare “Chapter N”' },
		{ key: 'missing_dropcap', label: 'Missing drop cap', desc: 'Body starts lower-case or mid-word' },
		{ key: 'fragmented', label: 'Fragmented paragraphs', desc: 'Very low words-per-paragraph' },
		{ key: 'duplicate_titles', label: 'Duplicate titles in a book', desc: 'Same title on multiple chapters' },
		{ key: 'tiny_chapters', label: 'Tiny chapters', desc: 'Under 150 words' },
		{ key: 'giant_chapters', label: 'Giant chapters', desc: 'Over 8,000 words — a split may be missed' }
	];

	const integrityTotal = $derived(
		audit ? Object.values(audit.integrity).reduce((n, c) => n + c.total, 0) : 0
	);
	const qualityTotal = $derived(
		audit ? Object.values(audit.quality).reduce((n, c) => n + c.total, 0) : 0
	);
	const totalFindings = $derived(integrityTotal + qualityTotal);

	// A finding is against one EDITION, and the reader route takes its content
	// language from the URL's locale prefix — so a link without one opens
	// whichever edition the admin's own locale resolves to, which for a Swahili
	// finding is usually the English text. Every link here is localized to the
	// language the finding is actually about.
	// `en-modern` is a content language with no locale of its own, and a language
	// could be added to the registry before its interface exists — so an unrouted
	// code falls back to an unprefixed link rather than inventing a 404. The row
	// still names the edition either way.
	// Books, sermons and plans are per-language ROWS sharing a slug, so a finding
	// is identified by the triple. Keying on book+order alone crashed the page
	// with `each_key_duplicate` the moment one chapter was flagged in two
	// editions — which for `the-key-in-my-hand` chapter 2 meant six.
	const findingKey = (f: AuditChapterFinding) => `${f.book}:${f.language}:${f.order}`;

	const editionHref = (path: string, language: string) =>
		(locales as readonly string[]).includes(language)
			? localizeHref(path, { locale: language as (typeof locales)[number] })
			: localizeHref(path);

	function evidence(f: AuditChapterFinding): string {
		if (f.avg_words != null) return `${f.avg_words} words/¶ · ${f.paragraphs} ¶`;
		if (f.word_count != null) return `${f.word_count} words`;
		if (f.starts) return `“${f.starts}…”`;
		if (f.ends) return `…${f.ends}`;
		return '';
	}

	// One bad book can flag many chapters; collapse them under a per-edition
	// heading so a check is one expandable line per book, not one per chapter.
	type BookGroup = { book: string; language: string; items: AuditChapterFinding[] };
	function byBook(items: AuditChapterFinding[]): BookGroup[] {
		const groups = new Map<string, BookGroup>();
		for (const f of items) {
			const k = `${f.book}:${f.language}`;
			let g = groups.get(k);
			if (!g) {
				g = { book: f.book, language: f.language, items: [] };
				groups.set(k, g);
			}
			g.items.push(f);
		}
		return [...groups.values()];
	}
</script>

<svelte:head><title>Admin · Audit — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
	<header class="mb-6 flex flex-wrap items-end justify-between gap-3">
		<div>
			<p class="eyebrow mb-2 text-accent">Admin</p>
			<h1 class="text-display">Content audit</h1>
			<p class="mt-2 text-body text-muted">Quality and integrity checks across the library. Heuristics are advisory — read the chapter before fixing.</p>
		</div>
		{#if audit}
			<button class="btn btn-ghost" onclick={auditRes.load} disabled={auditRes.loading}
				>{auditRes.loading ? 'Re-running…' : 'Re-run'}</button
			>
		{/if}
	</header>

	<AdminGate resource={auditRes} errorTitle="Couldn't run the audit" loadingText="Running audit…">
		{#snippet children(a)}
			<p class="mb-8 text-body {totalFindings ? 'text-warning' : 'text-muted'}">
				{#if totalFindings}<strong>{integrityTotal}</strong> integrity {integrityTotal === 1 ? 'issue' : 'issues'} · <strong>{qualityTotal}</strong> quality {qualityTotal === 1 ? 'flag' : 'flags'}{:else}No findings — the library looks clean. 🎉{/if}
			</p>

			<!-- One chapter row, used everywhere findings are chapter-shaped. When a
			     book is grouped, `bare` drops the repeated slug and shows only /order. -->
			{#snippet chapterItem(f: AuditChapterFinding, bare = false)}
				<li class="flex items-baseline justify-between gap-3 py-1.5">
					<a
						href={editionHref(`/books/${f.book}/${f.order}`, f.language)}
						class="min-w-0 truncate text-body text-text hover:text-accent"
					>
						{#if bare}<span class="text-muted">/{f.order}</span>{:else}<span class="text-muted">{f.book}/{f.order}</span> <span class="text-micro text-muted">{f.language}</span>{/if}
						— {f.title || '(untitled)'}
					</a>
					{#if evidence(f)}<span class="shrink-0 text-small text-muted">{evidence(f)}</span>{/if}
				</li>
			{/snippet}

			<!-- The server caps every list at AUDIT_LIMIT but still reports the true
			     total, so any list can be truncated — say so, or an admin reads 100
			     rows as "all of them". -->
			{#snippet moreLine(shown: number, total: number)}
				{#if shown < total}<p class="mt-1 text-small text-muted">…and {total - shown} more</p>{/if}
			{/snippet}

			<!-- Chapter findings grouped by edition: a lone hit renders flat, a book
			     with several collapses under its own sub-heading. -->
			{#snippet chapterList(items: AuditChapterFinding[], total: number = items.length)}
				<ul class="mt-1">
					{#each byBook(items) as g (g.book + ':' + g.language)}
						{#if g.items.length === 1}
							{@render chapterItem(g.items[0])}
						{:else}
							<li class="py-1.5">
								<a href={editionHref(`/books/${g.book}`, g.language)} class="text-body text-text hover:text-accent">
									<span class="text-muted">{g.book}</span> <span class="text-micro text-muted">{g.language}</span>
								</a>
								<span class="text-small text-muted">· {g.items.length} chapters</span>
								<ul class="ml-4 border-l border-border pl-3">
									{#each g.items as f (findingKey(f))}
										{@render chapterItem(f, true)}
									{/each}
								</ul>
							</li>
						{/if}
					{/each}
				</ul>
				{@render moreLine(items.length, total)}
			{/snippet}

			<!-- A collapsible check. Header is always visible (label + count); the
			     body renders only when opened. `open` lets integrity bugs default
			     to expanded while advisory quality checks stay folded. -->
			{#snippet check(label: string, desc: string, total: number, open: boolean, body: import('svelte').Snippet)}
				<details class="group border-b border-border py-2" {open}>
					<summary class="flex cursor-pointer list-none items-baseline justify-between gap-3">
						<span class="text-body font-semibold text-text">
							<span class="mr-1 inline-block text-muted transition-transform group-open:rotate-90">›</span>{label}
						</span>
						<span class="shrink-0 text-small {total ? 'text-warning' : 'text-muted'}">{total || 'clear'}</span>
					</summary>
					{#if desc}<p class="ml-4 mt-1 text-small text-muted">{desc}</p>{/if}
					{#if total}<div class="ml-4">{@render body()}</div>{/if}
				</details>
			{/snippet}

			<div class="grid gap-10 md:grid-cols-2">
				<!-- Integrity: real data defects. Loud, first, open when non-empty. -->
				<section>
					<h2 class="text-h3 mb-1 flex items-baseline gap-2">
						Data integrity
						{#if integrityTotal}<span class="text-small font-normal text-warning">fix these</span>{/if}
					</h2>
					<p class="mb-3 text-small text-muted">Structural defects readers hit directly.</p>

					{#snippet planDays()}
						<ul class="mt-1">
							{#each a.integrity.broken_plan_days.items as d (d.plan + ':' + d.language + ':' + d.day)}
								<li class="py-1.5 text-body">
									<a href={editionHref(`/plans/${d.plan}`, d.language)} class="text-text hover:text-accent">{d.plan}</a>
									<span class="text-small text-muted">day {d.day} → {d.book}/{d.order} ({d.language})</span>
								</li>
							{/each}
						</ul>
						{@render moreLine(a.integrity.broken_plan_days.items.length, a.integrity.broken_plan_days.total)}
					{/snippet}
					{@render check('Broken plan days', 'A plan day points at a missing chapter', a.integrity.broken_plan_days.total, a.integrity.broken_plan_days.total > 0, planDays)}

					{#snippet emptyBooks()}
						<ul class="mt-1">
							{#each a.integrity.empty_books.items as b (b.book + b.language)}
								<li class="py-1.5 text-body"><a href={editionHref(`/books/${b.book}`, b.language)} class="text-text hover:text-accent">{b.title}</a> <span class="text-small text-muted">{b.author} · {b.language}</span></li>
							{/each}
						</ul>
						{@render moreLine(a.integrity.empty_books.items.length, a.integrity.empty_books.total)}
					{/snippet}
					{@render check('Books with no chapters', '', a.integrity.empty_books.total, a.integrity.empty_books.total > 0, emptyBooks)}

					{#snippet emptyChapters()}
						{@render chapterList(a.integrity.empty_chapters.items, a.integrity.empty_chapters.total)}
					{/snippet}
					{@render check('Empty chapters', 'No body text', a.integrity.empty_chapters.total, a.integrity.empty_chapters.total > 0, emptyChapters)}

					{#snippet orderGaps()}
						<ul class="mt-1">
							{#each a.integrity.order_gaps.items as g (g.book + ':' + g.language)}
								<li class="py-1.5 text-body"><a href={editionHref(`/books/${g.book}`, g.language)} class="text-text hover:text-accent">{g.book}</a> <span class="text-small text-muted">{g.language} · missing {g.missing.join(', ')} of {g.count}</span></li>
							{/each}
						</ul>
						{@render moreLine(a.integrity.order_gaps.items.length, a.integrity.order_gaps.total)}
					{/snippet}
					{@render check('Chapter-order gaps', 'Missing chapter numbers', a.integrity.order_gaps.total, a.integrity.order_gaps.total > 0, orderGaps)}
				</section>

				<!-- Quality: advisory heuristics. Folded by default; expand to inspect. -->
				<section>
					<h2 class="text-h3 mb-1">Content quality</h2>
					<p class="mb-3 text-small text-muted">Advisory heuristics — expect false positives.</p>

					{#each QUALITY as q (q.key)}
						{@const c = a.quality[q.key]}
						{#if q.key === 'duplicate_titles'}
							{#snippet dupTitles()}
								<ul class="mt-1">
									{#each a.quality.duplicate_titles.items as f (f.book + ':' + f.language + ':' + f.title)}
										<li class="flex items-baseline justify-between gap-3 py-1.5">
											<a href={editionHref(`/books/${f.book}`, f.language)} class="min-w-0 truncate text-body text-text hover:text-accent"><span class="text-muted">{f.book}</span> <span class="text-micro text-muted">{f.language}</span> — “{f.title}”</a>
											<span class="shrink-0 text-small text-muted">×{f.count}</span>
										</li>
									{/each}
								</ul>
								{@render moreLine(a.quality.duplicate_titles.items.length, a.quality.duplicate_titles.total)}
							{/snippet}
							{@render check(q.label, q.desc, c.total, false, dupTitles)}
						{:else}
							{@const items = c.items as AuditChapterFinding[]}
							{#snippet chapters()}
								{@render chapterList(items, c.total)}
							{/snippet}
							{@render check(q.label, q.desc, c.total, false, chapters)}
						{/if}
					{/each}
				</section>
			</div>
		{/snippet}
	</AdminGate>
</div>
