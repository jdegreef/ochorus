<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { afterNavigate } from '$app/navigation';
	import { theme } from '$lib/theme.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { paletteUi } from '$lib/paletteUi.svelte';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { siteFont } from '$lib/siteFont.svelte';
	import { listen } from '$lib/listen.svelte';
	import { browser } from '$app/environment';
	import { API_BASE_URL } from '$lib/config';
	import { lang } from '$lib/lang.svelte';
	import { footerLocales } from '$lib/footerLocales';
	import { loginHref } from '$lib/loginHref';
	import { bibleCredit, creditParts } from '$lib/bibleCredit';
	import { i18n } from '$lib/i18n.svelte';
	import { auth } from '$lib/auth.svelte';
	import { pwa } from '$lib/pwa.svelte';
	import { initAnalytics } from '$lib/analytics';
	import { localizeHref, deLocalizeHref, getLocale, getTextDirection, locales } from '$lib/paraglide/runtime';
	import AccountMenu from '$lib/components/AccountMenu.svelte';
	import QuickSettings from '$lib/components/QuickSettings.svelte';
	import FeedbackFab from '$lib/components/FeedbackFab.svelte';
	import { MEASURE } from '$lib/readerPrefs.svelte';
	import { pageWidth } from '$lib/pageWidth.svelte';
	import { isReaderRoute } from '$lib/readerRoutes';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import FeedbackDialog from '$lib/components/FeedbackDialog.svelte';
	import PwaToasts from '$lib/components/PwaToasts.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import type { IconName } from '$lib/components/Icon.svelte';
	import { PRIMARY_NAV, ENGLISH_HUBS, ORIGINALS_DEST } from '$lib/contentNav';
	// The slash-correct builder: /originals prerenders to originals/index.html.
	import { localizeHref as pageHref } from '$lib/href';
	import BrandMark from '$lib/components/BrandMark.svelte';
	import BrandSprite from '$lib/components/BrandSprite.svelte';
	import { dismissable } from '$lib/actions/dismissable';
	// Preload the primary Latin subsets of the two brand fonts (display + body).
	// @fontsource already ships them font-display:swap; preloading fetches them on
	// the critical path so the hero/headings (Fraunces) and body copy (Hanken)
	// swap in sooner — a small LCP win. Vite resolves these to the same hashed
	// URLs the @fontsource CSS requests, so there's no duplicate download. The
	// Latin-ext / Vietnamese / Cyrillic subsets stay lazy (rare glyphs).
	import frauncesLatin from '@fontsource-variable/fraunces/files/fraunces-latin-wght-normal.woff2?url';
	import hankenLatin from '@fontsource-variable/hanken-grotesk/files/hanken-grotesk-latin-wght-normal.woff2?url';

	let { children } = $props();
	const t = i18n.t;

	onMount(() => {
		theme.init();
		siteFont.init();
		readerPrefs.init();
		pageWidth.init();
		auth.init();
		pwa.init();
		// Cookieless pageview analytics; no-ops unless PUBLIC_PLAUSIBLE_DOMAIN is
		// set. The script self-tracks SPA route changes from here on.
		initAnalytics();
	});

	// Leaving a chapter is the safe moment to take a waiting app update.
	afterNavigate(() => pwa.navigated());

	// Reflect the URL locale on <html> for accessibility + correct hyphenation.
	$effect(() => {
		if (browser) {
			document.documentElement.lang = getLocale();
			document.documentElement.dir = getTextDirection(getLocale());
		}
	});

	// When signed in, mirror preference changes back to the profile (debounced).
	$effect(() => {
		// touch the values so the effect tracks them
		void theme.current;
		void readerPrefs.scale;
		void listen.rate;
		void listen.voiceURI;
		if (auth.user) auth.pushPrefs();
	});

	// App destinations only — About Us and Contact live in the footer (matching
	// Take Root, whose app nav carries five primary destinations).
	// Home (chrome) then the five content types, whose order is shared with the
	// footer and command palette via PRIMARY_NAV so the three can't drift (F2).
	const NAV = $derived<{ href: string; label: string; icon: IconName }[]>([
		{ href: '/', label: t('nav.home'), icon: 'grid' },
		...PRIMARY_NAV.map((d) => ({ href: d.href, label: t(d.labelKey), icon: d.icon }))
	]);

	// The reroute hook strips the locale prefix before routing, so page.route.id
	// is the canonical path ("/books", "/books/[slug]") — compare against that.
	const isActive = (href: string) =>
		href === '/' ? $page.route.id === '/' : ($page.route.id?.startsWith(href) ?? false);

	// Mobile nav drawer (collapsed behind a hamburger on small screens).
	let navOpen = $state(false);
	let navEl = $state<HTMLElement>();

	/** Reading surfaces pin their OWN bar to the top; see .appnav-static. */
	const inReader = $derived(isReaderRoute($page.route.id));

	// Publish the bar's RENDERED height so the handful of pages with their own
	// sticky sub-bar (search filters, the biographies index) can sit below it
	// rather than under it. Measured rather than assumed: the bar wraps when the
	// mobile drawer opens, and its height changes with the type scale.
	//
	// This is a FACT about the nav, not a policy about who should clear it. It
	// used to publish 0 on the reading routes — true there only because the nav
	// is static and rides away with the scroll. In the reader's page-turn mode
	// nothing scrolls, so it never rides away, and a consumer that trusted the 0
	// pinned itself underneath a bar that was still sitting there. Whether to
	// clear the nav depends on what the consumer is doing; the height doesn't.
	// Focus mode is the one case where the height really is 0: the nav is not
	// rendered at all.
	let navH = $state(0);
	$effect(() => {
		if (!navEl) return;
		// Measure once, synchronously, BEFORE observing. A ResizeObserver's first
		// callback lands a frame late, so the reader's page-turn bar — which now
		// starts at var(--appnav-h) — spent that frame at 0, drawn underneath the
		// nav, and then jumped 56px down. Nobody sees a stale height here: an
		// element that just rendered has its real one.
		navH = Math.round(navEl.getBoundingClientRect().height);
		const ro = new ResizeObserver(([entry]) => {
			navH = Math.round(entry.target.getBoundingClientRect().height);
		});
		ro.observe(navEl);
		return () => ro.disconnect();
	});

	const copyrightYear = new Date().getFullYear();

	// Footer language strip: the ADVERTISED locales, named in their own language,
	// linking to that locale's home. Advertised — not every UI locale — because
	// this strip is a promise: "Ochorus is available in your language." A locale
	// with nothing to read delivers a fully translated interface wrapped around
	// an empty library, which is a worse first impression than not offering it.
	// (pt and ar were the cases that taught us this and have since filled up;
	// hi is today's example, wired with zero books. See advertised-locales.ts.)
	// Same rule the sitemap and hreflang use, so the site makes one consistent
	// claim about which languages it serves.
	//
	// Those locales stay switchable in Settings, so a reader who wants the
	// translated UI can still have it — this only stops us advertising it.
	//
	// ...with one exception, which is why the rule lives in footerLocales.ts
	// (and is tested there): the locale the reader is ACTUALLY IN is always
	// listed, advertised or not.
	const footerLangs = $derived(footerLocales(lang.available, lang.current));

	// Footer sign-up CTA target. Reuses loginHref's guard (which keeps a reader
	// who is already on /login from being redirected back to it — see loginHref)
	// and just adds mode=signup so the login page opens on its "create account"
	// form. The caller localizes the path, exactly as the header's sign-in link
	// does. Only rendered when accounts exist AND the reader is signed out.
	// ...and not on /login itself, where the form is already the whole page and
	// a second "Create an account" band under it only competes with it.
	const onLogin = $derived(deLocalizeHref($page.url.pathname).startsWith('/login'));
	const withSignup = (href: string) => `${href}${href.includes('?') ? '&' : '?'}mode=signup`;
	const signupHref = $derived(withSignup(loginHref($page.url.pathname, $page.url.search)));

	// Footer "My Account" column — the reader's own pages. Signed in, the links
	// go straight there; signed out, they route through /login (via the same
	// loginHref guard the header's sign-in link uses) carrying a redirect to the
	// localized target, so a successful sign-in lands the reader on the page they
	// asked for.
	const accountLinks = $derived.by(() => {
		// `signup` opens the form on "create account": a signed-out reader following
		// Bookshelf / Notebook from here most likely has no account yet, and /login
		// pitches that destination beside the form (LoginPitch).
		const dest = (path: string, signup = false) => {
			const target = localizeHref(path);
			if (auth.user) return target;
			const href = localizeHref(loginHref(target));
			return signup ? withSignup(href) : href;
		};
		return [
			{ href: dest('/favorites', true), labelKey: 'fav.yourFavorites' },
			{ href: dest('/notebook', true), labelKey: 'notebook.title' },
			{ href: dest('/settings'), labelKey: 'account.settings' }
		];
	});

	// Feedback is a modal, not a page, so it can't ride in accountLinks. Signed
	// in, the footer entry opens the same FeedbackDialog the account dropdown
	// does; signed out, it requires sign-up first — routing to /login with a
	// redirect back to the current page, since there's no feedback page to land
	// on (they open it from here or the dropdown once signed in).
	let feedbackOpen = $state(false);
	const feedbackSignedOutHref = $derived(
		localizeHref(loginHref($page.url.pathname, $page.url.search))
	);

	// Footer column count: brand + Explore + mission are always present (3);
	// Discover adds one for English only, My Account adds one whenever accounts
	// exist. Every reachable class is spelled as a LITERAL below so Tailwind's
	// scanner keeps it (the count switches at runtime, not the child list).
	const footerGridClass = $derived.by(() => {
		const n = 3 + (lang.current === 'en' ? 1 : 0) + (auth.enabled ? 1 : 0);
		return n === 5 ? 'lg:grid-cols-5' : n === 4 ? 'lg:grid-cols-4' : 'lg:grid-cols-3';
	});

	// The API is a separate origin in production (api.ochorus.com). Prerendered
	// pages bake their content, but the personal blocks (Continue reading,
	// Today's reading) and every SPA navigation fetch from it, so warming DNS +
	// TLS up front shaves the first API round-trip. `crossorigin` because those
	// fetches are cross-origin CORS; empty API_BASE_URL means same-origin, where
	// a preconnect would be pointless.
	const apiOrigin = API_BASE_URL && /^https?:\/\//.test(API_BASE_URL)
		? new URL(API_BASE_URL).origin
		: '';
