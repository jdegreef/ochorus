<script lang="ts">
	import type { BookSummary } from '$lib/library-public';
	import { canonStrip, divisionKey, testamentKey } from '$lib/bible';
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
	 */
	let { books }: { books: readonly BookSummary[] } = $props();
	const t = i18n.t;
	const testaments = $derived(canonStrip(books));
</script>

<nav class="canon" aria-label={t('bible.canonLabel')}>
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
										<a
											class="spine"
											href={localizeHref(`/books/${slot.book.slug}`)}
											title={slot.book.title}
											style:--spine-w={slot.weight}
											style:--spine-c={slot.book.cover_color || null}>{slot.name}</a
										>
									{:else}
										<span class="spine absent" title={slot.name}>{slot.name}</span>
									{/if}
								</li>
							{/each}
						</ol>
						<!-- A one-book division (Acts, Revelation) is named by its spine.
						     Visual only: the list's aria-label names it for a screen reader. -->
						{#if group.slots.length > 1}
							<span class="canon-label" aria-hidden="true">{t(divisionKey(group.division.id))}</span>
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
		display: flex;
		align-items: center;
		justify-content: flex-start;
		box-sizing: border-box;
		/* 17px for the shortest book, 35px for the longest: both testaments
		   fit a desktop column, and scroll on anything narrower. */
		width: calc(1.0625rem + var(--spine-w, 0) * 1.125rem);
		height: 7rem;
		padding-block: 0.5rem;
		writing-mode: vertical-rl;
		border-radius: 2px 2px 1px 1px;
		/* hex-ok: a cover colour, not a theme colour — the book's own cloth, dark in both themes */
		background: var(--spine-c, #4a3a2a);
		/* Two gilt bands, as on a cloth spine, and a little roundness. */
		background-image:
			linear-gradient(
				to bottom,
				transparent 0.3rem,
				rgb(224 180 92 / 0.55) 0.3rem,
				rgb(224 180 92 / 0.55) calc(0.3rem + 1px),
				transparent calc(0.3rem + 1px),
				transparent calc(100% - 0.3rem - 1px),
				rgb(224 180 92 / 0.55) calc(100% - 0.3rem - 1px),
				rgb(224 180 92 / 0.55) calc(100% - 0.3rem),
				transparent calc(100% - 0.3rem)
			),
			linear-gradient(to right, rgb(255 255 255 / 0.1), transparent 40%, rgb(0 0 0 / 0.18));
		/* hex-ok: light ink on that dark cloth, as a cover sets its title */
		color: #f3ead9;
		font-family: var(--font-display);
		font-size: var(--fs-micro);
		line-height: 1;
		white-space: nowrap;
		overflow: hidden;
		text-decoration: none;
		transition: transform 0.15s ease;
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
		background: none;
		border: 1px dashed var(--border-strong);
		color: var(--muted);
		opacity: 0.6;
	}
	@media (prefers-reduced-motion: reduce) {
		.spine {
			transition: none;
		}
	}
</style>
