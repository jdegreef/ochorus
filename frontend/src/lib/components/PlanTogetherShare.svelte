<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { READING_DAYS, parseIsoDay, type ReadingDays } from '$lib/planSchedule';
	import { nextMonday, togetherQuery } from '$lib/planTogether';
	import { messageShareLinks } from '$lib/share';
	import { localToday } from '$lib/streak';

	/**
	 * "Read together", for whoever leads a group: pick the day the group starts
	 * and the days it reads, and pass on the link that carries both. Everyone
	 * who opens it sees the same day of the plan (PlanTogetherBanner); nothing
	 * about them is stored anywhere (see $lib/planTogether).
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
	const RULE_LABEL: Record<ReadingDays, string> = {
		daily: 'plans.everyDay',
		weekdays: 'plans.weekdays',
		monsat: 'plans.monSat'
	};

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
	const message = $derived(
		startDate
			? `${t('together.message')
					.replace('%t%', title)
					.replace('%d%', new Intl.DateTimeFormat(getLang(), { weekday: 'long', month: 'long', day: 'numeric' }).format(startDate))}\n${link}`
			: ''
	);
	const [whatsapp, email] = $derived(messageShareLinks(title, message, t('login.email')));

	let copied = $state(false);
	let timer: ReturnType<typeof setTimeout> | undefined;
	$effect(() => () => clearTimeout(timer));
	async function copy() {
		try {
			await navigator.clipboard.writeText(link);
			copied = true;
			clearTimeout(timer);
			timer = setTimeout(() => (copied = false), 1500);
		} catch {
			/* no clipboard: the link is on screen to copy by hand */
		}
	}
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
					>{t(RULE_LABEL[r])}</button
				>
			{/each}
		</div>
		{#if link}
			<p class="link mt-3 text-small text-muted">{link}</p>
			<div class="mt-3 flex flex-wrap gap-2">
				<button type="button" class="btn btn-sm" onclick={copy}>
					<Icon name={copied ? 'check' : 'page'} size={15} />
					{copied ? t('share.linkCopied') : t('share.copyLink')}
				</button>
				<a class="btn btn-sm" href={whatsapp.href} target="_blank" rel="noopener noreferrer"
					><Icon name="share" size={15} /> {whatsapp.name}</a
				>
				<a class="btn btn-sm" href={email.href}><Icon name="mail" size={15} /> {email.name}</a>
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
