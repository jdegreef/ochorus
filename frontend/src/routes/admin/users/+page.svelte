<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { getAdminUsers } from '$lib/library-admin';

	const users = adminResource(getAdminUsers, 'Something went wrong loading users.');
	const data = $derived(users.data);

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number | null | undefined) => nf.format(n ?? 0);
	const weekLabel = (iso: string) =>
		new Date(iso + 'T00:00:00').toLocaleDateString('en', { month: 'short', day: 'numeric' });
	const pct = (n: number, total: number) => (total ? Math.round((n / total) * 100) : 0);
	const dayFmt = (iso: string | null) =>
		iso ? new Date(iso).toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' }) : '—';

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
							<div class="stat-number">{fmt(c.value)}</div>
							<div class="mt-2 text-small font-semibold text-text">{c.label}</div>
							<div class="text-small text-muted">{c.sub}</div>
						</div>
					{/each}
				</section>

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
									<li class="flex items-center justify-between gap-3">
										<span class="text-body {m.method === 'unknown' ? 'text-muted' : 'text-text'}"
											>{m.label}</span
										>
										<span class="font-semibold tabular-nums text-text">{fmt(m.count)}</span>
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
						<h2 class="text-h3 mb-3">Recent sign-ups</h2>
						{#if d.recent.length}
							<ul class="divide-y divide-border">
								<!-- Keyed by position: the list is replaced wholesale on each load
							     and the payload carries no stable id, so email+date could
							     collide (blank emails, same timestamp). -->
							{#each d.recent as u, i (i)}
									<li class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-2.5">
										<div class="min-w-0">
											{#if u.display_name}
												<div class="truncate font-semibold text-text">{u.display_name}</div>
												<div class="truncate text-small text-muted">{u.email || '—'}</div>
											{:else}
												<div class="truncate font-semibold text-text">{u.email || '—'}</div>
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
									<div class="h-3 flex-1 overflow-hidden rounded-full bg-surface-2">
										<div class="h-full rounded-full bg-accent-soft" style="width: {(l.count / localeMax) * 100}%"></div>
									</div>
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
			{/if}
		{/snippet}
	</AdminGate>
</div>
