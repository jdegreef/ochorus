<script lang="ts">
	import { CONTACT_EMAIL, SITE_URL } from '$lib/config';
	import { hreflangAll, jsonLd } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import Seo from '$lib/components/Seo.svelte';

	const t = i18n.t;

	const path = '/contact';
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);

	// ContactPage, a leaf of the WebSite — the schema counterpart every hub/leaf
	// already carries. Names and description reuse the same i18n strings the
	// visible page and <Seo> use, so the three can't drift.
	const contactLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'ContactPage',
			name: t('contact.heading'),
			description: t('contact.metaDescription'),
			url: canonical,
			isPartOf: { '@type': 'WebSite', name: 'Ochorus', url: SITE_URL },
			isAccessibleForFree: true
		})
	);
</script>

<Seo
	title="{t('nav.contact')} — Ochorus"
	description={t('contact.metaDescription')}
	{canonical}
	hreflang={hreflangAll(path)}
	ogImage="{SITE_URL}/og/default.png"
	structuredData={[contactLd]}
/>

<div class="reading-page">
	<p class="eyebrow mb-2 text-accent">{t('nav.contact')}</p>
	<h1 class="text-h1 mb-6">{t('contact.heading')}</h1>

	<p class="text-body text-muted">
		{t('contact.intro')}
	</p>

	<!-- The page said "a direct contact option is coming soon" while About and the
	     footer both sent people here to get in touch — so the one page named
	     Contact was the one page you could not contact anyone from. The address
	     is the ministry's existing support mailbox (see DEPLOYMENT.md §5). -->
	<div class="mt-8 rounded-card border border-border bg-surface-2 p-6">
		<h2 class="text-h2 mb-1">{t('contact.emailLabel')}</h2>
		<p class="mb-4 text-small text-muted">{t('contact.emailSub')}</p>
		<a class="btn btn-primary" href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>
	</div>

	<div class="mt-4 rounded-card border border-border p-6">
		<h2 class="text-h2 mb-1">{t('contact.title')}</h2>
		<p class="text-small text-muted">
			{t('contact.messageSub')}
		</p>
	</div>

	<p class="mt-8 text-small text-muted">{t('contact.basedIn')}</p>
</div>
