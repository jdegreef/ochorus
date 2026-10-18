<script lang="ts">
	import { portal } from '$lib/actions/portal';
	import { publishHeight } from '$lib/actions/publishHeight';
	import { holdFlag } from '$lib/presenceFlag';

	/**
	 * The read verb pinned to the foot of a phone screen, once the page's own
	 * read card has scrolled away (`show` — the caller's `elementVisible` gate,
	 * so there are never two primaries on screen). Shared by the book page and
	 * the plan page, so the two can't drift in look, clearance or breakpoint.
	 *
	 * `hideFrom` is the width at which the page keeps its read verb in view by
	 * other means and the bar steps aside: `sm` for the book page (its sticky
	 * sub-nav carries a Continue button from 640px), `lg` for the plan page (its
	 * side panel sticks from 1024px).
	 *
	 * Portalled to <body>, as every fixed overlay is, and clear of the tab bar
	 * and the listen bar (the shared bottom-chrome expression). While it is up,
	 * the body gains room at its foot so the footer's last line clears it.
	 */
	let {
		show,
		eyebrow,
		title,
		href,
		label,
		onread,
		hideFrom = 'lg'
	}: {
		show: boolean;
		/** Small line above the title — "Day 14 of 96", the book's name. */
		eyebrow: string;
		/** What the button opens — the day's or chapter's title. */
		title: string;
		href: string;
		/** The read verb: Start, Continue, Begin reading. */
		label: string;
		onread?: () => void;
		hideFrom?: 'sm' | 'lg';
	} = $props();

	// <body data-read-bar> (and data-read-bar-until-sm) while the bar is up, for
	// the foot clearance below: a flag rather than `body:has(.read-bar)`, which
	// restyled the whole page each time the bar came or went on scroll (INP).
	$effect(() => {
		if (!show) return;
		const releases = [holdFlag(document.body, 'data-read-bar')];
		if (hideFrom === 'sm') releases.push(holdFlag(document.body, 'data-read-bar-until-sm'));
		return () => releases.forEach((release) => release());
	});
</script>

{#if show}
	<!-- Its height published as --dockbar-h, so other fixed chrome (the PWA
	     toasts) sits above it; 0 where it steps aside (display: none). -->
	<div class="read-bar" class:until-sm={hideFrom === 'sm'} use:portal use:publishHeight={'--dockbar-h'}>
		<span class="min-w-0 flex-1">
			<span class="block truncate text-eyebrow text-muted" dir="auto">{eyebrow}</span>
			<span class="block truncate text-small font-semibold text-text" dir="auto">{title}</span>
		</span>
		<a {href} class="btn btn-primary shrink-0" onclick={onread}>{label}</a>
	</div>
{/if}

<style>
	.read-bar {
		position: fixed;
		inset-inline: 0;
		/* The shared clearance every fixed bottom chrome uses (.min-left). */
		bottom: max(env(safe-area-inset-bottom) + var(--listenbar-h, 0px), var(--tabbar-h, 0px));
		z-index: var(--z-popover);
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.625rem 1.25rem;
		border-top: 1px solid var(--border);
		background: var(--surface);
		box-shadow: var(--shadow-card);
	}
	/* While the bar is up, the page's foot scrolls clear of it. First, so the
	   resets below win wherever the bar steps aside. */
	:global(body[data-read-bar]) {
		padding-bottom: 4.5rem;
	}
	@media (min-width: 1024px) {
		.read-bar {
			display: none;
		}
		:global(body[data-read-bar]) {
			padding-bottom: 0;
		}
	}
	@media (min-width: 640px) {
		.read-bar.until-sm {
			display: none;
		}
		:global(body[data-read-bar-until-sm]) {
			padding-bottom: 0;
		}
	}
</style>
