<script lang="ts">
	import type { BookSummary } from '$lib/library-public';
	import { bibleChapters, type BiblePlace } from '$lib/bible';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/href';

	/**
	 * What an opened book shows on the /bible hub, in either view: its short
	 * house overview (`intro`, from /bible/links/), then its chapters as the
	 * book page's chips (`.chapter-grid` in app.css) — filled behind the reader
	 * and ringed where Continue would open (`place`, after mount), as on the
	 * book page. Built only while open: 1,189 chips on every load would bloat
	 * the prerendered page, and the book pages already link each chapter.
	 */
	let {
		book,
		place = null,
		intro = ''
	}: { book: BookSummary; place?: BiblePlace | null; intro?: string } = $props();
	const t = i18n.t;
	const lang = getLang();
</script>

{#if intro}<p class="chapter-panel-intro">{intro}</p>{/if}
<ol class="chapter-grid">
	{#each bibleChapters(book, lang) as ch (ch.n)}
		{@const current = !place?.finished && ch.n === place?.current}
		{@const read = !current && ch.n <= (place?.behind ?? 0)}
		<li>
			<a
				class="chapter-chip"
				class:read
				class:current
				href={localizeHref(ch.href)}
				aria-current={current ? 'step' : undefined}
				aria-label="{ch.name}{read ? `, ${t('settings.heatmapRead')}` : ''}"
				title={ch.name}>{ch.n}</a
			>
		</li>
	{/each}
</ol>

<style>
	.chapter-panel-intro {
		max-width: 65ch;
		margin: 0 0 0.75rem;
		font-size: var(--fs-small);
		line-height: 1.55;
		color: var(--muted);
	}
</style>
