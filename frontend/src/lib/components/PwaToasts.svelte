<script lang="ts">
	import { pwa } from '$lib/pwa.svelte';
	import { storageHealth } from '$lib/storageHealth.svelte';
	import { undo } from '$lib/undo.svelte';
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

	<!-- Auto-dismissed after a beat: purely informational, unlike the update and
	     storage toasts below, which ask the reader to do something. -->
	{#if pwa.offlineReady}
		<div class="pwa-toast">
			<span>{t('pwa.ready')}</span>
			<button class="pwa-link" onclick={() => pwa.dismissOfflineReady()}>{t('pwa.dismiss')}</button>
		</div>
	{/if}

	{#if pwa.updateReady}
		<div class="pwa-toast pwa-update">
			<span>{t('pwa.updateReady')}</span>
			<button class="btn btn-sm btn-primary" onclick={() => pwa.applyUpdate()}>{t('pwa.refresh')}</button>
		</div>
	{/if}

	<!-- "Removed · Undo" — a removed highlight, note or bookmark, for a few
	     seconds (see $lib/undo). Same stack, same styles: it is one more short
	     message that asks for one tap. An `inline` offer is drawn by the modal
	     that made it instead (the stack's aria-live already announces the rest). -->
	{#if undo.current && !undo.current.inline}
		<div class="pwa-toast">
			<span
				>{t(
					undo.current.kind === 'finished'
						? 'undo.finished'
						: undo.current.kind === 'moved'
							? 'undo.moved'
							: undo.current.kind === 'note'
							? 'undo.noteCleared'
							: 'undo.removed'
				)}</span
			>
			<button class="btn btn-sm btn-primary" onclick={() => undo.act()}>{t('undo.action')}</button>
			<button class="pwa-link" onclick={() => undo.dismiss()}>{t('pwa.dismiss')}</button>
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
		/* Clear the audio player when one is up (it publishes --listenbar-h) and
		   the home-indicator strip below it. Listening offline used to put the
		   "reading from your device" pill straight over the transport controls.
		   The phone tab bar (--tabbar-h, safe area included) never shows with the
		   Listen bar, so clear whichever is up. */
		bottom: calc(
			1rem + max(env(safe-area-inset-bottom) + var(--listenbar-h, 0px), var(--tabbar-h, 0px))
		);
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
		font-size: var(--fs-small);
		color: var(--text);
		box-shadow: var(--shadow-popover);
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
		font-size: var(--fs-small);
	}
</style>