</script>

<svelte:head>
	{#if apiOrigin}
		<link rel="preconnect" href={apiOrigin} crossorigin="anonymous" />
	{/if}
	<link rel="preload" href={frauncesLatin} as="font" type="font/woff2" crossorigin="anonymous" />
	<link rel="preload" href={hankenLatin} as="font" type="font/woff2" crossorigin="anonymous" />
	<!-- Feed autodiscovery: browsers and readers surface the "new works" Atom feed. -->
	<link rel="alternate" type="application/atom+xml" title="Ochorus — New in the Library" href="/feed.xml" />
</svelte:head>

<div
	class="flex min-h-screen flex-col"
	style="--reading-scale: {readerPrefs.scale}; --reading-measure: {MEASURE[
		readerPrefs.measure
	]}; --pw: {pageWidth.rem}rem; --appnav-h: {readerUi.focus ? 0 : navH}px"
>
	<a href="#main" class="skip-link">{t('a11y.skipToContent')}</a>
	<!-- Defines the Ochorus wordmark <symbol> once; every BrandMark <use>s it. -->
	<BrandSprite />
	{#if !readerUi.focus}
		<nav
			class="appnav"
			class:appnav-static={inReader}
			aria-label={t('a11y.mainNav')}
			bind:this={navEl}
			use:dismissable={{ open: navOpen, onDismiss: () => (navOpen = false) }}
		>
			<div class="appnav-inner">
			<!-- No separate wordmark: the logo carries "Ochorus" in the artwork. -->
			<a class="brand" href={localizeHref('/')}><BrandMark height={36} /></a>
			<button
				class="navtoggle"
				aria-label={t('a11y.menu')}
				aria-expanded={navOpen}
				onclick={() => (navOpen = !navOpen)}
			>
				{#if navOpen}
					<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
				{:else}
					<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
				{/if}
			</button>
			<!-- No focus trap: this is a disclosure, not a modal. It pushes the page
			     down rather than covering it, Escape and an outside click both close
			     it, and focusTrap is built for overlays that MOUNT on open — applied
			     to an always-rendered element it would seize focus on page load. -->
			<div class="navmenu" class:open={navOpen}>
				<div class="navlinks">
					{#each NAV as item (item.href)}
						<a
							href={localizeHref(item.href)}
							class:active={isActive(item.href)}
							aria-current={isActive(item.href) ? 'page' : undefined}
							onclick={() => (navOpen = false)}><Icon name={item.icon} />{item.label}</a
						>
					{/each}
				</div>
			</div>
			<div class="navctl">
					<button
						class="navsearch"
						onclick={() => paletteUi.openPalette()}
						aria-label={t('nav.search')}
						title={t('nav.search')}
					>
						<Icon name="search" size={18} />
						<kbd class="navsearch-kbd" aria-hidden="true">⌘K</kbd>
					</button>
					<!-- No language control here, deliberately. Switching locale lives in
					     two places instead: the footer strip below, and Settings.

					     A header dropdown had to list EVERY UI locale to be worth its
					     slot, and that made the chrome contradict itself — hi appeared in
					     the header while the footer strip, the sitemap and hreflang all
					     omit it, because hi has nothing to read yet. Two controls a
					     screen apart offering different language lists reads as a bug
					     whichever one you notice first. The footer strip is the promise
					     ("Ochorus is available in your language") and Settings is the
					     escape hatch that still carries the full `lang.available` list,
					     so a reader who wants a wired-but-empty locale can have it
					     without us advertising it. -->
					<!-- Quick settings: gear opens a theme + reading-width popover (the
					     full Settings page is still linked from the account menu). -->
					<QuickSettings />
					<AccountMenu />
			</div>
			</div>
		</nav>
	{/if}

	<main id="main" class="flex-1">
		{@render children()}
	</main>

	{#if !readerUi.focus}
		<footer class="site-footer border-t border-border bg-surface-2">
			<!-- The footer sits under every page, so it orients rather than
			     decorates: a signed-out reader meets one invitation, everyone meets
			     two short link columns split by intent (where to read vs. what else
			     is here), and the utility links (About / Contact / Terms) sit in a
			     slim bar at the very bottom, where a reader looks for them last. An
			     indigo-to-gold hairline along the top edge is the one colourful
			     gesture — the signature pairing, kept to a 2px rule. -->

			<!-- Sign-up invitation, signed-out readers only. auth.enabled gates it
			     the same way the header's sign-in control is (AccountMenu): with
			     Supabase keys absent the whole auth UI hides rather than offering a
			     button that can't work, and once signed in the prompt is spent, so
			     it drops. Every string is an EXISTING, already-translated key reused
			     from the sign-up flow (home.signupTitle / login.syncNote /
			     login.createAccountLink), so the band mints no footer-only keys —
			     the trade is that rewording those at their source also rewords this
			     band. -->
			{#if auth.enabled && !auth.user && !onLogin}
				<div class="mx-auto max-w-5xl px-5 pt-10 sm:pt-12">
					<div class="footer-invite">
						<span class="footer-invite-mark" aria-hidden="true">
							<Icon name="bookmark" size={22} />
						</span>
						<div class="footer-invite-text">
							<p class="footer-invite-title">{t('home.signupTitle')}</p>
							<p class="text-small text-muted">{t('login.syncNote')}</p>
						</div>
						<a href={localizeHref(signupHref)} class="btn footer-invite-cta">
							<span>{t('login.createAccountLink')}</span>
							<Icon name="chevron-right" size={16} class="footer-invite-arrow" />
						</a>
					</div>
				</div>
			{/if}

			<!-- Content columns: brand · Explore · [Discover] · [My Account] ·
			     mission. Discover is English-only (see that block's note) and My
			     Account shows only where accounts exist, so the count runs 3–5 —
			     computed once in footerGridClass, which spells every reachable
			     grid-cols literal out for Tailwind's scanner. -->
			<div
				class="mx-auto grid max-w-5xl grid-cols-2 gap-x-8 gap-y-10 px-5 py-10 sm:py-12 {footerGridClass}"
			>
				<div class="col-span-2 lg:col-span-1">
					<a class="inline-block text-text" href={localizeHref('/')} aria-label={t('common.home')}>
						<BrandMark height={34} />
					</a>
					<p class="mt-2 max-w-xs text-small text-muted">
						{t('footer.tagline')}
					</p>
				</div>
				<!-- Labelled by their own headings rather than a duplicated aria-label:
				     the visible heading IS the accessible name, so the two can't drift
				     apart in translation, and a landmark is how a screen-reader user
				     reaches these links without arrowing the whole page. -->
				<nav aria-labelledby="footer-explore-heading">
					<h2 id="footer-explore-heading" class="footer-heading">{t('footer.explore')}</h2>
					<ul class="footer-links">
						<!-- The primary five, in PRIMARY_NAV order (shared with the top nav and
						     the command palette so the three can't drift — F2). -->
						{#each PRIMARY_NAV as d (d.href)}
							<li><a href={localizeHref(d.href)}>{t(d.labelKey)}</a></li>
						{/each}
						<!-- Non-English readers have no Discover column, so the two links that
						     serve every language — Originals (its books are translated) and
						     RSS — ride in Explore for them. -->
						{#if lang.current !== 'en'}
							<li><a href={pageHref(ORIGINALS_DEST.href)}>{t(ORIGINALS_DEST.labelKey)}</a></li>
							<li><a href="/feed.xml">RSS</a></li>
						{/if}
					</ul>
				</nav>
				<!-- Discover — English-only hubs, shown only to English readers rather
				     than localized. The content is lifted from / parsed against the
				     English works (scripture cites English book names, quotes cite
				     English chapters, articles have no translations yet), so there is no
				     localized page to send anyone to, and a locale-prefixed link would
				     promise a missing page and let the prerender crawler bake localized
				     copies of it. Because the column only ever renders in English, its
				     heading is a plain literal (like RSS) — it needs no catalogue key.
				     The trailing slash matches these pages' canonical URLs. -->
				{#if lang.current === 'en'}
					<nav aria-labelledby="footer-discover-heading">
						<h2 id="footer-discover-heading" class="footer-heading">Discover</h2>
						<ul class="footer-links">
							{#each ENGLISH_HUBS as d (d.href)}
								<li><a href="{d.href}/">{t(d.labelKey)}</a></li>
							{/each}
							<li><a href={pageHref(ORIGINALS_DEST.href)}>{t(ORIGINALS_DEST.labelKey)}</a></li>
							<li><a href="/feed.xml">RSS</a></li>
						</ul>
					</nav>
				{/if}
				<!-- My Account — the reader's own pages (saved works + notebook). Shown
				     in every locale, signed in or out: these routes aren't localized
				     content, they're the reader's own data, and a signed-out reader's
				     links route through /login with a redirect so they land on the page
				     after authenticating (see accountLinks). Gated on auth.enabled the
				     same way the sign-in control and the sign-up invite are — with
				     accounts disabled at the deployment level there is nowhere to send
				     anyone, so the column drops rather than offering dead links. The
				     heading reuses account.title, already translated in every locale. -->
				{#if auth.enabled}
					<nav aria-labelledby="footer-account-heading">
						<h2 id="footer-account-heading" class="footer-heading">{t('account.title')}</h2>
						<ul class="footer-links">
							{#each accountLinks as d (d.labelKey)}
								<li><a href={d.href}>{t(d.labelKey)}</a></li>
							{/each}
							<li>
								<!-- Feedback opens a modal when signed in; signed out it needs an
								     account first, so it links to /login like the rows above. -->
								{#if auth.user}
									<button type="button" onclick={() => (feedbackOpen = true)}
										>{t('feedback.send')}</button
									>
								{:else}
									<a href={feedbackSignedOutHref}>{t('feedback.send')}</a>
								{/if}
							</li>
						</ul>
					</nav>
				{/if}
				<!-- Mission rides in the grid rather than spanning the row on mobile
				     (unlike the brand column) so the link columns pair up two-per-row:
				     with Explore · Discover · My Account it makes an even 2×2 for a
				     signed-in English reader instead of leaving My Account stranded. -->
				<div class="lg:col-span-1">
					<h2 class="footer-heading">{t('footer.ministryHeading')}</h2>
					<p class="text-small text-muted">
						{t('footer.mission')}
					</p>
					<p class="mt-4 text-small text-muted">
						{t('footer.ministry')}
					</p>
				</div>
			</div>
			<!-- Bible credit. Renders only for a locale whose Bible is licensed rather
			     than public domain — today that is Hindi alone (IRV, CC BY-SA 4.0).
			     It sits in the footer because the verses it credits are quoted inside
			     ordinary sermon and biography prose, so there is no one page to put
			     it on; the footer is on all of them. lang="en" because the notice is
			     carried in the publisher's own wording, and an English sentence
			     announced by a Hindi synthesiser is worse than no announcement.
			     See bibleCredit.ts, and library/language_seed.py which owns the
			     same string. -->
			{#if bibleCredit(lang.current)}
				<p class="mx-auto max-w-5xl border-t border-border px-5 py-4 text-small text-muted" lang="en">
					{#each creditParts(bibleCredit(lang.current)) as part, i (i)}{#if part.href}<a
								class="underline"
								href={part.href}
								rel="license noreferrer">{part.text}</a
							>{:else}{part.text}{/if}{/each}
				</p>
			{/if}
			<!-- Language strip. Each locale is named in its OWN language (Español, not
			     "Spanish") — a reader scanning for their language recognises the
			     autonym, not the English exonym. Real <a href>s so crawlers can reach
			     every locale's home, but the click goes through lang.choose(): Paraglide
			     resolves the locale from the URL prefix, and a client-side navigation
			     would change the URL without re-resolving it. `choose`, not `set` — a
			     reader-initiated switch MUST record the choice, or the next profile pull
			     adopts the account's saved locale and bounces them straight back to
			     English (that was the bug; langChoice.test.ts guards it).
			     No hreflang attribute
			     here — on an <a> it carries no SEO weight (Google reads it from head
			     <link>, the sitemap, or headers) and it makes audit tools report
			     phantom broken alternates on every page. -->
			<nav
				class="border-t border-border"
				aria-label={t('footer.languages')}
			>
				<div
					class="mx-auto flex max-w-5xl flex-wrap items-baseline gap-x-5 gap-y-1 px-5 py-4 text-small"
				>
					<span class="eyebrow py-1 text-text"
						>{t('footer.languages')}</span
					>
					{#each footerLangs as l (l.code)}
						<!-- nowrap per item: a language name breaking mid-word ("Kiswa- hili")
						     is worse than the row wrapping between names.
						     lang={l.code} on each name so a screen reader pronounces the
						     autonym with that language's voice — an English synthesiser
						     reading "Kiswahili" or "العربية" out of an English page is
						     exactly the reader this strip exists for.
						     py-1 on both branches: these wrap to several rows on a phone,
						     and a mis-tap here doesn't scroll something, it switches the
						     whole site's language and records the choice. -->
						{#if l.code === lang.current}
							<span
								class="footer-lang whitespace-nowrap py-1 font-semibold text-text"
								lang={l.code}
								aria-current="true">{l.native_name}</span
							>
						{:else}
							<a
								href={localizeHref('/', { locale: l.code as (typeof locales)[number] })}
								class="footer-lang whitespace-nowrap py-1 text-muted hover:text-text"
								lang={l.code}
								onclick={(e) => {
									// Hand modified and non-primary clicks back to the browser.
									// The href is already the correct locale home, so cmd/ctrl-click
									// opens it in a new tab exactly right — but an unconditional
									// preventDefault swallows that, and "open in a new tab" silently
									// doing nothing is the kind of break nobody reports.
									// The new tab resolves its locale from the URL prefix on load, so
									// it needs no choice recorded; only the in-place switch below does.
									if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0)
										return;
									e.preventDefault();
									lang.choose(l.code);
								}}>{l.native_name}</a
							>
						{/if}
					{/each}
				</div>
			</nav>

			<!-- Utility bar at the very bottom: the About / Contact / Terms links a
			     reader looks for last, paired with the copyright. These were a
			     content column of their own; moved here so the two columns above are
			     content-only and the utility links sit where footers conventionally
			     keep them. The About landmark keeps its heading string as its
			     accessible name. Symbol, year and the product's own name need no
			     translating, so the © costs no catalogue keys. -->
			<div class="border-t border-border">
				<div
					class="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-5 py-4 text-small"
				>
					<nav class="flex flex-wrap gap-x-5 gap-y-1" aria-label={t('footer.aboutHeading')}>
						<a class="text-muted hover:text-text" href={localizeHref('/about')}>{t('nav.about')}</a>
						<a class="text-muted hover:text-text" href={localizeHref('/contact')}>{t('nav.contact')}</a>
						<a class="text-muted hover:text-text" href="{localizeHref('/legal')}#privacy"
							>{t('footer.legal')}</a>
					</nav>
					<p class="text-muted">© {copyrightYear} Ochorus</p>
				</div>
			</div>
		</footer>
	{/if}
</div>

<CommandPalette />
<PwaToasts />

<!-- The floating feedback button — signed-in only, hidden in focus mode and over
     the admin console (it self-gates). Opens its own FeedbackDialog. -->
<FeedbackFab />

<!-- Feedback modal, opened from the footer's My Account column (the account
     dropdown mounts its own). FeedbackDialog is signed-in only, and feedbackOpen
     is only ever set from the signed-in branch above. -->
{#if feedbackOpen}
	<FeedbackDialog onClose={() => (feedbackOpen = false)} />
{/if}

<style>
	/* The footer's one colourful gesture: an indigo-to-gold hairline along the
	   top edge. Purely decorative, so it stays a 2px rule. */
	.site-footer {
		position: relative;
	}
	.site-footer::before {
		content: '';
		position: absolute;
		inset-block-start: 0;
		inset-inline: 0;
		block-size: 2px;
		background: linear-gradient(90deg, var(--accent) 0%, var(--accent) 55%, var(--gold) 100%);
	}

	/* Sign-up invitation. A tinted panel — the same soft-indigo surface the
	   primary button already uses — so it reads as one warm call, not an ad. */
	.footer-invite {
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: center;
		gap: 1.25rem;
		padding: 1.25rem 1.5rem;
		border: 1px solid var(--accent-soft-border);
		border-radius: var(--radius-card);
		background: var(--accent-soft);
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
	.footer-invite-text {
		display: grid;
		gap: 0.15rem;
	}
	.footer-invite-title {
		font-family: var(--font-display);
		font-weight: 600;
		font-size: var(--fs-h3);
		color: var(--text);
	}

	/* The one deliberately LOUD control in the app: it wears the base .btn
	   recipe (metrics, radius, type) via `class="btn footer-invite-cta"` and
	   overrides only the loud bits. Every other .btn-primary is soft by design
	   (STYLE_GUIDE §5); this single conversion CTA is the exception — a solid
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

	@media (max-width: 640px) {
		.footer-invite {
			grid-template-columns: auto 1fr;
		}
		.footer-invite-cta {
			grid-column: 1 / -1;
			justify-content: center;
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
