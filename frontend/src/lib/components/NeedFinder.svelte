<script lang="ts">
	import { getLang } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { contentLang, readingTime } from '$lib/reading';
	import { NEEDS, NEED_MIN_CHIPS, needLabelKey, loadNeedPicks, type NeedPick, type NeedPicks } from '$lib/needFinder';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import Portrait from '$lib/components/Portrait.svelte';
	import Arrow from '$lib/components/Arrow.svelte';

	/**
	 * "What do you need today?" — a row of situations ("I'm anxious", "Prayer
	 * feels dry"), each one press away from three picks out of its topic shelf:
	 * a short read, a book, and a plan, article or life — then "More on <topic>".
	 * The curation is `$lib/needFinder`; this only draws it.
	 *
	 * `needs` is the ids this language can answer (`availableNeeds`); fewer than
	 * three and it renders nothing. No chip is chosen in the baked HTML, so the
	 * prerendered page carries only the chips and hydration fetches nothing: the
	 * picks load on the first press (one topic, plus the plan list once).
	 *
	 * `place`: on the home page it is a section with a "All topics →" header; at
	 * the top of /topics it sits under the page header as a secondary section
	 * (`h2.section-label`, page-design), with no link to the page it is on.
	 */
	let { needs, place = 'home' }: { needs: readonly string[]; place?: 'home' | 'topics' } = $props();

	const t = i18n.t;
	const shown = $derived(NEEDS.filter((n) => needs.includes(n.id)));

	let selected = $state<string | null>(null);
	let result = $state<NeedPicks | null>(null);
	let failed = $state(false);

	async function choose(id: string) {
		if (selected === id) {
			// Pressing the chosen chip again closes the picks.
			selected = null;
			return;
		}
		const need = NEEDS.find((n) => n.id === id);
		if (!need) return;
		selected = id;
		result = null;
		failed = false;
		try {
			const picks = await loadNeedPicks(need, getLang());
			if (selected === id) result = picks;
		} catch {
			if (selected === id) failed = true;
		}
	}

	function retry() {
		const id = selected;
		selected = null;
		if (id) void choose(id);
	}

	const EYEBROW: Record<NeedPick['kind'], string> = {
		shortRead: 'home.need.shortRead',
		book: 'home.need.book',
		plan: 'home.need.plan',
		article: 'home.need.article',
		life: 'home.need.life'
	};

	function byline(p: NeedPick): string {
		const parts = [p.byline];
		if (p.chapter) parts.push(`${t('continue.chapter')} ${p.chapter}`);
		else if (p.words) parts.push(readingTime(p.words));
		return parts.filter(Boolean).join(' · ');
	}
</script>

{#if shown.length >= NEED_MIN_CHIPS}
	<section class={place === 'home' ? 'page-col px-5 pt-14' : 'mb-12'}>
		{#if place === 'home'}
			<SectionHeader
				title={t('home.need.title')}
				href={localizeHref('/topics')}
				linkText={t('home.allTopics')}
			/>
		{:else}
			<h2 class="section-label">{t('home.need.title')}</h2>
		{/if}
		<div class="flex flex-wrap gap-2" role="group" aria-label={t('home.need.title')}>
			{#each shown as need (need.id)}
				<button
					type="button"
					class="chip"
					class:active={selected === need.id}
					aria-pressed={selected === need.id}
					aria-controls="need-finder-picks"
					onclick={() => choose(need.id)}>{t(needLabelKey(need.id))}</button
				>
			{/each}
		</div>

		<div id="need-finder-picks" aria-live="polite" aria-busy={!!selected && !result && !failed}>
			{#if selected && result && result.picks.length}
				<ul role="list" class="picks m-0 mt-6 grid list-none gap-3 p-0 md:grid-cols-3">
					{#each result.picks as pick (pick.kind)}
						<li>
							<a class="pick group" href={localizeHref(pick.href)}>
								<span class="pick-art" aria-hidden="true">
									{#if pick.portrait}
										<Portrait
											slug={pick.portrait.slug}
											name={pick.portrait.name}
											url={pick.portrait.photo_url}
											px={56}
											tone="hover"
											decorative
											class="aspect-square h-auto w-full rounded-full"
										/>
									{:else if pick.cover}
										<BookCover book={pick.cover} rounded="rounded-sm" />
									{/if}
								</span>
								<span class="min-w-0">
									<span class="eyebrow block text-accent">{t(EYEBROW[pick.kind])}</span>
									<span class="pick-title mt-1 line-clamp-2" lang={contentLang(pick.language) || undefined} dir="auto"
										>{pick.title}</span
									>
									{#if byline(pick)}
										<span class="mt-1 block truncate text-small text-muted">{byline(pick)}</span>
									{/if}
								</span>
							</a>
						</li>
					{/each}
				</ul>
				<a
					class="mt-4 inline-block text-small font-semibold text-accent"
					href={localizeHref(`/topics/${result.topic.slug}`)}
					>{t('home.need.more').replace('%topic%', result.topic.title)} <Arrow /></a
				>
			{:else if selected && failed}
				<p class="mt-6 text-small text-muted">
					{t('common.loadError')}
					<button type="button" class="font-semibold text-accent" onclick={retry}>{t('error.tryAgain')}</button>
				</p>
			{:else if selected && !result}
				<!-- The picks' shape while their shelf loads. -->
				<div class="mt-6 grid gap-3 md:grid-cols-3" aria-hidden="true">
					{#each [0, 1, 2] as i (i)}
						<div class="pick">
							<span class="pick-art skeleton aspect-[3/4] rounded-sm"></span>
							<span class="flex-1">
								<span class="skeleton block h-3 w-20 rounded"></span>
								<span class="skeleton mt-2 block h-5 w-3/4 rounded"></span>
								<span class="skeleton mt-2 block h-4 w-1/2 rounded"></span>
							</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</section>
{/if}

<style>
	/* One row per pick: a small cover (or face) at the start, the words beside
	   it — the resume card's recipe at a smaller cover, so three fit a row. */
	.pick {
		display: flex;
		align-items: center;
		gap: 0.875rem;
		height: 100%;
		padding: 0.75rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		color: var(--text);
		text-decoration: none;
		transition: background-color var(--duration-fast);
	}
	a.pick:hover {
		background: var(--surface-2);
	}
	.pick-art {
		flex: none;
		width: 3.5rem;
	}
	.pick-title {
		font-family: var(--font-display);
		font-size: var(--fs-body);
		font-weight: 600;
		line-height: 1.25;
		transition: color var(--duration-fast);
	}
	a.pick:hover .pick-title,
	a.pick:focus-visible .pick-title {
		color: var(--accent);
	}
	@media (prefers-reduced-motion: reduce) {
		.pick,
		.pick-title {
			transition: none;
		}
	}
</style>
