<script lang="ts">
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumbLd, hreflangFor, absUrl } from '$lib/seo';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import WhoseWords from '$lib/components/WhoseWords.svelte';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;
	const path = '/quotes/game/';
	const canonical = `${SITE_URL}${path}`;
	const hreflang = hreflangFor(path, ['en']);

	// English literals, as on the other quote pages: what they describe is English.
	const title = 'Whose words? A daily Christian quotation game — Ochorus';
	const description =
		'One quotation a day from the classic Christian writers — Spurgeon, Andrew Murray, ' +
		'Augustine, John Wesley and more. Guess who said it from four portraits, then read ' +
		'the line in the book it comes from, free.';

	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.quotes'), href: '/quotes/' },
		{ name: t('game.title'), href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));
	const gameLd = jsonLd({
		'@context': 'https://schema.org',
		'@type': 'Game',
		name: 'Whose words?',
		description,
		url: canonical,
		inLanguage: 'en',
		isAccessibleForFree: true
	});
</script>

<Seo
	{title}
	{description}
	{canonical}
	{hreflang}
	ogImage={absUrl('/og/quotes.png')}
	structuredData={[crumbsLd, gameLd]}
/>

<div class="page-col px-5 py-10">
	<PageHeader title={t('game.title')} tagline={t('game.tagline')} />
	<WhoseWords />
</div>
