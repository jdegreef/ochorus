<script lang="ts">
	import { coverGradient, coverSrcset, isArtCover, isPlateCover } from '$lib/coverArt';
	import { coverStyleFor } from '$lib/coverStyles';
	import { eraOf } from '$lib/eras';
	import type { BookSummary } from '$lib/library';
	import { i18n } from '$lib/i18n.svelte';
	import BrandMark from './BrandMark.svelte';

	const t = i18n.t;

	/**
	 * A book's cover: a committed GROUND — a painting, or the plate drawn from
	 * the book's own colour — with the book's type set over it here. The box
	 * keeps a fixed 3:4 aspect so nothing shifts while a lazy image loads.
	 *
	 * THE TYPE IS DRAWN HERE, FOR EVERY TIER. It used to be drawn here only over
	 * `covers/art/` paintings; a generated plate arrived from `covers.py` with
	 * its words already in the file, and this component had a hand-built SVG
	 * replica of that plate for the rare book carrying no file at all.
	 *
	 * Two implementations of one drawing is a promise nobody could keep, and it
	 * wasn't kept: the replica had its own type ramp (58/46 against the
	 * generator's 60/50/42/34), its own wrap budget, line height, title centre,
	 * rule offset and gradient angle, no vignette at all, and — worse than any
	 * measurement — no RTL, no per-script font stacks and no script scaling, so
	 * an Arabic book's fallback came out in Georgia, set left-to-right.
	 *
	 * CSS has all of that for free. The title below is real text: the browser
	 * shapes Arabic, picks the Devanagari face, honours `dir` from the document,
	 * wraps where the words actually are (rather than at a character count that
	 * means nothing off the Latin script), and scales with the card through
	 * container units.
	 *
	 * And it can be set in a WEBFONT, which is what turned this from a tidy-up
	 * into the point. An SVG served through `<img>` renders in an isolated
	 * document that cannot reach the page's fonts, so `covers.py` could only name
	 * faces a device already has — Georgia, on every book in the library. The
	 * type here is styled per author by `$lib/coverStyles`: Bunyan in the Fell
	 * types his century printed, Spurgeon in a Victorian display face, Augustine
	 * in Roman capitals. That is not expressible in a file the generator writes.
	 *
	 * WHAT THE COMMITTED FILE STILL CARRIES is everything that is NOT words: the
	 * painting, or the plate's gradient, vignette and topic emblem. So there is
	 * one drawing of the type (here) and one of the ground (the file), and
	 * neither is a copy of the other. The proportions the two share — the frame
	 * inset, the emblem band, where the mark sits — are copied deliberately and
	 * named on both sides (STYLE_GUIDE §5); the algorithms never are.
	 *
	 * THE COLOURED PLATE BELOW is now only the missing-file case: the
	 * admin-imported book whose ground isn't drawn yet, and the broken image. It
	 * paints in CSS what the plate file paints in SVG, and wears the same type as
	 * everything else.
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

	// The two grounds that carry no words and want type over them. A DESIGNED
	// raster (the ministry titles, `/covers/<slug>.jpg`) is excluded by both:
	// its words are in the file, and a second set over them would be a mess.
	const isArt = $derived(isArtCover(book.cover_url));
	const isPlate = $derived(isPlateCover(book.cover_url));
	const overFile = $derived(isArt || isPlate);
	const srcset = $derived(coverSrcset(book.cover_url));
	const label = $derived(`${t('a11y.coverOf')} ${book.title}`);

	/** The author's house style — the whole of what varies between covers here. */
	const style = $derived(coverStyleFor(eraOf(book.author.birth_year), book.author.slug));
</script>

