<script lang="ts">
	import '../app.css';
	import { onMount, untrack } from 'svelte';
	import { page } from '$app/stores';
	import { afterNavigate, beforeNavigate } from '$app/navigation';
	import { midBook } from '$lib/midBook.svelte';
	import { crossesLocale } from '$lib/localeNavigation';
	import { theme } from '$lib/theme.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { paletteUi } from '$lib/paletteUi.svelte';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { siteFont } from '$lib/siteFont.svelte';
	import { palette } from '$lib/palette.svelte';
	import { listen } from '$lib/listen.svelte';
	import { browser } from '$app/environment';
	import { API_BASE_URL } from '$lib/config';
	import { lang } from '$lib/lang.svelte';
	import { footerLocales } from '$lib/footerLocales';
	import { FOR_INDEX, FOR_LINKS, forPath } from '$lib/forLinks';
	import { loginHref, withSignup } from '$lib/loginHref';
	import { seenOnView, withSource } from '$lib/signupSource';
	import { bibleCredit, creditParts } from '$lib/bibleCredit';
	import { i18n } from '$lib/i18n.svelte';
	import { auth } from '$lib/auth.svelte';
	import { pwa } from '$lib/pwa.svelte';
	import { initAnalytics } from '$lib/analytics';
	import { install } from '$lib/install.svelte';
	import { localizeHref, deLocalizeHref, getLocale, getTextDirection, locales } from '$lib/paraglide/runtime';
	import AccountMenu from '$lib/components/AccountMenu.svelte';
	import QuickSettings from '$lib/components/QuickSettings.svelte';
	import FeedbackFab from '$lib/components/FeedbackFab.svelte';
	import { MEASURE } from '$lib/readerPrefs.svelte';
	import { pageWidth } from '$lib/pageWidth.svelte';
	import { isReaderRoute } from '$lib/readerRoutes';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import FeedbackDialog from '$lib/components/FeedbackDialog.svelte';
	import UnsyncedSignOutDialog from '$lib/components/UnsyncedSignOutDialog.svelte';
	import PwaToasts from '$lib/components/PwaToasts.svelte';
	import SignInSheet from '$lib/components/SignInSheet.svelte';
	import OneTap from '$lib/components/OneTap.svelte';
	import { ONE_TAP_ENABLED } from '$lib/oneTap';
	import { applyHeldPlanEmail } from '$lib/planEmail';
	import { openFrom } from '$lib/signInSheet.svelte';
	import TabBar from '$lib/components/TabBar.svelte';
	import { ACCOUNT_NAV, accountHref } from '$lib/accountNav';
	import Icon from '$lib/components/Icon.svelte';
	import type { IconName } from '$lib/components/Icon.svelte';
	import {
		PRIMARY_NAV,
		SERIES_DEST,
		AUDIENCE_DESTS,
		ENGLISH_HUBS,
		ORIGINALS_DEST,
		AZ_INDEX_DEST
	} from '$lib/contentNav';
	import type { NavSection } from '$lib/contentNav';
	// The slash-correct builder: /originals prerenders to originals/index.html.
	import { localizeHref as pageHref } from '$lib/href';
	import BrandMark from '$lib/components/BrandMark.svelte';
	import BrandSprite from '$lib/components/BrandSprite.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import { chapterMeter } from '$lib/components/WorkCard.svelte';
	import { currentBook } from '$lib/currentBook.svelte';
	import { benediction, PASSAGE } from '$lib/benediction';
	import { dismissable } from '$lib/actions/dismissable';
	// Preload the primary Latin subsets of the two brand fonts (display + body).
	// @fontsource already ships them font-display:swap; preloading fetches them on
	// the critical path so the hero/headings (Fraunces) and body copy (Hanken)
	// swap in sooner — a small LCP win. Vite resolves these to the same hashed
	// URLs the @fontsource CSS requests, so there's no duplicate download. The
	// Latin-ext / Vietnamese / Cyrillic subsets stay lazy (rare glyphs).
	import frauncesLatin from '@fontsource-variable/fraunces/files/fraunces-latin-wght-normal.woff2?url';
	import hankenLatin from '@fontsource-variable/hanken-grotesk/files/hanken-grotesk-latin-wght-normal.woff2?url';
	// Korean's faces, as their own stylesheet: ~100 KB of @font-face rules that
	// only a Korean page should pay for (see fonts-ko.css).
	import koFonts from '$lib/fonts-ko.css?url';

	let { children } = $props();
	const t = i18n.t;

	onMount(() => {
		theme.init();
		siteFont.init();
		palette.init();
		readerPrefs.init();
		pageWidth.init();
		if (!/Mac|iPhone|iPad/.test(navigator.platform)) searchKbd = 'Ctrl K';
		auth.init();
		pwa.init();
		// Cookieless pageview analytics; no-ops unless PUBLIC_PLAUSIBLE_DOMAIN is
		// set. The script self-tracks SPA route changes from here on.
		initAnalytics();
		install.init();
	});

	// A plan's daily email asked for while signed out is turned on here, the
	// moment an account exists, however it arrived ($lib/planEmail).
	$effect(() => {
		// untrack: applying writes the plan schedules, which this shouldn't depend on.
		if (auth.user) untrack(applyHeldPlanEmail);
	});

	// A navigation into another locale must be a full document load: the
	// locale (messages, <html lang/dir>) is fixed per document, so a client-side
	// hop between /ar/… and /… kept the old one's direction. Cancelled and
	// re-issued as a real load — a history PUSH, so a cross-locale goto loses
	// replaceState/keepFocus (none exists today; use location.replace for one).
	// Links you write by hand: also mark them data-sveltekit-reload, which
	// stops a hover preload running the target's load in the wrong locale.
	beforeNavigate(({ from, to, type, cancel }) => {
		midBook.navigated();
		if (type === 'leave' || type === 'popstate' || !crossesLocale(from?.url, to?.url)) return;
		cancel();
		location.assign(to!.url.href);
	});

	// Leaving a chapter is the safe moment to take a waiting app update.
	afterNavigate(({ from, to }) => {
		pwa.navigated();
		// Focus mode hides this layout's nav and footer, and only the reading
		// surfaces carry a way out of it (FocusExit, Escape). It was never reset,
		// so any link out of the text — breadcrumb, scripture chip, colophon, the
		// plan-day redirect — landed on a page with no nav and no exit. Keep it
		// across chapter-to-chapter turns (same route), drop it on anything else.
		if (from?.route.id !== to?.route.id) readerUi.exitFocus();
		install.touch();
	});

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
		void palette.current;
		void readerPrefs.own.scale;
		void listen.ownRate;
		void listen.voiceURI;
		if (auth.user) auth.pushPrefs();
	});

	// App destinations only — About Us and Contact live in the footer (matching
	// Take Root, whose app nav carries five primary destinations).
	// Home (chrome) then the five content types, whose order is shared with the
	// footer and command palette via PRIMARY_NAV so the three can't drift (F2).
	// Home is chrome, not a section, so it has no hue and keeps the accent.
	const NAV = $derived<{ href: string; label: string; icon: IconName; section?: NavSection }[]>([
		{ href: '/', label: t('nav.home'), icon: 'grid' },
		...PRIMARY_NAV.map((d) => ({ href: d.href, label: t(d.labelKey), icon: d.icon, section: d.section }))
	]);

	// The reroute hook strips the locale prefix before routing, so page.route.id
	// is the canonical path ("/books", "/books/[slug]") — compare against that.
	// Book Series hangs off Books (its breadcrumb and the Books page's rail) and
	// has no nav slot of its own, so its pages keep Books lit.
	const isActive = (href: string) => {
		const route = $page.route.id ?? '';
		if (href === '/') return route === '/';
		return route.startsWith(href) || (href === '/books' && route.startsWith(SERIES_DEST.href));
	};

	// Tablet "More ▾" (768–1023px only, by app.css): the destinations the
	// one-row bar has no room for — Biographies, whose link is hidden there,
	// then Originals and (in English) the hubs the footer carries.
	let navMoreOpen = $state(false);
	// English-only hubs stay unlocalized (the footer's rule), so each item
	// carries its final href; `active` is matched on the route path.
	const navMore = $derived(
		[
			...PRIMARY_NAV.filter((d) => d.href === '/biographies').map((d) => ({
				path: d.href,
				href: localizeHref(d.href),
				label: t(d.labelKey)
			})),
			{ path: ORIGINALS_DEST.href, href: localizeHref(ORIGINALS_DEST.href), label: t(ORIGINALS_DEST.labelKey) },
			...(lang.current === 'en'
				? ENGLISH_HUBS.map((d) => ({ path: d.href, href: `${d.href}/`, label: t(d.labelKey) }))
				: [])
		].map((d) => ({ ...d, active: isActive(d.path) }))
	);
	const navMoreActive = $derived(navMore.some((d) => d.active));

	// Mobile nav drawer (collapsed behind a hamburger on small screens).
	let navOpen = $state(false);
	// The search shortcut hint (the palette answers both ⌘K and Ctrl+K):
	// prerendered as ⌘K, respelt on mount off Apple platforms; CSS hides it on
	// touch devices.
	let searchKbd = $state('⌘K');
	let navEl = $state<HTMLElement>();

	/** Reading surfaces pin their OWN bar to the top; see .appnav-static. */
	const inReader = $derived(isReaderRoute($page.route.id));
	// The phone tab bar (TabBar; phones only, by its CSS). Not on the reading
	// surfaces, whose own bottom bar holds that edge; not in focus mode; not
	// while the Listen bar holds it. Where it shows (TabBar publishes
	// --tabbar-h), the top bar sheds its hamburger, gear and sign-in button —
	// they live in its "More" sheet (app.css); a signed-in avatar stays.
	const withTabBar = $derived(!inReader && !readerUi.focus && listen.status === 'idle');

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
	// Published as --appnav-h: 0 in focus mode (no nav at all), the measured
	// height once there is one, and nothing before that, so the per-breakpoint
	// estimate on `.app-root` (app.css) holds for a prerendered page.
	const appnavH = $derived(readerUi.focus ? '--appnav-h: 0px; ' : navH ? `--appnav-h: ${navH}px; ` : '');
	// …and hand it to script (readerUi.navHeight) for pages that must clear it.
	$effect(() => {
		readerUi.navHeight = navH;
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
	const signupHref = $derived(
		withSource(withSignup(loginHref($page.url.pathname, $page.url.search)), 'footer')
	);

	// Footer "Before you go" cards (markup has the why). The first card is the
	// invitation for a signed-out reader, else the signed-in reader's current
	// book — except on home, whose hero already resumes it — else a way in.
	const showInvite = $derived(auth.enabled && !auth.user && !onLogin);
	const onHome = $derived(deLocalizeHref($page.url.pathname) === '/');
	const resume = $derived(!showInvite && auth.user && !onHome ? currentBook.item : null);
	const resumeMeter = $derived(
		resume ? chapterMeter(resume.order, resume.chapterCount, resume.pct) : ''
	);

	// The current book is resolved only as the footer nears the viewport: it
	// may fetch the language's book list, and most page views never scroll this
	// far. Re-resolved each time the footer comes back into reach (the layout,
	// and so the footer, outlives navigations), and on `ochorus:sync`.
	function nearView(node: HTMLElement) {
		const io = new IntersectionObserver(
			(entries) => {
				if (auth.user && entries.some((e) => e.isIntersecting)) currentBook.refresh();
			},
			{ rootMargin: '600px 0px' }
		);
		io.observe(node);
		const unwatch = currentBook.watch();
		return {
			destroy() {
				io.disconnect();
				unwatch();
			}
		};
	}

	// The footer's closing blessing, in this locale's own Bible (or none).
	const blessing = $derived(benediction(lang.current));

	// Footer "My Account" column — the reader's own pages (ACCOUNT_NAV, shared
	// with the phone "More" sheet; accountHref routes a signed-out reader
	// through /login with a redirect back).
	const accountLinks = $derived(
		ACCOUNT_NAV.map((d) => ({
			href: accountHref(d.path, !!auth.user, d.signup),
			labelKey: d.labelKey
		}))
	);

	// Feedback is a modal, not a page, so it can't ride in accountLinks. Signed
	// in, the footer entry opens the same FeedbackDialog the account dropdown
	// does; signed out, it requires sign-up first — routing to /login with a
	// redirect back to the current page, since there's no feedback page to land
	// on (they open it from here or the dropdown once signed in).
	let feedbackOpen = $state(false);
	const feedbackSignedOutHref = $derived(
		withSource(localizeHref(loginHref($page.url.pathname, $page.url.search)), 'feedback')
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
	{#if getLocale() === 'ko'}
		<link rel="stylesheet" href={koFonts} />
	{/if}
	<!-- Feed autodiscovery: browsers and readers surface the "new works" Atom feed. -->
	<link rel="alternate" type="application/atom+xml" title="Ochorus — New in the Library" href="/feed.xml" />
</svelte:head>

<div
	class="app-root flex min-h-screen flex-col"
	style="--reading-scale: {readerPrefs.own.scale}; --reading-measure: {MEASURE[
		readerPrefs.own.measure
	]}; --pw: {pageWidth.rem}rem; {appnavH}padding-bottom: var(--tabbar-h, 0px)"
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
			<div class="appnav-inner chrome-col">
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
							data-section={item.section}
							data-home={item.href === '/' ? '' : undefined}
							onclick={() => (navOpen = false)}><Icon name={item.icon} />{item.label}</a
						>
					{/each}
				</div>
				<div class="navmore" use:dismissable={{ open: navMoreOpen, onDismiss: () => (navMoreOpen = false) }}>
					<button
						class="navmore-btn"
						class:active={navMoreActive}
						aria-expanded={navMoreOpen}
						aria-controls={navMoreOpen ? 'nav-more' : undefined}
						onclick={() => (navMoreOpen = !navMoreOpen)}
						>{t('nav.more')}<Icon name="chevron-right" size={16} mirror={false} class="rotate-90" /></button
					>
					{#if navMoreOpen}
						<div id="nav-more" class="account-menu navmore-menu" role="group" aria-label={t('nav.more')}>
							{#each navMore as d (d.path)}
								<a
									href={d.href}
									class="account-item"
									aria-current={d.active ? 'page' : undefined}
									onclick={() => (navMoreOpen = false)}>{d.label}</a
								>
							{/each}
						</div>
					{/if}
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
						<kbd class="navsearch-kbd" aria-hidden="true">{searchKbd}</kbd>
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

			<!-- "Before you go": two cards that hand the reader a next step. The
			     first is personal — for a signed-out reader, the sign-up invitation
			     (gated on auth.enabled the way the header's sign-in control is, and
			     dropped on /login, where the form is already the page); for a
			     signed-in one, the book they are in (Continue reading, the same
			     current book the home hero resumes — so not on home, where the hero
			     already shows it); else a way into the library. The second is always
			     Reading Plans. Every string is an EXISTING, already-translated key
			     (the invitation's from the sign-up flow), so the row mints no
			     footer-only keys — the trade is that rewording those at their source
			     also rewords these cards. -->
			<div class="chrome-col px-5 pt-10 sm:pt-12" use:nearView>
				<div class="footer-cards">
					{#if showInvite}
						<div class="footer-card footer-invite">
							<span class="footer-card-mark" aria-hidden="true">
								<Icon name="bookmark" size={22} />
							</span>
							<p class="footer-card-title">{t('home.signupTitle')}</p>
							<p class="text-small text-muted">{t('login.syncNote')}</p>
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
						<!-- The whole card is the link: one target, named by its title. -->
						<a class="footer-card footer-resume" href={pageHref(resume.href)}>
							<div class="w-14 shrink-0">
								<BookCover book={resume.book} rounded="rounded-sm" />
							</div>
							<div class="min-w-0 flex-1">
								<p class="eyebrow text-accent">{t('continue.title')}</p>
								<p class="footer-card-title mt-1 truncate">{resume.title}</p>
								<p class="truncate text-small text-muted">{resume.author}</p>
								<div class="mt-2">
									<ProgressBar percent={resume.pct} label="{resume.title}: {resumeMeter}" />
								</div>
								<p class="mt-1 truncate text-micro text-muted">{resumeMeter}</p>
							</div>
						</a>
					{:else}
						<div class="footer-card">
							<span class="footer-card-mark" aria-hidden="true">
								<Icon name="compass" size={22} />
							</span>
							<p class="footer-card-title">{t('seals.nextBooks')}</p>
							<p class="text-small text-muted">{t('footer.tagline')}</p>
							<a class="footer-card-link" href={localizeHref('/books')}
								>{t('home.browseLibrary')}<Icon name="chevron-right" size={16} /></a
							>
						</div>
					{/if}
					<div class="footer-card">
						<span class="footer-card-mark" aria-hidden="true">
							<Icon name="calendar" size={22} />
						</span>
						<p class="footer-card-title">{t('plans.title')}</p>
						<p class="text-small text-muted">{t('plans.tagline')}</p>
						<a class="footer-card-link" href={localizeHref('/plans')}
							>{t('seals.nextPlans')}<Icon name="chevron-right" size={16} /></a
						>
					</div>
				</div>
			</div>

			<!-- The closing word: the Aaronic blessing in this locale's own Bible
			     ($lib/benediction — verbatim from that Bible, never translated
			     here). A locale whose Bible lacks it shows nothing rather than
			     another language's verse. lang/dir on the figure so a screen reader
			     voices it in its own language and Arabic sets right to left. -->
			{#if blessing}
				<figure
					class="footer-blessing chrome-col px-5"
					lang={lang.current}
					dir={getTextDirection(lang.current)}
				>
					<svg
						class="footer-blessing-lamp"
						width="30"
						height="34"
						viewBox="0 0 34 40"
						fill="none"
						stroke="currentColor"
						stroke-width="1.5"
						aria-hidden="true"
					>
						<path d="M17 4c3 4 3 7 0 10c-3-3-3-6 0-10z" />
						<path d="M6 20h22l-3 10H9z" />
						<path d="M13 30v4h8v-4M10 36h14" />
						<path d="M28 22c4 0 4 6 0 6" />
					</svg>
					<blockquote>{blessing.lines.join(' ')}</blockquote>
					<!-- bdi: the verse span keeps its own order inside an RTL caption. -->
					<figcaption>{blessing.book} <bdi dir="ltr">{PASSAGE}</bdi></figcaption>
				</figure>
			{/if}

			<!-- Content columns: brand · Explore · [Discover] · [My Account] ·
			     mission. Discover is English-only (see that block's note) and My
			     Account shows only where accounts exist, so the count runs 3–5 —
			     computed once in footerGridClass, which spells every reachable
			     grid-cols literal out for Tailwind's scanner. -->
			<div
				class="chrome-col grid grid-cols-2 gap-x-8 gap-y-10 px-5 py-10 sm:py-12 {footerGridClass}"
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
						<li><a href={pageHref(SERIES_DEST.href)}>{t(SERIES_DEST.labelKey)}</a></li>
						{#each AUDIENCE_DESTS as d (d.href)}
							<li><a href={pageHref(d.href)}>{t(d.labelKey)}</a></li>
						{/each}
						<li><a href={pageHref(AZ_INDEX_DEST.href)}>{t(AZ_INDEX_DEST.labelKey)}</a></li>
						<!-- Non-English readers have no Discover column, so the two links that
						     serve every language — Originals (its books are translated) and
						     RSS — ride in Explore for them. -->
						{#if lang.current !== 'en'}
							<li><a href={pageHref(ORIGINALS_DEST.href)}>{t(ORIGINALS_DEST.labelKey)}</a></li>
							<li><a href={localizeHref('/rss/')}>RSS</a></li>
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
							<li><a href={localizeHref('/rss/')}>RSS</a></li>
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
									<a href={feedbackSignedOutHref} use:seenOnView={'feedback'}>{t('feedback.send')}</a>
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
				<p class="chrome-col border-t border-border px-5 py-4 text-small text-muted" lang="en">
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
					class="chrome-col flex flex-wrap items-baseline gap-x-5 gap-y-1 px-5 py-4 text-small"
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
								dir={getTextDirection(l.code)}
								aria-current="true">{l.native_name}</span
							>
						{:else}
							<a
								href={localizeHref('/', { locale: l.code as (typeof locales)[number] })}
								class="footer-lang whitespace-nowrap py-1 text-muted hover:text-text"
								lang={l.code}
								dir={getTextDirection(l.code)}
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
					class="chrome-col flex flex-wrap items-center justify-between gap-x-6 gap-y-2 px-5 py-4 text-small"
				>
					<nav class="footer-legal flex flex-wrap gap-x-5 gap-y-1" aria-label={t('footer.aboutHeading')}>
						<a class="text-muted hover:text-text" href={localizeHref('/about')}>{t('nav.about')}</a>
						<a class="text-muted hover:text-text" href={localizeHref('/contact')}>{t('nav.contact')}</a>
						<a class="text-muted hover:text-text" href="{localizeHref('/legal')}#privacy"
							>{t('footer.legal')}</a>
					</nav>
					<p class="text-muted">© {copyrightYear} Ochorus</p>
				</div>
			</div>
			<!-- "Ochorus for …" — the landing pages for churches, homeschool
			     families, parents ($lib/forLinks), as the footer's last row, read
			     left to right like the language strip above. English-only like
			     Discover: the pages are English copy for now, so a localized
			     reader is not sent to them, and the label is a plain literal. -->
			{#if lang.current === 'en'}
				<nav class="border-t border-border" aria-label="Ochorus for">
					<div
						class="chrome-col flex flex-wrap items-baseline gap-x-5 gap-y-1 px-5 py-4 text-small"
					>
						<a class="eyebrow py-1 text-text hover:underline" href={FOR_INDEX}>Ochorus for</a>
						{#each FOR_LINKS as l (l.slug)}
							<a class="whitespace-nowrap py-1 text-muted hover:text-text" href={forPath(l.slug)}
								>{l.label}</a
							>
						{/each}
					</div>
				</nav>
			{/if}
		</footer>
	{/if}
</div>

{#if withTabBar}
	<TabBar />
{/if}
<CommandPalette />
<PwaToasts />
{#if auth.enabled}<SignInSheet />{/if}
{#if auth.enabled && ONE_TAP_ENABLED}<OneTap />{/if}

<!-- The floating feedback button — signed-in only, hidden in focus mode and over
     the admin console (it self-gates). Opens its own FeedbackDialog. -->
<FeedbackFab />

<!-- Feedback modal, opened from the footer's My Account column (the account
     dropdown mounts its own). FeedbackDialog is signed-in only, and feedbackOpen
     is only ever set from the signed-in branch above. -->
{#if feedbackOpen}
	<FeedbackDialog onClose={() => (feedbackOpen = false)} />
{/if}
<!-- Sign-out asked for with changes still on this device only (both the
     account dropdown and settings route through auth.signOut). -->
{#if auth.signOutBlocked}
	<UnsyncedSignOutDialog />
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

	/* "Before you go" cards: two across from sm, stacked on a phone. Each is a
	   framed panel on the page ground, so it lifts off the footer's tint. */
	.footer-cards {
		display: grid;
		gap: 1rem;
	}
	@media (min-width: 640px) {
		.footer-cards {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	.footer-card {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 0.6rem;
		padding: 1.25rem 1.5rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.footer-card-mark {
		display: grid;
		place-items: center;
		inline-size: 2.75rem;
		block-size: 2.75rem;
		border-radius: var(--radius-sm);
		background: var(--accent-soft);
		color: var(--accent);
	}
	.footer-card-title {
		max-inline-size: 100%;
		font-family: var(--font-display);
		font-weight: 600;
		font-size: var(--fs-h3);
		color: var(--text);
	}
	/* The text link that ends a card; pushed to the card's foot so two cards of
	   different copy lengths still line their links up. */
	.footer-card-link {
		margin-block-start: auto;
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding-block: 0.35rem;
		font-weight: 600;
		color: var(--accent);
	}
	.footer-card-link :global(svg) {
		transition: transform var(--duration-fast) ease;
	}
	.footer-card-link:hover :global(svg) {
		transform: translateX(3px);
	}
	:global([dir='rtl']) .footer-card-link :global(svg) {
		transform: scaleX(-1);
	}
	:global([dir='rtl']) .footer-card-link:hover :global(svg) {
		transform: scaleX(-1) translateX(3px);
	}
	/* The sign-up card keeps the invitation's warm soft-indigo panel, and its
	   mark goes solid, so the one conversion card still reads as the call. */
	.footer-invite {
		border-color: var(--accent-soft-border);
		background: var(--accent-soft);
	}
	.footer-invite .footer-card-mark {
		background: var(--accent);
		color: var(--accent-contrast);
	}
	.footer-invite :global(.footer-invite-cta) {
		margin-block-start: auto;
	}
	/* Continue reading: the whole card is the link, cover beside the meter. */
	.footer-resume {
		flex-direction: row;
		align-items: center;
		gap: 1rem;
		color: inherit;
	}
	.footer-resume:hover {
		text-decoration: none;
		background: var(--surface-2);
	}

	/* The closing blessing: the footer's one quiet moment between the cards
	   and the link columns. Display face, italic, gold lamp above. */
	.footer-blessing {
		margin: 0 auto;
		padding-block: 3rem 0.5rem;
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
	}
	.footer-blessing-lamp {
		color: var(--gold);
	}
	.footer-blessing blockquote {
		margin: 1rem 0 0;
		max-inline-size: 46rem;
		font-family: var(--font-display);
		font-style: italic;
		font-weight: 400;
		font-size: clamp(1.25rem, 1rem + 1vw, 1.75rem);
		line-height: 1.45;
		color: var(--text);
		text-wrap: balance;
	}
	/* Only Latin script has a true Fraunces italic; elsewhere the browser
	   would fake one by slanting the fallback face, which mangles Arabic,
	   Devanagari and Ethiopic. */
	.footer-blessing:is(:lang(ar), :lang(hi), :lang(am), :lang(uk)) blockquote {
		font-style: normal;
	}
	.footer-blessing figcaption {
		margin-block-start: 0.75rem;
		font-size: var(--fs-small);
		letter-spacing: 0.08em;
		color: var(--muted);
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

	@media (prefers-reduced-motion: reduce) {
		.footer-invite-cta,
		.footer-invite-cta :global(.footer-invite-arrow),
		.footer-card-link :global(svg) {
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
