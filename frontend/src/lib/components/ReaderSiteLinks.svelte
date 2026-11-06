<script lang="ts">
	/**
	 * The site's destinations, at the foot of a reading surface's "⋯" group.
	 *
	 * The chapter reader and the sermon page draw no site nav and no footer
	 * (design #7: one slim bar while reading — see the root layout's
	 * `siteChrome`), so this is where the rest of Ochorus stays one tap away:
	 * Home, then the primary journeys in PRIMARY_NAV's order — the same list
	 * the nav, the footer and the palette map, so the four cannot drift.
	 */
	import Icon from './Icon.svelte';
	import { PRIMARY_NAV } from '$lib/contentNav';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';

	/** Called as a link is followed, so the group can close itself. */
	let { onpick }: { onpick: () => void } = $props();
	const t = i18n.t;
</script>

<div class="site-links" role="group" aria-label={t('a11y.mainNav')}>
	<a class="account-item site-link" href={localizeHref('/')} onclick={onpick}
		><Icon name="grid" size={18} />{t('nav.home')}</a
	>
	{#each PRIMARY_NAV as d (d.href)}
		<a class="account-item site-link" href={localizeHref(d.href)} onclick={onpick}
			><Icon name={d.icon} size={18} />{t(d.labelKey)}</a
		>
	{/each}
</div>

<style>
	/* A rule off the reading tools above it, then compact rows: these are the
	   way out of the text, not tools for it. */
	.site-links {
		margin-top: 0.35rem;
		padding-top: 0.35rem;
		border-top: 1px solid var(--border);
	}
	.site-link {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		color: var(--muted);
	}
	.site-link:hover {
		color: var(--text);
	}
</style>
