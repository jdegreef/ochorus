<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { ApiError } from '$lib/api';
	import {
		getReviewQueue,
		approveReview,
		type ReviewQueue,
		type ReviewQueueBook,
		type ReviewQueueBio
	} from '$lib/library';

	let queue = $state<ReviewQueue | null>(null);
	let loading = $state(true);
	let denied = $state(false);
	let error = $state<string | null>(null);
	let seq = 0;

	// Per-item state keyed by `${kind}:${slug}:${language}`.
	let busy = $state<Record<string, boolean>>({});
	let rowError = $state<Record<string, string>>({});

	const key = (kind: string, slug: string, language: string) => `${kind}:${slug}:${language}`;

	async function load() {
		const id = ++seq;
		loading = true;
		denied = false;
		error = null;
		try {
			const result = await getReviewQueue();
			if (id !== seq) return;
			queue = result;
		} catch (e) {
			if (id !== seq) return;
			if (e instanceof ApiError && (e.status === 401 || e.status === 403)) denied = true;
			else error = e instanceof Error ? e.message : 'Something went wrong loading the queue.';
		} finally {
			if (id === seq) loading = false;
		}
	}

	$effect(() => {
		if (auth.enabled && !auth.initialized) return;
		void auth.user?.email;
		load();
	});

	async function approve(kind: 'book' | 'bio', slug: string, language: string) {
		const k = key(kind, slug, language);
		busy = { ...busy, [k]: true };
		rowError = { ...rowError, [k]: '' };
		try {
			await approveReview({ kind, slug, language });
			// Drop the approved item from the local list.
			if (queue) {
				if (kind === 'book') {
					queue.books = queue.books.filter((b) => !(b.slug === slug && b.language === language));
				} else {
					queue.bios = queue.bios.filter((b) => !(b.slug === slug && b.language === language));
				}
			}
		} catch (e) {
			const msg =
				e instanceof ApiError && e.body && typeof e.body === 'object' && 'detail' in e.body
					? String((e.body as { detail: unknown }).detail)
					: 'Approve failed.';
			rowError = { ...rowError, [k]: msg };
		} finally {
			busy = { ...busy, [k]: false };
		}
	}

	const total = $derived((queue?.books.length ?? 0) + (queue?.bios.length ?? 0));
</script>

<svelte:head><title>Admin · Review queue — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-3xl px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<header class="mb-6 mt-3">
		<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">Admin</p>
		<h1 class="text-display">Review queue</h1>
		<p class="mt-2 text-body text-muted">
			AI translations awaiting a native-speaker check. Approving clears the “awaiting review” badge in the reader.
		</p>
	</header>

	{#if loading && !queue}
		<p class="text-body text-muted">Loading…</p>
	{:else if denied}
		<div class="rounded-2xl border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">Not authorised</h2>
			<p class="text-body text-muted">You don't have access to the admin dashboard.</p>
		</div>
	{:else if error}
		<div class="rounded-2xl border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">Couldn't load the queue</h2>
			<p class="mb-5 text-body text-muted">{error}</p>
			<button class="btn btn-ghost" onclick={load}>Try again</button>
		</div>
	{:else if queue}
		{#if total === 0}
			<div class="rounded-2xl border border-border bg-surface p-8 text-center">
				<p class="text-h3">All clear 🎉</p>
				<p class="mt-1 text-body text-muted">Nothing is awaiting review.</p>
			</div>
		{:else}
			<!-- Books -->
			<section class="mb-8">
				<h2 class="text-h3 mb-3">Books <span class="text-muted">({queue.books.length})</span></h2>
				{#if queue.books.length}
					<ul class="space-y-2">
						{#each queue.books as b (key('book', b.slug, b.language))}
							{@const k = key('book', b.slug, b.language)}
							<li class="rounded-xl border border-border bg-surface p-4">
								<div class="flex items-center justify-between gap-3">
									<div class="min-w-0">
										<a href="/books/{b.slug}" class="block truncate font-semibold text-text hover:text-accent">{b.title}</a>
										<div class="text-small text-muted">
											{b.author} · <span class="text-gold uppercase">{b.language}</span> · {b.chapters} ch
										</div>
									</div>
									<button
										class="btn btn-primary shrink-0 !py-1.5 !text-small"
										disabled={busy[k]}
										onclick={() => approve('book', b.slug, b.language)}
									>
										{busy[k] ? 'Approving…' : 'Approve'}
									</button>
								</div>
								{#if rowError[k]}<p class="mt-2 text-small text-gold">{rowError[k]}</p>{/if}
							</li>
						{/each}
					</ul>
				{:else}
					<p class="text-body text-muted">None.</p>
				{/if}
			</section>

			<!-- Author bios -->
			<section>
				<h2 class="text-h3 mb-3">Author bios <span class="text-muted">({queue.bios.length})</span></h2>
				{#if queue.bios.length}
					<ul class="space-y-2">
						{#each queue.bios as b (key('bio', b.slug, b.language))}
							{@const k = key('bio', b.slug, b.language)}
							<li class="rounded-xl border border-border bg-surface p-4">
								<div class="flex items-center justify-between gap-3">
									<div class="min-w-0">
										<a href="/authors/{b.slug}" class="block truncate font-semibold text-text hover:text-accent">{b.name}</a>
										<div class="text-small text-muted">
											<span class="text-gold uppercase">{b.language}</span>
											· {[b.has_short && 'short', b.has_long && 'long-form'].filter(Boolean).join(' + ')} bio
										</div>
									</div>
									<button
										class="btn btn-primary shrink-0 !py-1.5 !text-small"
										disabled={busy[k]}
										onclick={() => approve('bio', b.slug, b.language)}
									>
										{busy[k] ? 'Approving…' : 'Approve'}
									</button>
								</div>
								{#if rowError[k]}<p class="mt-2 text-small text-gold">{rowError[k]}</p>{/if}
							</li>
						{/each}
					</ul>
				{:else}
					<p class="text-body text-muted">None.</p>
				{/if}
			</section>
		{/if}
	{/if}
</div>
