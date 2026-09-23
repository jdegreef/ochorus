<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import * as m from '$lib/paraglide/messages.js';
	import type { PersonGroup } from '$lib/journal';
	import { initials } from '$lib/strings';
	import { remindLabel } from '$lib/prayerRemind';

	/**
	 * The prayer list, by person: one card for each person or place the reader
	 * is praying for, with what they are praying, any reminder, and how many
	 * updates the story has gathered. Tapping a card opens those prayers; the
	 * "Pray" button starts a new one already addressed to them.
	 */
	let {
		cards,
		locale,
		onopen,
		onpray,
		showGroup = true
	}: {
		cards: PersonGroup[];
		locale: string;
		/** Show just this person's prayers ('' = the unnamed ones). */
		onopen: (person: string) => void;
		/** Start a new prayer for this person. */
		onpray: (person: string, group: PersonGroup['group']) => void;
		/** Off inside a group's own list, where the heading already names it. */
		showGroup?: boolean;
	} = $props();

	const t = i18n.t;
</script>

<ul class="cards">
	{#each cards as c (c.person.toLowerCase())}
		<li class="card" data-group={c.group || 'none'}>
			<button class="card-open" onclick={() => onopen(c.person)}>
				<span class="head">
					<span class="avatar" aria-hidden="true">{c.person ? initials(c.person) : '✦'}</span>
					<span class="name">{c.person || t('notebook.forAnyone')}</span>
					{#if c.group && showGroup}<span class="group">{t(`notebook.group_${c.group}`)}</span>{/if}
				</span>
				<span class="prayers">
					{#each c.prayers.slice(0, 3) as p (p.id)}
						<span class="prayer">{p.title || p.body}</span>
					{/each}
					{#if c.prayers.length > 3}
						<span class="text-micro text-muted">+{c.prayers.length - 3}</span>
					{/if}
				</span>
				<span class="meta text-micro">
					{#if c.remind}<span class="rem"><span aria-hidden="true" class="me-1">🔔</span>{remindLabel(c.remind, locale)}</span>{/if}
					{#if c.updates}<span>{c.updates === 1 ? t('notebook.oneUpdate') : m.notebook_updates_many({ n: String(c.updates) })}</span>{/if}
				</span>
			</button>
			{#if c.person}
				<button class="pray btn btn-ghost btn-sm" onclick={() => onpray(c.person, c.group)}>
					+ {t('notebook.prayer')}
				</button>
			{/if}
		</li>
	{/each}
</ul>

<style>
	.cards {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 14rem), 1fr));
		gap: 0.9rem;
		margin-top: 1.5rem;
	}
	.card {
		--hue: var(--muted);
		position: relative;
		display: flex;
		flex-direction: column;
		border: 1px solid var(--border);
		border-top: 3px solid color-mix(in srgb, var(--hue) 65%, transparent);
		border-radius: var(--radius-sm);
		background: var(--surface);
		box-shadow: var(--shadow-card);
	}
	.card[data-group='family'] {
		--hue: var(--accent);
	}
	.card[data-group='friends'] {
		--hue: var(--hl-blue);
	}
	.card[data-group='church'] {
		--hue: var(--gold);
	}
	.card[data-group='missions'] {
		--hue: var(--hl-green);
	}
	.card[data-group='work'] {
		--hue: var(--hl-rose);
	}
	.card-open {
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
		padding: 0.9rem 1rem 0.5rem;
		text-align: start;
		cursor: pointer;
		flex: 1;
	}
	.card-open:hover .name {
		color: var(--accent);
	}
	.head {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		min-width: 0;
	}
	.avatar {
		flex: none;
		display: grid;
		place-items: center;
		width: 2.1rem;
		height: 2.1rem;
		border-radius: 50%;
		background: color-mix(in srgb, var(--hue) 16%, var(--surface));
		color: color-mix(in srgb, var(--hue) 70%, var(--text));
		font-size: var(--fs-small);
		font-weight: 700;
	}
	.name {
		font-weight: 600;
		color: var(--text);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.group {
		margin-inline-start: auto;
		flex: none;
		padding: 0 0.5rem;
		border-radius: 999px;
		background: color-mix(in srgb, var(--hue) 14%, transparent);
		color: color-mix(in srgb, var(--hue) 70%, var(--text));
		font-size: var(--fs-micro);
		font-weight: 600;
	}
	.prayers {
		display: grid;
		gap: 0.25rem;
	}
	.prayer {
		font-family: var(--font-display);
		color: var(--text);
		line-height: 1.45;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 0.75rem;
		color: var(--muted);
	}
	.meta .rem {
		color: var(--warning);
		font-weight: 600;
	}
	.pray {
		align-self: flex-start;
		margin: 0 0.6rem 0.6rem;
	}
</style>
