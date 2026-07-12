<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { ApiError } from '$lib/api';
	import { getAdminStats, type AdminStats, type SourceType } from '$lib/library';
	import { localizeHref } from '$lib/paraglide/runtime';

	// Internal tool: copy is English-only (not run through Paraglide).
	let stats = $state<AdminStats | null>(null);
	let loading = $state(true);
	let denied = $state(false);
	let error = $state<string | null>(null);
	let lastUser = $state<string | null | undefined>(undefined);

	async function load() {
		loading = true;
		denied = false;
		error = null;
		try {
			stats = await getAdminStats();
		} catch (e) {
			if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
				denied = true;
			} else {
				error = e instanceof Error ? e.message : 'Something went wrong loading the dashboard.';
			}
		} finally {
			loading = false;
		}
	}

	// Load on mount and whenever the signed-in identity changes (auth initialises
	// asynchronously, so the user may arrive after the first paint).
	$effect(() => {
		const email = auth.user?.email ?? null;
		if (email !== lastUser) {
			lastUser = email;
			load();
		}
	});

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number | null | undefined) => nf.format(n ?? 0);
	const dateFmt = (iso: string) =>
		new Date(iso).toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' });

	const SOURCE_LABELS: Record<SourceType, string> = {
		public_domain: 'Public domain',
		ai_reviewed: 'AI · reviewed',
		ai_unreviewed: 'AI · unreviewed'
	};

	// Headline numbers, in a fixed order.
	const cards = $derived(
		stats
			? [
					{ label: 'Works', value: stats.totals.works, sub: 'distinct titles' },
					{
						label: 'Books',
						value: stats.totals.books,
						sub: `${fmt(stats.totals.published_books)} published`
					},
					{ label: 'Chapters', value: stats.totals.chapters, sub: 'across all books' },
					{ label: 'Words', value: stats.totals.words, sub: 'chapters + sermons' },
					{
						label: 'Sermons',
						value: stats.totals.sermons,
						sub: `${fmt(stats.totals.published_sermons)} published`
					},
					{
						label: 'Plans',
						value: stats.totals.plans,
						sub: `${fmt(stats.totals.published_plans)} published`
					},
					{
						label: 'Authors',
						value: stats.totals.authors,
						sub: `${fmt(stats.totals.authors_with_bio)} with a bio`
					},
					{ label: 'Languages', value: stats.totals.languages, sub: 'with content' }
				]
			: []
	);

	// Content-health chips — only those with a non-zero count are shown.
	const flags = $derived(
		stats
			? [
					{ label: 'unpublished books', n: stats.attention.unpublished_books },
					{ label: 'unpublished sermons', n: stats.attention.unpublished_sermons },
					{ label: 'unreviewed AI translations', n: stats.attention.unreviewed_translations },
					{ label: 'authors without a bio', n: stats.attention.authors_without_bio },
					{ label: 'empty chapters', n: stats.attention.empty_chapters }
				].filter((f) => f.n > 0)
			: []
	);

	const loginHref = `/login?redirect=${encodeURIComponent('/admin')}`;
</script>

