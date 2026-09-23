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
	 */
	let { books }: { books: CoverBook[] } = $props();

	const t = i18n.t;
</script>

{#if books.length}
	<section class="page-col px-5 pt-14">
		<SectionHeader
			title={t('home.discoverNext')}
			href={localizeHref('/books')}
			linkText={t('home.allBooks')}
		/>
		<!-- Its own ramp rather than .book-grid: this strip is exactly six books,
		     and .book-grid's open-shelf ramp passes through five columns, which
		     would leave a lone sixth card on a second row. 2 / 3 / 6 all divide
		     six. -->
		<div class="grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 lg:grid-cols-6">
			{#each books as book, i (book.slug)}
				<!-- The first row is above the fold at every breakpoint (2 up on
				     mobile, 6 up on desktop); three covers the common cases
				     without eagerly loading a shelf nobody has scrolled to. -->
				<BookCard {book} showAuthor priority={i < 3} />
			{/each}
		</div>
	</section>
{/if}
