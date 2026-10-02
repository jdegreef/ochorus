<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import { auth } from '$lib/auth.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import TrendChip from '$lib/components/TrendChip.svelte';
	import ColumnChart from '$lib/components/ColumnChart.svelte';
	import {
		type SearchType
	} from '$lib/library-public';
	import {
		getAdminSearchGap,
		type AdminSearchGap,
		type AdminSearchGapWork,
		getAdminSearchStats,
		createAdminTranslationJob,
		decideSearch,
		getAdminSearchDecisions,
		undoSearchDecision,
		type SearchDecisionRow,
		type SearchOutcome,
		type SearchUnanswered,
		periodTrend,
		pointsTrend,
		type SearchStatsWindow,
		type SearchTopQuery,
		type Trend
	} from '$lib/library-admin';
	import { ApiError } from '$lib/api';

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

	// One period at a time, each compared with the period before it — rather
	// than 7d and 30d side by side, which left the trend to mental arithmetic.
	type Period = '7d' | '30d';
	const PERIODS: Record<Period, string> = { '7d': '7 days', '30d': '30 days' };
	let period = $state<Period>('30d');

	// Searches that found something, and how many of them led to an open. Opens
	// are rows, not searches (one search can open several results), so they're
	// capped at the searches that found something rather than reading as more
	// than everyone.
	const found = (w: SearchStatsWindow) => w.searches - w.zero_results;
	const opened = (w: SearchStatsWindow) => Math.min(w.clicks ?? 0, found(w));
	const openRate = (w: SearchStatsWindow) => (found(w) ? opened(w) / found(w) : 0);

	type Card = { label: string; value: string; sub: string; trend: Trend };
	const cards = $derived.by<Card[]>(() => {
		if (!data) return [];
		const cur = data.overview[period];
		// Optional: the static frontend can go live before the API that sends it.
		const prev = data.overview[`${period}_prev`];
		// A rate with no searches behind it, now or before, has nothing to
		// compare, so it gets no chip.
		const rateTrend = (f: (w: SearchStatsWindow) => number, base: (w: SearchStatsWindow) => number) =>
			prev && base(cur) && base(prev) ? f(prev) : null;
		return [
			{
				label: 'Searches',
				value: fmt(cur.searches),
				sub: `${fmt(cur.distinct_queries)} distinct`,
				trend: prev ? periodTrend(cur.searches, prev.searches) : null
			},
			{
				label: 'Zero-result rate',
				value: pct(cur.zero_rate),
				sub: `${fmt(cur.zero_results)} found nothing`,
				trend: pointsTrend(cur.zero_rate, rateTrend((w) => w.zero_rate, (w) => w.searches), {
					lowerIsBetter: true
				})
			},
			{
				label: 'Opened a result',
				value: pct(openRate(cur)),
				sub: `${fmt(cur.clicks)} opens from ${fmt(found(cur))} searches`,
				trend: pointsTrend(openRate(cur), rateTrend(openRate, found))
			},
			{
				label: 'Distinct queries',
				value: fmt(cur.distinct_queries),
				sub: cur.searches ? `${pct(cur.distinct_queries / cur.searches)} of searches` : '—',
				trend: prev ? periodTrend(cur.distinct_queries, prev.distinct_queries) : null
			}
		];
	});

	// Where the period's searches ended: the funnel that separates a content gap
	// (nothing found) from a ranking gap (found, nothing opened).
	const funnel = $derived.by(() => {
		if (!data) return [];
		const w = data.overview[period];
		return [
			{ label: 'Searched', n: w.searches, note: '' },
			{ label: 'Found something', n: found(w), note: `${fmt(w.zero_results)} found nothing → see Unanswered searches` },
			{ label: 'Opened a result', n: opened(w), note: 'the rest → see Found, but not opened' }
		];
	});
	const funnelTop = $derived(Math.max(1, funnel[0]?.n ?? 0));

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

	// Queue a translation straight from a gap: a work that exists elsewhere,
	// translated into the language whose readers searched for it and found
	// nothing. Keyed per (target language, work) so each button tracks its own
	// state; 'busy' | 'done' | an error string.
	let queued = $state<Record<string, 'busy' | 'done' | string>>({});
	const queueKey = (lang: string, w: AdminSearchGapWork) => `${lang}${w.type}:${w.slug}`;
	async function queueWork(targetLang: string, w: AdminSearchGapWork, query: string) {
		const k = queueKey(targetLang, w);
		if (queued[k] === 'busy' || queued[k] === 'done') return;
		queued = { ...queued, [k]: 'busy' };
		try {
			await createAdminTranslationJob({ type: w.type, slug: w.slug, language: targetLang });
			queued = { ...queued, [k]: 'done' };
			// Record it as the query's triage outcome. The row stays on Open until
			// the next refresh, so a second work can still be queued from it.
			void decide(targetLang, query, 'translate', { target: `${w.type}:${w.slug}`, hide: false });
		} catch (e) {
			const body = e instanceof ApiError ? (e.body as { detail?: string } | null) : null;
			queued = { ...queued, [k]: body?.detail ?? 'Could not queue — try again.' };
		}
	}

	// Triage: each unanswered query gets an outcome and leaves the Open list.
	// Decisions live server-side (SearchDecision); the Handled and Wanted tabs
	// read them with what readers did since.
	const decisions = adminResource(
		getAdminSearchDecisions,
		'Something went wrong loading triage decisions.'
	);
	type TriageTab = 'open' | 'handled' | 'wanted';
	let tab = $state<TriageTab>('open');
	const decided = $derived(decisions.data?.decisions ?? []);
	const handled = $derived(decided.filter((d) => d.outcome !== 'wanted'));
	// Ranked by demand since it was marked: the import shopping list, in order.
	const wanted = $derived(
		decided.filter((d) => d.outcome === 'wanted').sort((a, b) => b.misses_since - a.misses_since)
	);
	// Hidden from Open the moment they're decided. Not cleared on refresh: the
	// server leaves decided queries out anyway, and a refresh that started before
	// a decision would otherwise bring it back. Undo is what removes a key.
	let decidedNow = $state<Record<string, true>>({});
	let deciding = $state<Record<string, 'busy' | string>>({});
	const openQueries = (lang: SearchUnanswered) =>
		lang.queries.filter((q) => !decidedNow[gapKey(lang.code, q.query)]);
	const openCount = $derived(
		(data?.unanswered_by_language ?? []).reduce((n, l) => n + openQueries(l).length, 0)
	);
	// The same grant the decide endpoint checks: the translation queue at "act"
	// in that language. Contributors and reviewers see the list but can't change it.
	const canDecide = (language: string) => auth.can('translate', 'act', language);
	const shortDate = (iso: string) =>
		new Date(iso).toLocaleDateString('en', { month: 'short', day: 'numeric' });

	async function decide(
		language: string,
		query: string,
		outcome: SearchOutcome,
		{ target = '', hide = true }: { target?: string; hide?: boolean } = {}
	) {
		const k = gapKey(language, query);
		deciding = { ...deciding, [k]: 'busy' };
		try {
			await decideSearch({ query, language, outcome, target });
			if (hide) decidedNow = { ...decidedNow, [k]: true };
			const { [k]: _, ...rest } = deciding;
			deciding = rest;
			void decisions.load();
		} catch (e) {
			const body = e instanceof ApiError ? (e.body as { detail?: string } | null) : null;
			deciding = { ...deciding, [k]: body?.detail ?? 'Could not save — try again.' };
		}
	}

	async function undo(d: SearchDecisionRow) {
		const k = gapKey(d.language, d.query);
		deciding = { ...deciding, [k]: 'busy' };
		try {
			await undoSearchDecision(d.query, d.language);
			const { [k]: _, ...rest } = deciding;
			deciding = rest;
			const { [k]: __, ...stillHidden } = decidedNow;
			decidedNow = stillHidden;
			// Both: the decision leaves its tab and the query rejoins Open.
			await Promise.all([decisions.load(), stats.load()]);
		} catch (e) {
			const body = e instanceof ApiError ? (e.body as { detail?: string } | null) : null;
			deciding = { ...deciding, [k]: body?.detail ?? 'Could not undo — try again.' };
		}
	}
