<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { isArtCover } from '$lib/coverArt';
	import { cachedResumeBooks, knownAbsent, libraryBooks, unfinishedBookSlugs } from '$lib/resumeBooks';
	import { workSlugKey } from '$lib/reading-schema';
	import { getLang } from '$lib/lang.svelte';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { i18n } from '$lib/i18n.svelte';
	import { liturgicalSeason, SEASON_COLOUR } from '$lib/liturgical';
	import Fleuron from '$lib/components/Fleuron.svelte';

	/**
	 * The signed-in home's painted hero: the greeting set over the painting the
	 * reader is living in — the wordless ground (`/covers/art/…`) of the book
	 * they most recently opened and haven't finished, i.e. the first card of
	 * "Continue reading" below it. The book's own `cover_url` decides, read from
	 * the same shared lists that strip uses (`$lib/resumeBooks`), so the two
	 * agree on which book is current, a book this language lacks is skipped,
	 * and a plate-covered book asks for no painting that doesn't exist. Anything
	 * without a painting — a plate, a sermon, no reading yet — gets DEFAULT_ART.
	 *
	 * Picked at creation from the cache (the dashboard renders client-side only),
	 * so a returning reader's first paint is already theirs; corrected when the
	 * full list lands, and again on `ochorus:sync` when the sign-in merge brings
	 * in progress from the account.
	 *
	 * The scrim runs from the foot, where the text sits, rather than from one
	 * side, so it needs no mirroring in a right-to-left locale; the framed plate
	 * sits at the inline end, so it moves to the left there on its own. The
	 * painting is decoration (alt=""); the greeting is the page's <h1>.
	 *
	 * The scrim is the reader's palette, deepened (--hero-tint), over a wash
	 * that drifts very slowly — still under prefers-reduced-motion — with the
	 * page's paper grain laid over it, so the band reads as a canvas. The date
	 * line names the season of the Church year beside the civil date, with a
	 * dot in its liturgical colour.
	 */
	let { greeting }: { greeting: string } = $props();

	// Van Gogh's cypresses (the Absolute Surrender ground): green, sky and a
	// moon — legible under the scrim, and warm in every theme.
	const DEFAULT_ART = '/covers/art/absolute-surrender-640.webp';

	/** The current book's painting from `books`, null if it has none there. */
	function paintingOf(books: { slug: string; cover_url: string | null }[]): string | null {
		const lang = getLang();
		const absent = knownAbsent(lang);
		const slug = unfinishedBookSlugs().find((s) => !absent.has(workSlugKey('book', s)));
		if (!slug) return null;
		const url = books.find((b) => b.slug === slug)?.cover_url;
		return url && isArtCover(url) ? url : null;
	}

	let art = $state(browser ? (paintingOf(cachedResumeBooks(getLang())) ?? DEFAULT_ART) : DEFAULT_ART);

	function repick() {
		const lang = getLang();
		const cached = paintingOf(cachedResumeBooks(lang));
		if (cached) art = cached;
		if (!unfinishedBookSlugs().length) return;
		libraryBooks(lang)
			.then((books) => (art = paintingOf(books) ?? DEFAULT_ART))
			.catch(() => {});
	}

	onMount(() => {
		repick();
		window.addEventListener('ochorus:sync', repick);
		return () => window.removeEventListener('ochorus:sync', repick);
	});

	const fallBack = () => (art = DEFAULT_ART);

	const today = new Intl.DateTimeFormat(getLang(), {
		weekday: 'long',
		day: 'numeric',
		month: 'long'
	}).format(new Date());

	const season = liturgicalSeason(new Date());
	const seasonName = i18n.t(`liturgical.${season}`);
</script>

