<!--
	The dashboard's "how things are moving" (GET /api/admin/trends/): the reader
	pulse as four trend tiles, each language's progress toward its Level 1
	target, and the AI-translation review backlog. Every block links to the
	fuller page its numbers summarise.
-->
<script lang="ts">
	import Sparkline from '$lib/components/Sparkline.svelte';
	import TrendChip from '$lib/components/TrendChip.svelte';
	import { adminReviewHref } from '$lib/adminLinks';
	import { levelProgress, pulseTiles, waitedFor, weekLabel } from '$lib/adminDashboard';
	import type { AdminTrends } from '$lib/library-admin';

	let { trends }: { trends: AdminTrends } = $props();

	const tiles = $derived(pulseTiles(trends.pulse));
	const review = $derived(trends.review);
	const reviewMax = $derived(Math.max(1, ...review.arrived, ...review.approved));
	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number) => nf.format(n);
	const pct = (share: number) => `${Math.round(share * 100)}%`;
	const shortWeek = (iso: string) =>
		new Date(iso + 'T00:00:00').toLocaleDateString('en', { month: 'short', day: 'numeric' });
</script>

<!-- Pulse: the last 7 days against the 7 before, with eight weeks of line. -->
<section class="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4" aria-label="Reader pulse">
	{#each tiles as t (t.label)}
		<a
			href={t.href}
			class="block rounded-card border border-border bg-surface p-5 transition-colors hover:border-accent hover:no-underline"
		>
			<div class="flex items-start justify-between gap-2">
				<div class="stat-number-sm text-text">{t.value}</div>
				<Sparkline values={t.values} labels={t.labels} name={t.label} format={t.format} partial />
			</div>
			<div class="mt-2 flex flex-wrap items-center gap-x-2 text-small font-semibold text-text">
				{t.label}
				<TrendChip trend={t.trend} title="Change vs the 7 days before" />
			</div>
			<div class="text-small text-muted">{t.sub}</div>
		</a>
	{/each}
</section>

<div class="mb-10 grid gap-6 md:grid-cols-2">
	<!-- Progress toward each language's Level 1 target -->
	<section class="rounded-card border border-border bg-surface p-5">
		<div class="mb-1 flex flex-wrap items-baseline justify-between gap-2">
			<h2 class="text-h3">Toward Level 1</h2>
			<a href="/admin/language-health" class="text-small font-semibold text-accent hover:underline">
				Language health →
			</a>
		</div>
		<p class="mb-4 text-small text-muted">
			Published works per language against its Level 1 target, furthest behind first.
		</p>
		{#if trends.languages.length}
			<ul class="space-y-4">
				{#each trends.languages as l (l.code)}
					{@const p = levelProgress(l.level1)}
					<li>
						<div class="flex flex-wrap items-baseline justify-between gap-x-3 text-small">
							<a href="/admin/languages/{l.code}" class="font-semibold text-text hover:text-accent">
								{l.name}
								{#if !l.is_live}<span class="ms-1 text-micro font-semibold uppercase text-muted">
										not live
									</span>{/if}
							</a>
							<span class="tabular-nums text-muted">{p.text} · {p.pct}%</span>
						</div>
						<div
							class="mt-1 h-2 overflow-hidden rounded-full bg-surface-2"
							role="progressbar"
							aria-label="{l.name} Level 1 progress"
							aria-valuemin={0}
							aria-valuemax={l.level1.total}
							aria-valuenow={l.level1.done}
						>
							<div class="h-full rounded-full bg-accent" style="width: {p.pct}%"></div>
						</div>
						<div
							class="mt-1 flex flex-wrap items-center justify-between gap-x-3 text-micro text-muted"
						>
							<span>
								{#if l.reviewed_share === null}
									No AI translations
								{:else}
									{pct(l.reviewed_share)} of {fmt(l.ai_translations)} AI translations reviewed
								{/if}
							</span>
							{#if l.health.length > 1}
								<span class="inline-flex items-center gap-1">
									health
									<Sparkline
										values={l.health}
										labels={l.health.map((_, i) => `day ${i + 1}`)}
										name="{l.name} health"
										description="{l.name} health score, latest {l.health[l.health.length - 1]}"
										width={56}
										height={16}
									/>
								</span>
							{/if}
						</div>
					</li>
				{/each}
			</ul>
		{:else}
			<p class="text-body text-muted">No target languages yet.</p>
		{/if}
	</section>

	<!-- Review backlog -->
	<section class="rounded-card border border-border bg-surface p-5">
		<div class="mb-1 flex flex-wrap items-baseline justify-between gap-2">
			<h2 class="text-h3">Review backlog</h2>
			<a href="/admin/review" class="text-small font-semibold text-accent hover:underline">
				Review queue →
			</a>
		</div>
		<p class="mb-4 text-small text-muted">
			AI-translated books and sermons waiting on a native reviewer.
		</p>
		<div class="flex flex-wrap items-baseline gap-x-6 gap-y-2">
			<div>
				<div class="stat-number-sm text-text">{fmt(review.waiting)}</div>
				<div class="text-small text-muted">waiting</div>
			</div>
			{#if review.oldest}
				<div class="min-w-0 flex-1 text-small">
					<span class="text-muted">Oldest, waiting {waitedFor(review.oldest.created_at)}:</span>
					<a
						href={adminReviewHref(review.oldest.kind, review.oldest.slug, review.oldest.language)}
						class="block truncate font-semibold text-text hover:text-accent"
					>
						{review.oldest.title}
						<span class="font-normal text-muted">({review.oldest.language})</span>
					</a>
				</div>
			{/if}
		</div>

		<!-- Each week: AI translations that arrived beside approvals confirmed. -->
		<div class="mt-5">
			<div class="mb-2 flex gap-4 text-micro text-muted" aria-hidden="true">
				<span class="inline-flex items-center gap-1">
					<span class="h-2 w-2 rounded-sm bg-warning"></span>Arrived
				</span>
				<span class="inline-flex items-center gap-1">
					<span class="h-2 w-2 rounded-sm bg-accent"></span>Approved
				</span>
			</div>
			<ol
				class="flex h-24 items-end gap-1.5"
				aria-label="AI translations arrived and approved per week"
			>
				{#each review.weeks as w, i (w)}
					<li
						class="flex h-full flex-1 flex-col justify-end"
						title="{weekLabel(w)}: {fmt(review.arrived[i])} arrived, {fmt(
							review.approved[i]
						)} approved"
					>
						<span class="sr-only">
							{weekLabel(w)}: {review.arrived[i]} arrived, {review.approved[i]} approved
						</span>
						<div class="flex h-full items-end gap-0.5" aria-hidden="true">
							<div
								class="flex-1 rounded-t-sm bg-warning"
								style="height: {(review.arrived[i] / reviewMax) * 100}%"
							></div>
							<div
								class="flex-1 rounded-t-sm bg-accent"
								style="height: {(review.approved[i] / reviewMax) * 100}%"
							></div>
						</div>
					</li>
				{/each}
			</ol>
			<div class="mt-1 flex justify-between text-micro text-muted" aria-hidden="true">
				<span>{shortWeek(review.weeks[0])}</span>
				<span>this week</span>
			</div>
			{#if !review.first_decision}
				<p class="mt-2 text-micro text-muted">No review decisions recorded yet.</p>
			{/if}
		</div>
	</section>
</div>
