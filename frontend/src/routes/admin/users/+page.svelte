<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { ApiError } from '$lib/api';
	import { getAdminUsers, type AdminUsers } from '$lib/library';

	let data = $state<AdminUsers | null>(null);
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
			const result = await getAdminUsers();
			if (id !== seq) return;
			data = result;
		} catch (e) {
			if (id !== seq) return;
			if (e instanceof ApiError && (e.status === 401 || e.status === 403)) denied = true;
			else error = e instanceof Error ? e.message : 'Something went wrong loading users.';
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
	const pct = (n: number, total: number) => (total ? Math.round((n / total) * 100) : 0);

	const cards = $derived(
		data
			? [
					{ label: 'Registered users', value: data.total, sub: 'total accounts' },
					{ label: 'Activated', value: data.with_activity, sub: `${pct(data.with_activity, data.total)}% have read` },
					{ label: 'Dormant', value: data.dormant, sub: 'no reading yet' },
					{ label: 'New · 7d', value: data.signups_7d, sub: 'this week' },
					{ label: 'New · 30d', value: data.signups_30d, sub: 'this month' }
				]
			: []
	);

	const signupMax = $derived(Math.max(1, ...(data?.weekly_signups.map((w) => w.count) ?? [1])));
	const localeMax = $derived(Math.max(1, ...(data?.by_locale.map((l) => l.count) ?? [1])));
</script>

<svelte:head><title>Admin · Users — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-5xl px-5 py-10">
	<header class="mb-6 flex flex-wrap items-end justify-between gap-3">
		<div>
			<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">Admin</p>
			<h1 class="text-display">Users</h1>
			<p class="mt-2 text-body text-muted">Account growth and make-up. Aggregate counts only — no personal data.</p>
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
			<h2 class="text-h3 mb-2">Couldn't load users</h2>
			<p class="mb-5 text-body text-muted">{error}</p>
			<button class="btn btn-ghost" onclick={load}>Try again</button>
		</div>
	{:else if data}
		{@const d = data}
		{#if d.total === 0}
			<div class="rounded-2xl border border-border bg-surface p-8 text-center">
				<p class="text-h3">No accounts yet</p>
				<p class="mt-1 text-body text-muted">Sign-ups will appear here once readers create accounts.</p>
			</div>
		{:else}
			<!-- Overview -->
			<section class="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
				{#each cards as c (c.label)}
					<div class="rounded-2xl border border-border bg-surface p-4">
						<div class="text-display !text-3xl !leading-none text-text">{fmt(c.value)}</div>
						<div class="mt-2 text-small font-semibold text-text">{c.label}</div>
						<div class="text-small text-muted">{c.sub}</div>
					</div>
				{/each}
			</section>

			<!-- Weekly signups -->
			<section class="mb-8 rounded-2xl border border-border bg-surface p-5">
				<h2 class="text-h3 mb-4">New sign-ups per week</h2>
				<div class="flex items-end gap-1.5" style="height: 8rem">
					{#each d.weekly_signups as w (w.week)}
						<div class="flex flex-1 flex-col items-center gap-1">
							<div class="text-small tabular-nums text-muted">{w.count || ''}</div>
							<div
								class="w-full rounded-t bg-accent-soft"
								style="height: {(w.count / signupMax) * 100}%; min-height: {w.count ? '3px' : '0'}"
							></div>
							<div class="text-micro text-muted">{weekLabel(w.week)}</div>
						</div>
					{/each}
				</div>
			</section>

			<div class="grid gap-6 md:grid-cols-2">
				<!-- By locale -->
				<section class="rounded-2xl border border-border bg-surface p-5">
					<h2 class="text-h3 mb-3">Preferred language</h2>
					<ul class="space-y-2">
						{#each d.by_locale as l (l.code)}
							<li class="flex items-center gap-3">
								<span class="w-28 shrink-0 truncate text-body text-text">{l.name} <span class="text-small text-muted">{l.code}</span></span>
								<div class="h-3 flex-1 overflow-hidden rounded-full bg-surface-2">
									<div class="h-full rounded-full bg-accent-soft" style="width: {(l.count / localeMax) * 100}%"></div>
								</div>
								<span class="w-10 shrink-0 text-right text-small tabular-nums text-muted">{fmt(l.count)}</span>
							</li>
						{/each}
					</ul>
				</section>

				<!-- By theme -->
				<section class="rounded-2xl border border-border bg-surface p-5">
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
		{/if}
	{/if}
</div>
