<script lang="ts">
	/**
	 * The floating feedback button — a small "+" pinned bottom-right that opens the
	 * feedback dialog from anywhere on the site (Intercom-style).
	 *
	 * Shown only to a signed-in reader, and hidden where it would be in the way:
	 * in the reader's immersive focus mode, and over the admin console (admins have
	 * the feedback queue). Mounted once in the root layout; it captures the current
	 * page's context through the dialog and records `source: 'fab'`. On phones
	 * with the tab bar, or on a reading surface with its footer row (chapter,
	 * sermon), it steps aside: the bar's centre "+" does the same job.
	 *
	 * On a wide screen it says what it is — "+ Send feedback" — in the margin
	 * beside the page column, never wider than that margin; a bare "+" in the
	 * corner of a browse page read as "add something". And while it shows, the
	 * site footer keeps a clear strip at its foot so the button never sits on
	 * the page's last line.
	 */
	import { page } from '$app/stores';
	import { auth } from '$lib/auth.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { pageWidth } from '$lib/pageWidth.svelte';
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
		style="--pw: {pageWidth.rem}rem"
		aria-label={t('feedback.send')}
		title={t('feedback.send')}
		aria-haspopup="dialog"
		onclick={() => (open = true)}
	>
		<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.4"
			stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>
		<span class="fb-label" aria-hidden="true">{t('feedback.send')}</span>
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
		/* Clear whichever bottom bar is up — the chapter reader's progress footer
		   (--foot-h, which already includes the home-indicator strip) or the
		   Listen bar — as the floating bookmark does. It sat on top of the phone
		   reader's "Next" button. */
		bottom: calc(
			1rem +
				max(
					env(safe-area-inset-bottom),
					var(--foot-h, 0px),
					var(--listenbar-h, 0px) + env(safe-area-inset-bottom)
				)
		);
		z-index: var(--z-chrome); /* above content, below the dialog overlay */
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
		flex: none;
		width: 1.5rem;
		height: 1.5rem;
	}
	/* The label: only where the margin beside the page column can hold it, at
	   the default 76rem column. The cap follows the reader's own page width
	   (--pw, set on the button: it mounts outside the layout column that sets
	   it), so a wider column gets a narrower label that ellipses rather than
	   spill over the text. */
	.fb-label {
		display: none;
	}
	@media (min-width: 100rem) {
		.fb-fab {
			width: auto;
			max-width: calc((100vw - var(--pw, 76rem)) / 2 - 2rem);
			gap: 0.45rem;
			padding-inline: 0.9rem 1.15rem;
		}
		.fb-label {
			display: block;
			overflow: hidden;
			font-size: var(--fs-small);
			font-weight: 600;
			white-space: nowrap;
			text-overflow: ellipsis;
		}
	}
	/* Room under the footer's last row (the copyright line sits at the
	   reading end, exactly where the button floats) while the button shows.
	   Phones with the tab bar hide the button, so only from sm up. */
	@media (min-width: 640px) {
		:global(:root:has(.fb-fab) .site-footer) {
			padding-bottom: 4.5rem;
		}
	}
	/* Phones with the tab bar carry the "+" in its centre slot (TabBar.svelte),
	   and the reading surfaces in their footer's (FootFeedback.svelte) — so the floating
	   one would only duplicate it (and it covered "More", then the text). */
	/* The tab bar shows upright and sideways (TabBar's query list); the reading
	   footer's "+" only below 640px — so a sideways phone in a reader keeps this
	   button, the one feedback control it has. */
	@media (max-width: 639.98px), (max-height: 499.98px) and (pointer: coarse) {
		:global(:root:has(.tabbar)) .fb-fab {
			display: none;
		}
	}
	@media (max-width: 639.98px) {
		:global(:root:has(.foot-actions)) .fb-fab {
			display: none;
		}
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
