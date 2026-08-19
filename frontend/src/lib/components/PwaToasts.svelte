<script lang="ts">
	import { pwa } from '$lib/pwa.svelte';
	import { storageHealth } from '$lib/storageHealth.svelte';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;
</script>

<!-- Fixed, unobtrusive stack in the bottom-right. Layered above the reader. -->
<div class="pwa-stack" aria-live="polite">
	{#if !pwa.online}
		<div class="pwa-pill pwa-offline">
			<span class="pwa-dot"></span>
			{t('pwa.offline')}
		</div>
	{/if}

	{#if pwa.offlineReady}
		<div class="pwa-toast">
			<span>{t('pwa.ready')}</span>
			<button class="pwa-link" onclick={() => pwa.dismissOfflineReady()}>{t('pwa.dismiss')}</button>
		</div>
	{/if}

	{#if pwa.updateReady}
		<div class="pwa-toast pwa-update">
			<span>{t('pwa.updateReady')}</span>
			<button class="pwa-cta" onclick={() => pwa.applyUpdate()}>{t('pwa.refresh')}</button>
		</div>
	{/if}

	{#if storageHealth.writeFailed}
		<div class="pwa-toast" role="alert">
			<span>{t('storage.saveFailed')}</span>
			<button class="pwa-link" onclick={() => storageHealth.acknowledge()}>{t('pwa.dismiss')}</button>
		</div>
	{/if}
</div>

<style>
	.pwa-stack {
		position: fixed;
		inset-inline-end: 1rem;
		bottom: 1rem;
		z-index: 60;
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 0.5rem;
		pointer-events: none;
	}
	.pwa-pill,
	.pwa-toast {
		pointer-events: auto;
		display: flex;
		align-items: center;
		gap: 0.6rem;
		border-radius: 999px;
		border: 1px solid var(--border);
		background: var(--surface);
		padding: 0.5rem 0.9rem;
		font-size: 0.85rem;
		color: var(--text);
		box-shadow: 0 8px 30px rgb(0 0 0 / 0.18);
	}
	.pwa-toast {
		border-radius: var(--radius-card);
	}
	.pwa-offline {
		color: var(--muted);
	}
	.pwa-dot {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 999px;
		background: var(--muted);
	}
	.pwa-link {
		color: var(--muted);
		text-decoration: underline;
		font-size: 0.8rem;
	}
	.pwa-cta {
		border-radius: 999px;
		background: var(--accent);
		/* Theme-aware foreground: white fails contrast on the light-lavender dark
		   accent (~2.5:1); --accent-contrast is dark there, white in light mode. */
		color: var(--accent-contrast);
		padding: 0.25rem 0.75rem;
		font-weight: 600;
		font-size: 0.8rem;
	}
	.pwa-cta:hover {
		filter: brightness(1.05);
	}
</style>
