<script lang="ts">
	import { coverGradient, coverSrcset, isArtCover } from '$lib/coverArt';
	import type { BookSummary } from '$lib/library';
	import { i18n } from '$lib/i18n.svelte';
	import BrandMark from './BrandMark.svelte';

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
	let {
		book,
		rounded = 'rounded-card',
		priority = false
	}: {
		book: BookSummary;
		rounded?: string;
		/** The page's main image (a book's own page): load it eagerly, declare its
		 * intrinsic size so space is reserved before app.css lands, and skip the
		 * skeleton — an LCP image should not wait for a lazy queue or fade in. */
		priority?: boolean;
	} = $props();

	// Keyed by the URL they describe, not free-floating: the book page renders
	// ONE BookCover and SvelteKit reuses it across /books/a → /books/b, so a
	// plain `failed = true` from a broken cover on A would leave B showing the
	// plate for the rest of the session. Derived rather than reset in an effect —
	// an $effect that writes state is a $derived in disguise (frontend/CLAUDE.md).
	let loadedUrl = $state('');
	let failedUrl = $state('');
	const loaded = $derived(loadedUrl === book.cover_url);
	const failed = $derived(failedUrl === book.cover_url);

	// A painting gets the cover's type drawn over it here — it carries none of
	// its own, which is what lets every language share one file.
	const isArt = $derived(isArtCover(book.cover_url));
	const srcset = $derived(coverSrcset(book.cover_url));
	const label = $derived(`${t('a11y.coverOf')} ${book.title}`);
</script>

