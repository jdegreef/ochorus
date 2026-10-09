<script lang="ts">
	import { onMount } from 'svelte';
	import { isArtCover } from '$lib/coverArt';
	import { isPaleGround } from '$lib/groundBars';
	import type { ResumeBook } from '$lib/resumeItems';
	import { offerFinish } from '$lib/progress';
	import { localizeHref } from '$lib/href';
	import { getLang } from '$lib/lang.svelte';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { i18n } from '$lib/i18n.svelte';
	import { liturgicalSeason, SEASON_COLOUR } from '$lib/liturgical';
	import { artCredit, SEASON_ART, type ArtCredit } from '$lib/heroArt';
	import { localDayNumber } from '$lib/dailyArticles';
	import { dayPart } from '$lib/greeting';
	import * as m from '$lib/paraglide/messages.js';
	import Fleuron from '$lib/components/Fleuron.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import { chapterMeter } from '$lib/components/WorkCard.svelte';

	/**
	 * The signed-in home's painted hero: the greeting set over a painting —
	 * the ground (`/covers/art/…`) of the book the reader is in, else the
	 * season's (SEASON_ART) — blurred across the band as its colour.
	 *
	 * With a book in progress (`current`, decided once by HomeDashboard through
	 * `$lib/currentBook.svelte`, which also has "Continue reading" below leave
	 * it out) the hero is its resume point: the book's own cover, TITLED (a
	 * bare `/covers/art/` ground is wordless on purpose and, hung alone, read
	 * as a blank page), linked back to the chapter, beside a resume block under
	 * the greeting — title, author, meter and a Continue button. A plate
	 * cover has no painting to wash, so the band takes the season's. With no
	 * book in progress, the season's painting hangs in the frame instead,
	 * labelled on the mat with the museum's own credit.
	 *
	 * A PALE ground (misty whites, a flower border on cream — `PALE_GROUNDS`,
	 * measured at build time) is not washed across the band: blurred and
	 * scrimmed it came out as grey-brown mud. The band is the reader's tint.
	 *
	 * The scrim runs from the foot, where the text sits, rather than from one
	 * side, so it needs no mirroring in a right-to-left locale; the cover or
	 * frame sits at the inline end, so it moves to the left there on its own.
	 * The painting is decoration (alt=""); the greeting is the page's <h1>.
	 * With nothing in progress, the resume block's place offers the library.
	 *
	 * The scrim is the reader's palette, deepened (--hero-tint), over a wash
	 * that drifts very slowly — still under prefers-reduced-motion — with the
	 * page's paper grain laid over it, so the band reads as a canvas. The date
	 * line names the season of the Church year beside the civil date, with a
	 * dot in its liturgical colour.
	 */
	let { name, current }: { name: string; current: ResumeBook | null } = $props();
	const t = i18n.t;

	// The date, season and greeting turn over with the reader's day, so a tab
	// left open overnight is right when the reader comes back to it (as
	// HomeArticles below re-picks its shelf).
	let now = $state(new Date());
	const today = $derived(
		new Intl.DateTimeFormat(getLang(), { weekday: 'long', day: 'numeric', month: 'long' }).format(now)
	);
	const season = $derived(liturgicalSeason(now));
	const seasonArt = $derived(SEASON_ART[season]);

	// The current book's painting washes the band; a plate, or a painting that
	// failed to load, leaves it to the season's.
	let broken = $state<string | null>(null);
	const bookArt = $derived(current && isArtCover(current.book.cover_url) ? current.book.cover_url : null);
	const art = $derived(bookArt && bookArt !== broken ? bookArt : seasonArt);
	const pale = $derived(isPaleGround(art));

	const href = $derived(current ? localizeHref(current.href) : '');
	const meter = $derived(current ? chapterMeter(current.order, current.chapterCount, current.pct) : '');

	// The museum's label for the season's painting, lettered on the mat like
	// a gallery print — only while the frame hangs (no book in progress). The
	// frame (and so the label) is hidden on a phone; a painting with no
	// curated entry hangs unlabelled.
	let label = $state<ArtCredit | null>(null);
	$effect(() => {
		const url = seasonArt;
		label = null;
		if (current) return;
		artCredit(url).then((c) => {
			if (seasonArt === url) label = c;
		});
	});

	// "Good evening, James" — for the time of the reader's day, on the same
	// clock as the date, so the two never disagree. Parameterised so the name
	// sits where each language wants it (Paraglide's message functions, not
	// the param-free t() facade); a plain greeting when there is no name to
	// use (greetingName returns '' rather than an email handle).
	const GREETING = {
		morning: { named: m.home_good_morning_named, bare: m.home_good_morning },
		afternoon: { named: m.home_good_afternoon_named, bare: m.home_good_afternoon },
		evening: { named: m.home_good_evening_named, bare: m.home_good_evening }
	};
	const greeting = $derived.by(() => {
		const g = GREETING[dayPart(now.getHours(), getLang())];
		return name ? g.named({ name }) : g.bare();
	});

	// The leaf draws itself on the first time the dashboard opens in a
	// session — not on every return to it. The flag is spent on mount, so a
	// reader who loses it (reduced motion, hero offscreen) just sees it drawn.
	const DRAWN_KEY = 'ochorus:hero-leaf-drawn';
	const drawIn = (() => {
		try {
			if (sessionStorage.getItem(DRAWN_KEY)) return false;
			sessionStorage.setItem(DRAWN_KEY, '1');
			return true;
		} catch {
			return false;
		}
	})();

	let hero: HTMLElement;
	let offscreen = $state(false);

	onMount(() => {
		// A new day, or a new part of it: the date, season and greeting follow.
		const turn = (x: Date) => `${localDayNumber(x)}:${dayPart(x.getHours(), getLang())}`;
		const onVisible = () => {
			if (document.visibilityState !== 'visible') return;
			const d = new Date();
			if (turn(d) !== turn(now)) now = d;
		};
		document.addEventListener('visibilitychange', onVisible);
		// The drift is paused while the hero is scrolled away: nobody sees it,
		// and an endless animation keeps the compositor awake for the whole
		// visit to the dashboard.
		const io = new IntersectionObserver(([e]) => (offscreen = !e.isIntersecting));
		io.observe(hero);
		return () => {
			document.removeEventListener('visibilitychange', onVisible);
			io.disconnect();
		};
	});
