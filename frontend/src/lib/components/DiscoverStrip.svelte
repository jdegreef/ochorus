<script lang="ts">
	import type { CoverBook } from '$lib/library-public';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import BookCard from '$lib/components/BookCard.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';

	/**
	 * The "Discover your next book" six-book strip, shared by the logged-out home
	 * and the signed-in dashboard so the two can't drift. Hidden when empty, like
	 * the topics row: if the shelf failed to load (see the note in +page.ts) a
	 * bare heading over an empty grid reads as "Ochorus has no books", where
	 * showing nothing simply reads as a shorter page.
	 *
	 * On the signed-in dashboard it sits on the page's one night band (app.css,
	 * .night-band): six covers are the most colourful thing the page has, and
	 * they look their best on a dark ground. The band re-declares the theme
	 * tokens, so BookCard and the header draw in its night palette with no
	 * variant of their own; its heading wears the Books icon, like the
	 * dashboard's other shelves. The logged-out home asks for `band="none"`
	 * instead — one ground with sections parted by space, every heading there a
	 * plain start-aligned `<h2>` with no icon (design #17).
	 *
	 * `belowHero`: the logged-out home's hero fans out its own covers above
	 * this shelf, one of them fetched at high priority, and pushes the row well
	 * below the first screen — so here no cover is fetched high or eagerly.
	 */
	let {
		books,
		band = 'night',
		belowHero = false
	}: { books: CoverBook[]; band?: 'night' | 'none'; belowHero?: boolean } = $props();

	const t = i18n.t;
</script>

{#snippet shelf()}
	<section class="page-col px-5 pt-14">
		<SectionHeader
			section={band === 'night' ? 'books' : undefined}
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
		       desktop — one even row of six. (The first book used to be set
		                large, as a magazine leads with its pick; beside five
		                small tinted cards it read as a layout bug — design
		                review #1.) -->
		<div class="discover-rail">
			{#each books as book, i (book.slug)}
				<!-- The first row starts above the fold at every breakpoint; three
				     covers the common cases without eagerly loading a shelf
				     nobody has scrolled to. Only the first is fetched HIGH: it is
				     the likeliest LCP of an even row (none is, under the home hero:
				     `belowHero`) — on a phone the row starts
				     at the very foot of the first screen (y≈800 of 844,
				     measured), where three high fetches only raced the fonts. -->
				<BookCard {book} showAuthor priority={!belowHero && i === 0} eager={!belowHero && i < 3} />
			{/each}
		</div>
	</section>
{/snippet}

{#if books.length}
	{#if band === 'night'}
		<div class="night-band">{@render shelf()}</div>
	{:else}
		{@render shelf()}
	{/if}
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
			grid-template-columns: repeat(6, minmax(0, 1fr));
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
