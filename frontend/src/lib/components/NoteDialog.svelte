<script lang="ts">
	/**
	 * The highlight/note editor.
	 *
	 * Both reading surfaces open the same dialog — pick a colour, write a note,
	 * save, or remove the highlight — and it existed as two byte-identical
	 * copies, markup and CSS, in <Reader> and in the chapter route. Nothing here
	 * knows about marks storage or which work is open; the host owns the state
	 * and what saving means, so this is the shape of the dialog and nothing else.
	 */
	import { i18n } from '$lib/i18n.svelte';
	import { focusTrap } from '$lib/actions/focusTrap';
	import { HIGHLIGHT_COLORS } from '$lib/reading-schema';

	interface Props {
		/** The note text, edited in place. */
		text: string;
		/** The highlight colour, edited in place. */
		color: string;
		/** Show the destructive action — only meaningful for an existing mark. */
		canRemove?: boolean;
		onSave: () => void;
		onRemove: () => void;
		onClose: () => void;
	}

	let {
		text = $bindable(),
		color = $bindable(),
		canRemove = false,
		onSave,
		onRemove,
		onClose
	}: Props = $props();

	const t = i18n.t;
</script>

<div
	class="note-overlay"
	role="dialog"
	aria-modal="true"
	aria-label={t('reader.note')}
	use:focusTrap={{ onEscape: onClose }}
>
	<div class="note-card">
		<h2 class="mb-2 text-h3">{t('reader.note')}</h2>
		<div class="mb-3 flex items-center gap-2.5" role="group" aria-label={t('reader.highlight')}>
			{#each HIGHLIGHT_COLORS as c (c)}
				<button
					type="button"
					class="hl-swatch"
					data-color={c}
					class:active={color === c}
					aria-pressed={color === c}
					aria-label="{t('reader.highlight')}: {t(`reader.hl_${c}`)}"
					title={t(`reader.hl_${c}`)}
					onclick={() => (color = c)}
				></button>
			{/each}
		</div>
		<textarea
			bind:value={text}
			rows="5"
			class="field w-full"
			aria-label={t('reader.note')}
			placeholder="…"
		></textarea>
		<div class="mt-3 flex items-center gap-2">
			{#if canRemove}
				<button class="btn btn-ghost text-danger" onclick={onRemove}>
					{t('reader.removeHighlight')}
				</button>
			{/if}
			<button class="btn btn-ghost ms-auto" onclick={onClose}>{t('common.cancel')}</button>
			<button class="btn btn-primary" onclick={onSave}>{t('common.save')}</button>
		</div>
	</div>
</div>

<style>
	/* The colour swatches (.hl-swatch and its per-colour variants) are styled
	   globally in app.css. */
	.note-overlay {
		position: fixed;
		inset: 0;
		z-index: 50;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
		background: rgb(0 0 0 / 0.4);
	}
	.note-card {
		width: 100%;
		max-width: 32rem;
		border-radius: var(--radius-card);
		border: 1px solid var(--border);
		background: var(--surface);
		padding: 1.25rem;
		box-shadow: var(--shadow-popover);
	}
</style>
