<script lang="ts">
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { ERAS, eraOf } from '$lib/eras';
	import { formatLifespan, type AuthorBio, type BookSummary } from '$lib/library-public';
	import { firstSentence } from '$lib/firstSentence';
	import Portrait from '$lib/components/Portrait.svelte';

	/**
	 * A series whose every volume is ABOUT a person (The Key Teachings of …):
	 * the books shown as the people, not as thirty-six covers that all say
	 * "Key Teachings". Each card is the face, the name set large, the dates and
	 * one line on who they were (the first sentence of their short bio, in
	 * this language), and it opens the book. Grouped by era, earliest first, so the shelf reads as a
	 * walk through church history.
	 *
	 * `subjectOf` maps a book to its subject's slug; a subject the writers list
	 * doesn't hold still gets a card, named from the cover byline, with initials.
	 */
	let {
		books,
		authors,
		subjectOf
	}: {
		books: BookSummary[];
		authors: AuthorBio[];
		subjectOf: (book: BookSummary) => string;
	} = $props();
	const t = i18n.t;

	const bySlug = $derived(new Map(authors.map((a) => [a.slug, a])));
	const cards = $derived(
		books
			.map((book) => {
				const slug = subjectOf(book);
				const a = bySlug.get(slug);
				return {
					book,
					slug,
					name: a?.name ?? book.cover_byline ?? book.title,
					photo: a?.photo_url ?? '',
					born: a?.birth_year ?? null,
					life: a ? formatLifespan(a.birth_year, a.death_year, t('common.bornPrefix')) : '',
					line: a ? firstSentence(a.bio) : ''
				};
			})
			.sort((x, y) => (x.born ?? 9999) - (y.born ?? 9999) || x.name.localeCompare(y.name))
	);
	const eras = $derived(
		ERAS.map((era) => ({ era, cards: cards.filter((c) => eraOf(c.born) === era.id) })).filter(
			(g) => g.cards.length
		)
	);
</script>

{#each eras as { era, cards: group } (era.id)}
	<section class="mb-10">
		<h3 class="era-head font-display text-h3 font-semibold">
			{t(era.k)} <span class="text-small font-normal text-muted">{era.range}</span>
		</h3>
		<ul class="subject-grid">
			{#each group as c (c.book.slug)}
				<li>
					<a class="subject-card group" href={localizeHref(`/books/${c.book.slug}`)}>
						<Portrait
							slug={c.slug}
							name={c.name}
							url={c.photo}
							px={88}
							tone="hover"
							decorative
							class="h-[4.5rem] w-[4.5rem] sm:h-[5.5rem] sm:w-[5.5rem]"
							initialsClass="text-h3"
						/>
						<span class="min-w-0">
							<span class="subject-name font-display block font-semibold">{c.name}</span>
							{#if c.life}<span class="block text-small text-muted">{c.life}</span>{/if}
							{#if c.line}<span class="subject-line mt-1 block text-small">{c.line}</span>{/if}
						</span>
					</a>
				</li>
			{/each}
		</ul>
	</section>
{/each}

<style>
	.era-head {
		margin-block-end: 1rem;
		padding-block-end: 0.5rem;
		border-block-end: 1px solid var(--border);
	}
	.subject-grid {
		display: grid;
		gap: 0.75rem;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 19rem), 1fr));
	}
	.subject-card {
		display: flex;
		align-items: center;
		gap: 1rem;
		block-size: 100%;
		padding: 0.875rem 1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		color: var(--text);
		transition:
			border-color var(--duration-base),
			background var(--duration-base);
	}
	.subject-card:hover,
	.subject-card:focus-visible {
		border-color: var(--accent);
		background: var(--surface-2);
	}
	.subject-name {
		font-size: var(--fs-h3);
		line-height: 1.2;
	}
	.subject-card:hover .subject-name {
		color: var(--accent);
	}
	.subject-line {
		color: var(--text);
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
