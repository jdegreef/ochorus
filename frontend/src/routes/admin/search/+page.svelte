<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import {
		type SearchType
	} from '$lib/library-public';
	import {
		getAdminSearchGap,
		type AdminSearchGap,
		getAdminSearchStats,
		type SearchTopQuery
	} from '$lib/library-admin';

	const stats = adminResource(
		getAdminSearchStats,
		'Something went wrong loading search stats.',
		undefined,
		// The per-query gap panels are keyed to the queries in the payload that
		// was showing; a refresh invalidates them.
		() => {
			gaps = {};
		}
	);
	const data = $derived(stats.data);

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number | null | undefined) => nf.format(n ?? 0);
	const pct = (rate: number) => `${Math.round(rate * 100)}%`;
	const dayLabel = (iso: string) =>
		new Date(iso + 'T00:00:00').toLocaleDateString('en', { month: 'short', day: 'numeric' });

	const cards = $derived(
		data
			? [
					{ label: 'Searches · 7d', value: data.overview['7d'].searches, sub: `${fmt(data.overview['7d'].distinct_queries)} distinct` },
					{ label: 'Searches · 30d', value: data.overview['30d'].searches, sub: `${fmt(data.overview['30d'].distinct_queries)} distinct` },
					{ label: 'Zero results · 7d', value: data.overview['7d'].zero_results, sub: `${pct(data.overview['7d'].zero_rate)} of searches` },
					{ label: 'Zero results · 30d', value: data.overview['30d'].zero_results, sub: `${pct(data.overview['30d'].zero_rate)} of searches` },
					{ label: 'Results opened · 30d', value: data.overview.clicks_30d ?? 0, sub: 'searches that led somewhere' }
				]
			: []
	);

	const dayMax = $derived(Math.max(1, ...(data?.daily.map((d) => d.searches) ?? [1])));
	const langMax = $derived(Math.max(1, ...(data?.by_language.map((l) => l.searches) ?? [1])));

	// "Where else does this exist?" — one query at a time, because the answer
	// costs a real search in every live language. Cached per (language, query)
	// for the life of the loaded report; Refresh clears it, which is also how
	// you re-check a row after the translation you queued has landed.
	type GapState = { loading: boolean; data?: AdminSearchGap; error?: string };
	let gaps = $state<Record<string, GapState>>({});
	// U+001F, not a literal NUL: a NUL makes git treat the file as binary, so
	// its diffs stop rendering in review.
	const gapKey = (language: string, q: string) => `${language}\u001f${q}`;

	// "18 chapters · 2 sermons". Every search type's name pluralises with a bare
	// -s, so the rule beats a lookup table — a seventh type reads correctly with
	// no edit here. Admin-only and English-only, so no i18n.
	const byType = (counts: Partial<Record<SearchType, number>>) =>
		Object.entries(counts)
			.sort((a, b) => b[1] - a[1])
			.map(([kind, n]) => `${fmt(n)} ${kind}${n === 1 ? '' : 's'}`)
			.join(' · ');

	async function checkGap(language: string, q: string) {
		const key = gapKey(language, q);
		const current = gaps[key];
		if (current?.loading || current?.data) return; // a failure stays retryable
		gaps = { ...gaps, [key]: { loading: true } };
		try {
			const result = await getAdminSearchGap(q, language);
			gaps = { ...gaps, [key]: { loading: false, data: result } };
		} catch (e) {
			const message = e instanceof Error ? e.message : 'Lookup failed.';
			gaps = { ...gaps, [key]: { loading: false, error: message } };
		}
	}
</script>

