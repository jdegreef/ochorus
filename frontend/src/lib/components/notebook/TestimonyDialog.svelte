<script lang="ts">
	import { onDestroy } from 'svelte';
	import { i18n } from '$lib/i18n.svelte';
	import * as m from '$lib/paraglide/messages.js';
	import { focusTrap } from '$lib/actions/focusTrap';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import type { JournalEntry } from '$lib/journal';
	import {
		renderTestimonyCard,
		shareTestimonyCard,
		testimonyText,
		type TestimonyLabels,
		type TestimonyOptions
	} from '$lib/testimonyCard';

	/**
	 * Share an answered prayer as a testimony card — previewed first, because a
	 * prayer is personal: who it was for is left off unless the reader includes
	 * it, and the request itself can be left off too. Nothing leaves the device
	 * until they press Share.
	 */
	let { entry, locale, onclose }: { entry: JournalEntry; locale: string; onclose: () => void } = $props();

	const t = i18n.t;
	let includeRequest = $state(true);
	let includePerson = $state(false);
	let preview = $state<string | null>(null);
	let blob: Blob | null = null;
	let busy = $state(false);

	function waited(n: number): string {
		const s =
			n === 0
				? t('notebook.answeredSameDay')
				: n === 1
					? t('notebook.answeredAfterOneDay')
					: m.notebook_answered_after_days({ n: String(n) });
		return s.charAt(0).toLocaleUpperCase(locale) + s.slice(1);
	}

	const labels: TestimonyLabels = {
		heading: t('notebook.answeredPrayer'),
		prayed: t('notebook.testimonyPrayed'),
		answered: t('notebook.otdAnswered'),
		forPerson: (person) => m.notebook_testimony_for({ person }),
		meta: (days, on) => `${waited(days)} · ${on}`
	};

	const opts = $derived<TestimonyOptions>({ includeRequest, includePerson, locale, site: 'ochorus.com' });
	const text = $derived(testimonyText(entry, opts, labels));

	// Redraw the preview whenever what goes on the card changes.
	$effect(() => {
		const current = text;
		const o = opts;
		let cancelled = false;
		renderTestimonyCard(current, labels.answered, o).then((b) => {
			if (cancelled) return;
			blob = b;
			if (preview) URL.revokeObjectURL(preview);
			preview = URL.createObjectURL(b);
		});
		return () => {
			cancelled = true;
		};
	});
	onDestroy(() => {
		if (preview) URL.revokeObjectURL(preview);
	});

	async function share() {
		if (!blob) return;
		busy = true;
		try {
			await shareTestimonyCard(blob, text);
		} finally {
			busy = false;
		}
	}
</script>

<div
	class="td-overlay"
	role="dialog"
	aria-modal="true"
	aria-label={t('notebook.testimonyTitle')}
	use:focusTrap={{ onEscape: onclose }}
>
	<div class="td-card">
		<h2 class="text-h3">{t('notebook.testimonyTitle')}</h2>
		<div class="preview">
			{#if preview}
				<img src={preview} use:hydrateSrc={{ src: preview }} alt={[text.heading, text.request, text.answer, text.meta]
						.filter(Boolean)
						.map((s) => s!.replace(/[.!?…]+$/, ''))
						.join('. ')} />
			{/if}
		</div>
		<fieldset class="mt-3 grid gap-1.5 text-small">
			<label><input type="checkbox" bind:checked={includeRequest} /> {t('notebook.testimonyIncludeRequest')}</label>
			{#if entry.person}
				<label
					><input type="checkbox" bind:checked={includePerson} />
					{m.notebook_testimony_include_person({ person: entry.person })}</label
				>
			{/if}
		</fieldset>
		<p class="mt-2 text-micro text-muted">{t('notebook.testimonyHint')}</p>
		<div class="mt-4 flex justify-end gap-2">
			<button class="btn btn-ghost" onclick={onclose}>{t('common.cancel')}</button>
			<button class="btn btn-primary" onclick={share} disabled={!preview || busy}>{t('reader.share')}</button>
		</div>
	</div>
</div>

<style>
	.td-overlay {
		position: fixed;
		inset: 0;
		z-index: 50;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
		background: rgb(0 0 0 / 0.4);
	}
	.td-card {
		width: 100%;
		max-width: 28rem;
		max-height: calc(100dvh - 2rem);
		overflow-y: auto;
		border-radius: var(--radius-card);
		border: 1px solid var(--border);
		background: var(--surface);
		padding: 1.25rem;
		box-shadow: var(--shadow-popover);
	}
	.preview {
		margin-top: 0.75rem;
		aspect-ratio: 1;
		border-radius: var(--radius-sm);
		background: var(--surface-2);
		overflow: hidden;
	}
	.preview img {
		display: block;
		width: 100%;
		height: 100%;
	}
	fieldset label {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		cursor: pointer;
	}
</style>
