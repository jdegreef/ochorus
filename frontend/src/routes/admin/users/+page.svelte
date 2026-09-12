<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import TrendChip from '$lib/components/TrendChip.svelte';
	import { getAdminUsers, periodTrend, type Trend } from '$lib/library-admin';

	const users = adminResource(getAdminUsers, 'Something went wrong loading users.');
	const data = $derived(users.data);

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
	function maskEmail(email: string): string {
		const at = email.indexOf('@');
		if (at <= 0) return '•••';
		const local = email.slice(0, at);
		return `${local.slice(0, 1)}${'•'.repeat(Math.max(3, local.length - 1))}${email.slice(at)}`;
	}
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
								<!-- Keyed by position: the list is replaced wholesale on each load
							     and the payload carries no stable id, so email+date could
							     collide (blank emails, same timestamp). -->
							{#each d.recent as u, i (i)}
									<li class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-2.5">
										<div class="min-w-0">
											{#if u.display_name}
												<div class="truncate font-semibold text-text">{u.display_name}</div>
												{@render emailCell(u.email, i, 'text-small text-muted')}
											{:else}
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
			{/if}
		{/snippet}
	</AdminGate>
</div>
