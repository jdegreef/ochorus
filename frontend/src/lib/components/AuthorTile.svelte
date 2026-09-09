<script lang="ts">
	import type { AuthorBio } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { portraitPosition } from '$lib/portraits';
	import { initials } from '$lib/strings';

	/**
	 * A compact author card — grayscale portrait (or initials fallback) beside
	 * the name and book count, linking to the author page. Shared by the
	 * logged-out home's author roster and the "My Library" following section,
	 * which had grown identical inline copies.
	 */
	let { author }: { author: AuthorBio } = $props();
	const t = i18n.t;
</script>

<a
	href={localizeHref(`/authors/${author.slug}`)}
	class="card-tint flex items-center gap-3 rounded-card border border-border p-4"
>
	{#if author.photo_url}
		<img
			src={author.photo_url}
			alt="{t('a11y.portraitOf')} {author.name}"
			loading="lazy"
			class="h-11 w-11 shrink-0 rounded-full border border-border object-cover"
			style="filter: grayscale(1); object-position: {portraitPosition(author.slug)}"
		/>
	{:else}
		<span
			class="font-display flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-accent-soft text-small font-semibold text-accent"
		>
			{initials(author.name)}
		</span>
	{/if}
	<span class="min-w-0">
		<span class="block truncate text-small font-semibold text-text">{author.name}</span>
		{#if author.book_count}
			<span class="block text-small text-muted">
				{author.book_count}
				{author.book_count === 1 ? t('common.bookOne') : t('common.bookMany')}
			</span>
		{/if}
	</span>
</a>
