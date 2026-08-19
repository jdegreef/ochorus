<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { ApiError } from '$lib/api';
	import { getAdminAudit, type AdminAudit, type AuditChapterFinding } from '$lib/library';

	let audit = $state<AdminAudit | null>(null);
	let loading = $state(true);
	let denied = $state(false);
	let error = $state<string | null>(null);
	let seq = 0;

	async function load() {
		const id = ++seq;
		loading = true;
		denied = false;
		error = null;
		try {
			const result = await getAdminAudit();
			if (id !== seq) return;
			audit = result;
		} catch (e) {
			if (id !== seq) return;
			if (e instanceof ApiError && (e.status === 401 || e.status === 403)) denied = true;
			else error = e instanceof Error ? e.message : 'Something went wrong running the audit.';
		} finally {
			if (id === seq) loading = false;
		}
	}

	$effect(() => {
		if (auth.enabled && !auth.initialized) return;
		void auth.user?.email;
		load();
	});

	// Quality checks, ordered by reader impact.
	const QUALITY: { key: keyof AdminAudit['quality']; label: string; desc: string }[] = [
		{ key: 'mid_sentence_splits', label: 'Mid-sentence splits', desc: "Chapter body doesn't end in sentence punctuation" },
		{ key: 'generic_titles', label: 'Generic / missing titles', desc: 'Empty title, or a bare “Chapter N”' },
		{ key: 'missing_dropcap', label: 'Missing drop cap', desc: 'Body starts lower-case or mid-word' },
		{ key: 'fragmented', label: 'Fragmented paragraphs', desc: 'Very low words-per-paragraph' },
		{ key: 'duplicate_titles', label: 'Duplicate titles in a book', desc: 'Same title on multiple chapters' },
		{ key: 'tiny_chapters', label: 'Tiny chapters', desc: 'Under 150 words' },
		{ key: 'giant_chapters', label: 'Giant chapters', desc: 'Over 8,000 words — a split may be missed' }
	];
	const totalFindings = $derived(
		audit
			? [...Object.values(audit.quality), ...Object.values(audit.integrity)].reduce(
					(n, c) => n + c.total,
					0
				)
			: 0
	);

	function evidence(f: AuditChapterFinding): string {
		if (f.avg_words != null) return `${f.avg_words} words/¶ · ${f.paragraphs} ¶`;
		if (f.word_count != null) return `${f.word_count} words`;
		if (f.starts) return `“${f.starts}…”`;
		if (f.ends) return `…${f.ends}`;
		return '';
	}
</script>

