<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import {
		getAdminLanguageHealth,
		type AdminLanguageHealth,
		type HealthScoreKey,
		type HealthWeights
	} from '$lib/library-admin';
	import {
		BAND_FAIR,
		BAND_STRONG,
		HEALTH_KEYS,
		blockers,
		healthBand,
		nextActions,
		plural,
		pointsBreakdown
	} from '$lib/languageHealth';

	const res = adminResource(getAdminLanguageHealth, 'Something went wrong loading language health.');

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number) => nf.format(n);
	const pts = (n: number) => (n >= 10 ? Math.round(n).toString() : n.toFixed(1).replace(/\.0$/, ''));
	// One book is worth a fraction of a point — two places keep 0.17 and 0.38 apart.
	const perBook = (n: number) => n.toFixed(2);

	// What each ingredient measures, for "How the score works".
	const COMPONENTS: Record<HealthScoreKey, { label: string; hint: string }> = {
		readiness: { label: 'Readiness', hint: 'share of the go-live checks met' },
		coverage: { label: 'Coverage', hint: 'books here ÷ the English shelf' },
		review: { label: 'Review', hint: 'share of translations a human has confirmed' },
		engagement: { label: 'Engagement', hint: 'readers, against a fixed target' }
	};

	const BAND_INK = { accent: 'text-accent', text: 'text-text', warning: 'text-warning' } as const;
	const BAND_CHIP = {
		accent: 'border-accent-soft-border bg-accent-soft text-accent',
		text: 'border-border text-muted',
		warning: 'border-warning/40 text-warning'
	} as const;

	// The raw count behind each bar, so a percentage never hides the size of the job.
	function countLine(
		key: HealthScoreKey,
		l: AdminLanguageHealth,
		sourceBooks: number,
		engagementTarget: number | undefined
	): string {
		switch (key) {
			case 'readiness':
				return l.readiness.ready ? 'all checks met' : `${fmt(l.readiness.blocking.length)} blocking`;
			case 'coverage':
				return `${fmt(l.content.published_books)} of ${fmt(sourceBooks)} books`;
			case 'review': {
				const total = l.content.published_books;
				return total ? `${fmt(total - l.content.unreviewed_books)} of ${fmt(total)} reviewed` : 'nothing to review';
			}
			case 'engagement':
				return engagementTarget
					? `${fmt(l.readers)} of ${plural(engagementTarget, 'reader')}`
					: plural(l.readers, 'reader');
		}
	}

	const formula = (w: HealthWeights) =>
		HEALTH_KEYS.map((k) => `${Math.round(w[k] * 100)} × ${COMPONENTS[k].label.toLowerCase()}`).join(' + ');
</script>

