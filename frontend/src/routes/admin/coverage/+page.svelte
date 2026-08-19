<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { ApiError } from '$lib/api';
	import { getAdminCoverage, type AdminCoverage, type AdminCoverageRow } from '$lib/library';

	let cov = $state<AdminCoverage | null>(null);
	let loading = $state(true);
	let denied = $state(false);
	let error = $state<string | null>(null);
	let seq = 0;

	type Tab = 'books' | 'sermons' | 'plans';
	let tab = $state<Tab>('books');

	async function load() {
		const id = ++seq;
		loading = true;
		denied = false;
		error = null;
		try {
			const result = await getAdminCoverage();
			if (id !== seq) return;
			cov = result;
		} catch (e) {
			if (id !== seq) return;
			if (e instanceof ApiError && (e.status === 401 || e.status === 403)) denied = true;
			else error = e instanceof Error ? e.message : 'Something went wrong loading coverage.';
		} finally {
			if (id === seq) loading = false;
		}
	}

	$effect(() => {
		if (auth.enabled && !auth.initialized) return;
		void auth.user?.email;
		load();
	});

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
</script>

<svelte:head><title>Admin · Coverage — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-6xl px-5 py-10">
	<header class="mb-6">
		<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">Admin</p>
		<h1 class="text-display">Coverage matrix</h1>
		<p class="mt-2 text-body text-muted">Every work × language — where each is translated, and where the gaps are.</p>
	</header>

	{#if loading && !cov}
		<p class="text-body text-muted">Loading…</p>
	{:else if denied}
		<div class="rounded-2xl border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">Not authorised</h2>
			<p class="text-body text-muted">You don't have access to the admin dashboard.</p>
		</div>
	{:else if error}
		<div class="rounded-2xl border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">Couldn't load coverage</h2>
			<p class="mb-5 text-body text-muted">{error}</p>
			<button class="btn btn-ghost" onclick={load}>Try again</button>
		</div>
	{:else if cov}
		<!-- Tabs -->
		<div class="mb-4 flex flex-wrap items-center gap-2">
			{#each TABS as t (t.key)}
				<button
					class="rounded-full border px-3.5 py-1.5 text-small font-semibold {tab === t.key
						? 'border-accent-soft-border bg-accent-soft text-accent'
						: 'border-border text-muted hover:text-text'}"
					onclick={() => (tab = t.key)}
				>
					{t.label} ({cov[t.key].length})
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
		</div>

		<div class="overflow-x-auto rounded-2xl border border-border bg-surface">
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
								{@const m = cellMeta(r.cells[l.code])}
								<td class="px-3 py-2.5 text-center">
									<span class="inline-flex min-w-[2.2rem] justify-center rounded-full px-1.5 py-0.5 text-small {m.cls}">{m.label}</span>
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
	{/if}
</div>
