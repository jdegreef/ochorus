<script lang="ts">
	import type { BookSummary } from '$lib/library-public';
	import {
		canonReading,
		canonStrip,
		divisionKey,
		spineLabel,
		testamentKey,
		type BiblePlace
	} from '$lib/bible';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { scrollEdges } from '$lib/actions/scrollEdges';

	/**
	 * The /bible hub's canon strip: all 66 books as a shelf of slim spines, one
	 * row per testament, grouped by division, each linking to its book. Pure
	 * CSS — no cover images, so 66 books cost no requests: a spine wears its
	 * book's `cover_color` and is as thick as the book is long (`weight`). A
	 * book the language lacks keeps its place as a pale, unlinked outline, so
	 * the canon's shape stays whole however much of it has shipped.
	 *
	 * The spine names are the canon's short English names (`CANON`, via
	 * `canonStrip`): the hub is drawn only in BIBLE_LOCALES, English today.
	 * On a phone each row scrolls sideways, snapping to a division.
	 *
	 * A spine's two kinds of length both show: its thickness is the book's
	 * words, its height its chapters (`tall`), so Psalms stands tallest and
	 * Obadiah stays a sliver. A thin spine shows the book's abbreviation, set
	 * whole (`spineLabel`). Where the reader has read (`placeOf`, the page's
	 * own reading of their progress): a finished book carries a tick, a book
	 * under way fills from the shelf up as far as they have read, and a line
	 * above counts them. Nothing personal before mount — the prerender and a
	 * first visit draw the plain shelf.
	 */
	let {
		books,
		placeOf
	}: { books: readonly BookSummary[]; placeOf?: (book: BookSummary) => BiblePlace | null } = $props();
	const t = i18n.t;
	const testaments = $derived(canonStrip(books));
	const reading = $derived(placeOf ? canonReading(books, placeOf) : null);
	/** A spine's reading: finished, or the share of its chapters behind the reader. */
	function readOf(book: BookSummary, chapters: number): { done: boolean; fill: number } | null {
		const place = placeOf?.(book);
		if (!place) return null;
		if (place.finished) return { done: true, fill: 1 };
		return place.behind > 0 && chapters ? { done: false, fill: place.behind / chapters } : null;
	}
</script>

