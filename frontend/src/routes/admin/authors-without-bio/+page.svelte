<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { getAdminAuthorsWithoutBio } from '$lib/library-admin';

	const res = adminResource(
		getAdminAuthorsWithoutBio,
		'Something went wrong loading authors.'
	);

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number) => nf.format(n);
	const worksLabel = (a: { books: number; sermons: number }) => {
		const parts: string[] = [];
		if (a.books) parts.push(`${fmt(a.books)} book${a.books === 1 ? '' : 's'}`);
		if (a.sermons) parts.push(`${fmt(a.sermons)} sermon${a.sermons === 1 ? '' : 's'}`);
		return parts.join(' · ') || 'no works yet';
	};
</script>

<svelte:head><title>Admin · Authors without a bio — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-3xl px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<AdminGate resource={res} errorTitle="Couldn't load authors" loadingText="Loading…" panelClass="mt-6">
		{#snippet children(authors)}
			<header class="mb-6 mt-3">
				<p class="eyebrow mb-2 text-accent">Admin · Worklist</p>
				<h1 class="text-display">Authors without a bio</h1>
				<p class="mt-2 text-body text-muted">Authors whose biography is empty, the ones carrying the most content first. Open an author to see their page; write bios with the write-biography workflow.</p>
			</header>

			{#if authors.length}
				<ul class="divide-y divide-border rounded-card border border-border bg-surface">
					{#each authors as a (a.slug)}
						<li class="flex items-baseline justify-between gap-3 px-4 py-3">
							<a href="/authors/{a.slug}" class="min-w-0 truncate font-semibold text-text hover:text-accent" target="_blank" rel="noopener">{a.name} ↗</a>
							<span class="shrink-0 text-small text-muted">{worksLabel(a)}</span>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="rounded-card border border-border bg-surface p-5 text-body text-muted">Every author has a bio.</p>
			{/if}
		{/snippet}
	</AdminGate>
</div>
