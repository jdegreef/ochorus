<script lang="ts">
	/**
	 * The feedback "+" in the centre of a reading surface's phone footer
	 * (`.foot-actions` — the chapter's and the sermon's). It stands in for the
	 * floating FeedbackFab, which sat over the text being read; FeedbackFab steps
	 * aside wherever a `.foot-actions` row is up. Signed-in readers only, like
	 * every other feedback entry point. Renders its own footer slot, so the
	 * row's spacing is the same whether or not it shows.
	 */
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import FeedbackDialog from '$lib/components/FeedbackDialog.svelte';

	const t = i18n.t;
	let open = $state(false);
</script>

{#if auth.enabled && auth.user}
	<span class="foot-slot">
		<button
			class="foot-add"
			aria-label={t('feedback.send')}
			title={t('feedback.send')}
			aria-haspopup="dialog"
			onclick={() => (open = true)}
			><svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.4"
				stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg
			></button
		>
	</span>
	{#if open}
		<FeedbackDialog source="fab" onClose={() => (open = false)} />
	{/if}
{/if}

<style>
	/* One footer slot's share of the row, as `.foot-btn` takes on each page. */
	.foot-slot {
		flex: 1 1 0;
		min-height: 2.9rem;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	/* The tab bar's round accent button (TabBar.svelte `.add`), sized to sit
	   inside the row rather than proud of it: the footer floats over the text,
	   so a raised button would cover the line above. */
	.foot-add {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 2.6rem;
		height: 2.6rem;
		border-radius: 999px;
		border: 1px solid var(--accent-soft-border);
		background: var(--accent);
		color: var(--accent-contrast);
		cursor: pointer;
	}
	.foot-add:active {
		transform: scale(0.96);
	}
	.foot-add:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 3px;
	}
	.foot-add svg {
		width: 1.35rem;
		height: 1.35rem;
	}
</style>
