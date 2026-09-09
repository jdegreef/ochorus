<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { afterNavigate } from '$app/navigation';
	import { theme } from '$lib/theme.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { paletteUi } from '$lib/paletteUi.svelte';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
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
	import { localizeHref, getLocale, getTextDirection, locales } from '$lib/paraglide/runtime';
	import AccountMenu from '$lib/components/AccountMenu.svelte';
	import QuickSettings from '$lib/components/QuickSettings.svelte';
	import { MEASURE } from '$lib/readerPrefs.svelte';
	import { pageWidth } from '$lib/pageWidth.svelte';
	import { isReaderRoute } from '$lib/readerRoutes';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import PwaToasts from '$lib/components/PwaToasts.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import type { IconName } from '$lib/components/Icon.svelte';
	import BrandMark from '$lib/components/BrandMark.svelte';
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
	const NAV = $derived<{ href: string; label: string; icon: IconName }[]>([
		{ href: '/', label: t('nav.home'), icon: 'grid' },
		{ href: '/books', label: t('nav.books'), icon: 'book' },
		{ href: '/topics', label: t('nav.topics'), icon: 'tag' },
		{ href: '/plans', label: t('nav.plans'), icon: 'calendar' },
		{ href: '/sermons', label: t('nav.sermons'), icon: 'mic' },
		{ href: '/biographies', label: t('nav.biographies'), icon: 'users' }
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
	const signupHref = $derived.by(() => {
		const base = loginHref($page.url.pathname, $page.url.search);
		return base.includes('?') ? `${base}&mode=signup` : `${base}?mode=signup`;
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

<svelte:window
	onkeydown={(e) => {
		if (e.key === 'Escape') navOpen = false;
	}}
	onclick={(e) => {
		// Same dismissal the account and settings menus in this bar already use.
		// The toggle stops propagation, so opening never immediately re-closes.
		if (navOpen && navEl && !navEl.contains(e.target as Node)) navOpen = false;
	}}
/>

<div
	class="flex min-h-screen flex-col"
	style="--reading-scale: {readerPrefs.scale}; --reading-measure: {MEASURE[
		readerPrefs.measure
	]}; --pw: {pageWidth.rem}rem; --appnav-h: {readerUi.focus ? 0 : navH}px"
>
	<a href="#main" class="skip-link">{t('a11y.skipToContent')}</a>
	{#if !readerUi.focus}
		<nav
			class="appnav"
			class:appnav-static={inReader}
			aria-label={t('a11y.mainNav')}
			bind:this={navEl}
		>
			<div class="appnav-inner">
			<!-- No separate wordmark: the logo carries "Ochorus" in the artwork. -->
			<a class="brand" href={localizeHref('/')}><BrandMark height={36} /></a>
			<button
				class="navtoggle"
				aria-label={t('a11y.menu')}
				aria-expanded={navOpen}
				onclick={(e) => {
					e.stopPropagation();
					navOpen = !navOpen;
				}}
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
		<footer class="border-t border-border bg-surface-2">
			<!-- Four columns on wide screens; below that the two LINK columns stay
			     side by side and only the prose blocks span the full width.
			     It was three columns with every link in the middle one: an eight-item
			     list against a two-line brand and a three-line mission, so the middle
			     column ran about three times the height of its neighbours and the
			     block ended on a ragged edge. Splitting the links by INTENT — where
			     to read vs. who we are — balances that as a side effect of fixing the
			     harder problem, which was that a reader scanning for "About Us" had
			     to read past five content links to reach it.
			     Keeping the two link columns paired on a phone matters more than it
			     looks: stacked, the footer ran past 800px on a 390px screen, and it
			     sits under EVERY page. Prose can't halve like that (the mission
			     statement at ~180px wide is a column of two-word lines), so those
			     span instead. -->
			<div
				class="mx-auto grid max-w-5xl grid-cols-2 gap-x-8 gap-y-10 px-5 py-10 sm:py-12 lg:grid-cols-4"
			>
				<div class="col-span-2 lg:col-span-1">
					<a class="inline-block text-text" href={localizeHref('/')} aria-label={t('common.home')}>
						<BrandMark height={34} />
					</a>
					<p class="mt-2 max-w-xs text-small text-muted">
						{t('footer.tagline')}
					</p>
					<!-- Sign-up CTA, signed-out readers only. auth.enabled gates it the
					     same way the header's sign-in control is gated (AccountMenu): with
					     Supabase keys absent the whole auth UI hides rather than offering a
					     button that can't work. Once signed in the prompt is spent, so it
					     drops. Reuses login.createAccountLink — already translated in every
					     advertised locale — rather than minting a footer-only string. Soft
					     btn-primary to match the header control; w-fit so the pill hugs its
					     label instead of stretching the brand column. -->
					{#if auth.enabled && !auth.user}
						<a
							href={localizeHref(signupHref)}
							class="btn btn-sm btn-primary mt-4 w-fit hover:no-underline"
						>
							{t('login.createAccountLink')}
						</a>
					{/if}
				</div>
				<!-- Labelled by their own headings rather than a duplicated aria-label
				     string: the visible heading IS the accessible name, so the two
				     can't drift apart in a translation. Landmarks (not bare <div>s)
				     because that is how a screen-reader user reaches the footer links
				     without arrowing through the whole page — the language strip below
				     was already a labelled <nav>; these two were not. -->
				<nav aria-labelledby="footer-explore-heading">
					<h2 id="footer-explore-heading" class="footer-heading">{t('footer.explore')}</h2>
					<ul class="footer-links">
						<li><a href={localizeHref('/books')}>{t('nav.books')}</a></li>
						<li><a href={localizeHref('/topics')}>{t('nav.topics')}</a></li>
						<li><a href={localizeHref('/plans')}>{t('nav.plans')}</a></li>
						<li><a href={localizeHref('/sermons')}>{t('nav.sermons')}</a></li>
						<li><a href={localizeHref('/biographies')}>{t('nav.biographies')}</a></li>
						<!-- English only, and shown only to English readers rather than
						     localized. The scripture graph is built from citations parsed
						     against English book names, so there is no Spanish or Swahili
						     version to send anyone to — and offering the link under a
						     locale prefix would both promise a page that does not exist
						     and let the prerender crawler bake localized copies of it. -->
						{#if lang.current === 'en'}
							<!-- Articles are original English writing with no translations
							     yet, so — like Scripture and Quotes below — the link is shown
							     only to English readers rather than localized to a page that
							     would list nothing. It ungates when articles are translated. -->
							<li><a href="/articles/">{t('nav.articles')}</a></li>
							<li><a href="/scripture/">{t('reader.scripture')}</a></li>
							<!-- Quotes, like Scripture, is an English-only hub: the
							     quotations are lifted from the English works and every
							     citation names an English chapter. Footer, not top nav —
							     it is an entry point for search, not a primary journey. -->
							<li><a href="/quotes/">{t('nav.quotes')}</a></li>
						{/if}
						<li><a href="/feed.xml">RSS</a></li>
					</ul>
				</nav>
				<!-- Notebook is deliberately absent. It is per-account state, and a
				     signed-out visitor who clicks it from a footer that promised
				     content lands on an empty shell. It lives in the account menu,
				     which is where a signed-in reader already looks for it. -->
				<nav aria-labelledby="footer-about-heading">
					<h2 id="footer-about-heading" class="footer-heading">{t('footer.aboutHeading')}</h2>
					<ul class="footer-links">
						<li><a href={localizeHref('/about')}>{t('nav.about')}</a></li>
						<li><a href={localizeHref('/contact')}>{t('nav.contact')}</a></li>
						<li><a href="{localizeHref('/legal')}#privacy">{t('footer.legal')}</a></li>
					</ul>
				</nav>
				<div class="col-span-2 lg:col-span-1">
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
								class="whitespace-nowrap py-1 font-semibold text-text"
								lang={l.code}
								aria-current="true">{l.native_name}</span
							>
						{:else}
							<a
								href={localizeHref('/', { locale: l.code as (typeof locales)[number] })}
								class="whitespace-nowrap py-1 text-muted hover:text-text"
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

			<!-- A copyright line, which a site publishing Terms is normally expected
			     to carry. Symbol, year and the product's own name: nothing here needs
			     translating, so it costs no catalogue keys. -->
			<div class="border-t border-border">
				<p class="mx-auto max-w-5xl px-5 py-3 text-small text-muted">
					© {copyrightYear} Ochorus
				</p>
			</div>
		</footer>
	{/if}
</div>

<CommandPalette />
<PwaToasts />
