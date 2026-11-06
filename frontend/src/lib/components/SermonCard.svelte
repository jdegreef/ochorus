<script lang="ts">
	import type { SermonSummary } from '$lib/library-public';
	import { localizeHref } from '$lib/href';
	import { readingTime } from '$lib/reading';

	/**
	 * A sermon on a SHELF — the one row for "here is a sermon, go read it".
	 *
	 * Not every mention of a sermon: the resume tile in Continue reading is a
	 * progress row, Sermon of the day is a feature panel, and prev/next on a
	 * sermon page is navigation. Those are different jobs. This is the one that
	 * lists sermons to choose between — on the sermons index, a topic, an
	 * author's page, favourites and the 404 picks alike, so a sermon looks the
	 * same wherever it is listed (one reading-time figure: the shared
	 * `readingTime()`, never a page's own `word_count / 200`).
	 *
	 * A plain list row (design review #8): the title in the serif, ONE muted
	 * meta line — preacher · passage · length — and one clamped line of the
	 * "In brief". Hairlines between rows come from the list wrapper
	 * (`.sermon-list`, below). The whole row is the link; there is nothing else
	 * to click. It replaced a bordered card with an era rail, a passage
	 * monogram, the passage again in capitals, a dotted leader and a chevron
	 * that expanded the brief in place — the full brief now lives only on the
	 * sermon's own page ("In brief"), one tap away, which is where a reader who
	 * wants more than a line is going anyway.
	 *
	 * Put rows inside an element with class `sermon-list` (app.css: the measure
	 * and the first row's missing hairline).
	 */
	let {
		sermon,
		showAuthor = false
	}: {
		sermon: SermonSummary;
		/** Name the preacher. Off where a heading already does (an author page,
		 *  the index grouped by preacher). */
		showAuthor?: boolean;
	} = $props();
	// The link is named by its title and described by the meta line only; the
	// brief stays out of both, so a links list or rotor reads the title, not a
	// 400-character paragraph (the clamp only hides it visually).
	const uid = $props.id();
</script>

<a
	class="sermon-row"
	href={localizeHref(`/sermons/${sermon.slug}`)}
	aria-labelledby="{uid}-t"
	aria-describedby="{uid}-m"
>
	<!-- The <h3> keeps the title's heading semantics under the page's h2s. -->
	<h3 id="{uid}-t" class="sermon-row-title">{sermon.title}</h3>
	<!-- Spaces are explicit ({' '}) around each dot, so the gap is even and a
	     screen reader's description still separates the segments. -->
	<span id="{uid}-m" class="sermon-row-meta"
		>{#if showAuthor}<span>{sermon.author.name}</span>{' '}<span class="sep" aria-hidden="true">·</span>{' '}{/if}{#if sermon.scripture_ref}<span
				>{sermon.scripture_ref}</span
			>{' '}<span class="sep" aria-hidden="true">·</span>{' '}{/if}<span class="whitespace-nowrap"
			>{readingTime(sermon.word_count)}</span
		></span
	>
	{#if sermon.summary}
		<span class="sermon-row-brief line-clamp-1">{sermon.summary}</span>
	{/if}
</a>

<style>
	.sermon-row {
		display: block;
		padding-block: 0.75rem;
		border-block-start: 1px solid var(--border);
		color: var(--text);
		text-decoration: none;
	}
	.sermon-row-title {
		margin: 0;
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		font-weight: 600;
		line-height: 1.3;
		color: var(--text);
		text-wrap: balance;
		transition: color var(--duration-fast);
	}
	.sermon-row:hover .sermon-row-title {
		color: var(--accent);
		text-decoration: underline;
		text-underline-offset: 0.15em;
		text-decoration-thickness: 1px;
	}
	.sermon-row:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
		border-radius: var(--radius-sm);
	}
	.sermon-row-meta {
		display: block;
		margin-block-start: 0.15rem;
		font-size: var(--fs-small);
		color: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	.sermon-row-brief {
		/* line-clamp-1 sets display: -webkit-box; it stays a block of its own. */
		margin-block-start: 0.2rem;
		max-width: 64ch;
		font-size: var(--fs-small);
		color: var(--muted);
	}
</style>
