<script lang="ts">
	import type { CoverBook } from '$lib/library-public';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import BookCard from '$lib/components/BookCard.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';

	/**
	 * The "Discover Your Next Book" six-book strip, shared by the logged-out home
	 * and the signed-in dashboard so the two can't drift. Hidden when empty, like
	 * the topics row: if the shelf failed to load (see the note in +page.ts) a
	 * bare heading over an empty grid reads as "Ochorus has no books", where
	 * showing nothing simply reads as a shorter page.
	 *
	 * It sits on the home page's one night band (app.css, .night-band): six
	 * covers are the most colourful thing the page has, and they look their best
	 * on a dark ground. The band re-declares the theme tokens, so BookCard and
	 * the header draw in its night palette with no variant of their own.
	 */
	let { books }: { books: CoverBook[] } = $props();

	const t = i18n.t;
</script>

{#if books.length}
	<div class="night-band">
		<section class="page-col px-5 pt-14">
			<SectionHeader
				title={t('home.discoverNext')}
				href={localizeHref('/books')}
				linkText={t('home.allBooks')}
			/>
			<!-- Its own layout rather than .book-grid (whose open-shelf ramp passes
			     through five columns and would strand a sixth card):
			       phone  — a rail that scrolls sideways, the third cover peeking
			                at the edge so it reads as "there is more this way"
			                rather than a tall stack of six;
			       tablet — three across, two rows;
			       desktop — one row with the first book set large, as a
			                magazine leads with its pick, the rest standing
			                bottom-aligned beside it. -->
			<div class="discover-rail">
				{#each books as book, i (book.slug)}
					<!-- The first row is above the fold at every breakpoint; three
					     covers the common cases without eagerly loading a shelf
					     nobody has scrolled to. -->
					<BookCard {book} showAuthor priority={i < 3} />
				{/each}
			</div>
		</section>
	</div>
{/if}

<style>
	.discover-rail {
		display: grid;
		grid-auto-flow: column;
		grid-auto-columns: 42%;
		gap: 1rem;
		/* Bleed to the screen edge so a card slides off it, not off the
		   column's padding; the padding brings the first card back in line. */
		margin-inline: -1.25rem;
		padding-inline: 1.25rem;
		scroll-padding-inline: 1.25rem;
		/* Room for the cards' hover lift and shadow inside the scroller. */
		padding-block: 0.25rem 0.75rem;
		overflow-x: auto;
		scroll-snap-type: x mandatory;
		scrollbar-width: none;
	}
	.discover-rail::-webkit-scrollbar {
		display: none;
	}
	.discover-rail > :global(*) {
		scroll-snap-align: start;
	}
	@media (min-width: 640px) {
		.discover-rail {
			grid-auto-flow: row;
			grid-template-columns: repeat(3, minmax(0, 1fr));
			row-gap: 1.5rem;
			margin-inline: 0;
			padding-inline: 0;
			padding-block: 0;
			overflow: visible;
		}
	}
	@media (min-width: 1024px) {
		.discover-rail {
			grid-template-columns: minmax(0, 1.75fr) repeat(5, minmax(0, 1fr));
			align-items: end;
		}
		/* .book-card fills its cell (height: 100%) to level a grid row; here
		   the row is the lead's height, so the others keep their own and stand
		   on the baseline beside it. */
		.discover-rail > :global(*) {
			height: auto;
		}
	}
	/* Print lays the six out flat rather than as a clipped rail. */
	@media print {
		.discover-rail {
			grid-auto-flow: row;
			grid-template-columns: repeat(3, minmax(0, 1fr));
			margin-inline: 0;
			padding-inline: 0;
			overflow: visible;
		}
	}
</style>
