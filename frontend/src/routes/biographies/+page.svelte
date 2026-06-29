<script lang="ts">
	import type { AuthorBio } from '$lib/library';

	let { data } = $props();
	const authors = $derived<AuthorBio[]>(data.authors);

	const initials = (name: string) =>
		name.split(' ').filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase();
</script>

<svelte:head><title>Biographies — Ochorus</title></svelte:head>

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
					<span
						class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-accent-soft text-h3 font-semibold text-accent"
						style="font-family: var(--font-display)"
					>
						{initials(author.name)}
					</span>
					<div>
						<h2 class="text-h2">{author.name}</h2>
						{#if author.book_count > 0}
							<a href="/books" class="text-small font-semibold text-accent">
								{author.book_count} book{author.book_count === 1 ? '' : 's'} in the library →
							</a>
						{/if}
					</div>
				</div>
				<p class="mt-4 text-body leading-relaxed text-muted">{author.bio}</p>
			</article>
		{/each}
	</div>
</div>
