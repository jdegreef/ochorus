<script lang="ts">
	import { onMount } from 'svelte';
	import Arrow from '$lib/components/Arrow.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { groupStatus, togetherFromQuery, type Together } from '$lib/planTogether';
	import { planTogether } from '$lib/planTogether.svelte';

	/**
	 * Where a "read together" group is today, on the plan page: shown to anyone
	 * who arrives by a group's link, and to a reader who joined one on this
	 * device. "The group is on Day 4 today", with that day one tap away, and a
	 * Join that lays the reader's own plan calendar on the group's dates.
	 * Nothing about the reader is shared: their progress stays their own.
	 *
	 * Client-only by nature — the link's query and "today" are the reader's,
	 * never the build's — so it renders nothing until mounted.
	 */
	let {
		slug,
		dayCount,
		today,
		dayHref
	}: { slug: string; dayCount: number; today: Date | null; dayHref: (day: number) => string } = $props();
	const t = i18n.t;

	let fromLink = $state<Together | null>(null);
	onMount(() => (fromLink = togetherFromQuery(new URLSearchParams(location.search))));

	const joined = $derived(planTogether.get(slug));
	/** The link's group wins over a joined one: following a new link is how a
	 *  reader moves to another group. */
	const group = $derived(fromLink ?? joined);
	const isJoined = $derived(!!group && !!joined && joined.start === group.start && joined.rule === group.rule);
	const status = $derived(group && today ? groupStatus(group, dayCount, today) : null);
	const fmt = $derived(new Intl.DateTimeFormat(getLang(), { weekday: 'long', month: 'long', day: 'numeric' }));
</script>

{#if group && status}
	<section class="together rounded-card p-4" aria-labelledby="together-heading">
		<p id="together-heading" class="text-eyebrow text-accent">{t('together.eyebrow')}</p>
		<p class="mt-1 text-body font-semibold text-text">
			{#if status.kind === 'before'}
				{t('together.starts').replace('%d%', fmt.format(status.starts))}
			{:else if status.kind === 'today'}
				{t('together.today').replace('%n%', String(status.day))}
			{:else if status.kind === 'next'}
				{t('together.next').replace('%d%', fmt.format(status.date)).replace('%n%', String(status.day))}
			{:else}
				{t('together.finished').replace('%d%', fmt.format(status.ended))}
			{/if}
		</p>
		{#if status.kind === 'today' || status.kind === 'next'}
			<p class="mt-1 text-small">
				<a class="font-semibold text-accent hover:underline" href={dayHref(status.day)}
					>{t('plans.day')} {status.day} <Arrow /></a
				>
			</p>
		{/if}
		{#if status.kind !== 'finished'}
			<div class="mt-3 flex flex-wrap items-center gap-2 text-small">
				{#if isJoined}
					<span class="text-muted">✓ {t('together.joined')}</span>
					<button type="button" class="btn btn-sm btn-ghost" onclick={() => planTogether.leave(slug)}
						>{t('together.leave')}</button
					>
				{:else}
					<button type="button" class="btn btn-sm btn-primary" onclick={() => planTogether.join(slug, group)}
						>{t('together.join')}</button
					>
					<span class="text-muted">{t('together.joinHint')}</span>
				{/if}
			</div>
		{/if}
	</section>
{/if}

<style>
	.together {
		margin-bottom: 1rem;
		border: 1px solid color-mix(in srgb, var(--color-accent) 30%, var(--color-border));
		background: color-mix(in srgb, var(--color-accent) 7%, var(--color-surface));
	}
</style>
