<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { ApiError } from '$lib/api';
	import {
		getAdminCoverage,
		getAdminTranslationJobs,
		createAdminTranslationJob,
		type AdminCoverageRow,
		type AdminTranslationJob,
		type TranslationJobType
	} from '$lib/library-admin';

	// Load the open translation queue right after coverage — via onLoad, so it
	// waits for auth to settle and re-runs on every (authenticated) refresh, the
	// way adminResource already sequences a page's dependent fetches. Firing it
	// from a bare $effect instead would race the Supabase session restore: the
	// pre-auth GET 403s and, with no auth dependency, never re-runs.
	const coverage = adminResource(getAdminCoverage, 'Something went wrong loading coverage.', () =>
		void loadJobs()
	);
	const cov = $derived(coverage.data);

	type Tab = 'books' | 'sermons' | 'plans';
	let tab = $state<Tab>('books');

	const TABS: { key: Tab; label: string }[] = [
		{ key: 'books', label: 'Books' },
		{ key: 'sermons', label: 'Sermons' },
		{ key: 'plans', label: 'Plans' }
	];

	const rows = $derived<AdminCoverageRow[]>(cov ? cov[tab] : []);
	const langs = $derived(cov?.languages ?? []);
	// Books link to their admin detail page; sermons/plans (no admin detail yet)
	// link to their live pages.
	const rowHref = (slug: string) =>
		tab === 'books' ? `/admin/books/${slug}` : tab === 'sermons' ? `/sermons/${slug}` : `/plans/${slug}`;

	// Per-language totals for the active matrix (how many works exist in each).
	const totals = $derived(
		langs.map((l) => rows.reduce((n, r) => n + (r.cells[l.code] ? 1 : 0), 0))
	);

	function cellMeta(v: string | undefined) {
		switch (v) {
			case 'public_domain':
				return { label: 'PD', cls: 'border border-border text-text' };
			case 'ai_reviewed':
				return { label: 'AI✓', cls: 'border border-accent-soft-border bg-accent-soft text-accent' };
			case 'ai_unreviewed':
				return { label: 'AI·', cls: 'border border-warning/40 text-warning' };
			case 'present':
				return { label: '●', cls: 'text-accent' };
			default:
				return { label: '·', cls: 'text-muted' };
		}
	}

	// --- Translation queue -----------------------------------------------------
	// Each missing cell (a work not yet in a language) becomes a click target that
	// files a translation job — the same GitHub-issue queue the per-language pages
	// use (POST /api/admin/translation-jobs/). A cell with an open job shows its
	// state instead of the button and links to the issue.
	//
	// The matrix tab maps 1:1 onto a job type (plural → singular).
	const jobType = $derived<TranslationJobType>(
		tab === 'books' ? 'book' : tab === 'sermons' ? 'sermon' : 'plan'
	);

	let jobs = $state<AdminTranslationJob[]>([]);
	// null = the jobs GET failed (unknown): keep the buttons and let POST surface
	// the real error; false = the queue isn't configured (no token) → no buttons.
	let jobsConfigured = $state<boolean | null>(null);
	let queueing = $state<string | null>(null); // "type:slug:lang" while POSTing
	let queueError = $state<string | null>(null);

	async function loadJobs() {
		try {
			const res = await getAdminTranslationJobs();
			jobs = res.jobs;
			jobsConfigured = res.configured;
		} catch {
			jobsConfigured = null;
		}
	}

	const jobKey = (slug: string, lang: string) => `${jobType}:${slug}:${lang}`;
	// Index the open jobs by `type:slug:lang` so each of the matrix's many cells
	// is an O(1) lookup rather than a linear scan of the whole queue.
	const jobIndex = $derived(
		new Map(jobs.map((j) => [`${j.type}:${j.slug}:${j.language}`, j]))
	);
	const jobFor = (slug: string, lang: string) => jobIndex.get(jobKey(slug, lang));

	async function queue(slug: string, lang: string) {
		queueError = null;
		queueing = jobKey(slug, lang);
		try {
			const res = await createAdminTranslationJob({ type: jobType, slug, language: lang });
			if (!jobs.some((j) => j.url === res.job.url)) jobs = [...jobs, res.job];
		} catch (e) {
			const body = e instanceof ApiError ? (e.body as { detail?: string } | null) : null;
			queueError =
				body?.detail ??
				(e instanceof Error ? e.message : "Couldn't queue the translation — try again.");
		} finally {
			queueing = null;
		}
	}
</script>

