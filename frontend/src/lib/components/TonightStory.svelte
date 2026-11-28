<script lang="ts">
	import { bookChapterPath } from '$lib/reading-schema';
	import { onMount } from 'svelte';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { readingTime } from '$lib/reading';
	import { dayIndex } from '$lib/quoteText';
	import type { HubPerson } from '$lib/library-public';
	import Portrait from '$lib/components/Portrait.svelte';
	import { tableQuestion } from '$lib/tableQuestions';
	import { lang } from '$lib/lang.svelte';

	/**
	 * "Tonight's story": one true story a day from the people strip, for a
	 * parent at bedtime who wants one thing to read, not a shelf to choose
	 * from. Each `HubPerson` is a whole chapter (a life in five minutes), so
	 * the card opens it directly. The prerendered pick is the build day's;
	 * after mount it is re-taken for the reader's own day (FeaturedQuote's
	 * rule), so the HTML and the browser agree until the day turns.
	 */
	let { people, class: klass = '' }: { people: HubPerson[]; class?: string } = $props();
	const t = i18n.t;

	// svelte-ignore state_referenced_locally
	let at = $state(dayIndex(new Date(), people.length));
	onMount(() => {
		at = dayIndex(new Date(), people.length);
	});
	const p = $derived(people[at % Math.max(people.length, 1)]);
	// The story's question for the table, where this language has one.
	const ask = $derived(p ? tableQuestion(p.book, p.chapter, lang.current) : null);
</script>

{#if p}
	<section class="tonight {klass}" aria-labelledby="tonight-heading">
		<span class="moon" aria-hidden="true"></span>
		<Portrait
			slug={p.slug}
			name={p.name}
			url={p.photo_url}
			px={96}
			tone="color"
			decorative
			class="size-20 shrink-0 sm:size-24"
			initialsClass="text-h3"
		/>
		<div class="min-w-0 flex-1">
			<h2 id="tonight-heading" class="eyebrow label">{t('audience.tonightStory')}</h2>
			<p class="name font-display" dir="auto">{p.name}</p>
			<p class="hook" dir="auto">{p.hook}</p>
			{#if ask}<p class="ask" dir="auto"><span class="ask-label">{t('reader.tableQuestion')}:</span> {ask}</p>{/if}
		</div>
		<div class="cta">
			<a href={localizeHref(bookChapterPath(p.book, p.chapter, false))} class="btn btn-solid">{t('audience.readTonight')}</a>
			{#if p.words}<span class="time">{readingTime(p.words)}</span>{/if}
		</div>
	</section>
{/if}

<style>
	/* hex-ok-file: a night-sky card — the ground, the moon and the type on it are
	   the picture's, the same in both themes, like a cover. */
	.tonight {
		position: relative;
		overflow: hidden;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 1rem 1.25rem;
		margin-bottom: 2.5rem;
		padding: 1.25rem 1.5rem;
		border-radius: var(--radius-card);
		background:
			radial-gradient(circle at 12% 20%, rgb(255 255 255 / 0.08) 0 1px, transparent 2px),
			radial-gradient(circle at 78% 30%, rgb(255 255 255 / 0.1) 0 1px, transparent 2px),
			radial-gradient(circle at 55% 80%, rgb(255 255 255 / 0.07) 0 1px, transparent 2px),
			linear-gradient(135deg, #1b2547, #2c2a5c 60%, #3b2f5e);
		color: #f5f1e6;
	}
	.moon {
		position: absolute;
		inset-block-start: -1.5rem;
		inset-inline-end: -1.5rem;
		width: 4.5rem;
		height: 4.5rem;
		border-radius: var(--radius-pill);
		background: #f3e2a9;
		box-shadow: 0 0 40px rgb(243 226 169 / 0.35);
		opacity: 0.85;
	}
	.label {
		color: #f3e2a9;
	}
	.name {
		margin-top: 0.15rem;
		font-size: var(--fs-h2);
		font-weight: 600;
		line-height: 1.15;
	}
	.hook {
		margin-top: 0.15rem;
		color: rgb(245 241 230 / 0.82);
	}
	.ask {
		margin-top: 0.5rem;
		font-size: var(--fs-small);
		color: rgb(245 241 230 / 0.82);
	}
	.ask-label {
		color: #f3e2a9;
		font-weight: 600;
	}
	.cta {
		position: relative;
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	.cta .btn {
		background: #f3e2a9;
		border-color: #f3e2a9;
		color: #1b2547;
	}
	.time {
		font-size: var(--fs-small);
		color: rgb(245 241 230 / 0.75);
	}
	@media (min-width: 640px) {
		.tonight {
			flex-wrap: nowrap;
			padding: 1.5rem 2rem;
		}
	}
</style>
