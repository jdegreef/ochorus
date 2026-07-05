<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { theme } from '$lib/theme.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { lang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { auth } from '$lib/auth.svelte';
	import { pwa } from '$lib/pwa.svelte';
	import { listLanguages } from '$lib/library';
	import LanguagePicker from '$lib/components/LanguagePicker.svelte';
	import AccountMenu from '$lib/components/AccountMenu.svelte';
	import PwaToasts from '$lib/components/PwaToasts.svelte';

	let { children } = $props();
	const t = i18n.t;

	onMount(async () => {
		theme.init();
		lang.init();
		i18n.init(lang.current);
		readerPrefs.init();
		auth.init();
		pwa.init();
		try {
			lang.setAvailable(await listLanguages());
		} catch {
			/* keep the English default if the API is unreachable */
		}
	});

	// When signed in, mirror preference changes back to the profile (debounced).
	$effect(() => {
		// touch the values so the effect tracks them
		void theme.current;
		void readerPrefs.scale;
		void lang.current;
		if (auth.user) auth.pushPrefs();
	});

	const NAV = $derived([
		{ href: '/about', label: t('nav.about') },
		{ href: '/books', label: t('nav.books') },
		{ href: '/plans', label: t('nav.plans') },
		{ href: '/biographies', label: t('nav.biographies') },
		{ href: '/contact', label: t('nav.contact') }
	]);

	const isActive = (href: string) =>
		href === '/' ? $page.url.pathname === '/' : $page.url.pathname.startsWith(href);
</script>

<div class="flex min-h-screen flex-col">
	{#if !readerUi.focus}
		<header class="sticky top-0 z-20 border-b border-border bg-bg/90 backdrop-blur">
			<div class="mx-auto flex max-w-5xl items-center justify-between gap-4 px-5 py-3.5">
				<a href="/" class="text-display !text-2xl !text-text hover:no-underline">Ochorus</a>
				<nav class="flex items-center gap-1 sm:gap-2">
					{#each NAV as item (item.href)}
						<a
							href={item.href}
							class="rounded-md px-2.5 py-1.5 text-small font-medium hover:bg-surface-2 hover:no-underline sm:px-3"
							class:text-text={isActive(item.href)}
							class:text-muted={!isActive(item.href)}
							aria-current={isActive(item.href) ? 'page' : undefined}
						>
							{item.label}
						</a>
					{/each}
					<button
						class="rounded-md px-2.5 py-1.5 text-small text-muted hover:bg-surface-2"
						onclick={() => goto('/search')}
						aria-label={t('nav.search')}
						title={t('nav.search')}
					>
						⌕
					</button>
					<LanguagePicker />
					<button
						class="rounded-md px-2.5 py-1.5 text-small text-muted hover:bg-surface-2"
						onclick={() => theme.toggle()}
						aria-label="Toggle light and dark theme"
						title="Toggle theme"
					>
						{theme.current === 'dark' ? '☾' : '☀'}
					</button>
					<AccountMenu />
				</nav>
			</div>
		</header>
	{/if}

	<main class="flex-1">
		{@render children()}
	</main>

	{#if !readerUi.focus}
		<footer class="border-t border-border bg-surface-2">
			<div class="mx-auto grid max-w-5xl gap-8 px-5 py-12 sm:grid-cols-3">
				<div>
					<div class="text-display !text-xl !text-text">Ochorus</div>
					<p class="mt-2 max-w-xs text-small text-muted">
						Equipping people with classic Christian books — free to read, in your language.
					</p>
				</div>
				<div>
					<h3 class="mb-3 text-small font-semibold uppercase tracking-wider text-text">Explore</h3>
					<ul class="space-y-2 text-small text-muted">
						<li><a href="/books" class="hover:text-text">{t('nav.books')}</a></li>
						<li><a href="/biographies" class="hover:text-text">{t('nav.biographies')}</a></li>
						<li><a href="/about" class="hover:text-text">{t('nav.about')}</a></li>
						<li><a href="/contact" class="hover:text-text">{t('nav.contact')}</a></li>
					</ul>
				</div>
				<div>
					<h3 class="mb-3 text-small font-semibold uppercase tracking-wider text-text">Newsletter</h3>
					<p class="text-small text-muted">
						Reach us at
						<a href="mailto:support@ochorus.com" class="text-accent">support@ochorus.com</a>.
					</p>
					<p class="mt-4 text-[0.78rem] text-muted">A ministry since 2021 · Kampala, Uganda</p>
				</div>
			</div>
		</footer>
	{/if}
</div>

<PwaToasts />
