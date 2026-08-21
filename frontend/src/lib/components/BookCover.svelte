<script lang="ts">
	import { coverGradient } from '$lib/coverArt';
	import type { BookSummary } from '$lib/library';
	import { i18n } from '$lib/i18n.svelte';
	import lockup from '$lib/brand/ochorus-lockup.svg?raw';

	const t = i18n.t;

	/**
	 * A book's cover: the committed artwork when there is one, otherwise a plate
	 * drawn from the book's own colour. The box keeps a fixed 3:4 aspect so
	 * nothing shifts while a lazy image loads.
	 *
	 * THE PLATE IS A PLACEHOLDER, NOT A REPLICA. It used to be a hand-built SVG
	 * copy of `covers.py`'s generated cover — same frame, eyebrow, centred title,
	 * divider, lockup — on the theory that a book without a file should look like
	 * one with a file. Two implementations of one drawing is a promise nobody
	 * could keep, and it wasn't kept: the copy had its own type ramp (58/46
	 * against the generator's 60/50/42/34), its own wrap budget, line height,
	 * title centre, rule offset and gradient angle, no vignette at all, and —
	 * worse than any measurement — no RTL, no per-script font stacks and no
	 * script scaling, so an Arabic book's fallback came out in Georgia, set
	 * left-to-right.
	 *
	 * CSS has all of that for free. The title below is real text: the browser
	 * shapes Arabic, picks the Devanagari face, honours `dir` from the document,
	 * wraps where the words actually are (rather than at a character count that
	 * means nothing off the Latin script), sets it in the real brand serif — the
	 * generated file can only name fonts a device already has, so it settles for
	 * Georgia — and scales with the card through container units.
	 *
	 * The proportions below are the house style's (frame at 4.3% of the width,
	 * lockup at 22.7%, rule at 12.7%), so the two tiers still read as one shelf.
	 * What is gone is the second ALGORITHM: no wrap budget, no type ramp, no
	 * block centre to recompute — the parts that drifted, and the only parts a
	 * reviewer could not check by eye.
	 *
	 * It is rarely seen: every published book carries a `cover_url`, so this is
	 * the admin-imported book whose file isn't drawn yet, and the broken image.
	 *
	 * hex-ok-file: the ink is white ON the book's own `cover_color` — data, not a
	 * theme surface (STYLE_GUIDE §1), so it must not follow the reader's theme.
	 * White is safe here because a plate colour is floored for contrast where it
	 * is minted (`covers.ink_safe`), so what reaches this component already
	 * carries white type at AA.
	 */
	let { book, rounded = 'rounded-card' }: { book: BookSummary; rounded?: string } = $props();

	let loaded = $state(false);
	let failed = $state(false);
</script>

<div class="relative aspect-[3/4] w-full overflow-hidden {rounded} shadow-sm">
	{#if book.cover_url && !failed}
		{#if !loaded}
			<div class="absolute inset-0 animate-pulse bg-surface-2"></div>
		{/if}
		<img
			src={book.cover_url}
			alt="{t('a11y.coverOf')} {book.title}"
			loading="lazy"
			onload={() => (loaded = true)}
			onerror={() => (failed = true)}
			class="absolute inset-0 h-full w-full object-cover transition-opacity duration-[var(--duration-base)]"
			class:opacity-0={!loaded}
			class:opacity-100={loaded}
		/>
	{:else}
		<div
			class="plate"
			style="background: {coverGradient(book.cover_color)}"
			role="img"
			aria-label="{t('a11y.coverOf')} {book.title}"
		>
			<div class="type">
				<div class="eyebrow">{book.author.name}</div>
				<!-- Title, rule and subtitle move as one block so the auto margins
				     centre THEM between the byline and the mark. Left as three
				     siblings, the leftover space split three ways and the title rode
				     up the plate. -->
				<div class="middle">
					<div class="title">{book.title}</div>
					<div class="rule"></div>
					{#if book.subtitle}<div class="subtitle">{book.subtitle}</div>{/if}
				</div>
				<div class="mark">
					<!-- eslint-disable-next-line svelte/no-at-html-tags -- our own build-time asset -->
					{@html lockup}
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	/* Every length is in container units, so one rule serves the 40px fan on a
	   topic card and the 300px plate on a book page — the scaling the SVG was
	   kept for, without the SVG. */
	/* The plate is the query container; every length below is on a DESCENDANT of
	   it. An element cannot query itself — cq units in `.plate`'s own padding
	   would silently fall back to the viewport, which at a 300px plate on a
	   1240px window meant 111px of padding and a cover with nothing on it. */
	.plate {
		container-type: inline-size;
		position: relative;
		height: 100%;
		width: 100%;
	}
	.type {
		display: flex;
		flex-direction: column;
		/* Deliberately NOT `align-items: center`: that sizes each line to its own
		   max-content width, so a long title overflows the plate instead of
		   wrapping inside it. The children stretch and centre their text. */
		height: 100%;
		padding: 9cqw 7cqw;
		color: #fff;
		text-align: center;
	}
	.type::before {
		content: '';
		position: absolute;
		inset: 4.3cqw;
		border: 1px solid rgb(255 255 255 / 0.22);
	}
	.eyebrow {
		font-size: 3.9cqw;
		letter-spacing: 0.28em;
		text-transform: uppercase;
		opacity: 0.86;
		/* The eyebrow is the one line that can overrun: a long byline has nowhere
		   to wrap to at this letter-spacing, so it is clipped rather than allowed
		   to push the title down the plate. */
		max-width: 100%;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}
	/* Optical centre of the space between the byline and the mark, which is
	   where covers.py puts the title — as a layout rule, not a coordinate. */
	.middle {
		margin: auto 0;
	}
	.title {
		font-family: var(--font-display, Georgia, 'Times New Roman', serif);
		font-weight: 600;
		font-size: 9.5cqw;
		line-height: 1.15;
		text-wrap: balance;
	}
	.rule {
		width: 12.7cqw;
		/* The generated cover drops the rule 52 units below the title's last
		   baseline on an 800-unit plate; this is that gap, proportionally. */
		margin: 5cqw auto 0;
		border-top: 1px solid rgb(255 255 255 / 0.55);
	}
	.subtitle {
		margin-top: 3cqw;
		font-family: var(--font-display, Georgia, serif);
		font-style: italic;
		font-size: 3.7cqw;
		opacity: 0.85;
		/* Two lines, like the generator's subtitle budget; beyond that the plate
		   is a thumbnail and the words are unreadable anyway. */
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		overflow: hidden;
	}
	.mark {
		margin-inline: auto;
		width: 22.7cqw;
		opacity: 0.82;
	}
	/* The lockup paints with `currentColor`, which the plate has already set to
	   white — no fill override, so one colour decision serves the whole plate. */
	.mark :global(svg) {
		width: 100%;
		height: auto;
		display: block;
	}
</style>
