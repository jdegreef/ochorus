<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { getAdminUnpublished } from '$lib/library-admin';

	const res = adminResource(
		getAdminUnpublished,
		'Something went wrong loading unpublished content.'
	);

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number) => nf.format(n);
</script>

<svelte:head><title>Admin · Unpublished — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<AdminGate resource={res} errorTitle="Couldn't load unpublished content" loadingText="Loading…" panelClass="mt-6">
		{#snippet children(d)}
			<header class="mb-6 mt-3">
				<p class="eyebrow mb-2 text-accent">Admin · Worklist</p>
				<h1 class="text-display">Unpublished</h1>
				<p class="mt-2 text-body text-muted">Books and sermons that aren't live on the site. Open one to publish it.</p>
			</header>

			{#if !d.books.length && !d.sermons.length}
				<p class="rounded-card border border-border bg-surface p-5 text-body text-muted">Nothing is unpublished — everything is live.</p>
			{/if}

			{#if d.books.length}
				<section class="mb-8">
					<h2 class="mb-3 text-h3">Books <span class="text-muted">· {fmt(d.books.length)}</span></h2>
					<ul class="divide-y divide-border rounded-card border border-border bg-surface">
						{#each d.books as b (b.slug + b.language)}
							<li class="flex items-baseline justify-between gap-3 px-4 py-3">
								<a href="/admin/books/{b.slug}" class="min-w-0">
									<span class="block truncate font-semibold text-text hover:text-accent">{b.title}</span>
									<span class="text-small text-muted">{b.author} · {b.language} · {fmt(b.chapters)} ch · {fmt(b.words)} words</span>
								</a>
								<span class="shrink-0 text-small font-semibold text-accent">Publish →</span>
							</li>
						{/each}
					</ul>
				</section>
			{/if}

			{#if d.sermons.length}
				<section>
					<h2 class="mb-3 text-h3">Sermons <span class="text-muted">· {fmt(d.sermons.length)}</span></h2>
					<ul class="divide-y divide-border rounded-card border border-border bg-surface">
						{#each d.sermons as s (s.slug + s.language)}
							<li class="flex items-baseline justify-between gap-3 px-4 py-3">
								<a href="/admin/sermons/{s.slug}" class="min-w-0">
									<span class="block truncate font-semibold text-text hover:text-accent">{s.title}</span>
									<span class="text-small text-muted">{s.author} · {s.language}</span>
								</a>
								<span class="shrink-0 text-small font-semibold text-accent">Publish →</span>
							</li>
						{/each}
					</ul>
				</section>
			{/if}
		{/snippet}
	</AdminGate>
</div>
