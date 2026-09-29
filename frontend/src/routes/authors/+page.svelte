<script lang="ts">
	import { formatLifespan } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { lang } from '$lib/lang.svelte';
	import { hreflangAll, itemList } from '$lib/seo';
	import { authorIndex } from '$lib/authorIndex';
	import { ORIGINALS_SLUG } from '$lib/originals';
	import type { PageData } from './$types';
	import Seo from '$lib/components/Seo.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';

	// The library A–Z: every writer and, under each, every book of theirs in
	// this language — see $lib/authorIndex for why this page exists. It used to
	// be a hidden, noindexed crawl anchor that redirected to /biographies on
	// mount; the same complete link set is now the page itself, visible and
	// indexable. Deliberately NOT paginated: it must stay complete, for readers
	// and for the prerender crawl (svelte.config.js seeds it per locale).
	let { data }: { data: PageData } = $props();
	const t = i18n.t;

	// The imprint is not a person and has no author page — /originals instead.
	const groups = $derived(authorIndex(data.authors, data.books, lang.current, [ORIGINALS_SLUG]));
	const writerCount = $derived(groups.reduce((n, g) => n + g.entries.length, 0));
	const bookCount = $derived(groups.reduce((n, g) => n + g.entries.reduce((m, e) => m + e.books.length, 0), 0));

	const title = $derived(t('nav.azIndex'));
	const hreflang = hreflangAll('/authors/');
	const canonical = `${SITE_URL}${localizeHref('/authors')}`;
	const authorsLd = $derived(
		itemList(
			title,
			groups.flatMap((g) =>
				g.entries.map((e) => ({ name: e.author.name, url: localizeHref(`/authors/${e.author.slug}`) }))
			)
		)
	);
</script>

<Seo
	title={`${title} — Ochorus`}
	description={t('authors.indexTagline')}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og/biographies.png`}
	structuredData={groups.length ? [authorsLd] : []}
/>

<div class="page-col px-5 py-10">
	<PageHeader {title} tagline={t('authors.indexTagline')} meta={groups.length ? counts : undefined} />
	{#snippet counts()}
		{writerCount}
		{writerCount === 1 ? t('common.authorOne') : t('common.authorMany')}
		<span class="opacity-50">·</span>
		{bookCount}
		{bookCount === 1 ? t('common.bookOne') : t('common.bookMany')}
	{/snippet}

	<!-- Empty only when the fetch failed (the build throws instead; see +page.ts). -->
	{#if data.loadError || groups.length === 0}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else}
		<!-- Real anchors, not the Biographies rail's buttons: every group is in the
		     HTML (no paging), so each #letter- target always exists. -->
		<nav class="mb-6 flex flex-wrap gap-x-1 gap-y-0.5 text-small" aria-label={t('bios.jumpAz')}>
			{#each groups as g (g.letter)}
				<a
					href="#letter-{g.letter === '#' ? 'other' : g.letter}"
					class="rounded-sm px-1.5 py-0.5 font-semibold text-accent hover:bg-accent-soft">{g.letter}</a
				>
			{/each}
		</nav>

		{#if data.eras.length}
			<nav class="mb-10 flex flex-wrap items-center gap-2" aria-label={t('bios.sortEra')}>
				<span class="eyebrow me-1">{t('bios.sortEra')}</span>
				{#each data.eras as era (era.id)}
					<a class="tag" href={localizeHref(`/biographies/era/${era.id}`)}>{t(era.k)}</a>
				{/each}
			</nav>
		{/if}

		{#each groups as g (g.letter)}
			<section id="letter-{g.letter === '#' ? 'other' : g.letter}" class="az-group mb-10">
				<GroupHeading name={g.letter} count={g.entries.length} />
				<ul class="grid gap-x-10 gap-y-5 sm:grid-cols-2 lg:grid-cols-3">
					{#each g.entries as { author, books: own } (author.slug)}
						{@const life = formatLifespan(author.birth_year, author.death_year, t('common.bornPrefix'))}
						<li>
							<a class="font-semibold hover:text-accent" href={localizeHref(`/authors/${author.slug}`)}
								>{author.name}</a
							>
							{#if life}<span class="text-small text-muted"> · {life}</span>{/if}
							{#if own.length}
								<ul class="mt-1 space-y-0.5 text-small">
									{#each own as b (b.slug)}
										<li>
											<a class="text-muted hover:text-accent" href={localizeHref(`/books/${b.slug}`)}
												>{b.title}</a
											>
										</li>
									{/each}
								</ul>
							{/if}
						</li>
					{/each}
				</ul>
			</section>
		{/each}
	{/if}
</div>

<style>
	/* The jump links land the letter heading below the sticky app nav. */
	.az-group {
		scroll-margin-top: calc(var(--appnav-h, 0px) + 1rem);
	}
</style>
