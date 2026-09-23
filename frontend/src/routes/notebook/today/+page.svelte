<script lang="ts">
	import { onDestroy, tick } from 'svelte';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import * as m from '$lib/paraglide/messages.js';
	import { localizeHref } from '$lib/href';
	import { readJSON, writeJSON } from '$lib/persisted';
	import { DAILY_DRAFT_KEY } from '$lib/reading-schema';
	import { localToday } from '$lib/streak';
	import { lookupScripture, type ScriptureResult } from '$lib/scripture.svelte';
	import { appendPhrase, dictation } from '$lib/dictation.svelte';
	import DictateButton from '$lib/components/notebook/DictateButton.svelte';
	import {
		DAILY_STEPS,
		composeDaily,
		dailyStreak,
		dailyVerse,
		prayersByPerson,
		type DailyStep
	} from '$lib/journal';
	import { journal } from '$lib/journal.svelte';

	/**
	 * The daily prayer: four short movements — Adore, Confess, Thanks, Ask —
	 * each opened with a verse and a question, written (or spoken) on a ruled
	 * page, and saved to the Notebook as one entry. A streak counts the days in
	 * a row. What is written survives leaving the page (a draft for today).
	 */

	const t = i18n.t;
	const locale = getLang();
	const today = localToday();

	type Draft = { day: string; step: DailyStep; parts: Partial<Record<DailyStep, string>> };
	const saved = readJSON<Draft | null>(DAILY_DRAFT_KEY, null);
	// Yesterday's unfinished draft is not today's prayer.
	const draft: Draft = saved && saved.day === today ? saved : { day: today, step: 'adore', parts: {} };

	let step = $state<DailyStep>(DAILY_STEPS.includes(draft.step) ? draft.step : 'adore');
	let parts = $state<Partial<Record<DailyStep, string>>>(draft.parts);
	let finished = $state(false);

	$effect(() => {
		if (!finished) writeJSON(DAILY_DRAFT_KEY, { day: today, step, parts: $state.snapshot(parts) });
	});

	const index = $derived(DAILY_STEPS.indexOf(step));
	const last = $derived(index === DAILY_STEPS.length - 1);
	const names = $derived(
		Object.fromEntries(DAILY_STEPS.map((s) => [s, t(`notebook.step_${s}`)])) as Record<DailyStep, string>
	);
	const streak = $derived(dailyStreak(journal.store, today));
	// Counting today once it is prayed, and as the day it would become until then.
	const dayNumber = $derived(streak.doneToday ? streak.streak : streak.streak + 1);

	// The verse's words come from the Scripture API, which serves one English
	// text (the ASV); in any other language the reference alone is shown.
	const ref = $derived(dailyVerse(step, today));
	let verse = $state<ScriptureResult | null>(null);
	$effect(() => {
		const r = ref;
		verse = null;
		if (locale !== 'en') return;
		lookupScripture(r).then((v) => {
			if (r === ref) verse = v;
		});
	});

	// Ask: the people on the reader's prayer list, a tap from being named.
	const people = $derived(prayersByPerson(journal.store).filter((c) => c.person));

	let sheet = $state<HTMLTextAreaElement>();

	/** Add a line (a name tapped, a phrase spoken) and carry on writing after it. */
	function append(text: string) {
		const cur = parts[step]?.trimEnd() ?? '';
		parts[step] = cur ? `${cur}\n${text}` : text;
		tick().then(() => {
			const end = sheet?.value.length ?? 0;
			sheet?.focus();
			sheet?.setSelectionRange(end, end);
		});
	}

	function go(to: number) {
		dictation.stop();
		step = DAILY_STEPS[Math.max(0, Math.min(DAILY_STEPS.length - 1, to))];
		window.scrollTo({ top: 0 });
	}

	function finish() {
		dictation.stop();
		const body = composeDaily(parts, names);
		if (body) {
			journal.add({
				kind: 'daily',
				title: t('notebook.dailyTitle'),
				body,
				ref: '',
				person: '',
				group: '',
				collection: ''
			});
		}
		finished = true;
		writeJSON(DAILY_DRAFT_KEY, null);
	}

	onDestroy(() => dictation.stop());

	const longDate = new Date().toLocaleDateString(locale, { weekday: 'long', day: 'numeric', month: 'long' });
</script>

