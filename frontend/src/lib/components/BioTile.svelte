<script lang="ts">
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { formatLifespan, type AuthorBio } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { initials, portraitPosition, portraitSrcset } from '$lib/portraits';

	/**
	 * A writer as a portrait tile — the biographies grid view. AuthorBioCard is
	 * one writer per row with their bio and books, which is the right card for
	 * reading about people and a long scroll for finding one: 101 rows. The grid
	 * puts five faces in that space. Same hover as the row card (grayscale
	 * portrait warms to colour), same id for the A–Z jump and old #slug links.
	 */
	let { author }: { author: AuthorBio } = $props();
	const t = i18n.t;
	const works = $derived(author.book_count + author.sermon_count);
</script>

<a
	id={author.slug}
	href={localizeHref(`/authors/${author.slug}`)}
	data-sveltekit-preload-data="hover"
	style="scroll-margin-top: calc(var(--pinned-offset, 5rem) + 0.5rem)"
	class="card-tint group flex flex-col items-center gap-2 rounded-card border border-border px-3 pb-4 pt-5 text-center text-text hover:no-underline"
>
	{#if author.photo_url}
		{@const source = { src: author.photo_url, srcset: portraitSrcset(author.photo_url) }}
		<img
			src={source.src}
			srcset={source.srcset}
			use:hydrateSrc={source}
			sizes="96px"
			width="96"
			height="96"
			alt="{t('a11y.portraitOf')} {author.name}"
			loading="lazy"
			class="h-24 w-24 rounded-full border border-border object-cover grayscale transition-[filter] duration-[var(--duration-base)] group-hover:grayscale-0"
			style="object-position: {portraitPosition(author.slug)}"
		/>
	{:else}
		<span
			class="font-display flex h-24 w-24 items-center justify-center rounded-full bg-accent-soft text-h2 font-semibold text-accent"
		>
			{initials(author.name)}
		</span>
	{/if}
	<span class="font-display text-body font-semibold leading-snug group-hover:underline">{author.name}</span>
	{#if author.birth_year}
		<span class="whitespace-nowrap text-small text-muted"
			>{formatLifespan(author.birth_year, author.death_year, t('common.bornPrefix'))}</span
		>
	{/if}
	{#if works > 0}
		<span class="text-micro font-semibold text-accent">
			{#if author.book_count > 0}
				{author.book_count}
				{author.book_count === 1 ? t('common.bookOne') : t('common.bookMany')}
			{:else}
				{author.sermon_count}
				{author.sermon_count === 1 ? t('bios.sermonsOne') : t('bios.sermonsMany')}
			{/if}
		</span>
	{/if}
</a>
