<script lang="ts">
	import { onMount } from 'svelte';
	import type { CoverBook } from '$lib/library-public';
	import { formatLifespan } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';
	import { readingMinutes, readingTime } from '$lib/reading';
	import { sermonArt, sermonCoverFace } from '$lib/sermonArt';
	import { inkSafe } from '$lib/coverArt';
	import { scrollEdges } from '$lib/actions/scrollEdges';
	import BookCard from '$lib/components/BookCard.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import {
		TONIGHT_MAX_MINUTES,
		tonightKey,
		tonightShelf,
		wordsOf,
		type TonightItem
	} from '$lib/tonightShelf';

	/**
	 * "Tonight, under 20 minutes" (idea #27): whole works to finish in one
	 * evening — short books, single sermons, one-sitting biographies — from the
	 * home snapshot's pool (`$lib/tonightShelf`).
	 *
	 * Evening only (19:00–04:00 on the reader's clock), and decided at MOUNT:
	 * the page is prerendered, so the baked HTML has no shelf and the clock is
	 * read where the reader is. Re-checked when the tab comes back into view, so
	 * a tab left open from the afternoon gains it at night. Every card is a
	 * `BookCard` (the home shelves' one cover card): a book wears its cover, a
	 * sermon the plate `sermonCoverFace` sets for it (the resume card's), and a
	 * biography a plate with the writer's name — each with a "Kind · N min read"
	 * line, at the reader's own pace.
	 */
	let { items }: { items: TonightItem[] } = $props();
	const t = i18n.t;

	let now = $state<Date | null>(null);
	onMount(() => {
		now = new Date();
		const onVisible = () => {
			if (document.visibilityState === 'visible') now = new Date();
		};
		document.addEventListener('visibilitychange', onVisible);
		return () => document.removeEventListener('visibilitychange', onVisible);
	});

	const shown = $derived(now ? tonightShelf(items, now, readingMinutes) : []);

	/** The fields `BookCard` needs that a plate set from a sermon or a writer has
	 *  no use for. */
	const plateExtras = (words: number) => ({
		source_type: 'public_domain' as const,
		series: null,
		chapter_count: 1,
		word_count: words,
		has_modern_edition: false
	});

	function card(item: TonightItem): { book: CoverBook; href: string; kind: string } {
		const words = wordsOf(item);
		if (item.kind === 'book') {
			return { book: item.book, href: `/books/${item.book.slug}`, kind: t('search.typeBook') };
		}
		if (item.kind === 'sermon') {
			return {
				book: { ...sermonCoverFace(item.sermon), ...plateExtras(words) },
				href: `/sermons/${item.sermon.slug}`,
				kind: t('search.typeSermon')
			};
		}
		const w = item.writer;
		const kind = t('articles.kindBiography');
		return {
			book: {
				// Namespaced like a sermon's: BookCover keys its tables by BOOK slug.
				slug: `bio:${w.slug}`,
				language: w.language,
				title: w.name,
				subtitle: formatLifespan(w.birth_year, w.death_year, t('common.bornPrefix')),
				cover_title: '',
				// The plate's byline names the work, not the name again.
				cover_byline: kind,
				cover_color: inkSafe(sermonArt(`bio:${w.slug}`).hue),
				cover_url: '',
				series_position: null,
				author: { slug: w.slug, name: w.name, birth_year: w.birth_year },
				...plateExtras(words)
			},
			href: `/authors/${w.slug}#bio`,
			kind
		};
	}
</script>

{#if shown.length}
	<section class="page-col px-5 pt-14" data-testid="tonight-shelf">
		<SectionHeader
			title={t('home.tonightTitle').replace('%n%', String(TONIGHT_MAX_MINUTES))}
			subtitle={t('home.tonightSubtitle')}
		/>
		<div class="tonight-rows">
			<div class="cover-rail tonight-row" use:scrollEdges>
				{#each shown as item (tonightKey(item))}
					{@const c = card(item)}
					{@const label = `${c.kind} · ${readingTime(wordsOf(item))}`}
					<BookCard
						book={c.book}
						showAuthor={item.kind !== 'bio'}
						showSeries={false}
						link={{
							href: c.href,
							cta: t('book.beginReading'),
							label,
							ariaLabel:
								item.kind === 'bio'
									? `${c.book.title} — ${label}`
									: `${c.book.title} — ${c.book.author.name} · ${label}`
						}}
					/>
				{/each}
			</div>
		</div>
	</section>
{/if}

<style>
	/* The /books Browse row (BooksShelf .browse-row): one line of cards that
	   scrolls sideways with snap, sized off its own width — a little over two
	   on a phone so the next cover peeks in, then four, five, six across. */
	.tonight-rows {
		container: tonight-rows / inline-size;
	}
	.tonight-row {
		--across: 2.3;
		display: grid;
		grid-auto-flow: column;
		grid-auto-columns: calc((100% - (var(--across) - 1) * 1rem) / var(--across));
		column-gap: 1rem;
		padding-block: 0.375rem 0.5rem;
		scroll-snap-type: x proximity;
	}
	.tonight-row > :global(*) {
		scroll-snap-align: start;
	}
	@container tonight-rows (min-width: 36rem) {
		.tonight-row {
			--across: 4;
		}
	}
	@container tonight-rows (min-width: 56rem) {
		.tonight-row {
			--across: 5;
		}
	}
	@container tonight-rows (min-width: 68rem) {
		.tonight-row {
			--across: 6;
		}
	}
</style>
