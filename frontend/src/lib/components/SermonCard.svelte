<script lang="ts">
	import type { SermonSummary } from '$lib/library';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { readingTime, preachedYear } from '$lib/reading';
	import Emblem from '$lib/components/Emblem.svelte';
	import { emblemForSermon } from '$lib/emblems';
	import { hueForBirthYear } from '$lib/eras';

	/**
	 * A sermon on a SHELF — the one card for "here is a sermon, go read it".
	 *
	 * Not every mention of a sermon: the resume tile in Continue reading is a
	 * progress row, Sermon of the week is a feature panel, and prev/next on a
	 * sermon page is navigation. Those are different jobs. This is the one that
	 * lists sermons to choose between.
	 *
	 * There were three: this card (topics), a `sermonRow` snippet living inside
	 * the sermons index, and a hand-rolled list on the author page that computed
	 * its own reading time with `Math.round(word_count / 200)` rather than the
	 * shared `readingTime()`. The same sermon therefore had three different
	 * lengths of metadata and, on the author page, a length that could disagree
	 * with the one on its own page.
	 *
	 * Two variants, the same pair Books already has (`BookCard` / `BookListRow`):
	 *
	 *   - `card` — compact, for a grid beside other content (a topic's sermons,
	 *     an author's sermons).
	 *   - `row` — full width, with the era rail, the era-tinted emblem and the
	 *     brief, for the sermons index where sermons ARE the content.
	 *
	 * `.sermon-row*` is styled globally in app.css; only `card` carries scoped
	 * styles here.
	 */
	let {
		sermon,
		showAuthor = false,
		variant = 'card'
	}: {
		sermon: SermonSummary;
		/** Name the preacher. The index turns this off when a heading already does. */
		showAuthor?: boolean;
		variant?: 'card' | 'row';
	} = $props();
	const t = i18n.t;
	/** Empty for a sermon with no recorded date — the row drops the "· 1857". */
	const year = $derived(preachedYear(sermon.preached_on));
</script>

{#if variant === 'row'}
	<a
		class="sermon-row group"
		style="--row-hue: {hueForBirthYear(sermon.author.birth_year)}"
		href={localizeHref(`/sermons/${sermon.slug}`)}
	>
		<!-- Every sermon wears its own illustrated emblem, themed to the text it
		     expounds — the raven with bread, the bruised reed, the golden key — so
		     a shelf of prose rows gets a scannable visual anchor. -->
		<div class="sermon-row-emblem emblem-chip">
			<Emblem name={emblemForSermon(sermon.slug)} />
		</div>
		<div class="min-w-0 flex-1">
			<!-- Eyebrow line: whose sermon (only when no heading above says so) and
			     the passage at the start, the length at the top right of the row. -->
			<div class="flex flex-wrap items-baseline justify-between gap-x-4">
				<p class="sermon-row-ref min-w-0">
					{#if showAuthor}{sermon.author.name}<span class="opacity-40"> · </span>{/if}
					{sermon.scripture_ref}
				</p>
				<!-- ms-auto, not just justify-between: when a long passage pushes this
				     to its own line, justify-between leaves it stranded at the start of
				     that line. The auto margin keeps it flush to the end either way. -->
				<p class="ms-auto shrink-0 text-small text-muted">
					{readingTime(sermon.word_count)}
					{#if year}<span class="opacity-50"> · </span>{year}{/if}
				</p>
			</div>
			<h3 class="sermon-row-title mt-1">{sermon.title}</h3>
			<!-- Not every sermon has a brief written yet, so the row has to read as
			     finished without one — hence the brief hanging below a complete
			     title/passage/length line rather than sitting between them. -->
			{#if sermon.summary}
				<!-- Clamped on a phone only: a 400-character brief runs to eleven lines
				     at 375px, and twenty-six of those is a very long shelf. The full
				     text is one tap away, and it fits in three or four lines from sm up
				     where the measure is wider. Same rule AuthorBioCard uses. -->
				<p class="sermon-row-brief mt-2.5 line-clamp-5 text-body sm:line-clamp-none">
					{sermon.summary}
				</p>
			{/if}
		</div>
	</a>
{:else}
	<a class="sermon-card" href={localizeHref(`/sermons/${sermon.slug}`)}>
		<span class="emblem emblem-chip"><Emblem name={emblemForSermon(sermon.slug)} /></span>
		<span class="min-w-0 flex-1">
			<span class="eyebrow sermon-label">{t('sermons.label')}</span>
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
{/if}

<style>
	.sermon-card {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 0.85rem 1rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: var(--color-surface);
		transition:
			border-color var(--duration-fast),
			background var(--duration-fast);
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
	.sermon-label {
		display: inline-block;
		font-size: var(--fs-micro);
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
		font-size: var(--fs-small);
		color: var(--color-muted);
		margin-top: 0.1rem;
	}
	.meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 0.6rem;
		margin-top: 0.35rem;
		font-size: var(--fs-small);
		color: var(--color-muted);
	}
	.ref {
		color: var(--color-accent);
	}
</style>
