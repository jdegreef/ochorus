<script lang="ts">
	import { page } from '$app/stores';
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { downloadFile } from '$lib/dataExport';
	import { localeName } from '$lib/lang.svelte';
	import { getAdminActivity, type AdminActionRow } from '$lib/library-admin';
	import { relativeTime } from '$lib/relativeTime';
	import { unslug } from '$lib/strings';
	import {
		actionMeta,
		actorName,
		absoluteTime,
		busiestActor,
		categoryCounts,
		CATEGORIES,
		groupByDay,
		initials,
		parseTarget,
		summariseDetail,
		todayStats,
		toCsv,
		type Category,
		type IconName,
		type ParsedTarget
	} from '$lib/adminActivity';

	// One object's history when ?target= is present; the whole log otherwise.
	const target = $derived($page.url.searchParams.get('target') ?? '');

	// The rows on screen and the cursor for the next older page. Seeded from each
	// fresh base load (a Refresh, or a change of target) and then grown in place
	// by "Load older". The resource's onLoad is the reset point — it runs after
	// the resource's own supersession check, so a stale load can't wipe the rows
	// a newer page accumulated.
	let rows = $state<AdminActionRow[]>([]);
	let cursor = $state<number | null>(null);
	let loadingOlder = $state(false);
	let olderError = $state<string | null>(null);

	const activity = adminResource(
		() => getAdminActivity({ target: target || undefined }),
		'Something went wrong loading activity.',
		() => target,
		(result) => {
			rows = result.actions;
			cursor = result.next_cursor;
			olderError = null;
		}
	);
	const data = $derived(activity.data);

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

	// The display name for a target — the one thing left out of parseTarget,
	// because a language's name is localeName's job and the rest is a slug.
	function displayName(t: ParsedTarget): string {
		if (t.kind === 'language') return localeName(t.slug);
		if (t.kind === 'other') return t.slug || '—';
		return unslug(t.slug);
	}
	const targetName = (target: string) => displayName(parseTarget(target));

	// ---- filter state (all client-side over the loaded window) ----
	let query = $state('');
	let activeCat = $state<Category | 'all'>('all');
	let activeActor = $state('');
	let searchEl = $state<HTMLInputElement | null>(null);

	async function loadOlder() {
		if (cursor == null || loadingOlder) return;
		loadingOlder = true;
		olderError = null;
		// The scope this page belongs to. A base reload (a Refresh, or navigating
		// to another target) reseeds rows/cursor while this is in flight; if that
		// happened, drop this page rather than append it to a different query's.
		const scope = target;
		try {
			const res = await getAdminActivity({ before: cursor, target: scope || undefined });
			if (scope !== target) return;
			rows = [...rows, ...res.actions];
			cursor = res.next_cursor;
		} catch (e) {
			if (scope !== target) return;
			olderError = e instanceof Error ? e.message : 'Could not load older activity.';
		} finally {
			loadingOlder = false;
		}
	}

	// Blank actors (only a DEBUG tokenless request) are dropped: their empty value
	// would collide with the "All admins" sentinel and can't be filtered on anyway.
	const actors = $derived([...new Set(rows.map((r) => r.actor))].filter(Boolean));
	const catCounts = $derived(categoryCounts(rows));

	function matches(r: AdminActionRow): boolean {
		if (activeCat !== 'all' && actionMeta(r.action).category !== activeCat) return false;
		if (activeActor && r.actor !== activeActor) return false;
		const q = query.trim().toLowerCase();
		if (q) {
			const hay = `${r.target} ${r.actor} ${r.label} ${JSON.stringify(r.detail)}`.toLowerCase();
			if (!hay.includes(q)) return false;
		}
		return true;
	}

	const filtered = $derived(rows.filter(matches));
	const groups = $derived(groupByDay(filtered, now));
	const isFiltered = $derived(activeCat !== 'all' || !!activeActor || query.trim() !== '');

	// ---- the header figures: computed from the loaded window ----
	const today = $derived(todayStats(rows, now));
	const busiest = $derived(busiestActor(rows));
	const lastGoLive = $derived(rows.find((r) => r.action === 'language.go_live'));
	const lastPublish = $derived(rows.find((r) => r.action === 'content.publish'));
	const cards = $derived([
		{ value: String(today.count), label: 'Actions today', sub: `${today.readerFacing} reader-facing` },
		{ value: actorName(busiest.actor), label: 'Most active', sub: `${busiest.count} of ${rows.length} shown` },
		{
			value: lastGoLive ? targetName(lastGoLive.target) : '—',
			label: 'Last go-live',
			sub: lastGoLive ? rel(new Date(lastGoLive.at)) : 'none in this window'
		},
		{
			value: lastPublish ? targetName(lastPublish.target) : '—',
			label: 'Last publish',
			sub: lastPublish ? rel(new Date(lastPublish.at)) : 'none in this window'
		}
	]);

	function onKey(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			searchEl?.focus();
		}
	}

	function exportCsv() {
		downloadFile(
			`ochorus-activity-${now.toISOString().slice(0, 10)}.csv`,
			'text/csv;charset=utf-8',
			toCsv(filtered)
		);
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

<div class="mx-auto max-w-5xl px-5 py-10">
	<header class="mb-6 flex flex-wrap items-end justify-between gap-3">
		<div>
			<p class="eyebrow mb-2 text-accent">Admin</p>
			<h1 class="text-display">Activity</h1>
			<p class="mt-2 text-body text-muted">
				Every change made from this dashboard — who, what and when. Append-only.
			</p>
		</div>
		{#if data && data.actions.length > 0}
			<div class="flex items-center gap-2">
				<button class="btn btn-ghost" onclick={exportCsv}>Export CSV</button>
				<button class="btn btn-ghost" onclick={activity.load} disabled={activity.loading}
					>{activity.loading ? 'Refreshing…' : 'Refresh'}</button
				>
			</div>
		{/if}
	</header>

	{#if target}
		<div class="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-card border border-accent-soft-border bg-accent-soft px-4 py-3">
			<p class="text-body text-text">
				History for <span class="font-semibold">{targetName(target)}</span>
				<span class="text-small text-muted">· {target}</span>
			</p>
			<a href="/admin/activity" class="btn btn-ghost">← All activity</a>
		</div>
	{/if}

	<AdminGate resource={activity} errorTitle="Couldn't load activity">
		{#snippet children(d)}
			{#if d.actions.length === 0}
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
							All <span class="tabular-nums opacity-70">{rows.length}</span>
						</button>
						{#each CATEGORIES as cat (cat)}
							<button
								class="rounded-full border px-3 py-1.5 text-small font-semibold {activeCat === cat
									? 'border-accent bg-accent text-accent-contrast'
									: 'border-border text-muted hover:text-text'}"
								onclick={() => (activeCat = cat)}
							>
								{unslug(cat)}
								<span class="tabular-nums opacity-70">{catCounts[cat]}</span>
							</button>
						{/each}
					</div>
					{#if actors.length > 1}
						<select
							bind:value={activeActor}
							aria-label="Filter by admin"
							class="rounded-full border border-border bg-surface px-3 py-1.5 text-small font-semibold text-text"
						>
							<option value="">All admins</option>
							{#each actors as a (a)}
								<option value={a}>{actorName(a)}</option>
							{/each}
						</select>
					{/if}
				</div>

				<p class="mb-3 text-small text-muted">
					{#if isFiltered}
						{filtered.length} matching · {rows.length} loaded of {d.total}
					{:else}
						Showing {rows.length} of {d.total} action{d.total === 1 ? '' : 's'}.
					{/if}
				</p>

				{#if filtered.length === 0}
					<div class="rounded-card border border-dashed border-border bg-surface p-8 text-center">
						<p class="text-h3">Nothing matches</p>
						<p class="mt-1 text-body text-muted">
							No actions fit these filters. Clear the search or pick a different category.
						</p>
					</div>
				{:else}
					{#each groups as g (g.label)}
						<section class="mb-4">
							<div class="sticky top-0 z-10 flex items-baseline gap-3 bg-bg py-2">
								<h2 class="text-small font-semibold text-text">{g.label}</h2>
								<span class="text-small tabular-nums text-muted">{g.rows.length}</span>
								<span class="h-px flex-1 bg-border"></span>
							</div>
							<ul class="overflow-hidden rounded-card border border-border bg-surface">
								{#each g.rows as a, i (a.at + a.action + a.target + i)}
									{@const meta = actionMeta(a.action)}
									{@const t = parseTarget(a.target)}
									{@const at = new Date(a.at)}
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
														{displayName(t)}{#if t.lang}<span class="text-small font-normal text-muted"> · {t.lang}</span>{/if}
													</a>
												{:else}
													<span class="font-medium text-text">{displayName(t)}</span>
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
													{:else if part.kind === 'quote'}
														<span class="italic">“{part.text}”</span>
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
								{/each}
							</ul>
						</section>
					{/each}
				{/if}

				{#if cursor != null}
					<div class="mt-4 flex flex-col items-center gap-2">
						<button class="btn btn-ghost" onclick={loadOlder} disabled={loadingOlder}>
							{loadingOlder ? 'Loading…' : 'Load older'}
						</button>
						{#if olderError}<p class="text-small text-danger">{olderError}</p>{/if}
					</div>
				{/if}
			{/if}
		{/snippet}
	</AdminGate>
</div>
