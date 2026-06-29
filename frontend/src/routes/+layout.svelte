<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { theme } from '$lib/theme.svelte';

	let { children } = $props();
	onMount(() => theme.init());

	const NAV = [
		{ href: '/about', label: 'About Us' },
		{ href: '/books', label: 'Books' },
		{ href: '/biographies', label: 'Biographies' },
		{ href: '/contact', label: 'Contact' }
	];

	const isActive = (href: string) =>
		href === '/' ? $page.url.pathname === '/' : $page.url.pathname.startsWith(href);
</script>

<div class="flex min-h-screen flex-col">
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
					class="ml-1 rounded-md px-2.5 py-1.5 text-small text-muted hover:bg-surface-2"
					onclick={() => theme.toggle()}
					aria-label="Toggle light and dark theme"
					title="Toggle theme"
				>
					{theme.current === 'dark' ? '☾' : '☀'}
				</button>
			</nav>
		</div>
	</header>

	<main class="flex-1">
		{@render children()}
	</main>

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
					<li><a href="/books" class="hover:text-text">Books</a></li>
					<li><a href="/biographies" class="hover:text-text">Biographies</a></li>
					<li><a href="/about" class="hover:text-text">About Us</a></li>
					<li><a href="/contact" class="hover:text-text">Contact</a></li>
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
</div>
