<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { ApiError } from '$lib/api';
	import { getAdminSearchStats, type AdminSearchStats } from '$lib/library';

	let data = $state<AdminSearchStats | null>(null);
	let loading = $state(true);
	let denied = $state(false);
	let error = $state<string | null>(null);
	let seq = 0;

	async function load() {
		const id = ++seq;
		loading = true;
		denied = false;
		error = null;
		try {
			const result = await getAdminSearchStats();
			if (id !== seq) return;
			data = result;
		} catch (e) {
			if (id !== seq) return;
			if (e instanceof ApiError && (e.status === 401 || e.status === 403)) denied = true;
			else error = e instanceof Error ? e.message : 'Something went wrong loading search stats.';
		} finally {
			if (id === seq) loading = false;
		}
	}

	$effect(() => {
		if (auth.enabled && !auth.initialized) return;
		void auth.user?.email;
		load();
	});

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
					{ label: 'Zero results · 30d', value: data.overview['30d'].zero_results, sub: `${pct(data.overview['30d'].zero_rate)} of searches` }
				]
			: []
	);

	const dayMax = $derived(Math.max(1, ...(data?.daily.map((d) => d.searches) ?? [1])));
	const langMax = $derived(Math.max(1, ...(data?.by_language.map((l) => l.searches) ?? [1])));
</script>

<svelte:head><title>Admin · Search — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-5xl px-5 py-10">
	<header class="mb-6 flex flex-wrap items-end justify-between gap-3">
		<div>
			<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">Admin</p>
			<h1 class="text-display">Search</h1>
			<p class="mt-2 text-body text-muted">
				What readers look for — and what they don't find. Anonymous queries only.
			</p>
		</div>
		{#if data}
			<button class="btn btn-ghost" onclick={load} disabled={loading}>{loading ? 'Refreshing…' : 'Refresh'}</button>
		{/if}
	</header>

	{#if loading && !data}
		<p class="text-body text-muted">Loading…</p>
	{:else if denied}
		<div class="rounded-2xl border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">Not authorised</h2>
			<p class="text-body text-muted">You don't have access to the admin dashboard.</p>
		</div>
	{:else if error}
		<div class="rounded-2xl border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">Couldn't load search stats</h2>
			<p class="mb-5 text-body text-muted">{error}</p>
			<button class="btn btn-ghost" onclick={load}>Try again</button>
		</div>
	{:else if data}
		{@const d = data}
		{#if d.overview['30d'].searches === 0}
			<div class="rounded-2xl border border-border bg-surface p-8 text-center">
				<p class="text-h3">No searches logged yet</p>
				<p class="mt-1 text-body text-muted">
					Once readers use search, their (anonymous) queries show up here — zero-result queries are
					the best signal for what content to add next.
				</p>
			</div>
		{:else}
			<!-- Overview -->
			<section class="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
				{#each cards as c (c.label)}
					<div class="rounded-2xl border border-border bg-surface p-4">
						<div class="text-display !text-3xl !leading-none text-text">{fmt(c.value)}</div>
						<div class="mt-2 text-small font-semibold text-text">{c.label}</div>
						<div class="text-small text-muted">{c.sub}</div>
					</div>
				{/each}
			</section>

			<!-- Daily volume -->
			<section class="mb-8 rounded-2xl border border-border bg-surface p-5">
				<h2 class="text-h3 mb-1">Daily searches</h2>
				<p class="mb-4 text-small text-muted">Last 14 days; the darker segment is zero-result searches.</p>
				<div class="flex items-end gap-2" style="height: 8rem">
					{#each d.daily as day (day.day)}
						<div class="flex flex-1 flex-col items-center gap-1">
							<div class="text-small tabular-nums text-muted">{day.searches || ''}</div>
							<div
								class="flex w-full flex-col justify-end overflow-hidden rounded-t"
								style="height: {(day.searches / dayMax) * 100}%; min-height: {day.searches ? '3px' : '0'}"
							>
								<div class="w-full flex-1 bg-accent-soft"></div>
								{#if day.zero}
									<div class="w-full bg-accent" style="height: {(day.zero / day.searches) * 100}%"></div>
								{/if}
							</div>
							<div class="text-[0.7rem] text-muted">{dayLabel(day.day)}</div>
						</div>
					{/each}
				</div>
			</section>

			<div class="grid gap-6 lg:grid-cols-2">
				<!-- Top queries -->
				<section class="rounded-2xl border border-border bg-surface p-5">
					<h2 class="text-h3 mb-3">Top queries · 30d</h2>
					{#if d.top_queries.length}
						<ul class="space-y-2">
							{#each d.top_queries as q (q.query)}
								<li class="flex items-baseline justify-between gap-3">
									<a href="/search?q={encodeURIComponent(q.query)}" class="min-w-0 truncate text-body text-text hover:text-accent">
										{q.query}
									</a>
									<span class="shrink-0 text-small tabular-nums text-muted">{fmt(q.count)}</span>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="text-body text-muted">No queries yet.</p>
					{/if}
				</section>

				<!-- Zero-result queries -->
				<section class="rounded-2xl border border-border bg-surface p-5">
					<h2 class="text-h3 mb-1">Zero results · 30d</h2>
					<p class="mb-3 text-small text-muted">Each of these is a reader asking for something the library doesn't have (or can't find) yet.</p>
					{#if d.zero_result_queries.length}
						<ul class="space-y-2">
							{#each d.zero_result_queries as q (q.query)}
								<li class="flex items-baseline justify-between gap-3">
									<a href="/search?q={encodeURIComponent(q.query)}" class="min-w-0 truncate text-body text-text hover:text-accent">
										{q.query}
									</a>
									<span class="shrink-0 text-small tabular-nums text-muted">{fmt(q.count)}</span>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="text-body text-muted">Nothing missed — every search found something.</p>
					{/if}
				</section>
			</div>

			<!-- By language -->
			<section class="mt-6 rounded-2xl border border-border bg-surface p-5">
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
	{/if}
</div>