<svelte:head><title>Admin · Audit — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
	<header class="mb-6 flex flex-wrap items-end justify-between gap-3">
		<div>
			<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">Admin</p>
			<h1 class="text-display">Content audit</h1>
			<p class="mt-2 text-body text-muted">Quality and integrity checks across the library. Heuristics are advisory — read the chapter before fixing.</p>
		</div>
		{#if audit}
			<button class="btn btn-ghost" onclick={load} disabled={loading}>{loading ? 'Re-running…' : 'Re-run'}</button>
		{/if}
	</header>

	{#if loading && !audit}
		<p class="text-body text-muted">Running audit…</p>
	{:else if denied}
		<div class="rounded-2xl border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">Not authorised</h2>
			<p class="text-body text-muted">You don't have access to the admin dashboard.</p>
		</div>
	{:else if error}
		<div class="rounded-2xl border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">Couldn't run the audit</h2>
			<p class="mb-5 text-body text-muted">{error}</p>
			<button class="btn btn-ghost" onclick={load}>Try again</button>
		</div>
	{:else if audit}
		{@const a = audit}
		<p class="mb-6 text-body {totalFindings ? 'text-warning' : 'text-muted'}">
			{#if totalFindings}<strong>{totalFindings}</strong> finding{totalFindings === 1 ? '' : 's'} across all checks.{:else}No findings — the library looks clean. 🎉{/if}
		</p>

		{#snippet chapterItem(f: AuditChapterFinding)}
			<li class="flex items-baseline justify-between gap-3 py-1.5">
				<a href="/books/{f.book}/{f.order}" class="min-w-0 truncate text-body text-text hover:text-accent">
					<span class="text-muted">{f.book}/{f.order}</span> — {f.title || '(untitled)'}
				</a>
				{#if evidence(f)}<span class="shrink-0 text-small text-muted">{evidence(f)}</span>{/if}
			</li>
		{/snippet}

		{#snippet section(label: string, desc: string, total: number, hasItems: boolean)}
			<div class="flex items-baseline justify-between gap-3 border-b border-border pb-1">
				<h3 class="text-body font-semibold text-text">{label}</h3>
				<span class="shrink-0 text-small {total ? 'text-warning' : 'text-muted'}">{total || 'none'}</span>
			</div>
			{#if desc}<p class="mt-1 text-small text-muted">{desc}</p>{/if}
			{#if !hasItems && total}<p class="mt-1 text-small text-muted">Showing first items…</p>{/if}
		{/snippet}

		<div class="grid gap-6 md:grid-cols-2">
			<!-- Quality -->
			<section>
				<h2 class="text-h3 mb-3">Content quality</h2>
				<div class="space-y-5">
					{#each QUALITY as check (check.key)}
						{@const c = a.quality[check.key]}
						<div>
							{@render section(check.label, check.desc, c.total, c.items.length >= c.total)}
							{#if c.total}
								<ul class="mt-1">
									{#if check.key === 'duplicate_titles'}
										{#each a.quality.duplicate_titles.items as f (f.book + f.title)}
											<li class="flex items-baseline justify-between gap-3 py-1.5">
												<a href="/books/{f.book}" class="min-w-0 truncate text-body text-text hover:text-accent"><span class="text-muted">{f.book}</span> — “{f.title}”</a>
												<span class="shrink-0 text-small text-muted">×{f.count}</span>
											</li>
										{/each}
									{:else}
										{#each (c.items as AuditChapterFinding[]) as f (f.book + '/' + f.order)}
											{@render chapterItem(f)}
										{/each}
									{/if}
								</ul>
								{#if c.items.length < c.total}<p class="mt-1 text-small text-muted">…and {c.total - c.items.length} more</p>{/if}
							{/if}
						</div>
					{/each}
				</div>
			</section>

			<!-- Integrity -->
			<section>
				<h2 class="text-h3 mb-3">Data integrity</h2>
				<div class="space-y-5">
					<!-- Broken plan days -->
					<div>
						{@render section('Broken plan days', 'A plan day points at a missing chapter', a.integrity.broken_plan_days.total, true)}
						{#if a.integrity.broken_plan_days.total}
							<ul class="mt-1">
								{#each a.integrity.broken_plan_days.items as d (d.plan + d.day)}
									<li class="py-1.5 text-body">
										<a href="/plans/{d.plan}" class="text-text hover:text-accent">{d.plan}</a>
										<span class="text-small text-muted">day {d.day} → {d.book}/{d.order} ({d.language})</span>
									</li>
								{/each}
							</ul>
						{/if}
					</div>
					<!-- Empty books -->
					<div>
						{@render section('Books with no chapters', '', a.integrity.empty_books.total, true)}
						{#if a.integrity.empty_books.total}
							<ul class="mt-1">
								{#each a.integrity.empty_books.items as b (b.book + b.language)}
									<li class="py-1.5 text-body"><a href="/books/{b.book}" class="text-text hover:text-accent">{b.title}</a> <span class="text-small text-muted">{b.author} · {b.language}</span></li>
								{/each}
							</ul>
						{/if}
					</div>
					<!-- Empty chapters -->
					<div>
						{@render section('Empty chapters', 'No body text', a.integrity.empty_chapters.total, a.integrity.empty_chapters.items.length >= a.integrity.empty_chapters.total)}
						{#if a.integrity.empty_chapters.total}
							<ul class="mt-1">
								{#each a.integrity.empty_chapters.items as f (f.book + '/' + f.order)}
									{@render chapterItem(f)}
								{/each}
							</ul>
							{#if a.integrity.empty_chapters.items.length < a.integrity.empty_chapters.total}<p class="mt-1 text-small text-muted">…and {a.integrity.empty_chapters.total - a.integrity.empty_chapters.items.length} more</p>{/if}
						{/if}
					</div>
					<!-- Order gaps -->
					<div>
						{@render section('Chapter-order gaps', 'Missing chapter numbers', a.integrity.order_gaps.total, true)}
						{#if a.integrity.order_gaps.total}
							<ul class="mt-1">
								{#each a.integrity.order_gaps.items as g (g.book)}
									<li class="py-1.5 text-body"><a href="/books/{g.book}" class="text-text hover:text-accent">{g.book}</a> <span class="text-small text-muted">missing {g.missing.join(', ')} of {g.count}</span></li>
								{/each}
							</ul>
						{/if}
					</div>
				</div>
			</section>
		</div>
	{/if}
</div>
