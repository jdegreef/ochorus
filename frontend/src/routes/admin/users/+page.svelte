<script lang="ts">
	import { apiFetchRaw } from '$lib/api';
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import TrendChip from '$lib/components/TrendChip.svelte';
	import {
		formatDuration,
		getAdminUserDirectory,
		getAdminUsers,
		maskEmail,
		periodTrend,
		type AdminUserSort,
		type Trend
	} from '$lib/library-admin';

	const users = adminResource(getAdminUsers, 'Something went wrong loading users.');
	const data = $derived(users.data);

	// The searchable directory: every account, not just the recent 25. A second
	// resource with a key over (query, page, sort), so it re-fetches when any of
	// them change; the search box is debounced into `query` so it doesn't fire
	// per keystroke.
	let search = $state('');
	let query = $state('');
	let dirPage = $state(1);
	let dirSort = $state<AdminUserSort>('recent');
	let searchTimer: ReturnType<typeof setTimeout> | undefined;
	function onSearch(v: string) {
		search = v;
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => {
			query = search.trim();
			dirPage = 1;
		}, 300);
	}
	function setSort(s: AdminUserSort) {
		dirSort = s;
		dirPage = 1;
	}
	const directory = adminResource(
		() => getAdminUserDirectory({ q: query, page: dirPage, sort: dirSort }),
		'Something went wrong loading the directory.',
		() => `${query}\u0000${dirPage}\u0000${dirSort}`
	);
	const dir = $derived(directory.data);

	const SORTS: { key: AdminUserSort; label: string }[] = [
		{ key: 'recent', label: 'Newest' },
		{ key: 'seen', label: 'Last seen' },
		{ key: 'active', label: 'Most active' },
		{ key: 'name', label: 'Name' }
	];

	// Download the directory (the current search + sort, all matching rows) as
	// CSV. apiFetchRaw carries the auth header a plain <a download> can't; the
	// blob→object-URL→click dance mirrors the dashboard's inventory export.
	let exporting = $state(false);
	async function exportCsv() {
		exporting = true;
		try {
			const params = new URLSearchParams({ fmt: 'csv' });
			if (query) params.set('q', query);
			if (dirSort !== 'recent') params.set('sort', dirSort);
			const res = await apiFetchRaw(`/api/admin/users/directory/?${params}`);
			const url = URL.createObjectURL(await res.blob());
			const a = document.createElement('a');
			a.href = url;
			a.download = 'ochorus-users.csv';
			a.click();
			URL.revokeObjectURL(url);
		} catch {
			/* denied or offline — the page already surfaces auth errors */
		} finally {
			exporting = false;
		}
	}

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number | null | undefined) => nf.format(n ?? 0);
	const weekLabel = (iso: string) =>
		new Date(iso + 'T00:00:00').toLocaleDateString('en', { month: 'short', day: 'numeric' });
	const pct = (n: number, total: number) => (total ? Math.round((n / total) * 100) : 0);
	const dayFmt = (iso: string | null) =>
		iso ? new Date(iso).toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' }) : '—';

	type Card = { label: string; value: number; sub: string; trend: Trend };
	const cards = $derived<Card[]>(
		data
			? [
					{ label: 'Registered users', value: data.total, sub: 'total accounts', trend: null },
					{ label: 'Activated', value: data.with_activity, sub: `${pct(data.with_activity, data.total)}% have read`, trend: null },
					{ label: 'Dormant', value: data.dormant, sub: 'no reading yet', trend: null },
					{ label: 'New · 7d', value: data.signups_7d, sub: 'vs prev 7 days', trend: periodTrend(data.signups_7d, data.signups_prev_7d) },
					{ label: 'New · 30d', value: data.signups_30d, sub: 'vs prev 30 days', trend: periodTrend(data.signups_30d, data.signups_prev_30d) }
				]
			: []
	);

	// A country code → flag emoji (two regional-indicator letters); a globe for
	// the "unknown" bucket or anything that isn't a 2-letter code.
	const flag = (code: string) =>
		/^[A-Za-z]{2}$/.test(code)
			? String.fromCodePoint(...[...code.toUpperCase()].map((c) => 0x1f1e6 + c.charCodeAt(0) - 65))
			: '🌐';
	// Drop the "Continent/" prefix for a compact label; the city carries the info.
	const tzLabel = (tz: string) => (tz === 'Other' ? tz : tz.split('/').pop()!.replace(/_/g, ' '));

	const signupMax = $derived(Math.max(1, ...(data?.weekly_signups.map((w) => w.count) ?? [1])));
	const localeMax = $derived(Math.max(1, ...(data?.by_locale.map((l) => l.count) ?? [1])));
	const methodMax = $derived(Math.max(1, ...(data?.by_method.map((m) => m.count) ?? [1])));
	const countryMax = $derived(Math.max(1, ...(data?.by_country.map((c) => c.count) ?? [1])));
	const tzMax = $derived(Math.max(1, ...(data?.by_timezone.map((t) => t.count) ?? [1])));

	// Emails are PII: masked by default, revealed on demand (per row, or all at once).
	// Reveals are cleared on every (re)load so a stale row index can't expose a
	// different account. Server-side access logging is a follow-up (needs an endpoint).
	let showAllEmails = $state(false);
	let revealedRows = $state<Record<number, boolean>>({});
	const emailShown = (i: number) => showAllEmails || revealedRows[i] === true;
	const toggleRow = (i: number) => (revealedRows = { ...revealedRows, [i]: !revealedRows[i] });
	const toggleAllEmails = () => {
		showAllEmails = !showAllEmails;
		if (!showAllEmails) revealedRows = {};
	};
	$effect(() => {
		// Re-mask whenever the list reloads (Refresh / first load).
		void data;
		showAllEmails = false;
		revealedRows = {};
	});