<svelte:head><title>{t('notebook.dailyTitle')} — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="page-col px-5 py-10">
	<div class="daily">
		<a class="back text-small" href={localizeHref('/notebook')}>← {t('notebook.title')}</a>

		{#if finished}
			<div class="amen">
				<p class="amen-word">{t('notebook.dailyAmen')}</p>
				<p class="text-body text-muted">{t('notebook.dailySaved')}</p>
				<p class="streak mt-4"><span aria-hidden="true" class="me-1">🔥</span>{m.notebook_daily_day_n({ n: String(streak.streak) })}</p>
				<a class="btn btn-primary mt-6 inline-block" href={localizeHref('/notebook')}>{t('notebook.dailyToNotebook')}</a>
			</div>
		{:else}
			<header class="mb-5 text-center">
				<p class="text-small text-muted">{longDate} · <span class="streak">{m.notebook_daily_day_n({ n: String(dayNumber) })}</span></p>
				<h1 class="text-h1 mt-1">{t('notebook.dailyTitle')}</h1>
			</header>

			<!-- The four movements; each can be visited in any order. -->
			<ol class="steps" aria-label={t('notebook.dailyTitle')}>
				{#each DAILY_STEPS as s, i (s)}
					<li>
						<button
							class="step"
							class:active={s === step}
							class:done={s !== step && !!parts[s]?.trim()}
							aria-current={s === step ? 'step' : undefined}
							onclick={() => go(i)}
						>
							{#if s !== step && parts[s]?.trim()}✓ {/if}{names[s]}
						</button>
					</li>
				{/each}
			</ol>

			<section class="sheet" aria-labelledby="step-q">
				<p class="verse">
					{#if verse}<span class="verse-text">“{verse.verses.map((v) => v.text).join(' ')}”</span>{/if}
					<span class="verse-ref">{ref}</span>
				</p>
				<p id="step-q" class="question">{t(`notebook.stepQ_${step}`)}</p>

				<textarea
					bind:this={sheet}
					class="ruled"
					rows="7"
					bind:value={parts[step]}
					placeholder={t('notebook.dailyPlaceholder')}
					aria-labelledby="step-q"
				></textarea>

				{#if step === 'ask' && people.length}
					<div class="mt-4">
						<p class="mb-2 text-micro font-semibold text-muted">{t('notebook.dailyOnList')}</p>
						<div class="flex flex-wrap gap-1.5">
							{#each people as c (c.person.toLowerCase())}
								<button class="chip" onclick={() => append(`${c.person} — `)}>+ {c.person}</button>
							{/each}
						</div>
					</div>
				{/if}

				<div class="controls">
					<DictateButton
						lang={locale}
						ontext={(said) => {
							parts[step] = appendPhrase(parts[step] ?? '', said, locale);
						}}
					/>
					<span class="ms-auto"></span>
					{#if index > 0}
						<button class="btn btn-ghost btn-sm" onclick={() => go(index - 1)}>{t('notebook.dailyBack')}</button>
					{/if}
					{#if last}
						<button class="btn btn-primary btn-sm" onclick={finish}>{t('notebook.dailyFinish')}</button>
					{:else}
						<button class="btn btn-primary btn-sm" onclick={() => go(index + 1)}>
							{m.notebook_daily_next({ step: names[DAILY_STEPS[index + 1]] })} →
						</button>
					{/if}
				</div>
			</section>
		{/if}
	</div>
</div>

<style>
	.daily {
		--rule-gap: 2rem;
		max-width: 34rem;
		margin-inline: auto;
	}
	.back {
		display: inline-block;
		margin-bottom: 1.25rem;
		color: var(--muted);
	}
	.streak {
		color: var(--warning);
		font-weight: 600;
	}
	.steps {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 0.35rem;
		margin-bottom: 1rem;
	}
	.step {
		width: 100%;
		padding: 0.4rem 0.25rem;
		border: 1px solid var(--border-strong);
		border-radius: 999px;
		background: var(--surface);
		color: var(--muted);
		font-size: var(--fs-small);
		font-weight: 600;
		cursor: pointer;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.step.active {
		border-color: color-mix(in srgb, var(--gold) 60%, transparent);
		background: color-mix(in srgb, var(--gold) 16%, var(--surface));
		color: var(--text);
	}
	.step.done {
		color: color-mix(in srgb, var(--hl-green) 65%, var(--text));
	}
	/* One sheet of the notebook, the same paper and rules as the Notebook page. */
	.sheet {
		position: relative;
		padding-block: 1.25rem 1rem;
		padding-inline: 2.5rem 1.25rem;
		border: 1px solid var(--border);
		border-radius: 4px 10px 10px 4px;
		background: var(--surface);
		box-shadow: var(--shadow-card);
	}
	:global([dir='rtl']) .sheet {
		border-radius: 10px 4px 4px 10px;
	}
	.sheet::before {
		content: '';
		position: absolute;
		top: 0;
		bottom: 0;
		inset-inline-start: 1.25rem;
		border-inline-start: 1.5px solid color-mix(in srgb, var(--danger) 45%, transparent);
	}
	.verse {
		font-family: var(--font-display);
		color: var(--text);
		line-height: 1.6;
	}
	.verse-text {
		display: block;
		font-style: italic;
	}
	.verse-ref {
		display: block;
		margin-top: 0.15rem;
		font-size: var(--fs-small);
		color: var(--accent);
		font-weight: 600;
	}
	.question {
		margin-top: 0.9rem;
		font-family: var(--font-display);
		font-style: italic;
		color: var(--muted);
	}
	.ruled {
		display: block;
		width: 100%;
		margin-top: 0.5rem;
		resize: vertical;
		border: none;
		padding: 0;
		background-color: transparent;
		background-image: linear-gradient(
			to bottom,
			transparent calc(var(--rule-gap) - 1px),
			color-mix(in srgb, var(--accent) 22%, transparent) calc(var(--rule-gap) - 1px)
		);
		background-size: 100% var(--rule-gap);
		background-attachment: local;
		line-height: var(--rule-gap);
		font-family: var(--font-display);
		font-size: var(--fs-body);
		color: var(--text);
	}
	.ruled:focus-visible {
		outline: none;
		background-image: linear-gradient(
			to bottom,
			transparent calc(var(--rule-gap) - 1px),
			color-mix(in srgb, var(--accent) 45%, transparent) calc(var(--rule-gap) - 1px)
		);
	}
	.ruled::placeholder {
		color: var(--muted);
		font-style: italic;
	}
	.controls {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem;
		margin-top: 1rem;
	}
	.amen {
		padding: 3rem 1rem;
		text-align: center;
	}
	.amen-word {
		font-family: var(--font-display);
		font-size: var(--fs-display);
		font-style: italic;
		color: var(--text);
	}
</style>
