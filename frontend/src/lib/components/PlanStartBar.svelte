<script lang="ts">
	import { portal } from '$lib/actions/portal';

	/**
	 * The plan page's read verb, pinned to the foot of a PHONE screen whenever
	 * the read card is off screen (the page decides when to mount it) — so the
	 * one action the page exists for is a thumb away from the first screen,
	 * where the cover fan pushes the card below the fold, to the bottom of a
	 * long day list. Hidden from sm up. It docks on the tab bar (`--tabbar-h`),
	 * or on the screen's edge where there is none. Portalled: `.page-col` is
	 * transformed, which would otherwise pin `position: fixed` to the column.
	 */
	let {
		href,
		label,
		title,
		meta,
		onstart
	}: { href: string; label: string; title: string; meta: string; onstart?: () => void } = $props();

	let barEl = $state<HTMLElement>();

	/**
	 * Publish the bar's height as --startbar-h, from which the style below
	 * derives --listenbar-h — the variable the fixed bottom chrome (the PWA
	 * toasts, FloatingBookmark) already clears — so a toast stacks above the
	 * bar instead of covering its button. Measured, like ListenBar's: the
	 * height moves with the type scale.
	 */
	$effect(() => {
		if (!barEl) return;
		const root = document.documentElement;
		const ro = new ResizeObserver(([entry]) => {
			root.style.setProperty('--startbar-h', `${Math.round(entry.target.getBoundingClientRect().height)}px`);
		});
		ro.observe(barEl);
		return () => {
			ro.disconnect();
			root.style.removeProperty('--startbar-h');
		};
	});
</script>

<div class="reader-dock plan-startbar" bind:this={barEl} use:portal>
	<div class="min-w-0 flex-1">
		<p class="truncate text-small text-muted">{meta}</p>
		<p class="truncate font-semibold text-text" dir="auto">{title}</p>
	</div>
	<a {href} class="btn btn-primary shrink-0" onclick={onstart}>{label}</a>
</div>

<style>
	/* The glass chrome is .reader-dock's (app.css); this only places it. */
	.plan-startbar {
		display: none;
	}
	@media (max-width: 639.98px) {
		.plan-startbar {
			bottom: var(--tabbar-h, 0px);
			z-index: 30; /* under the tab bar's z-40 and the dialogs */
			display: flex;
			align-items: center;
			gap: 0.75rem;
			padding: 0.6rem 1rem;
			animation: startbar-in var(--duration-base) ease-out;
		}
		/* No tab bar: sit on the edge and fill the home-indicator strip, as
		   ListenBar does, rather than float above it. */
		:global(:root:not(:has(.tabbar))) .plan-startbar {
			padding-bottom: calc(0.6rem + env(safe-area-inset-bottom));
		}
		/* What the toasts clear, measured from the safe area as ListenBar's is:
		   the tab bar under the bar (less its own safe-area strip) plus the bar. */
		:global(:root:has(.plan-startbar)) {
			--listenbar-h: calc(
				var(--tabbar-h, env(safe-area-inset-bottom)) - env(safe-area-inset-bottom) + var(--startbar-h, 0px)
			);
		}
		/* Room under the footer's last line while the bar can cover it. */
		:global(:root:has(.plan-startbar) .site-footer) {
			padding-bottom: 5rem;
		}
	}
	@keyframes startbar-in {
		from {
			transform: translateY(100%);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.plan-startbar {
			animation: none;
		}
	}
</style>
