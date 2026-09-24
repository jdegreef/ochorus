<script lang="ts">
	import { coverGradient, coverSrcset, isArtCover, isPlateCover } from '$lib/coverArt';
	import { isLongTitle } from '$lib/coverCardMarkup';
	import { coverTitle } from '$lib/coverTitle';
	import { coverLayoutFor, typeTopFor } from '$lib/coverLayouts';
	import { groundBar } from '$lib/groundBars';
	import { scrimStrength } from '$lib/coverScrim';
	import { coverStyleFor, scriptOf, volumeNumeral } from '$lib/coverStyles';
	import { contentLang } from '$lib/reading';
	import { eraOf } from '$lib/eras';
	// The cover's whole drawing, in the one file that also feeds the share-card
	// script (see its header). Global rather than scoped, like app.css's other
	// component classes, and namespaced under `.cover-*` so it cannot collide.
	import './cover-type.css';
	import type { CoverBook } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';
	import { hydrateSrc, type ImgSource } from '$lib/hydrateSrc';
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
		book: CoverBook;
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
	// The loaded cover's intrinsic aspect, and the url it was measured for. A
	// designed cover composed narrower (or wider) than 3:4 is matted below so
	// `object-cover` cannot crop its baked-in byline and mark; that decision is
	// keyed by url for the same reason `loaded`/`failed` are — SvelteKit reuses
	// one BookCover across books, and a ratio measured for A must not mat B.
	let ratioUrl = $state('');
	let ratio = $state(0);
	const loaded = $derived(loadedUrl === book.cover_url);
	const failed = $derived(failedUrl === book.cover_url);

	/** What a cover that has loaded tells us: that it is here (the placeholder
	 *  can go), and its shape (whether a designed cover needs its mat). */
	function onLoaded(img: HTMLImageElement) {
		loadedUrl = book.cover_url;
		if (img.naturalHeight) {
			ratio = img.naturalWidth / img.naturalHeight;
			ratioUrl = book.cover_url;
		}
	}

	/**
	 * Run `onLoaded` for an image that finished BEFORE this component hydrated.
	 *
	 * These pages are prerendered, so a cover's `<img>` is in the HTML and the
	 * browser fetches it long before the scripts arrive — often it has finished,
	 * and fired its `load` event, before Svelte attaches `onload`. That event is
	 * gone; nothing replays it. Measured on /books/: the first-row cover loaded
	 * at 1.0s and was only seen as loaded at 2.3s, when the grid re-rendered.
	 * So on attach, an image that is already complete is treated as loaded now.
	 */
	function whenComplete(img: HTMLImageElement, source: ImgSource) {
		// Repoint FIRST, in the same action rather than a second one beside it:
		// a cover prerendered for another book must not be measured as this one's.
		// Two actions would make that depend on the order Svelte attaches them.
		const repoint = hydrateSrc(img, source);
		if (img.complete && img.naturalWidth) onLoaded(img);
		return repoint;
	}

	// The two grounds that carry no words and want type over them. A DESIGNED
	// raster (the ministry titles, `/covers/<slug>.jpg`) is excluded by both:
	// its words are in the file, and a second set over them would be a mess.
	const isArt = $derived(isArtCover(book.cover_url));
	const isPlate = $derived(isPlateCover(book.cover_url));
	const overFile = $derived(isArt || isPlate);
	// A designed raster: a cover file that is neither a painting nor a plate
	// ground, so its words are IN the pixels and nothing is drawn over it.
	const isDesigned = $derived(!!book.cover_url && !overFile);
	// A designed cover is composed at the artwork's OWN aspect, not always 3:4:
	// the byline sits near the top edge and the Ochorus mark near the foot, and
	// `object-cover` on an off-3:4 file scales it to fill the card and crops
	// exactly those. So one that isn't 3:4 is CONTAINED whole (no crop) and the
	// 3:4 remainder filled by a blurred, dimmed copy of itself — a soft mat that
	// reads as intentional. One already 3:4 fills the card as it always has and
	// gets no mat; the grounds above are drawn at 3:4 to be covered, never here.
	const needsMat = $derived(
		isDesigned && ratioUrl === book.cover_url && Math.abs(ratio - 3 / 4) > 0.01
	);
	/** The cover's `src`/`srcset`, stated once for the markup and the action
	 *  that keeps them on this book (see `$lib/hydrateSrc`). */
	const source = $derived({ src: book.cover_url, srcset: coverSrcset(book.cover_url) || undefined });
	const label = $derived(`${t('a11y.coverOf')} ${book.title}`);
	const setTitle = $derived(coverTitle(book));

	/** The author's house style — a class name; `cover-type.css` holds the rest. */
	const style = $derived(
		coverStyleFor(eraOf(book.author.birth_year), book.author.slug, book.slug)
	);
	/** This edition's language as a browser will accept it. `en-modern` is
	 *  Ochorus' own edition marker, not a BCP-47 subtag, so a browser drops it
	 *  whole and shapes the title in the UI locale instead — which is the defect
	 *  `contentLang` exists for, and every other content-language attribute in
	 *  the app already goes through it. */
	const lang = $derived(contentLang(book.language));
	/** The script whose metrics this edition needs correcting for; null for
	 *  Latin. The FACE needs no class — app.css's stacks fall back per glyph. */
	const script = $derived(scriptOf(lang));
	/** This book's place in its series, in its edition's digits; null outside one. */
	const volume = $derived(volumeNumeral(book.series_position, lang));
	/** `dir="rtl"` on an Arabic edition's type block, and NO attribute at all
	 *  otherwise — a spread rather than `dir={…}`, which Svelte writes as the
	 *  `dir` property and so leaves `dir=""` behind on every other cover. */
	const blockDir = $derived(script === 'arabic' ? { dir: 'rtl' as const } : {});
	/** The layout a painting is composed in (`coverLayouts.ts`); null for the
	 *  framed composition, and always null off a painting. */
	const layout = $derived(isArt ? coverLayoutFor(book.author.slug, script, book.slug) : null);
	/** How far a laid-out painting is cropped to clear its scan border
	 *  (`groundBars.ts`). The framed scrim hides the border, so only a layout
	 *  asks. */
	const bar = $derived(layout ? groundBar(book.cover_url) : 0);
