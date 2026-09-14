<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { getAdminLanguageHealth, type HealthScoreKey } from '$lib/library-admin';

	const res = adminResource(getAdminLanguageHealth, 'Something went wrong loading language health.');

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number) => nf.format(n);
	const pct = (n: number) => `${Math.round(n * 100)}%`;

	// The four ingredients of the composite, in the order the backend weights
	// them, with a one-line "what it measures" for the reader.
	const COMPONENTS: { key: HealthScoreKey; label: string; hint: string }[] = [
		{ key: 'readiness', label: 'Readiness', hint: 'How much of the go-live bar is met' },
		{ key: 'coverage', label: 'Coverage', hint: 'Share of the English shelf that exists here' },
		{ key: 'review', label: 'Review', hint: 'Share of translations a human has confirmed' },
		{ key: 'engagement', label: 'Engagement', hint: 'Readers, against the busiest language' }
	];

	// Readiness check keys → a human label for the blocking chips.
	const CHECK_LABEL: Record<string, string> = {
		bible: 'Bible',
		attribution: 'Attribution',
		glossary: 'Glossary',
		ui: 'Interface',
		books: 'Books',
		sermons: 'Sermons',
		bios: 'Biographies',
		plans: 'Reading plans',
		topics: 'Topic shelves'
	};

	// A health band drives the bar colour: strong, needs-work, weak.
	const band = (h: number) =>
		h >= 75 ? 'text-accent' : h >= 45 ? 'text-text' : 'text-warning';
	const barBand = (h: number) =>
		h >= 75 ? 'bg-accent' : h >= 45 ? 'bg-text/60' : 'bg-warning';
</script>

<svelte:head><title>Admin · Language health — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<AdminGate resource={res} errorTitle="Couldn't load language health" loadingText="Loading…" panelClass="mt-6">
		{#snippet children(data)}
			<header class="mb-6 mt-3">
				<p class="eyebrow mb-2 text-accent">Admin · Health</p>
				<h1 class="text-display">Language health</h1>
				<p class="mt-2 text-body text-muted">
					One score per language, ranked, composing four signals: how much of the go-live bar is
					met, how much of the {fmt(data.source_published_books)}-book English shelf exists here, how
					much of it a human has reviewed, and how many readers it has. It's a pointer to where the
					next hour of work goes — open a language to act on its weakest signal.
				</p>
			</header>

			<!-- Legend -->
			<div class="mb-6 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
				{#each COMPONENTS as c (c.key)}
					<div class="rounded-card border border-border bg-surface px-3 py-2">
						<p class="text-small font-semibold text-text">{c.label}</p>
						<p class="text-micro text-muted">{c.hint}</p>
					</div>
				{/each}
			</div>

			<ol class="flex flex-col gap-3">
				{#each data.languages as l, i (l.code)}
					<li class="rounded-card border border-border bg-surface p-4">
						<div class="flex items-start justify-between gap-4">
							<div class="min-w-0">
								<div class="flex items-baseline gap-2">
									<span class="text-small tabular-nums text-muted">#{i + 1}</span>
									<a href="/admin/languages/{l.code}" class="font-semibold text-text hover:text-accent"
										>{l.name}</a
									>
									<span class="text-small text-muted">{l.native_name}</span>
									{#if l.is_source}<span class="rounded-full bg-accent-soft px-2 py-0.5 text-micro text-accent">source</span>{/if}
									{#if l.is_live}<span class="rounded-full border border-border px-2 py-0.5 text-micro text-muted">live</span>{/if}
								</div>
								<p class="mt-1 text-small text-muted">
									{fmt(l.content.published_books)} books · {fmt(l.content.sermons)} sermons · {fmt(
										l.content.bios
									)} bios · {fmt(l.content.plans)} plans · {fmt(l.readers)} reader{l.readers === 1
										? ''
										: 's'}
									{#if l.content.unreviewed_books}
										· <span class="text-warning">{fmt(l.content.unreviewed_books)} awaiting review</span>
									{/if}
								</p>
							</div>
							<div class="shrink-0 text-end">
								<span class="text-h2 tabular-nums {band(l.health)}">{l.health}</span>
								<span class="block text-micro text-muted">/ 100</span>
							</div>
						</div>

						<!-- Component breakdown -->
						<div class="mt-3 grid gap-x-4 gap-y-1.5 sm:grid-cols-2">
							{#each COMPONENTS as c (c.key)}
								<div class="flex items-center gap-2">
									<span class="w-20 shrink-0 text-micro text-muted">{c.label}</span>
									<span class="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-2">
										<span
											class="block h-full rounded-full {barBand(Math.round(l.scores[c.key] * 100))}"
											style="width: {pct(l.scores[c.key])}"
										></span>
									</span>
									<span class="w-9 shrink-0 text-end text-micro tabular-nums text-muted"
										>{pct(l.scores[c.key])}</span
									>
								</div>
							{/each}
						</div>

						<!-- Readiness -->
						<div class="mt-3 flex flex-wrap items-center gap-1.5">
							{#if l.readiness.ready}
								<span class="rounded-full border border-accent/40 px-2 py-0.5 text-micro text-accent">Ready to go live</span>
							{:else}
								<span class="text-micro text-muted">Blocking:</span>
								{#each l.readiness.blocking as key (key)}
									<span class="rounded-full border border-warning/40 px-2 py-0.5 text-micro text-warning"
										>{CHECK_LABEL[key] ?? key}</span
									>
								{/each}
							{/if}
						</div>
					</li>
				{/each}
			</ol>
		{/snippet}
	</AdminGate>
</div>
