<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import * as m from '$lib/paraglide/messages.js';
	import type { PersonGroup, PrayerList as List } from '$lib/journal';
	import { groupReminders } from '$lib/groupReminders.svelte';
	import { downloadGroupCalendar, remindLabel } from '$lib/prayerRemind';
	import PrayerList from './PrayerList.svelte';
	import ReminderPicker from './ReminderPicker.svelte';

	/**
	 * The prayer lists, by group — Family, Friends, Church, Missions, Work, The
	 * world — each with its people's prayers and its own reminder: "Family every
	 * morning", "Missions on Sundays", a repeating calendar event that carries the
	 * list. Tapping a person opens their prayers; "+ Prayer" starts one for them.
	 */
	let {
		lists,
		locale,
		onopen,
		onpray
	}: {
		lists: List[];
		locale: string;
		onopen: (person: string) => void;
		onpray: (person: string, group: PersonGroup['group']) => void;
	} = $props();

	const t = i18n.t;
	/** The list whose reminder is being chosen, if any. */
	let choosing = $state<string | null>(null);
	const name = (g: List['group']) => (g ? t(`notebook.group_${g}`) : t('notebook.forAnyone'));
	const key = (g: List['group']) => g || 'other';
</script>

{#each lists as list (key(list.group))}
	{@const remind = groupReminders.get(list.group)}
	<section class="list" data-group={list.group || 'none'} id="list-{key(list.group)}" aria-labelledby="list-h-{key(list.group)}">
		<header class="head">
			<h3 id="list-h-{key(list.group)}" class="name">
				<span class="dot" aria-hidden="true"></span>{name(list.group)}
				<span class="count text-small font-normal">{list.count === 1 ? t('notebook.oneListPrayer') : m.notebook_list_prayers({ n: String(list.count) })}</span>
			</h3>
			{#if remind}
				<button class="remind on text-micro" onclick={() => (choosing = key(list.group))}>
					<span aria-hidden="true" class="me-1">🔔</span>{remindLabel(remind, locale)}
				</button>
			{:else}
				<button class="remind text-micro" onclick={() => (choosing = key(list.group))}>
					<span aria-hidden="true" class="me-1">🔔</span>{t('notebook.listRemind')}
				</button>
			{/if}
		</header>

		{#if choosing === key(list.group)}
			<div class="mt-3">
				<ReminderPicker
					value={remind}
					{locale}
					title={m.notebook_list_remind_title({ group: name(list.group) })}
					onsave={(r) => {
						groupReminders.set(list.group, r);
						downloadGroupCalendar(list, name(list.group), r);
						choosing = null;
					}}
					onremove={() => {
						groupReminders.set(list.group, '');
						choosing = null;
					}}
					oncancel={() => (choosing = null)}
				/>
			</div>
		{/if}

		<PrayerList cards={list.cards} {locale} {onopen} {onpray} showGroup={false} />
	</section>
{/each}

<style>
	.list {
		--hue: var(--muted);
		margin-top: 2rem;
	}
	.list[data-group='family'] {
		--hue: var(--accent);
	}
	.list[data-group='friends'] {
		--hue: var(--hl-blue);
	}
	.list[data-group='church'] {
		--hue: var(--gold);
	}
	.list[data-group='missions'] {
		--hue: var(--hl-green);
	}
	.list[data-group='work'] {
		--hue: var(--hl-rose);
	}
	.head {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.35rem 1rem;
		padding-bottom: 0.35rem;
		border-bottom: 2px solid color-mix(in srgb, var(--hue) 45%, transparent);
	}
	.name {
		display: flex;
		align-items: baseline;
		gap: 0.5rem;
		font-family: var(--font-display);
		font-size: var(--fs-h3);
	}
	.dot {
		align-self: center;
		width: 0.7rem;
		height: 0.7rem;
		border-radius: 50%;
		background: var(--hue);
	}
	.remind {
		color: var(--muted);
		cursor: pointer;
	}
	.remind:hover {
		color: var(--accent);
	}
	.remind.on {
		color: var(--warning);
		font-weight: 600;
	}
	/* The cards' own top margin is for standing alone; inside a list, tighter. */
	.list :global(.cards) {
		margin-top: 0.9rem;
	}
</style>
