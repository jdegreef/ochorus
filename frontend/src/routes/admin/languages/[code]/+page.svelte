<script lang="ts">
	import { ApiError } from '$lib/api';
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import LanguageSettingsCard from '$lib/components/LanguageSettingsCard.svelte';
	import {
		type SourceType
	} from '$lib/library-public';
	import {
		getAdminLanguageDetail,
		getAdminTranslationJobs,
		createAdminTranslationJob,
		type AdminLangBio,
		type AdminTranslationJob,
		type TranslationJobType,
		getAdminLanguageReadiness,
		updateAdminLanguageThresholds,
		type AdminLanguageReadiness,
		type LanguageThresholds,
		goLiveAdminLanguage,
		checkAdminLanguageDeploy,
		type GoLiveResult
	} from '$lib/library-admin';

	let { data } = $props();

	// Translation queue (buttons on the todo lists). Derived state: queued =
	// open GitHub issue, in_progress = claimed by a worker session. null
	// configured = the GET failed — keep the buttons and let POST surface errors.
	let jobs = $state<AdminTranslationJob[]>([]);
	let jobsConfigured = $state<boolean | null>(null);
	let queueing = $state<string | null>(null); // "type:slug" while POSTing
	let queueError = $state<string | null>(null);

	// Readiness: fetched separately from the detail payload because the Bible
	// check makes a live API call. Failure is non-fatal — the page is still
	// useful without the panel, so we surface the error and move on.
	let readiness = $state<AdminLanguageReadiness | null>(null);
	let readinessError = $state<string | null>(null);
	let savingBar = $state(false);

	async function loadReadiness(code: string) {
		readiness = null;
		readinessError = null;
		try {
			readiness = await getAdminLanguageReadiness(code);
		} catch (e) {
			readinessError = e instanceof Error ? e.message : 'Could not load readiness.';
		}
	}

	async function saveThreshold(patch: Partial<LanguageThresholds>) {
		if (!readiness) return;
		savingBar = true;
		readinessError = null;
		try {
			await updateAdminLanguageThresholds(readiness.code, patch);
			// Re-fetch rather than patching locally: changing the bar changes the
			// verdict, and the server is the one that decides it.
			await loadReadiness(readiness.code);
		} catch (e) {
			readinessError = e instanceof Error ? e.message : 'Could not save.';
		} finally {
			savingBar = false;
		}
	}

	// Shared tokens only (app.css): accent for cleared, gold for attention —
	// matching how "unpublished" and queue errors already read on this page.
	// There is no `success` token; inventing one renders as unstyled text.
	const CHECK_TONE: Record<string, string> = {
		pass: 'text-accent',
		fail: 'text-warning',
		unknown: 'text-muted',
		skipped: 'text-muted'
	};
	const CHECK_MARK: Record<string, string> = {
		pass: '✓',
		fail: '✕',
		unknown: '?',
		skipped: '–'
	};

	// --- Going live -----------------------------------------------------------
	// Two facts, kept apart on purpose: `launched` means the decision is recorded,
	// `deploy` means the rebuild was triggered. A language can be live in the
	// database while the deploy failed, and a single green tick would hide that.
	let launching = $state(false);
	let launchResult = $state<GoLiveResult | null>(null);
	let launchError = $state<string | null>(null);
	let deployState = $state<{ status: string; detail: string } | null>(null);

	async function launch(force: boolean) {
		if (!readiness) return;
		const label = readiness.code.toUpperCase();
		const warning = force
			? `Take ${label} live DESPITE ${readiness.blocking.length} failing check(s)?\n\n`
			: `Take ${label} live?\n\n`;
		if (
			!confirm(
				warning +
					'This records the launch and triggers a rebuild of the reader. Readers ' +
					'see the language when that build finishes — not immediately.'
			)
		)
			return;

		launching = true;
		launchError = null;
		launchResult = null;
		try {
			launchResult = await goLiveAdminLanguage(readiness.code, force);
			await loadReadiness(readiness.code);
		} catch (e) {
			launchError = e instanceof Error ? e.message : 'Could not take it live.';
		} finally {
			launching = false;
		}
	}

	async function checkDeploy() {
		if (!readiness) return;
		deployState = { status: 'checking', detail: 'Reading the live sitemap…' };
		try {
			deployState = await checkAdminLanguageDeploy(readiness.code);
		} catch (e) {
			deployState = {
				status: 'unknown',
				detail: e instanceof Error ? e.message : 'Check failed.'
			};
		}
	}

	const BAR_FIELDS: { key: keyof LanguageThresholds; label: string }[] = [
		{ key: 'min_books', label: 'Books' },
		{ key: 'min_sermons', label: 'Sermons' },
		{ key: 'min_bios', label: 'Biographies' },
		{ key: 'min_plans', label: 'Plans' }
	];

	const language = adminResource(
		() => getAdminLanguageDetail(data.code),
		'Something went wrong loading this language.',
		() => data.code,
		// The queue and the readiness report hang off this payload. English is
		// the source language: it has nothing to translate and no bar to clear.
		(result) => {
			if (result.is_source) return;
			void loadJobs();
			void loadReadiness(data.code);
		}
	);
	const detail = $derived(language.data);
	const load = language.load;

	async function loadJobs() {
		try {
			const res = await getAdminTranslationJobs();
			jobs = res.jobs;
			jobsConfigured = res.configured;
		} catch {
			jobsConfigured = null;
		}
	}

	const jobFor = (type: TranslationJobType, slug: string) =>
		jobs.find((j) => j.type === type && j.slug === slug && j.language === data.code);

	// One POST + the dedup that both the single and bulk paths need — kept in one
	// place so they can't drift.
	async function postJob(type: TranslationJobType, slug: string) {
		const res = await createAdminTranslationJob({ type, slug, language: data.code });
		if (!jobs.some((j) => j.url === res.job.url)) jobs = [...jobs, res.job];
	}

	async function queue(type: TranslationJobType, slug: string) {
		queueError = null;
		queueing = `${type}:${slug}`;
		try {
			await postJob(type, slug);
		} catch (e) {
			const body = e instanceof ApiError ? (e.body as { detail?: string } | null) : null;
			queueError =
				body?.detail ??
				(e instanceof Error ? e.message : "Couldn't queue the translation — try again.");
		} finally {
			queueing = null;
		}
	}

	// Bulk-queue the currently-shown todo rows of one type in a single click, so
	// filling a section isn't N separate presses. Only rows that aren't already
	// queued are posted; each POST opens a real GitHub issue, so we confirm the
	// count first. Sequential (not Promise.all) to keep it gentle on the API and
	// to stop cleanly on the first error. `busy` gates every queue control while
	// any single or bulk POST is in flight.
	let bulkQueueing = $state<TranslationJobType | null>(null);
	const busy = $derived(queueing !== null || bulkQueueing !== null);

	async function queueBulk(type: TranslationJobType, rows: { slug: string }[]) {
		const pending = rows.filter((r) => !jobFor(type, r.slug));
		if (!pending.length) return;
		if (
			!confirm(
				`Queue ${pending.length} ${type} translation${pending.length === 1 ? '' : 's'} for ` +
					`${detail?.language.name ?? data.code}? This opens ${pending.length} GitHub issue` +
					`${pending.length === 1 ? '' : 's'}.`
			)
		)
			return;
		queueError = null;
		bulkQueueing = type;
		try {
			for (const r of pending) await postJob(type, r.slug);
		} catch (e) {
			const body = e instanceof ApiError ? (e.body as { detail?: string } | null) : null;
			queueError =
				body?.detail ??
				(e instanceof Error ? e.message : "Couldn't queue the translations — try again.");
		} finally {
			bulkQueueing = null;
		}
	}

	// What each section shows. "Live" is what a reader can actually reach in this
	// language right now (published rows only — an unpublished translation exists
	// but serves nothing); "suggested" is the ranked queue of what to do next.
	type View = 'all' | 'live' | 'suggested' | 'attention';
	let view = $state<View>('all');
	const VIEWS: { id: View; label: string }[] = [
		{ id: 'all', label: 'All' },
		{ id: 'live', label: 'Live on site' },
		{ id: 'suggested', label: 'Suggested' },
		{ id: 'attention', label: 'Needs attention' }
	];

	/** "Needs attention" is the finishing worklist: a translated row that isn't
	 *  live yet (unpublished) or is still an unreviewed AI draft. Sermons and
	 *  plans carry no source_type, so only their publish state can flag them. */
	const attnPublishable = (r: { is_published: boolean; source_type: SourceType }) =>
		!r.is_published || r.source_type === 'ai_unreviewed';
	const attnSimple = (r: { is_published: boolean }) => !r.is_published;

	/** Books/sermons/plans to list: none under "suggested", published-only under
	 *  "live", attention-only under "attention" (pass the matching predicate). */
	const present = <T extends { is_published: boolean }>(rows: T[], attn: (r: T) => boolean): T[] =>
		view === 'suggested'
			? []
			: view === 'live'
				? rows.filter((r) => r.is_published)
				: view === 'attention'
					? rows.filter(attn)
					: rows;
	/** Bios have no publish flag — a translated biography either exists or doesn't,
	 *  and if it exists it is live. So "live" and "all" show the same rows; under
	 *  "attention" an unreviewed AI bio is what's left to check. */
	const presentBios = (rows: AdminLangBio[]): AdminLangBio[] =>
		view === 'suggested' ? [] : view === 'attention' ? rows.filter((a) => !a.reviewed) : rows;
	/** Todo rows to list: hidden under "live" and "attention" (both are about
	 *  finishing existing translations, not starting new ones). */
	const suggested = <T,>(rows: T[]): T[] => (view === 'live' || view === 'attention' ? [] : rows);

	// One derived view of the payload, so the template stays declarative —
	// Svelte 5 won't allow {@const} as a direct child of <section>.
	const shown = $derived({
		books: present(detail?.books ?? [], attnPublishable),
		sermons: present(detail?.sermons ?? [], attnSimple),
		plans: present(detail?.plans ?? [], attnSimple),
		bios: presentBios(detail?.bios ?? []),
		todoBooks: suggested(detail?.todo.books ?? []),
		todoSermons: suggested(detail?.todo.sermons ?? []),
		// Topics carry no publish/review state, so nothing to attend to there.
		topics: view === 'suggested' || view === 'attention' ? [] : (detail?.topics ?? []),
		todoPlans: suggested(detail?.todo.plans ?? []),
		todoBios: suggested(detail?.todo.bios ?? []),
		todoTopics: suggested(detail?.todo.topics ?? []),
		articles: present(detail?.articles ?? [], attnPublishable),
		todoArticles: suggested(detail?.todo.articles ?? [])
	});
	// Under "suggested" an empty translated list is the point, not a gap; under
	// "attention" an empty list is the good outcome (nothing left to fix).
	const emptyLabel = $derived(
		view === 'live'
			? 'Nothing live yet.'
			: view === 'suggested'
				? ''
				: view === 'attention'
					? 'Nothing needs attention.'
					: 'None yet.'
	);

	// Jump bar. The page is a tall stack (readiness + settings + six content
	// sections), so anchors let you reach Articles without scrolling past
	// everything. Counts track the current view; order matches the DOM order of
	// the sections below. Readiness only exists for a target language, and has no
	// count to tally. ids match the `scroll-mt-*` sections so a jump lands clear
	// of the sticky bar.
	const navSections = $derived([
		...(detail && !detail.is_source
			? [{ id: 'sec-readiness', label: 'Readiness', count: null as number | null }]
			: []),
		{ id: 'sec-books', label: 'Books', count: shown.books.length },
		{ id: 'sec-bios', label: 'Bios', count: shown.bios.length },
		{ id: 'sec-sermons', label: 'Sermons', count: shown.sermons.length },
		{ id: 'sec-plans', label: 'Plans', count: shown.plans.length },
		{ id: 'sec-topics', label: 'Topics', count: shown.topics.length },
		{ id: 'sec-articles', label: 'Articles', count: shown.articles.length }
	]);

	// A "Next to work on" list can run to dozens of rows (every missing topic
	// shelf, every unstarted book) — on a mature language that is most of the
	// page's height. Show the top slice, ranked as the API already returns them,
	// and let each section expand on demand. Keyed per section so opening one
	// doesn't open the rest.
	const TODO_CAP = 8;
	let todoExpanded = $state<Record<string, boolean>>({});
	const capTodo = <T,>(key: string, rows: T[]): T[] =>
		todoExpanded[key] ? rows : rows.slice(0, TODO_CAP);

	// A translated list is the "done pile" — useful to have, but on a mature
	// language it's most of the page, and the admin is usually here to see what's
	// LEFT. So collapse it behind its count when it's long; short lists stay open
	// (nothing to save by hiding a handful). The heading and count stay visible
	// either way, so the state is legible while folded.
	const COLLAPSE_AT = 8;

	// Translation coverage, per content type: how far this language has come
	// against the English catalogue. A bar reads faster than "217/312 books" and
	// answers the question the page exists for. Counts are the full translated
	// totals (not the view filter). English (source) has no coverage to show.
	const progress = $derived(
		detail && !detail.is_source
			? [
					{ label: 'Books', done: detail.books.length, total: detail.english_counts.books },
					{ label: 'Sermons', done: detail.sermons.length, total: detail.english_counts.sermons },
					{ label: 'Plans', done: detail.plans.length, total: detail.english_counts.plans },
					{ label: 'Bios', done: detail.bios.length, total: detail.english_counts.bios },
					{ label: 'Articles', done: detail.articles.length, total: detail.english_counts.articles }
				]
			: []
	);
	const pct = (done: number, total: number) =>
		total > 0 ? Math.round((done / total) * 100) : 0;

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number | null | undefined) => nf.format(n ?? 0);

	/** "5 books, 13 sermons" — why this author is where they are in the queue. */
	const worksLabel = (a: { book_count: number; sermon_count: number }) =>
		[
			a.book_count && `${fmt(a.book_count)} book${a.book_count === 1 ? '' : 's'}`,
			a.sermon_count && `${fmt(a.sermon_count)} sermon${a.sermon_count === 1 ? '' : 's'}`
		]
			.filter(Boolean)
			.join(', ');

	const SOURCE_BADGE: Record<SourceType, string> = {
		public_domain: 'PD',
		ai_reviewed: 'AI✓',
		ai_unreviewed: 'AI·'
	};
