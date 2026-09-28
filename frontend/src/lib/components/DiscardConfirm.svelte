<script lang="ts">
	/**
	 * "Discard what you've written?" — asked in place when Escape or Cancel
	 * would throw away text the reader typed (a note, a Notebook entry). Nothing
	 * is lost without it: the draft stays until they choose Discard.
	 */
	import { i18n } from '$lib/i18n.svelte';

	let { onKeep, onDiscard }: { onKeep: () => void; onDiscard: () => void } = $props();
	const t = i18n.t;
</script>

<div class="discard-confirm" role="alert">
	<span class="me-auto text-small">{t('common.discardDraft')}</span>
	<button type="button" class="btn btn-ghost btn-sm" onclick={onKeep}>{t('common.keepEditing')}</button>
	<button type="button" class="btn btn-sm text-danger" onclick={onDiscard}>{t('common.discard')}</button>
</div>

<style>
	.discard-confirm {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem;
		margin-top: 0.75rem;
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: color-mix(in srgb, var(--danger) 6%, transparent);
	}
</style>
