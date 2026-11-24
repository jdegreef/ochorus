<script lang="ts">
	import type { BibleBookLinks } from '$lib/library-public';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { bibleText } from '$lib/bibleLocales';

	/**
	 * Where a book of the Bible leads in the rest of the library, as one line:
	 * its sermons (the sermons shelf filtered to it) and the classics' passages
	 * on it (`/scripture/<book>/`). Draws nothing when it has neither. The
	 * API sends the classics' page in English alone (the scripture pages are
	 * English only), so only English ever draws that link.
	 */
	let { links, class: cls = '' }: { links: BibleBookLinks | undefined; class?: string } = $props();
	const IN_CLASSICS = { en: 'In the classics', es: 'En los clásicos' };
	const lang = getLang();
</script>

{#if links && (links.sermons || links.scripture)}
	<p class="bible-more {cls}">
		{#if links.sermons}
			<a href={localizeHref(`/sermons?book=${encodeURIComponent(links.sermon_book)}`)}>
				{links.sermons}
				{i18n.tn(links.sermons, 'common.sermonOne', 'common.sermonMany')}
			</a>
		{/if}
		{#if links.sermons && links.scripture}<span class="sep" aria-hidden="true"> · </span>{/if}
		{#if links.scripture}
			<a href={localizeHref(`/scripture/${links.scripture}/`)}>{bibleText(IN_CLASSICS, lang)}</a>
		{/if}
	</p>
{/if}

<style>
	/* No margin of its own: each caller spaces it (the list row, the panel). */
	.bible-more {
		font-size: var(--fs-small);
	}
	.bible-more a {
		color: var(--accent);
	}
	.bible-more a:hover {
		text-decoration: underline;
	}
</style>