</script>

<svelte:head><title>Admin · Users — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

{#snippet emailCell(email: string | null | undefined, i: number, cls: string)}
	{#if email}
		<button
			type="button"
			class="block max-w-full truncate text-start {cls} hover:text-text focus-visible:text-text"
			title={emailShown(i) ? 'Hide email' : 'Reveal email'}
			aria-label={emailShown(i) ? 'Hide email' : 'Reveal email'}
			onclick={() => toggleRow(i)}
		>{emailShown(i) ? email : maskEmail(email)}</button>
	{:else}
		<div class="truncate {cls}">—</div>
	{/if}
{/snippet}

<!-- The horizontal count bar shared by every breakdown list (method, language,
     country, timezone): a track with an accent fill scaled to the list's max. -->
{#snippet bar(value: number, max: number)}
	<div class="h-3 flex-1 overflow-hidden rounded-full bg-surface-2">
		<div class="h-full rounded-full bg-accent-soft" style="width: {(value / max) * 100}%"></div>
	</div>
{/snippet}

<div class="mx-auto max-w-5xl px-5 py-10">
	<header class="mb-6 flex flex-wrap items-end justify-between gap-3">
		<div>
			<p class="eyebrow mb-2 text-accent">Admin</p>
			<h1 class="text-display">Users</h1>
			<p class="mt-2 text-body text-muted">Account growth, make-up, and who's signing up. Admin-only.</p>
		</div>
		{#if data}
			<button class="btn btn-ghost" onclick={users.load} disabled={users.loading}
				>{users.loading ? 'Refreshing…' : 'Refresh'}</button
			>
		{/if}
	</header>

	<AdminGate resource={users} errorTitle="Couldn't load users">
		{#snippet children(d)}
			{#if d.total === 0}
				<div class="rounded-card border border-border bg-surface p-8 text-center">
					<p class="text-h3">No accounts yet</p>
					<p class="mt-1 text-body text-muted">Sign-ups will appear here once readers create accounts.</p>
				</div>
			{:else}
				<!-- Overview -->
				<section class="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
					{#each cards as c (c.label)}
						<div class="rounded-card border border-border bg-surface p-4">
							<div class="flex items-baseline gap-2">
								<div class="stat-number">{fmt(c.value)}</div>
								<TrendChip trend={c.trend} />
							</div>
							<div class="mt-2 text-small font-semibold text-text">{c.label}</div>
							<div class="text-small text-muted">{c.sub}</div>
						</div>
					{/each}
				</section>

				<p class="mb-8 -mt-4 text-micro text-muted">
					Activated = has opened at least one book. Dormant = registered but hasn't started reading.
				</p>

				<!-- Weekly signups -->
				<section class="mb-8 rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3 mb-4">New sign-ups per week</h2>
					<div class="flex items-end gap-1.5" style="height: 8rem">
						{#each d.weekly_signups as w (w.week)}
							<div class="flex flex-1 flex-col items-center gap-1">
								<div class="text-small tabular-nums text-muted">{w.count || ''}</div>
								<div
									class="w-full rounded-t-sm bg-accent-soft"
									style="height: {(w.count / signupMax) * 100}%; min-height: {w.count ? '3px' : '0'}"
								></div>
								<div class="text-micro text-muted">{weekLabel(w.week)}</div>
							</div>
						{/each}
					</div>
				</section>

				<!-- By sign-in method + Recent sign-ups -->
				<div class="mb-8 grid gap-6 lg:grid-cols-3">
					<!-- By sign-in method -->
					<section class="rounded-card border border-border bg-surface p-5">
						<h2 class="text-h3 mb-3">By sign-in method</h2>
						{#if d.by_method.length}
							<ul class="space-y-2">
								{#each d.by_method as m (m.method)}
									<li class="flex items-center gap-3">
										<span class="w-20 shrink-0 truncate text-body {m.method === 'unknown' ? 'text-muted' : 'text-text'}"
											>{m.label}</span
										>
										{@render bar(m.count, methodMax)}
										<span class="w-8 shrink-0 text-right font-semibold tabular-nums text-text">{fmt(m.count)}</span>
									</li>
								{/each}
							</ul>
							<p class="mt-3 text-micro text-muted">
								Counts overlap — an account with more than one method is in each.
							</p>
						{:else}
							<p class="text-body text-muted">No sign-in methods recorded yet.</p>
						{/if}
					</section>

					<!-- Recent sign-ups -->
					<section class="rounded-card border border-border bg-surface p-5 lg:col-span-2">
						<div class="mb-3 flex items-center justify-between gap-3">
							<h2 class="text-h3">Recent sign-ups</h2>
							{#if d.recent.length}
								<button
									type="button"
									class="text-small text-muted underline-offset-2 hover:text-text hover:underline"
									aria-pressed={showAllEmails}
									onclick={toggleAllEmails}>{showAllEmails ? 'Hide emails' : 'Reveal emails'}</button
								>
							{/if}
						</div>
						{#if d.recent.length}
							<ul class="divide-y divide-border">
								{#each d.recent as u, i (u.uid)}
										<li class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-2.5">
											<div class="min-w-0">
												{#if u.display_name}
													<a href="/admin/users/{u.uid}" class="block truncate font-semibold text-text hover:text-accent hover:underline">{u.display_name}</a>
													{@render emailCell(u.email, i, 'text-small text-muted')}
												{:else}
													<!-- No name: the row is reached via the "View" link; email stays a reveal button. -->
													<a href="/admin/users/{u.uid}" class="text-small text-accent hover:underline">View profile →</a>
													{@render emailCell(u.email, i, 'font-semibold text-text')}
												{/if}
											</div>
											<div class="flex items-baseline gap-4 text-small text-muted">
												<span class="text-text">
													{#if u.providers.length}
														{u.providers.map((p) => p.label).join(', ')}
													{:else}
														<span class="text-muted">—</span>
													{/if}
												</span>
												<span class="whitespace-nowrap tabular-nums" title="Joined">{dayFmt(u.joined_at)}</span>
												<span class="hidden whitespace-nowrap tabular-nums sm:inline" title="Last seen"
													>seen {dayFmt(u.last_seen_at)}</span
												>
												<a
													href="/admin/users/{u.uid}"
													class="whitespace-nowrap text-accent hover:underline"
													aria-label="View {u.display_name || u.email || 'this reader'}'s profile">View →</a
												>
											</div>
										</li>
									{/each}
							</ul>
						{:else}
							<p class="text-body text-muted">No sign-ups yet.</p>
						{/if}
					</section>
				</div>

				<div class="grid gap-6 md:grid-cols-2">
					<!-- By locale -->
					<section class="rounded-card border border-border bg-surface p-5">
						<h2 class="text-h3 mb-3">Preferred language</h2>
						<ul class="space-y-2">
							{#each d.by_locale as l (l.code)}
								<li class="flex items-center gap-3">
									<span class="w-28 shrink-0 truncate text-body text-text">{l.name} <span class="text-small text-muted">{l.code}</span></span>
									{@render bar(l.count, localeMax)}
									<span class="w-10 shrink-0 text-right text-small tabular-nums text-muted">{fmt(l.count)}</span>
								</li>
							{/each}
						</ul>
					</section>

					<!-- By theme -->
					<section class="rounded-card border border-border bg-surface p-5">
						<h2 class="text-h3 mb-3">Reading theme</h2>
						<ul class="space-y-2">
							{#each d.by_theme as t (t.theme)}
								<li class="flex items-center justify-between gap-3">
									<span class="text-body text-text">{t.label}</span>
									<span class="text-small tabular-nums text-muted">
										<span class="font-semibold text-text">{fmt(t.count)}</span> · {pct(t.count, d.total)}%
									</span>
								</li>
							{/each}
						</ul>
					</section>
				</div>

				<!-- Where readers are (approximate: from the browser timezone) -->
				{#if d.by_country.length || d.by_timezone.length}
					<div class="mt-6 grid gap-6 md:grid-cols-2">
						<!-- By country -->
						<section class="rounded-card border border-border bg-surface p-5">
							<h2 class="text-h3 mb-1">By country</h2>
							<p class="mb-3 text-micro text-muted">
								Approximate — derived from each reader's browser timezone, not their IP.
							</p>
							{#if d.by_country.length}
								<ul class="space-y-2">
									{#each d.by_country as c (c.code)}
										<li class="flex items-center gap-3">
											<span class="w-32 shrink-0 truncate text-body {c.code === 'unknown' ? 'text-muted' : 'text-text'}">
												<span aria-hidden="true">{flag(c.code)}</span> {c.name}
											</span>
											{@render bar(c.count, countryMax)}
											<span class="w-10 shrink-0 text-right text-small tabular-nums text-muted">{fmt(c.count)}</span>
										</li>
									{/each}
								</ul>
							{:else}
								<p class="text-body text-muted">No location signal yet.</p>
							{/if}
						</section>

						<!-- By timezone -->
						<section class="rounded-card border border-border bg-surface p-5">
							<h2 class="text-h3 mb-1">By timezone</h2>
							<p class="mb-3 text-micro text-muted">
								The raw signal behind the countries — and the only one for readers we can't map.
							</p>
							{#if d.by_timezone.length}
								<ul class="space-y-2">
									{#each d.by_timezone as t (t.timezone)}
										<li class="flex items-center gap-3">
											<span class="w-32 shrink-0 truncate text-body text-text" title={t.timezone}>{tzLabel(t.timezone)}</span>
											{@render bar(t.count, tzMax)}
											<span class="w-10 shrink-0 text-right text-small tabular-nums text-muted">{fmt(t.count)}</span>
										</li>
									{/each}
								</ul>
							{:else}
								<p class="text-body text-muted">No timezones recorded yet.</p>
							{/if}
						</section>
					</div>
				{/if}

				<!-- All users: searchable directory (every account, not just the recent 25) -->
				<section class="mt-8 rounded-card border border-border bg-surface p-5">
					<div class="mb-4 flex flex-wrap items-center justify-between gap-3">
						<h2 class="text-h3">All users{#if dir} <span class="text-muted">· {fmt(dir.total)}</span>{/if}</h2>
						<div class="flex items-center gap-2">
							<input
								type="search"
								placeholder="Search name or email…"
								aria-label="Search users"
								class="w-56 rounded-card border border-border bg-surface-2 px-3 py-1.5 text-body text-text"
								value={search}
								oninput={(e) => onSearch(e.currentTarget.value)}
							/>
							<button
								type="button"
								class="btn btn-ghost whitespace-nowrap"
								disabled={exporting || !dir?.total}
								onclick={exportCsv}>{exporting ? 'Exporting…' : 'Export CSV'}</button
							>
						</div>
					</div>
					<div class="mb-3 flex flex-wrap gap-2">
						{#each SORTS as s (s.key)}
							<button
								type="button"
								class="rounded-full px-3 py-1 text-small {dirSort === s.key ? 'bg-accent-soft text-text' : 'text-muted hover:text-text'}"
								aria-pressed={dirSort === s.key}
								onclick={() => setSort(s.key)}>{s.label}</button>
						{/each}
					</div>
					{#if directory.loading && !dir}
						<p class="text-body text-muted">Loading…</p>
					{:else if directory.error}
						<p class="text-body text-warning">{directory.error}</p>
					{:else if dir && dir.results.length}
						<div class="overflow-x-auto">
							<table class="w-full text-start text-small">
								<thead class="text-micro uppercase text-muted">
									<tr class="border-b border-border">
										<th class="py-2 text-start font-semibold">Reader</th>
										<th class="py-2 text-start font-semibold">Sign-in</th>
										<th class="py-2 text-start font-semibold">Lang</th>
										<th class="py-2 text-end font-semibold">Works</th>
										<th class="py-2 text-end font-semibold">Time</th>
										<th class="py-2 text-end font-semibold">Joined</th>
										<th class="py-2 text-end font-semibold">Seen</th>
									</tr>
								</thead>
								<tbody class="divide-y divide-border">
									{#each dir.results as u (u.uid)}
										<tr class="hover:bg-surface-2">
											<td class="py-2 pe-3">
												<a href="/admin/users/{u.uid}" class="font-semibold text-text hover:text-accent hover:underline">{u.display_name || 'Unnamed'}</a>
												<div class="text-micro text-muted">{u.email ? maskEmail(u.email) : '—'}</div>
											</td>
											<td class="py-2 pe-3 text-muted">{u.providers.map((p) => p.label).join(', ') || '—'}</td>
											<td class="py-2 pe-3 text-muted">{u.locale}</td>
											<td class="py-2 ps-3 text-end tabular-nums text-text">{fmt(u.works)}</td>
											<td class="py-2 ps-3 text-end tabular-nums text-text">{formatDuration(u.reading_seconds)}</td>
											<td class="py-2 ps-3 text-end tabular-nums text-muted">{dayFmt(u.joined_at)}</td>
											<td class="py-2 ps-3 text-end tabular-nums text-muted">{dayFmt(u.last_seen_at)}</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
						{#if dir.pages > 1}
							<div class="mt-4 flex items-center justify-between gap-3 text-small text-muted">
								<span>Page {dir.page} of {dir.pages}</span>
								<div class="flex gap-2">
									<button type="button" class="btn btn-ghost" disabled={dir.page <= 1} onclick={() => (dirPage = dir.page - 1)}>Prev</button>
									<button type="button" class="btn btn-ghost" disabled={dir.page >= dir.pages} onclick={() => (dirPage = dir.page + 1)}>Next</button>
								</div>
							</div>
						{/if}
					{:else}
						<p class="text-body text-muted">No users match “{query}”.</p>
					{/if}
				</section>
			{/if}
		{/snippet}
	</AdminGate>
</div>
