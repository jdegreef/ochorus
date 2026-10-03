<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { workPath } from '$lib/editionHref';
	import FunnelBars from '$lib/components/FunnelBars.svelte';
	import TrendChip from '$lib/components/TrendChip.svelte';
	import ColumnChart from '$lib/components/ColumnChart.svelte';
	import ReachSpark from '$lib/components/ReachSpark.svelte';
	import EventMarker from '$lib/components/EventMarker.svelte';
	import { adminEditionHref, EVENT_KINDS, eventKey, formatDuration, getAdminEngagement, periodTrend, type EngagementEvent, type EngagementKind, type EngagementTopRow, type Trend } from '$lib/library-admin';
	import { deltaWords, followingWeek, weeklySummary } from '$lib/engagementSummary';

	const engagement = adminResource(getAdminEngagement, 'Something went wrong loading engagement.');
	const data = $derived(engagement.data);

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number | null | undefined) => nf.format(n ?? 0);
	const weekLabel = (iso: string) =>
		new Date(iso + 'T00:00:00').toLocaleDateString('en', { month: 'short', day: 'numeric' });

	const weekMax = $derived(Math.max(1, ...(data?.weekly_active.map((w) => w.readers) ?? [1])));
	const langMax = $derived(Math.max(1, ...(data?.by_language.map((l) => l.readers) ?? [1])));
	const heartKindMax = $derived(Math.max(1, ...(data?.hearts_by_kind.map((h) => h.count) ?? [1])));

	// A FavoriteKind value → a readable plural ("book" → "Books"). The kinds are
	// a small fixed set from the server; anything unmapped is title-cased so a new
	// kind still reads sensibly.
	const kindLabels: Record<string, string> = {
		book: 'Books',
		author: 'Authors',
		sermon: 'Sermons',
		plan: 'Plans',
		topic: 'Topics',
		article: 'Articles',
		quote: 'Quotes'
	};
	const kindLabel = (k: string) => kindLabels[k] ?? k.charAt(0).toUpperCase() + k.slice(1);

	// Sparkline for the Active · 7d tile: the 8-week active series as one line, so
	// the trend behind the number reads at a glance. Built to a 100×28 viewBox.
	const sparkPoints = $derived.by(() => {
		const series = data?.weekly_active ?? [];
		if (series.length < 2) return '';
		const n = series.length - 1;
		return series
			.map((w, i) => `${(i / n) * 100},${26 - (w.readers / weekMax) * 24}`)
			.join(' ');
	});

	// Reading pulse — the headline figures, each with a plain-English sub and,
	// where there's a prior window to divide by, a week-over-week trend chip. The
	// active tile also carries the weekly sparkline (`spark`). Readers sits beside
	// Registered users so the accounts that never opened a chapter read as a gap.
	const cards = $derived<{ label: string; value: number; sub: string; trend: Trend; spark?: boolean }[]>(
		data
			? [
					{
						label: 'Active · 7d',
						value: data.overview.active_7d,
						sub: `${fmt(data.overview.active_1d)} today`,
						trend: periodTrend(data.overview.active_7d, data.overview.active_7d_prev),
						spark: true
					},
					{
						label: 'Active · 30d',
						value: data.overview.active_30d,
						sub: 'in the last month',
						trend: periodTrend(data.overview.active_30d, data.overview.active_30d_prev)
					},
					{
						label: 'Hearts',
						value: data.overview.hearts,
						sub: `${fmt(data.overview.hearts_7d)} this week`,
						trend: periodTrend(data.overview.hearts_7d, data.overview.hearts_7d_prev)
					},
					{ label: 'Readers', value: data.overview.readers, sub: 'with saved progress', trend: null },
					{ label: 'Registered users', value: data.overview.total_users, sub: 'accounts', trend: null },
					{ label: 'Marked chapters', value: data.overview.marked_chapters, sub: `${fmt(data.overview.readers_with_marks)} readers`, trend: null }
				]
			: []
	);

	// Every kind shares the slug column but not the namespace, so the row's
	// kind decides the path (a bare /books/<slug> 404s for anything else).
	const workHref = (w: { kind: EngagementKind; slug: string }) => workPath(w.kind, w.slug);

	// Top content — one tab per readable kind, each carrying its own top works.
	const topTabs: { key: EngagementKind; label: string }[] = [
		{ key: 'book', label: 'Books' },
		{ key: 'sermon', label: 'Sermons' },
		{ key: 'bio', label: 'Authors' },
		{ key: 'article', label: 'Articles' }
	];
	let topTab = $state<EngagementKind>('book');
	const topRows = $derived<EngagementTopRow[]>(data?.top_content[topTab] ?? []);
	// A "where readers stop" column for the kinds whose rows carry a curve
	// (books: the others are one document each).
	const hasReach = $derived(topRows.some((r) => r.reach !== undefined));
	const topTabLabel = $derived(topTabs.find((t) => t.key === topTab)?.label ?? '');
	const finishedPct = (b: EngagementTopRow) =>
		b.readers ? Math.round((b.finishers / b.readers) * 100) : 0;

	// A heatmap cell's gold wash, scaled to the busiest chapter so the strip's
	// contrast is about this book, not an absolute count. Unmarked chapters stay
	// at the recessed surface tone.
	const heatColor = (readers: number) => {
		const peak = data?.highlight_heatmap?.peak_readers ?? 0;
		const pct = peak ? Math.round((readers / peak) * 82) : 0;
		return `color-mix(in srgb, var(--gold) ${pct}%, var(--surface-2))`;
	};

	// The opening sentence: the last 7 days in words, plus this week's events.
	const summary = $derived(data ? weeklySummary(data, workHref) : null);
	let copied = $state('');
	async function copySummary() {
		if (!summary) return;
		try {
			await navigator.clipboard.writeText(summary.text);
			copied = 'Copied';
		} catch {
			copied = 'Couldn’t copy; select the sentence instead';
		}
	}

	// What the team did, under the weekly chart: each week's events, and the
	// one being pointed at, named in the line under the chart.
	const eventsByWeek = $derived.by(() => {
		const byWeek = new Map<string, EngagementEvent[]>();
		for (const e of data?.events ?? []) {
			const list = byWeek.get(e.week);
			if (list) list.push(e);
			else byWeek.set(e.week, [e]);
		}
		return byWeek;
	});
	const after = (week: string) => followingWeek(data?.weekly_active ?? [], week);
	let pointed = $state<EngagementEvent | null>(null);

	const planSteps = $derived(
		data
			? [
					{ label: 'Started', count: data.plan_funnel.started },
					{ label: 'Came back', count: data.plan_funnel.returned },
					{ label: 'Completed', count: data.plan_funnel.completed }
				]
			: []
	);
