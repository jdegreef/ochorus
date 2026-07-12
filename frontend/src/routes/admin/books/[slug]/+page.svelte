<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { ApiError } from '$lib/api';
	import { API_BASE_URL } from '$lib/config';
	import { getAdminBook, type AdminBookDetail, type SourceType } from '$lib/library';

	let { data } = $props();

	let book = $state<AdminBookDetail | null>(null);
	let loading = $state(true);
	let denied = $state(false);
	let error = $state<string | null>(null);
	let seq = 0;

	async function load(slug: string) {
		const id = ++seq;
		loading = true;
		denied = false;
		error = null;
		try {
			const result = await getAdminBook(slug);
			if (id !== seq) return;
			book = result;
		} catch (e) {
			if (id !== seq) return;
			if (e instanceof ApiError && (e.status === 401 || e.status === 403)) denied = true;
			else if (e instanceof ApiError && e.status === 404) error = 'No such work.';
			else error = e instanceof Error ? e.message : 'Something went wrong loading this book.';
		} finally {
			if (id === seq) loading = false;
		}
	}

	$effect(() => {
		const slug = data.slug;
		if (auth.enabled && !auth.initialized) return;
		void auth.user?.email;
		load(slug);
	});

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number | null | undefined) => nf.format(n ?? 0);
	const djangoAdmin = (path: string) => `${API_BASE_URL}${path}`;

	const SOURCE_LABEL: Record<SourceType, string> = {
		public_domain: 'Public domain',
		ai_reviewed: 'AI · reviewed',
		ai_unreviewed: 'AI · unreviewed'
	};
	const FLAG_LABEL: Record<string, string> = {
		'generic-title': 'generic title',
		empty: 'empty',
		tiny: 'tiny',
		giant: 'giant',
		fragmented: 'fragmented',
		'no-dropcap': 'no drop cap',
		'mid-split': 'mid-sentence'
	};
</script>

<svelte:head><title>Admin · {book?.title ?? data.slug} — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	{#if loading && !book}
		<p class="mt-6 text-body text-muted">Loading…</p>
	{:else if denied}
		<div class="mt-6 rounded-2xl border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">Not authorised</h2>
			<p class="text-body text-muted">You don't have access to the admin dashboard.</p>
		</div>
	{:else if error}
		<div class="mt-6 rounded-2xl border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">{error}</h2>
			<button class="btn btn-ghost mt-3" onclick={() => load(data.slug)}>Try again</button>
		</div>
	{:else if book}
		{@const b = book}
		<header class="mb-6 mt-3">
			<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">Admin · Work</p>
			<h1 class="text-display">{b.title}</h1>
			<p class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-body text-muted">
				<span>by <a href="/authors/{b.author.slug}" class="text-accent hover:underline">{b.author.name}</a></span>
				<span class="text-small">·</span>
				<span class="text-small">slug <code class="text-text">{b.slug}</code></span>
				<span class="text-small">·</span>
				<span class="text-small">{b.languages.length} language{b.languages.length === 1 ? '' : 's'}</span>
			</p>
		</header>

		<div class="space-y-5">
			{#each b.languages as l (l.code)}
				<section class="rounded-2xl border border-border bg-surface p-5">
					<div class="mb-3 flex flex-wrap items-start justify-between gap-3">
						<div>
							<h2 class="text-h3">{l.native_name} <span class="text-muted">· {l.name} ({l.code})</span></h2>
							<p class="mt-1 text-body text-text">{l.title}{#if l.subtitle}<span class="text-muted"> — {l.subtitle}</span>{/if}</p>
							<div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-small text-muted">
								<span>{SOURCE_LABEL[l.source_type]}</span>
								<span>· {fmt(l.chapters.length)} ch · {fmt(l.word_count)} words</span>
								{#if !l.is_published}<span class="text-gold">· unpublished</span>{/if}
							</div>
						</div>
						<div class="flex shrink-0 flex-col items-end gap-1 text-small">
							<a href={djangoAdmin(`/admin/library/book/${l.id}/change/`)} class="text-accent hover:underline" target="_blank" rel="noopener">Edit in Django admin ↗</a>
							{#if l.source_url}<a href={l.source_url} class="text-muted hover:text-accent" target="_blank" rel="noopener">source ↗</a>{/if}
							{#if l.pdf_url}<a href={l.pdf_url} class="text-muted hover:text-accent" target="_blank" rel="noopener">PDF ↗</a>{/if}
						</div>
					</div>

					{#if l.chapters.length}
						<ul class="divide-y divide-border rounded-xl border border-border">
							{#each l.chapters as c (c.order)}
								<li class="flex items-baseline justify-between gap-3 px-3 py-2">
									<a href="/books/{b.slug}/{c.order}" class="min-w-0 truncate text-body text-text hover:text-accent">
										<span class="text-muted tabular-nums">{c.order}.</span> {c.title || '(untitled)'}
									</a>
									<span class="flex shrink-0 items-center gap-2">
										{#each c.flags as f (f)}
											<span class="rounded-full border border-gold/40 px-2 py-0.5 text-[0.7rem] text-gold">{FLAG_LABEL[f] ?? f}</span>
										{/each}
										<span class="text-small tabular-nums text-muted">{fmt(c.word_count)}</span>
									</span>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="text-body text-gold">No chapters.</p>
					{/if}
				</section>
			{/each}
		</div>
	{/if}
</div>
