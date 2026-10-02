<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import ChapterLengthChart from '$lib/components/ChapterLengthChart.svelte';
	import {
		getAdminAudit,
		dismissAuditFinding,
		undoAuditDismissal,
		type AdminAudit,
		type AuditChapterFinding,
		type AuditDismissTarget,
		type Capped
	} from '$lib/library-admin';
	import { localizeHref } from '$lib/href';
	import { relativeTime } from '$lib/relativeTime';
	import { locales } from '$lib/paraglide/runtime';

	// '' = all editions. Filtering is server-side (accurate per-language totals
	// even when a check is capped), so a change re-fetches via the resource key.
	let language = $state('');
	// The scan is cached server-side; Re-run forces a fresh one. Not $state: the
	// fetcher reads it (untracked) for the one load it covers, then clears it —
	// nothing reactive observes it, and the resource key is `language` alone.
	let forceRefresh = false;

	// Client-side stale-while-revalidate. The last scan per language is kept in
	// sessionStorage and used to seed the first paint, so returning to this page
	// shows the previous result at once (with its own "scanned … ago" stamp) while
	// a fresh scan loads in the background — instead of a blank "Running audit…"
	// on every visit. The server already caches the scan; this hides the
	// round-trip's flash too. Best-effort: any storage failure just falls back to
	// the normal load.
	const cacheKey = (lang: string) => `admin:audit:${lang || 'all'}`;
	function readAuditCache(lang: string): AdminAudit | null {
		if (typeof sessionStorage === 'undefined') return null;
		try {
			const raw = sessionStorage.getItem(cacheKey(lang));
			return raw ? (JSON.parse(raw) as AdminAudit) : null;
		} catch {
			return null;
		}
	}
	const auditRes = adminResource(
		() => getAdminAudit(language, forceRefresh),
		'Something went wrong running the audit.',
		() => language,
		(result) => {
			try {
				sessionStorage?.setItem(cacheKey(language), JSON.stringify(result));
			} catch {
				/* private mode / quota — the fetch still populated the page */
			}
		}
	);
	// Seed the first paint from cache; the load already in flight overwrites it.
	// `language` is always '' on mount (no URL seeding), so the default "all
	// editions" scan is the one to restore.
	auditRes.data ??= readAuditCache('');
	const audit = $derived(auditRes.data);

	async function rerun() {
		forceRefresh = true;
		try {
			await auditRes.load();
		} finally {
			forceRefresh = false;
		}
	}

	// "Scanned 3 minutes ago". Admin is English-only (see frontend/CLAUDE.md).
	const scannedAgo = $derived(
		audit?.scanned_at
			? relativeTime(new Date(audit.scanned_at).getTime(), 'en', 'just now')
			: ''
	);

	// Names ride along with the audit (registry-sourced), so a language an admin
	// added without a deploy reads as itself; the code is the fallback while the
	// payload is still loading. Mirrors the review queue.
	const languageName = (code: string) => audit?.language_names?.[code] ?? code.toUpperCase();

	// Accepting a finding is a write, so serialise it against the re-run it
	// triggers and against a second click. `lastUndo` keeps the most recent
	// acceptance reversible without a separate screen — the reviewer's own
	// misfire is the case undo exists for.
	let busy = $state(false);
	let lastUndo = $state<{ target: AuditDismissTarget; label: string } | null>(null);
	// A failed write must say so — otherwise the row stays on screen and the
	// admin reads "nothing happened" as "accepted".
	let actionError = $state<string | null>(null);

	async function dismiss(target: AuditDismissTarget, label: string) {
		if (busy) return;
		busy = true;
		actionError = null;
		try {
			await dismissAuditFinding(target);
			lastUndo = { target, label };
			await auditRes.load();
		} catch (e) {
			actionError = e instanceof Error ? e.message : "Couldn't accept that finding.";
		} finally {
			busy = false;
		}
	}

	async function undoDismiss() {
		if (busy || !lastUndo) return;
		busy = true;
		actionError = null;
		try {
			await undoAuditDismissal(lastUndo.target);
			lastUndo = null;
			await auditRes.load();
		} catch (e) {
			actionError = e instanceof Error ? e.message : "Couldn't undo that.";
		} finally {
			busy = false;
		}
	}

	// A check's static description. `key` is a plain string, not a keyof the
	// payload type: the backend can ship a check before this file learns its
	// name, and that check must still render (see `qualityChecks`).
	type Tier = 'readers' | 'navigation' | 'fine';
	type CheckDef = { key: string; label: string; desc: string; tier?: Tier };

	// Reader impact, most-felt first. The chip's text and colour live here so
	// the markup never spells a tier out.
	const TIERS: Record<Tier, { label: string; chip: string }> = {
		readers: { label: 'Readers see it', chip: 'border-warning/40 text-warning' },
		navigation: { label: 'Navigation', chip: 'border-border-strong text-text' },
		fine: { label: 'Probably fine', chip: 'border-border text-muted' }
	};
	const TIER_ORDER: Tier[] = ['readers', 'navigation', 'fine'];

	// Quality checks are advisory book-qa heuristics. Rendered by tier, then in
	// this order within a tier.
	const QUALITY: (CheckDef & { tier: Tier })[] = [
		{ key: 'mid_sentence_splits', label: 'Mid-sentence splits', desc: "Chapter body doesn't end in sentence punctuation", tier: 'readers' },
		{ key: 'generic_titles', label: 'Generic / missing titles', desc: 'Empty title, or a bare “Chapter N”', tier: 'navigation' },
		{ key: 'missing_dropcap', label: 'Missing drop cap', desc: 'Body starts lower-case or mid-word', tier: 'readers' },
		{ key: 'fragmented', label: 'Fragmented paragraphs', desc: 'Very low words-per-paragraph', tier: 'readers' },
		{
			key: 'loose_text',
			label: 'Text outside paragraphs',
			desc: 'Text sitting between blocks, outside any paragraph — often captions or poems that lost their markup',
			tier: 'readers'
		},
		{ key: 'duplicate_titles', label: 'Duplicate titles in a book', desc: 'Same title on multiple chapters', tier: 'navigation' },
		{ key: 'tiny_chapters', label: 'Tiny chapters', desc: 'Under 150 words', tier: 'navigation' },
		{ key: 'giant_chapters', label: 'Giant chapters', desc: 'Over 8,000 words — a split may be missed', tier: 'fine' }
	];

	const INTEGRITY: CheckDef[] = [
		{ key: 'broken_plan_days', label: 'Broken plan days', desc: 'A plan day points at a missing chapter or article' },
		{ key: 'empty_books', label: 'Books with no chapters', desc: 'A published book with no chapters' },
		{ key: 'empty_chapters', label: 'Empty chapters', desc: 'No body text' },
		{ key: 'order_gaps', label: 'Chapter-order gaps', desc: 'Missing chapter numbers' }
	];
	const integrityDef = (key: keyof AdminAudit['integrity']) => INTEGRITY.find((d) => d.key === key)!;

	// "loose_text" → "Loose text": the label a check wears until it's named above.
	const humanize = (key: string) => {
		const s = key.replace(/_/g, ' ');
		return s.charAt(0).toUpperCase() + s.slice(1);
	};

	type QualityCheck = CheckDef & { tier: Tier; c: Capped<unknown> };
	// The quality checks this payload actually carries, in tier order. Driven by
	// the payload, not QUALITY: a known check the server didn't send is skipped
	// (rather than reading `.total` of undefined), and one this file doesn't
	// know yet still renders — humanized label, top tier, so it can't hide.
	const qualityChecks = $derived.by((): QualityCheck[] => {
		if (!audit) return [];
		const payload = audit.quality as Record<string, Capped<unknown> | undefined>;
		const known = new Set(QUALITY.map((q) => q.key));
		const defs: (CheckDef & { tier: Tier })[] = [
			...QUALITY,
			...Object.keys(payload)
				.filter((k) => !known.has(k))
				.map((k) => ({ key: k, label: humanize(k), desc: '', tier: 'readers' as const }))
		];
		return TIER_ORDER.flatMap((t) =>
			defs.flatMap((d) => {
				const c = payload[d.key];
				return d.tier === t && c ? [{ ...d, c }] : [];
			})
		);
	});

	const integrityTotal = $derived(
		audit ? Object.values(audit.integrity).reduce((n, c) => n + c.total, 0) : 0
	);
	const failingIntegrity = $derived(
		audit ? Object.values(audit.integrity).filter((c) => c.total > 0).length : 0
	);
	const qualityTotal = $derived(qualityChecks.reduce((n, q) => n + q.c.total, 0));

	// The quality bar: one segment per flagged check, biggest first, so a check
	// that dominates the total shows as one. Shades of the warning hue step down
	// by rank, mixed toward the track so they hold in light and dark themes.
	const qualitySegments = $derived(
		qualityChecks
			.filter((q) => q.c.total > 0)
			.sort((x, y) => y.c.total - x.c.total)
			.map((q, i, all) => ({
				key: q.key,
				label: q.label,
				total: q.c.total,
				color: `color-mix(in srgb, var(--warning) ${all.length > 1 ? Math.round(100 - (i * 65) / (all.length - 1)) : 100}%, var(--surface-2))`
			}))
	);

	// An unknown check's items are only known to be objects; the chapter list
	// keys rows on book/language/order, so use it only when they're there.
	const isChapterShaped = (items: unknown[]): items is AuditChapterFinding[] =>
		items.every((f) => typeof f === 'object' && f !== null && 'book' in f && 'order' in f);

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
		if (f.loose_runs != null) return `${f.loose_runs} loose · “${f.loose}”`;
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
			<div class="flex items-center gap-2">
				{#if audit.languages.length > 1}
					<label class="sr-only" for="audit-language">Filter by language</label>
					<select
						id="audit-language"
						class="field text-small"
						bind:value={language}
						disabled={auditRes.loading}
					>
						<option value="">All languages</option>
						{#each audit.languages as code (code)}
							<option value={code}>{languageName(code)}</option>
						{/each}
					</select>
				{/if}
				<div class="flex flex-col items-end">
					<button class="btn btn-ghost" onclick={rerun} disabled={auditRes.loading}
						>{auditRes.loading ? 'Re-running…' : 'Re-run'}</button
					>
					{#if scannedAgo}<span class="mt-1 text-micro text-muted">Scanned {scannedAgo}</span>{/if}
				</div>
			</div>
		{/if}
	</header>

	<AdminGate resource={auditRes} errorTitle="Couldn't run the audit" loadingText="Running audit…">
		{#snippet children(a)}
			<!-- Summary: integrity defects (fix these) and advisory quality flags
			     are different kinds of thing, so each gets its own tile rather than
			     a share of one bar. -->
			<div class={lastUndo || actionError ? 'mb-2' : 'mb-8'}>
				<div class="grid gap-3 sm:grid-cols-2">
					<div class="rounded-card border border-border bg-surface p-4">
						<p class="eyebrow mb-2 text-muted">Data integrity</p>
						{#if integrityTotal}
							<div class="stat-number text-danger">{integrityTotal}</div>
							<div class="mt-2 text-small text-muted">
								{integrityTotal === 1 ? 'issue' : 'issues'} in {failingIntegrity} of {INTEGRITY.length} checks · fix these
							</div>
						{:else}
							<div class="stat-number-sm">All clear</div>
							<div class="mt-2 text-small text-muted">{INTEGRITY.length} of {INTEGRITY.length} checks pass</div>
						{/if}
					</div>
					<div class="rounded-card border border-border bg-surface p-4">
						<p class="eyebrow mb-2 text-muted">Content quality</p>
						{#if qualityTotal}
							<div class="stat-number text-warning">{qualityTotal}</div>
							<div class="mt-2 text-small text-muted">
								{qualityTotal === 1 ? 'flag' : 'flags'} in {qualitySegments.length} {qualitySegments.length === 1 ? 'check' : 'checks'} · advisory
							</div>
						{:else}
							<div class="stat-number-sm">All clear</div>
							<div class="mt-2 text-small text-muted">{qualityChecks.length} of {qualityChecks.length} checks pass · advisory</div>
						{/if}
					</div>
				</div>
				{#if qualitySegments.length}
					<div
						class="mt-4 flex h-2 gap-0.5 overflow-hidden rounded-full bg-surface-2"
						role="img"
						aria-label="Quality flags by check: {qualitySegments.map((s) => `${s.label} ${s.total}`).join(', ')}"
					>
						{#each qualitySegments as s (s.key)}
							<div style="flex: {s.total} 1 0; min-width: 2px; background: {s.color}"></div>
						{/each}
					</div>
					<ul class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-small text-muted" aria-hidden="true">
						{#each qualitySegments as s (s.key)}
							<li class="flex items-center gap-1.5">
								<span class="inline-block h-2 w-2 shrink-0 rounded-full" style="background: {s.color}"></span>
								{s.label} <span class="tabular-nums text-text">{s.total}</span>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
			{#if actionError}
				<p class="mb-8 text-small text-warning">{actionError}</p>
			{:else if lastUndo}
				<p class="mb-8 flex items-baseline gap-2 text-small text-muted">
					Accepted <span class="text-text">{lastUndo.label}</span>.
					<button
						type="button"
						class="text-accent hover:underline disabled:opacity-50"
						disabled={busy}
						onclick={undoDismiss}>Undo</button
					>
				</p>
			{/if}

			<!-- "Accept as known" — only shown on advisory quality findings (an
			     integrity defect is fixed, not accepted, so those rows pass no
			     checkKey). Removes the finding and files it under the check's count. -->
			{#snippet acceptBtn(target: AuditDismissTarget, label: string)}
				<button
					type="button"
					class="shrink-0 text-small text-muted hover:text-accent disabled:opacity-50"
					title="Accept as known — remove this from the audit"
					disabled={busy}
					onclick={() => dismiss(target, label)}>accept</button
				>
			{/snippet}

			<!-- One chapter row, used everywhere findings are chapter-shaped. When a
			     book is grouped, `bare` drops the repeated slug and shows only /order.
			     `checkKey` (present only for dismissible quality checks) adds Accept. -->
			{#snippet chapterItem(f: AuditChapterFinding, bare = false, checkKey?: string)}
				<li class="flex items-baseline justify-between gap-3 py-1.5">
					<a
						href={editionHref(`/books/${f.book}/${f.order}`, f.language)}
						class="min-w-0 truncate text-body text-text hover:text-accent"
					>
						{#if bare}<span class="text-muted">/{f.order}</span>{:else}<span class="text-muted">{f.book}/{f.order}</span> <span class="text-micro text-muted">{f.language}</span>{/if}
						— {f.title || '(untitled)'}
					</a>
					<span class="flex shrink-0 items-baseline gap-2">
						{#if evidence(f)}<span class="text-small text-muted">{evidence(f)}</span>{/if}
						{#if checkKey}{@render acceptBtn({ check: checkKey, book: f.book, language: f.language, ref: String(f.order) }, `${f.book}/${f.order}`)}{/if}
					</span>
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
			{#snippet chapterList(items: AuditChapterFinding[], total: number = items.length, checkKey?: string)}
				<ul class="mt-1">
					{#each byBook(items) as g (g.book + ':' + g.language)}
						{#if g.items.length === 1}
							{@render chapterItem(g.items[0], false, checkKey)}
						{:else}
							<li class="py-1.5">
								<a href={editionHref(`/books/${g.book}`, g.language)} class="text-body text-text hover:text-accent">
									<span class="text-muted">{g.book}</span> <span class="text-micro text-muted">{g.language}</span>
								</a>
								<span class="text-small text-muted">· {g.items.length} chapters</span>
								<ul class="ml-4 border-l border-border pl-3">
									{#each g.items as f (findingKey(f))}
										{@render chapterItem(f, true, checkKey)}
									{/each}
								</ul>
							</li>
						{/if}
					{/each}
				</ul>
				{@render moreLine(items.length, total)}
			{/snippet}

			<!-- A collapsible check. Header is always visible (label, tier chip,
			     description, count); the body renders only when opened. `open` lets
			     integrity bugs default to expanded while advisory quality checks stay
			     folded. -->
			{#snippet check(def: CheckDef, total: number, open: boolean, body: import('svelte').Snippet, dismissed = 0)}
				<details class="group border-b border-border py-2" {open}>
					<summary class="flex cursor-pointer list-none items-baseline justify-between gap-3">
						<span class="flex min-w-0 items-baseline">
							<span class="mr-1 inline-block shrink-0 text-muted transition-transform group-open:rotate-90">›</span>
							<span class="min-w-0">
								<span class="text-body font-semibold text-text">{def.label}</span>
								{#if def.tier}<span class="ml-1.5 inline-block whitespace-nowrap rounded-full border px-2 align-middle text-micro {TIERS[def.tier].chip}">{TIERS[def.tier].label}</span>{/if}
								{#if def.desc}<span class="block text-small text-muted">{def.desc}</span>{/if}
							</span>
						</span>
						<span class="shrink-0 text-small">
							{#if dismissed}<span class="text-muted">{dismissed} accepted ·&nbsp;</span>{/if}<span
								class={total ? 'text-warning' : 'text-muted'}>{#if total}{total}{:else}✓ clear{/if}</span
							>
						</span>
					</summary>
					{#if total}<div class="ml-4">{@render body()}</div>{/if}
				</details>
			{/snippet}

			<!-- The four integrity checks, as rows. Rendered under the section
			     heading when any fails, or behind the folded line when all pass. -->
			{#snippet integrityChecks()}
				{#snippet planDays()}
					<ul class="mt-1">
						{#each a.integrity.broken_plan_days.items as d (d.plan + ':' + d.language + ':' + d.day)}
							<li class="py-1.5 text-body">
								<a href={editionHref(`/plans/${d.plan}`, d.language)} class="text-text hover:text-accent">{d.plan}</a>
								<span class="text-small text-muted">day {d.day} → {d.article ? `article ${d.article}` : `${d.book}/${d.order}`} ({d.language})</span>
							</li>
						{/each}
					</ul>
					{@render moreLine(a.integrity.broken_plan_days.items.length, a.integrity.broken_plan_days.total)}
				{/snippet}
				{@render check(integrityDef('broken_plan_days'), a.integrity.broken_plan_days.total, a.integrity.broken_plan_days.total > 0, planDays)}

				{#snippet emptyBooks()}
					<ul class="mt-1">
						{#each a.integrity.empty_books.items as b (b.book + b.language)}
							<li class="py-1.5 text-body"><a href={editionHref(`/books/${b.book}`, b.language)} class="text-text hover:text-accent">{b.title}</a> <span class="text-small text-muted">{b.author} · {b.language}</span></li>
						{/each}
					</ul>
					{@render moreLine(a.integrity.empty_books.items.length, a.integrity.empty_books.total)}
				{/snippet}
				{@render check(integrityDef('empty_books'), a.integrity.empty_books.total, a.integrity.empty_books.total > 0, emptyBooks)}

				{#snippet emptyChapters()}
					{@render chapterList(a.integrity.empty_chapters.items, a.integrity.empty_chapters.total)}
				{/snippet}
				{@render check(integrityDef('empty_chapters'), a.integrity.empty_chapters.total, a.integrity.empty_chapters.total > 0, emptyChapters)}

				{#snippet orderGaps()}
					<ul class="mt-1">
						{#each a.integrity.order_gaps.items as g (g.book + ':' + g.language)}
							<li class="py-1.5 text-body"><a href={editionHref(`/books/${g.book}`, g.language)} class="text-text hover:text-accent">{g.book}</a> <span class="text-small text-muted">{g.language} · missing {g.missing.join(', ')} of {g.count}</span></li>
						{/each}
					</ul>
					{@render moreLine(a.integrity.order_gaps.items.length, a.integrity.order_gaps.total)}
				{/snippet}
				{@render check(integrityDef('order_gaps'), a.integrity.order_gaps.total, a.integrity.order_gaps.total > 0, orderGaps)}
			{/snippet}

			<div class="grid gap-10">
				{#if integrityTotal}
					<!-- Integrity: real data defects. Loud, first, open when non-empty. -->
					<section>
						<h2 class="text-h3 mb-1 flex items-baseline gap-2">
							Data integrity
							<span class="text-small font-normal text-danger">fix these</span>
						</h2>
						<p class="mb-3 text-small text-muted">Structural defects readers hit directly.</p>
						{@render integrityChecks()}
					</section>
				{:else}
					<!-- All clear: one folded line, so the advisory list below gets the
					     page instead of sharing it with four green rows. -->
					<details class="group rounded-card border border-border bg-surface-2 px-4 py-3">
						<summary class="flex cursor-pointer list-none items-baseline gap-1">
							<span class="inline-block shrink-0 text-muted transition-transform group-open:rotate-90">›</span>
							<span class="min-w-0">
								<span class="text-body font-semibold text-text">Data integrity: all {INTEGRITY.length} checks clear</span>
								<span class="block text-small text-muted">{INTEGRITY.map((d) => d.label).join(' · ')}</span>
							</span>
						</summary>
						<div class="mt-2">{@render integrityChecks()}</div>
					</details>
				{/if}

				<!-- Quality: advisory heuristics. Folded by default; expand to inspect. -->
				<section>
					<h2 class="text-h3 mb-1">Content quality</h2>
					<p class="mb-3 text-small text-muted">Advisory heuristics — expect false positives.</p>

					{#each qualityChecks as q (q.key)}
						{#if q.key === 'duplicate_titles'}
							{#snippet dupTitles()}
								<ul class="mt-1">
									{#each a.quality.duplicate_titles.items as f (f.book + ':' + f.language + ':' + f.title)}
										<li class="flex items-baseline justify-between gap-3 py-1.5">
											<a href={editionHref(`/books/${f.book}`, f.language)} class="min-w-0 truncate text-body text-text hover:text-accent"><span class="text-muted">{f.book}</span> <span class="text-micro text-muted">{f.language}</span> — “{f.title}”</a>
											<span class="flex shrink-0 items-baseline gap-2">
												<span class="text-small text-muted">×{f.count}</span>
												{@render acceptBtn({ check: 'duplicate_titles', book: f.book, language: f.language, ref: f.title }, `${f.book} “${f.title}”`)}
											</span>
										</li>
									{/each}
								</ul>
								{@render moreLine(a.quality.duplicate_titles.items.length, a.quality.duplicate_titles.total)}
							{/snippet}
							{@render check(q, q.c.total, false, dupTitles, q.c.dismissed)}
						{:else}
							{@const items = q.c.items}
							{#snippet findings()}
								{#if isChapterShaped(items)}
									{@render chapterList(items, q.c.total, q.key)}
								{:else}
									<!-- A check this page doesn't know the shape of: show the
									     raw rows rather than nothing. -->
									<ul class="mt-1">
										{#each items as item, i (i)}
											<li class="break-all py-1.5 text-small text-muted">{JSON.stringify(item)}</li>
										{/each}
									</ul>
									{@render moreLine(items.length, q.c.total)}
								{/if}
							{/snippet}
							{@render check(q, q.c.total, false, findings, q.c.dismissed)}
						{/if}
					{/each}

					<!-- After the checks, not beside one: Tiny and Giant sit in
					     different tiers, and this is context for tuning both. -->
					{#if a.chapter_lengths}
						<div class="mt-6"><ChapterLengthChart data={a.chapter_lengths} /></div>
					{/if}
				</section>
			</div>
		{/snippet}
	</AdminGate>
</div>