<nav class="canon" aria-label={t('bible.canonLabel')}>
	{#if reading && (reading.finished || reading.started)}
		<!-- The reader's Bible at a glance: what the ticks and fills below add up to. -->
		<div class="canon-meter">
			<span class="font-display font-semibold"
				>{t('bible.canonRead').replace('%n%', String(reading.finished)).replace('%total%', String(reading.total))}</span
			>
			{#if reading.started}
				<span class="text-small text-muted">{t('bible.canonUnderWay').replace('%n%', String(reading.started))}</span>
			{/if}
			<span class="canon-bar" aria-hidden="true"
				><i style:width="{(reading.finished / Math.max(1, reading.total)) * 100}%"></i></span
			>
		</div>
	{/if}
	{#each testaments as testament (testament.testament)}
		<div class="canon-row">
			<p class="canon-testament eyebrow-micro text-muted">{t(testamentKey(testament.testament))}</p>
			<ol class="canon-shelf cover-rail" use:scrollEdges>
				{#each testament.divisions as group (group.division.id)}
					<li class="canon-division">
						<ol class="canon-spines" aria-label={t(divisionKey(group.division.id))}>
							{#each group.slots as slot (slot.position)}
								<!-- An absent book has nothing to open, so nothing to announce:
								     a screen reader hears the books that are here. -->
								<li aria-hidden={slot.book ? undefined : 'true'}>
									{#if slot.book}
										{@const read = readOf(slot.book, slot.chapters)}
										<a
											class="spine"
											class:done={read?.done}
											href={localizeHref(`/books/${slot.book.slug}`)}
											title={slot.book.title}
											aria-label={read?.done
												? `${slot.book.title} · ${t('bible.canonFinished')}`
												: slot.book.title}
											style:--spine-w={slot.weight}
											style:--spine-t={slot.tall}
											style:--spine-c={slot.book.cover_color || null}
											>{#if read && !read.done}<span class="spine-fill" style:height="{read.fill * 100}%"
												></span>{/if}<span class="spine-name">{spineLabel(slot)}</span></a
										>
									{:else}
										<span class="spine absent" title={slot.name}><span class="spine-name">{slot.abbr}</span></span>
									{/if}
								</li>
							{/each}
						</ol>
						<!-- A one-book division (Acts, Revelation) is named by its spine.
						     Visual only: the list's aria-label names it for a screen reader. -->
						{#if group.slots.length > 1}
							<span class="canon-label" aria-hidden="true">{t(divisionKey(group.division.id))}</span>
						{:else}
							<!-- An empty label's height, so its spine stands on the row's one
							     shelf line (the row aligns to the bottom). -->
							<span class="canon-label" aria-hidden="true">&nbsp;</span>
						{/if}
					</li>
				{/each}
			</ol>
		</div>
	{/each}
</nav>

<style>
	.canon {
		margin-bottom: 3rem;
	}
	.canon-row + .canon-row {
		margin-top: 1.25rem;
	}
	.canon-testament {
		margin-bottom: 0.5rem;
	}
	.canon-shelf {
		display: flex;
		/* One shelf line for the whole row: spines are as tall as their book's
		   chapters, so each division is a different height, and its label sits
		   under the line. */
		align-items: flex-end;
		gap: 0.75rem;
		/* Room for a spine's hover rise inside the scroller's clip. */
		padding-top: 0.375rem;
		padding-bottom: 0.25rem;
		scroll-snap-type: x proximity;
		scroll-padding-inline: 0;
	}
	.canon-division {
		display: flex;
		flex-direction: column;
		flex-shrink: 0;
		scroll-snap-align: start;
	}
	.canon-spines {
		display: flex;
		align-items: flex-end;
		gap: 2px;
		/* The shelf the spines stand on. */
		border-bottom: 1px solid var(--border-strong);
		padding-bottom: 1px;
	}
	.canon-label {
		margin-top: 0.375rem;
		font-size: var(--fs-micro);
		line-height: 1.3;
		color: var(--muted);
		white-space: nowrap;
	}
	.spine {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		box-sizing: border-box;
		/* 17px for the shortest book, 35px for the longest: both testaments
		   fit a desktop column, and scroll on anything narrower. */
		width: calc(1.0625rem + var(--spine-w, 0) * 1.125rem);
		/* Chapters set the height (`tall`): 5rem for one, 8.5rem for Psalms'
		   150. The spines stand on one shelf line, so only the tops vary. */
		height: calc(5rem + var(--spine-t, 0.4) * 3.5rem);
		/* Physical sides: in vertical writing, padding-block is left and right,
		   and would floor every spine's width at the padding. */
		padding: 0.9rem 0;
		writing-mode: vertical-rl;
		border-radius: 2px 2px 1px 1px;
		/* hex-ok: a cover colour, not a theme colour — the book's own cloth, dark in both themes */
		background: var(--spine-c, #4a3a2a);
		/* A little roundness; the gilt bands are the ::before / ::after rules,
		   at the very ends, clear of the name. */
		background-image: linear-gradient(to right, rgb(255 255 255 / 0.1), transparent 40%, rgb(0 0 0 / 0.18));
		/* hex-ok: light ink on that dark cloth, as a cover sets its title */
		color: #f3ead9;
		/* The interface face, upright weight: a name read sideways at this size
		   needs the sans's open shapes more than the serif's character. */
		font-family: var(--font-sans);
		font-size: var(--fs-eyebrow);
		font-weight: 600;
		letter-spacing: 0.02em;
		line-height: 1;
		white-space: nowrap;
		overflow: hidden;
		text-decoration: none;
		transition: transform 0.15s ease;
	}
	.spine::before,
	.spine::after {
		content: '';
		position: absolute;
		/* Across the spine: in its vertical writing the block axis is the
		   horizontal one (inset-inline would run top to bottom). */
		inset-block: 0 0;
		height: 1px;
		background: rgb(224 180 92 / 0.6);
	}
	.spine::before {
		top: 0.45rem;
	}
	.spine::after {
		bottom: 0.45rem;
	}
	.spine-name {
		position: relative;
	}
	/* A book under way: lighter cloth from the shelf up, as far as the reader
	   has read, under a gilt line. */
	.spine-fill {
		position: absolute;
		/* Across the spine: in its vertical writing the block axis is the
		   horizontal one (inset-inline would run top to bottom). */
		inset-block: 0 0;
		bottom: 0;
		background: rgb(255 255 255 / 0.2);
		border-top: 1px solid rgb(224 180 92 / 0.85);
	}
	/* A finished book: a gilt tick at its foot, set upright. */
	.spine.done::after {
		content: '✓';
		height: auto;
		bottom: 0.3rem;
		background: none;
		writing-mode: horizontal-tb;
		text-align: center;
		font-size: var(--fs-micro);
		line-height: 1;
		color: rgb(240 200 110);
	}
	.spine.done {
		padding-bottom: 1.3rem;
	}
	/* The reader's count over the strip, and a bar of the canon read. */
	.canon-meter {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.35rem 0.9rem;
		margin-bottom: 1rem;
	}
	.canon-bar {
		flex: 1 1 12rem;
		max-width: 22rem;
		height: 6px;
		border-radius: var(--radius-pill);
		background: var(--border);
		overflow: hidden;
	}
	.canon-bar i {
		display: block;
		height: 100%;
		background: var(--accent);
	}
	a.spine:hover,
	a.spine:focus-visible {
		transform: translateY(-0.375rem);
	}
	a.spine:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}
	.spine.absent {
		width: 1.0625rem;
		height: 6rem;
		background: none;
		border: 1px dashed var(--border-strong);
		color: var(--muted);
		opacity: 0.6;
	}
	.spine.absent::before,
	.spine.absent::after {
		display: none;
	}
	@media (prefers-reduced-motion: reduce) {
		.spine {
			transition: none;
		}
	}
</style>