<section class="home-hero">
	<!-- The painting twice: blurred and scaled as the band's colour (a 600px
	     ground stretched to the page width only reads as a smear), and whole,
	     sharp and framed beside the greeting, where it is seen at its own size. -->
	<img
		src={art}
		alt=""
		class="home-hero-wash"
		use:hydrateSrc={{ src: art }}
		onerror={fallBack}
	/>
	<div class="home-hero-scrim"></div>
	<div class="home-hero-grain"></div>
	<div class="page-col relative flex items-end justify-between gap-8 px-5 pb-10 pt-16 sm:pb-12 sm:pt-20">
		<div class="min-w-0">
			<p class="eyebrow home-hero-date mb-3">
				{today}<span class="home-hero-season"
					><span class="home-hero-season-dot season-{SEASON_COLOUR[season]}" aria-hidden="true"></span>{seasonName}</span
				>
			</p>
			<h1 class="text-display home-hero-ink">{greeting}</h1>
			<div class="mt-4"><Fleuron /></div>
		</div>
		<span class="home-hero-frame">
			<img
				src={art}
				alt=""
				class="home-hero-plate"
				use:hydrateSrc={{ src: art }}
				onerror={fallBack}
			/>
		</span>
	</div>
</section>

<style>
	.home-hero {
		position: relative;
		overflow: hidden;
		background: var(--hero-ground);
	}
	.home-hero-wash {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: cover;
		/* Blurred enough to lose the 640px source's pixels at page width, not so
		   much that the painting's shapes go: its light still reads through. */
		filter: blur(18px) saturate(1.3);
		transform: scale(1.18);
		animation: home-hero-drift 60s ease-in-out infinite alternate;
	}
	/* A slow drift across the painting — a minute each way, too slow to watch,
	   enough that the band is never quite still. */
	@keyframes home-hero-drift {
		from {
			transform: scale(1.18) translate3d(-1.5%, 0, 0);
		}
		to {
			transform: scale(1.26) translate3d(1.5%, -2%, 0);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.home-hero-wash {
			animation: none;
		}
	}
	.home-hero-scrim,
	.home-hero-grain {
		position: absolute;
		inset: 0;
	}
	.home-hero-scrim {
		background: var(--hero-scrim);
	}
	/* The page's paper tooth (the light specks .night-band uses in every
	   theme), so the band reads as canvas rather than a screen gradient. */
	.home-hero-grain {
		background-image: var(--grain-light-specks);
		opacity: 0.7;
		pointer-events: none;
	}
	/* The painting framed like a print in a gallery: a gilt fillet, a cream
	   mat, a hairline of gilt again where the mat meets the picture. */
	.home-hero-frame {
		display: none;
		flex-shrink: 0;
		width: 11rem;
		padding: 0.55rem;
		background: var(--hero-mat);
		border-radius: 3px;
		box-shadow:
			0 0 0 2px var(--hero-gilt),
			0 0 0 3px var(--hero-gilt-deep),
			var(--hero-plate-shadow);
	}
	.home-hero-plate {
		display: block;
		width: 100%;
		aspect-ratio: 3 / 4;
		object-fit: cover;
		border: 1px solid var(--hero-gilt);
		box-shadow: 0 0 0 1px var(--hero-gilt-deep);
	}
	@media (min-width: 640px) {
		.home-hero-frame {
			display: block;
		}
	}
	.home-hero-ink {
		color: var(--hero-ink);
		text-shadow: 0 2px 18px rgb(0 0 0 / 0.35);
	}
	.home-hero-date {
		color: var(--hero-ink);
	}
	/* The season of the Church year, after the date: a hairline separator, the
	   season's liturgical colour as a dot, its name. */
	.home-hero-season {
		display: inline-flex;
		align-items: center;
		gap: 0.45em;
		margin-inline-start: 0.75em;
		padding-inline-start: 0.75em;
		border-inline-start: 1px solid color-mix(in srgb, var(--hero-ink) 45%, transparent);
	}
	.home-hero-season-dot {
		width: 0.55em;
		height: 0.55em;
		border-radius: 50%;
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--hero-ink) 18%, transparent);
	}
	.season-violet {
		background: var(--season-violet);
	}
	.season-white {
		background: var(--season-white);
	}
	.season-red {
		background: var(--season-red);
	}
	.season-green {
		background: var(--season-green);
	}
</style>
