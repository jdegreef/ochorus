<script lang="ts">
	/**
	 * The site's destinations, at the foot of a reading surface's "⋯" group.
	 *
	 * The chapter reader and the sermon page draw no site nav and no footer
	 * (design #7: one slim bar while reading — see the root layout's
	 * `siteChrome`), so this is where the rest of Ochorus stays one tap away:
	 * Home, then the primary journeys in `primaryNav` order (the Bible among
	 * them where its books have shipped) — the same list the nav, the footer
	 * and the palette map, so the four cannot drift — then
	 * Settings, which stands in for the nav's gear and account menu (palette,
	 * site style, language, sign-in).
	 */
	import Icon from './Icon.svelte';
	import { primaryNav } from '$lib/contentNav';
	import { lang } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';

	/** Called as a link is followed, so the group can close itself. */
	let { onpick }: { onpick: () => void } = $props();
	const t = i18n.t;
</script>

<div class="site-links" role="group" aria-label={t('a11y.mainNav')}>
	<a class="account-item more-item site-link" href={localizeHref('/')} onclick={onpick}
		><Icon name="grid" size={20} />{t('nav.home')}</a
	>
	{#each primaryNav(lang.current) as d (d.href)}
		<a class="account-item more-item site-link" href={localizeHref(d.href)} onclick={onpick}
			><Icon name={d.icon} size={20} />{t(d.labelKey)}</a
		>
	{/each}
	<a class="account-item more-item site-link" href={localizeHref('/settings')} onclick={onpick}
		><Icon name="gear" size={20} />{t('settings.title')}</a
	>
</div>

<style>
	/* A rule off the reading tools above it, and muted: these are the way out
	   of the text, not tools for it. Row shape is the shared `.more-item`. */
	.site-links {
		margin-top: 0.35rem;
		padding-top: 0.35rem;
		border-top: 1px solid var(--border);
	}
	.site-link {
		color: var(--muted);
	}
	.site-link:hover {
		color: var(--text);
	}
</style>