<svelte:head><title>Admin — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-6xl px-5 py-10">
	<header class="mb-8 flex flex-wrap items-end justify-between gap-4">
		<div>
			<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">Admin</p>
			<h1 class="text-display">Content dashboard</h1>
			<p class="mt-2 text-body text-muted">A snapshot of the library — quantities, languages and health.</p>
		</div>
		{#if stats}
			<button class="btn btn-ghost" onclick={load} disabled={loading}>
				{loading ? 'Refreshing…' : 'Refresh'}
			</button>
		{/if}
	</header>

	{#if loading && !stats}
		<p class="text-body text-muted">Loading…</p>
	{:else if denied}
		<div class="rounded-2xl border border-border bg-surface p-8">
			{#if auth.enabled && !auth.user}
				<h2 class="text-h3 mb-2">Sign in required</h2>
				<p class="mb-5 text-body text-muted">
					The admin dashboard is restricted. Please sign in with an administrator account.
				</p>
				<a class="btn btn-primary" href={localizeHref(loginHref)}>Sign in</a>
			{:else}
				<h2 class="text-h3 mb-2">Not authorised</h2>
				<p class="text-body text-muted">
					{#if auth.user}This account ({auth.user.email}) doesn't have{:else}You don't have{/if}
					access to the admin dashboard.
				</p>
			{/if}
		</div>
	{:else if error}
		<div class="rounded-2xl border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">Couldn't load the dashboard</h2>
			<p class="mb-5 text-body text-muted">{error}</p>
			<button class="btn btn-ghost" onclick={load}>Try again</button>
		</div>
	{:else if stats}
		<!-- Attention flags -->
		{#if flags.length}
			<div class="mb-8 flex flex-wrap gap-2">
				{#each flags as f (f.label)}
					<span
						class="inline-flex items-center gap-1.5 rounded-full border border-gold/40 bg-gold/10 px-3 py-1 text-small text-gold"
					>
						<strong class="font-semibold">{fmt(f.n)}</strong>
						{f.label}
					</span>
				{/each}
			</div>
		{/if}

		<!-- Headline totals -->
		<section class="mb-10 grid grid-cols-2 gap-3 sm:grid-cols-4">
			{#each cards as c (c.label)}
				<div class="rounded-2xl border border-border bg-surface p-4">
					<div class="text-display !text-3xl !leading-none text-text">{fmt(c.value)}</div>
					<div class="mt-2 text-small font-semibold text-text">{c.label}</div>
					<div class="text-small text-muted">{c.sub}</div>
				</div>
			{/each}
		</section>

		<!-- By language -->
		<section class="mb-10">
			<h2 class="text-h2 mb-3">By language</h2>
			<div class="overflow-x-auto rounded-2xl border border-border bg-surface">
				<table class="w-full min-w-[40rem] border-collapse text-body">
					<thead>
						<tr class="border-b border-border text-small uppercase tracking-wide text-muted">
							<th class="px-4 py-3 text-left font-semibold">Language</th>
							<th class="px-4 py-3 text-right font-semibold">Books</th>
							<th class="px-4 py-3 text-right font-semibold">Chapters</th>
							<th class="px-4 py-3 text-right font-semibold">Sermons</th>
							<th class="px-4 py-3 text-right font-semibold">Plans</th>
							<th class="px-4 py-3 text-right font-semibold">Words</th>
							<th class="px-4 py-3 text-left font-semibold">Source</th>
						</tr>
					</thead>
					<tbody>
						{#each stats.languages as l (l.code)}
							<tr class="border-b border-border last:border-0">
								<td class="px-4 py-3">
									<span class="font-semibold text-text">{l.name}</span>
									<span class="text-small text-muted">· {l.code}</span>
								</td>
								<td class="px-4 py-3 text-right tabular-nums">
									{fmt(l.books)}
									{#if l.published_books !== l.books}
										<span class="text-small text-muted">({fmt(l.published_books)} pub)</span>
									{/if}
								</td>
								<td class="px-4 py-3 text-right tabular-nums">{fmt(l.chapters)}</td>
								<td class="px-4 py-3 text-right tabular-nums">{fmt(l.sermons)}</td>
								<td class="px-4 py-3 text-right tabular-nums">{fmt(l.plans)}</td>
								<td class="px-4 py-3 text-right tabular-nums">{fmt(l.words)}</td>
								<td class="px-4 py-3 text-small text-muted">
									{#if l.source_types.public_domain}<span title="Public domain">PD {l.source_types.public_domain}</span>{/if}
									{#if l.source_types.ai_reviewed}<span class="ml-2" title="AI reviewed">AI✓ {l.source_types.ai_reviewed}</span>{/if}
									{#if l.source_types.ai_unreviewed}<span class="ml-2 text-gold" title="AI unreviewed">AI· {l.source_types.ai_unreviewed}</span>{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</section>

		<div class="grid gap-6 md:grid-cols-2">
			<!-- Books by source type -->
			<section class="rounded-2xl border border-border bg-surface p-5">
				<h2 class="text-h3 mb-3">Books by source</h2>
				<ul class="space-y-2 text-body">
					{#each Object.entries(SOURCE_LABELS) as [key, label] (key)}
						<li class="flex items-center justify-between">
							<span class="text-muted">{label}</span>
							<span class="font-semibold tabular-nums text-text"
								>{fmt(stats.source_types[key as SourceType])}</span
							>
						</li>
					{/each}
					<li class="flex items-center justify-between border-t border-border pt-2">
						<span class="text-muted">Author bio translations</span>
						<span class="font-semibold tabular-nums text-text">
							{fmt(stats.author_translations.total)}
							<span class="text-small font-normal text-muted"
								>({fmt(stats.author_translations.reviewed)} reviewed)</span
							>
						</span>
					</li>
				</ul>
			</section>

			<!-- Recently added -->
			<section class="rounded-2xl border border-border bg-surface p-5">
				<h2 class="text-h3 mb-3">Recently added books</h2>
				{#if stats.recent_books.length}
					<ul class="space-y-3">
						{#each stats.recent_books as b (`${b.slug}-${b.language}`)}
							<li class="flex items-start justify-between gap-3">
								<div class="min-w-0">
									<a
										href={localizeHref(`/books/${b.slug}`)}
										class="block truncate font-semibold text-text hover:text-accent"
										>{b.title}</a
									>
									<div class="text-small text-muted">
										{b.author} · {b.language}
										{#if !b.is_published}· <span class="text-gold">unpublished</span>{/if}
									</div>
								</div>
								<span class="shrink-0 text-small text-muted">{dateFmt(b.created_at)}</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="text-body text-muted">No books yet.</p>
				{/if}
			</section>
		</div>
	{/if}
</div>
