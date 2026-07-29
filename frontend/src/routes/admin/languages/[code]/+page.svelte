<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { ApiError } from '$lib/api';
	import {
		getAdminLanguageDetail,
		getAdminTranslationJobs,
		createAdminTranslationJob,
		type AdminLangBio,
		type AdminLanguageDetail,
		type AdminTranslationJob,
		type SourceType,
		type TranslationJobType
	} from '$lib/library';

	let { data } = $props();

	let detail = $state<AdminLanguageDetail | null>(null);
	let loading = $state(true);
	let denied = $state(false);
	let error = $state<string | null>(null);
	let seq = 0;

	// Translation queue (buttons on the todo lists). Derived state: queued =
	// open GitHub issue, in_progress = claimed by a worker session. null
	// configured = the GET failed — keep the buttons and let POST surface errors.
	let jobs = $state<AdminTranslationJob[]>([]);
	let jobsConfigured = $state<boolean | null>(null);
	let queueing = $state<string | null>(null); // "type:slug" while POSTing
	let queueError = $state<string | null>(null);

	async function load(code: string) {
		const id = ++seq;
		loading = true;
		denied = false;
		error = null;
		try {
			const result = await getAdminLanguageDetail(code);
			if (id !== seq) return;
			detail = result;
			if (!result.is_source) void loadJobs();
		} catch (e) {
			if (id !== seq) return;
			if (e instanceof ApiError && (e.status === 401 || e.status === 403)) denied = true;
			else error = e instanceof Error ? e.message : 'Something went wrong loading this language.';
		} finally {
			if (id === seq) loading = false;
		}
	}

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

	async function queue(type: TranslationJobType, slug: string) {
		queueError = null;
		queueing = `${type}:${slug}`;
		try {
			const res = await createAdminTranslationJob({ type, slug, language: data.code });
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

	// Fetch once auth has settled, and again when the language (route param) or
	// signed-in identity changes.
	$effect(() => {
		const code = data.code;
		if (auth.enabled && !auth.initialized) return;
		void auth.user?.email;
		load(code);
	});

	// What each section shows. "Live" is what a reader can actually reach in this
	// language right now (published rows only — an unpublished translation exists
	// but serves nothing); "suggested" is the ranked queue of what to do next.
	type View = 'all' | 'live' | 'suggested';
	let view = $state<View>('all');
	const VIEWS: { id: View; label: string }[] = [
		{ id: 'all', label: 'All' },
		{ id: 'live', label: 'Live on site' },
		{ id: 'suggested', label: 'Suggested' }
	];

	/** Books/sermons/plans to list: none under "suggested", published-only under "live". */
	const present = <T extends { is_published: boolean }>(rows: T[]): T[] =>
		view === 'suggested' ? [] : view === 'live' ? rows.filter((r) => r.is_published) : rows;
	/** Bios have no publish flag — a translated biography either exists or doesn't,
	 *  and if it exists it is live. So "live" and "all" show the same rows. */
	const presentBios = (rows: AdminLangBio[]): AdminLangBio[] =>
		view === 'suggested' ? [] : rows;
	/** Todo rows to list: hidden under "live". */
	const suggested = <T,>(rows: T[]): T[] => (view === 'live' ? [] : rows);

	// One derived view of the payload, so the template stays declarative —
	// Svelte 5 won't allow {@const} as a direct child of <section>.
	const shown = $derived({
		books: present(detail?.books ?? []),
		sermons: present(detail?.sermons ?? []),
		plans: present(detail?.plans ?? []),
		bios: presentBios(detail?.bios ?? []),
		todoBooks: suggested(detail?.todo.books ?? []),
		todoSermons: suggested(detail?.todo.sermons ?? []),
		todoPlans: suggested(detail?.todo.plans ?? []),
		todoBios: suggested(detail?.todo.bios ?? [])
	});
	// Under "suggested" an empty translated list is the point, not a gap.
	const emptyLabel = $derived(
		view === 'live' ? 'Nothing live yet.' : view === 'suggested' ? '' : 'None yet.'
	);

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

	{#if loading && !detail}
		<p class="mt-6 text-body text-muted">Loading…</p>
	{:else if denied}
		<div class="mt-6 rounded-2xl border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">Not authorised</h2>
			<p class="text-body text-muted">You don't have access to the admin dashboard.</p>
		</div>
	{:else if error}
		<div class="mt-6 rounded-2xl border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">Couldn't load this language</h2>
			<p class="mb-5 text-body text-muted">{error}</p>
			<button class="btn btn-ghost" onclick={() => load(data.code)}>Try again</button>
		</div>
	{:else if detail}
		{@const d = detail}
		{#snippet queueControl(type: TranslationJobType, slug: string)}
			{@const job = jobFor(type, slug)}
			{#if job}
				<a
					href={job.url}
					target="_blank"
					rel="noopener"
					class="shrink-0 rounded-full border px-2.5 py-0.5 text-small hover:no-underline {job.state ===
					'in_progress'
						? 'border-border bg-surface-2 text-gold'
						: 'border-accent-soft-border bg-accent-soft text-accent'}"
					title="Open the job issue on GitHub"
				>
					{job.state === 'in_progress' ? 'Translating…' : 'Queued ↗'}
				</a>
			{:else}
				<button
					class="btn btn-ghost shrink-0 !px-2.5 !py-0.5 !text-small"
					disabled={jobsConfigured === false || queueing !== null}
					title={jobsConfigured === false
						? 'Set GITHUB_TRANSLATION_TOKEN on the API to enable the queue'
						: `Queue a ${d.language.name} translation`}
					onclick={() => queue(type, slug)}
				>
					{queueing === `${type}:${slug}` ? 'Queueing…' : 'Translate'}
				</button>
			{/if}
		{/snippet}
		<header class="mb-8 mt-3">
			<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">Admin · Language</p>
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
				<p class="mt-3 text-body text-muted">
					<strong class="text-text">{fmt(d.books.length)}</strong>/{fmt(d.english_counts.books)} books ·
					<strong class="text-text">{fmt(d.sermons.length)}</strong>/{fmt(d.english_counts.sermons)} sermons ·
					<strong class="text-text">{fmt(d.plans.length)}</strong>/{fmt(d.english_counts.plans)} plans ·
					<strong class="text-text">{fmt(d.bios.length)}</strong>/{fmt(d.english_counts.bios)} long-form bios translated
				</p>
			{/if}
			{#if !d.is_source}
				<div class="mt-4 flex flex-wrap items-center gap-2" role="group" aria-label="Filter what each section shows">
					{#each VIEWS as v (v.id)}
						<button
							class="rounded-full border px-3.5 py-1.5 text-small font-semibold {view === v.id
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
						{:else}Everything — translated and suggested.{/if}
					</span>
				</div>
			{/if}
		</header>

		<div class="grid gap-6 md:grid-cols-2">
			<!-- Books -->
			<section class="rounded-2xl border border-border bg-surface p-5">
				<h2 class="text-h3 mb-3">Books <span class="text-muted">({fmt(shown.books.length)})</span></h2>
				{#if shown.books.length}
					<ul class="space-y-2">
						{#each shown.books as b (b.slug)}
							<li class="flex items-start justify-between gap-3">
								<a href="/books/{b.slug}" class="min-w-0 font-medium text-text hover:text-accent">
									<span class="block truncate">{b.title}</span>
									<span class="text-small text-muted">{b.author} · {fmt(b.chapters)} ch{#if !b.is_published} · <span class="text-gold">unpublished</span>{/if}</span>
								</a>
								<span class="shrink-0 text-small text-muted" title={b.source_type}>{SOURCE_BADGE[b.source_type]}</span>
							</li>
						{/each}
					</ul>
				{:else if emptyLabel}
					<p class="text-body text-muted">{emptyLabel}</p>
				{/if}
				{#if shown.todoBooks.length}
					<div class="mt-4 border-t border-border pt-3">
						<p class="mb-2 text-small font-semibold uppercase tracking-wide text-muted">Next to work on</p>
						{#if queueError}
							<p class="mb-2 text-small text-gold">{queueError}</p>
						{/if}
						<ul class="space-y-1.5">
							{#each shown.todoBooks as b (b.slug)}
								<li class="flex items-center justify-between gap-3 text-body">
									<span class="min-w-0 truncate">
										<a href="/books/{b.slug}" class="text-accent hover:underline">{b.title}</a>
										<span class="text-small text-muted">· {b.author}</span>
									</span>
									{@render queueControl('book', b.slug)}
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			</section>

			<!-- Long-form bios -->
			<section class="rounded-2xl border border-border bg-surface p-5">
				<h2 class="text-h3 mb-3">Long-form bios <span class="text-muted">({fmt(shown.bios.length)})</span></h2>
				{#if shown.bios.length}
					<ul class="space-y-2">
						{#each shown.bios as a (a.slug)}
							<li class="flex items-center justify-between gap-3">
								<a href="/authors/{a.slug}" class="min-w-0 truncate font-medium text-text hover:text-accent">{a.name}</a>
								{#if !a.reviewed}<span class="shrink-0 text-small text-gold" title="AI translation, unreviewed">unreviewed</span>{/if}
							</li>
						{/each}
					</ul>
				{:else if emptyLabel}
					<p class="text-body text-muted">{emptyLabel}</p>
				{/if}
				{#if shown.todoBios.length}
					<div class="mt-4 border-t border-border pt-3">
						<p class="mb-2 text-small font-semibold uppercase tracking-wide text-muted">
							Next to work on <span class="font-normal normal-case tracking-normal">· most-published authors first</span>
						</p>
						{#if queueError}
							<p class="mb-2 text-small text-gold">{queueError}</p>
						{/if}
						<ul class="space-y-1.5">
							{#each shown.todoBios as a (a.slug)}
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
					</div>
				{/if}
			</section>

			<!-- Sermons -->
			<section class="rounded-2xl border border-border bg-surface p-5">
				<h2 class="text-h3 mb-3">Sermons <span class="text-muted">({fmt(shown.sermons.length)})</span></h2>
				{#if shown.sermons.length}
					<ul class="space-y-2">
						{#each shown.sermons as s (s.slug)}
							<li class="flex items-start justify-between gap-3">
								<a href="/sermons/{s.slug}" class="min-w-0 font-medium text-text hover:text-accent">
									<span class="block truncate">{s.title}</span>
									<span class="text-small text-muted">{s.author}{#if !s.is_published} · <span class="text-gold">unpublished</span>{/if}</span>
								</a>
							</li>
						{/each}
					</ul>
				{:else if emptyLabel}
					<p class="text-body text-muted">{emptyLabel}</p>
				{/if}
				{#if shown.todoSermons.length}
					<div class="mt-4 border-t border-border pt-3">
						<p class="mb-2 text-small font-semibold uppercase tracking-wide text-muted">Next to work on</p>
						{#if queueError}
							<p class="mb-2 text-small text-gold">{queueError}</p>
						{/if}
						<ul class="space-y-1.5">
							{#each shown.todoSermons as s (s.slug)}
								<li class="flex items-center justify-between gap-3 text-body">
									<span class="min-w-0 truncate">
										<a href="/sermons/{s.slug}" class="text-accent hover:underline">{s.title}</a>
										<span class="text-small text-muted">· {s.author}</span>
									</span>
									{@render queueControl('sermon', s.slug)}
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			</section>

			<!-- Plans -->
			<section class="rounded-2xl border border-border bg-surface p-5">
				<h2 class="text-h3 mb-3">Plans <span class="text-muted">({fmt(shown.plans.length)})</span></h2>
				{#if shown.plans.length}
					<ul class="space-y-2">
						{#each shown.plans as p (p.slug)}
							<li class="flex items-start justify-between gap-3">
								<a href="/plans/{p.slug}" class="min-w-0 font-medium text-text hover:text-accent">
									<span class="block truncate">{p.title}</span>
									<span class="text-small text-muted">{fmt(p.days)} days{#if !p.is_published} · <span class="text-gold">unpublished</span>{/if}</span>
								</a>
							</li>
						{/each}
					</ul>
				{:else if emptyLabel}
					<p class="text-body text-muted">{emptyLabel}</p>
				{/if}
				{#if shown.todoPlans.length}
					<div class="mt-4 border-t border-border pt-3">
						<p class="mb-2 text-small font-semibold uppercase tracking-wide text-muted">Next to work on</p>
						{#if queueError}
							<p class="mb-2 text-small text-gold">{queueError}</p>
						{/if}
						<ul class="space-y-1.5">
							{#each shown.todoPlans as p (p.slug)}
								<li class="flex items-center justify-between gap-3 text-body">
									<span class="min-w-0 truncate">
										<a href="/plans/{p.slug}" class="text-accent hover:underline">{p.title}</a>
									</span>
									{@render queueControl('plan', p.slug)}
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			</section>
		</div>
	{/if}
</div>
