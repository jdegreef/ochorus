<script lang="ts">
	import { SITE_URL } from '$lib/config';
	import { hreflangAll } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import Seo from '$lib/components/Seo.svelte';

	const t = i18n.t;

	const path = '/about';
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
</script>

<Seo
	title="{t('nav.about')} — Ochorus"
	description={t('about.metaDescription')}
	{canonical}
	hreflang={hreflangAll(path)}
	ogImage="{SITE_URL}/og/default.png"
/>

<div class="mx-auto max-w-2xl px-5 py-12">
	<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">{t('nav.about')}</p>
	<h1 class="text-h1 mb-8">{t('about.title')}</h1>

	<div class="reading-page space-y-5 text-body text-muted">
		<h2 class="text-h2 !text-text">{t('about.heading')}</h2>
		<p>{t('about.p1')}</p>
		<p>{t('about.p2')}</p>
		<p>{t('about.p3')}</p>
		<p>{t('about.p4')}</p>

		<h2 class="text-h2 !text-text pt-4">{t('about.outreachHeading')}</h2>
		<p>{t('about.outreachP1')}</p>
		<p>{t('about.outreachP2')}</p>
	</div>

	<!-- Rooted in Scripture: three verses as callouts. Public-domain wording
	     (WEB in English); the es/sw/lg renderings await a native-review pass. -->
	<section class="mt-12">
		<h2 class="text-h2 !text-text mb-5">{t('about.scripturesHeading')}</h2>
		<div class="space-y-4">
			{#each [['about.scripture1', 'about.scripture1Ref'], ['about.scripture2', 'about.scripture2Ref'], ['about.scripture3', 'about.scripture3Ref']] as [text, ref] (ref)}
				<figure class="rounded-card border-s-2 border-gold bg-surface-2 py-4 pe-4 ps-5">
					<blockquote class="text-body text-text" style="font-family: var(--font-display)">
						“{t(text)}”
					</blockquote>
					<figcaption class="mt-2 text-small text-muted">{t(ref)}</figcaption>
				</figure>
			{/each}
		</div>
	</section>

	<div class="mt-10 flex flex-wrap gap-3">
		<a href={localizeHref('/books')} class="btn btn-primary">{t('home.browseLibrary')}</a>
		<a href={localizeHref('/contact')} class="btn btn-ghost">{t('about.getInTouch')}</a>
	</div>
</div>