{#snippet contentLine(l: AdminLanguageHealth)}
	{fmt(l.content.published_books)} books · {fmt(l.content.sermons)} sermons · {fmt(l.content.bios)} bios ·
	{fmt(l.content.plans)} plans · {plural(l.readers, 'reader')}
{/snippet}

<svelte:head><title>Admin · Language health — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<AdminGate resource={res} errorTitle="Couldn't load language health" loadingText="Loading…" panelClass="mt-6">
		{#snippet children(data)}
			{@const sources = data.languages.filter((l) => l.is_source)}
			{@const ranked = data.languages.filter((l) => !l.is_source)}
			<header class="mb-6 mt-3">
				<p class="eyebrow mb-2 text-accent">Admin · Health</p>
				<h1 class="text-display">Language health</h1>
				<p class="mt-2 text-body text-muted">
					Each translation scored out of 100, ranked. Every row names the work worth the most points next.
				</p>
				<details class="mt-4 rounded-card border border-border bg-surface px-4 py-3">
					<summary class="cursor-pointer text-small font-semibold text-text">How the score works</summary>
					<p class="mt-2 rounded bg-surface-2 px-3 py-2 font-mono text-micro text-text">{formula(data.weights)}</p>
					<ul class="mt-2 flex flex-col gap-1 text-small text-muted">
						{#each HEALTH_KEYS as k (k)}
							<li>
								<span class="font-semibold text-text">{COMPONENTS[k].label}</span>
								({Math.round(data.weights[k] * 100)} pts): {COMPONENTS[k].hint}{k === 'coverage'
									? ` (${fmt(data.source_published_books)} books)`
									: k === 'engagement' && data.engagement_target
										? ` of ${plural(data.engagement_target, 'reader')}, so another language's readers never move this score`
										: ''}.
							</li>
						{/each}
					</ul>
					<p class="mt-2 text-small text-muted">
						Bands: <span class="text-accent">Strong</span> ≥ {BAND_STRONG} · Fair {BAND_FAIR}–{BAND_STRONG - 1} ·
						<span class="text-warning">Weak</span> &lt; {BAND_FAIR}. English is the source the others are measured
						against, so it is shown as the reference, not ranked.
					</p>
				</details>
			</header>

			<!-- The source shelf: the target every translation is measured against. -->
			{#each sources as s (s.code)}
				<div class="mb-4 flex flex-wrap items-center gap-x-4 gap-y-1 rounded-card bg-surface-2 px-4 py-3">
					<span class="rounded-full bg-accent-soft px-2 py-0.5 text-micro text-accent">source</span>
					<a href="/admin/languages/{s.code}" class="font-semibold text-text hover:text-accent">{s.name}</a>
					<span class="text-small tabular-nums text-muted">{@render contentLine(s)}</span>
					{#if s.content.unreviewed_books}
						<span class="text-small text-warning">{fmt(s.content.unreviewed_books)} awaiting review</span>
					{/if}
				</div>
			{/each}

			<ol class="flex flex-col gap-3">
				{#each ranked as l, i (l.code)}
					{@const b = healthBand(l.health)}
					{@const breakdown = pointsBreakdown(l.scores, data.weights)}
					{@const actions = nextActions(l, data.source_published_books, data.weights)}
					<li class="rounded-card border border-border bg-surface p-4">
						<div class="flex items-start justify-between gap-4">
							<div class="min-w-0">
								<div class="flex flex-wrap items-baseline gap-x-2 gap-y-1">
									<span class="text-small tabular-nums text-muted">#{i + 1}</span>
									<a href="/admin/languages/{l.code}" class="font-semibold text-text hover:text-accent">{l.name}</a>
									<span class="text-small text-muted">{l.native_name}</span>
									<!-- Status knows whether the language is live: a live one only
									     needs telling about a check that has since failed. -->
									{#if l.is_live && l.readiness.ready}
										<span class="rounded-full border border-accent-soft-border px-2 py-0.5 text-micro text-accent">Live</span>
									{:else if l.is_live}
										<span class="rounded-full border border-warning/40 px-2 py-0.5 text-micro text-warning"
											>Live · failing: {blockers(l).map((c) => c.label).join(', ')}</span
										>
									{:else if l.readiness.ready}
										<a
											href="/admin/languages/{l.code}#sec-readiness"
											class="rounded-full border border-accent/40 bg-accent-soft px-2 py-0.5 text-micro text-accent hover:underline"
											>Ready to launch →</a
										>
									{:else}
										<span class="rounded-full border border-border px-2 py-0.5 text-micro text-muted">Not live</span>
										{#each blockers(l) as c (c.key)}
											<span class="rounded-full border border-warning/40 px-2 py-0.5 text-micro text-warning"
												>{c.label}</span
											>
										{/each}
									{/if}
								</div>
								<p class="mt-1 text-small text-muted">{@render contentLine(l)}</p>
							</div>
							<div class="shrink-0 text-end">
								<span class="text-h2 tabular-nums {BAND_INK[b.tone]}">{l.health}</span>
								<span class="block text-micro text-muted">/ 100</span>
								<span class="mt-1 inline-block rounded-full border px-2 py-0.5 text-micro {BAND_CHIP[b.tone]}"
									>{b.label}</span
								>
							</div>
						</div>

						<!-- One bar of 100 points: each signal's track is as wide as its
						     weight, filled to what it earned. On a phone the tracks would be
						     too narrow for their labels, so they fall back to a 2×2 grid. -->
						<div
							class="mt-3 grid grid-cols-2 gap-x-1.5 gap-y-2 sm:[grid-template-columns:var(--weighted)]"
							style="--weighted: {breakdown.map((p) => `${p.max}fr`).join(' ')}"
						>
							{#each breakdown as p (p.key)}
								{@const line = countLine(p.key, l, data.source_published_books, data.engagement_target)}
								<div class="min-w-0">
									<ProgressBar
										percent={p.max ? (p.earned / p.max) * 100 : 0}
										label="{COMPONENTS[p.key].label}: {pts(p.earned)} of {pts(p.max)} points"
										size="md"
									/>
									<p class="mt-1 truncate text-micro text-text" title={COMPONENTS[p.key].label}>
										{COMPONENTS[p.key].label}
										<span class="tabular-nums text-muted">{pts(p.earned)}/{pts(p.max)}</span>
									</p>
									<p class="truncate text-micro tabular-nums text-muted" title={line}>{line}</p>
								</div>
							{/each}
						</div>

						{#if actions.length}
							{@const [top, ...rest] = actions}
							<div class="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-card bg-accent-soft px-3 py-2.5">
								<div class="min-w-0">
									<p class="eyebrow text-accent">Biggest gain</p>
									<p class="text-small text-text">
										{top.label} · <span class="font-semibold tabular-nums">+{pts(top.gain)} pts</span>
										{#if top.perUnit}<span class="tabular-nums text-muted"> ({perBook(top.perUnit)} per book)</span>{/if}
									</p>
								</div>
								<a
									href={top.href}
									class="shrink-0 rounded-card bg-accent px-3 py-1.5 text-small font-semibold text-accent-contrast hover:opacity-90"
									>{top.cta} →</a
								>
							</div>
							{#if rest.length}
								<p class="mt-2 text-micro text-muted">
									Then:
									{#each rest as a, j (a.key)}
										<a href={a.href} class="text-accent hover:underline">{a.label}</a>
										<span class="tabular-nums">(+{pts(a.gain)} pts{a.perUnit ? `, ${perBook(a.perUnit)} per book` : ''})</span
										>{j < rest.length - 1 ? ' · ' : ''}
									{/each}
								</p>
							{/if}
						{/if}
					</li>
				{/each}
			</ol>
		{/snippet}
	</AdminGate>
</div>
