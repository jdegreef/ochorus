<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import ModalShell from '$lib/components/ModalShell.svelte';

	/**
	 * Sign-out was asked for, but changes on this device haven't reached the
	 * account — usually because the reader is offline. Signing out wipes the
	 * device's reading data, so this asks first: stay, try again, or sign out
	 * and discard them. Rendered by the layout while `auth.signOutBlocked`.
	 */
	const t = i18n.t;
	let busy = $state(false);

	const stay = () => (auth.signOutBlocked = false);
	async function signOut(force: boolean) {
		busy = true;
		await auth.signOut({ force });
		busy = false;
	}
</script>

<ModalShell
	onClose={stay}
	role="alertdialog"
	ariaLabelledby="uso-title"
	ariaDescribedby="uso-body"
	width="26rem"
>
	<h2 id="uso-title" class="mb-2 text-h3">{t('signout.unsyncedTitle')}</h2>
	<p id="uso-body" class="mb-5 text-body text-muted">{t('signout.unsyncedBody')}</p>
	<div class="flex flex-col gap-2">
		<button class="btn btn-primary" onclick={stay} disabled={busy}>{t('signout.stay')}</button>
		<button class="btn btn-ghost" onclick={() => signOut(false)} disabled={busy}>
			{busy ? t('settings.syncing') : t('signout.retry')}
		</button>
		<button class="btn btn-ghost text-danger" onclick={() => signOut(true)} disabled={busy}>
			{t('signout.discard')}
		</button>
	</div>
</ModalShell>