<!-- One query list, three uses: top, unopened and zero-result. They differ only
     in the rows and the empty state, so the markup lives once. -->
{#snippet queryList(rows: SearchTopQuery[])}
	<ul class="space-y-2">
		{#each rows as q (q.query)}
			<li class="flex items-baseline justify-between gap-3">
				<a
					href="/search?q={encodeURIComponent(q.query)}"
					class="min-w-0 truncate text-body text-text hover:text-accent">{q.query}</a
				>
				<span class="shrink-0 text-small tabular-nums text-muted">{fmt(q.count)}</span>
			</li>
		{/each}
	</ul>
{/snippet}

<svelte:head><title>Admin · Search — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-5xl px-5 py-10">
	<header class="mb-6 flex flex-wrap items-end justify-between gap-3">
		<div>
			<p class="eyebrow mb-2 text-accent">Admin</p>
			<h1 class="text-display">Search</h1>
			<p class="mt-2 text-body text-muted">
				What readers look for — and what they don't find. Anonymous queries only.
			</p>
		</div>
		{#if data}
			<button class="btn btn-ghost" onclick={stats.load} disabled={stats.loading}
				>{stats.loading ? 'Refreshing…' : 'Refresh'}</button
			>
		{/if}
	</header>

	<AdminGate resource={stats} errorTitle="Couldn't load search stats">
		{#snippet children(d)}
			{#if d.overview['30d'].searches === 0}
				<div class="rounded-card border border-border bg-surface p-8 text-center">
					<p class="text-h3">No searches logged yet</p>
					<p class="mt-1 text-body text-muted">
						Once readers use search, their (anonymous) queries show up here — zero-result queries are
						the best signal for what content to add next.
					</p>
				</div>
			{:else}
				<!-- Overview -->
				<section class="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-5">
					{#each cards as c (c.label)}
						<div class="rounded-card border border-border bg-surface p-4">
							<div class="stat-number">{fmt(c.value)}</div>
							<div class="mt-2 text-small font-semibold text-text">{c.label}</div>
							<div class="text-small text-muted">{c.sub}</div>
						</div>
					{/each}
				</section>

				<!-- Daily volume -->
				<section class="mb-8 rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3 mb-1">Daily searches</h2>
					<p class="mb-4 text-small text-muted">Last 14 days; the darker segment is zero-result searches.</p>
					<div class="flex items-end gap-2" style="height: 8rem">
						{#each d.daily as day (day.day)}
							<div class="flex flex-1 flex-col items-center gap-1">
								<div class="text-small tabular-nums text-muted">{day.searches || ''}</div>
								<div
									class="flex w-full flex-col justify-end overflow-hidden rounded-t-sm"
									style="height: {(day.searches / dayMax) * 100}%; min-height: {day.searches ? '3px' : '0'}"
								>
									<div class="w-full flex-1 bg-accent-soft"></div>
									{#if day.zero}
										<div class="w-full bg-accent" style="height: {(day.zero / day.searches) * 100}%"></div>
									{/if}
								</div>
								<div class="text-micro text-muted">{dayLabel(day.day)}</div>
							</div>
						{/each}
					</div>
				</section>

				<div class="grid gap-6 lg:grid-cols-2">
					<!-- Top queries -->
					<section class="rounded-card border border-border bg-surface p-5">
						<h2 class="text-h3 mb-3">Top queries · 30d</h2>
						{#if d.top_queries.length}
							{@render queryList(d.top_queries)}
						{:else}
							<p class="text-body text-muted">No queries yet.</p>
						{/if}
					</section>

					<!-- Found something, opened nothing -->
					<section class="rounded-card border border-border bg-surface p-5">
						<h2 class="text-h3 mb-1">Found, but not opened · 30d</h2>
						<p class="mb-3 text-small text-muted">
							These returned results and nobody clicked one. A query answered by forty
							near-misses looks like a success everywhere else on this page — this is the
							only place it shows up, and it's usually a better content signal than a
							zero-result query, because nobody complains about a search that returned
							something.
						</p>
						{#if d.unopened_queries?.length}
							{@render queryList(d.unopened_queries)}
						{:else if d.overview.clicks_30d}
							<p class="text-body text-muted">Every recurring query led somewhere.</p>
						{:else}
							<!-- No clicks at all reads as "everything failed", which would be
							     wrong on the day the measurement ships. -->
							<p class="text-body text-muted">
								No opened results recorded yet — this fills in as readers use search.
							</p>
						{/if}
					</section>

					<!-- Zero-result queries -->
					<section class="rounded-card border border-border bg-surface p-5">
						<h2 class="text-h3 mb-1">Zero results · 30d</h2>
						<p class="mb-3 text-small text-muted">Each of these is a reader asking for something the library doesn't have (or can't find) yet.</p>
						{#if d.zero_result_queries.length}
							{@render queryList(d.zero_result_queries)}
						{:else}
							<p class="text-body text-muted">Nothing missed — every search found something.</p>
						{/if}
					</section>
				</div>

				<!-- Unanswered, by language: the translation worklist -->
				{#if d.unanswered_by_language.length}
					<section class="mt-6 rounded-card border border-border bg-surface p-5">
						<h2 class="text-h3 mb-1">What each language couldn't answer · 30d</h2>
						<p class="mb-5 text-small text-muted">
							The same zero-result queries, split by the language the reader was in — which is the
							form you can act on. Check a query to see whether the library already has that
							content in another language: if it does, it's a translation job; if it doesn't,
							it's a work to acquire.
						</p>
						<div class="space-y-6">
							{#each d.unanswered_by_language as lang (lang.code)}
								<div>
									<h3 class="mb-2 text-body font-semibold text-text">
										{lang.name}
										<span class="text-small font-normal text-muted">
											{lang.code} · {fmt(lang.total)} unanswered searches
										</span>
									</h3>
									<ul class="space-y-1">
										{#each lang.queries as q (q.query)}
											{@const gap = gaps[gapKey(lang.code, q.query)]}
											<li class="border-t border-border py-2 first:border-t-0">
												<div class="flex items-baseline justify-between gap-3">
													<span class="min-w-0 truncate text-body text-text">{q.query}</span>
													<span class="flex shrink-0 items-baseline gap-3">
														<span class="text-small tabular-nums text-muted">{fmt(q.count)}×</span>
														{#if !gap?.data}
															<!-- Gone once answered: the answer replaces the question. -->
															<button
																class="btn btn-sm btn-ghost"
																onclick={() => checkGap(lang.code, q.query)}
																disabled={gap?.loading}
															>
																{gap?.loading ? 'Checking…' : gap?.error ? 'Retry' : 'Elsewhere?'}
															</button>
														{/if}
													</span>
												</div>
												{#if gap?.error}
													<p class="mt-1 text-small text-muted">{gap.error}</p>
												{:else if gap?.data}
													{#if gap.data.elsewhere.length}
														<ul class="mt-1 space-y-0.5">
															{#each gap.data.elsewhere as other (other.code)}
																<li class="text-small text-muted">
																	<span class="text-text">{other.name}</span>
																	— {fmt(other.matches)}
																	{other.matches === 1 ? 'match' : 'matches'}
																	<span class="text-muted">({byType(other.by_type)})</span>
																</li>
															{/each}
														</ul>
													{:else}
														<p class="mt-1 text-small text-muted">
															No matches in any other language — nothing to translate from.
														</p>
													{/if}
												{/if}
											</li>
										{/each}
									</ul>
								</div>
							{/each}
						</div>
					</section>
				{/if}

				<!-- By language -->
				<section class="mt-6 rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3 mb-3">Searches by language · 30d</h2>
					<ul class="space-y-2">
						{#each d.by_language as l (l.code)}
							<li class="flex items-center gap-3">
								<span class="w-28 shrink-0 truncate text-body text-text">{l.name} <span class="text-small text-muted">{l.code}</span></span>
								<div class="h-3 flex-1 overflow-hidden rounded-full bg-surface-2">
									<div class="h-full rounded-full bg-accent-soft" style="width: {(l.searches / langMax) * 100}%"></div>
								</div>
								<span class="w-24 shrink-0 text-right text-small tabular-nums text-muted">
									{l.zero ? `${fmt(l.searches)} · ${fmt(l.zero)} zero` : fmt(l.searches)}
								</span>
							</li>
						{/each}
					</ul>
				</section>
			{/if}
		{/snippet}
	</AdminGate>
</div>