</script>

<section class="home-hero" class:offscreen class:pale bind:this={hero}>
	<!-- The painting twice: blurred and scaled as the band's colour (a 600px
	     ground stretched to the page width only reads as a smear), and whole,
	     sharp and framed beside the greeting, where it is seen at its own size.
	     A pale ground is not washed at all: the band is the tint (.pale). -->
	{#if !pale}
		<div class="home-hero-drift">
			<img
				src={art}
				alt=""
				class="home-hero-wash"
				use:hydrateSrc={{ src: art }}
				onerror={() => (broken = bookArt)}
			/>
		</div>
	{/if}
	<div class="home-hero-scrim"></div>
	<div class="home-hero-grain"></div>
	<div class="page-col relative flex items-end justify-between gap-8 px-5 pb-8 pt-9 sm:pb-9 sm:pt-11">
		<div class="min-w-0">
			<p class="eyebrow home-hero-date mb-3">
				{today}<span class="sr-only">, </span><span class="home-hero-season"
					><span class="home-hero-season-dot" style:background="var(--season-{SEASON_COLOUR[season]})" aria-hidden="true"
					></span>{i18n.t(`liturgical.${season}`)}</span
				>
			</p>
			<h1 class="text-display home-hero-ink">{greeting}</h1>
			<div class="mt-4"><Fleuron {drawIn} /></div>
			{#if current}
				<div class="home-hero-resume mt-6">
					<p class="eyebrow home-hero-date">{t('continue.title')}</p>
					<a {href} class="home-hero-ink mt-1.5 block font-display text-h3 font-semibold">{current.title}</a>
					<p class="home-hero-sub mt-0.5 text-small">{current.author}</p>
					<div class="mt-3 flex items-center gap-4">
						<a {href} class="btn btn-sm home-hero-cta">{t('book.continue')}</a>
						<div class="min-w-0 flex-1">
							<!-- Done with it, or done with it elsewhere: finish it from here,
							     as its card in "Continue reading" offered (with an Undo). -->
							<div class="flex items-baseline justify-between gap-3">
								<p class="home-hero-sub text-micro">{meter}</p>
								<button
									type="button"
									class="home-hero-sub home-hero-finish text-micro"
									aria-label="{t('continue.markFinished')}: {current.title}"
									onclick={() => current && offerFinish(current.slug)}>{t('continue.markFinished')}</button
								>
							</div>
							<div class="home-hero-meter mt-1">
								<ProgressBar percent={current.pct} label="{current.title}: {meter}" />
							</div>
						</div>
					</div>
				</div>
			{:else}
				<!-- Nothing open: a way on, so the band is never just a greeting
				     over an empty middle (Continue reading below is empty too). -->
				<div class="home-hero-resume mt-6">
					<p class="home-hero-sub text-small">{t('home.discoverNext')}</p>
					<a href={localizeHref('/books')} class="btn btn-sm home-hero-cta mt-3">{t('home.browseLibrary')}</a>
				</div>
			{/if}
		</div>
		{#if current}
			<!-- The book itself, titled, as a way back in. Decorative to a screen
			     reader beside the titled link above (tabindex -1, aria-hidden): one
			     link per destination in the reading order. -->
			<a {href} class="home-hero-book" tabindex="-1" aria-hidden="true">
				<BookCover book={current.book} rounded="rounded-sm" />
			</a>
		{:else}
			<span class="home-hero-frame">
				<img src={seasonArt} alt="" class="home-hero-plate" use:hydrateSrc={{ src: seasonArt }} />
				{#if label}
					<span class="home-hero-label" title={label.credit}
						>{label.artist}<br /><i>{label.title}</i>{label.year ? `, ${label.year}` : ''}</span
					>
				{/if}
			</span>
		{/if}
	</div>
</section>

<style>
	.home-hero {
		position: relative;
		overflow: hidden;
		background: var(--hero-ground);
	}
	/* The drift moves this wrapper, not the blurred image inside it: the blur
	   is then drawn once into the wrapper's layer and the compositor only
	   slides the bitmap, rather than re-running the filter every frame. */
	.home-hero-drift {
		position: absolute;
		inset: 0;
		animation: home-hero-drift 60s ease-in-out infinite alternate;
	}
	.offscreen .home-hero-drift {
		animation-play-state: paused;
	}
	.home-hero-wash {
		width: 100%;
		height: 100%;
		object-fit: cover;
		/* Blurred enough to lose the 640px source's pixels at page width, not so
		   much that the painting's shapes go: its light still reads through.
		   Saturated and lifted, so its colour survives the scrim rather than
		   settling into a murky dark (the scrim, not the wash, holds the text's
		   contrast — palettes.test.ts measures it against a WHITE painting). */
		filter: blur(18px) saturate(1.6) brightness(1.15);
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
		.home-hero-drift {
			animation: none;
			transform: scale(1.18);
		}
	}
	/* A pale painting is not washed across the band (see the header): the
	   band is the reader's tint, lit a little from the top so it reads as a
	   ground, not a flat fill. */
	.pale {
		background:
			radial-gradient(ellipse 90% 120% at 50% 0%, color-mix(in srgb, var(--hero-tint) 72%, var(--hero-ink)) 0%, transparent 70%),
			var(--hero-tint);
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
		width: 9.5rem;
		padding: 0.5rem;
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
	/* The museum's label, lettered on the mat under the picture, small, in
	   the mat's own ink (app.css --hero-mat-ink). */
	.home-hero-label {
		display: block;
		margin-top: 0.45rem;
		font-size: var(--fs-micro);
		line-height: 1.3;
		color: var(--hero-mat-ink);
		text-align: center;
		overflow-wrap: anywhere;
	}
	/* The book in progress, titled, standing in the frame's place: a cover
	   lifted off the band, not matted — it is a book to open, not a print. */
	.home-hero-book {
		display: none;
		flex-shrink: 0;
		width: 8.5rem;
		box-shadow: var(--hero-plate-shadow);
		border-radius: var(--radius-sm);
		transition: transform var(--duration-fast) ease;
	}
	.home-hero-book:hover {
		transform: translateY(-3px);
	}
	@media (min-width: 640px) {
		.home-hero-frame,
		.home-hero-book {
			display: block;
		}
	}
	.home-hero-resume {
		max-width: 26rem;
	}
	.home-hero-sub {
		color: color-mix(in srgb, var(--hero-ink) 80%, transparent);
	}
	/* The button in the mat's cream and ink — the frame's own pair, measured
	   by palettes.test.ts — so it belongs to the hero in every palette. */
	.home-hero-cta {
		background: var(--hero-mat);
		color: var(--hero-mat-ink);
		border-color: var(--hero-gilt);
	}
	.home-hero-cta:hover {
		text-decoration: none;
		border-color: var(--hero-gilt-deep);
	}
	.home-hero-finish:hover,
	.home-hero-finish:focus-visible {
		color: var(--hero-ink);
		text-decoration: underline;
	}
	/* The meter on the dark band: an ink track, a gilt fill. */
	.home-hero-meter :global(.track) {
		background: var(--hero-ink-faint);
	}
	.home-hero-meter :global(.fill) {
		background: var(--hero-gilt);
	}
	.home-hero-ink {
		color: var(--hero-ink);
		text-shadow: var(--hero-ink-shadow);
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
		border-inline-start: 1px solid var(--hero-rule);
	}
	.home-hero-season-dot {
		width: 0.55em;
		height: 0.55em;
		border-radius: 50%;
		box-shadow: 0 0 0 2px var(--hero-ink-faint);
	}
</style>
