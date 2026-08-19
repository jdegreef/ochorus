<script lang="ts">
	import type { SermonSummary } from '$lib/library';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { readingTime } from '$lib/reading';
	import Emblem from '$lib/components/Emblem.svelte';
	import { emblemForSermon } from '$lib/emblems';

	let { sermon, showAuthor = false }: { sermon: SermonSummary; showAuthor?: boolean } =
		$props();
	const t = i18n.t;
</script>

<a class="sermon-card" href={localizeHref(`/sermons/${sermon.slug}`)}>
	<span class="emblem emblem-chip"><Emblem name={emblemForSermon(sermon.slug)} /></span>
	<span class="min-w-0 flex-1">
		<span class="chip">{t('sermons.label')}</span>
		<span class="title">{sermon.title}</span>
		{#if showAuthor}
			<span class="author">{sermon.author.name}</span>
		{/if}
		<span class="meta">
			{#if sermon.scripture_ref}<span class="ref">{sermon.scripture_ref}</span>{/if}
			<span class="time">{readingTime(sermon.word_count)}</span>
		</span>
	</span>
</a>

<style>
	.sermon-card {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 0.85rem 1rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: var(--color-surface);
		transition: border-color 0.15s, background 0.15s;
	}
	.sermon-card:hover {
		border-color: var(--color-accent);
		background: var(--color-surface-2);
		text-decoration: none;
	}
	/* The sermon's emblem chip (recipe in app.css) — only size and hue here. */
	.emblem {
		--chip-size: 2.75rem;
		--chip-hue: var(--color-accent);
	}
	.chip {
		display: inline-block;
		font-size: 0.62rem;
		font-weight: 600;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--color-accent);
	}
	.title {
		display: block;
		font-weight: 600;
		line-height: 1.3;
		color: var(--color-text);
	}
	.author {
		display: block;
		font-size: 0.85rem;
		color: var(--color-muted);
		margin-top: 0.1rem;
	}
	.meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 0.6rem;
		margin-top: 0.35rem;
		font-size: 0.78rem;
		color: var(--color-muted);
	}
	.ref {
		color: var(--color-accent);
	}
</style>
