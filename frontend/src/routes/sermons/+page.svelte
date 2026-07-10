<script lang="ts">
	import type { SermonSummary } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { localizeHref } from '$lib/paraglide/runtime';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;

	let { data } = $props();
	const sermons = $derived<SermonSummary[]>(data.sermons);

	// Group sermons by author, preserving the API's author-ordered sequence.
	const grouped = $derived(
		(() => {
			const map = new Map<string, { name: string; slug: string; items: SermonSummary[] }>();
			for (const s of sermons) {
				const key = s.author.slug;
				if (!map.has(key)) map.set(key, { name: s.author.name, slug: key, items: [] });
				map.get(key)!.items.push(s);
			}
			return [...map.values()];
		})()
	);

	const readMins = (words: number) => Math.max(1, Math.round(words / 200));
</script>

<svelte:head>
	<title>Sermons — Ochorus</title>
	<meta
		name="description"
		content="Classic Christian sermons — free to read. The preached word from the writers whose books you can read on Ochorus."
	/>
	<link rel="canonical" href="{SITE_URL}/sermons" />
	<meta property="og:type" content="website" />
	<meta property="og:title" content="Sermons — Ochorus" />
	<meta property="og:url" content="{SITE_URL}/sermons" />
</svelte:head>

<div class="mx-auto max-w-3xl px-5 py-12">
	<header class="mb-10">
		<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">{t('nav.sermons')}</p>
		<h1 class="text-display mb-3">{t('sermons.title')}</h1>
		<p class="text-body text-muted">
			{t('sermons.tagline')}
		</p>
	</header>

	{#if grouped.length}
		<div class="space-y-10">
			{#each grouped as group (group.slug)}
				<section>
					<h2 class="mb-3 text-h3">
						<a href={localizeHref(`/authors/${group.slug}`)} class="!text-text hover:underline">{group.name}</a>
					</h2>
					<ul class="divide-y divide-border">
						{#each group.items as sermon (sermon.slug)}
							<li>
								<a
									href={localizeHref(`/sermons/${sermon.slug}`)}
									class="flex items-baseline justify-between gap-3 py-3 hover:no-underline"
								>
									<span class="flex-1">
										<span class="block text-body font-medium text-text">{sermon.title}</span>
										{#if sermon.scripture_ref}
											<span class="text-small text-accent">{sermon.scripture_ref}</span>
										{/if}
									</span>
									<span class="shrink-0 text-[0.8rem] text-muted">{readMins(sermon.word_count)} min</span>
								</a>
							</li>
						{/each}
					</ul>
				</section>
			{/each}
		</div>
	{:else}
		<p class="text-body text-muted">No sermons in the library yet — check back soon.</p>
	{/if}
</div>
