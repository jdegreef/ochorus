<script lang="ts">
	import { onDestroy } from 'svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { dictation } from '$lib/dictation.svelte';

	/**
	 * Speak instead of type, anywhere the Notebook takes writing — a note, a
	 * prayer, how it was answered, an update, the daily prayer. Each settled
	 * phrase is handed to `ontext` to add where the reader is writing; what is
	 * still being heard shows underneath. Not rendered where the browser has no
	 * speech recognition (Firefox), so nothing is offered that can't work.
	 */
	let { ontext, lang = getLang() }: { ontext: (text: string) => void; lang?: string } = $props();

	const t = i18n.t;
	const id = `dictate-${Math.random().toString(36).slice(2, 8)}`;
	const mine = $derived(dictation.listening && dictation.owner === id);

	function toggle() {
		if (mine) dictation.stop();
		else dictation.start(lang, ontext, id);
	}

	// A form that closes mid-sentence must not keep the microphone open.
	onDestroy(() => {
		if (dictation.owner === id) dictation.stop();
	});
</script>

{#if dictation.supported}
	<span class="dictate">
		<button
			type="button"
			class="btn btn-ghost btn-sm"
			class:listening={mine}
			aria-pressed={mine}
			title={t('notebook.dailySpeakHint')}
			onclick={toggle}
		>
			<span aria-hidden="true" class="me-1">🎙</span>{mine ? t('notebook.dailyListening') : t('notebook.dailySpeak')}
		</button>
		{#if mine && dictation.interim}
			<span class="interim" aria-live="polite">{dictation.interim}</span>
		{/if}
	</span>
{/if}

<style>
	.dictate {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		min-width: 0;
	}
	.listening {
		color: var(--danger);
	}
	/* A soft pulse while the microphone is open. */
	.listening span {
		animation: pulse 1.2s ease-in-out infinite;
	}
	@keyframes pulse {
		50% {
			opacity: 0.35;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.listening span {
			animation: none;
		}
	}
	.interim {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-family: var(--font-display);
		font-style: italic;
		font-size: var(--fs-small);
		color: var(--muted);
	}
</style>
