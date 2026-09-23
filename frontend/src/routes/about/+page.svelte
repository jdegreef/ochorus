<script lang="ts">
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { SITE_URL } from '$lib/config';
	import { hreflangAll, jsonLd } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { LIVE_LOCALES } from '$lib/live-locales.generated';
	import Seo from '$lib/components/Seo.svelte';

	const t = i18n.t;

	const path = '/about';
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);

	// The number of languages a reader can actually read Ochorus in — the LIVE
	// (advertised) locales, so the stat is always true and never hand-counted.
	const languageCount = LIVE_LOCALES.length;

	// The "from the page to the field" gallery. Captions double as each image's
	// accessible name — the figure describes the photo, so alt repeats it rather
	// than inventing a second description that could drift.
	// The outreach gallery. Uniform aspect per row (two wide, three portrait,
	// three landscape) so the grid never leaves ragged gaps; `span` carries the
	// column count at mobile (2-col) and sm+ (6-col). Captions double as alt text.
	// `pos` overrides the object-position for a portrait source whose subject sits
	// off-centre, so object-cover keeps them in frame instead of trimming to centre.
	const field: { img: string; cap: string; span: string; aspect: string; pos?: string }[] = [
		{ img: 'gate', cap: 'about.capGate', span: 'col-span-2 sm:col-span-3', aspect: 'aspect-video' },
		{ img: 'matugga-read', cap: 'about.capMatugga', span: 'col-span-2 sm:col-span-3', aspect: 'aspect-video' },
		{ img: 'handover', cap: 'about.capHandover', span: 'col-span-1 sm:col-span-2', aspect: 'aspect-[3/4]' },
		{ img: 'teacher-standing', cap: 'about.capTeacher', span: 'col-span-1 sm:col-span-2', aspect: 'aspect-[3/4]' },
		{ img: 'staff-seated', cap: 'about.capStaff', span: 'col-span-1 sm:col-span-2', aspect: 'aspect-[3/4]' },
		{ img: 'school', cap: 'about.capSchool', span: 'col-span-1 sm:col-span-2', aspect: 'aspect-[4/3]' },
		// The source is a near-square 3:4 portrait: his face fills the top and the
		// books the bottom, so a 4:3 crop trimmed both. A 15/14 box holds the whole
		// subject, and a top-biased position keeps his full face in frame.
		{
			img: 'soar',
			cap: 'about.capSoar',
			span: 'col-span-1 sm:col-span-2',
			aspect: 'aspect-[15/14]',
			pos: 'object-[center_30%]'
		},
		{ img: 'murray-table', cap: 'about.capMurray', span: 'col-span-1 sm:col-span-2', aspect: 'aspect-[4/3]' }
	];

	// The printed original, shown as a box + cover + interior spread.
	const featureShots = [
		{ img: 'book-box', alt: 'about.featureAltBox', cls: 'col-span-2 aspect-[3/2]' },
		{ img: 'book-cover', alt: 'about.featureAltCover', cls: 'aspect-[3/4]' },
		{ img: 'book-interior', alt: 'about.featureAltInterior', cls: 'aspect-[3/4]' }
	];

	// Lightbox: any photo opens large in a native <dialog> (free Escape-to-close,
	// backdrop, focus handling). Prerender-safe — the dialog is empty until opened.
	let dialogEl = $state<HTMLDialogElement | null>(null);
	let lightbox = $state<{ src: string; cap: string } | null>(null);
	function openLightbox(src: string, cap: string) {
		lightbox = { src, cap };
		dialogEl?.showModal();
	}

	// Count-up: a stat's final value is already in the DOM (so prerender / no-JS /
	// reduced-motion all show the real number); this animates from 0 to it once,
	// when the tile scrolls into view, then restores the exact string. Parses an
	// optional prefix ($) and suffix (+) and keeps thousands separators.
	function countUp(node: HTMLElement, value: string) {
		if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
		const m = value.match(/^(\D*)([\d,]+)(\D*)$/);
		if (!m) return;
		const [, prefix, digits, suffix] = m;
		const target = Number(digits.replace(/,/g, ''));
		const grouped = digits.includes(',');
		const fmt = (v: number) => prefix + (grouped ? v.toLocaleString('en-US') : String(v)) + suffix;
		let raf = 0;
		const io = new IntersectionObserver(
			(entries) => {
				if (!entries[0].isIntersecting) return;
				io.disconnect();
				const start = performance.now();
				const tick = (now: number) => {
					const p = Math.min(1, (now - start) / 900);
					node.textContent = fmt(Math.round(target * (1 - Math.pow(1 - p, 3))));
					if (p < 1) raf = requestAnimationFrame(tick);
					else node.textContent = value;
				};
				raf = requestAnimationFrame(tick);
			},
			{ threshold: 0.5 }
		);
		io.observe(node);
		return {
			destroy() {
				io.disconnect();
				if (raf) cancelAnimationFrame(raf);
			}
		};
	}

	// AboutPage, a leaf of the WebSite — the schema counterpart every hub/leaf
	// already carries. Names and description reuse the same i18n strings the
	// visible page and <Seo> use, so the three can't drift.
	const aboutLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'AboutPage',
			name: t('about.title'),
			description: t('about.metaDescription'),
			url: canonical,
			isPartOf: { '@type': 'WebSite', name: 'Ochorus', url: SITE_URL },
			isAccessibleForFree: true
		})
	);
