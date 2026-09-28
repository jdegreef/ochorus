<script lang="ts">
	// $lib/href, not the raw Paraglide runtime: a non-final detail crumb (the
	// reader's book link) must get its trailing slash or it falls through to the
	// SPA shell instead of the prerendered page. Index-page crumbs are left
	// unslashed by that helper, so nothing else changes.
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';

	// A visible breadcrumb trail for detail pages — the on-page counterpart of
	// the JSON-LD BreadcrumbList in the head (see seo.ts breadcrumb()), so the
	// two describe the same path. Items run from the site root; the LAST item is
	// the current page, rendered as plain text with aria-current rather than a
	// link. Hrefs are unlocalized app paths — localizeHref adds the locale prefix.
	let { items }: { items: { name: string; href: string }[] } = $props();
	const t = i18n.t;
</script>

<!-- A list, so a screen reader announces "list, N items" and each crumb's
     place in the trail. -->
<nav class="mb-5 text-small text-muted" aria-label={t('a11y.breadcrumb')}>
	<ol class="flex flex-wrap items-center gap-1.5">
		{#each items as item, i (item.href)}
			{#if i < items.length - 1}
				<li class="flex items-center gap-1.5">
					<a href={localizeHref(item.href)} class="hover:text-text"><bdi>{item.name}</bdi></a>
					<!-- No flip: › is a bidi-mirrored character, drawn as ‹ in RTL already. -->
					<span aria-hidden="true">›</span>
				</li>
			{:else}
				<li class="flex min-w-0">
					<span class="truncate text-text" aria-current="page"><bdi>{item.name}</bdi></span>
				</li>
			{/if}
		{/each}
	</ol>
</nav>
