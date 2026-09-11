<script lang="ts">
	import { goto } from '$app/navigation';
	import { apiFetchRaw } from '$lib/api';
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { type SourceType } from '$lib/library-public';
	import {
		getAdminStats,
		getAdminAttention,
		getAdminTranslationJobs,
		countJobsByLanguageType,
		type TranslationJobType
	} from '$lib/library-admin';
	import AddLanguageForm from '$lib/components/AddLanguageForm.svelte';

	let exporting = $state<'csv' | 'json' | null>(null);

	async function exportInventory(fmt: 'csv' | 'json') {
		exporting = fmt;
		try {
			const res = await apiFetchRaw(`/api/admin/export/${fmt === 'csv' ? '?fmt=csv' : ''}`);
			const blob = await res.blob();
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `ochorus-inventory.${fmt}`;
			a.click();
			URL.revokeObjectURL(url);
		} catch {
			/* denied or offline — the dashboard already surfaces auth errors */
		} finally {
			exporting = null;
		}
	}

	// Internal tool: copy is English-only (not run through Paraglide).
	// `loadedAt` is stamped by onLoad (only on a non-superseded payload), so the
	// header can say how fresh the figures are — a snapshot is easy to misread as
	// live.
	let loadedAt = $state<Date | null>(null);
	const dashboard = adminResource(
		getAdminStats,
		'Something went wrong loading the dashboard.',
		undefined,
		() => (loadedAt = new Date())
	);
	const stats = $derived(dashboard.data);

	// The "needs attention" hub — its own resource so it paints as soon as it
	// loads, independent of the (heavier) stats call. The API returns raw signals;
	// the ranking, labels and links are composed here (admin is English-only).
	const attentionRes = adminResource(getAdminAttention, 'Something went wrong loading attention.');
	const att = $derived(attentionRes.data);

	// The translation queue is GitHub issues, reached over a slow paginated API
	// that can be unconfigured or unreachable. Kept as its own best-effort
	// resource so it NEVER blocks the (DB-fast) By-language table: the counts
	// paint immediately and the "+N queued" overlay (countJobsByLanguageType,
	// unit-tested) fills in when jobs arrive — or stays silent if it can't.
	const jobsRes = adminResource(getAdminTranslationJobs, 'Something went wrong loading the queue.');
	const queued = $derived(countJobsByLanguageType(jobsRes.data?.jobs ?? []));

	type HubTier = 'critical' | 'backlog' | 'demand';
	interface HubRow { tier: HubTier; value: string; big: boolean; label: string; why: string; href: string; }
	const dotClass: Record<HubTier, string> = {
		critical: 'bg-danger',
		backlog: 'bg-warning',
		demand: 'bg-accent'
	};

	// Actionable rows, in reader-impact order: integrity defects → the review
	// backlog → unmet demand. Only rows with a real filtered destination are
	// clickable rows; count-only signals with no page yet go in the "also" line.
	const hubRows = $derived.by<HubRow[]>(() => {
		if (!att) return [];
		const rows: HubRow[] = [];
		if (att.empty_chapters)
			rows.push({ tier: 'critical', value: fmt(att.empty_chapters), big: true, label: 'Empty chapters', why: 'Published chapters with no body text.', href: '/admin/audit' });
		if (att.empty_books)
			rows.push({ tier: 'critical', value: fmt(att.empty_books), big: true, label: 'Books with no chapters', why: 'A published book that opens to nothing.', href: '/admin/audit' });
		if (att.unreviewed_translations)
			rows.push({ tier: 'backlog', value: fmt(att.unreviewed_translations), big: true, label: 'AI translations awaiting review', why: 'Readers see an “awaiting review” badge until a native speaker checks these.', href: '/admin/review' });
		if (att.searches.zero_30d)
			rows.push({ tier: 'demand', value: fmt(att.searches.zero_30d), big: true, label: 'Searches that found nothing · 30d', why: `Readers asked; the library had no answer — ${Math.round(att.searches.zero_rate * 100)}% of searches.`, href: '/admin/search' });
		for (const l of att.languages_missing_books)
			rows.push({ tier: 'demand', value: l.name, big: false, label: `${l.name} live with 0 books`, why: `${fmt(l.sermons)} sermon${l.sermons === 1 ? '' : 's'}, but nothing for a book reader to open.`, href: `/admin/languages/${l.code}` });
		return rows;
	});
	// Integrity is "clean" when neither structural count is set — shown as
	// reassurance rather than an empty gap.
	const integrityClean = $derived(!!att && att.empty_chapters === 0 && att.empty_books === 0);
	// Real signals that have no dedicated page to open yet — surfaced as counts.
	const alsoCounts = $derived.by<string[]>(() => {
		if (!att) return [];
		const a: string[] = [];
		if (att.unpublished_books) a.push(`${fmt(att.unpublished_books)} unpublished book${att.unpublished_books === 1 ? '' : 's'}`);
		if (att.unpublished_sermons) a.push(`${fmt(att.unpublished_sermons)} unpublished sermon${att.unpublished_sermons === 1 ? '' : 's'}`);
		if (att.authors_without_bio) a.push(`${fmt(att.authors_without_bio)} author${att.authors_without_bio === 1 ? '' : 's'} without a bio`);
		return a;
	});

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number | null | undefined) => nf.format(n ?? 0);
	const timeFmt = (d: Date) => d.toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' });
	const dateFmt = (iso: string) =>
		new Date(iso).toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' });

	const SOURCE_LABELS: Record<SourceType, string> = {
		public_domain: 'Public domain',
		ai_reviewed: 'AI · reviewed',
		ai_unreviewed: 'AI · unreviewed'
	};

	// Headline numbers, in a fixed order.
	const cards = $derived(
		stats
			? [
					{ label: 'Works', value: stats.totals.works, sub: 'distinct titles' },
					{
						label: 'Books',
						value: stats.totals.books,
						sub: `${fmt(stats.totals.published_books)} published`
					},
					{ label: 'Chapters', value: stats.totals.chapters, sub: 'across all books' },
					{
						label: 'Words',
						value: stats.totals.words,
						// A raw word count is abstract; hours-to-read (~200 wpm) is relatable.
						// The words are still chapters + sermons — that stays true.
						sub: `≈ ${fmt(Math.round(stats.totals.words / 12000))} hrs of reading`
					},
					{
						label: 'Sermons',
						value: stats.totals.sermons,
						sub: `${fmt(stats.totals.published_sermons)} published`
					},
					{
						label: 'Plans',
						value: stats.totals.plans,
						sub: `${fmt(stats.totals.published_plans)} published`
					},
					{
						label: 'Authors',
						value: stats.totals.authors,
						sub: `${fmt(stats.totals.authors_with_bio)} with a bio`
					},
					{ label: 'Languages', value: stats.totals.languages, sub: 'with content' }
				]
			: []
	);

	// Content-health chips — only those with a non-zero count are shown.
	const flags = $derived(
		stats
			? [
					{ label: 'unpublished books', n: stats.attention.unpublished_books, href: null },
					{ label: 'unpublished sermons', n: stats.attention.unpublished_sermons, href: null },
					{
						label: 'unreviewed AI translations',
						n: stats.attention.unreviewed_translations,
						href: '/admin/review'
					},
					{ label: 'authors without a bio', n: stats.attention.authors_without_bio, href: null },
					// The audit lists the empty chapters themselves (integrity check). The
					// other flags have no destination page yet — a Wave-3 acquisition/list
					// view — so they stay non-links rather than pointing nowhere.
					{ label: 'empty chapters', n: stats.attention.empty_chapters, href: '/admin/audit' }
				].filter((f) => f.n > 0)
			: []
	);