</script>

<svelte:head><title>Admin · Engagement — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-5xl px-5 py-10">
	<header class="mb-6 flex flex-wrap items-end justify-between gap-3">
		<div>
			<p class="eyebrow mb-2 text-accent">Admin</p>
			<h1 class="text-h1">Engagement</h1>
			<p class="mt-2 max-w-prose text-body text-muted">
				What readers are reading, marking, and loving — aggregate counts only, no personal data.
			</p>
			<span class="privacy-badge mt-3 inline-flex items-center gap-2 text-small text-muted">
				<span class="privacy-dot" aria-hidden="true"></span>
				Aggregate only · no individual readers
			</span>
		</div>
		{#if data}
			<button class="btn btn-ghost btn-sm" onclick={engagement.load} disabled={engagement.loading}
				>{engagement.loading ? 'Refreshing…' : 'Refresh'}</button
			>
		{/if}
	</header>

	<AdminGate resource={engagement} errorTitle="Couldn't load engagement">
		{#snippet children(d)}
			{#if d.overview.readers === 0}
				<div class="rounded-card border border-border bg-surface p-8 text-center">
					<p class="text-h3">No reading activity yet</p>
					<p class="mt-1 text-body text-muted">Once signed-in readers start reading, their (anonymous, aggregate) activity shows up here.</p>
				</div>
			{:else}
				<!-- This week in one sentence (built from the numbers below). -->
				{#if summary}
					<section class="mb-6 rounded-card border border-border bg-surface p-5">
						<div class="flex flex-wrap items-start justify-between gap-3">
							<p class="max-w-prose font-serif text-h3 leading-snug text-text">
								{#each summary.parts as part, i (i)}{#if part.href}<a href={part.href} class="text-accent underline decoration-1 underline-offset-4">{part.text}</a>{:else if part.strong}<strong>{part.text}</strong>{:else}{part.text}{/if}{/each}
							</p>
							<span class="flex shrink-0 items-center gap-2">
								{#if copied}<span class="text-micro text-muted" aria-live="polite">{copied}</span>{/if}
								<button class="btn btn-ghost btn-sm" onclick={copySummary}>Copy summary</button>
							</span>
						</div>
						{#each summary.events as e (eventKey(e))}
							<p class="mt-3 flex items-center gap-2 rounded-card bg-surface-2 px-3 py-2 text-small text-muted">
								<EventMarker kind={e.kind} />
								<span>This week: <span class="font-semibold text-text">{e.title}</span>, {e.detail}.</span>
							</p>
						{/each}
					</section>
				{/if}

				<!-- Reading pulse -->
				<p class="section-label">Reading pulse</p>
				<!-- Three across at most: at six the tiles were too narrow for a label and
				     its chip on one line, so "Active · 7d" broke at the dot. -->
				<section class="grid grid-cols-2 gap-3 sm:grid-cols-3">
					{#each cards as c (c.label)}
						<div class="rounded-card border border-border bg-surface p-4">
							<div class="flex items-start justify-between gap-2">
								<div class="stat-number">{fmt(c.value)}</div>
								{#if c.spark && sparkPoints}
									<svg class="spark" viewBox="0 0 100 28" preserveAspectRatio="none" aria-hidden="true">
										<polyline points={sparkPoints} />
									</svg>
								{/if}
							</div>
							<div class="mt-2 flex items-center gap-2">
								<span class="whitespace-nowrap text-small font-semibold text-text">{c.label}</span>
								<TrendChip trend={c.trend} />
							</div>
							<div class="text-small text-muted">{c.sub}</div>
						</div>
					{/each}
				</section>

				{#if d.overview.readers < 20}
					<p class="mt-3 text-micro text-muted">
						Early data — only {fmt(d.overview.readers)} reader{d.overview.readers === 1 ? '' : 's'} so far. Read the charts below as directional, not statistically firm.
					</p>
				{/if}

				<!-- Reading time (from sittings) -->
				{#if d.time.sessions}
					<section class="mt-8 rounded-card border border-border bg-surface p-5">
						<div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
							<h2 class="text-h3">Reading time</h2>
							<span class="text-small text-muted">Active reading — foreground, non-idle — not tab-open time.</span>
						</div>
						<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
							{#each [
								{ label: 'Total time', text: formatDuration(d.time.total_seconds), sub: `${fmt(d.time.sessions)} sittings` },
								{ label: 'Avg sitting', text: formatDuration(d.time.avg_session_seconds), sub: `${fmt(d.time.readers)} readers` },
								{ label: 'Last 7 days', text: formatDuration(d.time.seconds_7d), sub: `${fmt(d.time.readers_7d)} readers` },
								{ label: 'Last 30 days', text: formatDuration(d.time.seconds_30d), sub: `${fmt(d.time.readers_30d)} readers` }
							] as c (c.label)}
								<div class="rounded-card bg-surface-2 p-4">
									<div class="stat-number">{c.text}</div>
									<div class="mt-2 text-small font-semibold text-text">{c.label}</div>
									<div class="text-small text-muted">{c.sub}</div>
								</div>
							{/each}
						</div>
					</section>
				{/if}

				<!-- Weekly active -->
				<section class="mt-8 rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3 mb-4">Weekly active readers</h2>
					<ColumnChart
						columns={d.weekly_active.map((w, i) => ({
							key: w.week,
							label: weekLabel(w.week),
							value: w.readers,
							current: i === d.weekly_active.length - 1,
							title: `Week of ${weekLabel(w.week)} · ${fmt(w.readers)} reader${w.readers === 1 ? '' : 's'}`
						}))}
					>
						{#snippet foot(col)}
							<!-- What happened that week, under its bar (wide screens; the list
							     below carries the same events on a phone). -->
							<div class="hidden h-5 items-center justify-center gap-1 sm:flex">
								{#each eventsByWeek.get(col.key) ?? [] as e (eventKey(e))}
									<EventMarker kind={e.kind} label="{e.title}, {e.detail}" active={pointed === e} onpoint={() => (pointed = e)} />
								{/each}
							</div>
						{/snippet}
					</ColumnChart>
					{#if d.events.length}
						<p class="mt-2 hidden min-h-[2.6em] text-small text-muted sm:block" aria-live="polite">
							{#if pointed}
								{@const n = after(pointed.week)}
								<span class="font-semibold text-text">{pointed.title}</span> · {weekLabel(pointed.date)} · {pointed.detail}{#if n}<br />Readers the next week: {fmt(n.readers)} ({deltaWords(n.delta)}){/if}
							{:else}
								Hover or tap a marker to see what happened that week.
							{/if}
						</p>
						<ul class="mt-3 divide-y divide-border border-t border-border sm:hidden">
							{#each d.events.toReversed() as e (eventKey(e))}
								{@const n = after(e.week)}
								<li class="flex items-center gap-2 py-2 text-small">
									<span class="w-12 shrink-0 tabular-nums text-muted">{weekLabel(e.date)}</span>
									<EventMarker kind={e.kind} />
									<span class="min-w-0 flex-1"><span class="font-semibold text-text">{e.title}</span> <span class="text-muted">{e.detail}</span></span>
									<span class="shrink-0 tabular-nums text-muted">{n ? `${deltaWords(n.delta)} next week` : 'this week'}</span>
								</li>
							{/each}
						</ul>
					{/if}
					<p class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-micro text-muted">
						<span>The last bar is this week so far.</span>
						{#each Object.entries(EVENT_KINDS) as [k, { label }] (k)}
							{#if d.events.some((e) => e.kind === k)}
								<span class="inline-flex items-center gap-1.5"><EventMarker kind={k as EngagementEvent['kind']} small />{label}</span>
							{/if}
						{/each}
					</p>
				</section>

				<!-- Rising this week — biggest gain in weekly readers -->
				{#if d.rising.length}
					<section class="mt-8 rounded-card border border-border bg-surface p-5">
						<div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
							<h2 class="text-h3">Rising this week</h2>
							<span class="text-small text-muted">Biggest gain in weekly readers vs last week — what's catching on now.</span>
						</div>
						<ul class="space-y-2">
							{#each d.rising as b (`${b.kind}:${b.slug}`)}
								<li class="flex items-baseline justify-between gap-3">
									<a href={workHref(b)} class="min-w-0 truncate text-body text-text hover:text-accent">
										{b.title}{#if b.author}<span class="text-small text-muted"> · {b.author}</span>{/if}
									</a>
									<span class="shrink-0 text-small tabular-nums text-muted">
										<span class="font-semibold text-text">{fmt(b.this_week)}</span> this week
										<span class="ms-2 font-semibold text-accent">↑ {fmt(b.delta)}</span>
									</span>
								</li>
							{/each}
						</ul>
					</section>
				{/if}

				<!-- Top content — reach vs depth, by kind -->
				<section class="mt-8 rounded-card border border-border bg-surface p-5">
					<div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
						<h2 class="text-h3">Top content</h2>
						<span class="text-small text-muted">An open isn't a read — reach and depth side by side.</span>
					</div>
					<div class="seg mb-4" role="tablist" aria-label="Content type">
						{#each topTabs as t (t.key)}
							<button
								role="tab"
								aria-selected={topTab === t.key}
								class={topTab === t.key ? 'active' : ''}
								onclick={() => (topTab = t.key)}>{t.label}</button
							>
						{/each}
					</div>
					{#if topRows.length}
						<div class="overflow-x-auto">
							<table class="w-full">
								<thead>
									<tr class="text-micro uppercase tracking-wide text-muted">
										<th class="py-2 pe-3 text-start font-semibold">Title</th>
										<th class="px-3 py-2 text-end font-semibold">Readers</th>
										<th class="px-3 py-2 text-end font-semibold">Finished</th>
										{#if hasReach}<th class="px-3 py-2 text-start font-semibold">Where readers stop</th>{/if}
										<th class="px-3 py-2 text-end font-semibold">Hearts</th>
										<th class="ps-3 py-2 text-end font-semibold">Highlighted</th>
									</tr>
								</thead>
								<tbody>
									{#each topRows as b (`${b.kind}:${b.slug}`)}
										<tr class="border-t border-border">
											<td class="max-w-0 py-2 pe-3" class:min-w-48={hasReach}>
												<a href={workHref(b)} class="block truncate text-body text-text hover:text-accent">
													{b.title}{#if b.author}<span class="text-small text-muted"> · {b.author}</span>{/if}
												</a>
											</td>
											<td class="px-3 py-2 text-end tabular-nums">{fmt(b.readers)}</td>
											<td class="px-3 py-2">
												<div class="ms-auto flex w-32 items-center gap-2">
													<div class="depthbar" title="{fmt(b.finishers)} of {fmt(b.readers)} finished">
														<span style="width: {finishedPct(b)}%"></span>
													</div>
													<span class="w-9 shrink-0 text-end text-micro text-muted tabular-nums">{finishedPct(b)}%</span>
												</div>
											</td>
											{#if hasReach}
												<td class="px-3 py-2">
													{#if b.reach}
														<!-- The full chart, with chapter lengths and flags, is on the book's admin page. -->
														<a href={adminEditionHref(b.slug, b.reach.language)} class="block w-fit hover:opacity-80">
															<ReachSpark reach={b.reach} />
														</a>
													{:else}
														<span class="text-micro text-muted">—</span>
													{/if}
												</td>
											{/if}
											<td class="px-3 py-2 text-end tabular-nums">{fmt(b.hearts)}</td>
											<td class="ps-3 py-2 text-end tabular-nums">{fmt(b.highlighters)}</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{:else}
						<p class="mt-3 text-body text-muted">No {topTabLabel.toLowerCase()} activity yet.</p>
					{/if}
				</section>

				<!-- Highlight heatmap — where readers mark up the most-marked book -->
				{#if d.highlight_heatmap && d.highlight_heatmap.chapters.length}
					{@const hm = d.highlight_heatmap}
					<section class="mt-6 rounded-card border border-border bg-surface p-5">
						<div class="mb-1 flex flex-wrap items-baseline justify-between gap-2">
							<h2 class="text-h3">Where readers mark up</h2>
							<span class="text-small text-muted">Highlight density by chapter</span>
						</div>
						<p class="mb-3 text-small text-muted">
							<a href="/books/{hm.slug}" class="text-text hover:text-accent">{hm.title}</a>{#if hm.author}<span> · {hm.author}</span>{/if} — the most-marked book.
						</p>
						<div class="heatstrip">
							{#each hm.chapters as c (c.chapter)}
								<div
									class="heatcell"
									style="background: {heatColor(c.readers)}"
									title="Chapter {c.chapter} · {fmt(c.readers)} reader{c.readers === 1 ? '' : 's'} highlighted"
								></div>
							{/each}
						</div>
						<div class="mt-3 flex flex-wrap items-center justify-between gap-2 text-small text-muted">
							<span class="flex items-center gap-2">
								Fewer
								<span class="heatkey" style="background: color-mix(in srgb, var(--gold) 15%, var(--surface-2))"></span>
								<span class="heatkey" style="background: color-mix(in srgb, var(--gold) 45%, var(--surface-2))"></span>
								<span class="heatkey" style="background: color-mix(in srgb, var(--gold) 82%, var(--surface-2))"></span>
								more highlighted
							</span>
							{#if hm.peak_chapter}
								<span>Peak · chapter {hm.peak_chapter} · <span class="font-semibold text-text tabular-nums">{fmt(hm.peak_readers)}</span> readers</span>
							{/if}
						</div>
					</section>
				{/if}

				<!-- Hearts: most loved + saved by kind -->
				{#if d.overview.hearts}
					<div class="mt-6 grid gap-6 lg:grid-cols-2">
						<section class="rounded-card border border-border bg-surface p-5">
							<h2 class="text-h3 mb-1">Most loved</h2>
							<p class="mb-3 text-small text-muted">The works readers hearted most — books, sermons and authors.</p>
							{#if d.most_loved.length}
								<ul class="space-y-2">
									{#each d.most_loved as b (`${b.kind}:${b.slug}`)}
										<li class="flex items-baseline justify-between gap-3">
											<a href={workHref(b)} class="min-w-0 truncate text-body text-text hover:text-accent">
												{b.title}{#if b.author}<span class="text-small text-muted"> · {b.author}</span>{/if}
											</a>
											<span class="shrink-0 text-small tabular-nums text-muted">
												<span class="font-semibold text-text">{fmt(b.hearts)}</span> <span class="text-accent" aria-hidden="true">♥</span>
											</span>
										</li>
									{/each}
								</ul>
							{:else}
								<p class="text-body text-muted">No hearts on readable works yet.</p>
							{/if}
						</section>

						<section class="rounded-card border border-border bg-surface p-5">
							<h2 class="text-h3 mb-1">Saved by kind</h2>
							<p class="mb-3 text-small text-muted">Readers save more than they read — authors, plans, topics and quotes too.</p>
							<ul class="space-y-2">
								{#each d.hearts_by_kind as h (h.kind)}
									<li class="flex items-center gap-3">
										<span class="w-20 shrink-0 truncate text-body text-text">{kindLabel(h.kind)}</span>
										<div class="h-3 flex-1 overflow-hidden rounded-full bg-surface-2">
											<div class="h-full rounded-full bg-accent-soft" style="width: {(h.count / heartKindMax) * 100}%"></div>
										</div>
										<span class="w-10 shrink-0 text-right text-small tabular-nums text-muted">{fmt(h.count)}</span>
									</li>
								{/each}
							</ul>
						</section>
					</div>
				{/if}

				<!-- Reading plans: funnel + per-plan -->
				{#if d.plan_funnel.started}
					<section class="mt-6 rounded-card border border-border bg-surface p-5">
						<div class="mb-4 flex flex-wrap items-baseline justify-between gap-2">
							<h2 class="text-h3">Reading plans</h2>
							<span class="text-small text-muted">Plans live or die on retention — where readers drop off.</span>
						</div>
						<FunnelBars steps={planSteps} />
						{#if d.plan_funnel.by_plan.length}
							<div class="mt-5 overflow-x-auto">
								<table class="w-full">
									<thead>
										<tr class="text-micro uppercase tracking-wide text-muted">
											<th class="py-2 pe-3 text-start font-semibold">Plan</th>
											<th class="px-3 py-2 text-end font-semibold">Started</th>
											<th class="px-3 py-2 text-end font-semibold">Came back</th>
											<th class="px-3 py-2 text-end font-semibold">Completed</th>
											<th class="ps-3 py-2 text-end font-semibold">Completion</th>
										</tr>
									</thead>
									<tbody>
										{#each d.plan_funnel.by_plan as p (p.slug)}
											<tr class="border-t border-border">
												<td class="max-w-0 py-2 pe-3">
													<a href="/plans/{p.slug}" class="block truncate text-body text-text hover:text-accent">{p.title}</a>
												</td>
												<td class="px-3 py-2 text-end tabular-nums">{fmt(p.started)}</td>
												<td class="px-3 py-2 text-end tabular-nums">{fmt(p.returned)}</td>
												<td class="px-3 py-2 text-end tabular-nums">{fmt(p.completed)}</td>
												<td class="ps-3 py-2 text-end tabular-nums text-muted">{p.started ? Math.round((p.completed / p.started) * 100) : 0}%</td>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
						{/if}
					</section>
				{/if}

				<!-- By language -->
				<section class="mt-6 rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3 mb-3">Readers by language</h2>
					<ul class="space-y-2">
						{#each d.by_language as l (l.code)}
							<li class="flex items-center gap-3">
								<span class="w-28 shrink-0 truncate text-body text-text">{l.name} <span class="text-small text-muted">{l.code}</span></span>
								<div class="h-3 flex-1 overflow-hidden rounded-full bg-surface-2">
									<div class="h-full rounded-full bg-accent-soft" style="width: {(l.readers / langMax) * 100}%"></div>
								</div>
								<span class="w-10 shrink-0 text-right text-small tabular-nums text-muted">{fmt(l.readers)}</span>
							</li>
						{/each}
					</ul>
				</section>
			{/if}
		{/snippet}
	</AdminGate>
</div>

<style>
	/* Privacy badge — a persistent reminder that this page is aggregate-only,
	   dressed as a quiet feature rather than fine print. */
	.privacy-badge {
		border: 1px solid var(--border);
		border-radius: 999px;
		background: var(--surface);
		padding: 0.3rem 0.7rem;
	}
	.privacy-dot {
		width: 7px;
		height: 7px;
		border-radius: 999px;
		background: var(--accent);
	}

	/* Reading-pulse sparkline — the 8-week active line behind the number. */
	.spark {
		width: 68px;
		height: 26px;
		flex-shrink: 0;
	}
	.spark polyline {
		fill: none;
		stroke: var(--accent);
		stroke-width: 1.6;
		stroke-linecap: round;
		stroke-linejoin: round;
		vector-effect: non-scaling-stroke;
	}

	/* Highlight heatmap — one gold cell per chapter, wrapping across the width.
	   Gold is the reading-mark colour (STYLE_GUIDE §5); 2px corners keep the
	   small cells square rather than rounding to dots. */
	.heatstrip {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(14px, 1fr));
		gap: 4px;
	}
	.heatcell {
		aspect-ratio: 1;
		border-radius: 2px;
		border: 1px solid var(--border);
	}
	.heatkey {
		display: inline-block;
		width: 14px;
		height: 14px;
		border-radius: 2px;
		border: 1px solid var(--border);
	}

	/* Completion bar under a most-read book: how far readers got. */
	.depthbar {
		flex: 1;
		height: 6px;
		border-radius: 999px;
		background: var(--surface-2);
		overflow: hidden;
		border: 1px solid var(--border);
	}
	.depthbar span {
		display: block;
		height: 100%;
		background: var(--accent);
	}
</style>
