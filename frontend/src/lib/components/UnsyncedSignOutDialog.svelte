<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { focusTrap } from '$lib/actions/focusTrap';

	/**
	 * Sign-out was asked for, but changes on this device haven't reached the
	 * account — usually because the reader is offline. Signing out wipes the
	 * device's reading data, so this asks first: stay, try again, or sign out
	 * and discard them. Rendered by the layout while `auth.signOutBlocked`.
	 */
	const t = i18n.t;
	let busy = $state(false);

	const stay = () => (auth.signOutBlocked = false);
	async function retry() {
		busy = true;
		await auth.signOut();
		busy = false;
	}
	async function discard() {
		busy = true;
		await auth.signOut({ force: true });
		busy = false;
	}
</script>

<div
	class="uso-overlay"
	role="alertdialog"
	aria-modal="true"
	aria-labelledby="uso-title"
	aria-describedby="uso-body"
	use:focusTrap={{ onEscape: stay }}
>
	<div class="uso-card">
		<h2 id="uso-title" class="mb-2 text-h3">{t('signout.unsyncedTitle')}</h2>
		<p id="uso-body" class="mb-5 text-body text-muted">{t('signout.unsyncedBody')}</p>
		<div class="flex flex-col gap-2">
			<button class="btn btn-primary" onclick={stay} disabled={busy}>{t('signout.stay')}</button>
			<button class="btn btn-ghost" onclick={retry} disabled={busy}>
				{busy ? t('settings.syncing') : t('signout.retry')}
			</button>
			<button class="btn btn-ghost uso-discard" onclick={discard} disabled={busy}>
				{t('signout.discard')}
			</button>
		</div>
	</div>
</div>

<style>
	.uso-overlay {
		position: fixed;
		inset: 0;
		z-index: 50;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
		background: rgb(0 0 0 / 0.4);
	}
	.uso-card {
		width: 100%;
		max-width: 26rem;
		border-radius: var(--radius-card);
		border: 1px solid var(--border);
		background: var(--surface);
		padding: 1.25rem;
		box-shadow: var(--shadow-popover);
	}
	.uso-discard {
		color: var(--danger);
	}
</style>
