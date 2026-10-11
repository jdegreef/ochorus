<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import Arrow from '$lib/components/Arrow.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { auth } from '$lib/auth.svelte';
	import { localizeHref } from '$lib/href';
	import { loginHref } from '$lib/loginHref';
	import { countedDay, groupDateFormat, groupStatus, togetherFromQuery } from '$lib/planTogether';
	import { planTogether } from '$lib/planTogether.svelte';
	import { getGroup, joinGroup, leaveGroup, type GroupTotals } from '$lib/readingGroups';

	/**
	 * Where a "read together" group is today, on the plan page: shown to anyone
	 * who arrives by a group's link, and to a reader who joined one on this
	 * device. "The group is on Day 4 today", with that day one tap away, and a
	 * Join that lays the reader's own plan calendar on the group's dates.
	 * Nothing about the reader is shared: their progress stays their own —
	 * unless the group's link carries totals ($lib/readingGroups) and they
	 * choose to be counted, and then only as one in a number ("7 of 12 have
	 * read Day 4"), never by name.
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

	// The query is read only once mounted (a prerendered page has none at build
	// time), then live, so moving to another plan doesn't carry this one's group.
	let mounted = $state(false);
	onMount(() => (mounted = true));
	const fromLink = $derived(mounted ? togetherFromQuery(page.url.searchParams) : null);

	const joined = $derived(planTogether.get(slug));
	/** The link's group wins over a joined one: following a new link is how a
	 *  reader moves to another group. */
	const group = $derived(fromLink ?? joined);
	const isJoined = $derived(
		!!group && !!joined && joined.start === group.start && joined.rule === group.rule && joined.group === group.group
	);
	const status = $derived(group && today ? groupStatus(group, dayCount, today) : null);
	const fmt = $derived(groupDateFormat(getLang()));

	// The group's totals, when its leader turned them on: fetched for the day
	// the banner talks about, refetched when the reader signs in, joins or
	// leaves. A failed fetch just leaves the numbers out.
	const code = $derived(group?.group);
	const day = $derived(status ? countedDay(status, dayCount) : null);
	let totals = $state<GroupTotals | null>(null);
	let refresh = $state(0);
	$effect(() => {
		void refresh;
		void auth.user;
		const c = code;
		if (!c) return;
		let live = true;
		getGroup(c, day).then(
			(g) => live && (totals = g),
			() => live && (totals = null)
		);
		return () => (live = false);
	});
	// Only numbers that are this group's: a code pasted onto another plan's
	// link, or onto other dates, shows nothing.
	const shown = $derived(
		group &&
			totals &&
			totals.code === code &&
			totals.plan_slug === slug &&
			totals.start_on === group.start &&
			totals.reading_days === group.rule
			? totals
			: null
	);

	let busy = $state(false);
	/** Be counted in group `c` (this banner's, unless the reader is leaving
	 *  it — the local leave takes the code away), or stop being. */
	async function counting(on: boolean, c = code) {
		if (!c || busy) return;
		busy = true;
		try {
			await (on ? joinGroup(c) : leaveGroup(c));
		} catch {
			// Unchanged on the server; the refresh shows what is true.
		} finally {
			busy = false;
			refresh++;
		}
	}
	// Joining lays the plan on the group's dates, on this device; being
	// counted is asked separately (below), so it is never a side effect. Asking
	// to be counted joins too, so the group — and its "stop counting me" —
	// stays on the plan page after the link is gone.
	function join() {
		if (group) planTogether.join(slug, group);
	}
	function countMe() {
		join();
		void counting(true);
	}
	/** Leaving the group also stops counting, if the reader was. */
	function leave() {
		const counted = shown?.counted ? code : undefined;
		planTogether.leave(slug);
		if (counted) void counting(false, counted);
	}
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
		{#if shown}
			<p class="mt-1 text-small text-muted">
				{#if shown.done !== null && shown.day}
					{t('together.readCount')
						.replace('%d%', String(shown.done))
						.replace('%n%', String(shown.members))
						.replace('%k%', String(shown.day))}
				{:else}
					{t('together.members').replace('%n%', String(shown.members))}
					{#if shown.members < shown.min_counted}
						· {t('together.countSoon').replace('%m%', String(shown.min_counted))}
					{/if}
				{/if}
			</p>
		{/if}
		{#if status.kind === 'today' || status.kind === 'next'}
			<p class="mt-1 text-small">
				<a class="font-semibold text-accent hover:underline" href={dayHref(status.day)}
					>{t('plans.day')} {status.day} <Arrow /></a
				>
			</p>
		{/if}
		<!-- Leave stays offered once the group has finished, or its banner would
		     never go; joining a finished group has nothing to offer. -->
		{#if isJoined || status.kind !== 'finished'}
			<div class="mt-3 flex flex-wrap items-center gap-2 text-small">
				{#if isJoined}
					<span class="text-muted">✓ {t('together.joined')}</span>
					<button type="button" class="btn btn-sm btn-ghost" onclick={leave}>{t('together.leave')}</button>
				{:else}
					<button type="button" class="btn btn-sm btn-primary" onclick={join}>{t('together.join')}</button>
					<span class="text-muted">{t('together.joinHint')}</span>
				{/if}
			</div>
		{/if}
		<!-- Being counted is its own choice, and needs an account (the count is
		     of synced plan progress); seeing the numbers doesn't. -->
		{#if shown && status.kind !== 'finished'}
			<div class="mt-2 flex flex-wrap items-center gap-2 text-small">
				{#if shown.counted}
					<span class="text-muted">✓ {t('together.counted')}</span>
					<button type="button" class="btn btn-sm btn-ghost" disabled={busy} onclick={() => counting(false)}
						>{t('together.countStop')}</button
					>
				{:else if auth.user}
					<button type="button" class="btn btn-sm btn-ghost" disabled={busy} onclick={countMe}
						>{t('together.countMe')}</button
					>
				{:else if auth.enabled}
					<a class="text-accent hover:underline" href={localizeHref(loginHref(page.url.pathname, page.url.search))}
						>{t('together.countSignInJoin')}</a
					>
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
