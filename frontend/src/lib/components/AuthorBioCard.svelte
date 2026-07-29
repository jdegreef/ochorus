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

	const initials = (name: string) =>
		name.split(' ').filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase();
</script>

<article id={author.slug} class="scroll-mt-24">
	<div class="flex items-center gap-4">
		<a href={localizeHref(`/authors/${author.slug}`)} class="shrink-0 hover:no-underline">
			{#if author.photo_url}
				<img
					src={author.photo_url}
					alt="{t('a11y.portraitOf')} {author.name}"
					loading="lazy"
					width="56"
					height="56"
					class="h-14 w-14 rounded-full border border-border object-cover"
					style="filter: grayscale(1)"
				/>
			{:else}
				<span
					class="flex h-14 w-14 items-center justify-center rounded-full bg-accent-soft text-h3 font-semibold text-accent"
					style="font-family: var(--font-display)"
				>
					{initials(author.name)}
				</span>
			{/if}
		</a>
		<div>
			<h2 class="text-h2">
				<a href={localizeHref(`/authors/${author.slug}`)} class="!text-text hover:underline">{author.name}</a>
				{#if author.birth_year}
					<!-- nowrap: the dates were breaking after the en-dash ("1843–" / "1919"). -->
					<span class="ml-2 whitespace-nowrap text-body font-normal text-muted"
						>{formatLifespan(author.birth_year, author.death_year, t('common.bornPrefix'))}</span
					>
				{/if}
				{#if author.has_long_bio}
					<span
						class="ml-2 align-middle rounded-full bg-accent-soft px-2 py-0.5 text-[0.68rem] font-semibold uppercase tracking-wide text-accent"
						title={t('bios.fullLifeHint')}
					>
						{t('bios.fullLife')}
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
					{t('bios.viewBiography')} →
				{/if}
			</a>
		</div>
	</div>
	<!-- Every writer carries a short mini-bio (2–4 sentences), localized to
	     the reader's language. Rendered in full — the summaries are authored
	     to card length, so we show complete sentences rather than clamping
	     mid-word. The `{#if}` guards the rare row that still lacks prose. -->
	{#if author.bio}
		<p class="mt-4 text-body leading-relaxed text-muted">{author.bio}</p>
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

	<!-- Their works: a scrollable strip of the writer's books, straight
	     into the reader. -->
	{#if shelf.length}
		<div class="mt-4 flex gap-3 overflow-x-auto pb-1" aria-label={t('nav.books')}>
			{#each shelf.slice(0, 8) as book (book.slug)}
				<a
					href={localizeHref(`/books/${book.slug}`)}
					class="w-16 shrink-0 hover:no-underline"
					title={book.title}
				>
					<BookCover {book} />
				</a>
			{/each}
		</div>
	{/if}
</article>
