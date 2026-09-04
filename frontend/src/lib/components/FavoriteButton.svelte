<script lang="ts">
	import { favorites, type FavoriteKind } from '$lib/favorites.svelte';
	import { i18n } from '$lib/i18n.svelte';

	/**
	 * A heart toggle for favoriting an author / book / plan / sermon. Works
	 * signed-out (device-local) and syncs to the account when signed in, like
	 * highlights. `label` shows text next to the heart on wider layouts.
	 */
	interface Props {
		kind: FavoriteKind;
		slug: string;
		showLabel?: boolean;
	}
	let { kind, slug, showLabel = false }: Props = $props();
	const t = i18n.t;

	const active = $derived(favorites.has(kind, slug));
	const label = $derived(active ? t('fav.saved') : t('fav.save'));
</script>

<button
	type="button"
	class="fav-btn"
	class:active
	onclick={() => favorites.toggle(kind, slug)}
	aria-pressed={active}
	aria-label={label}
	title={label}
>
	<svg
		width="18"
		height="18"
		viewBox="0 0 24 24"
		fill={active ? 'currentColor' : 'none'}
		stroke="currentColor"
		stroke-width="1.8"
		stroke-linecap="round"
		stroke-linejoin="round"
		aria-hidden="true"
	>
		<path
			d="M19 14c1.5-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7z"
		/>
	</svg>
	{#if showLabel}<span class="fav-label">{label}</span>{/if}
</button>

<style>
	.fav-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.4rem 0.6rem;
		border-radius: var(--radius-sm);
		border: 1px solid var(--border);
		background: var(--surface);
		color: var(--muted);
		font-size: var(--fs-small);
		font-weight: 600;
		cursor: pointer;
		transition:
			color var(--duration-fast),
			border-color var(--duration-fast);
	}
	.fav-btn:hover {
		border-color: var(--accent);
		color: var(--accent);
	}
	.fav-btn.active {
		color: var(--danger);
		border-color: color-mix(in srgb, var(--danger) 45%, var(--border));
	}
</style>