<svelte:head><title>Admin · Coverage — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-6xl px-5 py-10">
	<header class="mb-6">
		<p class="eyebrow mb-2 text-accent">Admin</p>
		<h1 class="text-display">Coverage matrix</h1>
		<p class="mt-2 text-body text-muted">Every work × language — where each is translated, and where the gaps are.</p>
	</header>

	<AdminGate resource={coverage} errorTitle="Couldn't load coverage">
		{#snippet children(d)}
			<!-- Tabs -->
			<div class="mb-4 flex flex-wrap items-center gap-2">
				{#each TABS as t (t.key)}
					<button
						class="rounded-full border px-4 py-1.5 text-small font-semibold {tab === t.key
							? 'border-accent-soft-border bg-accent-soft text-accent'
							: 'border-border text-muted hover:text-text'}"
						onclick={() => (tab = t.key)}
					>
						{t.label} ({d[t.key].length})
					</button>
				{/each}
			</div>

			<!-- Legend -->
			<div class="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-small text-muted">
				{#if tab === 'books'}
					<span><span class="text-text">PD</span> public domain</span>
					<span><span class="text-accent">AI✓</span> reviewed</span>
					<span><span class="text-warning">AI·</span> unreviewed</span>
				{:else}
					<span><span class="text-accent">●</span> present</span>
				{/if}
				<span><span class="text-muted">·</span> missing</span>
				{#if jobsConfigured !== false}
					<span><span class="text-accent">◷</span> queued</span>
					<span><span class="text-warning">◐</span> translating</span>
					<span class="text-muted">— click a gap to queue a translation</span>
				{/if}
			</div>

			{#if queueError}
				<div class="mb-3 rounded-card border border-warning/40 bg-warning/5 px-4 py-2 text-small text-warning" role="alert">
					{queueError}
				</div>
			{/if}

			<div class="overflow-x-auto rounded-card border border-border bg-surface">
				<table class="w-full border-collapse text-body">
					<thead>
						<tr class="border-b border-border text-small text-muted">
							<th class="sticky left-0 z-10 bg-surface px-4 py-3 text-left font-semibold">Work</th>
							{#each langs as l (l.code)}
								<th class="px-3 py-3 text-center font-semibold" title={l.name}>
									<a href="/admin/languages/{l.code}" class="text-muted hover:text-accent">{l.code}</a>
								</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each rows as r (r.slug)}
							<tr class="border-b border-border last:border-0 hover:bg-surface-2">
								<td class="sticky left-0 z-10 bg-surface px-4 py-2.5">
									<a href={rowHref(r.slug)} class="block max-w-[16rem] truncate font-medium text-text hover:text-accent">{r.title}</a>
									{#if r.author}<span class="block max-w-[16rem] truncate text-small text-muted">{r.author}</span>{/if}
								</td>
								{#each langs as l (l.code)}
									{@const v = r.cells[l.code]}
									{@const job = v ? undefined : jobFor(r.slug, l.code)}
									<td class="group px-3 py-2.5 text-center">
										{#if v}
											{@const m = cellMeta(v)}
											<span class="inline-flex min-w-[2.2rem] justify-center rounded-full px-1.5 py-0.5 text-small {m.cls}">{m.label}</span>
										{:else if job}
											<a
												href={job.url}
												target="_blank"
												rel="noopener"
												class="inline-flex min-w-[2.2rem] justify-center rounded-full px-1.5 py-0.5 text-small hover:no-underline {job.state === 'in_progress' ? 'text-warning' : 'text-accent'}"
												title={job.state === 'in_progress'
													? `Translating ${r.title} → ${l.name}… (open issue)`
													: `Queued: ${r.title} → ${l.name} (open issue)`}
											>
												{job.state === 'in_progress' ? '◐' : '◷'}
											</a>
										{:else if jobsConfigured === false}
											<span
												class="inline-flex min-w-[2.2rem] justify-center rounded-full px-1.5 py-0.5 text-small text-muted"
												title="Set GITHUB_TRANSLATION_TOKEN on the API to enable the queue"
											>·</span>
										{:else}
											{@const busy = queueing === jobKey(r.slug, l.code)}
											<button
												type="button"
												class="inline-flex min-w-[2.2rem] justify-center rounded-full px-1.5 py-0.5 text-small text-muted transition-colors hover:bg-accent-soft hover:text-accent disabled:opacity-50 disabled:hover:bg-transparent disabled:hover:text-muted"
												disabled={queueing !== null}
												title={`Queue a ${l.name} translation of ${r.title}`}
												aria-label={`Queue a ${l.name} translation of ${r.title}`}
												onclick={() => queue(r.slug, l.code)}
											>
												{#if busy}
													<span>…</span>
												{:else}
													<span class="group-hover:hidden">·</span>
													<span class="hidden group-hover:inline">+</span>
												{/if}
											</button>
										{/if}
									</td>
								{/each}
							</tr>
						{/each}
					</tbody>
					<tfoot>
						<tr class="border-t border-border text-small text-muted">
							<td class="sticky left-0 z-10 bg-surface px-4 py-2.5 font-semibold">Total ({rows.length})</td>
							{#each totals as n, i (langs[i].code)}
								<td class="px-3 py-2.5 text-center tabular-nums font-semibold text-text">{n}</td>
							{/each}
						</tr>
					</tfoot>
				</table>
			</div>
		{/snippet}
	</AdminGate>
</div>