<!-- The cover's type. Identical over a painting, over a plate file and over the
     CSS plate — the only difference is what is behind it, and whether an emblem
     is down there to leave room for. -->
{#snippet plateType(reserveEmblem: boolean)}
	<div
		class="type"
		style="--cover-face: {style.face}; --cover-weight: {style.weight}; --cover-transform: {style.transform}; --cover-tracking: {style.tracking}; --cover-scale: {style.scale}"
	>
		<div class="byline truncate" dir="auto">{book.author.name}</div>
		<!-- Title, rule and subtitle move as one block so the auto margins centre
		     THEM between the byline and the mark. Left as three siblings, the
		     leftover space split three ways and the title rode up the plate. -->
		<div class="middle">
			<div class="title" dir="auto">{book.title}</div>
			<div
				class="rule"
				class:rule-double={style.rule === 'double'}
				class:rule-diamond={style.rule === 'diamond'}
			></div>
			{#if book.subtitle}<div class="subtitle line-clamp-2" dir="auto">{book.subtitle}</div>{/if}
		</div>
		<!-- The band the plate file draws its topic emblem into. Reserved here
		     rather than drawn here: which emblem a book wears is decided from its
		     TOPICS, and `emblemNames.ts` was split out of `emblems.ts` precisely
		     so that a shelf need not pull all 51 drawings onto the critical path
		     to answer that (measured: 37 KB raw, on the home page). So the file
		     keeps the drawing, and this keeps the type off it — the auto margins
		     above centre the title in what is left.
		     Empty on a book whose topics have no emblem, which costs that cover a
		     little air and every OTHER plate a geometry that agrees with its
		     file. Paintings don't reserve it: there is no emblem under them. -->
		{#if reserveEmblem}<div class="emblem-band" aria-hidden="true"></div>{/if}
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
			alt={overFile ? '' : label}
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
		{#if overFile}
			<!-- The ground carries no words, so the cover's type is drawn here —
			     one shared image, a title per language. -->
			<div
				class="plate"
				class:over-art={isArt}
				class:over-ground={isPlate}
				role="img"
				aria-label={label}
			>
				{@render plateType(isPlate)}
			</div>
		{/if}
	{:else}
		<div
			class="plate"
			style="--plate: {coverGradient(book.cover_color)}"
			role="img"
			aria-label={label}
		>
			{@render plateType(false)}
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
	/* Over a PLATE FILE, nothing at all. The gradient and the vignette are in
	   the SVG underneath, drawn by `covers.py` from the same numbers as `.plate`
	   above — painting them a second time here would double the vignette and
	   darken every generated cover in the library. No scrim either: the ground
	   is a floored flat colour, not a photograph, so `ink_safe` has already
	   proved white sits on it. */
	.plate.over-ground {
		position: absolute;
		inset: 0;
		background: none;
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
	   pushing the title down the plate.
	   In the HOUSE serif on every cover, whatever the title is set in: the
	   author's face is the title's, and a byline that changed with it would make
	   the shelf's one constant line the loudest thing on the grid. */
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
	/* The one element the author's house style owns. Face, weight, case,
	   tracking and size all arrive as custom properties from `coverStyles.ts`;
	   the fallbacks are the house recipe, so a plate still draws if the style
	   ever fails to reach it. */
	.title {
		font-family: var(--cover-face, var(--font-display));
		font-weight: var(--cover-weight, 600);
		/* 9.5cqw is the base; the multiplier evens out how big five different
		   faces LOOK at one nominal size (see CoverStyle.scale). */
		font-size: calc(9.5cqw * var(--cover-scale, 1));
		letter-spacing: var(--cover-tracking, 0);
		text-transform: var(--cover-transform, none);
		line-height: 1.15;
		text-wrap: balance;
	}
	/* The rule under the title, in three treatments — the style's ornament.
	   Drawn as backgrounds rather than borders so the variants can put two lines
	   or a gap where the plain one puts one line, without changing the box. */
	.rule {
		width: 12.7cqw;
		/* The generated cover drops the rule 52 units below the title's last
		   baseline on an 800-unit plate; this is that gap, proportionally. */
		margin: 5cqw auto 0;
		height: 1px;
		background: rgb(255 255 255 / 0.55);
	}
	/* A double rule, the way a 17th-century title page breaks a page: the second
	   line lighter, so it reads as an echo rather than as a box. */
	.rule-double {
		width: 16cqw;
		height: 0.9cqw;
		background:
			linear-gradient(rgb(255 255 255 / 0.55) 0 0) top / 100% 1px no-repeat,
			linear-gradient(rgb(255 255 255 / 0.4) 0 0) bottom / 100% 1px no-repeat;
	}
	/* A lozenge between two short rules — the printer's fleuron, reduced to the
	   one shape that still reads at 40px. */
	.rule-diamond {
		position: relative;
		width: 18cqw;
		height: 1.6cqw;
		background:
			linear-gradient(rgb(255 255 255 / 0.55) 0 0) left center / 6cqw 1px no-repeat,
			linear-gradient(rgb(255 255 255 / 0.55) 0 0) right center / 6cqw 1px no-repeat;
	}
	.rule-diamond::before {
		content: '';
		position: absolute;
		inset: 50% auto auto 50%;
		width: 1.1cqw;
		height: 1.1cqw;
		translate: -50% -50%;
		rotate: 45deg;
		border: 1px solid rgb(255 255 255 / 0.62);
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
	/* The emblem's room, not the emblem: 120 units of drawing and a 24-unit gap
	   on a 600-wide plate, which is what `covers.py` places it at. Both sides
	   name the same three numbers (STYLE_GUIDE §5) — move one and look there. */
	.emblem-band {
		height: 20cqw;
		margin-bottom: 4cqw;
	}
	/* The mark paints with `currentColor`, which the plate has already set to
	   white — one colour decision serves the whole plate. */
	.type :global(.brandmark) {
		margin-inline: auto;
		opacity: 0.82;
	}
</style>
