<script lang="ts">
	import { onMount } from 'svelte';
	import PrintFlyer from '$lib/components/PrintFlyer.svelte';
	import QrPanel from '$lib/components/QrPanel.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import { page } from '$app/state';
	import { auth } from '$lib/auth.svelte';
	import { hrefInLocale } from '$lib/editionHref';
	import type { ForChrome } from '$lib/forChrome';
	import type { ForLocale } from '$lib/forLinks';
	import { localizeHref } from '$lib/href';
	import type { PlanSummary } from '$lib/library-public';
	import { loginHref } from '$lib/loginHref';
	import { READING_DAYS, parseIsoDay, type ReadingDays } from '$lib/planSchedule';
	import { groupDateFormat, nextMonday, togetherQuery } from '$lib/planTogether';
	import { MIN_COUNTED, createGroup } from '$lib/readingGroups';
	import { absUrl } from '$lib/seo';
	import { localToday } from '$lib/streak';

	/**
	 * "Start a reading group" on an "Ochorus for …" page: the leader picks one
	 * of the page's plans, the day the group begins and the days it reads, and
	 * leaves with everything a group needs to start — the link
	 * ($lib/planTogether: the schedule rides its query, nothing is stored), the
	 * share sheet, a QR code for the slide or the poster, and a bulletin insert
	 * to print. The plan page's own "Read together" does the same for one plan;
	 * this is the same link, made where a leader is deciding which plan.
	 *
	 * A signed-in leader may also turn on the group's totals, as there.
	 */
	let {
		plans,
		locale,
		words,
		onaction
	}: {
		plans: PlanSummary[];
		locale: ForLocale;
		words: ForChrome;
		/** Reports what the leader did, for the page's analytics. */
		onaction?: (action: string) => void;
	} = $props();

	const w = $derived(words.together);

	// Empty until the leader picks: the plan falls back to the first.
	let slug = $state('');
	let start = $state('');
	let rule = $state<ReadingDays>('daily');
	// Today is the reader's, not the build's: the prerendered page leaves the
	// date empty and the browser fills in the coming Monday.
	let todayIso = $state('');
	onMount(() => {
		todayIso = localToday(new Date());
		if (!start) start = nextMonday(new Date());
	});

	const plan = $derived(plans.find((p) => p.slug === slug) ?? plans[0]);
	const startDate = $derived(parseIsoDay(start));
	const dateText = $derived(startDate ? groupDateFormat(locale).format(startDate) : '');

	/** Totals made for this plan and these dates; any change leaves them behind. */
	let made = $state<{ code: string; slug: string; start: string; rule: ReadingDays } | null>(null);
	let making = $state(false);
	let failed = $state(false);
	const group = $derived(
		made && made.slug === plan?.slug && made.start === start && made.rule === rule ? made.code : undefined
	);
	const link = $derived(
		plan && startDate ? `${absUrl(hrefInLocale(`/plans/${plan.slug}`, locale))}${togetherQuery({ start, rule, group })}` : ''
	);
	const message = $derived(plan && dateText ? w.message(plan.title, dateText) : '');

	async function addTotals() {
		if (making || !plan || !startDate) return;
		making = true;
		failed = false;
		try {
			const g = await createGroup(plan.slug, { start, rule });
			made = { code: g.code, slug: plan.slug, start, rule };
			onaction?.('together-totals');
		} catch {
			failed = true;
		} finally {
			making = false;
		}
	}
</script>

{#if plan}
	<div class="together rounded-card border border-border bg-surface p-5 sm:p-6">
		<div class="controls">
			<h3 class="text-h3">{w.heading}</h3>
			<p class="mt-2 text-body text-muted">{w.body}</p>
			<div class="fields mt-4">
				<label class="block">
					<span class="text-eyebrow text-muted">{w.plan}</span>
					<select class="field mt-1 block w-full" value={plan.slug} onchange={(e) => (slug = e.currentTarget.value)}>
						{#each plans as p (p.slug)}
							<option value={p.slug}>{p.title}</option>
						{/each}
					</select>
				</label>
				<label class="block">
					<span class="text-eyebrow text-muted">{w.start}</span>
					<input class="field mt-1 block w-full" type="date" min={todayIso} bind:value={start} />
				</label>
			</div>
			<div class="mt-3">
				<span class="text-eyebrow text-muted" id="together-days">{w.days}</span>
				<div class="mt-1 flex flex-wrap gap-1.5" role="group" aria-labelledby="together-days">
					{#each READING_DAYS as r (r)}
						<button type="button" class="chip" class:active={rule === r} aria-pressed={rule === r} onclick={() => (rule = r)}
							>{w.dayLabels[r]}</button
						>
					{/each}
				</div>
			</div>
		</div>

		{#if link}
			<div class="result">
				<p class="text-eyebrow text-muted">{w.link}</p>
				<p class="link mt-1 text-small">{link}</p>
				<div class="mt-3 flex flex-wrap gap-2">
					<ShareButton url={link} title={message} label={w.share} showLabel onshare={() => onaction?.('together-share')} />
					<PrintFlyer
						label={words.flyer.print}
						onprint={() => onaction?.('together-flyer')}
						flyer={{
							eyebrow: words.flyer.eyebrow,
							title: plan.title,
							line: words.flyer.schedule(dateText, w.dayLabels[rule]),
							url: link,
							scan: words.flyer.scan,
							free: words.flyer.free,
							qrLabel: words.qr.alt(plan.title)
						}}
					/>
					<QrPanel
						value={link}
						label={plan.title}
						filename="{plan.slug}-qr.svg"
						words={words.qr}
						ondownload={() => onaction?.('together-qr-download')}
					/>
				</div>
				<!-- Totals are opt-in twice: the leader turns them on here, and each
				     reader chooses to be counted (PlanTogetherBanner). -->
				{#if auth.enabled}
					<div class="mt-4 text-small">
						{#if group}
							<p class="text-muted">✓ {w.totalsAdded}</p>
						{:else if !auth.user}
							<a class="text-accent hover:underline" href={localizeHref(loginHref(page.url.pathname))}>{w.totalsSignIn}</a>
						{:else}
							<button type="button" class="btn btn-sm btn-ghost" onclick={addTotals} disabled={making} aria-busy={making}
								>{w.totalsAdd}</button
							>
							{#if failed}<span class="ms-2 text-muted" role="status">{w.totalsFailed}</span>{/if}
						{/if}
						<p class="mt-1 text-muted">{w.totalsNote(MIN_COUNTED)}</p>
					</div>
				{/if}
			</div>
		{/if}
	</div>
{/if}

<style>
	.together {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: 1.5rem 2.5rem;
		border-color: color-mix(in srgb, var(--group, var(--color-accent)) 35%, var(--color-border));
		background: color-mix(in srgb, var(--group, var(--color-accent)) 5%, var(--color-surface));
	}
	.fields {
		display: grid;
		grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
		gap: 0.75rem;
	}
	.result {
		align-self: center;
	}
	.link {
		overflow-wrap: anywhere;
		color: var(--color-text);
	}
	@media (max-width: 767.98px) {
		.together,
		.fields {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
