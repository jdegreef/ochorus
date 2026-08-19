<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { ApiError } from '$lib/api';
	import { getAdminEngagement, type AdminEngagement } from '$lib/library';

	let data = $state<AdminEngagement | null>(null);
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
			const result = await getAdminEngagement();
			if (id !== seq) return;
			data = result;
		} catch (e) {
			if (id !== seq) return;
			if (e instanceof ApiError && (e.status === 401 || e.status === 403)) denied = true;
			else error = e instanceof Error ? e.message : 'Something went wrong loading engagement.';
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
	const weekLabel = (iso: string) =>
		new Date(iso + 'T00:00:00').toLocaleDateString('en', { month: 'short', day: 'numeric' });

	const cards = $derived(
		data
			? [
					{ label: 'Readers', value: data.overview.readers, sub: 'with saved progress' },
					{ label: 'Active · 7d', value: data.overview.active_7d, sub: `${fmt(data.overview.active_1d)} today` },
					{ label: 'Active · 30d', value: data.overview.active_30d, sub: 'in the last month' },
					{ label: 'Marked chapters', value: data.overview.marked_chapters, sub: `${fmt(data.overview.readers_with_marks)} readers` },
					{ label: 'Registered users', value: data.overview.total_users, sub: 'accounts' }
				]
			: []
	);

	const weekMax = $derived(Math.max(1, ...(data?.weekly_active.map((w) => w.readers) ?? [1])));
	const langMax = $derived(Math.max(1, ...(data?.by_language.map((l) => l.readers) ?? [1])));
</script>

<svelte:head><title>Admin · Engagement — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-5xl px-5 py-10">
	<header class="mb-6 flex flex-wrap items-end justify-between gap-3">
		<div>
			<p class="eyebrow mb-2 text-accent">Admin</p>
			<h1 class="text-display">Engagement</h1>
			<p class="mt-2 text-body text-muted">What readers are reading. Aggregate counts only — no personal data.</p>
		</div>
		{#if data}
			<button class="btn btn-ghost" onclick={load} disabled={loading}>{loading ? 'Refreshing…' : 'Refresh'}</button>
		{/if}
	</header>

	{#if loading && !data}
		<p class="text-body text-muted">Loading…</p>
	{:else if denied}
		<div class="rounded-card border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">Not authorised</h2>
			<p class="text-body text-muted">You don't have access to the admin dashboard.</p>
		</div>
	{:else if error}
		<div class="rounded-card border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">Couldn't load engagement</h2>
			<p class="mb-5 text-body text-muted">{error}</p>
			<button class="btn btn-ghost" onclick={load}>Try again</button>
		</div>
	{:else if data}
		{@const d = data}
		{#if d.overview.readers === 0}
			<div class="rounded-card border border-border bg-surface p-8 text-center">
				<p class="text-h3">No reading activity yet</p>
				<p class="mt-1 text-body text-muted">Once signed-in readers start reading, their (anonymous, aggregate) activity shows up here.</p>
			</div>
		{:else}
			<!-- Overview -->
			<section class="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
				{#each cards as c (c.label)}
					<div class="rounded-card border border-border bg-surface p-4">
						<div class="stat-number">{fmt(c.value)}</div>
						<div class="mt-2 text-small font-semibold text-text">{c.label}</div>
						<div class="text-small text-muted">{c.sub}</div>
					</div>
				{/each}
			</section>

			<!-- Weekly active -->
			<section class="mb-8 rounded-card border border-border bg-surface p-5">
				<h2 class="text-h3 mb-4">Weekly active readers</h2>
				<div class="flex items-end gap-2" style="height: 8rem">
					{#each d.weekly_active as w (w.week)}
						<div class="flex flex-1 flex-col items-center gap-1">
							<div class="text-small tabular-nums text-muted">{w.readers || ''}</div>
							<div
								class="w-full rounded-t-sm bg-accent-soft"
								style="height: {(w.readers / weekMax) * 100}%; min-height: {w.readers ? '3px' : '0'}"
							></div>
							<div class="text-micro text-muted">{weekLabel(w.week)}</div>
						</div>
					{/each}
				</div>
			</section>

			<div class="grid gap-6 lg:grid-cols-2">
				<!-- Most read -->
				<section class="rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3 mb-3">Most read</h2>
					{#if d.most_read.length}
						<ul class="space-y-2">
							{#each d.most_read as b (b.slug)}
								<li class="flex items-baseline justify-between gap-3">
									<a href="/books/{b.slug}" class="min-w-0 truncate text-body text-text hover:text-accent">
										{b.title}<span class="text-small text-muted"> · {b.author}</span>
									</a>
									<span class="shrink-0 text-small text-muted tabular-nums">
										<span class="font-semibold text-text">{fmt(b.readers)}</span> readers{#if b.finishers} · {fmt(b.finishers)} finished{/if}
									</span>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="text-body text-muted">No data yet.</p>
					{/if}
				</section>

				<!-- Most marked -->
				<section class="rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3 mb-3">Most highlighted</h2>
					{#if d.most_marked.length}
						<ul class="space-y-2">
							{#each d.most_marked as b (b.slug)}
								<li class="flex items-baseline justify-between gap-3">
									<a href="/books/{b.slug}" class="min-w-0 truncate text-body text-text hover:text-accent">
										{b.title}<span class="text-small text-muted"> · {b.author}</span>
									</a>
									<span class="shrink-0 text-small text-muted tabular-nums">
										<span class="font-semibold text-text">{fmt(b.readers)}</span> readers · {fmt(b.chapters)} ch
									</span>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="text-body text-muted">No highlights yet.</p>
					{/if}
				</section>
			</div>

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
	{/if}
</div>
