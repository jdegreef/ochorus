<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import { define } from '$lib/define.svelte';
	import { focusTrap } from '$lib/actions/focusTrap';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;
	let card = $state<HTMLDivElement>();

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') define.close();
	}
	function onPointerDown(e: MouseEvent) {
		if (define.open && card && !card.contains(e.target as Node)) define.close();
	}
</script>

<svelte:window onkeydown={onKey} onmousedown={onPointerDown} />

{#if define.open}
	<div
		bind:this={card}
		class="define-pop"
		style="top: {define.top}px; left: {define.left}px"
		role="dialog"
		aria-label="{t('reader.definition')}: {define.word}"
		use:focusTrap={{ onEscape: () => define.close() }}
	>
		<div class="flex items-baseline justify-between gap-3">
			<span class="define-word">{define.word}</span>
			{#if define.result?.phonetic}
				<span class="text-small text-muted">{define.result.phonetic}</span>
			{/if}
			<button class="define-close" onclick={() => define.close()} aria-label={t('a11y.close')}><Icon name="close" size={14} /></button>
		</div>

		{#if define.loading}
			<p class="mt-2 text-small text-muted">…</p>
		{:else if define.result && define.result.entries.length}
			{#each define.result.entries as entry, i (i)}
				<p class="mt-2 text-small leading-relaxed text-text">
					{#if entry.partOfSpeech}<em class="text-muted">{entry.partOfSpeech} · </em>{/if}
					{entry.text}
				</p>
			{/each}
			<p class="eyebrow mt-2 text-muted">
				{define.result.source === 'glossary' ? t('reader.glossarySource') : t('reader.dictionarySource')}
			</p>
		{:else}
			<p class="mt-2 text-small text-muted">{t('reader.noDefinition')}</p>
		{/if}
	</div>
{/if}

<style>
	.define-pop {
		position: absolute;
		z-index: 45;
		width: min(20rem, calc(100vw - 2rem));
		transform: translate(-50%, 0.5rem);
		padding: 0.9rem 1rem;
		border-radius: var(--radius-card);
		border: 1px solid var(--border);
		background: var(--surface);
		box-shadow: var(--shadow-popover);
	}
	.define-word {
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		font-weight: 600;
		color: var(--text);
	}
	.define-close {
		margin-inline-start: auto;
		padding: 0 0.25rem;
		color: var(--muted);
		cursor: pointer;
	}
	.define-close:hover {
		color: var(--text);
	}
</style>
