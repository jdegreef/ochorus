<script lang="ts">
	import type { TopicCount } from '$lib/library-public';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import TopicPill from '$lib/components/TopicPill.svelte';
	import { TOPIC_META } from '$lib/emblemNames';

	/**
	 * The "Browse by topic" pill row, shared by the logged-out home and the
	 * signed-in dashboard. Hidden when empty. `lastBlock` adds the bottom padding
	 * a final section wants: on the dashboard this is the last block, on the
	 * marketing page more sections follow, so it isn't.
	 *
	 * `quiet` is the logged-out home's row (design #17): the first eight names
	 * only — no emblem, no count — under a heading with no section icon; the
	 * header's "All topics →" is the way on. The dashboard keeps the full row.
	 */
	let {
		topics,
		lastBlock = false,
		quiet = false
	}: { topics: TopicCount[]; lastBlock?: boolean; quiet?: boolean } = $props();

	const t = i18n.t;

	// The full row carries 13 chips — two full lines at the default desktop
	// width (see HOME_TOPIC_LIMIT). Narrower screens show a prefix of the same
	// list so the teaser stays short and ends on a whole line: a phone (two
	// chips a line) keeps the first 8, a tablet (four a line) the first 12.
	const PHONE_CAP = 8;
	const TABLET_CAP = 12;
	// The quiet row: eight names at every width.
	const QUIET_CAP = 8;
</script>

{#if topics.length}
	<section class="page-col px-5 pt-14" class:pb-20={lastBlock}>
		<SectionHeader
			section={quiet ? undefined : 'topics'}
			title={t('home.browseTopic')}
			href={localizeHref('/topics')}
			linkText={t('home.allTopics')}
		/>
		<div class="flex flex-wrap gap-2.5">
			{#each quiet ? topics.slice(0, QUIET_CAP) : topics as topic, i (topic.slug)}
				<!-- Members, not books: a shelf carried by its sermons showed a bare
				     "0" here, which reads as an empty shelf rather than a full one. -->
				<TopicPill
					href={localizeHref(`/topics/${topic.slug}`)}
					title={topic.title}
					count={quiet ? undefined : topic.book_count + topic.sermon_count}
					emblem={quiet ? undefined : TOPIC_META[topic.slug]?.emblem}
					accent={quiet ? undefined : TOPIC_META[topic.slug]?.accent}
					class={quiet ? undefined : [i >= PHONE_CAP && 'max-sm:hidden', i >= TABLET_CAP && 'max-lg:hidden']}
				/>
			{/each}
		</div>
	</section>
{/if}
