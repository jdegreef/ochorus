<script lang="ts">
	/**
	 * The site footer, under every page but a focus-mode reader: the "Before
	 * you go" cards, the closing blessing, the link columns, the Bible credit,
	 * the language strip, the utility bar and "Ochorus for …". Its own
	 * component so footer work stops colliding with the root layout's.
	 */
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { untrack } from 'svelte';
	import { lang } from '$lib/lang.svelte';
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { footerLocales } from '$lib/footerLocales';
	import {
		FOR_EYEBROW,
		FOR_FAMILIES,
		FOR_FOOTER,
		forFamilyLinks,
		forIndexPath,
		forInline,
		forLabel,
		forLocale,
		forOfTheWeek,
		forPath
	} from '$lib/forLinks';
	import { SITE_URL } from '$lib/config';
	import { isUnmodifiedPrimaryClick } from '$lib/plainClick';
	import { nativeShare } from '$lib/share';
	import { loginHref, withSignup } from '$lib/loginHref';
	import { seenOnView, withSource } from '$lib/signupSource';
	import { bibleCredit, creditParts } from '$lib/bibleCredit';
	import { localizeHref, deLocalizeHref, getTextDirection, locales } from '$lib/paraglide/runtime';
	import { openFrom } from '$lib/signInSheet.svelte';
	import { ACCOUNT_NAV, accountHref } from '$lib/accountNav';
	import {
		PRIMARY_NAV,
		SERIES_DEST,
		AUDIENCE_DESTS,
		ENGLISH_HUBS,
		ORIGINALS_DEST,
		AZ_INDEX_DEST
	} from '$lib/contentNav';
	// The slash-correct builder: /originals prerenders to originals/index.html.
	import { localizeHref as pageHref } from '$lib/href';
	import BrandMark from '$lib/components/BrandMark.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import type { IconName } from '$lib/components/Icon.svelte';
	import { currentBook } from '$lib/currentBook.svelte';
	import { blessingFor } from '$lib/benediction';
	import { elementVisible } from '$lib/scrollSpy.svelte';
	import { pageShowsBook } from '$lib/footerResume';
	import { footerFeedback } from '$lib/footerFeedback.svelte';
	import { LIVE_LOCALE_BOOKS } from '$lib/live-locales.generated';
	import type { Snippet } from 'svelte';

	const t = i18n.t;
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
	/** The "Ochorus for …" row's language — shown only where it is the reader's. */
	const forLang = $derived(forLocale(lang.current));
	const forWords = $derived(FOR_FOOTER[forLang]);

	// "Pass it on": the pastors' page through the OS share sheet, else onto the
	// clipboard; with neither (or no script yet) the link just opens the page.
	// A link rather than ShareButton for that last case, and because its menu
	// opens downward, off the bottom of the page here.
	const pastorsPath = $derived(forPath('pastors', forLang));
	let forCopied = $state(false);
	let forCopyTimer: ReturnType<typeof setTimeout> | undefined;
	$effect(() => () => clearTimeout(forCopyTimer));
	async function passItOn(e: MouseEvent) {
		e.preventDefault();
		const url = `${SITE_URL}${pastorsPath}`;
		const r = await nativeShare(forWords.shareTitle, url);
		if (r !== 'unavailable') return;
		try {
			await navigator.clipboard.writeText(url);
			forCopied = true;
			clearTimeout(forCopyTimer);
			forCopyTimer = setTimeout(() => (forCopied = false), 4000);
		} catch {
			void goto(pastorsPath);
		}
	}

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

	// Footer "Before you go" cards: the invitation (signed out), else the
	// signed-in reader's current book, else a way into the library. The invite
	// goes by `expectedUser` (drawing only): a member's stored session keeps it
	// off the dashboard the home page draws before the session restores.
	const showInvite = $derived(auth.enabled && !auth.expectedUser && !onLogin);
	const path = $derived(deLocalizeHref($page.url.pathname));
	// Home's hero always shows it, so home never even resolves it.
	const wantResume = $derived(!!auth.user && path !== '/');
	const resume = $derived.by(() => {
		const item = wantResume ? currentBook.item : null;
		return item && !pageShowsBook(path, item.slug) ? item : null;
	});

	// Resolved only while it could be shown AND the footer is within reach: it
	// may fetch the language's book list, and most page views never scroll here.
	let footerCards = $state<HTMLElement>();
	const cardsNear = elementVisible(() => footerCards, { rootMargin: '600px 0px' });
	$effect(() => {
		if (!wantResume || !cardsNear.visible) return;
		void lang.current;
		untrack(() => currentBook.refresh());
		return currentBook.watch();
	});

	// The row's colour and its "This week" line come from $lib/forMeta (each
	// group's accent and tagline), which is too big to ride in the layout every
	// page loads: fetched once the footer is within reach (the resume cards'
	// observer, at the footer's top). Until then the links are all there (and
	// prerendered), with plain dots.
	let forMeta = $state<typeof import('$lib/forMeta')>();
	$effect(() => {
		// A failed load (offline, a chunk gone after a deploy) leaves the plain
		// dots; the next time the footer comes into reach tries again.
		if (cardsNear.visible && !forMeta)
			import('$lib/forMeta').then(
				(m) => (forMeta = m),
				() => {}
			);
	});

	const blessing = $derived(blessingFor(lang.current));

	// Phone fold state: the ids of the link columns the reader has opened.
	let openCols = $state(new Set<string>());
	function toggleCol(id: string) {
		const next = new Set(openCols);
		if (!next.delete(id)) next.add(id);
		openCols = next;
	}

	// Tell FeedbackFab once the Account column — which carries "Send feedback" —
	// has scrolled into view, or past it to the rows below, so the floating
	// button steps aside instead of duplicating it over the footer's last rows.
	// The column, not the link: on a phone the link may be folded away while
	// its heading still shows.
	$effect(() => {
		if (!auth.enabled) return; // no Account column to watch
		const node = document.getElementById('footer-account-heading')?.closest('nav');
		if (!node || typeof IntersectionObserver === 'undefined') return;
		const io = new IntersectionObserver(([e]) => {
			footerFeedback.reached = e.isIntersecting || e.boundingClientRect.top < 0;
		});
		io.observe(node);
		return () => {
			io.disconnect();
			footerFeedback.reached = false;
		};
	});

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
</script>