</script>

<Seo
	title="{t('nav.about')} — Ochorus"
	description={t('about.metaDescription')}
	{canonical}
	hreflang={hreflangAll(path)}
	ogImage="{SITE_URL}/og/about.png"
	structuredData={[aboutLd]}
/>

<!-- ============================= HERO =============================
     A photo band: text sits on the ministry's own photograph, so the type
     colour is a fixed cream over a dark scrim rather than a theme token —
     the ground here is the photo, identical in every site theme. -->
<section class="relative isolate overflow-hidden bg-black">
	<!-- Art-directed crop: a wide band centred on the crowd for md+ screens (the
	     source photo is nearly square, so a full-bleed wide band otherwise shows
	     only the empty roof); a taller crop on phones. Both crops trim the burnt-in
	     camera watermark. object-center keeps faces in frame at every ratio. -->
	<picture>
		<source
			media="(min-width: 768px)"
			srcset="/about/hero-wide-1000.jpg 1000w, /about/hero-wide.jpg 1600w"
			sizes="100vw"
		/>
		<img
			src="/about/hero-tall.jpg"
			srcset="/about/hero-tall-800.jpg 800w, /about/hero-tall.jpg 1600w"
			sizes="100vw"
			alt={t('about.heroAlt')}
			fetchpriority="high"
			width="1600"
			height="1105"
			class="absolute inset-0 -z-10 h-full w-full object-cover object-center opacity-70"
		/>
	</picture>
	<!-- Bottom-anchored scrim: keeps the crowd bright while the type stays legible. -->
	<div
		class="absolute inset-0 -z-10 bg-gradient-to-b from-black/25 via-black/10 to-black/85"
		aria-hidden="true"
	></div>
	<div
		class="mx-auto flex min-h-[clamp(420px,60vh,620px)] max-w-5xl flex-col justify-end px-5 py-16 sm:py-24"
	>
		<p class="eyebrow mb-3 text-gold">{t('about.title')}</p>
		<!-- The page <h1>. Light on the photo scrim, so the colour is theme-fixed
		     white (the ground is the photograph, not a theme surface). -->
		<h1 class="text-h1 max-w-[16ch] text-white">{t('about.heading')}</h1>
		<p class="mt-4 max-w-2xl text-body text-white/90">{t('about.p1')}</p>
		<p class="mt-6 text-small uppercase tracking-[0.12em] text-gold">{t('about.heroMeta')}</p>
	</div>
</section>

<!-- ============================= STORY ============================= -->
<section class="bg-bg">
	<div class="mx-auto max-w-2xl px-5 py-16 sm:py-20">
		<p class="eyebrow mb-4 text-accent">{t('about.storyEyebrow')}</p>
		<hr class="mb-6 h-[3px] w-14 border-0 bg-gold" />
		<p class="text-h3 font-display leading-snug text-text">{t('about.p2')}</p>
		<div class="mt-5 space-y-4 text-body text-muted">
			<p>{t('about.p3')}</p>
			<p>{t('about.p4')}</p>
		</div>
	</div>
</section>

