<script lang="ts">
	import { scripture } from '$lib/scripture.svelte';
	import { focusTrap } from '$lib/actions/focusTrap';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;
	let card = $state<HTMLDivElement>();

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') scripture.close();
	}
	function onPointerDown(e: MouseEvent) {
		if (scripture.open && card && !card.contains(e.target as Node)) scripture.close();
	}
</script>

<svelte:window onkeydown={onKey} onmousedown={onPointerDown} />

{#if scripture.open}
	<div
		bind:this={card}
		class="scripture-pop"
		style="top: {scripture.top}px; left: {scripture.left}px"
		role="dialog"
		aria-label="{t('reader.scripture')}: {scripture.result?.reference ?? scripture.ref}"
		use:focusTrap={{ onEscape: () => scripture.close() }}
	>
		<div class="flex items-baseline justify-between gap-3">
			<span class="scripture-ref-title">{scripture.result?.reference ?? scripture.ref}</span>
			<button class="scripture-close" onclick={() => scripture.close()} aria-label={t('a11y.close')}>✕</button>
		</div>

		{#if scripture.loading}
			<p class="mt-2 text-small text-muted">…</p>
		{:else if scripture.result}
			<p class="scripture-body mt-2">
				{#each scripture.result.verses as v (v.number)}<sup class="scripture-num">{v.number}</sup
					>{v.text}{' '}{/each}
			</p>
			<p class="mt-2 text-micro uppercase tracking-wider text-muted">{scripture.result.version}</p>
		{:else}
			<p class="mt-2 text-small text-muted">{t('reader.scriptureUnavailable')}</p>
		{/if}
	</div>
{/if}

<style>
	.scripture-pop {
		position: absolute;
		z-index: 45;
		width: min(22rem, calc(100vw - 2rem));
		transform: translate(-50%, 0.5rem);
		padding: 0.9rem 1rem;
		border-radius: var(--radius-card);
		border: 1px solid var(--border);
		background: var(--surface);
		box-shadow: var(--shadow-popover);
	}
	.scripture-ref-title {
		font-family: var(--font-display);
		font-size: var(--fs-body);
		font-weight: 600;
		color: var(--accent);
	}
	.scripture-body {
		font-size: var(--fs-body);
		line-height: 1.6;
		color: var(--text);
	}
	.scripture-num {
		font-size: 0.62em;
		font-weight: 600;
		color: var(--muted);
		margin-inline-end: 0.15em;
		vertical-align: super;
	}
	.scripture-close {
		margin-inline-start: auto;
		padding: 0 0.25rem;
		color: var(--muted);
		cursor: pointer;
	}
	.scripture-close:hover {
		color: var(--text);
	}
</style>
