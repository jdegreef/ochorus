<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { customShelves } from '$lib/customShelves.svelte';

	/**
	 * Put one book on the reader's own shelves: each shelf a toggle (✓ when the
	 * book is on it), and a field to make a new shelf with the book already on
	 * it. The one picker behind both entry points — the Bookshelf's book menu
	 * ("Add to a shelf") and the book page's "Add to a shelf" button — so they
	 * can't offer different things.
	 *
	 * Clicks stop here: both hosts are menus that close on an outside click,
	 * and ticking a shelf shouldn't close the menu it's in.
	 */
	let { slug }: { slug: string } = $props();
	const t = i18n.t;

	let newName = $state('');
	const shelves = $derived(customShelves.list());

	function create(e: Event) {
		e.preventDefault();
		if (customShelves.create(newName, slug)) newName = '';
	}
</script>

<div role="group" aria-label={t('shelves.addTo')}>
	{#each shelves as s (s.id)}
		{@const on = customShelves.has(s.id, slug)}
		<button
			type="button"
			class="account-item shelf-toggle"
			aria-pressed={on}
			onclick={(e) => {
				e.stopPropagation();
				customShelves.setBook(s.id, slug, !on);
			}}
		>
			<span class="check" aria-hidden="true">{on ? '✓' : ''}</span>
			<span class="truncate">{s.name}</span>
		</button>
	{/each}
	<form class="flex gap-1.5 px-2 py-1" onsubmit={create}>
		<input
			class="field min-w-0 flex-1 py-1"
			maxlength="80"
			placeholder={t('shelves.new')}
			aria-label={t('shelves.namePlaceholder')}
			bind:value={newName}
			onclick={(e) => e.stopPropagation()}
		/>
		<button class="btn btn-sm" type="submit" disabled={!newName.trim()}
			>{t('shelves.create')}</button
		>
	</form>
</div>

<style>
	.shelf-toggle {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding-block: 0.35rem;
	}
	.shelf-toggle .check {
		width: 1rem;
		flex: none;
		color: var(--color-accent);
		font-weight: 700;
	}
</style>
