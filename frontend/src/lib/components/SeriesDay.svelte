<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { numeral, volumeLabel } from '$lib/series';
	import { readingTime } from '$lib/reading';
	import type { SampleDay, SeriesBook } from '$lib/library-public';

	/**
	 * A daily devotional's month (Rooted, Daughters of the King): one real day
	 * of Book 1 split into the parts every day has — the verse, the teaching,
	 * the prompts, the prayer — so a parent sees what a day asks of a child,
	 * then the days of the volume the reader is in as dots that fill as they
	 * are read, with the next day one tap away.
	 *
	 * `read` and `next` are null until mount (progress is localStorage, and the
	 * prerendered page must not bake one visitor's month into every copy): the
	 * dots draw empty and the button opens Day 1.
	 */
	let {
		sample,
		days,
		book,
		firstSlug,
		lang,
		read,
		next
	}: {
		sample: SampleDay | null;
		days: number;
		book: SeriesBook;
		firstSlug: string;
		lang: string;
		read: number;
		next: number;
	} = $props();
	const t = i18n.t;
	const nextTitle = $derived(book.toc?.[next] ?? '');
	const dayLabel = (n: number) => `${t('plans.day')} ${numeral(n, lang)}`;
</script>

{#if sample}
	<section class="mt-12">
		<h2 class="section-label mb-4">{t('series.dayHeading')}</h2>
		<article class="day" {lang}>
			<header class="day-head">
				<h3 class="day-title" dir="auto">{sample.title}</h3>
				{#if sample.words}<p class="day-time">{readingTime(sample.words)}</p>{/if}
			</header>
			<div class="day-part">
				<p class="day-label">{t('series.dayVerse')}</p>
				<blockquote class="day-verse" dir="auto">
					<p>{sample.verse.text}</p>
					<cite>{sample.verse.ref}</cite>
				</blockquote>
			</div>
			<div class="day-part">
				<p class="day-label">{t('series.dayTeaching')}</p>
				<p class="day-teaching" dir="auto">{sample.teaching}</p>
			</div>
			{#each sample.prompts as prompt (prompt.label)}
				<div class="day-part">
					<p class="day-label" dir="auto">{prompt.label}</p>
					<p dir="auto">{prompt.text}</p>
				</div>
			{/each}
			<div class="day-part">
				<p class="day-label">{t('series.dayPray')}</p>
				<p class="day-prayer" dir="auto">{sample.prayer}</p>
			</div>
			<footer class="day-foot">
				<a href={localizeHref(`/books/${firstSlug}/${sample.order}`)} class="btn btn-primary">
					{t('series.keepReading')}
				</a>
			</footer>
		</article>
	</section>
{/if}

<section class="mt-12">
	<h2 class="section-label mb-2">
		{t('series.daysHeading').replace('%n%', numeral(days, lang))}
		{#if book.series_position}<span class="text-muted"> · {volumeLabel(book.series_position, lang)}</span>{/if}
	</h2>
	<p class="mb-4 text-small text-muted">
		{t('series.daysRead').replace('%n%', numeral(read, lang)).replace('%total%', numeral(days, lang))}
	</p>
	<ol class="dots" aria-label={t('series.daysHeading').replace('%n%', numeral(days, lang))}>
		{#each Array.from({ length: days }, (_, i) => i + 1) as d (d)}
			<li>
				<a
					href={localizeHref(`/books/${book.slug}/${d + 1}`)}
					class="dot"
					class:read={d <= read}
					class:next={d === next && read < days}
					title={book.toc?.[d] || dayLabel(d)}
					aria-label={dayLabel(d)}
				>
					{numeral(d, lang)}
				</a>
			</li>
		{/each}
	</ol>
	<a href={localizeHref(`/books/${book.slug}/${next + 1}`)} class="btn btn-primary mt-4">
		<!-- The day's own title ("Day 8 — The Sister Nobody Noticed") already
		     names it; the bare "Day 8" only where the list is missing. -->
		<span dir="auto">{nextTitle || dayLabel(next)}</span>
	</a>
</section>

<style>
	.day {
		display: grid;
		gap: 1.125rem;
		padding: 1.5rem 1.75rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		max-width: 46rem;
	}
	.day-head {
		display: grid;
		gap: 0.125rem;
	}
	.day-title {
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		font-weight: 600;
		line-height: 1.25;
		margin: 0;
	}
	.day-time {
		color: var(--muted);
		font-size: var(--fs-small);
		margin: 0;
	}
	.day-part {
		display: grid;
		gap: 0.25rem;
		padding-inline-start: 0.875rem;
		border-inline-start: 3px solid color-mix(in srgb, var(--series-accent, var(--accent)) 45%, transparent);
	}
	.day-part p {
		margin: 0;
	}
	.day-label {
		font-size: var(--fs-eyebrow);
		font-weight: 700;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--muted);
	}
	.day-verse {
		margin: 0;
		font-family: var(--font-display);
		font-size: var(--fs-body);
		line-height: 1.6;
	}
	.day-verse cite {
		display: block;
		margin-top: 0.25rem;
		font-family: var(--font-sans);
		font-style: normal;
		font-size: var(--fs-small);
		color: var(--muted);
	}
	.day-teaching {
		line-height: 1.65;
	}
	.day-prayer {
		font-family: var(--font-display);
		font-style: italic;
		line-height: 1.6;
	}
	.day-foot {
		display: flex;
		justify-content: flex-end;
	}
	.dots {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(2.25rem, 1fr));
		gap: 0.375rem;
		max-width: 30rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.dot {
		display: grid;
		place-items: center;
		aspect-ratio: 1;
		border-radius: var(--radius-pill);
		border: 1px solid var(--border);
		font-size: var(--fs-eyebrow);
		font-variant-numeric: tabular-nums;
		color: var(--muted);
		text-decoration: none;
	}
	.dot.read {
		background: var(--series-accent, var(--accent));
		border-color: var(--series-accent, var(--accent));
		color: var(--surface);
	}
	.dot.next {
		border: 2px solid var(--series-accent, var(--accent));
		color: var(--text);
		font-weight: 700;
	}
	.dot:hover {
		border-color: var(--series-accent, var(--accent));
	}
	@media (max-width: 639.98px) {
		.day {
			padding: 1.125rem 1rem;
		}
	}
</style>
