<script lang="ts">
	/**
	 * The site footer, under every page but a focus-mode reader. One band: the
	 * logo and a one-line mission, two short link columns (Library · More), the
	 * language switcher with the About / Contact / Privacy links under it, and the
	 * closing blessing as one small line. Above it, only a PERSONAL next step —
	 * the sign-up invitation, or a signed-in reader's current book — and never
	 * one that points at the page the reader is on. Its own component so footer
	 * work stops colliding with the root layout's.
	 */
	import { page } from '$app/stores';
	import { untrack } from 'svelte';
	import { lang } from '$lib/lang.svelte';
	import { auth } from '$lib/auth.svelte';
	import { WHATSAPP_CHANNEL_URL } from '$lib/config';
	import { i18n } from '$lib/i18n.svelte';
	import { footerLocales } from '$lib/footerLocales';
	import { FOR_FOOTER, forIndexPath, forLocale } from '$lib/forLinks';
	import { loginHref, withSignup } from '$lib/loginHref';
	import { seenOnView, withSource } from '$lib/signupSource';
	import { bibleCredit, creditParts } from '$lib/bibleCredit';
	import { localizeHref, deLocalizeHref, getTextDirection, locales } from '$lib/paraglide/runtime';
	import { isUnmodifiedPrimaryClick } from '$lib/plainClick';
	import { openFrom } from '$lib/signInSheet.svelte';
	import {
		PRIMARY_NAV,
		SERIES_DEST,
		AUDIENCE_DESTS,
		ENGLISH_HUBS,
		ORIGINALS_DEST,
		AZ_INDEX_DEST,
		BIBLE_DEST
	} from '$lib/contentNav';
	import { bibleIn } from '$lib/bible';
	// The slash-correct builder: /originals prerenders to originals/index.html.
	import { localizeHref as pageHref } from '$lib/href';
	import BrandMark from '$lib/components/BrandMark.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import type { currentBook as CurrentBookStore } from '$lib/currentBook.svelte';
	import { blessingFor } from '$lib/benediction';
	import { elementVisible } from '$lib/scrollSpy.svelte';
	import { pageShowsBook } from '$lib/footerResume';
	import { footerFeedback } from '$lib/footerFeedback.svelte';
	import { LIVE_LOCALE_BOOKS } from '$lib/live-locales.generated';
	import type { Snippet } from 'svelte';

	const t = i18n.t;
	const copyrightYear = new Date().getFullYear();

	// The language switcher: the ADVERTISED locales, named in their own language,
	// plus the one the reader is in (footerLocales — the same rule the sitemap
	// and hreflang use, so the site makes one claim about which languages it
	// serves; the rest stay switchable in Settings).
	const footerLangs = $derived(footerLocales(lang.available, lang.current));
	/** The /for/ hub's language — its link shows only where it is the reader's. */
	const forLang = $derived(forLocale(lang.current));

	const path = $derived(deLocalizeHref($page.url.pathname));

	// The personal next step. Signed out: the invitation (by `expectedUser`, so
	// a member's stored session keeps it off the dashboard home draws before
	// the session restores) — but not on /login, where the form IS the page.
	// The caller localizes signupHref, exactly as the header's sign-in link does.
	const showInvite = $derived(auth.enabled && !auth.expectedUser && !path.startsWith('/login'));
	const signupHref = $derived(
		withSource(withSignup(loginHref($page.url.pathname, $page.url.search)), 'footer')
	);
	// Signed in: their current book, unless this page already shows it (home's
	// hero, their lists, the book itself — pageShowsBook). Home never resolves it.
	const wantResume = $derived(!!auth.user && path !== '/');
	// The current-book store is imported only once it could be shown: it brings
	// the resume and library-list modules (and through them library-public and
	// seo), which no signed-out reader and no page view that stops short of the
	// footer needs in the JavaScript every page loads first.
	let currentBook = $state.raw<typeof CurrentBookStore | null>(null);
	const resume = $derived.by(() => {
		const item = wantResume ? (currentBook?.item ?? null) : null;
		return item && !pageShowsBook(path, item.slug) ? item : null;
	});

	// Resolved only while it could be shown AND the footer is within reach: it
	// may fetch the language's book list, and most page views never scroll here.
	let footerEl = $state<HTMLElement>();
	const footerNear = elementVisible(() => footerEl, { rootMargin: '600px 0px' });
	$effect(() => {
		if (!wantResume || !footerNear.visible || currentBook) return;
		void import('$lib/currentBook.svelte').then((m) => (currentBook = m.currentBook));
	});
	$effect(() => {
		const store = currentBook;
		if (!store || !wantResume || !footerNear.visible) return;
		void lang.current;
		untrack(() => store.refresh());
		return store.watch();
	});

	const blessing = $derived(blessingFor(lang.current));

	// Tell FeedbackFab once the band — which carries "Send feedback" — has
	// scrolled into view, or past it, so the floating button steps aside
	// instead of duplicating that link over the footer (or covering the
	// language switcher above it). The band, not the link, for that reason.
	let band = $state<HTMLElement>();
	$effect(() => {
		const node = band;
		if (!auth.enabled || !node || typeof IntersectionObserver === 'undefined') return;
		const io = new IntersectionObserver(([e]) => {
			footerFeedback.reached = e.isIntersecting || e.boundingClientRect.top < 0;
		});
		io.observe(node);
		return () => {
			io.disconnect();
			footerFeedback.reached = false;
		};
	});

	// Feedback is a modal, not a page. Signed in, the footer entry opens the
	// same FeedbackDialog the account dropdown does; signed out, it needs an
	// account first, so it routes to /login with a redirect back here.
	let feedbackOpen = $state(false);
	const feedbackSignedOutHref = $derived(
		withSource(localizeHref(loginHref($page.url.pathname, $page.url.search)), 'feedback')
	);

	const currentName = $derived(
		footerLangs.find((l) => l.code === lang.current)?.native_name ?? lang.currentEntry.native_name
	);
