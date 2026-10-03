<script lang="ts">
	import type { AuthorTileData } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import Portrait from '$lib/components/Portrait.svelte';

	/**
	 * A compact author card — grayscale portrait (or initials fallback) beside
	 * the name and book count (stacked above them on a phone), linking to the
	 * author page. Shared by the logged-out home's author roster and the "My
	 * Library" following section, which had grown identical inline copies.
	 */
	let { author }: { author: AuthorTileData } = $props();
	const t = i18n.t;
</script>

<a
	href={localizeHref(`/authors/${author.slug}`)}
	class="card-tint flex flex-col items-center gap-2 rounded-card border border-border p-4 text-center sm:flex-row sm:gap-3 sm:text-start"
>
	<Portrait
		slug={author.slug}
		name={author.name}
		url={author.photo_url}
		px={44}
		class="h-11 w-11"
	/>
	<span class="min-w-0">
		<!-- Two lines on a phone, where the tile is ~150px wide: truncating to one
		     cut "Andrew Murray" to "Andre…". -->
		<span class="line-clamp-2 text-small font-semibold text-text sm:block sm:truncate">{author.name}</span>
		{#if author.book_count}
			<span class="block text-small text-muted">
				{author.book_count}
				{author.book_count === 1 ? t('common.bookOne') : t('common.bookMany')}
			</span>
		{/if}
	</span>
</a>
