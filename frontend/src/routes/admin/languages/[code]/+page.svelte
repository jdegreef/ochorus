<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { ApiError } from '$lib/api';
	import { getAdminLanguageDetail, type AdminLanguageDetail, type SourceType } from '$lib/library';

	let { data } = $props();

	let detail = $state<AdminLanguageDetail | null>(null);
	let loading = $state(true);
	let denied = $state(false);
	let error = $state<string | null>(null);
	let seq = 0;

	async function load(code: string) {
		const id = ++seq;
		loading = true;
		denied = false;
		error = null;
		try {
			const result = await getAdminLanguageDetail(code);
			if (id !== seq) return;
			detail = result;
		} catch (e) {
			if (id !== seq) return;
			if (e instanceof ApiError && (e.status === 401 || e.status === 403)) denied = true;
			else error = e instanceof Error ? e.message : 'Something went wrong loading this language.';
		} finally {
			if (id === seq) loading = false;
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

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number | null | undefined) => nf.format(n ?? 0);

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
		</header>

		<div class="grid gap-6 md:grid-cols-2">
			<!-- Books -->
			<section class="rounded-2xl border border-border bg-surface p-5">
				<h2 class="text-h3 mb-3">Books <span class="text-muted">({fmt(d.books.length)})</span></h2>
				{#if d.books.length}
					<ul class="space-y-2">
						{#each d.books as b (b.slug)}
							<li class="flex items-start justify-between gap-3">
								<a href="/books/{b.slug}" class="min-w-0 font-medium text-text hover:text-accent">
									<span class="block truncate">{b.title}</span>
									<span class="text-small text-muted">{b.author} · {fmt(b.chapters)} ch{#if !b.is_published} · <span class="text-gold">unpublished</span>{/if}</span>
								</a>
								<span class="shrink-0 text-small text-muted" title={b.source_type}>{SOURCE_BADGE[b.source_type]}</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="text-body text-muted">None yet.</p>
				{/if}
				{#if d.todo.books.length}
					<div class="mt-4 border-t border-border pt-3">
						<p class="mb-2 text-small font-semibold uppercase tracking-wide text-muted">Next to work on</p>
						<ul class="space-y-1.5">
							{#each d.todo.books as b (b.slug)}
								<li class="text-body">
									<a href="/books/{b.slug}" class="text-accent hover:underline">{b.title}</a>
									<span class="text-small text-muted">· {b.author}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			</section>

			<!-- Long-form bios -->
			<section class="rounded-2xl border border-border bg-surface p-5">
				<h2 class="text-h3 mb-3">Long-form bios <span class="text-muted">({fmt(d.bios.length)})</span></h2>
				{#if d.bios.length}
					<ul class="space-y-2">
						{#each d.bios as a (a.slug)}
							<li class="flex items-center justify-between gap-3">
								<a href="/authors/{a.slug}" class="min-w-0 truncate font-medium text-text hover:text-accent">{a.name}</a>
								{#if !a.reviewed}<span class="shrink-0 text-small text-gold" title="AI translation, unreviewed">unreviewed</span>{/if}
							</li>
						{/each}
					</ul>
				{:else}
					<p class="text-body text-muted">None yet.</p>
				{/if}
				{#if d.todo.bios.length}
					<div class="mt-4 border-t border-border pt-3">
						<p class="mb-2 text-small font-semibold uppercase tracking-wide text-muted">Next to work on</p>
						<ul class="space-y-1.5">
							{#each d.todo.bios as a (a.slug)}
								<li class="text-body"><a href="/authors/{a.slug}" class="text-accent hover:underline">{a.name}</a></li>
							{/each}
						</ul>
					</div>
				{/if}
			</section>

			<!-- Sermons -->
			<section class="rounded-2xl border border-border bg-surface p-5">
				<h2 class="text-h3 mb-3">Sermons <span class="text-muted">({fmt(d.sermons.length)})</span></h2>
				{#if d.sermons.length}
					<ul class="space-y-2">
						{#each d.sermons as s (s.slug)}
							<li class="flex items-start justify-between gap-3">
								<a href="/sermons/{s.slug}" class="min-w-0 font-medium text-text hover:text-accent">
									<span class="block truncate">{s.title}</span>
									<span class="text-small text-muted">{s.author}{#if !s.is_published} · <span class="text-gold">unpublished</span>{/if}</span>
								</a>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="text-body text-muted">None yet.</p>
				{/if}
				{#if d.todo.sermons.length}
					<div class="mt-4 border-t border-border pt-3">
						<p class="mb-2 text-small font-semibold uppercase tracking-wide text-muted">Next to work on</p>
						<ul class="space-y-1.5">
							{#each d.todo.sermons as s (s.slug)}
								<li class="text-body">
									<a href="/sermons/{s.slug}" class="text-accent hover:underline">{s.title}</a>
									<span class="text-small text-muted">· {s.author}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			</section>

			<!-- Plans -->
			<section class="rounded-2xl border border-border bg-surface p-5">
				<h2 class="text-h3 mb-3">Plans <span class="text-muted">({fmt(d.plans.length)})</span></h2>
				{#if d.plans.length}
					<ul class="space-y-2">
						{#each d.plans as p (p.slug)}
							<li class="flex items-start justify-between gap-3">
								<a href="/plans/{p.slug}" class="min-w-0 font-medium text-text hover:text-accent">
									<span class="block truncate">{p.title}</span>
									<span class="text-small text-muted">{fmt(p.days)} days{#if !p.is_published} · <span class="text-gold">unpublished</span>{/if}</span>
								</a>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="text-body text-muted">None yet.</p>
				{/if}
				{#if d.todo.plans.length}
					<div class="mt-4 border-t border-border pt-3">
						<p class="mb-2 text-small font-semibold uppercase tracking-wide text-muted">Next to work on</p>
						<ul class="space-y-1.5">
							{#each d.todo.plans as p (p.slug)}
								<li class="text-body"><a href="/plans/{p.slug}" class="text-accent hover:underline">{p.title}</a></li>
							{/each}
						</ul>
					</div>
				{/if}
			</section>
		</div>
	{/if}
</div>
