<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { ApiError } from '$lib/api';
	import { auth } from '$lib/auth.svelte';
	import {
		getAdminCoverage,
		getAdminTranslationJobs,
		createAdminTranslationJob,
		type AdminCoverageRow,
		type AdminCoverageLanguage,
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

	// Queueing translation work is super-admin-only: a language admin reads the
	// matrix (state + what's already queued) but never files jobs from it. UX only
	// — the POST is gated server-side too (see admin_views/jobs.py).
	const canQueue = $derived(auth.isAdmin);

	type Tab = 'books' | 'sermons' | 'plans' | 'bios' | 'articles';
	let tab = $state<Tab>('books');

	const TABS: { key: Tab; label: string }[] = [
		{ key: 'books', label: 'Books' },
		{ key: 'sermons', label: 'Sermons' },
		{ key: 'plans', label: 'Plans' },
		{ key: 'bios', label: 'Biographies' },
		{ key: 'articles', label: 'Articles' }
	];

	// Each tab is one job type (the queue's singular names).
	const JOB_TYPE: Record<Tab, TranslationJobType> = {
		books: 'book',
		sermons: 'sermon',
		plans: 'plan',
		bios: 'bio',
		articles: 'article'
	};

	// `?? []` guards the deploy window where the SPA carries a new tab before the
	// API's payload does: a missing `cov[tab]` must render empty, not throw.
	const rows = $derived<AdminCoverageRow[]>(cov?.[tab] ?? []);
	const langs = $derived(cov?.languages ?? []);
	// Books link to their admin detail page; sermons/plans/bios/articles (no admin
	// detail yet) link to their live pages — a biography row is an author.
	const ROW_HREF_BASE: Record<Tab, string> = {
		books: '/admin/books',
		sermons: '/sermons',
		plans: '/plans',
		bios: '/authors',
		articles: '/articles'
	};
	const rowHref = (slug: string) => `${ROW_HREF_BASE[tab]}/${slug}`;

	// --- Planner controls: narrow and order the matrix to what you're working on.
	// All three act on the same derived row list, so totals, the "+N" column
	// counts and the column "queue all" all follow what's actually on screen.
	let q = $state('');
	let sortMode = $state<'default' | 'least' | 'most'>('default');
	let unreviewedOnly = $state(false);
	// Books only: narrow the matrix to one series, in volume order. With a series
	// chosen, a column's "queue all" files every missing volume of it in that
	// language — "translate the whole series into Swahili" is one press.
	let seriesFilter = $state('');
	const seriesOptions = $derived(cov?.series ?? []);
	// How many languages a work is present in — the completeness sort key.
	const completeness = (r: AdminCoverageRow) =>
		langs.reduce((n, l) => n + (r.cells[l.code] ? 1 : 0), 0);
	// A work with at least one AI translation still awaiting review — the backlog.
	const hasUnreviewed = (r: AdminCoverageRow) =>
		langs.some((l) => r.cells[l.code] === 'ai_unreviewed');
	const visibleRows = $derived.by(() => {
		let out = rows;
		const term = q.trim().toLowerCase();
		if (term)
			out = out.filter(
				(r) =>
					r.title.toLowerCase().includes(term) || (r.author ?? '').toLowerCase().includes(term)
			);
		if (unreviewedOnly) out = out.filter(hasUnreviewed);
		if (tab === 'books' && seriesFilter) {
			out = out
				.filter((r) => r.series === seriesFilter)
				.sort((a, b) => (a.series_position ?? 0) - (b.series_position ?? 0));
		}
		if (sortMode !== 'default')
			out = [...out].sort((a, b) =>
				sortMode === 'least'
					? completeness(a) - completeness(b)
					: completeness(b) - completeness(a)
			);
		return out;
	});

	// Per-language totals for the active matrix (how many visible works exist in each).
	const totals = $derived(
		langs.map((l) => visibleRows.reduce((n, r) => n + (r.cells[l.code] ? 1 : 0), 0))
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
	// state instead of the button and links to the issue. A row / column header can
	// also queue every gap along it at once, behind a count confirmation.
	//
	// The matrix tab maps 1:1 onto a job type (plural → singular).
	const jobType = $derived<TranslationJobType>(JOB_TYPE[tab]);

	let jobs = $state<AdminTranslationJob[]>([]);
	// null = the jobs GET failed (unknown): keep the buttons and let POST surface
	// the real error; false = the queue isn't configured (no token) → no buttons.
	let jobsConfigured = $state<boolean | null>(null);
	let queueing = $state<string | null>(null); // "type:slug:lang" while POSTing one
	let queueError = $state<string | null>(null);
	// A bulk enqueue awaiting the user's confirmation (the flooding guard): filing
	// N jobs means N worker sessions, so a row/column press asks before it fires.
	// The job type is captured here, at stage time, so switching tabs while the
	// confirmation is up can't file the targets under the new tab's type.
	let pendingBulk = $state<{
		label: string;
		type: TranslationJobType;
		targets: { slug: string; lang: string }[];
	} | null>(null);
	// Live progress while a confirmed bulk runs (jobs are filed one at a time).
	let bulkProgress = $state<{ done: number; total: number } | null>(null);
	// Any queue POST in flight — disables every enqueue control so two runs can't
	// overlap and trip the API's per-caller throttle.
	const busy = $derived(queueing !== null || bulkProgress !== null);

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
	// A cell is a queueable gap when the language is a translation target, the work
	// has no row in it, and no job is already open. Shared by the buttons, the bulk
	// counts, and the bulk target lists — so a non-queueable column (a stray content
	// language) never offers a button that the POST would only reject.
	const isGap = (l: AdminCoverageLanguage, r: AdminCoverageRow) =>
		l.queueable && !r.cells[l.code] && !jobFor(r.slug, l.code);
	// Missing-and-unqueued count per language column, for the header's "queue all".
	// Over the visible rows, so a filtered view queues only what it shows.
	const colGaps = $derived(
		langs.map((l) => visibleRows.reduce((n, r) => n + (isGap(l, r) ? 1 : 0), 0))
	);

	// File one job; returns null on success or a message to show. Type is passed in
	// (not read from jobType) so a bulk run is unaffected by a mid-run tab switch.
	async function enqueueOne(type: TranslationJobType, slug: string, lang: string): Promise<string | null> {
		try {
			const res = await createAdminTranslationJob({ type, slug, language: lang });
			if (!jobs.some((j) => j.url === res.job.url)) jobs = [...jobs, res.job];
			return null;
		} catch (e) {
			const body = e instanceof ApiError ? (e.body as { detail?: string } | null) : null;
			return body?.detail ?? (e instanceof Error ? e.message : 'failed');
		}
	}

	async function queue(slug: string, lang: string) {
		queueError = null;
		queueing = jobKey(slug, lang);
		const err = await enqueueOne(jobType, slug, lang);
		if (err) queueError = err === 'failed' ? "Couldn't queue the translation — try again." : err;
		queueing = null;
	}

	// Stage a row (a work into all its missing languages) or a column (all missing
	// works into a language) for confirmation. No-op when there's nothing to queue.
	function bulkRow(r: AdminCoverageRow) {
		const targets = langs.filter((l) => isGap(l, r)).map((l) => ({ slug: r.slug, lang: l.code }));
		if (targets.length)
			pendingBulk = { label: `“${r.title}” into every missing language`, type: jobType, targets };
	}
	function bulkCol(l: AdminCoverageLanguage) {
		const targets = visibleRows.filter((r) => isGap(l, r)).map((r) => ({ slug: r.slug, lang: l.code }));
		if (targets.length)
			pendingBulk = { label: `every missing work into ${l.name}`, type: jobType, targets };
	}

	async function runBulk() {
		if (!pendingBulk) return;
		const { targets, type } = pendingBulk; // type pinned at stage time
		pendingBulk = null;
		queueError = null;
		bulkProgress = { done: 0, total: targets.length };
		let failed = 0;
		let firstErr: string | null = null;
		for (const t of targets) {
			const err = await enqueueOne(type, t.slug, t.lang);
			if (err) {
				failed++;
				firstErr ??= err;
			}
			bulkProgress = { done: bulkProgress.done + 1, total: targets.length };
		}
		bulkProgress = null;
		if (failed) {
			// Don't surface the generic 'failed' sentinel — only a real backend detail.
			const detail = firstErr && firstErr !== 'failed' ? ` — ${firstErr}` : '';
			queueError = `Queued ${targets.length - failed} of ${targets.length}; ${failed} failed${detail}.`;
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
						{t.label} ({d[t.key]?.length ?? 0})
					</button>
				{/each}
			</div>

			<!-- Planner controls: filter, order and narrow to the review backlog. -->
			<div class="mb-3 flex flex-wrap items-center gap-2">
				<input
					type="text"
					bind:value={q}
					placeholder="Filter by title or author…"
					aria-label="Filter works"
					class="field min-w-48 flex-1 text-small"
				/>
				<select bind:value={sortMode} aria-label="Sort works" class="field text-small">
					<option value="default">Order: as listed</option>
					<option value="least">Least complete first</option>
					<option value="most">Most complete first</option>
				</select>
				<label class="flex items-center gap-1.5 text-small text-muted">
					<input type="checkbox" bind:checked={unreviewedOnly} />
					Only unreviewed AI
				</label>
				{#if tab === 'books' && seriesOptions.length}
					<select bind:value={seriesFilter} aria-label="Narrow to a series" class="field text-small">
						<option value="">All books</option>
						{#each seriesOptions as s (s.slug)}
							<option value={s.slug}>Series: {s.title}</option>
						{/each}
					</select>
				{/if}
			</div>

			<!-- Legend -->
			<div class="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-small text-muted">
				{#if tab === 'books'}
					<span><span class="text-text">PD</span> public domain</span>
				{/if}
				{#if tab === 'books' || tab === 'bios' || tab === 'articles'}
					<span><span class="text-accent">AI✓</span> reviewed</span>
					<span><span class="text-warning">AI·</span> unreviewed</span>
				{/if}
				{#if tab !== 'books'}
					<span><span class="text-accent">●</span> present</span>
				{/if}
				<span><span class="text-muted">·</span> missing</span>
				<span><span class="text-warning">⌕N</span> unmet searches · 30d</span>
				{#if jobsConfigured !== false}
					<span><span class="text-accent">◷</span> queued</span>
					<span><span class="text-warning">◐</span> translating</span>
					{#if canQueue}
						<span class="text-muted">— click a gap, or a row / column “+N”, to queue</span>
					{/if}
				{/if}
			</div>

			{#if pendingBulk}
				<div class="mb-3 flex flex-wrap items-center gap-3 rounded-card border border-accent-soft-border bg-accent-soft px-4 py-2.5 text-small text-accent" role="alertdialog">
					<span>
						Queue {pendingBulk.targets.length} translation{pendingBulk.targets.length === 1 ? '' : 's'}
						— {pendingBulk.label}? Each files a job a worker processes one at a time.
					</span>
					<span class="ml-auto flex gap-2">
						<button class="btn btn-sm btn-primary" onclick={runBulk}>Queue all</button>
						<button class="btn btn-sm btn-ghost" onclick={() => (pendingBulk = null)}>Cancel</button>
					</span>
				</div>
			{:else if bulkProgress}
				<div class="mb-3 rounded-card border border-border bg-surface-2 px-4 py-2 text-small text-muted" role="status">
					Queueing… {bulkProgress.done}/{bulkProgress.total}
				</div>
			{/if}

			{#if queueError}
				<div class="mb-3 rounded-card border border-warning/40 bg-warning/5 px-4 py-2 text-small text-warning" role="alert">
					{queueError}
				</div>
			{/if}

			<!-- Bounded scroll box so the header sticks on vertical scroll too: a bare
			     overflow-x container leaves `sticky top-0` nothing to stick within.
			     The Work column was already frozen (sticky left-0). -->
			<div class="max-h-[75vh] overflow-auto rounded-card border border-border bg-surface">
				<table class="w-full border-collapse text-body">
					<thead>
						<tr class="border-b border-border text-small text-muted">
							<th class="sticky left-0 top-0 z-30 bg-surface px-4 py-3 text-left font-semibold">Work</th>
							{#each langs as l, i (l.code)}
								<th class="sticky top-0 z-20 bg-surface px-3 py-3 text-center font-semibold align-top" title={l.name}>
									<a href="/admin/languages/{l.code}" class="text-muted hover:text-accent">{l.code}</a>
									{#if l.unmet_searches}
										<span
											class="mt-0.5 block text-micro font-normal text-warning"
											title={`${l.unmet_searches} reader search${l.unmet_searches === 1 ? '' : 'es'} found nothing in ${l.name} (30d) — demand to translate toward`}
										>⌕{l.unmet_searches}</span>
									{/if}
									{#if canQueue && jobsConfigured !== false && l.queueable && colGaps[i] > 0}
										<button
											type="button"
											class="mt-0.5 block w-full text-micro font-semibold text-muted transition-colors hover:text-accent disabled:opacity-40 disabled:hover:text-muted"
											disabled={busy}
											title={`Queue all ${colGaps[i]} missing ${l.name} translations`}
											aria-label={`Queue all ${colGaps[i]} missing ${l.name} translations`}
											onclick={() => bulkCol(l)}
										>+{colGaps[i]}</button>
									{/if}
								</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#if visibleRows.length === 0}
							<tr>
								<td colspan={langs.length + 1} class="px-4 py-8 text-center text-body text-muted">
									No works match these filters.
								</td>
							</tr>
						{/if}
						{#each visibleRows as r (r.slug)}
							{@const rowGaps = langs.reduce((n, l) => n + (isGap(l, r) ? 1 : 0), 0)}
							<tr class="group/row border-b border-border last:border-0 hover:bg-surface-2">
								<td class="sticky left-0 z-10 bg-surface px-4 py-2.5">
									<a href={rowHref(r.slug)} class="block max-w-[16rem] truncate font-medium text-text hover:text-accent">{r.title}</a>
									{#if r.author}<span class="block max-w-[16rem] truncate text-small text-muted">{r.author}</span>{/if}
									{#if canQueue && jobsConfigured !== false && rowGaps > 0}
										<button
											type="button"
											class="mt-1 text-micro font-semibold text-muted opacity-0 transition group-hover/row:opacity-100 hover:text-accent focus:opacity-100 disabled:opacity-40"
											disabled={busy}
											title={`Queue all ${rowGaps} missing translations of ${r.title}`}
											aria-label={`Queue all ${rowGaps} missing translations of ${r.title}`}
											onclick={() => bulkRow(r)}
										>Queue all {rowGaps}</button>
									{/if}
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
										{:else if jobsConfigured === false || !l.queueable || !canQueue}
											<span
												class="inline-flex min-w-[2.2rem] justify-center rounded-full px-1.5 py-0.5 text-small text-muted"
												title={jobsConfigured === false
													? 'Set GITHUB_TRANSLATION_TOKEN on the API to enable the queue'
													: !canQueue
														? `Missing: ${r.title} → ${l.name}`
														: `${l.name} isn't a translation target — nothing to queue`}
											>·</span>
										{:else}
											{@const spot = queueing === jobKey(r.slug, l.code)}
											<button
												type="button"
												class="inline-flex min-w-[2.2rem] justify-center rounded-full px-1.5 py-0.5 text-small text-muted transition-colors hover:bg-accent-soft hover:text-accent disabled:opacity-50 disabled:hover:bg-transparent disabled:hover:text-muted"
												disabled={busy}
												title={`Queue a ${l.name} translation of ${r.title}`}
												aria-label={`Queue a ${l.name} translation of ${r.title}`}
												onclick={() => queue(r.slug, l.code)}
											>
												{#if spot}
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
							<td class="sticky left-0 z-10 bg-surface px-4 py-2.5 font-semibold">Total ({visibleRows.length}{visibleRows.length !== rows.length ? ` of ${rows.length}` : ''})</td>
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
