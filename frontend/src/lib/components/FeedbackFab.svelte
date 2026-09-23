<script lang="ts">
	/**
	 * The floating feedback button — a small "+" pinned bottom-right that opens the
	 * feedback dialog from anywhere on the site (Intercom-style).
	 *
	 * Shown only to a signed-in reader, and hidden where it would be in the way:
	 * in the reader's immersive focus mode, and over the admin console (admins have
	 * the feedback queue). Mounted once in the root layout; it captures the current
	 * page's context through the dialog and records `source: 'fab'`.
	 */
	import { page } from '$app/stores';
	import { auth } from '$lib/auth.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import FeedbackDialog from '$lib/components/FeedbackDialog.svelte';

	const t = i18n.t;
	let open = $state(false);

	const show = $derived(
		auth.enabled &&
			!!auth.user &&
			!readerUi.focus &&
			!($page.route.id ?? '').startsWith('/admin')
	);
</script>

{#if show}
	<button
		class="fb-fab"
		aria-label={t('feedback.send')}
		title={t('feedback.send')}
		aria-haspopup="dialog"
		onclick={() => (open = true)}
	>
		<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.4"
			stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>
	</button>
{/if}

{#if open}
	<FeedbackDialog source="fab" onClose={() => (open = false)} />
{/if}

<style>
	.fb-fab {
		position: fixed;
		/* Logical, so it sits at the reading end — bottom-right in English,
		   bottom-left in Arabic. */
		inset-inline-end: 1rem;
		bottom: max(1rem, env(safe-area-inset-bottom));
		z-index: 40; /* above content, below the dialog overlay (z-50) */
		display: flex;
		align-items: center;
		justify-content: center;
		width: 3.25rem;
		height: 3.25rem;
		border-radius: 999px;
		border: 1px solid var(--accent-soft-border);
		background: var(--accent);
		color: var(--accent-contrast);
		box-shadow: var(--shadow-popover);
		cursor: pointer;
		transition:
			transform 0.15s ease,
			box-shadow 0.15s ease,
			filter 0.15s ease;
	}
	.fb-fab:hover {
		filter: brightness(1.06);
		transform: translateY(-1px);
	}
	.fb-fab:active {
		transform: translateY(0);
	}
	.fb-fab:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 3px;
	}
	.fb-fab svg {
		width: 1.5rem;
		height: 1.5rem;
	}
	@media (prefers-reduced-motion: reduce) {
		.fb-fab {
			transition: none;
		}
		.fb-fab:hover {
			transform: none;
		}
	}
</style>
