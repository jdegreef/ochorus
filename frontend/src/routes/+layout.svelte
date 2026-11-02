<script lang="ts">
	import '../app.css';
	import { onMount, untrack } from 'svelte';
	import { page } from '$app/stores';
	import { afterNavigate, beforeNavigate, goto, onNavigate } from '$app/navigation';
	import { flyCover, noteCoverTap } from '$lib/coverFlight';
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
	import { API_BASE_URL, SITE_URL } from '$lib/config';
	import { IS_APP, startAppShell } from '$lib/platform';
	import { lang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { auth } from '$lib/auth.svelte';
	import { pwa } from '$lib/pwa.svelte';
	import { initAnalytics } from '$lib/analytics';
	import { initWebVitals, notePageView } from '$lib/webVitals';
	import { install } from '$lib/install.svelte';
	import { localizeHref, getLocale, getTextDirection } from '$lib/paraglide/runtime';
	import AccountMenu from '$lib/components/AccountMenu.svelte';
	import QuickSettings from '$lib/components/QuickSettings.svelte';
	import FeedbackFab from '$lib/components/FeedbackFab.svelte';
	import { MEASURE } from '$lib/readerPrefs.svelte';
	import { pageWidth } from '$lib/pageWidth.svelte';
	import { isReaderRoute } from '$lib/readerRoutes';
	import { lazyComponent, onIdle } from '$lib/lazyComponent.svelte';
	import { signInSheet } from '$lib/signInSheet.svelte';
	import { ONE_TAP_ENABLED } from '$lib/oneTap';
	import { applyHeldPlanEmail } from '$lib/planEmail';
	import TabBar from '$lib/components/TabBar.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import type { IconName } from '$lib/components/Icon.svelte';
	import {
		PRIMARY_NAV,
		SERIES_DEST,
		ENGLISH_HUBS,
		ORIGINALS_DEST
	} from '$lib/contentNav';
	import type { NavSection } from '$lib/contentNav';
	import BrandMark from '$lib/components/BrandMark.svelte';
	import BrandSprite from '$lib/components/BrandSprite.svelte';
	import SiteFooter from '$lib/components/SiteFooter.svelte';
	import { dismissable } from '$lib/actions/dismissable';
	// Preload the primary Latin subsets of the two brand fonts (display + body).
	// @fontsource already ships them font-display:swap; preloading fetches them on
	// the critical path so the hero/headings (Fraunces) and body copy (Hanken)
	// swap in sooner — a small LCP win. Vite resolves these to the same hashed
	// URLs the @fontsource CSS requests, so there's no duplicate download. The
	// Latin-ext / Vietnamese / Cyrillic subsets stay lazy (rare glyphs).
	import frauncesLatin from '@fontsource-variable/fraunces/files/fraunces-latin-wght-normal.woff2?url';
	import hankenLatin from '@fontsource-variable/hanken-grotesk/files/hanken-grotesk-latin-wght-normal.woff2?url';
	// Each non-Latin script's faces, and the reader's optional ones, as their own
	// stylesheets: @font-face rules only the pages that draw them should wait on
	// (see app.css's header and $lib/fontSheets).
	import { SCRIPT_FONTS, READER_FONTS_SHEET, READER_SHEET_FONTS, linkSheet } from '$lib/fontSheets';

	let { children } = $props();
	const t = i18n.t;

	// The phone app's native shell (safe areas, outside links, Android's Back,
	// the splash) — before the first render, so <html data-app> is on when the
	// page first paints. Compiled out of the website (IS_APP is a constant).
	if (IS_APP && browser) {
		startAppShell({
			navigate: (path) => goto(path),
			isRoot: () => $page.route.id === '/',
			siteUrl: SITE_URL
		});
	}

	// The rarely-used global overlays load on first use, not with every page
	// ($lib/lazyComponent): the triggers stay here, the code comes when one fires.
	// ⌘K palette — on the shortcut or the nav's search button (paletteUi.open).
	const commandPalette = lazyComponent(() => import('$lib/components/CommandPalette.svelte'));
	// The sign-up sheet — when a prompt opens it (signInSheet.open).
	const signInSheetUi = lazyComponent(() => import('$lib/components/SignInSheet.svelte'));
	// The toast stack (an aria-live region, so mounted before its first message)
	// and One Tap (which waits seconds before asking anyway) — on idle after load.
	const pwaToasts = lazyComponent(() => import('$lib/components/PwaToasts.svelte'));
	const oneTap = lazyComponent(() => import('$lib/components/OneTap.svelte'));
	$effect(() => {
		if (paletteUi.open) commandPalette.load();
	});
	$effect(() => {
		if (auth.enabled && signInSheet.open) signInSheetUi.load();
	});
	onMount(() =>
		onIdle(() => {
			pwaToasts.load();
			if (auth.enabled && ONE_TAP_ENABLED) oneTap.load();
		})
	);

	// ⌘K / Ctrl+K toggles the palette from anywhere. It lives here rather than
	// in CommandPalette so the very first press works before the palette's code
	// has loaded; flipping the flag is what loads it.
	function onWindowKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			paletteUi.toggle();
		}
	}

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
		// Field INP attribution (`Slow tap` events); loads after idle, off
		// with analytics — see $lib/webVitals.
		initWebVitals(getLocale());
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

	// A tapped cover flies into the book page it opens ($lib/coverFlight;
	// the tap is noted by <svelte:document> below).
	onNavigate(flyCover);

	// Leaving a chapter is the safe moment to take a waiting app update.
	afterNavigate(({ from, to }) => {
		pwa.navigated();
		notePageView(to?.route.id);
		// Focus mode hides this layout's nav and footer, and only the reading
		// surfaces carry a way out of it (FocusExit, Escape). It was never reset,
		// so any link out of the text — breadcrumb, scripture chip, colophon, the
		// plan-day redirect — landed on a page with no nav and no exit. Keep it
		// across chapter-to-chapter turns (same route), drop it on anything else.
		if (from?.route.id !== to?.route.id) readerUi.exitFocus();
		install.touch();
	});

	// The reader's optional faces, once the reader has picked one:
	// --reading-font is applied after hydration too, so the sheet lands with the
	// choice.
	$effect(() => {
		if (READER_SHEET_FONTS.includes(readerPrefs.font)) linkSheet(READER_FONTS_SHEET);
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
	// The app's status-bar strip matches what sits under it (app.css,
	// `data-app-top`): the pinned nav, the reader's ground, or no nav at all.
	$effect(() => {
		if (IS_APP) document.documentElement.dataset.appTop = readerUi.focus ? 'none' : inReader ? 'static' : 'nav';
	});
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
		// On a reading surface, measure once, synchronously, BEFORE observing. A
		// ResizeObserver's first callback lands a frame late, so the reader's
		// page-turn bar — which now starts at var(--appnav-h) — spent that frame
		// at 0, drawn underneath the nav, and then jumped 56px down. Nobody sees a
		// stale height here: an element that just rendered has its real one.
		// Elsewhere nothing pins to the nav that first frame (the per-breakpoint
		// estimate on `.app-root` covers it), and the synchronous read forces a
		// layout of the half-built page inside the startup task a first tap waits
		// behind (mobile INP) — so leave it to the observer.
		if (untrack(() => inReader)) navH = Math.round(navEl.getBoundingClientRect().height);
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
	<!-- This document's script faces, before first paint (none for Latin). -->
	{#if SCRIPT_FONTS[getLocale()]}
		<link rel="stylesheet" href={SCRIPT_FONTS[getLocale()]} />
	{/if}
	<!-- Feed autodiscovery: browsers and readers surface the "new works" Atom feed. -->
	<link rel="alternate" type="application/atom+xml" title="Ochorus — New in the Library" href="/feed.xml" />
</svelte:head>

<svelte:window onkeydown={onWindowKeydown} />
<svelte:document onclickcapture={noteCoverTap} />

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
						onpointerenter={() => commandPalette.load()}
						onfocus={() => commandPalette.load()}
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
		<SiteFooter />
	{/if}
</div>

{#if withTabBar}
	<TabBar />
{/if}
{#if commandPalette.component}<commandPalette.component />{/if}
{#if pwaToasts.component}<pwaToasts.component />{/if}
{#if auth.enabled && signInSheetUi.component}<signInSheetUi.component />{/if}
{#if auth.enabled && ONE_TAP_ENABLED && oneTap.component}<oneTap.component />{/if}

<!-- The floating feedback button — signed-in only, hidden in focus mode and over
     the admin console (it self-gates). Opens its own FeedbackDialog. -->
<FeedbackFab />

<!-- Sign-out asked for with changes still on this device only (both the
     account dropdown and settings route through auth.signOut). -->
{#if auth.signOutBlocked}
	{#await import('$lib/components/UnsyncedSignOutDialog.svelte') then { default: UnsyncedSignOutDialog }}
		<UnsyncedSignOutDialog />
	{/await}
{/if}
