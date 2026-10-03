<script lang="ts" module>
	import { listFeaturedQuotes as fetchPool, type SavedQuote as Saved } from '$lib/library-public';

	// One fetch of the pool per page session: coming back to the home page
	// (from the reader, a tab switch) re-mounts this card, and the day's pick
	// doesn't change. A failed fetch isn't kept, so the next mount retries.
	let pending: Promise<Saved[]> | null = null;
	function todaysPool(): Promise<Saved[]> {
		pending ??= fetchPool().catch((e) => {
			pending = null;
			throw e;
		});
		return pending;
	}
</script>

<script lang="ts">
	import { onMount } from 'svelte';
	import { citeLine, quoteHref, type SavedQuote } from '$lib/library-public';
	import { dayIndex } from '$lib/quoteText';
	import { getLang } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import QuoteText from '$lib/components/QuoteText.svelte';

	/**
	 * The signed-in home's quotation of the day, set over a painting: the same
	 * pool and the same day's pick as the /quotes index's lead (FeaturedQuote),
	 * so the two agree on "today's line". Quotes are an English-only hub
	 * (contentNav ENGLISH_HUBS) — the pool is drawn from the English works — so
	 * this renders in English only, and nothing at all if the pool can't load.
	 *
	 * The painting turns over with the day too, from a few wordless grounds
	 * (CLAUDE.md, Covers) chosen for skies and light that sit well under text.
	 * It is decoration (alt=""). The painting shows clear in a fixed band at the
	 * top; the text always starts below that band, where the scrim is at full
	 * strength (--quote-scrim is measured in rem from the top, not as a share of
	 * the card), so a long quote that grows the card never climbs onto the sky.
	 */
	const t = i18n.t;

	const PAINTINGS = [
		'/covers/art/confessions-640.webp',
		'/covers/art/grace-abounding-640.webp',
		'/covers/art/absolute-surrender-640.webp',
		'/covers/art/all-of-grace-640.webp'
	];

	let quote = $state<SavedQuote | null>(null);
	const painting = PAINTINGS[dayIndex(new Date(), PAINTINGS.length)];

	onMount(() => {
		if (getLang() !== 'en') return;
		todaysPool()
			.then((pool) => {
				if (pool.length) quote = pool[dayIndex(new Date(), pool.length)];
			})
			.catch(() => {});
	});
</script>

{#if quote}
	<section class="page-col px-5 pt-14" aria-labelledby="home-quote-label">
		<div class="home-quote">
			<img src={painting} alt="" class="home-quote-art" use:hydrateSrc={{ src: painting }} />
			<div class="home-quote-scrim"></div>
			<div class="relative px-6 pb-6 pt-36 sm:px-10 sm:pb-10">
				<p id="home-quote-label" class="eyebrow home-quote-eyebrow mb-4">{t('quotes.featuredEyebrow')}</p>
				<figure class="m-0 flex flex-col gap-4">
					<blockquote class="home-quote-text font-display">“<QuoteText text={quote.text} />”</blockquote>
					<figcaption class="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-small">
						<a class="home-quote-author font-semibold" href={localizeHref(`/quotes/${quote.author.slug}/`)}
							>{quote.author.name}</a
						>
						<a class="home-quote-cite" href={quoteHref(quote)}>{citeLine(quote)}</a>
					</figcaption>
				</figure>
			</div>
		</div>
	</section>
{/if}

<style>
	.home-quote {
		position: relative;
		overflow: hidden;
		border-radius: var(--radius-card);
		background: var(--hero-ground);
	}
	.home-quote-art {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: cover;
		object-position: 50% 40%;
	}
	.home-quote-scrim {
		position: absolute;
		inset: 0;
		background: var(--quote-scrim);
	}
	.home-quote-eyebrow,
	.home-quote-cite {
		color: var(--hero-ink);
		opacity: 0.85;
	}
	.home-quote-text {
		margin: 0;
		max-width: 46rem;
		font-size: var(--fs-h2);
		line-height: 1.3;
		font-weight: 500;
		color: var(--hero-ink);
	}
	.home-quote-author {
		color: var(--hero-ink);
	}
</style>