</script>

<footer class="site-footer border-t border-border bg-surface-2" bind:this={footerEl}>
	<!-- The footer sits under every page, so it orients rather than decorates:
	     one band of what readers use, and an indigo-to-gold hairline along the
	     top edge as its one colourful gesture. -->

	{#if showInvite || resume}
		<div class="chrome-col px-5 pt-8">
			{#if showInvite}
				<div class="footer-invite">
					<span class="footer-invite-mark" aria-hidden="true"><Icon name="bookmark" size={22} /></span>
					<div class="min-w-0">
						<p class="footer-invite-title">{t('home.signupTitle')}</p>
						<p class="text-small text-muted">{t('login.syncNote')}</p>
					</div>
					<a
						href={localizeHref(signupHref)}
						class="btn footer-invite-cta"
						use:seenOnView={'footer'}
						onclick={(e) => openFrom(e, 'footer')}
					>
						<span>{t('login.createAccountLink')}</span>
						<Icon name="chevron-right" size={16} class="footer-invite-arrow" mirror={false} />
					</a>
				</div>
			{:else if resume}
				<!-- Lazy: WorkCard brings the cover stack ($lib/components/FooterResume). -->
				{#await import('$lib/components/FooterResume.svelte') then { default: FooterResume }}
					<div class="footer-resume-wrap"><FooterResume item={resume} /></div>
				{/await}
			{/if}
		</div>
	{/if}

	<!-- One link column, labelled by its own visible heading (the heading IS
	     the landmark's accessible name, so the two can't drift apart in
	     translation). Every link is in the prerendered HTML: the footer is on
	     every page, so it is how the crawl reaches each locale's Series,
	     young-reader hubs, Originals, A–Z and the /for/ hub. -->
	{#snippet linkColumn(id: string, heading: string, list: Snippet)}
		<nav aria-labelledby={id} class="footer-col">
			<h2 {id} class="footer-heading">{heading}</h2>
			{@render list()}
		</nav>
	{/snippet}
	<div class="footer-band chrome-col px-5 py-8 sm:py-10" bind:this={band}>
		<div class="footer-brand">
			<a class="inline-block text-text" href={localizeHref('/')} aria-label={t('common.home')}>
				<BrandMark height={30} />
			</a>
			<p class="mt-2 text-small text-muted">{t('footer.tagline')}</p>
			<p class="mt-1 text-small text-muted">{t('footer.ministry')}</p>
		</div>

		<!-- Read: the primary five, in PRIMARY_NAV order (shared with the top nav
		     and the command palette so the three can't drift — F2). -->
		{#snippet readList()}
			<ul class="footer-links">
				{#each PRIMARY_NAV as d (d.href)}
					<li><a href={localizeHref(d.href)}>{t(d.labelKey)}</a></li>
				{/each}
			</ul>
		{/snippet}
		{@render linkColumn('footer-read-heading', t('common.library'), readList)}

		<!-- More: what hangs off the library. Articles · Scripture · Quotes are
		     English-only hubs, shown only to English readers rather than
		     localized (their content is lifted from the English works, so there
		     is no localized page; a locale-prefixed link would let the crawl
		     bake one). The trailing slash matches those pages' canonical URLs.
		     The audience pages are one link to their /for/ hub, which lists all
		     of them (and is what the crawl follows to each) — only for a reader
		     of a language they are written in (English, French). -->
		{#snippet moreList()}
			<ul class="footer-links">
				<li><a href={pageHref(SERIES_DEST.href)}>{t(SERIES_DEST.labelKey)}</a></li>
				{#each AUDIENCE_DESTS as d (d.href)}
					<li><a href={pageHref(d.href)}>{t(d.labelKey)}</a></li>
				{/each}
				<li><a href={pageHref(AZ_INDEX_DEST.href)}>{t(AZ_INDEX_DEST.labelKey)}</a></li>
				<!-- The Bible, only where its books have shipped: elsewhere the page
				     404s, and a link would send the crawl there ($lib/bible). -->
				{#if bibleIn(lang.current)}
					<li><a href={pageHref(BIBLE_DEST.href)}>{t(BIBLE_DEST.labelKey)}</a></li>
				{/if}
				{#if lang.current === 'en'}
					{#each ENGLISH_HUBS as d (d.href)}
						<li><a href="{d.href}/">{t(d.labelKey)}</a></li>
					{/each}
				{/if}
				<li><a href={pageHref(ORIGINALS_DEST.href)}>{t(ORIGINALS_DEST.labelKey)}</a></li>
				{#if forLang === lang.current}
					<li><a href={forIndexPath(forLang)}>{FOR_FOOTER[forLang]}</a></li>
				{/if}
			</ul>
		{/snippet}
		{@render linkColumn('footer-more-heading', t('nav.more'), moreList)}

		<div class="footer-meta">
			<!-- The language switcher: a select-shaped disclosure whose list is real
			     links, not a <select>. A <select> that switches on `change` jumps
			     language on the first arrow key (WCAG 3.2.2), does nothing before
			     hydration, and drops the links to every locale's home that each
			     page carries. Here a closed row shows the current language; open,
			     each locale is named in its OWN language (the autonym a reader
			     scans for), lang on the name so a screen reader voices it in that
			     language, and how many books wait there (baked at build,
			     $lib/live-locales.generated) worded in the reader's UI language.
			     The list opens in flow, not as an overlay, so the footer's paint
			     containment can't clip it.
			     The click goes through lang.choose(), not set(): a reader-initiated
			     switch MUST record the choice, or the next profile pull adopts the
			     account's saved locale and bounces them back to English
			     (langChoice.test.ts). Modified clicks go to the browser: the href
			     is already that locale's home, so a new tab opens it right. -->
			<h2 class="footer-heading" id="footer-lang-heading">{t('nav.language')}</h2>
			<details class="footer-lang">
				<summary class="field footer-lang-current" aria-describedby="footer-lang-heading">
					<span lang={lang.current} dir={getTextDirection(lang.current)}>{currentName}</span>
					<Icon name="chevron-right" size={16} mirror={false} class="footer-lang-chevron" />
				</summary>
				<ul class="footer-lang-list" aria-labelledby="footer-lang-heading">
					{#each footerLangs as l (l.code)}
						<li>
							<a
								href={localizeHref('/', { locale: l.code as (typeof locales)[number] })}
								class="footer-lang-link"
								aria-current={l.code === lang.current ? 'true' : undefined}
								onclick={(e) => {
									if (!isUnmodifiedPrimaryClick(e)) return;
									e.preventDefault();
									lang.choose(l.code);
								}}
							>
								<span class="footer-lang-name" lang={l.code} dir={getTextDirection(l.code)}
									>{l.native_name}</span
								>
								{#if LIVE_LOCALE_BOOKS[l.code]}
									<span class="footer-lang-count">
										{LIVE_LOCALE_BOOKS[l.code]}
										{LIVE_LOCALE_BOOKS[l.code] === 1 ? t('common.bookOne') : t('common.bookMany')}
									</span>
								{/if}
							</a>
						</li>
					{/each}
				</ul>
			</details>
			<!-- The utility links a reader looks for last. Feedback is a modal when
			     signed in; signed out it needs an account first, so it links to
			     /login. RSS serves every language. -->
			<nav class="footer-legal footer-links" aria-label={t('footer.aboutHeading')}>
				<a href={localizeHref('/about')}>{t('nav.about')}</a>
				<a href={localizeHref('/contact')}>{t('nav.contact')}</a>
				<a href="{localizeHref('/legal')}#privacy">{t('footer.legal')}</a>
				{#if auth.enabled}
					{#if auth.user}
						<button type="button" onclick={() => (feedbackOpen = true)}>{t('feedback.send')}</button>
					{:else}
						<a href={feedbackSignedOutHref} use:seenOnView={'feedback'}>{t('feedback.send')}</a>
					{/if}
				{/if}
				<a href={localizeHref('/rss/')}>RSS</a>
				<!-- Only once a channel exists ($lib/config). -->
				{#if WHATSAPP_CHANNEL_URL}
					<a href={WHATSAPP_CHANNEL_URL} target="_blank" rel="noopener">WhatsApp</a>
				{/if}
			</nav>
		</div>
	</div>

	<!-- Bible credit. Renders only for a locale whose Bible is licensed rather
	     than public domain — today that is Hindi alone (IRV, CC BY-SA 4.0). It
	     sits in the footer because the verses it credits are quoted inside
	     ordinary sermon and biography prose, so there is no one page to put it
	     on; the footer is on all of them. lang="en" because the notice is
	     carried in the publisher's own wording. See bibleCredit.ts, and
	     library/language_seed.py which owns the same string. -->
	{#if bibleCredit(lang.current)}
		<p class="chrome-col px-5 pb-4 text-small text-muted" lang="en">
			{#each creditParts(bibleCredit(lang.current)) as part, i (i)}{#if part.href}<a
						class="underline"
						href={part.href}
						rel="license noreferrer">{part.text}</a
					>{:else}{part.text}{/if}{/each}
		</p>
	{/if}

	<!-- The closing word as one small line, verbatim from this locale's own
	     Bible ($lib/benediction; none where that Bible lacks it), beside the
	     copyright. lang/dir so it is voiced and set in its own language; bdi
	     keeps the verse span's own order inside an RTL line. Symbol, year and
	     the product's own name need no translating. -->
	<div class="border-t border-border">
		<div class="footer-foot chrome-col px-5 py-4 text-small text-muted">
			{#if blessing}
				<p class="footer-blessing" lang={lang.current} dir={getTextDirection(lang.current)}>
					<span class="footer-blessing-text">{blessing.text}</span>
					<span class="whitespace-nowrap ms-1">{blessing.book} <bdi dir="ltr">{blessing.passage}</bdi></span>
				</p>
			{/if}
			<p class="whitespace-nowrap">© {copyrightYear} Ochorus</p>
		</div>
	</div>
</footer>

<!-- Feedback modal, opened from the footer's "Send feedback" (the account
     dropdown mounts its own). FeedbackDialog is signed-in only, and
     feedbackOpen is only ever set from the signed-in branch above. -->
{#if feedbackOpen}
	<!-- Loaded on first open: most visits never send feedback. -->
	{#await import('$lib/components/FeedbackDialog.svelte') then { default: FeedbackDialog }}
		<FeedbackDialog onClose={() => (feedbackOpen = false)} />
	{/await}
{/if}

<style>
	.site-footer {
		position: relative;
		/* Under every page and almost always below the fold: skip its style,
		   layout and paint until it nears the viewport, so a long page's
		   recalcs (every tap that changes state) don't pay for a footer nobody
		   is looking at (INP). `auto` remembers the real height once rendered;
		   the figure is the measured band (≈760px stacked on a phone, ≈620px
		   stacked from sm, ≈420px in its one row from lg).
		   Nothing in it is sticky or overflows its box (paint containment would
		   clip it), and its IntersectionObservers (the resume card's 600px
		   prefetch, the feedback hand-off) fire as before. */
		content-visibility: auto;
		contain-intrinsic-block-size: auto 760px;
	}
	@media (min-width: 640px) {
		.site-footer {
			contain-intrinsic-block-size: auto 620px;
		}
	}
	@media (min-width: 1024px) {
		.site-footer {
			contain-intrinsic-block-size: auto 420px;
		}
	}
	/* The footer's one colourful gesture: an indigo-to-gold hairline along the
	   top edge. Purely decorative, so it stays a 2px rule. */
	.site-footer::before {
		content: '';
		position: absolute;
		inset-block-start: 0;
		inset-inline: 0;
		block-size: 2px;
		background: linear-gradient(90deg, var(--accent) 0%, var(--accent) 55%, var(--gold) 100%);
	}

	/* The band: brand over the two link columns and the language/legal block on
	   a phone; one row of four from lg. */
	.footer-band {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 2rem;
	}
	.footer-brand,
	.footer-meta {
		grid-column: 1 / -1;
	}
	.footer-brand {
		max-inline-size: 24rem;
	}
	@media (min-width: 1024px) {
		.footer-band {
			grid-template-columns: minmax(0, 1.4fr) minmax(0, 0.8fr) minmax(0, 0.8fr) minmax(0, 1.1fr);
			gap: 2.5rem;
		}
		.footer-brand,
		.footer-meta {
			grid-column: auto;
		}
	}

	/* The switcher: a .field-shaped row with a chevron that turns as it opens,
	   and under it the locales as touch rows (a mis-tap here doesn't scroll,
	   it switches the whole site's language). */
	.footer-lang {
		max-inline-size: 18rem;
	}
	.footer-lang-current {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
		min-block-size: 2.75rem;
		cursor: pointer;
		list-style: none;
	}
	.footer-lang-current::-webkit-details-marker {
		display: none;
	}
	.footer-lang-current :global(.footer-lang-chevron) {
		color: var(--muted);
		rotate: 90deg;
		transition: rotate var(--duration-fast) ease;
	}
	.footer-lang[open] .footer-lang-current :global(.footer-lang-chevron) {
		rotate: -90deg;
	}
	.footer-lang-list {
		margin-block-start: 0.25rem;
		padding-block: 0.25rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--surface);
	}
	.footer-lang-link {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.75rem;
		min-block-size: 2.75rem;
		align-content: center;
		flex-wrap: wrap;
		padding: 0.55rem 0.85rem;
		color: var(--text);
		text-decoration: none;
	}
	.footer-lang-link:hover {
		background: var(--surface-2);
		text-decoration: none;
	}
	/* The reader's own language: an accent edge, never the fill alone (Q1). */
	.footer-lang-link[aria-current] {
		border-inline-start: 3px solid var(--accent);
		padding-inline-start: calc(0.85rem - 3px);
	}
	.footer-lang-name {
		font-family: var(--font-display);
		font-weight: 600;
		white-space: nowrap;
	}
	.footer-lang-count {
		font-size: var(--fs-small);
		color: var(--muted);
	}
	@media (prefers-reduced-motion: reduce) {
		.footer-lang-current :global(.footer-lang-chevron) {
			transition: none;
		}
	}
	/* About · Contact · Privacy · Feedback · RSS, wrapping under the select. */
	/* The links wear app.css's .footer-links recipe (muted, tap padding, the
	   feedback <button> stripped to read as a link); only the row is laid out
	   here. */
	.footer-legal {
		display: flex;
		flex-wrap: wrap;
		gap: 0 1.1rem;
		margin-block-start: 1rem;
	}

	/* The bottom line: the blessing at the start, the copyright at the end. */
	.footer-foot {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.5rem 2rem;
	}
	.footer-blessing {
		flex: 1 1 32rem;
		max-inline-size: 60rem;
	}
	.footer-blessing-text {
		font-family: var(--font-display);
		font-style: italic;
		color: var(--text);
	}
	/* These scripts' display faces have no italic, so the browser would fake
	   a slant. (app.css keeps Korean upright site-wide, but this scoped italic
	   outranks it, so Korean is named here too.) */
	.footer-blessing:is(:lang(ar), :lang(hi), :lang(am), :lang(ko)) .footer-blessing-text {
		font-style: normal;
	}

	/* The personal next step: one framed row on the page ground, so it lifts
	   off the footer's tint — mark, words, call. Stacks on a phone. */
	.footer-invite {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		align-items: center;
		gap: 0.75rem 1rem;
		padding: 1rem 1.25rem;
		border: 1px solid var(--accent-soft-border);
		border-radius: var(--radius-card);
		background: var(--accent-soft);
	}
	.footer-invite-cta {
		grid-column: 1 / -1;
		justify-self: start;
	}
	@media (min-width: 640px) {
		.footer-invite {
			grid-template-columns: auto minmax(0, 1fr) auto;
		}
		.footer-invite-cta {
			grid-column: auto;
		}
	}
	.footer-invite-mark {
		display: grid;
		place-items: center;
		inline-size: 2.75rem;
		block-size: 2.75rem;
		border-radius: var(--radius-sm);
		background: var(--accent);
		color: var(--accent-contrast);
	}
	.footer-invite-title {
		font-family: var(--font-display);
		font-weight: 600;
		font-size: var(--fs-h3);
		color: var(--text);
	}
	.footer-resume-wrap {
		max-inline-size: 32rem;
	}

	/* The deliberately LOUD conversion control: it wears the base .btn
	   recipe (metrics, radius, type) via `class="btn footer-invite-cta"` and
	   overrides only the loud bits. A .btn-primary is soft by design
	   (STYLE_GUIDE §5) except the page's read verb (.btn-solid); this
	   conversion CTA is the other exception — a solid
	   indigo with a thin gold ring (the signature pairing) and a warm sweep on
	   hover. Scoped and unlayered, so it beats @layer components and changes
	   nothing else. */
	.footer-invite-cta {
		position: relative;
		overflow: hidden;
		isolation: isolate;
		text-decoration: none;
		color: var(--accent-contrast);
		background: var(--accent);
		box-shadow:
			inset 0 0 0 1px var(--gold),
			0 7px 18px -9px var(--accent);
		transition:
			transform var(--duration-fast) ease,
			box-shadow var(--duration-fast) ease,
			filter var(--duration-fast) ease;
	}
	.footer-invite-cta span {
		position: relative;
		z-index: 2;
	}
	.footer-invite-cta :global(.footer-invite-arrow) {
		position: relative;
		z-index: 2;
		transition: transform var(--duration-fast) ease;
	}
	.footer-invite-cta::after {
		content: '';
		position: absolute;
		inset: 0;
		z-index: 1;
		background: linear-gradient(115deg, transparent 35%, color-mix(in srgb, var(--gold) 45%, transparent) 50%, transparent 65%);
		transform: translateX(-130%);
		pointer-events: none;
	}
	.footer-invite-cta:hover {
		text-decoration: none;
		transform: translateY(-1px);
		filter: brightness(1.04);
		box-shadow:
			inset 0 0 0 1px var(--gold),
			0 11px 24px -9px var(--accent);
	}
	.footer-invite-cta:hover::after {
		animation: footer-invite-sheen 0.85s ease;
	}
	/* Only the arrow nudges — the label stays put. */
	.footer-invite-cta:hover :global(.footer-invite-arrow) {
		transform: translateX(3px);
	}
	/* Arrow points into the text's reading direction, so it flips in RTL. */
	:global([dir='rtl']) .footer-invite-cta :global(.footer-invite-arrow) {
		transform: scaleX(-1);
	}
	:global([dir='rtl']) .footer-invite-cta:hover :global(.footer-invite-arrow) {
		transform: scaleX(-1) translateX(3px);
	}
	@keyframes footer-invite-sheen {
		to {
			transform: translateX(130%);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.footer-invite-cta,
		.footer-invite-cta :global(.footer-invite-arrow) {
			transition: none;
		}
		.footer-invite-cta:hover {
			transform: none;
		}
		.footer-invite-cta:hover :global(.footer-invite-arrow) {
			transform: none;
		}
		.footer-invite-cta:hover::after {
			animation: none;
		}
	}
</style>
