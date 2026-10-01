<script lang="ts">
	import { page } from '$app/stores';
	import { SvelteSet } from 'svelte/reactivity';
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { downloadFile } from '$lib/dataExport';
	import { localeName } from '$lib/lang.svelte';
	import {
		exportAdminActivity,
		getAdminActivity,
		type AdminActionRow,
		type AdminActivityFilters
	} from '$lib/library-admin';
	import { relativeTime } from '$lib/relativeTime';
	import { unslug } from '$lib/strings';
	import {
		actionMeta,
		actorName,
		absoluteTime,
		CATEGORIES,
		groupBursts,
		groupByDay,
		initials,
		issueRange,
		parseTarget,
		summariseDetail,
		titleParts,
		toCsv,
		type Category,
		type Edition,
		type IconName
	} from '$lib/adminActivity';

	// One object's history when ?target= is present; the whole log otherwise.
	const target = $derived($page.url.searchParams.get('target') ?? '');

	// ---- filter state ----
	// Every filter runs on the server, over the whole log: filtering the loaded
	// page answered "nothing matches" for anything older than its newest 100.
	let query = $state('');
	// The search as sent — trails the input by a beat, so typing a word is one
	// request rather than one per keystroke.
	let sentQuery = $state('');
	let activeCat = $state<Category | 'all'>('all');
	let activeActor = $state('');
	let searchEl = $state<HTMLInputElement | null>(null);

	$effect(() => {
		const q = query.trim();
		const t = setTimeout(() => (sentQuery = q), 300);
		return () => clearTimeout(t);
	});

	const filters = $derived<AdminActivityFilters>({
		target: target || undefined,
		q: sentQuery || undefined,
		category: activeCat === 'all' ? undefined : activeCat,
		actor: activeActor || undefined
	});
	const filterKey = $derived(JSON.stringify(filters));

	// The rows on screen and the cursor for the next older page. Seeded from each
	// fresh base load (a Refresh, a change of target or filters) and then grown
	// in place by "Load older". The resource's onLoad is the reset point — it
	// runs after the resource's own supersession check, so a stale load can't
	// wipe the rows a newer page accumulated.
	let rows = $state<AdminActionRow[]>([]);
	let cursor = $state<number | null>(null);
	let loadingOlder = $state(false);
	let olderError = $state<string | null>(null);

	const activity = adminResource(
		() => getAdminActivity({ ...filters, dayStart: startOfToday() }),
		'Something went wrong loading activity.',
		() => filterKey,
		(result) => {
			rows = result.actions;
			cursor = result.next_cursor;
			olderError = null;
		}
	);
	const data = $derived(activity.data);
	const summary = $derived(data?.summary ?? null);

	function startOfToday(): Date {
		const d = new Date();
		return new Date(d.getFullYear(), d.getMonth(), d.getDate());
	}

	// One reference instant per render — every "ago" on the page agrees, and the
	// tests can pin it. A ticking clock buys nothing on an audit log.
	const now = new Date();
	const nowMs = now.getTime();
	const rel = (d: Date) => relativeTime(d.getTime(), 'en', 'just now', nowMs);

	// The stroke paths for each glyph. The meaning (which action wears which)
	// lives in adminActivity; only the drawing lives here.
	const ICONS: Record<IconName, string[]> = {
		globe: ['M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20', 'M2 12h20', 'M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20'],
		edit: ['M12 20h9', 'M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z'],
		sliders: ['M4 21v-7', 'M4 10V3', 'M12 21v-9', 'M12 8V3', 'M20 21v-5', 'M20 12V3', 'M1 14h6', 'M9 8h6', 'M17 16h6'],
		translate: ['M4 5h7', 'M9 3v2', 'M4 8c0 3 2 5 5 6', 'M5 12c2-1 4-3 5-6', 'M14 20l4-9 4 9', 'M15 17h6'],
		author: ['M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8', 'M4 21a8 8 0 0 1 16 0'],
		document: ['M6 2h9l5 5v15H6z', 'M15 2v5h5', 'M9 13h6', 'M9 17h6'],
		approve: ['M22 11.5V12a10 10 0 1 1-5.9-9.1', 'M22 4 12 14.3l-3-3'],
		undo: ['M3 7v6h6', 'M3 13a9 9 0 1 0 3-7']
	};

	// A row's display name. The server sends the work's real title; a
	// language's name is localeName's job; anything else falls back to its slug.
	type Named = { target: string; title?: string };
	function nameParts(row: Named): { name: string; edition: Edition | null } {
		const t = parseTarget(row.target);
		if (t.kind === 'language') return { name: localeName(t.slug), edition: null };
		if (t.kind === 'other') return { name: t.slug || '—', edition: null };
		if (t.kind === 'document') return titleParts(t.slug, row.title);
		return { name: row.title || unslug(t.slug), edition: null };
	}
	function rowName(row: Named): string {
		const { name, edition } = nameParts(row);
		return edition ? `${name} (${edition})` : name;
	}

	// ---- bursts: a bulk action folds into one expandable row ----
	const expanded = new SvelteSet<string>();
	const burstId = (rs: AdminActionRow[]) => `${rs[0].at}|${rs[0].target}`;
	function toggleBurst(id: string) {
		if (expanded.has(id)) expanded.delete(id);
		else expanded.add(id);
	}
	/** What a burst is a run of: "100 books", "12 sermons". */
	function burstNoun(rs: AdminActionRow[]): string {
		const kind = rs[0].target.split(':')[0];
		const nouns: Record<string, string> = {
			book: 'books',
			sermon: 'sermons',
			article: 'articles',
			plan: 'plans',
			author: 'authors',
			language: 'languages'
		};
		return `${rs.length} ${nouns[kind] ?? 'items'}`;
	}
	const clock = (iso: string) =>
		new Date(iso).toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' });
	/** A burst's time span, oldest–newest; one time when it fit in a minute. */
	function spanOf(rs: AdminActionRow[]): string {
		const from = clock(rs[rs.length - 1].at);
		const to = clock(rs[0].at);
		return from === to ? to : `${from}–${to}`;
	}

	async function loadOlder() {
		// While a reload for new filters is in flight, `cursor` still belongs to
		// the old query — pairing it with the new filters would fetch the wrong
		// window.
		if (cursor == null || loadingOlder || activity.loading) return;
		loadingOlder = true;
		olderError = null;
		// The query this page belongs to. A base reload (a Refresh, a new target
		// or filter) reseeds rows/cursor while this is in flight; if that
		// happened, drop this page rather than append it to a different query's.
		const scope = filterKey;
		try {
			const res = await getAdminActivity({ ...filters, before: cursor });
			if (scope !== filterKey) return;
			rows = [...rows, ...res.actions];
			cursor = res.next_cursor;
		} catch (e) {
			if (scope !== filterKey) return;
			olderError = e instanceof Error ? e.message : 'Could not load older activity.';
		} finally {
			loadingOlder = false;
		}
	}

	// The admin picker and chip counts come from the server's summary, so they
	// cover the whole log rather than whoever happens to be on the loaded page.
	const actors = $derived(summary?.actors ?? []);
	const catCounts = $derived(summary?.by_category ?? {});
	const catTotal = $derived(Object.values(catCounts).reduce((a, b) => a + b, 0));

	const groups = $derived(
		groupByDay(rows, now).map((g) => ({ ...g, items: groupBursts(g.rows) }))
	);
	const isFiltered = $derived(activeCat !== 'all' || !!activeActor || sentQuery !== '');

	// ---- the header figures: counted server-side over the whole log ----
	const cards = $derived.by(() => {
		if (!summary) return [];
		const { last_go_live: goLive, last_publish: publish } = summary;
		// With one admin, "most active" is always them — a card that never
		// changes. Show the week instead until there is a team to compare.
		const busiest = summary.actors[0];
		const second =
			summary.actors.length > 1
				? { value: actorName(busiest.actor), label: 'Most active', sub: `${busiest.count} of ${summary.all}` }
				: { value: String(summary.week), label: 'This week', sub: 'actions in the last 7 days' };
		return [
			{ value: String(summary.today), label: 'Actions today', sub: `${summary.today_reader_facing} reader-facing` },
			second,
			{
				value: goLive ? rowName(goLive) : '—',
				label: 'Last go-live',
				sub: goLive ? rel(new Date(goLive.at)) : 'never'
			},
			{
				value: publish ? rowName(publish) : '—',
				label: 'Last publish',
				sub: publish ? rel(new Date(publish.at)) : 'never'
			}
		];
	});

	function onKey(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			searchEl?.focus();
		}
	}

	// The file holds every row matching the filters, fetched for the purpose —
	// exporting the loaded page silently dropped everything older.
	let exporting = $state(false);
	let exportNote = $state<{ text: string; error: boolean } | null>(null);
	// A note describes one export; a filter change makes it stale.
	$effect(() => {
		void filterKey;
		exportNote = null;
	});
	async function exportCsv() {
		if (exporting) return;
		exporting = true;
		exportNote = null;
		try {
			// What the box says now, not the debounced value a click may beat.
			const res = await exportAdminActivity({ ...filters, q: query.trim() || undefined });
			downloadFile(
				`ochorus-activity-${new Date().toISOString().slice(0, 10)}.csv`,
				'text/csv;charset=utf-8',
				toCsv(res.actions)
			);
			if (res.truncated)
				exportNote = {
					text: `Exported the newest ${res.actions.length.toLocaleString('en')} rows — narrow the filters for the rest.`,
					error: false
				};
		} catch (e) {
			exportNote = { text: e instanceof Error ? e.message : 'Could not export activity.', error: true };
		} finally {
			exporting = false;
		}
	}

	// Loud (reader-facing) rows wear the accent tint the old page reserved for
	// exactly these two actions; the rest stay muted and lean on their glyph.
	const iconTone = (loud: boolean) =>
		loud
			? 'border-accent-soft-border bg-accent-soft text-accent'
			: 'border-border bg-surface-2 text-muted';
	const pillTone = (loud: boolean) =>
		loud ? 'border-accent-soft-border bg-accent-soft text-accent' : 'border-border text-muted';
