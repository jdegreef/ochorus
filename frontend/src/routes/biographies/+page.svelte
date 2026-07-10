<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import type { AuthorBio } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';

	const t = i18n.t;

	let { data } = $props();
	const authors = $derived<AuthorBio[]>(data.authors);

	const initials = (name: string) =>
		name.split(' ').filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase();

	// Redirect old /biographies#<slug> deep-links to the new author pages.
	onMount(() => {
		const slug = location.hash.replace(/^#/, '');
		if (slug) goto(localizeHref(`/authors/${slug}`), { replaceState: true });
	});
</script>

<svelte:head>
	<title>{t('bios.eyebrow')} — Ochorus</title>
	<meta name="description" content={t('bios.metaDescription')} />
	<link rel="canonical" href="{SITE_URL}{localizeHref('/biographies')}" />
	<meta property="og:type" content="website" />
	<meta property="og:title" content="{t('bios.eyebrow')} — Ochorus" />
	<meta property="og:url" content="{SITE_URL}{localizeHref('/biographies')}" />
</svelte:head>

<div class="mx-auto max-w-3xl px-5 py-12">
	<header class="mb-10">
		<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">{t('bios.eyebrow')}</p>
		<h1 class="text-display mb-3">{t('bios.title')}</h1>
		<p class="text-body text-muted">
			{t('bios.tagline')}
		</p>
	</header>

	<div class="space-y-10">
		{#each authors as author (author.slug)}
			<article id={author.slug} class="scroll-mt-24">
				<div class="flex items-center gap-4">
					<a href={localizeHref(`/authors/${author.slug}`)} class="shrink-0 hover:no-underline">
						{#if author.photo_url}
							<img
								src={author.photo_url}
								alt="Portrait of {author.name}"
								loading="lazy"
								class="h-14 w-14 rounded-full border border-border object-cover"
								style="filter: grayscale(1)"
							/>
						{:else}
							<span
								class="flex h-14 w-14 items-center justify-center rounded-full bg-accent-soft text-h3 font-semibold text-accent"
								style="font-family: var(--font-display)"
							>
								{initials(author.name)}
							</span>
						{/if}
					</a>
					<div>
						<h2 class="text-h2">
							<a href={localizeHref(`/authors/${author.slug}`)} class="!text-text hover:underline">{author.name}</a>
							{#if author.birth_year}
								<span class="ml-2 text-body font-normal text-muted"
									>{author.birth_year}–{author.death_year ?? ''}</span
								>
							{/if}
						</h2>
						<a href={localizeHref(`/authors/${author.slug}`)} class="text-small font-semibold text-accent">
							{#if author.book_count > 0}
								{author.book_count}
								{author.book_count === 1 ? t('bios.booksInLibraryOne') : t('bios.booksInLibraryMany')} →
							{:else}
								{t('bios.viewBiography')} →
							{/if}
						</a>
					</div>
				</div>
				<p class="mt-4 text-body leading-relaxed text-muted">{author.bio}</p>
			</article>
		{/each}
	</div>
</div>
