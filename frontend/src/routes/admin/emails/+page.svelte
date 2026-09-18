<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { getAdminEmailMetrics, type EmailMetricRow } from '$lib/library-admin';

	// Both by_step and by_broadcast rows share the metric fields; the label comes
	// from either `step` or `name`, so one table snippet serves both.
	type RateRow = EmailMetricRow & { step?: string; name?: string; id?: number };

	const metrics = adminResource(getAdminEmailMetrics, 'Something went wrong loading email metrics.');
	const data = $derived(metrics.data);

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number | null | undefined) => nf.format(n ?? 0);
	const pct = (r: number | null | undefined) => `${((r ?? 0) * 100).toFixed(1)}%`;

	// Friendly labels for the lifecycle step keys; an unmapped step is title-cased
	// so a newly added step still reads sensibly.
	const stepLabels: Record<string, string> = {
		welcome: 'Welcome',
		pick_plan: 'Pick a plan',
		classic: 'A classic',
		comeback: 'Come back'
	};
	const stepLabel = (s: string) =>
		stepLabels[s] ?? s.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());

	// Headline tiles from the overview rollup. Click rate is the reliable signal;
	// opens are undercounted by inbox privacy proxies (noted below the tiles).
	const tiles = $derived<{ label: string; value: string; sub: string }[]>(
		data
			? [
					{ label: 'Sent', value: fmt(data.overview.sent), sub: `${fmt(data.overview.delivered)} delivered` },
					{ label: 'Open rate', value: pct(data.overview.open_rate), sub: `${fmt(data.overview.opens)} opened` },
					{ label: 'Click rate', value: pct(data.overview.click_rate), sub: `${fmt(data.overview.clicks)} clicked` },
					{ label: 'Bounce rate', value: pct(data.overview.bounce_rate), sub: `${fmt(data.overview.bounces)} bounced` },
					{ label: 'Complaints', value: pct(data.overview.complaint_rate), sub: `${fmt(data.overview.complaints)} marked spam` },
					{ label: 'Failed', value: fmt(data.overview.failed), sub: 'send errors' }
				]
			: []
	);

	const subTiles = $derived(
		data
			? [
					{ label: 'Subscribers', value: fmt(data.subscribers.newsletter_opt_in), sub: `of ${fmt(data.subscribers.total)} with an account` },
					{ label: 'Unsubscribed', value: fmt(data.subscribers.unsubscribed), sub: 'opted out of everything' },
					{ label: 'Suppressed', value: fmt(data.subscribers.suppressed), sub: 'bounced or complained' }
				]
			: []
	);
</script>

<svelte:head><title>Admin · Emails — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-5xl px-5 py-10">
	<header class="mb-6 flex flex-wrap items-end justify-between gap-3">
		<div>
			<p class="eyebrow mb-2 text-accent">Admin</p>
			<h1 class="text-h1">Emails</h1>
			<p class="mt-2 max-w-prose text-body text-muted">
				Open, click, and bounce rates for lifecycle emails and broadcasts — aggregate counts only, no recipient identities.
			</p>
			<span class="privacy-badge mt-3 inline-flex items-center gap-2 text-small text-muted">
				<span class="privacy-dot" aria-hidden="true"></span>
				Aggregate only · no individual recipients
			</span>
		</div>
		{#if data}
			<button class="btn btn-ghost btn-sm" onclick={metrics.load} disabled={metrics.loading}
				>{metrics.loading ? 'Refreshing…' : 'Refresh'}</button
			>
		{/if}
	</header>

	<AdminGate resource={metrics} errorTitle="Couldn't load email metrics">
		{#snippet children(d)}
			{#if d.overview.sent === 0}
				<div class="rounded-card border border-border bg-surface p-8 text-center">
					<p class="text-h3">No emails sent yet</p>
					<p class="mt-1 text-body text-muted">
						Once the lifecycle sweep sends its first email (with <code>EMAIL_ENABLED</code> on), open and click rates show up here.
					</p>
				</div>
			{:else}
				<!-- Overview -->
				<p class="section-label">Overview</p>
				<section class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
					{#each tiles as t (t.label)}
						<div class="rounded-card border border-border bg-surface p-4">
							<div class="stat-number">{t.value}</div>
							<div class="mt-2 text-small font-semibold text-text">{t.label}</div>
							<div class="text-small text-muted">{t.sub}</div>
						</div>
					{/each}
				</section>
				<p class="mt-3 text-micro text-muted">
					Open rate is directional — inbox privacy proxies (Apple Mail, Gmail image caching) inflate or hide opens. Click rate is the reliable engagement signal.
				</p>

				<!-- Subscribers -->
				<p class="section-label mt-8">Subscribers</p>
				<section class="grid grid-cols-3 gap-3">
					{#each subTiles as t (t.label)}
						<div class="rounded-card border border-border bg-surface p-4">
							<div class="stat-number">{t.value}</div>
							<div class="mt-2 text-small font-semibold text-text">{t.label}</div>
							<div class="text-small text-muted">{t.sub}</div>
						</div>
					{/each}
				</section>

				<!-- By lifecycle step -->
				<section class="mt-8 rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3 mb-4">By lifecycle step</h2>
					{#if d.by_step.length === 0}
						<p class="text-body text-muted">No lifecycle emails sent yet.</p>
					{:else}
						{@render rateTable(d.by_step, (r) => stepLabel(r.step ?? ''))}
					{/if}
				</section>

				<!-- By broadcast -->
				{#if d.by_broadcast.length}
					<section class="mt-8 rounded-card border border-border bg-surface p-5">
						<h2 class="text-h3 mb-4">By broadcast</h2>
						{@render rateTable(d.by_broadcast, (r) => r.name ?? '')}
					</section>
				{/if}
			{/if}
		{/snippet}
	</AdminGate>
</div>

{#snippet rateTable(rows: RateRow[], label: (r: RateRow) => string)}
	<div class="overflow-x-auto">
		<table class="w-full text-small tabular-nums">
			<thead>
				<tr class="border-b border-border text-left text-muted">
					<th class="py-2 pr-3 font-semibold">Email</th>
					<th class="py-2 pr-3 text-right font-semibold">Sent</th>
					<th class="py-2 pr-3 text-right font-semibold">Delivered</th>
					<th class="py-2 pr-3 text-right font-semibold">Open rate</th>
					<th class="py-2 pr-3 text-right font-semibold">Click rate</th>
					<th class="py-2 text-right font-semibold">Bounce rate</th>
				</tr>
			</thead>
			<tbody>
				{#each rows as r (r.id ?? r.step ?? r.name)}
					<tr class="border-b border-border/50">
						<td class="py-2 pr-3 font-medium text-text">{label(r)}</td>
						<td class="py-2 pr-3 text-right">{fmt(r.sent)}</td>
						<td class="py-2 pr-3 text-right">{fmt(r.delivered)}</td>
						<td class="py-2 pr-3 text-right">{pct(r.open_rate)} <span class="text-muted">({fmt(r.opens)})</span></td>
						<td class="py-2 pr-3 text-right">{pct(r.click_rate)} <span class="text-muted">({fmt(r.clicks)})</span></td>
						<td class="py-2 text-right">{pct(r.bounce_rate)} <span class="text-muted">({fmt(r.bounces)})</span></td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/snippet}