</script>

<svelte:head><title>Admin · {detail?.language.name ?? data.code} — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-6xl px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<AdminGate resource={language} errorTitle="Couldn't load this language" loadingText="Loading…" panelClass="mt-6">
		{#snippet children(d)}
			{#snippet queueControl(type: TranslationJobType, slug: string)}
				{@const job = jobFor(type, slug)}
				{#if job}
					<a
						href={job.url}
						target="_blank"
						rel="noopener"
						class="shrink-0 rounded-full border px-2.5 py-0.5 text-small hover:no-underline {job.state ===
						'in_progress'
							? 'border-border bg-surface-2 text-warning'
							: 'border-accent-soft-border bg-accent-soft text-accent'}"
						title="Open the job issue on GitHub"
					>
						{job.state === 'in_progress' ? 'Translating…' : 'Queued ↗'}
					</a>
				{:else}
					<button
						class="btn btn-sm btn-ghost shrink-0"
						disabled={jobsConfigured === false || busy}
						title={jobsConfigured === false
							? 'Set GITHUB_TRANSLATION_TOKEN on the API to enable the queue'
							: `Queue a ${d.language.name} translation`}
						onclick={() => queue(type, slug)}
					>
						{queueing === `${type}:${slug}` ? 'Queueing…' : 'Translate'}
					</button>
				{/if}
			{/snippet}
			<!-- "Queue all N" for a section's shown todo rows — one click instead of N.
			     Skips rows already queued; hidden when the queue isn't configured or
			     there's nothing left to queue. -->
			{#snippet bulkQueueControl(type: TranslationJobType, rows: { slug: string }[])}
				{@const pending = rows.filter((r) => !jobFor(type, r.slug)).length}
				{#if jobsConfigured !== false && pending > 0}
					<button
						class="shrink-0 text-small font-semibold text-accent hover:underline disabled:opacity-50"
						disabled={busy}
						onclick={() => queueBulk(type, rows)}
					>
						{bulkQueueing === type ? 'Queueing…' : `Queue all ${fmt(pending)}`}
					</button>
				{/if}
			{/snippet}
			<!-- A translated ("done") list, folded behind its heading when long. The
			     heading + count stay visible folded, so the section's state reads at
			     a glance; the ▸ rotates open (same idiom as the content audit). When
			     the list is empty, there's nothing to fold — show the heading and the
			     empty note. -->
			{#snippet translatedList(title: string, count: number, body: import('svelte').Snippet)}
				{#if count}
					<details class="group mb-3" open={count <= COLLAPSE_AT}>
						<summary class="mb-3 flex cursor-pointer list-none items-baseline gap-2">
							<span
								class="inline-block text-muted transition-transform group-open:rotate-90"
								aria-hidden="true">›</span>
							<h2 class="text-h3">{title} <span class="text-muted">({fmt(count)})</span></h2>
						</summary>
						{@render body()}
					</details>
				{:else}
					<h2 class="text-h3 mb-3">{title} <span class="text-muted">({fmt(count)})</span></h2>
					{#if emptyLabel}<p class="text-body text-muted">{emptyLabel}</p>{/if}
				{/if}
			{/snippet}
			<header class="mb-8 mt-3">
				<p class="eyebrow mb-2 text-accent">Admin · Language</p>
				<h1 class="text-display">
					{d.language.native_name}
					{#if d.language.native_name !== d.language.name}<span class="text-muted">· {d.language.name}</span>{/if}
				</h1>
				<p class="mt-2 flex flex-wrap items-center gap-2 text-body text-muted">
					<span>Code {d.language.code}</span>
					{#if d.is_source}
						<span class="rounded-full border border-accent-soft-border bg-accent-soft px-2.5 py-0.5 text-small text-accent">Source language</span>
					{/if}
				</p>
				{#if !d.is_source}
					<!-- Coverage against the English catalogue, one bar per content type —
					     the "how far along is this language" answer at a glance. -->
					<div class="mt-4 grid max-w-xl grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
						{#each progress as p (p.label)}
							<div
								class="flex items-center gap-3 text-small"
								role="progressbar"
								aria-valuenow={pct(p.done, p.total)}
								aria-valuemin="0"
								aria-valuemax="100"
								aria-label="{p.label}: {fmt(p.done)} of {fmt(p.total)} translated"
							>
								<span class="w-16 flex-none text-muted">{p.label}</span>
								<span class="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-surface-2">
									<span class="block h-full rounded-full bg-accent" style="width: {pct(p.done, p.total)}%"></span>
								</span>
								<span class="w-16 flex-none text-right tabular-nums text-muted">
									<strong class="text-text">{fmt(p.done)}</strong>/{fmt(p.total)}
								</span>
							</div>
						{/each}
					</div>
				{/if}
				{#if !d.is_source}
					<div class="mt-4 flex flex-wrap items-center gap-2" role="group" aria-label="Filter what each section shows">
						{#each VIEWS as v (v.id)}
							<button
								class="rounded-full border px-4 py-1.5 text-small font-semibold {view === v.id
									? 'border-accent-soft-border bg-accent-soft text-accent'
									: 'border-border text-muted hover:text-text'}"
								aria-pressed={view === v.id}
								onclick={() => (view = v.id)}
							>
								{v.label}
							</button>
						{/each}
						<!-- "Live" means published, NOT necessarily reachable: the public
						     site is a prerendered static build, so a newly published row
						     only appears after the next frontend deploy — and only if the
						     language is one of the URL locales compiled into the app. -->
						<span class="text-small text-muted">
							{#if view === 'live'}Published — reaches readers after the next site build.
							{:else if view === 'suggested'}Ranked queue of what to translate next.
							{:else if view === 'attention'}Translated but unpublished or awaiting review — the finishing list.
							{:else}Everything — translated and suggested.{/if}
						</span>
					</div>
				{/if}
			</header>

			<!-- Jump bar. Sticky under the app nav (same anchor the admin rail pins to)
			     so it stays reachable down the whole page. Solid `bg-surface` like the
			     rail, so scrolled content doesn't bleed through. -->
			<nav
				aria-label="Jump to section"
				class="sticky top-[var(--appnav-h,0px)] z-30 -mx-5 mb-6 flex gap-1 overflow-x-auto border-b border-border bg-surface px-5 py-2"
			>
				{#each navSections as s (s.id)}
					<a
						href="#{s.id}"
						class="flex shrink-0 items-baseline gap-1.5 whitespace-nowrap rounded-full px-3 py-1 text-small font-semibold text-muted hover:bg-surface-2 hover:text-text hover:no-underline"
					>
						{s.label}
						{#if s.count !== null}<span class="text-muted">{fmt(s.count)}</span>{/if}
					</a>
				{/each}
			</nav>

			{#if !d.is_source}
				<!-- Readiness. Read-only about the verdict, editable about the BAR: the
				     thresholds are a judgement (a language with a big catalogue behind it
				     should clear a higher one than a first beachhead language), while
				     whether they're met is a fact the server computes. Nothing here
				     launches anything — the go-live action re-runs these same checks
				     server-side rather than trusting what this page is holding. -->
				<section
					id="sec-readiness"
					class="mb-6 scroll-mt-[calc(var(--appnav-h,0px)+4rem)] rounded-card border border-border bg-surface p-5"
				>
					<div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
						<h2 class="text-h3">Readiness</h2>
						{#if readiness}
							<span class="text-small font-semibold {readiness.ready ? 'text-accent' : 'text-warning'}">
								{readiness.ready
									? 'Every check clear'
									: `${readiness.blocking.length} blocking: ${readiness.blocking.join(', ')}`}
							</span>
						{/if}
					</div>

					{#if readinessError}
						<p class="mb-3 text-small text-warning">{readinessError}</p>
					{/if}

					{#if readiness}
						<ul class="mb-4 space-y-1.5">
							{#each readiness.checks as c (c.key)}
								<li class="flex items-baseline gap-2.5 text-body">
									<span class="w-3 flex-none font-semibold {CHECK_TONE[c.status]}" aria-hidden="true">
										{CHECK_MARK[c.status]}
									</span>
									<span class="w-32 flex-none font-medium text-text">{c.label}</span>
									<span class="min-w-0 text-muted">
										{c.detail}
										<span class="sr-only"> — {c.status}</span>
									</span>
								</li>
							{/each}
						</ul>

						<div class="border-t border-border pt-3">
							<p class="section-label">
								The bar for this language
							</p>
							<p class="mb-3 text-small text-muted">
								Set 0 to drop a requirement. Saving re-checks immediately.
							</p>
							<div class="flex flex-wrap items-end gap-4">
								{#each BAR_FIELDS as f (f.key)}
									<label class="text-small">
										<span class="mb-1 block text-muted">{f.label}</span>
										<input
											type="number"
											min="0"
											class="field w-20"
											value={readiness.thresholds[f.key]}
											disabled={savingBar}
											onchange={(e) =>
												saveThreshold({
													[f.key]: Number((e.currentTarget as HTMLInputElement).value)
												} as Partial<LanguageThresholds>)}
										/>
									</label>
								{/each}
								<label class="flex items-center gap-2 text-small text-muted">
									<input
										type="checkbox"
										checked={readiness.thresholds.require_all_topics}
										disabled={savingBar}
										onchange={(e) =>
											saveThreshold({
												require_all_topics: (e.currentTarget as HTMLInputElement).checked
											})}
									/>
									All topic shelves translated
								</label>
								<label class="flex items-center gap-2 text-small text-muted">
									<input
										type="checkbox"
										checked={readiness.thresholds.require_complete_ui}
										disabled={savingBar}
										onchange={(e) =>
											saveThreshold({
												require_complete_ui: (e.currentTarget as HTMLInputElement).checked
											})}
									/>
									Interface fully translated
								</label>
							</div>
						</div>
					{:else if !readinessError}
						<p class="text-body text-muted">Checking…</p>
					{/if}

					{#if readiness}
						<!-- The switch. Enabled when the checks are clear; the override is a
						     separate, plainer control so launching past a failing check is a
						     deliberate act rather than the same click. -->
						<div class="mt-4 flex flex-wrap items-center gap-3 border-t border-border pt-3">
							{#if readiness.status === 'live'}
								<span class="text-body font-semibold text-accent">Live</span>
								<button
									class="rounded-full border border-border px-4 py-1.5 text-small font-semibold text-muted hover:text-text"
									onclick={checkDeploy}
								>
									Has it shipped?
								</button>
							{:else}
								<button
									class="rounded-full bg-accent px-4 py-1.5 text-small font-semibold text-accent-contrast disabled:opacity-50"
									disabled={launching || !readiness.ready}
									onclick={() => launch(false)}
								>
									{launching ? 'Taking live…' : 'Go live'}
								</button>
								{#if readiness.unforceable.length}
									<!-- A hard blocker (a missing/incomplete UI catalogue) can't be
									     forced: launching would fail the reader build. So no "launch
									     anyway" here — say what to fix instead. -->
									<span class="text-small text-warning">
										Can't go live: {readiness.unforceable.join(', ')} must be
										resolved first (force won't skip {readiness.unforceable.length > 1
											? 'these'
											: 'this'}).
									</span>
								{:else if !readiness.ready}
									<span class="text-small text-muted">
										Clear the {readiness.blocking.length} failing check(s) first, or
									</span>
									<button
										class="text-small font-semibold text-warning underline disabled:opacity-50"
										disabled={launching}
										onclick={() => launch(true)}
									>
										launch anyway
									</button>
								{/if}
							{/if}
							<span class="text-small text-muted">
								Triggers a rebuild — readers see it when that finishes.
							</span>
						</div>

						{#if launchError}
							<p class="mt-2 text-small text-warning">{launchError}</p>
						{/if}

						{#if launchResult?.launched}
							<!-- Recorded and deployed are reported separately: a launch whose
							     rebuild failed is a real state, and one tick would hide it. -->
							<div class="mt-2 space-y-1 text-small">
								<p class="text-accent">
									Recorded as live{launchResult.forced ? ' (forced past failing checks)' : ''}.
								</p>
								{#if launchResult.deploy}
									<p class={launchResult.deploy.status === 'triggered' ? 'text-muted' : 'text-warning'}>
										{launchResult.deploy.detail}
									</p>
								{/if}
							</div>
						{/if}

						{#if deployState}
							<p
								class="mt-2 text-small {deployState.status === 'deployed'
									? 'text-accent'
									: deployState.status === 'pending'
										? 'text-warning'
										: 'text-muted'}"
							>
								{deployState.detail}
							</p>
						{/if}
					{/if}
				</section>

				{#if d.settings}
					<!-- What a translation job will actually use. Kept next to readiness
					     because the Bible and glossary checks above are exactly the ones
					     this section is how you fix. -->
					<LanguageSettingsCard
						settings={d.settings}
						onsaved={() => {
							load();
							loadReadiness(data.code);
						}}
					/>
				{/if}
			{/if}

			{#snippet todoMore(key: string, total: number)}
				{#if total > TODO_CAP}
					<button
						class="mt-2 text-small font-semibold text-accent hover:underline"
						aria-expanded={todoExpanded[key] ?? false}
						onclick={() => (todoExpanded[key] = !todoExpanded[key])}
					>
						{todoExpanded[key] ? 'Show fewer' : `Show all ${fmt(total)}`}
					</button>
				{/if}
			{/snippet}

			<div class="grid gap-6 md:grid-cols-2">
				<!-- Books -->
				<section
					id="sec-books"
					class="scroll-mt-[calc(var(--appnav-h,0px)+4rem)] rounded-card border border-border bg-surface p-5"
				>
					{#snippet booksList()}
						<ul class="space-y-2">
							{#each shown.books as b (b.slug)}
								<li class="flex items-start justify-between gap-3">
									<a href="/books/{b.slug}" class="min-w-0 font-medium text-text hover:text-accent">
										<span class="block truncate">{b.title}</span>
										<span class="text-small text-muted">{b.author} · {fmt(b.chapters)} ch{#if !b.is_published} · <span class="text-warning">unpublished</span>{/if}</span>
									</a>
									<span class="shrink-0 text-small text-muted" title={b.source_type}>{SOURCE_BADGE[b.source_type]}</span>
								</li>
							{/each}
						</ul>
					{/snippet}
					{@render translatedList('Books', shown.books.length, booksList)}
					{#if shown.todoBooks.length}
						<div class="mt-4 border-t border-border pt-3">
							<div class="mb-1 flex items-baseline justify-between gap-3">
								<p class="section-label">Next to work on</p>
								{@render bulkQueueControl('book', shown.todoBooks)}
							</div>
							{#if queueError}
								<p class="mb-2 text-small text-warning">{queueError}</p>
							{/if}
							<ul class="space-y-1.5">
								{#each capTodo('books', shown.todoBooks) as b (b.slug)}
									<li class="flex items-center justify-between gap-3 text-body">
										<span class="min-w-0 truncate">
											<a href="/books/{b.slug}" class="text-accent hover:underline">{b.title}</a>
											<span class="text-small text-muted">· {b.author}</span>
										</span>
										{@render queueControl('book', b.slug)}
									</li>
								{/each}
							</ul>
							{@render todoMore('books', shown.todoBooks.length)}
						</div>
					{/if}
				</section>

				<!-- Long-form bios -->
				<section
					id="sec-bios"
					class="scroll-mt-[calc(var(--appnav-h,0px)+4rem)] rounded-card border border-border bg-surface p-5"
				>
					{#snippet biosList()}
						<ul class="space-y-2">
							{#each shown.bios as a (a.slug)}
								<li class="flex items-center justify-between gap-3">
									<a href="/authors/{a.slug}" class="min-w-0 truncate font-medium text-text hover:text-accent">{a.name}</a>
									{#if !a.reviewed}<span class="shrink-0 text-small text-warning" title="AI translation, unreviewed">unreviewed</span>{/if}
								</li>
							{/each}
						</ul>
					{/snippet}
					{@render translatedList('Long-form bios', shown.bios.length, biosList)}
					{#if shown.todoBios.length}
						<div class="mt-4 border-t border-border pt-3">
							<div class="mb-1 flex items-baseline justify-between gap-3">
								<p class="section-label">
									Next to work on <span class="font-normal normal-case tracking-normal">· most-published authors first</span>
								</p>
								{@render bulkQueueControl('bio', shown.todoBios)}
							</div>
							{#if queueError}
								<p class="mb-2 text-small text-warning">{queueError}</p>
							{/if}
							<ul class="space-y-1.5">
								{#each capTodo('bios', shown.todoBios) as a (a.slug)}
									<li class="flex items-center justify-between gap-3 text-body">
										<span class="min-w-0 truncate">
											<a href="/authors/{a.slug}" class="text-accent hover:underline">{a.name}</a>
											{#if worksLabel(a)}
												<span class="text-small text-muted">· {worksLabel(a)}</span>
											{/if}
										</span>
										{@render queueControl('bio', a.slug)}
									</li>
								{/each}
							</ul>
							{@render todoMore('bios', shown.todoBios.length)}
						</div>
					{/if}
				</section>

				<!-- Sermons -->
				<section
					id="sec-sermons"
					class="scroll-mt-[calc(var(--appnav-h,0px)+4rem)] rounded-card border border-border bg-surface p-5"
				>
					{#snippet sermonsList()}
						<ul class="space-y-2">
							{#each shown.sermons as s (s.slug)}
								<li class="flex items-start justify-between gap-3">
									<a href="/sermons/{s.slug}" class="min-w-0 font-medium text-text hover:text-accent">
										<span class="block truncate">{s.title}</span>
										<span class="text-small text-muted">{s.author}{#if !s.is_published} · <span class="text-warning">unpublished</span>{/if}</span>
									</a>
								</li>
							{/each}
						</ul>
					{/snippet}
					{@render translatedList('Sermons', shown.sermons.length, sermonsList)}
					{#if shown.todoSermons.length}
						<div class="mt-4 border-t border-border pt-3">
							<div class="mb-1 flex items-baseline justify-between gap-3">
								<p class="section-label">Next to work on</p>
								{@render bulkQueueControl('sermon', shown.todoSermons)}
							</div>
							{#if queueError}
								<p class="mb-2 text-small text-warning">{queueError}</p>
							{/if}
							<ul class="space-y-1.5">
								{#each capTodo('sermons', shown.todoSermons) as s (s.slug)}
									<li class="flex items-center justify-between gap-3 text-body">
										<span class="min-w-0 truncate">
											<a href="/sermons/{s.slug}" class="text-accent hover:underline">{s.title}</a>
											<span class="text-small text-muted">· {s.author}</span>
										</span>
										{@render queueControl('sermon', s.slug)}
									</li>
								{/each}
							</ul>
							{@render todoMore('sermons', shown.todoSermons.length)}
						</div>
					{/if}
				</section>

				<!-- Plans -->
				<section
					id="sec-plans"
					class="scroll-mt-[calc(var(--appnav-h,0px)+4rem)] rounded-card border border-border bg-surface p-5"
				>
					{#snippet plansList()}
						<ul class="space-y-2">
							{#each shown.plans as p (p.slug)}
								<li class="flex items-start justify-between gap-3">
									<a href="/plans/{p.slug}" class="min-w-0 font-medium text-text hover:text-accent">
										<span class="block truncate">{p.title}</span>
										<span class="text-small text-muted">{fmt(p.days)} days{#if !p.is_published} · <span class="text-warning">unpublished</span>{/if}</span>
									</a>
								</li>
							{/each}
						</ul>
					{/snippet}
					{@render translatedList('Plans', shown.plans.length, plansList)}
					{#if shown.todoPlans.length}
						<div class="mt-4 border-t border-border pt-3">
							<div class="mb-1 flex items-baseline justify-between gap-3">
								<p class="section-label">Next to work on</p>
								{@render bulkQueueControl('plan', shown.todoPlans)}
							</div>
							{#if queueError}
								<p class="mb-2 text-small text-warning">{queueError}</p>
							{/if}
							<ul class="space-y-1.5">
								{#each capTodo('plans', shown.todoPlans) as p (p.slug)}
									<li class="flex items-center justify-between gap-3 text-body">
										<span class="min-w-0 truncate">
											<a href="/plans/{p.slug}" class="text-accent hover:underline">{p.title}</a>
										</span>
										{@render queueControl('plan', p.slug)}
									</li>
								{/each}
							</ul>
							{@render todoMore('plans', shown.todoPlans.length)}
						</div>
					{/if}
				</section>

				<!-- Topical shelves. Unlike the other types, an untranslated shelf is
				     INVISIBLE in this language rather than shown in English (topic prose
				     has no fallback), so the todo list is every missing shelf, not a
				     ranked top-N — a language wants all of them. -->
				<section
					id="sec-topics"
					class="scroll-mt-[calc(var(--appnav-h,0px)+4rem)] rounded-card border border-border bg-surface p-5"
				>
					{#snippet topicsList()}
						<ul class="space-y-2">
							{#each shown.topics as t (t.slug)}
								<li class="flex items-start justify-between gap-3">
									<a href="/topics/{t.slug}" class="min-w-0 font-medium text-text hover:text-accent">
										<span class="block truncate">{t.title}</span>
									</a>
								</li>
							{/each}
						</ul>
					{/snippet}
					{@render translatedList('Topics', shown.topics.length, topicsList)}
					{#if shown.todoTopics.length}
						<div class="mt-4 border-t border-border pt-3">
							<div class="mb-1 flex items-baseline justify-between gap-3">
								<p class="section-label">
									Hidden in this language ({fmt(shown.todoTopics.length)})
								</p>
								{@render bulkQueueControl('topic', shown.todoTopics)}
							</div>
							<p class="mb-2 text-small text-muted">
								A shelf with no title here is left out of this language's topic page entirely.
							</p>
							{#if queueError}
								<p class="mb-2 text-small text-warning">{queueError}</p>
							{/if}
							<ul class="space-y-1.5">
								{#each capTodo('topics', shown.todoTopics) as t (t.slug)}
									<li class="flex items-center justify-between gap-3 text-body">
										<span class="min-w-0 truncate">
											<a href="/topics/{t.slug}" class="text-accent hover:underline">{t.title}</a>
										</span>
										{@render queueControl('topic', t.slug)}
									</li>
								{/each}
							</ul>
							{@render todoMore('topics', shown.todoTopics.length)}
						</div>
					{/if}
				</section>

				<!-- Articles. Authorless SEO/devotional pages; like sermons, a single
				     body per language. A translated row ships ai_unreviewed until a
				     native speaker approves it. -->
				<section
					id="sec-articles"
					class="scroll-mt-[calc(var(--appnav-h,0px)+4rem)] rounded-card border border-border bg-surface p-5"
				>
					{#snippet articlesList()}
						<ul class="space-y-2">
							{#each shown.articles as a (a.slug)}
								<li class="flex items-start justify-between gap-3">
									<a href="/articles/{a.slug}" class="min-w-0 font-medium text-text hover:text-accent">
										<span class="block truncate">{a.title}</span>
										<span class="text-small text-muted">{fmt(a.word_count)} words{#if !a.is_published} · <span class="text-warning">unpublished</span>{/if}</span>
									</a>
									<span class="shrink-0 text-small text-muted" title={a.source_type}>{SOURCE_BADGE[a.source_type]}</span>
								</li>
							{/each}
						</ul>
					{/snippet}
					{@render translatedList('Articles', shown.articles.length, articlesList)}
					{#if shown.todoArticles.length}
						<div class="mt-4 border-t border-border pt-3">
							<div class="mb-1 flex items-baseline justify-between gap-3">
								<p class="section-label">Next to work on</p>
								{@render bulkQueueControl('article', shown.todoArticles)}
							</div>
							{#if queueError}
								<p class="mb-2 text-small text-warning">{queueError}</p>
							{/if}
							<ul class="space-y-1.5">
								{#each capTodo('articles', shown.todoArticles) as a (a.slug)}
									<li class="flex items-center justify-between gap-3 text-body">
										<span class="min-w-0 truncate">
											<a href="/articles/{a.slug}" class="text-accent hover:underline">{a.title}</a>
										</span>
										{@render queueControl('article', a.slug)}
									</li>
								{/each}
							</ul>
							{@render todoMore('articles', shown.todoArticles.length)}
						</div>
					{/if}
				</section>
			</div>
		{/snippet}
	</AdminGate>
</div>
