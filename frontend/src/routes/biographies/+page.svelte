<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import type { AuthorBio } from '$lib/library';
	import { SITE_URL } from '$lib/config';

	let { data } = $props();
	const authors = $derived<AuthorBio[]>(data.authors);

	const initials = (name: string) =>
		name.split(' ').filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase();

	// Redirect old /biographies#<slug> deep-links to the new author pages.
	onMount(() => {
		const slug = location.hash.replace(/^#/, '');
		if (slug) goto(`/authors/${slug}`, { replaceState: true });
	});
</script>

<svelte:head>
	<title>Biographies — Ochorus</title>
	<meta
		name="description"
		content="The lives behind the books — the preachers, missionaries and writers whose classic Christian works you can read free on Ochorus."
	/>
	<link rel="canonical" href="{SITE_URL}/biographies" />
	<meta property="og:type" content="website" />
	<meta property="og:title" content="Biographies — Ochorus" />
	<meta property="og:url" content="{SITE_URL}/biographies" />
</svelte:head>

<div class="mx-auto max-w-3xl px-5 py-12">
	<header class="mb-10">
		<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">Biographies</p>
		<h1 class="text-display mb-3">Find Your Christian Writers</h1>
		<p class="text-body text-muted">
			The lives behind the books — preachers, missionaries, and writers whose words still speak.
		</p>
	</header>

	<div class="space-y-10">
		{#each authors as author (author.slug)}
			<article id={author.slug} class="scroll-mt-24">
				<div class="flex items-center gap-4">
					<a href="/authors/{author.slug}" class="shrink-0 hover:no-underline">
						<span
							class="flex h-14 w-14 items-center justify-center rounded-full bg-accent-soft text-h3 font-semibold text-accent"
							style="font-family: var(--font-display)"
						>
							{initials(author.name)}
						</span>
					</a>
					<div>
						<h2 class="text-h2">
							<a href="/authors/{author.slug}" class="!text-text hover:underline">{author.name}</a>
						</h2>
						<a href="/authors/{author.slug}" class="text-small font-semibold text-accent">
							{#if author.book_count > 0}
								{author.book_count} book{author.book_count === 1 ? '' : 's'} in the library →
							{:else}
								View biography →
							{/if}
						</a>
					</div>
				</div>
				<p class="mt-4 text-body leading-relaxed text-muted">{author.bio}</p>
			</article>
		{/each}
	</div>
</div>
