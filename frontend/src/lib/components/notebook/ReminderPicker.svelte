<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { formatRemind, parseRemind } from '$lib/journal';
	import { weekdayName } from '$lib/prayerRemind';

	/**
	 * Choose a reminder — every day, or one day a week, at a time — for a single
	 * prayer or a whole prayer list. What saving does (record it, hand the
	 * reader a calendar event) is the caller's; this is the choosing.
	 */
	let {
		value,
		locale,
		title,
		onsave,
		onremove,
		oncancel
	}: {
		/** The current reminder ('daily@07:00', 'weekly-0@09:00') or ''. */
		value: string;
		locale: string;
		title: string;
		onsave: (remind: string) => void;
		/** Offered only when there is a reminder to remove. */
		onremove?: () => void;
		oncancel: () => void;
	} = $props();

	const t = i18n.t;
	// Seeded once: this is the picker's own working copy of the reminder.
	const seed = (() => parseRemind(value))();
	let freq = $state<'daily' | 'weekly'>(seed?.freq ?? 'daily');
	let day = $state(seed?.day ?? 0);
	let time = $state(seed?.time ?? '07:00');
	const weekdays = Array.from({ length: 7 }, (_, d) => weekdayName(d, locale));
</script>

<div class="remind-panel">
	<p class="mb-2 text-small font-semibold text-text">{title}</p>
	<div class="flex flex-wrap items-center gap-2">
		<div class="seg" role="group" aria-label={title}>
			<button type="button" class:active={freq === 'daily'} aria-pressed={freq === 'daily'} onclick={() => (freq = 'daily')}
				>{t('notebook.remindDaily')}</button
			>
			<button type="button" class:active={freq === 'weekly'} aria-pressed={freq === 'weekly'} onclick={() => (freq = 'weekly')}
				>{t('notebook.remindWeekly')}</button
			>
		</div>
		{#if freq === 'weekly'}
			<select class="field" bind:value={day} aria-label={t('notebook.remindDay')}>
				{#each weekdays as name, d (d)}<option value={d}>{name}</option>{/each}
			</select>
		{/if}
		<input class="field" type="time" bind:value={time} aria-label={t('notebook.remindTime')} />
	</div>
	<p class="mt-2 text-micro text-muted">{t('notebook.remindHint')}</p>
	<div class="mt-2 flex flex-wrap justify-end gap-2">
		{#if value && onremove}
			<button type="button" class="btn btn-ghost btn-sm" onclick={onremove}>{t('notebook.remindRemove')}</button>
		{/if}
		<button type="button" class="btn btn-ghost btn-sm" onclick={oncancel}>{t('common.cancel')}</button>
		<button type="button" class="btn btn-primary btn-sm" onclick={() => onsave(formatRemind(freq, day, time))} disabled={!time}
			>{t('notebook.remindSave')}</button
		>
	</div>
</div>

<style>
	.remind-panel {
		padding: 0.85rem 1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--surface-2);
	}
</style>
