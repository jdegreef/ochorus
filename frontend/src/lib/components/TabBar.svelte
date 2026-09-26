<script lang="ts">
	import { page } from '$app/stores';
	import Icon from '$lib/components/Icon.svelte';
	import type { IconName } from '$lib/components/Icon.svelte';
	import MoreSheet from '$lib/components/MoreSheet.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { PRIMARY_NAV, ENGLISH_HUBS, ORIGINALS_DEST } from '$lib/contentNav';

	/** The phone app bar, in thumb reach; the layout decides where it shows. */
	const t = i18n.t;
	let moreOpen = $state(false);

	/** Every browse destination counts as "Library" — the tab is the shelf. */
	const LIBRARY = [...PRIMARY_NAV, ...ENGLISH_HUBS, ORIGINALS_DEST]
		.map((d) => d.href)
		.concat('/authors', '/series');
	const routeId = $derived($page.route.id ?? '');
	const under = (prefixes: string[]) => prefixes.some((p) => routeId === p || routeId.startsWith(`${p}/`));

	const TABS = $derived<{ href: string; label: string; icon: IconName; active: boolean }[]>([
		{ href: '/', label: t('nav.home'), icon: 'grid', active: routeId === '/' },
		{ href: '/books', label: t('common.library'), icon: 'book', active: under(LIBRARY) },
		{ href: '/search', label: t('nav.search'), icon: 'search', active: under(['/search']) },
		{
			href: '/favorites',
			label: t('fav.yourFavorites'),
			icon: 'bookmark',
			active: under(['/favorites', '/notebook'])
		}
	]);
</script>

<nav class="tabbar" aria-label={t('nav.tabBar')}>
	{#each TABS as tab (tab.href)}
		<a
			href={localizeHref(tab.href)}
			class="tab"
			class:active={tab.active}
			aria-current={tab.active ? 'page' : undefined}
		>
			<span class="tab-icon"><Icon name={tab.icon} size={22} /></span>
			<span class="tab-label">{tab.label}</span>
		</a>
	{/each}
	<button
		class="tab"
		class:active={moreOpen}
		aria-haspopup="dialog"
		aria-expanded={moreOpen}
		onclick={() => (moreOpen = true)}
	>
		<span class="tab-icon"><Icon name="more" size={22} /></span>
		<span class="tab-label">{t('nav.more')}</span>
	</button>
</nav>

<MoreSheet bind:open={moreOpen} />

<style>
	/* Phones only. The scoped `display` lives in the media query — a `sm:hidden`
	   utility would be out-ranked by it and leak the bar onto desktop. */
	.tabbar {
		display: none;
	}
	@media (max-width: 639.98px) {
		.tabbar {
			position: fixed;
			inset-inline: 0;
			bottom: 0;
			z-index: 40;
			display: flex;
			padding-bottom: env(safe-area-inset-bottom);
			border-top: 1px solid var(--border);
			background: var(--surface);
		}
		/* Published for fixed bottom UI (the PWA toasts, the layout's clearance)
		   so nothing sits underneath the bar. */
		:global(:root:has(.tabbar)) {
			/* .tab's min-height + the 1px top border + the home-indicator strip. */
			--tabbar-h: calc(3.6rem + 1px + env(safe-area-inset-bottom));
		}
	}
	.tab {
		flex: 1 1 0;
		min-width: 0;
		min-height: 3.6rem;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.15rem;
		color: var(--muted);
		text-decoration: none;
	}
	.tab:hover {
		color: var(--text);
		text-decoration: none;
	}
	.tab-icon {
		width: 3.5rem;
		height: 1.9rem;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 999px;
	}
	.tab-label {
		max-width: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: var(--fs-eyebrow);
		font-weight: 600;
	}
	.tab.active {
		color: var(--accent);
	}
	.tab.active .tab-icon {
		background: var(--accent-soft);
	}
</style>
