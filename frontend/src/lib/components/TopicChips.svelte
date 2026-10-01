<script lang="ts">
	import type { TopicCount } from '$lib/library-public';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import TopicPill from '$lib/components/TopicPill.svelte';

	/**
	 * The "Browse by topic" pill row, shared by the logged-out home and the
	 * signed-in dashboard. Hidden when empty. `lastBlock` adds the bottom padding
	 * a final section wants: on the dashboard this is the last block, on the
	 * marketing page the mission teaser follows, so it isn't.
	 */
	let { topics, lastBlock = false }: { topics: TopicCount[]; lastBlock?: boolean } = $props();

	const t = i18n.t;
</script>

{#if topics.length}
	<section class="page-col px-5 pt-14" class:pb-20={lastBlock}>
		<SectionHeader
			title={t('home.browseTopic')}
			href={localizeHref('/topics')}
			linkText={t('home.allTopics')}
		/>
		<div class="flex flex-wrap gap-2.5">
			{#each topics as topic (topic.slug)}
				<!-- Members, not books: a shelf carried by its sermons showed a bare
				     "0" here, which reads as an empty shelf rather than a full one. -->
				<TopicPill
					href={localizeHref(`/topics/${topic.slug}`)}
					title={topic.title}
					count={topic.book_count + topic.sermon_count}
				/>
			{/each}
		</div>
	</section>
{/if}
