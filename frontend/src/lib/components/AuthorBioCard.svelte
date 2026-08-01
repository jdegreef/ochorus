<script lang="ts">
	import { type AuthorBio, type BookSummary, formatLifespan } from '$lib/library';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import BookCover from '$lib/components/BookCover.svelte';

	// One writer's card: portrait, name + lifespan, the "Full life" badge, a
	// works/CTA line, the mini-bio, and a scrollable strip of their books.
	// Shared by the biographies index and the per-era landing pages. `shelf` is
	// the writer's books (the caller groups the library's books by author).
	const t = i18n.t;
	let { author, shelf = [] }: { author: AuthorBio; shelf?: BookSummary[] } = $props();

	// Five covers fit the text column without a scrollbar; beyond that a "+N"
	// tile carries the rest to the author page.
	const SHELF_MAX = 5;

	const initials = (name: string) =>
		name.split(' ').filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase();
</script>

<!-- A bordered card (matching the site's rounded-card pattern) that reads as one
     tappable unit: hovering it warms the whole thing — border → accent and the
     portrait from grayscale to full colour. The author links carry preload-on-
     hover so the click lands instantly. -->
<article
	id={author.slug}
	class="group relative scroll-mt-36 rounded-card border border-border p-5 transition-colors hover:border-accent"
>
	<!-- Portrait beside the text, not above it. In the old two-up grid each row
	     was as tall as its TALLER card, so a 171-character bio next to a
	     640-character one left a hole; one writer per row makes every row
	     independent and the hole cannot form. -->
	<div class="flex gap-5">
		<a
			href={localizeHref(`/authors/${author.slug}`)}
			data-sveltekit-preload-data="hover"
			class="shrink-0 hover:no-underline"
		>
			{#if author.photo_url}
				<img
					src={author.photo_url}
					alt="{t('a11y.portraitOf')} {author.name}"
					loading="lazy"
					width="112"
					height="112"
					class="h-24 w-24 rounded-full border border-border object-cover grayscale transition-[filter] duration-300 group-hover:grayscale-0 sm:h-28 sm:w-28"
				/>
			{:else}
				<span
					class="flex h-24 w-24 items-center justify-center rounded-full bg-accent-soft text-display !text-3xl font-semibold text-accent sm:h-28 sm:w-28"
					style="font-family: var(--font-display)"
				>
					{initials(author.name)}
				</span>
			{/if}
		</a>
		<div class="min-w-0 flex-1">
			<h2 class="text-h2">
				<!-- Stretched link: the ::after covers the whole card, so the dead
				     space between the name and the CTA is clickable too. Links that
				     go SOMEWHERE ELSE (the book covers) sit above it with z-10. -->
				<a
					href={localizeHref(`/authors/${author.slug}`)}
					data-sveltekit-preload-data="hover"
					class="!text-text after:absolute after:inset-0 after:content-[''] hover:underline"
					>{author.name}</a
				>
				<!-- Below sm the name wraps to two lines on its own, and trailing the
				     dates and badge inline after it left them stranded raggedly at the
				     end. Give them their own row on mobile; keep the old inline flow
				     from sm up, where the name fits on one line. -->
				{#if author.birth_year || author.has_long_bio}
					<span class="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 sm:mt-0 sm:inline">
						{#if author.birth_year}
							<!-- nowrap: the dates were breaking after the en-dash ("1843–" / "1919"). -->
							<span class="whitespace-nowrap text-body font-normal text-muted sm:ms-2"
								>{formatLifespan(author.birth_year, author.death_year, t('common.bornPrefix'))}</span
							>
						{/if}
						{#if author.has_long_bio}
							<!-- Same nowrap rule as the dates: the badge was splitting into
							     "FULL" / "LIFE" across two lines on a phone. -->
							<span
								class="whitespace-nowrap align-middle rounded-full bg-accent-soft px-2 py-0.5 text-[0.68rem] font-semibold uppercase tracking-wide text-accent sm:ms-2"
								title={t('bios.fullLifeHint')}
							>
								{t('bios.fullLife')}
							</span>
						{/if}
					</span>
				{/if}
			</h2>
			<a href={localizeHref(`/authors/${author.slug}`)} class="text-small font-semibold text-accent">
				{#if author.book_count > 0}
					{author.book_count}
					{author.book_count === 1 ? t('bios.booksInLibraryOne') : t('bios.booksInLibraryMany')}
					{#if author.sermon_count > 0}
						· {author.sermon_count}
						{author.sermon_count === 1 ? t('bios.sermonsOne') : t('bios.sermonsMany')}
					{/if}
					→
				{:else if author.sermon_count > 0}
					{author.sermon_count}
					{author.sermon_count === 1 ? t('bios.sermonsOne') : t('bios.sermonsMany')} →
				{:else}
					<!-- Same wording as the read-more below: both links go to the same
					     author page, so they say the same thing. Adjacent cards used to
					     read "Read full biography →" and "View biography →" for one
					     action. -->
					{t('bios.readMore')} →
				{/if}
			</a>
	<!-- A short mini-bio (2–4 sentences) in the reader's language. Rendered in
	     full — the summaries are authored to card length, so we show complete
	     sentences rather than clamping mid-word. The `{#if}` matters: a bio with
	     no translation in this language is ABSENT, not English, so in a
	     partially-translated locale many cards legitimately show works only. -->
	{#if author.bio}
			<!-- line-clamp-3: mini-bios run 171-640 characters, so rendering them in
			     full gave every row a different height. The full text is one click
			     away on the author page, which the CTA below already points at. -->
			<p class="mt-3 line-clamp-5 text-body leading-relaxed text-muted sm:line-clamp-3">{author.bio}</p>
	{/if}
	<!-- The "View biography →" CTA above already serves book-less authors;
	     add the read-more only where the CTA is a book count AND there is
	     actually a biography to go and read. -->
	{#if author.book_count > 0 && author.bio}
		<a
			href={localizeHref(`/authors/${author.slug}`)}
			class="mt-1.5 inline-block text-small font-semibold text-accent"
		>
			{t('bios.readMore')} →
		</a>
	{/if}

	<!-- Their works, on a fixed rail. Counts run 0–7 across the library, and the
	     old strip rendered up to eight behind a horizontal scroll — so the
	     prolific writers got a long draggable row and everyone else got a stub.
	     Five is the cap now; the rest collapse into a
	     "+N" tile that goes where they were going anyway. BookCover holds a 3:4
	     box, so the rail height is identical for every writer who has one.

	     Five fit that column unscrolled on a desktop, but it is only ~177px on
	     a 375px phone, where five covers need 368px — so the rail keeps its
	     horizontal scroll. It costs nothing at widths that don't overflow (no
	     scrollbar appears) and holds every row to the same height, which
	     wrapping would not. `overscroll-x-contain` stops a swipe off the end of
	     the strip from turning into a browser back-navigation. -->
	{#if shelf.length}
			<div
			class="mt-4 flex gap-3 overflow-x-auto overscroll-x-contain pb-1"
			aria-label={t('nav.books')}
		>
				{#each shelf.slice(0, SHELF_MAX) as book (book.slug)}
					<a
						href={localizeHref(`/books/${book.slug}`)}
						class="relative z-10 w-16 shrink-0 hover:no-underline"
						title={book.title}
					>
						<BookCover {book} />
					</a>
				{/each}
				{#if shelf.length > SHELF_MAX}
					<a
						href={localizeHref(`/authors/${author.slug}`)}
						class="relative z-10 flex w-16 shrink-0 items-center justify-center rounded-card border border-dashed border-border text-small font-semibold text-muted transition-colors hover:border-accent hover:text-accent hover:no-underline"
						style="aspect-ratio: 3 / 4"
						title={t('bios.moreBooks')}
					>
						+{shelf.length - SHELF_MAX}
					</a>
				{/if}
			</div>
	{/if}
		</div>
	</div>
</article>