<!-- The cover's type. Identical over a painting and over a plain plate — the
     only difference is what is behind it, which is what `.plate` decides. -->
{#snippet plateType()}
	<div class="type">
		<div class="byline truncate" dir="auto">{book.author.name}</div>
		<!-- Title, rule and subtitle move as one block so the auto margins centre
		     THEM between the byline and the mark. Left as three siblings, the
		     leftover space split three ways and the title rode up the plate. -->
		<div class="middle">
			<div class="title" dir="auto">{book.title}</div>
			<div class="rule"></div>
			{#if book.subtitle}<div class="subtitle line-clamp-2" dir="auto">{book.subtitle}</div>{/if}
		</div>
		<!-- The shared mark, not a second copy of the inline-the-lockup recipe:
		     it sizes off the plate's container, hence a cq height. -->
		<BrandMark height="13.7cqw" />
	</div>
{/snippet}

<div class="relative aspect-[3/4] w-full overflow-hidden {rounded} shadow-sm">
	{#if book.cover_url && !failed}
		{#if !loaded && !priority}
			<div class="absolute inset-0 animate-pulse bg-surface-2"></div>
		{/if}
		<img
			src={book.cover_url}
			srcset={srcset || undefined}
			sizes={srcset ? (priority ? '128px' : '200px') : undefined}
			alt={isArt ? '' : label}
			loading={priority ? 'eager' : 'lazy'}
			fetchpriority={priority ? 'high' : undefined}
			width={priority ? 300 : undefined}
			height={priority ? 400 : undefined}
			onload={() => (loadedUrl = book.cover_url)}
			onerror={() => (failedUrl = book.cover_url)}
			class="absolute inset-0 h-full w-full object-cover transition-opacity duration-[var(--duration-base)]"
			class:opacity-0={!loaded && !priority}
			class:opacity-100={loaded || priority}
		/>
		{#if isArt}
			<!-- The painting carries no words, so the cover's type is drawn here —
			     one shared image, a title per language. -->
			<div class="plate over-art" role="img" aria-label={label}>{@render plateType()}</div>
		{/if}
	{:else}
		<div
			class="plate"
			style="--plate: {coverGradient(book.cover_color)}"
			role="img"
			aria-label={label}
		>
			{@render plateType()}
		</div>
	{/if}
</div>

<style>
	/* Every length is in container units, so one rule serves the plate at any
	   width a card gives it — 64px in an author's rail, 128px beside a book's
	   details, a grid cell on the shelf — which is the scaling the SVG was kept
	   for, without the SVG.
	   The `cq` sizes are deliberately outside the `--fs-*` ramp that
	   `typeScaleGuard` polices: this is artwork sized off its own container, not
	   interface text, and pinning it to the UI scale would stop it scaling. */
	/* The plate is the query container; every length below is on a DESCENDANT of
	   it. An element cannot query itself — cq units in `.plate`'s own padding
	   would silently fall back to the viewport, which at a 300px plate on a
	   1240px window meant 111px of padding and a cover with nothing on it. */
	.plate {
		container-type: inline-size;
		height: 100%;
		/* Two layers, as the file has: the book's gradient, and over it the same
		   vignette covers.py paints — radial, transparent to 55% and black 0.34
		   at the edge, centred at (50%, 42%). Not decoration: the generated
		   file's byline measures 4.87:1 with it and the plate measured 4.41:1
		   without, against a 4.5 bar. The vignette carries most of the margin
		   `ink_safe` floors the colour to earn. */
		background:
			radial-gradient(78% 78% at 50% 42%, transparent 55%, rgb(0 0 0 / 0.34) 100%),
			var(--plate);
	}
	/* Over a painting the plate paints no colour of its own — just the scrim the
	   composited SVG used to carry: a global darkener so white type holds
	   anywhere, and heavier bands top and bottom, under the byline and the mark,
	   which is where art is most likely to be pale. */
	.plate.over-art {
		position: absolute;
		inset: 0;
		background:
			linear-gradient(
				180deg,
				rgb(0 0 0 / 0.62) 0%,
				rgb(0 0 0 / 0.34) 30%,
				rgb(0 0 0 / 0.4) 70%,
				rgb(0 0 0 / 0.7) 100%
			),
			rgb(26 20 16 / 0.26);
	}
	.plate.over-art .type::before {
		border-color: rgb(255 255 255 / 0.3);
	}
	.type {
		display: flex;
		flex-direction: column;
		/* Deliberately NOT `align-items: center`: that sizes each line to its own
		   max-content width, so a long title overflows the plate instead of
		   wrapping inside it. The children stretch and centre their text. */
		height: 100%;
		/* 112/600 of the plate's width down, which is where covers.py's y=112
		   baseline falls. Not a cosmetic match: `ink_safe` floors a plate colour
		   for the contrast AT that height, so a byline sitting higher up the
		   gradient than the generator's would sit on a lighter tone than the
		   floor was computed against. */
		padding: 17cqw 7cqw 9cqw;
		color: #fff;
		text-align: center;
	}
	.type::before {
		content: '';
		position: absolute;
		inset: 4.3cqw;
		border: 1px solid rgb(255 255 255 / 0.22);
	}
	/* NOT `.eyebrow`: that class exists in app.css, is unlayered and would match
	   this element too, so two rules would own it and half its type would arrive
	   from somewhere the plate never mentions. The tracking here is the cover's
	   own (0.28em against the chrome's 0.08em), which is why it doesn't just use
	   the shared recipe. Truncation is Tailwind's `truncate` in the markup: a
	   long byline has nowhere to wrap to at this tracking, and clipping it beats
	   pushing the title down the plate. */
	.byline {
		font-size: 3.9cqw;
		letter-spacing: 0.28em;
		text-transform: uppercase;
		opacity: 0.86;
	}
	/* Optical centre of the space between the byline and the mark, which is
	   where covers.py puts the title — as a layout rule, not a coordinate. */
	.middle {
		margin: auto 0;
	}
	.title {
		font-family: var(--font-display);
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
		font-family: var(--font-display);
		font-style: italic;
		font-size: 3.7cqw;
		opacity: 0.85;
		/* `line-clamp-2` in the markup holds it to two lines, the generator's own
		   subtitle budget; past that the plate is a thumbnail and the words are
		   unreadable anyway. */
	}
	/* The mark paints with `currentColor`, which the plate has already set to
	   white — one colour decision serves the whole plate. */
	.type :global(.brandmark) {
		margin-inline: auto;
		opacity: 0.82;
	}
</style>
