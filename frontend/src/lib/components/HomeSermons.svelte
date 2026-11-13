<script lang="ts">
	import type { HomeSermons, SermonTile } from '$lib/homeShelves';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { lang } from '$lib/lang.svelte';
	import { listen } from '$lib/listen.svelte';
	import { contentLang, readingTime } from '$lib/reading';
	import { LISTEN_PARAM } from '$lib/listenOnArrival';
	import Icon from '$lib/components/Icon.svelte';
	import Portrait from '$lib/components/Portrait.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';

	/**
	 * Sermons on the logged-out home (design review 2026-11, #24): the library's
	 * second-largest shelf had one line on the page (Sermon of the day). Three
	 * rows under three tabs — the sermons page's "Start with these", "Under 10
	 * min" and "Recent" — each with the preacher, the passage, the length, one
	 * line of the "In brief", and Listen, which opens the sermon reading aloud
	 * in the device's own voice (`?listen`, $lib/listenOnArrival).
	 *
	 * Every label is the sermons page's own, already in every catalogue. The
	 * picks come from the build's snapshot ($lib/homeShelves); none, and the
	 * section is not drawn.
	 */
	let { sermons }: { sermons: HomeSermons | undefined } = $props();
	const t = i18n.t;

	type Tab = 'start' | 'short' | 'recent';
	const TABS: { id: Tab; label: string }[] = [
		{ id: 'start', label: 'sermons.startWith' },
		{ id: 'short', label: 'sermons.lengthShort' },
		{ id: 'recent', label: 'sort.recent' }
	];
	const tabs = $derived(sermons ? TABS.filter((tab) => sermons[tab.id].length) : []);
	let chosen = $state<Tab>('start');
	const rows = $derived<SermonTile[]>(sermons?.[chosen] ?? []);
	const panelId = $props.id();
</script>

{#if sermons && tabs.length}
	<section class="page-col px-5 pt-14">
		<SectionHeader
			title={t('sermons.title')}
			subtitle={t('sermons.tagline')}
			href={localizeHref('/sermons')}
			linkText={t('books.seeAll').replace('%n%', sermons.total.toLocaleString(lang.current))}
		/>
		{#if tabs.length > 1}
			<div class="mb-2 flex flex-wrap gap-2" role="group" aria-label={t('sermons.title')}>
				{#each tabs as tab (tab.id)}
					<button
						type="button"
						class="chip"
						class:active={chosen === tab.id}
						aria-pressed={chosen === tab.id}
						aria-controls={panelId}
						onclick={() => (chosen = tab.id)}>{t(tab.label)}</button
					>
				{/each}
			</div>
		{/if}
		<ul id={panelId} role="list" class="m-0 list-none p-0">
			{#each rows as s (s.slug)}
				{@const href = localizeHref(`/sermons/${s.slug}`)}
				<li class="row">
					<Portrait
						slug={s.author.slug}
						name={s.author.name}
						url={s.author.photo_url}
						px={48}
						decorative
						class="h-12 w-12 rounded-full object-cover"
					/>
					<a class="row-link min-w-0" {href}>
						<span class="row-title block" lang={contentLang(s.language) || undefined} dir="auto">{s.title}</span>
						<span class="block text-small text-muted"
							>{s.author.name}{#if s.scripture_ref}<span class="sep meta-sep" aria-hidden="true">·</span><span class="passage"
									>{s.scripture_ref}</span
								>{/if}<span class="sep meta-sep" aria-hidden="true">·</span>{readingTime(s.word_count)}</span
						>
						{#if s.summary}
							<span class="mt-0.5 line-clamp-1 text-small text-text" lang={contentLang(s.language) || undefined}
								>{s.summary}</span
							>
						{/if}
					</a>
					{#if listen.offered}
						<a class="listen-btn" href="{href}?{LISTEN_PARAM}" aria-label="{t('reader.listen')}: {s.title}"
							><Icon name="play" size={14} />{t('reader.listen')}</a
						>
					{/if}
				</li>
			{/each}
		</ul>
	</section>
{/if}

<style>
	/* The house sermon row's anatomy (SermonCard): the serif title, one muted
	   meta line, one clamped line of the brief, hairlines between rows — with
	   the preacher's face at the start and Listen at the end. */
	.row {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		gap: 0.5rem 1rem;
		align-items: center;
		padding-block: 0.875rem;
		border-block-end: 1px solid var(--border);
	}
	.row:last-child {
		border-block-end: 0;
	}
	@media (max-width: 39.99rem) {
		.row {
			grid-template-columns: auto minmax(0, 1fr);
		}
		.listen-btn {
			grid-column: 2;
			justify-self: start;
		}
	}
	.row-link {
		color: var(--text);
		text-decoration: none;
	}
	.row-title {
		font-family: var(--font-display);
		font-size: var(--fs-body);
		font-weight: 600;
		line-height: 1.25;
		transition: color var(--duration-fast);
	}
	.row-link:hover .row-title,
	.row-link:focus-visible .row-title {
		color: var(--accent);
	}
	/* The house separator (app.css .sep) with room either side. */
	.meta-sep {
		margin-inline: 0.35em;
	}
	.passage {
		color: var(--section-sermons);
		font-weight: 600;
	}
	.listen-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		min-height: 2.25rem;
		padding: 0.3rem 0.9rem;
		border: 1px solid var(--accent-soft-border);
		border-radius: var(--radius-pill);
		background: var(--accent-soft);
		color: var(--accent);
		font-size: var(--fs-small);
		font-weight: 600;
		white-space: nowrap;
		text-decoration: none;
	}
	.listen-btn:hover {
		border-color: var(--accent);
	}
	@media (prefers-reduced-motion: reduce) {
		.row-title {
			transition: none;
		}
	}
</style>
