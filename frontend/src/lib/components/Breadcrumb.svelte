<script lang="ts">
	import { localizeHref } from '$lib/paraglide/runtime';
	import { i18n } from '$lib/i18n.svelte';

	// A visible breadcrumb trail for detail pages — the on-page counterpart of
	// the JSON-LD BreadcrumbList in the head (see seo.ts breadcrumb()), so the
	// two describe the same path. Items run from the site root; the LAST item is
	// the current page, rendered as plain text with aria-current rather than a
	// link. Hrefs are unlocalized app paths — localizeHref adds the locale prefix.
	let { items }: { items: { name: string; href: string }[] } = $props();
	const t = i18n.t;
</script>

<nav
	class="mb-5 flex flex-wrap items-center gap-1.5 text-small text-muted"
	aria-label={t('a11y.breadcrumb')}
>
	{#each items as item, i (item.href)}
		{#if i < items.length - 1}
			<a href={localizeHref(item.href)} class="hover:text-text">{item.name}</a>
			<span aria-hidden="true">›</span>
		{:else}
			<span class="truncate text-text" aria-current="page">{item.name}</span>
		{/if}
	{/each}
</nav>
