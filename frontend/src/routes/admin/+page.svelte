<script lang="ts">
	import { goto } from '$app/navigation';
	import { apiFetchRaw } from '$lib/api';
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { type SourceType } from '$lib/library-public';
	import { getAdminStats } from '$lib/library-admin';
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
					{ label: 'Words', value: stats.totals.words, sub: 'chapters + sermons' },
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

	<AdminGate resource={dashboard} errorTitle="Couldn't load the dashboard">
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
				{#each cards as c (c.label)}
					<div class="rounded-card border border-border bg-surface p-5">
						<div class="stat-number">{fmt(c.value)}</div>
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
				<div class="overflow-x-auto rounded-card border border-border bg-surface">
					<table class="w-full min-w-[44rem] border-collapse text-body">
						<thead>
							<tr class="eyebrow border-b border-border text-muted">
								<th class="px-4 py-3 text-left font-semibold">Language</th>
								<th class="px-4 py-3 text-right font-semibold">Books</th>
								<th class="px-4 py-3 text-right font-semibold">Chapters</th>
								<th class="px-4 py-3 text-right font-semibold">Sermons</th>
								<th class="px-4 py-3 text-right font-semibold">Plans</th>
								<th class="px-4 py-3 text-right font-semibold">Bios</th>
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
										{/if}
									</td>
									<td class="px-4 py-3 text-right tabular-nums">{fmt(l.chapters)}</td>
									<td class="px-4 py-3 text-right tabular-nums">{fmt(l.sermons)}</td>
									<td class="px-4 py-3 text-right tabular-nums">{fmt(l.plans)}</td>
									<td class="px-4 py-3 text-right tabular-nums">{fmt(l.bios)}</td>
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
