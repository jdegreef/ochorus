<script lang="ts">
	import type { BibleBookLinks } from '$lib/library-public';
	import { localizeHref } from '$lib/href';

	/**
	 * Where a book of the Bible leads in the rest of the library, as one line:
	 * its sermons (the sermons shelf filtered to it) and the classics' passages
	 * on it (`/scripture/<book>/`). Draws nothing when it has neither. English,
	 * like the /bible hub's other own copy.
	 */
	let { links, class: cls = '' }: { links: BibleBookLinks | undefined; class?: string } = $props();
</script>

{#if links && (links.sermons || links.scripture)}
	<p class="bible-more {cls}">
		{#if links.sermons}
			<a href={localizeHref(`/sermons?book=${encodeURIComponent(links.sermon_book)}`)}
				>{links.sermons} {links.sermons === 1 ? 'sermon' : 'sermons'}</a
			>
		{/if}
		{#if links.sermons && links.scripture}<span class="sep" aria-hidden="true"> · </span>{/if}
		{#if links.scripture}
			<a href={localizeHref(`/scripture/${links.scripture}/`)}>In the classics</a>
		{/if}
	</p>
{/if}

<style>
	.bible-more {
		margin: 0;
		font-size: var(--fs-small);
	}
	.bible-more a {
		color: var(--accent);
	}
	.bible-more a:hover {
		text-decoration: underline;
	}
</style>
