<script lang="ts">
	import { isTranslated, type SourceType } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';

	/**
	 * "How did this text get here" — one badge, three placements.
	 *
	 * The same idea was drawn four ways: a white-on-black pill over the cover in
	 * BookCard, a bordered muted pill in BookListRow, and a byte-identical
	 * reviewed/unreviewed pill duplicated between the book page and the sermon
	 * page. The predicate for "this is a translation" (`!== 'public_domain'`)
	 * was written out in each of them.
	 *
	 * The two jobs are deliberately different, and that is the whole design:
	 *
	 *   - On a SHELF the question is "is this a translation?", which "Translated"
	 *     answers for both AI states. The review status still travels with it, on
	 *     the accessible name, because that costs nothing.
	 *   - On the WORK'S OWN PAGE the question is "who made this and has a native
	 *     speaker checked it?" — so `detail` says so in a sentence and marks an
	 *     unreviewed translation in the warning tone (CLAUDE.md: never present an
	 *     unreviewed translation as an original).
	 *
	 * A public-domain original renders nothing at all.
	 */
	let {
		sourceType,
		variant = 'detail',
		class: klass = ''
	}: {
		sourceType: SourceType;
		/** `detail` on the work's own page; `overlay` on artwork; `inline` in a text row. */
		variant?: 'detail' | 'overlay' | 'inline';
		/** Positioning/margins from the caller — this component owns colour and shape only. */
		class?: string;
	} = $props();

	const t = i18n.t;
	const unreviewed = $derived(sourceType === 'ai_unreviewed');
	/** The full sentence. Visible on `detail`; a hover title on the shelf, where
	 *  the badge's own word is the accessible name and the sentence is detail. */
	const full = $derived(unreviewed ? t('book.aiUnreviewed') : t('book.aiReviewed'));
</script>

{#if isTranslated(sourceType)}
	{#if variant === 'detail'}
		<p class="badge detail {klass}" class:unreviewed>{full}</p>
	{:else}
		<!-- .eyebrow is the shared uppercase-micro recipe (app.css); only colour,
		     padding and the tighter tracking are this component's business. -->
		<span class="badge eyebrow {variant} {klass}" class:unreviewed title={full}>
			{t('books.badgeTranslated')}
		</span>
	{/if}
{/if}

<style>
	.badge {
		display: inline-flex;
		align-items: center;
		gap: 0.375rem;
		border-radius: 9999px;
		border: 1px solid transparent;
	}

	/* On the work's own page: a sentence, and the warning tone when no native
	   speaker has signed the translation off yet. */
	.detail {
		padding: 0.25rem 0.75rem;
		font-size: var(--fs-small);
		border-color: var(--border);
		background: var(--surface-2);
		color: var(--muted);
	}
	.detail.unreviewed {
		border-color: color-mix(in srgb, var(--warning) 40%, transparent);
		background: color-mix(in srgb, var(--warning) 10%, transparent);
		color: var(--warning);
	}

	/* Over cover artwork: the cover is any colour, so the pill carries its own
	   ground rather than trusting a token to contrast with it.

	   Two defences, because the word's width is not ours to know: `max-width` +
	   ellipsis keeps it on the artwork whatever the locale, and below 6rem of
	   card it is dropped entirely rather than shown as "TRANSLA…". 6rem is where
	   it stops fitting for real — measured at a 320px viewport, where the
	   two-across shelf gives a 91px card. The same fact is still on the book's
	   own page, in the list view, and behind the shelf's Translated filter. */
	.overlay {
		padding: 0.125rem 0.375rem;
		/* Tighter than .eyebrow's own tracking on purpose: this one has a cover's
		   width to live in, and tracking is the cheapest 9px to give back. */
		letter-spacing: 0.04em;
		background: rgb(0 0 0 / 0.55);
		/* hex-ok: this pill carries its own dark ground on top of cover
		   artwork, so its ink is fixed white rather than a theme token. */
		color: #fff;
		backdrop-filter: blur(4px);
		/* The label is translated, so its width is not ours to know — Swahili's is
		   half again as long as English's. Never let it hang off the artwork. */
		max-width: calc(100% - 1rem);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	@container (max-width: 6rem) {
		.overlay {
			display: none;
		}
	}

	/* Beside a title in a list row. */
	.inline {
		padding: 0.125rem 0.375rem;
		border-color: var(--border);
		color: var(--muted);
		flex-shrink: 0;
	}
</style>