</script>

<!-- The cover's type. Identical over a painting, over a plate file and over the
     CSS plate — the only difference is what is behind it, and whether an emblem
     is down there to leave room for. -->
{#snippet plateType(reserveEmblem: boolean)}
	<!-- `script` IS the class suffix, so it is used as one rather than compared
	     against three times; a falsy entry is dropped, so a Latin cover emits no
	     script class at all and the fourth script is a table entry, not an edit
	     here. -->
	<!-- Right-to-left for an Arabic edition: the title sets its own direction,
	     but the Latin byline and the wordless rule take the block's, so a layout
	     that ranges its type to the start edge would otherwise split them
	     across both sides. `coverTypeMarkup` does the same. -->
	<div
		class={[
			'cover-type',
			`style-${style}`,
			script && `script-${script}`,
			isLongTitle(setTitle) && 'long-title',
			isArt && typeTopFor(book.slug, layout) && 'type-top'
		]}
		{...blockDir}
	>
		<!-- The byline takes no `lang`: an author's name is one row for every
		     edition (`Author` has no per-language name), so it is Latin on an
		     Arabic cover too, and claiming otherwise would tell a screen reader
		     to pronounce "Andrew Murray" as Arabic. -->
		<div class="byline" dir="auto">{book.author.name}</div>
		<!-- Title, rule and subtitle move as one block so the auto margins centre
		     THEM between the byline and the mark. Left as three siblings, the
		     leftover space split three ways and the title rode up the plate. -->
		<div class="middle">
			<!-- A series volume rides with the title block, so the auto margins
			     centre the numeral and the words together. -->
			{#if volume}<div class="volume" {lang}>{volume}</div>{/if}
			<!-- `lang` on the words themselves, not on the plate: it is what lets
			     a browser shape and hyphenate the title correctly. NOT an
			     accessibility win, though it looks like one — the plate is
			     `role="img"` with an `aria-label`, so a screen reader never
			     reaches these nodes and reads the label instead. The metrics come
			     from the class above, which the LANGUAGE decides — never the
			     characters (see `scriptOf`). -->
			<div class="title" {lang} dir="auto">{setTitle}</div>
			<div class="rule"></div>
			{#if book.subtitle}<div class="subtitle" {lang} dir="auto">
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
		<!-- The placeholder sits UNDER the image, not instead of it: an image
		     paints the moment it decodes and covers it, with no script involved.
		     It used to be the other way round — every cover held at opacity 0
		     until an `onload` handler revealed it — which on a prerendered shelf
		     meant a cover that had arrived at 1.0s stayed invisible until
		     hydration re-rendered the grid at 2.3s, and the page's LCP waited
		     with it. `loaded` now only retires the pulse, which would otherwise
		     animate under every cover forever. -->
		{#if !loaded && !priority}
			<div class="absolute inset-0 animate-pulse bg-surface-2"></div>
		{/if}
		<img
			src={source.src}
			srcset={source.srcset}
			alt={overFile ? '' : label}
			loading={priority ? 'eager' : 'lazy'}
			fetchpriority={priority ? 'high' : undefined}
			width={priority ? 300 : undefined}
			height={priority ? 400 : undefined}
			onload={(e) => onLoaded(e.currentTarget as HTMLImageElement)}
			onerror={() => (failedUrl = book.cover_url)}
			use:whenComplete={source}
			style={bar ? `--ground-bar: ${bar}` : undefined}
			class="cover-ground absolute inset-0 h-full w-full {needsMat
				? 'object-contain'
				: 'object-cover'}"
		/>
		{#if needsMat}
			<!-- The mat: the same cover, cover-filled, blurred and dimmed, behind the
			     contained one so the off-3:4 remainder is a soft continuation of the
			     art rather than a bare bar. `-z-10` puts it behind the foreground the
			     contained image lets show through; `scale-110` hides the blur's
			     transparent bleed at the edges. Decorative — the foreground `<img>`
			     already carries the label — and after it in the DOM so the real cover
			     stays `querySelector('img')`. -->
			<img
				src={source.src}
				srcset={source.srcset}
				use:hydrateSrc={source}
				alt=""
				aria-hidden="true"
				loading={priority ? 'eager' : 'lazy'}
				class="absolute inset-0 -z-10 h-full w-full scale-110 object-cover blur-xl brightness-[.82]"
			/>
		{/if}
		{#if overFile}
			<!-- The ground carries no words, so the cover's type is drawn here —
			     one shared image, a title per language. -->
			<!-- `--scrim-strength` only reaches a painting: the scrim it scales is on
			     `.over-art`, and a plate has none. Measured per work rather than
			     chosen, because how much darkening a picture needs is a property of
			     the picture — the library spans 0.30x to 1.00x, and one strength for
			     all of them has to be the palest one's. -->
			<!-- A layout's classes ride on the plate, beside the scrim they replace;
			     `cover-ground` above is how a layout moves the painting into its
			     window. The order matches `coverPlateMarkup`, which the parity gate
			     compares against. -->
			<div
				class={[
					'cover-plate over-file',
					isArt && 'over-art',
					book.subtitle && 'has-subtitle',
					layout && ['has-layout', `cover-layout-${layout.layout}`, `cover-hue-${layout.hue}`]
				]}
				style={isArt ? `--scrim-strength: ${scrimStrength(book.slug)}` : undefined}
				role="img"
				aria-label={label}
			>
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

