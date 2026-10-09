<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { READING_DAYS, READING_DAY_LABELS, parseIsoDay, type ReadingDays } from '$lib/planSchedule';
	import { groupDateFormat, nextMonday, togetherQuery } from '$lib/planTogether';
	import { localToday } from '$lib/streak';

	/**
	 * "Read together", for whoever leads a group: pick the day the group starts
	 * and the days it reads, and pass on the link that carries both — through
	 * the page's own share control (the phone's share sheet, or copy / WhatsApp
	 * / email). Everyone who opens it sees the same day of the plan
	 * (PlanTogetherBanner); nothing about anyone is collected ($lib/planTogether).
	 */
	let {
		title,
		url,
		today
	}: {
		title: string;
		/** The plan page's absolute, per-locale URL; the group rides its query. */
		url: string;
		today: Date | null;
	} = $props();
	const t = i18n.t;

	let open = $state(false);
	let start = $state('');
	let rule = $state<ReadingDays>('daily');
	const todayIso = $derived(today ? localToday(today) : '');

	function toggle() {
		open = !open;
		if (open && !start && today) start = nextMonday(today);
	}

	const startDate = $derived(parseIsoDay(start));
	const link = $derived(startDate ? `${url}${togetherQuery({ start, rule })}` : '');
	// Replacer functions, so a "$&" or a "%d%" in a plan's title is just text.
	const invite = $derived(
		startDate
			? t('together.message')
					.replace('%d%', () => groupDateFormat(getLang()).format(startDate))
					.replace('%t%', () => title)
			: ''
	);
</script>

<button type="button" class="btn btn-ghost btn-sm" aria-expanded={open} onclick={toggle}>
	<Icon name="users" size={18} strokeWidth={1.7} />
	<span class="btn-label">{t('together.button')}</span>
</button>

{#if open && today}
	<div class="panel rounded-card border border-border bg-surface p-4">
		<h2 class="text-body font-semibold text-text">{t('together.title')}</h2>
		<p class="mt-1 text-small text-muted">{t('together.intro')}</p>
		<label class="mt-3 block">
			<span class="text-eyebrow text-muted">{t('plans.startOn')}</span>
			<input class="field mt-1 block" type="date" min={todayIso} bind:value={start} />
		</label>
		<div class="mt-3 flex flex-wrap gap-1.5" role="group" aria-label={t('plans.readOn')}>
			{#each READING_DAYS as r (r)}
				<button type="button" class="chip" class:active={rule === r} aria-pressed={rule === r} onclick={() => (rule = r)}
					>{t(READING_DAY_LABELS[r])}</button
				>
			{/each}
		</div>
		{#if link}
			<p class="link mt-3 text-small text-muted">{link}</p>
			<div class="mt-3">
				<ShareButton url={link} title={invite} showLabel />
			</div>
		{/if}
	</div>
{/if}

<style>
	.panel {
		flex-basis: 100%;
	}
	.link {
		overflow-wrap: anywhere;
	}
</style>
