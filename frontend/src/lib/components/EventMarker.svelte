<!--
	An event marker on the Engagement page: a small round glyph, coloured by
	kind (an email to readers, a language taken live, works added). A button
	when `onpoint` is given (the chart's markers), a plain mark otherwise
	(the legend, the summary, the phone list).
-->
<script lang="ts">
	import { EVENT_KINDS, type EngagementEventKind } from '$lib/library-admin';

	let {
		kind,
		small = false,
		label,
		active = false,
		onpoint
	}: {
		kind: EngagementEventKind;
		small?: boolean;
		/** The button's accessible name; a plain mark is decorative. */
		label?: string;
		active?: boolean;
		onpoint?: () => void;
	} = $props();
</script>

{#if onpoint}
	<button
		type="button"
		class="ev ev-{kind}"
		class:ev-on={active}
		aria-label={label}
		onmouseenter={onpoint}
		onfocus={onpoint}
		onclick={onpoint}>{EVENT_KINDS[kind].glyph}</button
	>
{:else}
	<span class="ev ev-{kind}" class:ev-sm={small} aria-hidden="true">{EVENT_KINDS[kind].glyph}</span>
{/if}

<style>
	.ev {
		display: inline-grid;
		place-items: center;
		width: 1.125rem;
		height: 1.125rem;
		flex: none;
		border: 0;
		padding: 0;
		border-radius: 999px;
		color: var(--surface);
		font-size: var(--fs-micro);
		font-weight: 700;
		line-height: 1;
	}
	.ev-sm {
		width: 0.875rem;
		height: 0.875rem;
	}
	.ev-email {
		background: var(--accent);
	}
	.ev-language {
		background: var(--border-strong);
	}
	.ev-works {
		background: var(--gold);
	}
	button.ev {
		cursor: pointer;
	}
	button.ev:focus-visible,
	.ev-on {
		outline: 2px solid var(--text);
		outline-offset: 1px;
	}
</style>