<footer class="site-footer border-t border-border bg-surface-2">
	<!-- The footer sits under every page, so it orients rather than
	     decorates: a signed-out reader meets one invitation, everyone meets
	     two short link columns split by intent (where to read vs. what else
	     is here), and the utility links (About / Contact / Terms) sit in a
	     slim bar at the very bottom, where a reader looks for them last. An
	     indigo-to-gold hairline along the top edge is the one colourful
	     gesture — the signature pairing, kept to a 2px rule. -->

	<!-- "Before you go": a personal next step, then Reading Plans. Every
	     string is an existing translated key (the invitation's from the
	     sign-up flow), so the row mints no footer-only keys. -->
	{#snippet linkCard(icon: IconName, title: string, line: string, href: string, cta: string)}
		<div class="footer-card">
			<span class="footer-card-mark" aria-hidden="true"><Icon name={icon} size={22} /></span>
			<p class="footer-card-title">{title}</p>
			<p class="text-small text-muted">{line}</p>
			<a class="footer-card-link" {href}>{cta}<Icon name="chevron-right" size={16} /></a>
		</div>
	{/snippet}
	<div class="chrome-col px-5 pt-10 sm:pt-12" bind:this={footerCards}>
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
				<!-- Lazy: WorkCard brings the cover stack ($lib/components/FooterResume). -->
				{#await import('$lib/components/FooterResume.svelte')}
					<!-- Holds the cell so Reading Plans doesn't jump columns. -->
					<div aria-hidden="true"></div>
				{:then { default: FooterResume }}
					<FooterResume item={resume} />
				{/await}
			{:else}
				{@render linkCard(
					'compass',
					t('seals.nextBooks'),
					t('footer.tagline'),
					localizeHref('/books'),
					t('home.browseLibrary')
				)}
			{/if}
			{@render linkCard(
				'calendar',
				t('plans.title'),
				t('plans.tagline'),
				localizeHref('/plans'),
				t('seals.nextPlans')
			)}
		</div>
	</div>

	<!-- The closing word, verbatim from this locale's own Bible ($lib/benediction);
	     none where that Bible lacks it. lang/dir so it is voiced and set in its
	     own language. -->
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
			<blockquote>{blessing.text}</blockquote>
			<!-- bdi: the verse span keeps its own order inside an RTL caption. -->
			<figcaption>{blessing.book} <bdi dir="ltr">{blessing.passage}</bdi></figcaption>
		</figure>
	{/if}

	<!-- Content columns: brand · Explore · [Discover] · [My Account] ·
	     mission. Discover is English-only (see that block's note) and My
	     Account shows only where accounts exist, so the count runs 3–5 —
	     computed once in footerGridClass, which spells every reachable
	     grid-cols literal out for Tailwind's scanner. -->
	<!-- One link column. On a phone it folds to its heading (the footer had
	     grown a screen and a half tall there), opened by a toggle in the heading;
	     wider, the toggle is hidden and the heading reads plain. CSS decides
	     which, so the prerendered page (what crawlers read) carries every link
	     and nothing reflows after hydration. Only the visible half of the
	     heading names the landmark. -->
	{#snippet linkColumn(id: string, heading: string, list: Snippet)}
		<nav aria-labelledby={id} class="footer-col" class:open={openCols.has(id)}>
			<h2 {id} class="footer-heading">
				<span class="footer-col-label">{heading}</span>
				<button
					type="button"
					class="footer-col-toggle"
					aria-expanded={openCols.has(id)}
					onclick={() => toggleCol(id)}
				>
					{heading}<Icon name="chevron-right" size={16} mirror={false} class="footer-fold-chevron" />
				</button>
			</h2>
			{@render list()}
		</nav>
	{/snippet}
	<div
		class="footer-cols chrome-col grid grid-cols-2 gap-x-8 gap-y-10 px-5 py-10 sm:py-12 {footerGridClass}"
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
		{#snippet exploreList()}
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
		{/snippet}
		{@render linkColumn('footer-explore-heading', t('footer.explore'), exploreList)}
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
			{#snippet discoverList()}
				<ul class="footer-links">
				{#each ENGLISH_HUBS as d (d.href)}
					<li><a href="{d.href}/">{t(d.labelKey)}</a></li>
				{/each}
				<li><a href={pageHref(ORIGINALS_DEST.href)}>{t(ORIGINALS_DEST.labelKey)}</a></li>
				<li><a href={localizeHref('/rss/')}>RSS</a></li>
			</ul>
			{/snippet}
			{@render linkColumn('footer-discover-heading', 'Discover', discoverList)}
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
			{#snippet accountList()}
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
			{/snippet}
			{@render linkColumn('footer-account-heading', t('account.title'), accountList)}
		{/if}
		<!-- Mission rides in the grid rather than spanning the row on mobile
		     (unlike the brand column) so the link columns pair up two-per-row:
		     with Explore · Discover · My Account it makes an even 2×2 for a
		     signed-in English reader instead of leaving My Account stranded. -->
		<div class="footer-mission lg:col-span-1">
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
	{#snippet tile(code: string, name: string)}
		<span class="footer-lang-name">{name}</span>
		{#if LIVE_LOCALE_BOOKS[code]}
			<span class="footer-lang-count" lang={lang.current} dir={getTextDirection(lang.current)}
				>{LIVE_LOCALE_BOOKS[code]}
				{LIVE_LOCALE_BOOKS[code] === 1 ? t('common.bookOne') : t('common.bookMany')}</span
			>
		{/if}
	{/snippet}
	<nav
		class="border-t border-border"
		aria-label={t('footer.languages')}
	>
		<div class="chrome-col px-5 py-6">
			<p class="eyebrow mb-3 text-text">{t('footer.languages')}</p>
			<!-- Tiles: the autonym, and under it how many books wait in that
			     language (baked at build, $lib/live-locales.generated) — no
			     fallback, so each count is that language's own. The count is
			     worded in the reader's UI language, like every count on the site. -->
			<div class="footer-langs">
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
						class="footer-lang current"
						lang={l.code}
						dir={getTextDirection(l.code)}
						aria-current="true">{@render tile(l.code, l.native_name)}</span
					>
				{:else}
					<a
						href={localizeHref('/', { locale: l.code as (typeof locales)[number] })}
						class="footer-lang"
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
							// (Modifiers and button only, not defaultPrevented: isUnmodifiedPrimaryClick.)
							if (!isUnmodifiedPrimaryClick(e)) return;
							e.preventDefault();
							lang.choose(l.code);
						}}>{@render tile(l.code, l.native_name)}</a
					>
				{/if}
			{/each}
			</div>
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
	     families, parents ($lib/forLinks), as the footer's closing invitation:
	     a heading, the eighteen pages in four short columns (each link's dot in
	     its group's colour), this week's featured group and a way to pass the
	     site to a pastor. Only for readers of a language the pages are written
	     in (English, French): a reader of any other is not sent to copy they
	     can't read, and the words are the pages' own ($lib/forLinks), not
	     catalogue keys. -->
	{#if forLang === lang.current}
		<nav class="border-t border-border" aria-labelledby="footer-for-heading">
			<div class="footer-for chrome-col px-5 pt-10">
				<div>
					<a class="eyebrow footer-for-eyebrow hover:underline" href={forIndexPath(forLang)}
						>{FOR_EYEBROW[forLang]}</a
					>
					<h2 id="footer-for-heading" class="footer-for-title">{forWords.title}</h2>
					<p class="mt-2 text-small text-muted">{forWords.body}</p>
				</div>
				<div class="footer-for-families">
					{#each FOR_FAMILIES as fam (fam.id)}
						<div class="footer-for-family">
							<h3 class="footer-for-family-name">{fam[forLang]}</h3>
							<ul>
								{#each forFamilyLinks(fam.id) as l (l.slug)}
									<li>
										<a class="footer-for-link" href={forPath(l.slug, forLang)}
											><span
												class="footer-for-dot group-ink"
												style:--group={forMeta?.FOR_META[l.slug].accent}
												aria-hidden="true"
											></span>{forLabel(l, forLang)}</a
										>
									</li>
								{/each}
							</ul>
						</div>
					{/each}
				</div>
			</div>
			<div class="footer-for-foot chrome-col px-5">
				<p class="footer-for-week text-small text-muted">
					{#if forMeta}
						{@const featured = forOfTheWeek()}
						{forWords.thisWeek}
						<a class="footer-for-week-link hover:underline" href={forPath(featured.slug, forLang)}
							>{FOR_EYEBROW[forLang]} {forInline(featured, forLang)}</a
						>
						— {forMeta.forTagline(featured.slug, forLang)}.
					{/if}
				</p>
				<a class="btn btn-primary btn-sm footer-for-share" href={pastorsPath} onclick={passItOn}>
					<Icon name="share" size={16} />
					{forCopied ? forWords.copied : forWords.share}
				</a>
				<span class="sr-only" role="status">{forCopied ? forWords.copied : ''}</span>
			</div>
		</nav>
	{/if}
</footer>

<!-- Feedback modal, opened from the footer's My Account column (the account
     dropdown mounts its own). FeedbackDialog is signed-in only, and feedbackOpen
     is only ever set from the signed-in branch above. -->
{#if feedbackOpen}
	<!-- Loaded on first open: most visits never send feedback. -->
	{#await import('$lib/components/FeedbackDialog.svelte') then { default: FeedbackDialog }}
		<FeedbackDialog onClose={() => (feedbackOpen = false)} />
	{/await}
{/if}

<style>
	/* The footer's one colourful gesture: an indigo-to-gold hairline along the
	   top edge. Purely decorative, so it stays a 2px rule. */
	.site-footer {
		position: relative;
		/* Under every page and almost always below the fold: skip its style,
		   layout and paint until it nears the viewport, so a long page's
		   recalcs (every tap that changes state) don't pay for ~1,200px of
		   footer nobody is looking at (INP). `auto` remembers the real height
		   once rendered; the figure is the measured footer (≈1,500px on a
		   phone, ≈1,150–1,300px wider). Nothing in it is sticky or overflows
		   its box (paint containment would clip it), and its IntersectionObservers
		   (the resume card's 600px prefetch, the feedback hand-off) fire as before. */
		content-visibility: auto;
		contain-intrinsic-block-size: auto 1500px;
	}
	@media (min-width: 640px) {
		.site-footer {
			contain-intrinsic-block-size: auto 1250px;
		}
	}
	.site-footer::before {
		content: '';
		position: absolute;
		inset-block-start: 0;
		inset-inline: 0;
		block-size: 2px;
		background: linear-gradient(90deg, var(--accent) 0%, var(--accent) 55%, var(--gold) 100%);
	}

	/* "Ochorus for …": the invitation beside four columns on a wide screen,
	   above them on a narrow one; two columns on a phone. */
	.footer-for {
		display: grid;
		gap: 1.75rem 3.5rem;
	}
	@media (min-width: 1024px) {
		.footer-for {
			grid-template-columns: 18rem minmax(0, 1fr);
		}
	}
	/* Gold, deepened toward the ink so a 12px label still reads (4.5:1). */
	.footer-for-eyebrow {
		color: color-mix(in srgb, var(--gold) 70%, var(--text));
	}
	.footer-for-title,
	.footer-for-family-name {
		font-family: var(--font-display);
		font-weight: 600;
		color: var(--text);
	}
	.footer-for-title {
		margin-top: 0.5rem;
		font-size: var(--fs-h2);
		line-height: 1.15;
	}
	.footer-for-families {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 1.5rem;
	}
	@media (min-width: 768px) {
		.footer-for-families {
			grid-template-columns: repeat(4, minmax(0, 1fr));
		}
	}
	.footer-for-family {
		border-top: 2px solid var(--text);
		padding-top: 0.75rem;
	}
	.footer-for-family-name {
		margin-bottom: 0.25rem;
		font-size: var(--fs-body);
	}
	/* Each link a touch row: 44px on a phone, a tighter list once there's a
	   pointer to aim. */
	.footer-for-link {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		min-block-size: 2.75rem;
		font-size: var(--fs-small);
		color: var(--text);
	}
	@media (min-width: 768px) and (pointer: fine) {
		.footer-for-link {
			min-block-size: 1.9rem;
		}
	}
	.footer-for-link:hover {
		color: var(--accent);
		text-decoration: underline;
	}
	/* The group's colour as a dot in a soft ring of itself: its page's accent
	   ($lib/forMeta) through .group-ink, which leans it toward the ink so it
	   reads in either theme; a plain muted dot until that has loaded. */
	.footer-for-dot {
		--group: var(--border-strong);
		flex: none;
		inline-size: 0.5rem;
		block-size: 0.5rem;
		border-radius: 50%;
		background: currentColor;
		box-shadow: 0 0 0 0.3rem color-mix(in srgb, currentColor 18%, transparent);
		margin-inline: 0.3rem;
	}
	.footer-for-foot {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 1rem 1.5rem;
		margin-top: 1.75rem;
		padding-block: 1.1rem 1.5rem;
		border-top: 1px solid var(--border);
	}
	/* Filled in once forMeta loads (off screen): its room held so nothing
	   below it moves. */
	.footer-for-week {
		flex: 1 1 24rem;
		min-block-size: 1.5em;
	}
	.footer-for-week-link {
		font-weight: 600;
		color: var(--text);
	}
	/* .btn-primary, as a pill with a touch row's height and room at its
	   rounded ends. */
	.footer-for-share {
		min-block-size: 2.75rem;
		padding-inline: 1.1rem;
		border-radius: 999px;
	}

	/* Language tiles: autonym over its book count. Auto-fill columns, so a
	   phone gets two or three across and a desktop all ten in a row or two.
	   Each is at least 3rem tall: a mis-tap here doesn't scroll, it switches
	   the whole site's language. */
	.footer-langs {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(8.5rem, 1fr));
		gap: 0.5rem;
	}
	.footer-lang {
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
		min-block-size: 3rem;
		justify-content: center;
		padding: 0.55rem 0.85rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--surface);
		color: var(--text);
		text-decoration: none;
		transition: border-color var(--duration-fast) ease;
	}
	a.footer-lang:hover {
		border-color: var(--accent);
		text-decoration: none;
	}
	.footer-lang.current {
		border-color: var(--accent);
		box-shadow: inset 0 -2px 0 var(--gold);
	}
	.footer-lang-name {
		font-family: var(--font-display);
		font-size: var(--fs-body);
		font-weight: 600;
		white-space: nowrap;
	}
	.footer-lang-count {
		font-size: var(--fs-small);
		color: var(--muted);
	}

	/* Phone link columns: each folds to a ruled row, its heading's toggle the
	   tap target and a chevron that turns as it opens. Wider, the toggle is
	   hidden and the plain label shows. */
	.footer-col-toggle {
		display: none;
	}
	@media (max-width: 639.98px) {
		.footer-cols {
			row-gap: 0;
		}
		.footer-cols > :first-child {
			margin-block-end: 1.5rem;
		}
		.footer-col {
			grid-column: 1 / -1;
			border-block: 1px solid var(--border);
		}
		.footer-col + .footer-col {
			border-block-start: 0;
		}
		.footer-col .footer-heading {
			margin: 0;
		}
		.footer-col-label {
			display: none;
		}
		.footer-col-toggle {
			display: flex;
			inline-size: 100%;
			min-block-size: 3rem;
			align-items: center;
			justify-content: space-between;
			padding: 0;
			border: 0;
			background: none;
			font: inherit;
			letter-spacing: inherit;
			text-transform: inherit;
			color: inherit;
			cursor: pointer;
		}
		.footer-col:not(.open) :global(.footer-links) {
			display: none;
		}
		.footer-col.open :global(.footer-links) {
			padding-block-end: 1rem;
		}
		.footer-mission {
			grid-column: 1 / -1;
			margin-block-start: 2rem;
		}
	}
	.footer-col :global(.footer-fold-chevron) {
		color: var(--muted);
		transition: rotate var(--duration-fast) ease;
	}
	.footer-col.open :global(.footer-fold-chevron) {
		rotate: 90deg;
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
	/* The chevron already flips in RTL (Icon's .dir-flip); the hover nudge uses
	   `translate`, which composes with that flip instead of replacing it. */
	.footer-card-link :global(svg) {
		transition: translate var(--duration-fast) ease;
	}
	.footer-card-link:hover :global(svg) {
		translate: 3px;
	}
	:global([dir='rtl']) .footer-card-link:hover :global(svg) {
		translate: -3px;
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
	.footer-invite .footer-invite-cta {
		margin-block-start: auto;
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
	/* These scripts' display faces have no italic, so the browser would fake
	   a slant. (app.css keeps Korean upright site-wide, but this scoped italic
	   outranks it, so Korean is named here too.) */
	.footer-blessing:is(:lang(ar), :lang(hi), :lang(am), :lang(ko)) blockquote {
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
		.footer-card-link:hover :global(svg) {
			translate: none;
		}
		.footer-col :global(.footer-fold-chevron),
		.footer-lang {
			transition: none;
		}
		.footer-invite-cta:hover::after {
			animation: none;
		}
	}
</style>
