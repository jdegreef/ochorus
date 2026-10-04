<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { isArtCover } from '$lib/coverArt';
	import { cachedResumeBooks, knownAbsent, libraryBooks, unfinishedBookSlugs } from '$lib/resumeBooks';
	import { workSlugKey } from '$lib/reading-schema';
	import { getLang } from '$lib/lang.svelte';
	import { hydrateSrc } from '$lib/hydrateSrc';
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
	<div class="page-col relative flex items-end justify-between gap-8 px-5 pb-10 pt-16 sm:pb-12 sm:pt-20">
		<div class="min-w-0">
			<p class="eyebrow home-hero-date mb-3">{today}</p>
			<h1 class="text-display home-hero-ink">{greeting}</h1>
			<div class="mt-4"><Fleuron /></div>
		</div>
		<img
			src={art}
			alt=""
			class="home-hero-plate"
			use:hydrateSrc={{ src: art }}
			onerror={fallBack}
		/>
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
		filter: blur(28px) saturate(1.15);
		transform: scale(1.2);
	}
	.home-hero-scrim {
		position: absolute;
		inset: 0;
		background: var(--hero-scrim);
	}
	.home-hero-plate {
		display: none;
		flex-shrink: 0;
		width: 11rem;
		aspect-ratio: 3 / 4;
		object-fit: cover;
		border-radius: 4px;
		border: 4px solid var(--hero-ink);
		box-shadow: var(--hero-plate-shadow);
		transform: rotate(2deg);
	}
	@media (min-width: 640px) {
		.home-hero-plate {
			display: block;
		}
	}
	.home-hero-ink {
		color: var(--hero-ink);
	}
	.home-hero-date {
		color: var(--hero-ink);
	}
</style>
