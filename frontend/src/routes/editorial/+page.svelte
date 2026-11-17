<script lang="ts">
	import PageHeader from '$lib/components/PageHeader.svelte';
	import { CONTACT_EMAIL, SITE_URL } from '$lib/config';
	import { hreflangAll, jsonLd } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import Seo from '$lib/components/Seo.svelte';

	const t = i18n.t;

	const path = '/editorial';
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);

	// How the texts are chosen, sourced, edited and translated — the trust story
	// of a site that republishes public-domain works, and the page the home and
	// About pages' Organization names as its `publishingPrinciples` ($lib/seo).
	const sections = [
		'choosing',
		'sources',
		'editing',
		'translating',
		'scripture',
		'originals'
	] as const;

	const pageLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'WebPage',
			name: t('editorial.title'),
			description: t('editorial.metaDescription'),
			url: canonical,
			isPartOf: { '@type': 'WebSite', name: 'Ochorus', url: SITE_URL },
			isAccessibleForFree: true
		})
	);

	// The address is set as text and a mailto link, never inside the catalogue
	// string, so a changed CONTACT_EMAIL needs no translation.
	const [beforeEmail, afterEmail] = $derived(t('editorial.correctionsP').split('%email%'));
</script>

<Seo
	title="{t('editorial.title')} — Ochorus"
	description={t('editorial.metaDescription')}
	{canonical}
	hreflang={hreflangAll(path)}
	ogImage="{SITE_URL}/og/default.png"
	structuredData={[pageLd]}
/>

<div class="reading-page">
	<PageHeader title={t('editorial.title')} />

	<div class="space-y-5 text-body text-muted">
		<p>{t('editorial.intro')}</p>

		{#each sections as s (s)}
			<h2 id={s} class="text-h2 text-text pt-2 scroll-mt-24">{t(`editorial.${s}Heading`)}</h2>
			<p>{t(`editorial.${s}P`)}</p>
		{/each}

		<h2 id="corrections" class="text-h2 text-text pt-2 scroll-mt-24">
			{t('editorial.correctionsHeading')}
		</h2>
		<p>
			{beforeEmail}<a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>{afterEmail ?? ''}
		</p>
	</div>

	<div class="mt-10">
		<a href={localizeHref('/about')} class="btn btn-ghost">{t('nav.about')}</a>
	</div>
</div>
