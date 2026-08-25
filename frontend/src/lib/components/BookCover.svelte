<script lang="ts">
	import { coverGradient, coverSrcset, isArtCover, isPlateCover } from '$lib/coverArt';
	import { coverStyleFor, scriptOf } from '$lib/coverStyles';
	import { eraOf } from '$lib/eras';
	// The cover's whole drawing, in the one file that also feeds the share-card
	// script (see its header). Global rather than scoped, like app.css's other
	// component classes, and namespaced under `.cover-*` so it cannot collide.
	import './cover-type.css';
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

	/** The author's house style — a class name; `cover-type.css` holds the rest. */
	const style = $derived(coverStyleFor(eraOf(book.author.birth_year), book.author.slug));
	/** The script whose metrics this edition needs correcting for; '' for Latin.
	 *  The FACE needs no class — the stacks in app.css fall back per glyph. */
	const script = $derived(scriptOf(book.language));
</script>

<!-- The cover's type. Identical over a painting, over a plate file and over the
     CSS plate — the only difference is what is behind it, and whether an emblem
     is down there to leave room for. -->
{#snippet plateType(reserveEmblem: boolean)}
	<div class="cover-type style-{style}" class:script-arabic={script === 'arabic'}
		class:script-devanagari={script === 'devanagari'}
		class:script-cyrillic={script === 'cyrillic'}>
		<!-- The byline takes no `lang`: an author's name is one row for every
		     edition (`Author` has no per-language name), so it is Latin on an
		     Arabic cover too, and claiming otherwise would tell a screen reader
		     to pronounce "Andrew Murray" as Arabic. -->
		<div class="byline" dir="auto">{book.author.name}</div>
		<!-- Title, rule and subtitle move as one block so the auto margins centre
		     THEM between the byline and the mark. Left as three siblings, the
		     leftover space split three ways and the title rode up the plate. -->
		<div class="middle">
			<!-- `lang` on the words themselves, not on the plate: it is what lets a
			     browser pick the right shaping and hyphenation for the title, and
			     what tells a screen reader which language to read it in. The
			     metrics come from the class above, which the LANGUAGE decides —
			     never the characters (see `scriptOf`). -->
			<div class="title" lang={book.language} dir="auto">{book.title}</div>
			<div class="rule"></div>
			{#if book.subtitle}<div class="subtitle" lang={book.language} dir="auto">
				{book.subtitle}
			</div>{/if}
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
			<div class="cover-plate over-file" class:over-art={isArt} role="img" aria-label={label}>
				{@render plateType(isPlate)}
			</div>
		{/if}
	{:else}
		<div
			class="cover-plate"
			style="--plate: {coverGradient(book.cover_color)}"
			role="img"
			aria-label={label}
		>
			{@render plateType(false)}
		</div>
	{/if}
</div>