<!-- ======================= VISION & PILLARS ======================= -->
<section class="border-y border-border bg-surface">
	<div class="mx-auto grid max-w-5xl gap-10 px-5 py-16 sm:py-20 md:grid-cols-2 md:gap-14">
		<div>
			<p class="eyebrow mb-4 text-accent">{t('about.visionEyebrow')}</p>
			<p class="text-h2 font-display leading-tight text-text">{t('about.visionQuote')}</p>
		</div>
		<div class="space-y-6 self-center">
			{#each [['about.pillar1Title', 'about.pillar1Body'], ['about.pillar2Title', 'about.pillar2Body'], ['about.pillar3Title', 'about.pillar3Body']] as [title, body] (title)}
				<div>
					<p class="eyebrow mb-1.5 text-gold">{t(title)}</p>
					<p class="text-body text-muted">{t(body)}</p>
				</div>
			{/each}
		</div>
	</div>
</section>

<!-- ============================= STATS ============================= -->
<section class="bg-surface-2">
	<div class="mx-auto max-w-5xl px-5 py-16 sm:py-20">
		<div class="mb-10 max-w-2xl">
			<p class="eyebrow mb-3 text-gold">{t('about.statsEyebrow')}</p>
			<h2 class="text-h2 text-text">{t('about.statsHeading')}</h2>
			<p class="mt-3 text-body text-muted">{t('about.statsIntro')}</p>
		</div>
		<!-- Rounded floors, not hand-counted exacts: the library only grows, so
		     "100+" / "90+" / "1,000+" stay true between deploys without a recount.
		     Languages alone is exact and dynamic (the LIVE-locale registry). -->
		<dl
			class="grid grid-cols-2 gap-px overflow-hidden rounded-card border border-border bg-border sm:grid-cols-3 lg:grid-cols-6"
		>
			{#each [['7', 'about.statContinents'], [String(languageCount), 'about.statLanguages'], ['100+', 'about.statTitles'], ['90+', 'about.statSermons'], ['1,000+', 'about.statPrinted'], ['$0', 'about.statFree']] as [n, label] (label)}
				<div class="bg-surface p-6">
					<div class="mb-3.5 h-[3px] w-7 rounded bg-gold/80" aria-hidden="true"></div>
					<dd class="text-h2 font-display leading-none text-gold tabular-nums" use:countUp={n}>{n}</dd>
					<dt class="mt-3 text-small uppercase tracking-wider text-muted">{t(label)}</dt>
				</div>
			{/each}
		</dl>
	</div>
</section>

<!-- ===================== FROM PAGE TO FIELD ===================== -->
<section class="bg-bg">
	<div class="mx-auto max-w-5xl px-5 py-16 sm:py-20">
		<div class="mb-10 max-w-2xl">
			<p class="eyebrow mb-3 text-accent">{t('about.outreachHeading')}</p>
			<h2 class="text-h2 text-text">{t('about.fieldHeading')}</h2>
			<p class="mt-3 text-body text-muted">{t('about.outreachP1')}</p>
		</div>
		<div class="grid grid-cols-2 gap-4 sm:grid-cols-6">
			{#each field as f (f.img)}
				{@const src = `/about/${f.img}.jpg`}
				<figure class={f.span}>
					<button
						type="button"
						onclick={() => openLightbox(`/about/${f.img}.jpg`, t(f.cap))}
						class="group block w-full cursor-zoom-in overflow-hidden rounded-card border border-border bg-surface-2 {f.aspect} focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold"
					>
						<img
							{src}
							use:hydrateSrc={{ src }}
							alt={t(f.cap)}
							loading="lazy"
							class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.04] motion-reduce:transition-none motion-reduce:group-hover:scale-100 {f.pos ?? ''}"
						/>
					</button>
					<figcaption class="mt-2 text-small text-muted">{t(f.cap)}</figcaption>
				</figure>
			{/each}
		</div>
	</div>
</section>

<!-- ==================== FEATURE: written & printed ==================== -->
<section class="border-y border-border bg-surface">
	<div class="mx-auto grid max-w-5xl items-center gap-10 px-5 py-16 sm:py-20 md:grid-cols-2 md:gap-14">
		<div class="grid grid-cols-2 gap-4">
			{#each featureShots as s (s.img)}
				{@const src = `/about/${s.img}.jpg`}
				<button
					type="button"
					onclick={() => openLightbox(`/about/${s.img}.jpg`, t(s.alt))}
					class="group block w-full cursor-zoom-in overflow-hidden rounded-card border border-border bg-surface-2 {s.cls} focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold"
				>
					<img
						{src}
						use:hydrateSrc={{ src }}
						alt={t(s.alt)}
						loading="lazy"
						class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.04] motion-reduce:transition-none motion-reduce:group-hover:scale-100"
					/>
				</button>
			{/each}
		</div>
		<div>
			<p
				class="eyebrow mb-4 inline-block rounded-full border border-border px-3 py-1 text-gold"
			>
				{t('about.featureTag')}
			</p>
			<h2 class="text-h2 text-text">{t('about.featureHeading')}</h2>
			<div class="mt-4 space-y-4 text-body text-muted">
				<p>{t('about.featureP1')}</p>
				<p>{t('about.featureP2')}</p>
			</div>
		</div>
	</div>
</section>

<!-- ========================== SCRIPTURE ==========================
     Public-domain wording (WEB in English); other renderings await a native
     review pass. Kept from the previous page, unchanged. -->
<section class="bg-bg">
	<div class="mx-auto max-w-5xl px-5 py-16 sm:py-20">
		<p class="eyebrow mb-6 text-accent">{t('about.scripturesHeading')}</p>
		<div class="grid gap-5 md:grid-cols-3">
			{#each [['about.scripture1', 'about.scripture1Ref'], ['about.scripture2', 'about.scripture2Ref'], ['about.scripture3', 'about.scripture3Ref']] as [text, ref] (ref)}
				<figure class="rounded-card border-s-2 border-gold bg-surface py-5 pe-4 ps-5 shadow-sm">
					<blockquote class="font-display text-body italic text-text">
						“{t(text)}”
					</blockquote>
					<figcaption class="mt-3 text-small uppercase tracking-wider text-gold">
						{t(ref)}
					</figcaption>
				</figure>
			{/each}
		</div>
	</div>
</section>

<!-- =========================== PARTNER =========================== -->
<section class="border-y border-border bg-surface">
	<div class="mx-auto max-w-5xl px-5 py-16 sm:py-20">
		<p class="eyebrow mb-3 text-accent">{t('about.partnerEyebrow')}</p>
		<h2 class="mb-8 max-w-[22ch] text-h2 text-text">{t('about.partnerHeading')}</h2>
		<div class="flex max-w-3xl gap-5 rounded-card border border-border bg-surface-2 p-6 sm:p-8">
			<span
				class="font-display grid h-12 w-12 shrink-0 place-items-center rounded-full bg-bg text-h3 text-gold"
				aria-hidden="true">✦</span
			>
			<div>
				<h3 class="text-h3 font-display text-text">{t('about.partnerName')}</h3>
				<p class="mt-2 text-body text-muted">{t('about.partnerBody')}</p>
				<p class="mt-3">
					<a
						href="https://ugandapartnership.com"
						target="_blank"
						rel="noopener"
						class="text-small text-accent underline underline-offset-2">ugandapartnership.com</a
					>
				</p>
			</div>
		</div>
	</div>
</section>

<!-- ============================= CTA ============================= -->
<section class="bg-surface-2">
	<div class="mx-auto max-w-3xl px-5 py-16 text-center sm:py-20">
		<p class="eyebrow mb-3 text-gold">{t('about.ctaEyebrow')}</p>
		<h2 class="text-h2 mx-auto max-w-[18ch] text-text">{t('about.ctaHeading')}</h2>
		<p class="mx-auto mt-4 max-w-xl text-body text-muted">{t('about.ctaBody')}</p>
		<div class="mt-8 flex flex-wrap justify-center gap-3">
			<a href={localizeHref('/books')} class="btn btn-primary">{t('home.browseLibrary')}</a>
			<a href={localizeHref('/contact')} class="btn btn-ghost">{t('about.getInTouch')}</a>
		</div>
	</div>
</section>

<!-- ============================ LIGHTBOX ============================
     Native <dialog>: Escape and backdrop close it, focus is handled by the UA.
     Clicking outside the figure (target === the dialog) closes; the type colour
     is fixed cream on the photo's own dark ground, like the hero. -->
<dialog
	bind:this={dialogEl}
	onclose={() => (lightbox = null)}
	onclick={(e) => {
		if (e.target === dialogEl) dialogEl?.close();
	}}
	class="m-auto max-w-4xl bg-transparent p-0 backdrop:bg-black/85"
>
	{#if lightbox}
		<figure class="relative m-0">
			<button
				type="button"
				onclick={() => dialogEl?.close()}
				aria-label={t('about.close')}
				class="absolute end-3 top-3 grid h-9 w-9 place-items-center rounded-full bg-black/60 text-white hover:bg-black/80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
			>
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
					<path d="M6 6l12 12M18 6L6 18" />
				</svg>
			</button>
			<img
				src={lightbox.src}
				use:hydrateSrc={{ src: lightbox.src }}
				alt={lightbox.cap}
				class="max-h-[82vh] w-auto rounded-card"
			/>
			<figcaption class="mt-3 text-center text-small text-white/80">{lightbox.cap}</figcaption>
		</figure>
	{/if}
</dialog>
