<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { theme } from '$lib/theme.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { listen } from '$lib/listen.svelte';
	import { browser } from '$app/environment';
	import { lang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { auth } from '$lib/auth.svelte';
	import { pwa } from '$lib/pwa.svelte';
	import { localizeHref, getLocale, getTextDirection } from '$lib/paraglide/runtime';
	import AccountMenu from '$lib/components/AccountMenu.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import PwaToasts from '$lib/components/PwaToasts.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import type { IconName } from '$lib/components/Icon.svelte';
	import BrandMark from '$lib/components/BrandMark.svelte';

	let { children } = $props();
	const t = i18n.t;

	onMount(() => {
		theme.init();
		readerPrefs.init();
		auth.init();
		pwa.init();
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
		void readerPrefs.scale;
		void listen.rate;
		void listen.voiceURI;
		if (auth.user) auth.pushPrefs();
	});

	// App destinations only — About Us and Contact live in the footer (matching
	// Take Root, whose app nav carries five primary destinations).
	const NAV = $derived<{ href: string; label: string; icon: IconName }[]>([
		{ href: '/', label: t('nav.dashboard'), icon: 'grid' },
		{ href: '/books', label: t('nav.books'), icon: 'book' },
		{ href: '/topics', label: t('nav.topics'), icon: 'tag' },
		{ href: '/plans', label: t('nav.plans'), icon: 'calendar' },
		{ href: '/sermons', label: t('nav.sermons'), icon: 'mic' },
		{ href: '/biographies', label: t('nav.biographies'), icon: 'users' },
		{ href: '/search', label: t('nav.search'), icon: 'search' }
	]);

	// The reroute hook strips the locale prefix before routing, so page.route.id
	// is the canonical path ("/books", "/books/[slug]") — compare against that.
	const isActive = (href: string) =>
		href === '/' ? $page.route.id === '/' : ($page.route.id?.startsWith(href) ?? false);

	// Mobile nav drawer (collapsed behind a hamburger on small screens).
	let navOpen = $state(false);
</script>

<svelte:window
	onkeydown={(e) => {
		if (e.key === 'Escape') navOpen = false;
	}}
/>

<div class="flex min-h-screen flex-col">
	{#if !readerUi.focus}
		<nav class="appnav">
			<div class="appnav-inner">
			<a class="brand" href={localizeHref('/')}><BrandMark size={24} /><span>Ochorus</span></a>
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
				<div class="navctl">
					<!-- Settings (theme, language, reading, voice all live on the page now). -->
					<a
						class="prefs-btn"
						href={localizeHref('/settings')}
						aria-label={t('settings.title')}
						title={t('settings.title')}
						onclick={() => (navOpen = false)}
					>
						<Icon name="gear" size={19} />
					</a>
					<AccountMenu />
				</div>
			</div>
			</div>
		</nav>
	{/if}

	<main class="flex-1">
		{@render children()}
	</main>

	{#if !readerUi.focus}
		<footer class="border-t border-border bg-surface-2">
			<div class="mx-auto grid max-w-5xl gap-8 px-5 py-12 sm:grid-cols-3">
				<div>
					<div class="flex items-center gap-2 text-display !text-xl !text-text">
						<BrandMark size={22} /><span>Ochorus</span>
					</div>
					<p class="mt-2 max-w-xs text-small text-muted">
						{t('footer.tagline')}
					</p>
				</div>
				<div>
					<h3 class="mb-3 text-small font-semibold uppercase tracking-wider text-text">{t('footer.explore')}</h3>
					<ul class="space-y-2 text-small text-muted">
						<li><a href={localizeHref('/books')} class="hover:text-text">{t('nav.books')}</a></li>
						<li><a href={localizeHref('/topics')} class="hover:text-text">{t('nav.topics')}</a></li>
						<li><a href={localizeHref('/plans')} class="hover:text-text">{t('nav.plans')}</a></li>
						<li><a href={localizeHref('/sermons')} class="hover:text-text">{t('nav.sermons')}</a></li>
						<li><a href={localizeHref('/biographies')} class="hover:text-text">{t('nav.biographies')}</a></li>
						<li><a href={localizeHref('/notebook')} class="hover:text-text">{t('notebook.title')}</a></li>
						<li><a href={localizeHref('/about')} class="hover:text-text">{t('nav.about')}</a></li>
						<li><a href={localizeHref('/contact')} class="hover:text-text">{t('nav.contact')}</a></li>
					</ul>
				</div>
				<div>
					<h3 class="mb-3 text-small font-semibold uppercase tracking-wider text-text">{t('footer.newsletter')}</h3>
					<p class="text-small text-muted">
						{t('footer.reachUs')}
						<a href="mailto:support@ochorus.com" class="text-accent">support@ochorus.com</a>.
					</p>
					<p class="mt-4 text-[0.78rem] text-muted">
						{t('footer.ministry')}
					</p>
				</div>
			</div>
		</footer>
	{/if}
</div>

<CommandPalette />
<PwaToasts />
