<script lang="ts">
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, hreflangExact, itemList } from '$lib/seo';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { BIBLE_PATH } from '$lib/bible';
	import { BIBLE_PATHS, biblePathSteps, bibleStartPath } from '$lib/bibleHub';
	import { bibleText, type BibleText } from '$lib/bibleLocales';
	import { getLang } from '$lib/lang.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import Arrow from '$lib/components/Arrow.svelte';

	/**
	 * One "Where to start" path on a page of its own: the hub's switcher shows
	 * the same steps in place (routes/bible), but only a page can answer the
	 * search the path is for ("Bible chapters for grief"). Its prose is the
	 * hub's own, in each hub locale (`BIBLE_PATHS`); the chrome goes through the
	 * catalogue. A leaf page: the steps as a numbered list, then the other paths
	 * and the way back to the whole Bible.
	 */
	let { data } = $props();
	const t = i18n.t;
	const lang = getLang();
	const say = (text: BibleText) => bibleText(text, lang);
	const OTHER = { en: 'Other ways in', es: 'Otros caminos', fr: 'Autres chemins', pt: 'Outros caminhos', sw: 'Njia nyingine za kuanzia' };

	const startPath = $derived(BIBLE_PATHS.find((p) => p.id === data.pathId)!);
	const steps = $derived(biblePathSteps(startPath.steps, data.books, lang));
	const others = $derived(BIBLE_PATHS.filter((p) => p.id !== startPath.id));

	const path = $derived(bibleStartPath(startPath.slug));
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const hreflang = $derived(hreflangExact(path, data.languages));
	const crumbsLd = $derived(
		breadcrumbLd([
			{ name: t('common.home'), href: localizeHref('/') },
			{ name: t('nav.bible'), href: localizeHref(`${BIBLE_PATH}/`) },
			{ name: say(startPath.label), href: localizeHref(path) }
		])
	);
	// The steps in order: an ordered list of chapters, the shape the page is.
	const stepsLd = $derived(
		itemList(
			say(startPath.title),
			steps.map((s) => ({ name: s.title, url: localizeHref(s.href) }))
		)
	);
</script>

<Seo
	title={`${say(startPath.title)} — Ochorus`}
	description={say(startPath.lede)}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og/bible.png`}
	structuredData={[crumbsLd, stepsLd]}
/>

<div class="page-col px-5 py-10">
	<PageHeader eyebrow={t('bible.startHeading')} title={say(startPath.title)} tagline={say(startPath.lede)} />

	<ol class="steps" role="list">
		{#each steps as { book, title, href, why }, i (href)}
			<li>
				<a class="step card-tint" href={localizeHref(href)}>
					<span class="step-cover"><BookCover {book} rounded="rounded-sm" /></span>
					<span class="step-text">
						<span class="step-n">{i + 1}</span>
						<span class="step-title">{title}</span>
						<span class="step-why">{why}</span>
					</span>
				</a>
			</li>
		{/each}
	</ol>

	<section class="mt-12 border-t border-border pt-6" aria-labelledby="other-paths">
		<h2 id="other-paths" class="section-label">{say(OTHER)}</h2>
		<div class="flex flex-wrap gap-2">
			{#each others as p (p.id)}
				<a class="chip" href={localizeHref(bibleStartPath(p.slug))}>{say(p.label)}</a>
			{/each}
		</div>
		<p class="mt-6 text-small">
			<a href={localizeHref(`${BIBLE_PATH}/`)} class="font-medium text-accent hover:underline"
				>{t('nav.bible')} <Arrow /></a
			>
		</p>
	</section>
</div>

<style>
	.steps {
		display: grid;
		gap: 0.75rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.step {
		display: flex;
		gap: 1rem;
		align-items: center;
		padding: 0.75rem;
		border-radius: var(--radius-card);
		color: inherit;
		text-decoration: none;
	}
	.step-cover {
		display: block;
		flex: none;
		width: 4rem;
	}
	.step-text {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		min-width: 0;
	}
	.step-n {
		font-size: var(--fs-eyebrow);
		font-weight: 600;
		letter-spacing: 0.08em;
		color: var(--accent);
	}
	.step-title {
		font-family: var(--font-display);
		font-weight: 600;
		font-size: var(--fs-h3, 1.25rem);
		color: var(--text);
	}
	.step-why {
		color: var(--muted);
		line-height: 1.5;
	}
</style>
