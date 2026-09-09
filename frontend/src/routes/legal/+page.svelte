<script lang="ts">
	import { SITE_URL } from '$lib/config';
	import { hreflangAll, jsonLd } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import Seo from '$lib/components/Seo.svelte';

	const t = i18n.t;

	const path = '/legal';
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);

	// WebPage, a leaf of the WebSite — the schema counterpart every hub/leaf
	// already carries. One page holds both privacy and terms (the footer link is
	// "Privacy & Terms"), so a single WebPage names the pair; names and
	// description reuse the same i18n strings the visible page and <Seo> use.
	const legalLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'WebPage',
			name: t('legal.title'),
			description: t('legal.metaDescription'),
			url: canonical,
			isPartOf: { '@type': 'WebSite', name: 'Ochorus', url: SITE_URL },
			isAccessibleForFree: true
		})
	);
</script>

<Seo
	title="{t('legal.title')} — Ochorus"
	description={t('legal.metaDescription')}
	{canonical}
	hreflang={hreflangAll(path)}
	ogImage="{SITE_URL}/og/default.png"
	structuredData={[legalLd]}
/>

<div class="reading-page">
	<p class="eyebrow mb-2 text-accent">Ochorus</p>
	<h1 class="text-h1 mb-3">{t('legal.title')}</h1>
	<!-- Two documents on one page: the footer link says "Privacy & Terms", so a
	     reader arriving for one of them needs to see both and pick. -->
	<nav class="mb-6 flex flex-wrap gap-x-4 gap-y-1 text-small" aria-label={t('legal.title')}>
		<a href="#privacy">{t('legal.privacyHeading')}</a>
		<a href="#terms">{t('legal.termsHeading')}</a>
	</nav>

	<div class="space-y-5 text-body text-muted">
		<p>{t('legal.intro')}</p>

		<h2 id="privacy" class="text-h2 text-text pt-2 scroll-mt-24">{t('legal.privacyHeading')}</h2>
		<p>{t('legal.privacyP1')}</p>
		<p>{t('legal.privacyP2')}</p>
		<p>{t('legal.privacyP3')}</p>
		<p>{t('legal.privacyP4')}</p>
		<p>{t('legal.privacyP5')}</p>

		<h2 id="terms" class="text-h2 text-text pt-2 scroll-mt-24">{t('legal.termsHeading')}</h2>
		<p>{t('legal.termsP1')}</p>
		<p>{t('legal.termsP2')}</p>
		<p>{t('legal.termsP3')}</p>
		<p>{t('legal.termsP4')}</p>
		<p>{t('legal.termsP5')}</p>

		<p class="pt-2 text-small">{t('legal.ministry')}</p>
		<p class="text-small">{t('legal.updated')}</p>
	</div>

	<div class="mt-10">
		<a href={localizeHref('/about')} class="btn btn-ghost">{t('nav.about')}</a>
	</div>
</div>
