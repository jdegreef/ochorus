<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { workPath } from '$lib/editionHref';
	import FunnelBars from '$lib/components/FunnelBars.svelte';
	import TrendChip from '$lib/components/TrendChip.svelte';
	import ColumnChart from '$lib/components/ColumnChart.svelte';
	import ReachSpark from '$lib/components/ReachSpark.svelte';
	import Sparkline from '$lib/components/Sparkline.svelte';
	import SectionBar from '$lib/components/SectionBar.svelte';
	import EventMarker from '$lib/components/EventMarker.svelte';
	import { adminEditionHref, DEEP_SITTING_SECONDS, EVENT_KINDS, formatDuration, getAdminEngagement, periodTrend, sittingBucketLabel, type EngagementEvent, type EngagementKind, type EngagementTopRow, type Trend } from '$lib/library-admin';
	import { followingWeek, weeklySummary } from '$lib/engagementSummary';
	import { columnShares, headline, HEADLINE_WEEK, share } from '$lib/engagementCohorts';
	import { busiestCell, hourLabel, sendTime, WEEKDAYS } from '$lib/engagementHours';

	const engagement = adminResource(getAdminEngagement, 'Something went wrong loading engagement.');
	const data = $derived(engagement.data);

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number | null | undefined) => nf.format(n ?? 0);
	const weekLabel = (iso: string) =>
		new Date(iso + 'T00:00:00').toLocaleDateString('en', { month: 'short', day: 'numeric' });

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

	// Each tile's line. Two shapes, on purpose: the weekly chart's 8 calendar
	// weeks (this week last, dashed as in progress) for tiles whose sub-line
	// talks in weeks, and six rolling 30-day windows for the 30-day tile, so
	// its last point is the window its number counts. Marked chapters has no
	// line: marks keep no record of when each was made.
	type Line = { values: number[]; labels: string[]; name: string; partial: boolean };
	const weekLabels = $derived(data?.weekly_active.map((w) => `week of ${weekLabel(w.week)}`) ?? []);
	const weekly = (values: number[] | undefined, name: string): Line | undefined =>
		values?.length ? { values, labels: weekLabels, name, partial: true } : undefined;
	/** What a running total gained this calendar week (the line's last step). */
	const gained = (total: number[] | undefined) => (total && total.length > 1 ? total[total.length - 1] - total[total.length - 2] : 0);

	// Reading pulse — the headline figures, each with a plain-English sub, a
	// week-over-week trend chip where there's a prior window to divide by, and
	// its line. Readers sits beside Registered users so the accounts that never
	// opened a chapter read as a gap.
	const cards = $derived<{ label: string; value: number; sub: string; trend: Trend; line?: Line }[]>(
		data
			? [
					{
						label: 'Active · 7d',
						value: data.overview.active_7d,
						sub: `${fmt(data.overview.active_1d)} today`,
						trend: periodTrend(data.overview.active_7d, data.overview.active_7d_prev),
						line: weekly(data.weekly_active.map((w) => w.readers), 'Readers active per week')
					},
					{
						label: 'Active · 30d',
						value: data.overview.active_30d,
						sub: 'in the last month',
						trend: periodTrend(data.overview.active_30d, data.overview.active_30d_prev),
						line: data.trends ? {
							values: data.trends.active_30d.map((w) => w.readers),
							labels: data.trends.active_30d.map((w) => `30 days to ${weekLabel(w.end)}`),
							name: 'Readers per 30 days',
							partial: false
						} : undefined
					},
					{
						label: 'Hearts',
						value: data.overview.hearts,
						sub: `${fmt(data.overview.hearts_7d)} this week`,
						trend: periodTrend(data.overview.hearts_7d, data.overview.hearts_7d_prev),
						line: weekly(data.trends?.hearts, 'Hearts saved per week')
					},
					{
						label: 'Readers',
						value: data.overview.readers,
						sub: gained(data.trends?.readers) ? `+${fmt(gained(data.trends?.readers))} since Monday` : 'with saved progress',
						trend: null,
						line: weekly(data.trends?.readers, 'Readers, running total')
					},
					{
						label: 'Registered users',
						value: data.overview.total_users,
						sub: gained(data.trends?.users) ? `+${fmt(gained(data.trends?.users))} since Monday` : 'accounts',
						trend: null,
						line: weekly(data.trends?.users, 'Registered users, running total')
					},
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
	// The page's gold wash: 0–100% of a scale onto 0–82% gold, so the darkest
	// cell still carries text. Shared by the marks heatmap and the cohort grid.
	const goldWash = (pct: number) => `color-mix(in srgb, var(--gold) ${Math.round(pct * 0.82)}%, var(--surface-2))`;
	const heatColor = (readers: number) => {
		const peak = data?.highlight_heatmap?.peak_readers ?? 0;
		return goldWash(peak ? (readers / peak) * 100 : 0);
	};

	// Retention cohorts: one column per week after joining, as far as the
	// oldest shown cohort reaches.
	const cohorts = $derived(data?.cohorts?.rows ?? []);
	const cohortFloor = $derived(data?.cohorts?.min_size ?? 0);
	const cohortSpan = $derived(Math.max(0, ...cohorts.map((c) => c.active?.length ?? 0)));
	const cohortCols = $derived(columnShares(cohorts, cohortSpan));
	const cohortHead = $derived(headline(cohorts));

	// When people read: the grid shows once any hour clears the readers floor.
	const hours = $derived(data?.hours);
	const hoursShown = $derived(!!hours?.minutes.some((row) => row.some((m) => m != null)));
	const hoursMax = $derived(Math.max(1, ...(hours?.minutes.flat().map((m) => m ?? 0) ?? [1])));
	const hoursPeak = $derived(hours ? busiestCell(hours.minutes) : null);
	const hoursSend = $derived(hours ? sendTime(hours.minutes) : null);
	let pointedHour = $state<{ day: number; hour: number } | null>(null);
	// One tab stop for the whole grid; arrow keys move it (the ARIA grid
	// pattern), so 168 hours aren't 168 presses of Tab.
	let hourFocus = $state({ day: 0, hour: 0 });
	let hoursGrid = $state<HTMLElement>();
	const moveHour = (e: KeyboardEvent) => {
		const step: Record<string, [number, number]> = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] };
		const d = step[e.key];
		if (!d) return;
		e.preventDefault();
		hourFocus = { day: Math.min(6, Math.max(0, hourFocus.day + d[0])), hour: Math.min(23, Math.max(0, hourFocus.hour + d[1])) };
		hoursGrid?.querySelector<HTMLElement>(`[data-cell="${hourFocus.day}-${hourFocus.hour}"]`)?.focus();
	};
	const hourText = (day: number, hour: number) => {
		const m = hours?.minutes[day][hour];
		const span = `${WEEKDAYS[day]} ${hourLabel(hour)}–${hourLabel((hour + 1) % 24)}`;
		return m == null ? `${span}: fewer than ${hours?.min_readers} readers, left blank` : `${span}: ${fmt(m)} minutes read`;
	};

	// Sitting lengths: count sittings, or the minutes read in them. The second
	// shows where the reading actually happens.
	let lengthBy = $state<'sittings' | 'seconds'>('sittings');
	const deep = $derived.by(() => {
		const t = data?.time;
		if (!t?.lengths) return null;
		const n = t.lengths.filter((b) => b.min_seconds >= DEEP_SITTING_SECONDS).reduce((a, b) => a + b[lengthBy], 0);
		const total = lengthBy === 'sittings' ? t.sessions : t.total_seconds;
		return { n, pct: total ? Math.round((n / total) * 100) : 0 };
	});

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
		for (const e of events) {
			const list = byWeek.get(e.week);
			if (list) list.push(e);
			else byWeek.set(e.week, [e]);
		}
		return byWeek;
	});
	const events = $derived(data?.events ?? []);
	const after = (week: string) => followingWeek(data?.weekly_active ?? [], week);
	let pointed = $state<EngagementEvent | null>(null);

	// The section bar: one link per section the page is showing, in page order.
	// Sections that hide themselves when empty drop out of the bar too.
	const sections = $derived(
		data && data.overview.readers
			? [
					summary && { id: 'this-week', label: 'This week' },
					{ id: 'pulse', label: 'Pulse' },
					data.time.sessions && { id: 'reading-time', label: 'Reading time' },
					hoursShown && { id: 'hours', label: 'When people read' },
					{ id: 'weekly', label: 'Weekly readers' },
					cohortSpan && { id: 'cohorts', label: 'Do readers stay?' },
					data.rising.length && { id: 'rising', label: 'Rising' },
					{ id: 'top-content', label: 'Top content' },
					data.highlight_heatmap?.chapters.length && { id: 'marks', label: 'Where readers mark' },
					data.overview.hearts && { id: 'loved', label: 'Most loved' },
					data.plan_funnel.started && { id: 'plans', label: 'Plans' },
					{ id: 'languages', label: 'By language' }
				].filter((s): s is { id: string; label: string } => !!s)
			: []
	);

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
				<SectionBar {sections} />

				<!-- This week in one sentence (built from the numbers below). -->
				{#if summary}
					<section id="this-week" class="anchor mb-6 rounded-card border border-border bg-surface p-5">
						<div class="flex flex-wrap items-start justify-between gap-3">
							<p class="max-w-prose font-serif text-h3 leading-snug text-text">
								{#each summary.parts as part, i (i)}{#if part.href}<a href={part.href} class="text-accent underline decoration-1 underline-offset-4">{part.text}</a>{:else if part.strong}<strong>{part.text}</strong>{:else}{part.text}{/if}{/each}
							</p>
							<span class="flex shrink-0 items-center gap-2">
								{#if copied}<span class="text-micro text-muted" aria-live="polite">{copied}</span>{/if}
								<button class="btn btn-ghost btn-sm" onclick={copySummary}>Copy summary</button>
							</span>
						</div>
						{#each summary.events as e (e.id)}
							<p class="mt-3 flex items-center gap-2 rounded-card bg-surface-2 px-3 py-2 text-small text-muted">
								<EventMarker kind={e.kind} />
								<span>This week: <span class="font-semibold text-text">{e.title}</span>, {e.detail}.</span>
							</p>
						{/each}
					</section>
				{/if}

				<!-- Reading pulse -->
				<p id="pulse" class="anchor section-label">Reading pulse</p>
				<!-- Three across at most: at six the tiles were too narrow for a label and
				     its chip on one line, so "Active · 7d" broke at the dot. -->
				<section class="grid grid-cols-2 gap-3 sm:grid-cols-3">
					{#each cards as c (c.label)}
						<div class="rounded-card border border-border bg-surface p-4">
							<div class="flex items-start justify-between gap-2">
								<div class="stat-number">{fmt(c.value)}</div>
								{#if c.line}<Sparkline {...c.line} />{/if}
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
					<section id="reading-time" class="anchor mt-8 rounded-card border border-border bg-surface p-5">
						<div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
							<h2 class="text-h3">Reading time</h2>
							<span class="text-small text-muted">Active reading — foreground, non-idle — not tab-open time.</span>
						</div>
						<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
							{#each [
								{ label: 'Total time', text: formatDuration(d.time.total_seconds), sub: `${fmt(d.time.sessions)} sittings · ${fmt(d.time.readers)} readers`, line: undefined },
								{ label: 'Typical sitting', text: formatDuration(d.time.median_session_seconds, { precise: true }), sub: `median · average ${formatDuration(d.time.avg_session_seconds, { precise: true })}`, line: undefined },
								{ label: 'Last 7 days', text: formatDuration(d.time.seconds_7d), sub: `${fmt(d.time.readers_7d)} readers`, line: weekly(d.trends?.reading_seconds, 'Reading time per week') },
								{ label: 'Last 30 days', text: formatDuration(d.time.seconds_30d), sub: `${fmt(d.time.readers_30d)} readers`, line: undefined }
							] as c (c.label)}
								<div class="rounded-card bg-surface-2 p-4">
									<div class="flex items-start justify-between gap-2">
										<div class="stat-number">{c.text}</div>
										{#if c.line}<Sparkline {...c.line} format={formatDuration} />{/if}
									</div>
									<div class="mt-2 text-small font-semibold text-text">{c.label}</div>
									<div class="text-small text-muted">{c.sub}</div>
								</div>
							{/each}
						</div>
						{#if d.time.lengths?.length}
							<!-- How long sittings are: the spread the average hides. -->
							<div class="mt-5">
								<div class="mb-3 flex flex-wrap items-center justify-between gap-2">
									<h3 class="text-small font-semibold text-text">How long sittings are</h3>
									<div class="seg" role="group" aria-label="Measure sittings by">
										{#each [{ key: 'sittings', label: 'Sittings' }, { key: 'seconds', label: 'Minutes read' }] as const as m (m.key)}
											<button aria-pressed={lengthBy === m.key} class={lengthBy === m.key ? 'active' : ''} onclick={() => (lengthBy = m.key)}>{m.label}</button>
										{/each}
									</div>
								</div>
								<ColumnChart
									height="7rem"
									columns={d.time.lengths.map((b) => {
										const label = sittingBucketLabel(b);
										return {
											key: String(b.min_seconds),
											label,
											// Tenths of a minute, so a bucket holding a few seconds still draws.
											value: lengthBy === 'sittings' ? b.sittings : Math.round(b.seconds / 6) / 10,
											title: `${label} · ${fmt(b.sittings)} sitting${b.sittings === 1 ? '' : 's'}, ${formatDuration(b.seconds, { precise: true })} read`
										};
									})}
								/>
								{#if deep}
									<p class="mt-2 text-small text-muted" aria-live="polite">
										{DEEP_SITTING_SECONDS / 60} minutes or longer:
										<span class="font-semibold text-text"
											>{lengthBy === 'sittings' ? `${fmt(deep.n)} sitting${deep.n === 1 ? '' : 's'}` : formatDuration(deep.n)}</span
										>
										({deep.pct}% of {lengthBy === 'sittings' ? 'sittings' : 'all reading time'}).
									</p>
								{/if}
							</div>
						{/if}
					</section>
				{/if}

				<!-- When people read: weekday × hour, on each reader's own clock -->
				{#if hours && hoursShown}
					<section id="hours" class="anchor mt-8 rounded-card border border-border bg-surface p-5">
						<div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
							<h2 class="text-h3">When people read</h2>
							<span class="text-small text-muted">Minutes read by weekday and hour, in each reader's own time zone · {fmt(hours.readers)} readers · last {hours.days} days.</span>
						</div>
						{#if hoursPeak && hoursSend}
							<div class="mb-4 flex flex-wrap gap-6">
								<div>
									<div class="stat-number">{WEEKDAYS[hoursPeak.day]} {hourLabel(hoursPeak.hour)}</div>
									<div class="text-small text-muted">busiest hour</div>
								</div>
								<div>
									<div class="stat-number">≈ {hoursSend.label}</div>
									<div class="text-small text-muted">to send, reader-local: just before {hourLabel(hoursSend.hour)}, the week's peak hour</div>
								</div>
							</div>
						{/if}
						<div class="overflow-x-auto">
							<div class="hours" role="grid" tabindex="-1" aria-label="Minutes read by weekday and hour" bind:this={hoursGrid} onkeydown={moveHour}>
								<div role="row" class="contents">
									<span></span>
									{#each Array.from({ length: 24 }, (_, h) => h) as h (h)}
										<span role="columnheader" class="text-center text-micro text-muted">{h % 6 === 0 ? hourLabel(h) : ''}</span>
									{/each}
								</div>
								{#each hours.minutes as row, day (day)}
									<div role="row" class="contents">
										<span role="rowheader" class="self-center text-micro text-muted">{WEEKDAYS[day]}</span>
										{#each row as m, hour (hour)}
											<button
												type="button"
												role="gridcell"
												class="cell"
												class:blank={m == null}
												style={m == null ? '' : `background: ${goldWash((m / hoursMax) * 100)}`}
												data-cell="{day}-{hour}"
												tabindex={hourFocus.day === day && hourFocus.hour === hour ? 0 : -1}
												aria-label={hourText(day, hour)}
												title={hourText(day, hour)}
												onmouseenter={() => (pointedHour = { day, hour })}
												onfocus={() => (pointedHour = hourFocus = { day, hour })}
											></button>
										{/each}
									</div>
								{/each}
							</div>
						</div>
						<!-- For the eye only: each hour carries its own label for a screen reader. -->
						<p class="mt-2 min-h-[1.5em] text-small text-muted" aria-hidden="true">
							{#if pointedHour}{hourText(pointedHour.day, pointedHour.hour)}.{:else}Hover or tap an hour to read it.{/if}
						</p>
						<p class="mt-1 text-micro text-muted">
							A sitting counts in the hour it started. An hour with fewer than {hours.min_readers} readers is left blank.
							{#if hours.without_zone}{fmt(hours.without_zone)} reader{hours.without_zone === 1 ? ' has' : 's have'} no time zone yet, so they're left out.{/if}
						</p>
					</section>
				{/if}

				<!-- Weekly active -->
				<section id="weekly" class="anchor mt-8 rounded-card border border-border bg-surface p-5">
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
								{#each eventsByWeek.get(col.key) ?? [] as e (e.id)}
									<EventMarker kind={e.kind} label="{e.title}, {e.detail}" active={pointed === e} onpoint={() => (pointed = e)} />
								{/each}
							</div>
						{/snippet}
					</ColumnChart>
					{#if events.length}
						<p class="mt-2 hidden min-h-[2.6em] text-small text-muted sm:block" aria-live="polite">
							{#if pointed}
								{@const n = after(pointed.week)}
								<span class="font-semibold text-text">{pointed.title}</span> · {weekLabel(pointed.date)} · {pointed.detail}{#if n}<br />{n}{/if}
							{:else}
								Hover or tap a marker to see what happened that week.
							{/if}
						</p>
						<ul class="mt-3 divide-y divide-border border-t border-border sm:hidden">
							{#each [...events].reverse() as e (e.id)}
								{@const n = after(e.week)}
								<li class="flex items-center gap-2 py-2 text-small">
									<span class="w-12 shrink-0 tabular-nums text-muted">{weekLabel(e.date)}</span>
									<EventMarker kind={e.kind} />
									<span class="min-w-0 flex-1"><span class="font-semibold text-text">{e.title}</span> <span class="text-muted">{e.detail}</span></span>
									<span class="max-w-[9rem] text-end text-micro text-muted">{n ?? 'this week'}</span>
								</li>
							{/each}
						</ul>
					{/if}
					<p class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-micro text-muted">
						<span>The last bar is this week so far.</span>
						{#each Object.entries(EVENT_KINDS) as [k, { label }] (k)}
							{#if events.some((e) => e.kind === k)}
								<span class="inline-flex items-center gap-1.5"><EventMarker kind={k as EngagementEvent['kind']} small />{label}</span>
							{/if}
						{/each}
					</p>
				</section>

				<!-- Retention cohorts: does each week's sign-ups keep reading? -->
				{#if cohortSpan}
					<section id="cohorts" class="anchor mt-8 rounded-card border border-border bg-surface p-5">
						<div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
							<h2 class="text-h3">Do readers stay?</h2>
							<span class="text-small text-muted">Each row is a week's sign-ups; each column, a week after joining.</span>
						</div>
						{#if cohortHead}
							<div class="mb-4 flex flex-wrap gap-6">
								<div>
									<div class="stat-number">{cohortHead.recent.pct}%</div>
									<div class="text-small text-muted">
										still reading at week {HEADLINE_WEEK} · joined {weekLabel(cohortHead.recent.from)}{cohortHead.recent.to !== cohortHead.recent.from ? `–${weekLabel(cohortHead.recent.to)}` : ''}
									</div>
								</div>
								<div>
									<div class="stat-number text-muted">{cohortHead.earlier.pct}%</div>
									<div class="text-small text-muted">
										at week {HEADLINE_WEEK} · joined {weekLabel(cohortHead.earlier.from)}{cohortHead.earlier.to !== cohortHead.earlier.from ? `–${weekLabel(cohortHead.earlier.to)}` : ''}
									</div>
								</div>
							</div>
						{/if}
						<div class="overflow-x-auto">
							<table class="cohorts w-full text-small tabular-nums">
								<thead>
									<tr>
										<th scope="col" class="text-left">Joined</th>
										<th scope="col">People</th>
										{#each Array.from({ length: cohortSpan }, (_, k) => k) as k (k)}
											<th scope="col">Wk {k}</th>
										{/each}
									</tr>
								</thead>
								<tbody>
									{#each cohorts as c (c.week)}
										<tr>
											<th scope="row" class="text-left">{weekLabel(c.week)}</th>
											<td class="text-muted">{fmt(c.size)}</td>
											{#if !c.active}
												<td class="few text-muted" colspan={cohortSpan} title="Fewer than {cohortFloor} people: shares hidden">{c.size ? 'too few to show' : 'no sign-ups'}</td>
											{:else}
												{#each Array.from({ length: cohortSpan }, (_, k) => k) as k (k)}
													{#if k < c.active.length}
														{@const cell = share(c.active[k], c.size)}
														<td class="cell" style="background: {goldWash(cell.pct)}" title="Joined week of {weekLabel(c.week)}: {cell.readers} of {cell.people} read in week {k}">{cell.pct}%</td>
													{:else}
														<td></td>
													{/if}
												{/each}
											{/if}
										</tr>
									{/each}
								</tbody>
								<tfoot>
									<tr>
										<th scope="row" class="text-left">All</th>
										<td></td>
										{#each cohortCols as col, k (k)}
											<td class="cell font-semibold" style={col ? `background: ${goldWash(col.pct)}` : ''} title={col ? `${col.readers} of ${col.people} across the groups that reached week ${k}` : ''}>{col ? `${col.pct}%` : ''}</td>
										{/each}
									</tr>
								</tfoot>
							</table>
						</div>
						<p class="mt-2 text-micro text-muted">
							A reader counts in a week if they read on any day of it. This week is left out until it ends. A join week with fewer than {cohortFloor} people shows its size only.
						</p>
					</section>
				{/if}

				<!-- Rising this week — biggest gain in weekly readers -->
				{#if d.rising.length}
					<section id="rising" class="anchor mt-8 rounded-card border border-border bg-surface p-5">
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
				<section id="top-content" class="anchor mt-8 rounded-card border border-border bg-surface p-5">
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
					<section id="marks" class="anchor mt-6 rounded-card border border-border bg-surface p-5">
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
					<div id="loved" class="anchor mt-6 grid gap-6 lg:grid-cols-2">
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
					<section id="plans" class="anchor mt-6 rounded-card border border-border bg-surface p-5">
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
				<section id="languages" class="anchor mt-6 rounded-card border border-border bg-surface p-5">
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
	/* A section the bar links to: a jump lands clear of the site header and
	   the section bar (its measured height, published by SectionBar), plus the
	   0.5rem the other pages' anchors add. */
	.anchor {
		scroll-margin-top: calc(var(--appnav-h, 0px) + var(--section-bar-h, 44px) + 0.5rem);
	}
	/* The reading-hours grid: a day label, then 24 square hours. */
	.hours {
		display: grid;
		grid-template-columns: 2.25rem repeat(24, minmax(0.9rem, 1fr));
		gap: 2px;
		min-width: 30rem;
		max-width: 48rem;
	}
	.hours .cell.blank {
		background: repeating-linear-gradient(135deg, var(--surface-2) 0 3px, transparent 3px 6px);
	}
	.hours .cell {
		aspect-ratio: 1;
		border-radius: 2px;
	}
	.hours .cell:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 1px;
	}
	/* The retention grid: separated cells, so each reads as its own swatch. */
	.cohorts {
		border-collapse: separate;
		border-spacing: 3px;
	}
	.cohorts th {
		padding: 2px 6px;
		font-weight: 600;
		color: var(--muted);
		white-space: nowrap;
	}
	.cohorts td {
		padding: 6px 4px;
		min-width: 2.75rem;
		text-align: center;
		border-radius: 4px;
	}
	.cohorts td.few {
		text-align: left;
		background: repeating-linear-gradient(135deg, var(--surface-2) 0 4px, transparent 4px 8px);
	}
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