</script>

<!-- One query list, three uses: top, unopened and zero-result. They differ only
     in the rows and the empty state, so the markup lives once. -->
{#snippet queryList(rows: SearchTopQuery[])}
	{@const max = Math.max(1, ...rows.map((r) => r.count))}
	<ul class="space-y-2">
		{#each rows as q (q.query)}
			<li>
				<div class="flex items-baseline justify-between gap-3">
					<a
						href="/search?q={encodeURIComponent(q.query)}"
						class="min-w-0 truncate text-body text-text hover:text-accent">{q.query}</a
					>
					<span class="shrink-0 text-small tabular-nums text-muted">{fmt(q.count)}</span>
				</div>
				<!-- Volume bar, scaled to the top row of this list, so relative demand
				     reads at a glance instead of comparing numbers down the column. -->
				<div class="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2">
					<div class="h-full rounded-full bg-accent-soft" style="width: {(q.count / max) * 100}%"></div>
				</div>
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
				<!-- Period switch: drives the overview and the funnel; the query
				     lists below stay on 30 days, as their headings say. -->
				<div class="mb-3 flex flex-wrap items-center gap-2" role="group" aria-label="Period">
					{#each Object.entries(PERIODS) as [key, label] (key)}
						<button
							type="button"
							class="rounded-full px-3 py-1 text-small {period === key ? 'bg-accent-soft text-text' : 'text-muted hover:text-text'}"
							aria-pressed={period === key}
							onclick={() => (period = key as Period)}>{label}</button
						>
					{/each}
					<span class="text-small text-muted">· compared with the {PERIODS[period]} before</span>
				</div>

				<!-- Overview -->
				<section class="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
					{#each cards as c (c.label)}
						<div class="rounded-card border border-border bg-surface p-4">
							<div class="flex items-baseline gap-2">
								<div class="stat-number">{c.value}</div>
								<TrendChip trend={c.trend} />
							</div>
							<div class="mt-2 text-small font-semibold text-text">{c.label}</div>
							<div class="text-small text-muted">{c.sub}</div>
						</div>
					{/each}
				</section>

				<!-- Where searches end -->
				<section class="mb-8 rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3">Where searches end</h2>
					<p class="mb-4 text-small text-muted">
						Last {PERIODS[period]}. Nothing found is a content gap; found but not opened is
						usually a ranking or snippet problem. Keystrokes on the way to a search ("pra" →
						"prayer") aren't counted.
					</p>
					<ul class="space-y-3">
						{#each funnel as step (step.label)}
							<li class="grid grid-cols-[8rem_1fr_auto] items-center gap-3 sm:grid-cols-[10rem_1fr_auto]">
								<span class="text-body text-text">{step.label}</span>
								<div class="h-5 overflow-hidden rounded-sm bg-surface-2">
									<div class="h-full rounded-sm bg-accent" style="width: {(step.n / funnelTop) * 100}%"></div>
								</div>
								<span class="w-24 text-end text-small tabular-nums text-text"
									>{fmt(step.n)} <span class="text-muted">· {pct(step.n / funnelTop)}</span></span
								>
								{#if step.note}
									<span class="col-start-2 col-end-4 -mt-2 text-micro text-muted">{step.note}</span>
								{/if}
							</li>
						{/each}
					</ul>
				</section>

				<!-- Daily volume -->
				<section class="mb-8 rounded-card border border-border bg-surface p-5">
					<div class="mb-4 flex flex-wrap items-center justify-between gap-2">
						<div>
							<h2 class="text-h3">Daily searches</h2>
							<p class="text-small text-muted">Last 14 days. Hover a bar for the day's totals.</p>
						</div>
						<div class="flex items-center gap-3 text-micro text-muted">
							<span class="inline-flex items-center gap-1.5"><span class="h-2.5 w-2.5 rounded-sm bg-accent-soft"></span>found</span>
							<span class="inline-flex items-center gap-1.5"><span class="h-2.5 w-2.5 rounded-sm bg-accent"></span>zero-result</span>
						</div>
					</div>
					<ColumnChart
						columns={d.daily.map((day) => ({
							key: day.day,
							label: dayLabel(day.day),
							value: day.searches,
							part: day.zero,
							title: `${dayLabel(day.day)} · ${fmt(day.searches)} search${day.searches === 1 ? '' : 'es'}${day.zero ? `, ${fmt(day.zero)} zero-result` : ''}`
						}))}
					/>
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
						{:else if d.overview['30d'].clicks}
							<p class="text-body text-muted">Every recurring query led somewhere.</p>
						{:else}
							<!-- No clicks at all reads as "everything failed", which would be
							     wrong on the day the measurement ships. -->
							<p class="text-body text-muted">
								No opened results recorded yet — this fills in as readers use search.
							</p>
						{/if}
					</section>

				</div>

				<!-- Unanswered searches: the triage list. Open is the worklist (one row per
				     query and language); Handled and Wanted are the decisions made, with
				     what readers did since. -->
				<section class="mt-6 rounded-card border border-border bg-surface p-5">
					<div class="mb-1 flex flex-wrap items-center justify-between gap-3">
						<h2 class="text-h3">Unanswered searches · 30d</h2>
						<div class="flex flex-wrap gap-2" role="group" aria-label="Triage">
							{#each [['open', 'Open', openCount], ['handled', 'Handled', handled.length], ['wanted', 'Wanted', wanted.length]] as [key, label, n] (key)}
								<button
									type="button"
									class="rounded-full px-3 py-1 text-small {tab === key ? 'bg-accent-soft text-text' : 'text-muted hover:text-text'}"
									aria-pressed={tab === key}
									onclick={() => (tab = key as TriageTab)}>{label} <span class="tabular-nums">{n}</span></button
								>
							{/each}
						</div>
					</div>

					{#if tab === 'open'}
						<p class="mb-5 text-small text-muted">
							Searches that found nothing, by the language the reader was in. Check where else a
							query exists: if another language has it, queue a translation; if nothing does, mark
							it wanted. Each decision moves the query to Handled or Wanted.
						</p>
						{#if openCount === 0}
							<p class="text-body text-muted">
								{decided.length
									? 'Nothing open: every unanswered search has an outcome.'
									: 'No unanswered searches in the last 30 days.'}
							</p>
						{/if}
						<div class="space-y-6">
							{#each d.unanswered_by_language as lang (lang.code)}
								{@const rows = openQueries(lang)}
								{#if rows.length}
								<div>
									<h3 class="mb-2 text-body font-semibold text-text">
										{lang.name}
										<span class="text-small font-normal text-muted">
											{lang.code} · {fmt(lang.total)} unanswered searches
										</span>
									</h3>
									<ul class="space-y-1">
										{#each rows as q (q.query)}
											{@const gk = gapKey(lang.code, q.query)}
											{@const gap = gaps[gk]}
											{@const busy = deciding[gk]}
											<li class="border-t border-border py-2 first:border-t-0">
												<div class="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
													<span class="min-w-0 truncate text-body text-text">{q.query}</span>
													<span class="flex shrink-0 flex-wrap items-baseline gap-2">
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
														{#if canDecide(lang.code)}
															<button
																class="btn btn-sm btn-ghost"
																disabled={busy === 'busy'}
																onclick={() => decide(lang.code, q.query, 'wanted')}>Wanted</button
															>
															<button
																class="btn btn-sm btn-ghost"
																disabled={busy === 'busy'}
																onclick={() => decide(lang.code, q.query, 'out_of_scope')}>Out of scope</button
															>
														{/if}
													</span>
												</div>
												{#if q.reopened}
													<p class="mt-1 text-small text-danger">
														Reopened: {q.reopened.outcome_label.toLowerCase()}
														{shortDate(q.reopened.decided_at)}{q.reopened.target ? ` (${q.reopened.target})` : ''}, still
														{fmt(q.reopened.misses_since)} misses since.
													</p>
												{/if}
												{#if busy && busy !== 'busy'}
													<p class="mt-1 text-small text-warning">{busy}</p>
												{/if}
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
															No matches in any other language — nothing to translate from. Mark it wanted
															if it belongs in the library.
														</p>
													{/if}
													{#if gap.data.works.length}
														<ul class="mt-2 space-y-1 border-t border-border pt-2">
															{#each gap.data.works as w (w.type + ':' + w.slug)}
																{@const qk = queueKey(lang.code, w)}
																<li class="flex items-center justify-between gap-2">
																	<span class="min-w-0 truncate text-small">
																		<span class="text-text">{w.title}</span>
																		<span class="text-muted"> · {w.type}</span>
																	</span>
																	{#if queued[qk] === 'done'}
																		<span class="shrink-0 text-small text-accent">✓ queued</span>
																	{:else if queued[qk] && queued[qk] !== 'busy'}
																		<button
																			class="shrink-0 text-small text-warning hover:underline"
																			title={queued[qk]}
																			onclick={() => queueWork(lang.code, w, q.query)}>Retry</button
																		>
																	{:else if auth.isAdmin}
																		<button
																			class="btn btn-sm btn-ghost shrink-0"
																			disabled={queued[qk] === 'busy'}
																			onclick={() => queueWork(lang.code, w, q.query)}
																			>{queued[qk] === 'busy' ? 'Queueing…' : `Queue ${lang.name}`}</button
																		>
																	{/if}
																</li>
															{/each}
														</ul>
													{/if}
												{/if}
											</li>
										{/each}
									</ul>
								</div>
								{/if}
							{/each}
						</div>
					{:else}
						{@const rows = tab === 'handled' ? handled : wanted}
						<p class="mb-4 text-small text-muted">
							{tab === 'handled'
								? 'Queued translations and out-of-scope searches, with what readers did since. A translation that keeps finding nothing two weeks on goes back to Open.'
								: 'Searches for things the library doesn\'t have in any language, ranked by how often they\'ve been searched since: the import shopping list.'}
						</p>
						{#if decisions.error}
							<p class="text-body text-warning">{decisions.error}</p>
						{:else if decisions.loading && !decisions.data}
							<p class="text-body text-muted">Loading…</p>
						{:else if !rows.length}
							<p class="text-body text-muted">
								{tab === 'handled' ? 'Nothing handled yet.' : 'Nothing marked wanted yet.'}
							</p>
						{:else}
							<ul>
								{#each rows as row (row.language + row.query)}
									{@const busy = deciding[gapKey(row.language, row.query)]}
									<li class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-t border-border py-2.5 first:border-t-0">
										<div class="min-w-0">
											<span class="text-body text-text">{row.query}</span>
											<span class="ms-1 text-small text-muted">{row.language}</span>
											<div class="text-small text-muted">
												{row.outcome_label}{row.target ? ` · ${row.target}` : ''}{row.note ? ` · ${row.note}` : ''}
												· {shortDate(row.decided_at)}{row.decided_by ? ` by ${row.decided_by}` : ''}
											</div>
											{#if busy && busy !== 'busy'}
												<div class="text-small text-warning">{busy}</div>
											{/if}
										</div>
										<div class="flex shrink-0 items-baseline gap-3 text-small">
											{#if row.reopened}
												<span class="text-danger">Reopened · {fmt(row.misses_since)} misses since</span>
											{:else if row.outcome === 'wanted'}
												<span class="tabular-nums text-text">{fmt(row.misses_since)} searches since</span>
											{:else}
												<span class="tabular-nums text-muted"
													>{fmt(row.searches_since)} searches since · {fmt(row.misses_since)} found nothing</span
												>
											{/if}
											{#if canDecide(row.language)}
												<button
													class="btn btn-sm btn-ghost"
													disabled={busy === 'busy'}
													onclick={() => undo(row)}>{busy === 'busy' ? 'Undoing…' : 'Undo'}</button
												>
											{/if}
										</div>
									</li>
								{/each}
							</ul>
						{/if}
					{/if}
				</section>

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