</script>

<svelte:head><title>Admin — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-6xl px-5 py-10">
	<header class="mb-10 flex flex-wrap items-end justify-between gap-4">
		<div>
			<p class="eyebrow mb-2 text-accent">Admin</p>
			<h1 class="text-display">Content dashboard</h1>
			<p class="mt-2 text-body text-muted">A snapshot of the library — quantities, languages and health.</p>
		</div>
		{#if stats}
			<div class="flex flex-wrap items-center gap-2">
				{#if loadedAt}
					<span class="mr-1 text-small text-muted" title={loadedAt.toLocaleString('en')}
						>Updated {timeFmt(loadedAt)}</span
					>
				{/if}
				<button class="btn btn-sm btn-ghost" onclick={() => exportInventory('csv')} disabled={!!exporting}>
					{exporting === 'csv' ? 'Exporting…' : 'Export CSV'}
				</button>
				<button class="btn btn-sm btn-ghost" onclick={() => exportInventory('json')} disabled={!!exporting}>
					{exporting === 'json' ? 'Exporting…' : 'Export JSON'}
				</button>
				<button class="btn btn-ghost" onclick={dashboard.load} disabled={dashboard.loading}>
					{dashboard.loading ? 'Refreshing…' : 'Refresh'}
				</button>
			</div>
		{/if}
	</header>

	<!-- Needs attention hub: what to act on, aggregated across the admin. Its own
	     resource, so it paints before the heavier stats call and never blocks it. -->
	{#if att && (hubRows.length || alsoCounts.length || integrityClean)}
		<section class="mb-8 overflow-hidden rounded-card border border-border bg-surface">
			<div class="flex flex-wrap items-baseline justify-between gap-3 border-b border-border px-5 py-3">
				<div class="flex items-baseline gap-2">
					<h2 class="text-h3">Needs attention</h2>
					{#if hubRows.length}<span class="text-small text-muted">{hubRows.length} to act on</span>{/if}
				</div>
				<span class="text-small text-muted">Ranked by reader impact</span>
			</div>

			{#if integrityClean}
				<p class="flex items-center gap-2 border-b border-border px-5 py-2 text-small text-muted">
					<span class="text-accent">✓</span> Data integrity is clean — no empty chapters or bookless books.
				</p>
			{/if}

			{#each hubRows as r (r.label)}
				<a
					href={r.href}
					class="flex items-center gap-3 border-b border-border px-5 py-3 last:border-0 hover:bg-surface-2 hover:no-underline"
				>
					<span class="h-2 w-2 shrink-0 rounded-full {dotClass[r.tier]}"></span>
					<span class="w-16 shrink-0 truncate text-right font-semibold tabular-nums text-text {r.big ? 'stat-number-sm' : 'text-body'}">{r.value}</span>
					<span class="min-w-0 flex-1">
						<span class="block font-semibold text-text">{r.label}</span>
						<span class="block text-small text-muted">{r.why}</span>
					</span>
					<span class="shrink-0 text-small text-accent">→</span>
				</a>
			{/each}

			{#if alsoCounts.length}
				<p class="px-5 py-2.5 text-small text-muted">Also: {alsoCounts.join(' · ')}.</p>
			{/if}

			{#if !hubRows.length && !alsoCounts.length}
				<p class="px-5 py-3 text-small text-muted">Nothing needs attention right now.</p>
			{/if}
		</section>
	{/if}

	<AdminGate resource={dashboard} errorTitle="Couldn't load the dashboard">
		{#snippet loading()}
			<!-- Mirrors the real layout (attention chips + 8 stat tiles) so the first
			     paint has shape instead of a bare "Loading…" on empty cream. -->
			<div class="mb-10 flex flex-wrap gap-2" aria-hidden="true">
				{#each Array(3) as _, i (i)}
					<div class="h-7 w-40 animate-pulse rounded-full bg-surface-2"></div>
				{/each}
			</div>
			<div class="grid grid-cols-2 gap-4 sm:grid-cols-4" aria-hidden="true">
				{#each Array(8) as _, i (i)}
					<div class="rounded-card border border-border bg-surface p-5">
						<div class="h-8 w-20 animate-pulse rounded bg-surface-2"></div>
						<div class="mt-3 h-3 w-16 animate-pulse rounded bg-surface-2"></div>
						<div class="mt-2 h-3 w-24 animate-pulse rounded bg-surface-2"></div>
					</div>
				{/each}
			</div>
			<span class="sr-only">Loading the dashboard…</span>
		{/snippet}
		{#snippet children(s)}
			<!-- Attention flags -->
			{#if flags.length}
				<div class="mb-10 flex flex-wrap gap-2">
					{#each flags as f (f.label)}
						{#if f.href}
							<a
								href={f.href}
								class="inline-flex items-center gap-1.5 rounded-full border border-warning/40 bg-warning/10 px-3 py-1 text-small text-warning hover:bg-warning/20 hover:no-underline"
							>
								<strong class="font-semibold">{fmt(f.n)}</strong>
								{f.label} →
							</a>
						{:else}
							<span
								class="inline-flex items-center gap-1.5 rounded-full border border-warning/40 bg-warning/10 px-3 py-1 text-small text-warning"
							>
								<strong class="font-semibold">{fmt(f.n)}</strong>
								{f.label}
							</span>
						{/if}
					{/each}
				</div>
			{/if}

			<!-- Headline totals -->
			<section class="mb-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
				{#each cards as c, i (c.label)}
					<div class="rounded-card border border-border bg-surface p-5">
						<!-- The first four (Works / Books / Chapters / Words) are the library's
						     scale and carry the large figure; the rest read as secondary. -->
						<div class={i < 4 ? 'stat-number' : 'stat-number-sm'}>{fmt(c.value)}</div>
						<div class="mt-2 text-small font-semibold text-text">{c.label}</div>
						<div class="text-small text-muted">{c.sub}</div>
					</div>
				{/each}
			</section>

			<!-- By language -->
			<section class="mb-10">
				<div class="mb-1 flex flex-wrap items-center justify-between gap-2">
					<h2 class="text-h2">By language</h2>
					<a href="/admin/coverage" class="text-small font-semibold text-accent hover:underline">Coverage matrix →</a>
				</div>
				<p class="mb-3 text-small text-muted">Select a language to see what's translated and what to work on next.</p>
				<!-- The gold "+N" beside a count is items queued to translate into this
				     language but not yet live — additive, so "25 +11" is 25 live and 11
				     coming. Parentheses stay reserved for the "(N pub)" published subset.
				     Rendered from `queued`; blank (never "+0") when nothing is queued. -->
				{#snippet plus(code: string, type: TranslationJobType)}
					{@const n = queued[code]?.[type] ?? 0}
					{#if n}<span
							class="ml-1 text-small font-medium text-warning"
							title="Queued to translate">+{n}</span
						>{/if}
				{/snippet}
				<div class="overflow-x-auto rounded-card border border-border bg-surface">
					<table class="w-full min-w-[50rem] border-collapse text-body">
						<thead>
							<tr class="eyebrow border-b border-border text-muted">
								<th class="px-4 py-3 text-left font-semibold">Language</th>
								<th class="px-4 py-3 text-right font-semibold">Books</th>
								<th class="px-4 py-3 text-right font-semibold">Chapters</th>
								<th class="px-4 py-3 text-right font-semibold">Sermons</th>
								<th class="px-4 py-3 text-right font-semibold">Plans</th>
								<th class="px-4 py-3 text-right font-semibold">Bios</th>
								<th class="px-4 py-3 text-right font-semibold">Articles</th>
								<th class="px-4 py-3 text-right font-semibold">Words</th>
								<th class="px-4 py-3 text-left font-semibold">Source</th>
							</tr>
						</thead>
						<tbody>
							{#each s.languages as l (l.code)}
								<!-- Whole-row click is a mouse convenience; the language name is a
								     real anchor, so keyboard / AT users have the same destination
								     and clicks on the name still navigate normally. -->
								<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
								<tr
									class="cursor-pointer border-b border-border last:border-0 hover:bg-surface-2"
									onclick={(e) => {
										if (!(e.target as HTMLElement).closest('a')) goto(`/admin/languages/${l.code}`);
									}}
								>
									<td class="px-4 py-3">
										<a href="/admin/languages/{l.code}" class="font-semibold text-accent hover:underline">{l.name}</a>
										<span class="text-small text-muted">· {l.code}</span>
									</td>
									<td class="px-4 py-3 text-right tabular-nums">
										{fmt(l.books)}
										{#if l.published_books !== l.books}
											<span class="text-small text-muted">({fmt(l.published_books)} pub)</span>
										{/if}{@render plus(l.code, 'book')}
									</td>
									<td class="px-4 py-3 text-right tabular-nums">{fmt(l.chapters)}</td>
									<td class="px-4 py-3 text-right tabular-nums">{fmt(l.sermons)}{@render plus(l.code, 'sermon')}</td>
									<td class="px-4 py-3 text-right tabular-nums">{fmt(l.plans)}{@render plus(l.code, 'plan')}</td>
									<td class="px-4 py-3 text-right tabular-nums">{fmt(l.bios)}{@render plus(l.code, 'bio')}</td>
									<td class="px-4 py-3 text-right tabular-nums">{fmt(l.articles)}{@render plus(l.code, 'article')}</td>
									<td class="px-4 py-3 text-right tabular-nums">{fmt(l.words)}</td>
									<td class="px-4 py-3 text-small text-muted">
										{#if l.source_types.public_domain}<span title="Public domain">PD {l.source_types.public_domain}</span>{/if}
										{#if l.source_types.ai_reviewed}<span class="ml-2" title="AI reviewed">AI✓ {l.source_types.ai_reviewed}</span>{/if}
										{#if l.source_types.ai_unreviewed}<span class="ml-2 text-warning" title="AI unreviewed">AI· {l.source_types.ai_unreviewed}</span>{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
				<!-- Legend for the Source column badges — a persistent key beside the
				     per-cell hover titles, matching the coverage matrix. -->
				<p class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-micro text-muted">
					<span><span class="text-text">PD</span> public domain</span>
					<span><span class="text-accent">AI✓</span> AI reviewed</span>
					<span><span class="text-warning">AI·</span> AI unreviewed</span>
					<span><span class="text-warning">+N</span> queued to translate</span>
				</p>
				<!-- Starting a language begins here: the row is what the translate_*
				     commands read, so it has to exist before any work can be queued. -->
				<AddLanguageForm oncreated={dashboard.load} />
			</section>

			<div class="grid gap-6 md:grid-cols-2">
				<!-- Books by source type -->
				<section class="rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3 mb-3">Books by source</h2>
					<ul class="space-y-2 text-body">
						{#each Object.entries(SOURCE_LABELS) as [key, label] (key)}
							<li class="flex items-center justify-between">
								<span class="text-muted">{label}</span>
								<span class="font-semibold tabular-nums text-text"
									>{fmt(s.source_types[key as SourceType])}</span
								>
							</li>
						{/each}
						<li class="flex items-center justify-between border-t border-border pt-2">
							<span class="text-muted">Author bio translations</span>
							<span class="font-semibold tabular-nums text-text">
								{fmt(s.author_translations.total)}
								<span class="text-small font-normal text-muted"
									>({fmt(s.author_translations.reviewed)} reviewed)</span
								>
							</span>
						</li>
					</ul>
				</section>

				<!-- Recently added -->
				<section class="rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3 mb-3">Recently added books</h2>
					{#if s.recent_books.length}
						<ul class="space-y-3">
							{#each s.recent_books as b (`${b.slug}-${b.language}`)}
								<li class="flex items-start justify-between gap-3">
									<div class="min-w-0">
										<a
											href={`/admin/books/${b.slug}`}
											class="block truncate font-semibold text-text hover:text-accent"
											>{b.title}</a
										>
										<div class="text-small text-muted">
											{b.author} · {b.language}
											{#if !b.is_published}· <span class="text-warning">unpublished</span>{/if}
										</div>
									</div>
									<span class="shrink-0 text-small text-muted">{dateFmt(b.created_at)}</span>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="text-body text-muted">No books yet.</p>
					{/if}
				</section>
			</div>
		{/snippet}
	</AdminGate>
</div>