</script>

<svelte:head><title>Admin · Activity — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>
<svelte:window onkeydown={onKey} />

{#snippet actionRow(a: AdminActionRow)}
	{@const meta = actionMeta(a.action)}
	{@const t = parseTarget(a.target)}
	{@const at = new Date(a.at)}
	{@const np = nameParts(a)}
	<li class="grid grid-cols-[auto_1fr_auto] gap-3 border-b border-border p-4 last:border-0">
		<span class="grid h-8 w-8 place-items-center rounded-sm border {iconTone(meta.loud)}">
			<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
				{#each ICONS[meta.icon] as d (d)}<path {d} />{/each}
			</svg>
		</span>
		<div class="min-w-0">
			<div class="flex flex-wrap items-center gap-2">
				{#if t.href}
					<a href={t.href} class="font-medium text-text underline decoration-transparent underline-offset-2 hover:decoration-accent-soft-border hover:text-accent">
						{np.name}{#if t.lang}<span class="text-small font-normal text-muted">&nbsp;· {localeName(t.lang)}</span>{/if}
					</a>
				{:else}
					<span class="font-medium text-text">{np.name}</span>
				{/if}
				{#if np.edition}
					<span class="shrink-0 rounded-full border border-border px-2 py-0.5 text-micro font-semibold text-muted">{np.edition}</span>
				{/if}
				<span class="shrink-0 rounded-full border px-2.5 py-0.5 text-small font-semibold {pillTone(meta.loud)}">{a.label}</span>
				{#if !target && t.kind !== 'other'}
					<a
						href="/admin/activity?target={encodeURIComponent(a.target)}"
						title="Show this target's history"
						aria-label="Show this target's history"
						class="shrink-0 text-muted hover:text-accent"
					>
						<svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9" /><path d="M12 8v4l2.5 2.5" /></svg>
					</a>
				{/if}
			</div>
			<div class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-small text-muted">
				<span class="inline-flex items-center gap-1.5">
					<span class="grid h-5 w-5 place-items-center rounded-full text-micro font-bold {a.actor ? 'bg-accent text-accent-contrast' : 'border border-border bg-surface-2 text-muted'}">{initials(a.actor)}</span>
					{actorName(a.actor)}
				</span>
				{#each summariseDetail(a.detail) as part, pi (pi)}
					<span class="text-border-strong" aria-hidden="true">·</span>
					{#if part.kind === 'outcome'}
						<span class="font-semibold text-text">{part.text}</span>
					{:else if part.kind === 'diff'}
						<span>{part.label} <span class="text-text line-through opacity-70">{part.from}</span> <span class="font-semibold text-text">→ {part.to}</span></span>
					{:else if part.kind === 'warn'}
						<span class="font-semibold text-danger">{part.text}</span>
					{:else if part.kind === 'quote'}
						<span class="italic">“{part.text}”</span>
					{:else if part.kind === 'link'}
						<a
							href={part.href}
							target="_blank"
							rel="noopener"
							title={part.href}
							class="inline-flex items-center rounded-full border border-border px-2 py-0.5 text-micro font-semibold text-muted transition-colors hover:border-accent-soft-border hover:text-accent hover:no-underline"
							>{part.text}</a
						>
					{:else}
						<span>{part.text}</span>
					{/if}
				{/each}
			</div>
		</div>
		<div class="text-right">
			<div class="text-small tabular-nums text-muted" title={at.toString()}>{rel(at)}</div>
			<div class="text-micro tabular-nums text-muted opacity-70">{absoluteTime(a.at)}</div>
		</div>
	</li>
{/snippet}

<div class="mx-auto max-w-5xl px-5 py-10">
	<header class="mb-6 flex flex-wrap items-end justify-between gap-3">
		<div>
			<p class="eyebrow mb-2 text-accent">Admin</p>
			<h1 class="text-display">Activity</h1>
			<p class="mt-2 text-body text-muted">
				Every change made from this dashboard — who, what and when. Append-only.
			</p>
		</div>
		{#if summary && summary.all > 0}
			<div class="flex items-center gap-2">
				<button class="btn btn-ghost" onclick={exportCsv} disabled={exporting || data?.total === 0}
					>{exporting
						? 'Exporting…'
						: `Export CSV${data?.total != null ? ` · ${data.total.toLocaleString('en')}` : ''}`}</button
				>
				<button class="btn btn-ghost" onclick={activity.load} disabled={activity.loading}
					>{activity.loading ? 'Refreshing…' : 'Refresh'}</button
				>
			</div>
		{/if}
	</header>

	{#if target}
		<div class="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-card border border-accent-soft-border bg-accent-soft px-4 py-3">
			<p class="text-body text-text">
				History for <span class="font-semibold">{rowName({ target, title: rows[0]?.title })}</span>
				<span class="text-small text-muted">· {target}</span>
			</p>
			<a href="/admin/activity" class="btn btn-ghost">← All activity</a>
		</div>
	{/if}

	<AdminGate resource={activity} errorTitle="Couldn't load activity" keepDataOnError>
		{#snippet children(d)}
			{#if !d.summary || d.summary.all === 0}
				<div class="rounded-card border border-border bg-surface p-8 text-center">
					<p class="text-h3">{target ? 'No history for this target' : 'Nothing recorded yet'}</p>
					<p class="mt-1 text-body text-muted">
						{#if target}
							Nothing has been changed here through the admin yet.
						{:else}
							Creating a language, publishing a document or deciding a review will show up here.
						{/if}
					</p>
				</div>
			{:else}
				<!-- The window at a glance: answers "who took X live, and when?" without a scroll. -->
				<div class="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
					{#each cards as c (c.label)}
						<div class="rounded-card border border-border bg-surface p-4">
							<div class="stat-number truncate">{c.value}</div>
							<div class="mt-2 text-small font-semibold text-text">{c.label}</div>
							<div class="text-small text-muted">{c.sub}</div>
						</div>
					{/each}
				</div>

				<!-- Filter bar: category, admin and free-text — over the loaded window. -->
				<div class="mb-4 flex flex-wrap items-center gap-2">
					<label class="flex min-w-56 flex-1 items-center gap-2 rounded-sm border border-border bg-surface px-3 py-2 focus-within:border-accent">
						<svg class="h-4 w-4 shrink-0 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
						<input
							bind:this={searchEl}
							bind:value={query}
							type="text"
							placeholder="Search target, admin or detail…"
							aria-label="Search activity"
							class="w-full bg-transparent text-small text-text outline-none placeholder:text-muted"
						/>
						<kbd class="hidden shrink-0 rounded border border-border bg-surface-2 px-1.5 py-0.5 text-micro text-muted sm:inline">⌘K</kbd>
					</label>
					<div class="flex flex-wrap gap-1.5">
						<button
							class="rounded-full border px-3 py-1.5 text-small font-semibold {activeCat === 'all'
								? 'border-accent bg-accent text-accent-contrast'
								: 'border-border text-muted hover:text-text'}"
							onclick={() => (activeCat = 'all')}
						>
							All <span class="tabular-nums opacity-70">{catTotal}</span>
						</button>
						{#each CATEGORIES as cat (cat)}
							<button
								class="rounded-full border px-3 py-1.5 text-small font-semibold {activeCat === cat
									? 'border-accent bg-accent text-accent-contrast'
									: 'border-border text-muted hover:text-text'}"
								onclick={() => (activeCat = cat)}
							>
								{unslug(cat)}
								<span class="tabular-nums opacity-70">{catCounts[cat] ?? 0}</span>
							</button>
						{/each}
					</div>
					{#if actors.length > 1 || activeActor}
						<select
							bind:value={activeActor}
							aria-label="Filter by admin"
							class="rounded-full border border-border bg-surface px-3 py-1.5 text-small font-semibold text-text"
						>
							<option value="">All admins</option>
							{#each actors as a (a.actor)}
								<option value={a.actor}>{actorName(a.actor)}</option>
							{/each}
						</select>
					{/if}
				</div>

				{#if exportNote}
					<p class="mb-3 text-small {exportNote.error ? 'text-danger' : 'text-muted'}">{exportNote.text}</p>
				{/if}
				{#if activity.error}
					<p class="mb-3 text-small text-danger" role="alert">
						Couldn't apply these filters: {activity.error}
						<button class="ml-1 font-semibold underline" onclick={activity.load}>Try again</button>
					</p>
				{/if}
				<p class="mb-3 text-small text-muted" aria-live="polite">
					{#if isFiltered}
						{(d.total ?? 0).toLocaleString('en')} matching across all {d.summary.all.toLocaleString('en')} actions{#if rows.length < (d.total ?? 0)}&nbsp;· {rows.length} loaded{/if}
					{:else}
						Showing {rows.length} of {(d.total ?? 0).toLocaleString('en')} action{d.total === 1 ? '' : 's'}.
					{/if}
				</p>

				{#if rows.length === 0}
					<div class="rounded-card border border-dashed border-border bg-surface p-8 text-center">
						<p class="text-h3">Nothing matches</p>
						<p class="mt-1 text-body text-muted">
							No actions fit these filters. Clear the search or pick a different category.
						</p>
					</div>
				{:else}
					{#each groups as g, gi (g.label)}
						<section class="mb-4">
							<div class="sticky top-0 z-10 flex items-baseline gap-3 bg-bg py-2">
								<h2 class="text-small font-semibold text-text">{g.label}</h2>
								<!-- The oldest loaded day may continue past the page: say so rather than undercount it. -->
								<span class="text-small tabular-nums text-muted"
									>{g.rows.length}{gi === groups.length - 1 && cursor != null ? '+' : ''}</span
								>
								<span class="h-px flex-1 bg-border"></span>
							</div>
							<ul class="overflow-hidden rounded-card border border-border bg-surface">
								{#each g.items as item, i (item.kind === 'row' ? `r${item.row.at}${item.row.target}${i}` : `b${burstId(item.rows)}`)}
									{#if item.kind === 'row'}
										{@render actionRow(item.row)}
									{:else}
										{@const first = item.rows[0]}
										{@const meta = actionMeta(first.action)}
										{@const t = parseTarget(first.target)}
										{@const id = burstId(item.rows)}
										{@const open = expanded.has(id)}
										{@const issues = issueRange(item.rows)}
										{@const stale = item.rows.filter((r) => r.detail?.created === false).length}
										<li class="border-b border-border last:border-0">
											<div class="grid grid-cols-[auto_1fr_auto] gap-3 p-4">
												<span class="grid h-8 w-8 place-items-center rounded-sm border {iconTone(meta.loud)}">
													<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
														{#each ICONS[meta.icon] as d (d)}<path {d} />{/each}
													</svg>
												</span>
												<div class="min-w-0">
													<div class="flex flex-wrap items-center gap-2">
														<span class="font-medium text-text"
															>{burstNoun(item.rows)}{#if t.lang}<span class="text-small font-normal text-muted">&nbsp;· {localeName(t.lang)}</span>{/if}</span
														>
														<span class="shrink-0 rounded-full border px-2.5 py-0.5 text-small font-semibold {pillTone(meta.loud)}">{first.label}</span>
													</div>
													<div class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-small text-muted">
														<span class="inline-flex items-center gap-1.5">
															<span class="grid h-5 w-5 place-items-center rounded-full text-micro font-bold {first.actor ? 'bg-accent text-accent-contrast' : 'border border-border bg-surface-2 text-muted'}">{initials(first.actor)}</span>
															{actorName(first.actor)}
														</span>
														{#if issues}
															<span class="text-border-strong" aria-hidden="true">·</span>
															<span class="tabular-nums">{issues}</span>
														{/if}
														{#if stale}
															<!-- Folded, a duplicate click would hide inside the burst: surface it. -->
															<span class="text-border-strong" aria-hidden="true">·</span>
															<span class="font-semibold text-danger">{stale} already open</span>
														{/if}
													</div>
													{#if !open}
														<p class="mt-1.5 truncate text-small text-muted">
															{item.rows.slice(0, 4).map(rowName).join(' · ')}{item.rows.length > 4 ? ` · +${item.rows.length - 4} more` : ''}
														</p>
													{/if}
													<button
														class="mt-1.5 text-small font-semibold text-accent hover:underline"
														aria-expanded={open}
														onclick={() => toggleBurst(id)}>{open ? 'Hide' : `Show all ${item.rows.length}`}</button
													>
												</div>
												<div class="text-right">
													<div class="text-small tabular-nums text-muted" title={new Date(first.at).toString()}>{rel(new Date(first.at))}</div>
													<div class="text-micro tabular-nums text-muted opacity-70">
														{spanOf(item.rows)}
													</div>
												</div>
											</div>
											{#if open}
												<ul class="border-t border-border bg-surface-2 pl-6">
													{#each item.rows as a, j (a.at + a.target + j)}
														{@render actionRow(a)}
													{/each}
												</ul>
											{/if}
										</li>
									{/if}
								{/each}
							</ul>
						</section>
					{/each}
				{/if}

				{#if cursor != null}
					<div class="mt-4 flex flex-col items-center gap-2">
						<button class="btn btn-ghost" onclick={loadOlder} disabled={loadingOlder || activity.loading}>
							{loadingOlder ? 'Loading…' : 'Load older'}
						</button>
						{#if olderError}<p class="text-small text-danger">{olderError}</p>{/if}
					</div>
				{/if}
			{/if}
		{/snippet}
	</AdminGate>
</div>
