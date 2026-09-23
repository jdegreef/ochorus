<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { i18n } from '$lib/i18n.svelte';
	import * as m from '$lib/paraglide/messages.js';
	import { auth } from '$lib/auth.svelte';
	import { localizeHref } from '$lib/href';
	import { loginHref } from '$lib/loginHref';
	import { journalSync } from '$lib/journalSyncState.svelte';
	import { readingSync } from '$lib/readingSync';

	/**
	 * One line under the Notebook's date saying where the reader's writing is:
	 * only on this device (signed out), offline, waiting to sync, or synced —
	 * so no one has to wonder whether a prayer written on the bus is safe.
	 * Opening the Notebook signed in and online delivers anything still owed.
	 */
	const t = i18n.t;

	const signedIn = $derived(auth.enabled && !!auth.user);
	const status = $derived(
		!signedIn
			? 'device'
			: !journalSync.online
				? 'offline'
				: journalSync.count
					? 'waiting'
					: 'synced'
	);
	let syncing = $state(false);

	async function syncNow() {
		syncing = true;
		await readingSync.flushJournal();
		syncing = false;
	}

	onMount(() => {
		if (signedIn && journalSync.online && journalSync.count) void syncNow();
	});
</script>

<p class="sync sync-{status}" role="status">
	{#if status === 'device'}
		<span aria-hidden="true">📱</span>
		{t('notebook.syncDevice')}
		{#if auth.enabled}
			<a href={localizeHref(loginHref($page.url.pathname, $page.url.search))}>{t('notebook.syncSignIn')}</a>
		{/if}
	{:else if status === 'offline'}
		<span aria-hidden="true">⚡</span>
		{journalSync.count
			? m.notebook_sync_offline_waiting({ n: String(journalSync.count) })
			: t('notebook.syncOffline')}
	{:else if status === 'waiting'}
		<span aria-hidden="true">⏳</span>
		{m.notebook_sync_waiting({ n: String(journalSync.count) })}
		<button class="sync-now" onclick={syncNow} disabled={syncing}>
			{syncing ? t('notebook.syncing') : t('notebook.syncNow')}
		</button>
	{:else}
		<span aria-hidden="true">☁</span>
		{t('notebook.syncDone')}
	{/if}
</p>

<style>
	.sync {
		margin-top: 0.2rem;
		font-family: var(--font-sans);
		font-size: var(--fs-micro);
		font-style: normal;
		color: var(--muted);
	}
	.sync span {
		margin-inline-end: 0.25rem;
	}
	.sync-offline,
	.sync-waiting {
		color: var(--warning);
		font-weight: 600;
	}
	.sync a,
	.sync-now {
		margin-inline-start: 0.35rem;
		color: var(--accent);
		font-weight: 600;
		cursor: pointer;
	}
	.sync-now:disabled {
		color: var(--muted);
		cursor: default;
	}
</style>
