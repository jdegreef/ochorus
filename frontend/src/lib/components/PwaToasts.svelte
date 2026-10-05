<script lang="ts">
	import { pwa } from '$lib/pwa.svelte';
	import { storageHealth } from '$lib/storageHealth.svelte';
	import { undo } from '$lib/undo.svelte';
	import { page } from '$app/stores';
	import { install } from '$lib/install.svelte';
	import { chromeIntentUrl } from '$lib/installPrompt';
	import { isReaderRoute } from '$lib/readerRoutes';
	import { readerUi } from '$lib/readerUi.svelte';
	import { signupNudge } from '$lib/signupNudge.svelte';
	import { seenOnView } from '$lib/signupSource';
	import { openFrom } from '$lib/signInSheet.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';

	const t = i18n.t;
	// Never over the text being read: the install offer waits for a page that
	// isn't the reader (see $lib/installPrompt for when it's offered at all).
	const showInstall = $derived(install.offer && !readerUi.focus && !isReaderRoute($page.route.id));
	const isAndroid = $derived(typeof navigator !== 'undefined' && /Android/i.test(navigator.userAgent));
	const chromeHref = $derived(showInstall ? chromeIntentUrl($page.url.href) : null);
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

	<!-- A one-line sign-up suggestion after the reader saved something an
	     account would keep (see $lib/signupNudge). Signed-out readers only. -->
	{#if signupNudge.current}
		{@const n = signupNudge.current}
		<div class="pwa-toast nudge">
			<span>
				{n.n == null ? t(n.textKey) : t(n.textKey).replace('%n%', new Intl.NumberFormat(getLang()).format(n.n))}
				<a href={n.href} class="nudge-link" use:seenOnView={n.source} onclick={(e) => {
						// Read before dismissing: `n` is derived from the slot dismiss empties.
						const source = n.source;
						signupNudge.dismiss();
						openFrom(e, source);
					}}>{t(n.linkKey)}</a
				>
			</span>
			<button class="pwa-link" onclick={() => signupNudge.dismiss()}>{t('pwa.dismiss')}</button>
		</div>
	{/if}

	<!-- Add to home screen (see $lib/install). Native: the browser's own
	     dialog. iPhone Safari: the two taps. In another app's browser: open
	     the page in the real browser first. -->
	{#if showInstall}
		<div class="pwa-toast install" role="region" aria-label={t('install.title')}>
			<div class="install-text">
				<b>{t('install.title')}</b>
				<span class="text-small text-muted">
					{install.platform === 'ios'
						? t('install.iosSteps')
						: install.platform === 'inapp'
							? t(isAndroid ? 'install.inappAndroid' : 'install.inappIos')
							: t('install.body')}
				</span>
			</div>
			<div class="install-actions">
				{#if install.platform === 'native'}
					<button class="btn btn-sm btn-primary" onclick={() => install.install()}>{t('install.button')}</button>
				{:else if install.platform === 'inapp' && isAndroid && chromeHref}
					<a class="btn btn-sm btn-primary" href={chromeHref}>{t('install.openChrome')}</a>
				{/if}
				<button class="pwa-link" onclick={() => install.later()}>{t('install.later')}</button>
			</div>
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
		   Listen bar, so clear whichever is up — plus any bar docked ON TOP of
		   that, which publishes its height as --dockbar-h (use:publishHeight;
		   ReadBar, the book and plan pages' phone read bar), whose button the pill
		   would cover. */
		bottom: calc(
			1rem + max(env(safe-area-inset-bottom) + var(--listenbar-h, 0px), var(--tabbar-h, 0px)) +
				var(--dockbar-h, 0px)
		);
		z-index: var(--z-toast);
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
	.install {
		flex-direction: column;
		align-items: stretch;
		max-width: min(22rem, calc(100vw - 2rem));
	}
	.install-text {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
	}
	.install-actions {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	.nudge {
		max-width: min(24rem, calc(100vw - 2rem));
	}
	.nudge-link {
		font-weight: 600;
		color: var(--accent);
	}
	.pwa-link {
		color: var(--muted);
		text-decoration: underline;
		font-size: var(--fs-small);
	}
</style>
