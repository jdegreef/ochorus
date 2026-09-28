<script lang="ts">
	/**
	 * Writing in the Notebook without leaving the text: "Write about this" and
	 * "Pray this" on the reader's selection bar open this over the page, with the
	 * passage quoted at the top. What is saved keeps the passage as its source,
	 * so the Notebook can quote it and link straight back to the paragraph.
	 */
	import { i18n } from '$lib/i18n.svelte';
	import ModalShell from '$lib/components/ModalShell.svelte';
	import type { EntrySource, JournalKind } from '$lib/journal';
	import type { EntryDraft } from '$lib/journal.svelte';
	import EntryComposer from './EntryComposer.svelte';

	let {
		kind,
		source,
		onsave,
		onclose
	}: {
		kind: JournalKind;
		source: EntrySource;
		onsave: (draft: EntryDraft) => void;
		onclose: () => void;
	} = $props();

	const t = i18n.t;
</script>

<ModalShell
	onClose={onclose}
	ariaLabel={kind === 'prayer' ? t('reader.prayThis') : t('reader.writeAbout')}
	width="34rem"
>
	<blockquote class="jd-quote">
		<p>“{source.quote}”</p>
		<footer class="text-micro text-muted">{source.title}</footer>
	</blockquote>
	<EntryComposer editing {kind} {onsave} oncancel={onclose} />
</ModalShell>

<style>
	.jd-quote {
		margin-bottom: 1rem;
		padding-inline-start: 0.9rem;
		border-inline-start: 3px solid color-mix(in srgb, var(--gold) 60%, transparent);
	}
	.jd-quote p {
		font-family: var(--font-display);
		font-style: italic;
		line-height: 1.6;
		color: var(--text);
		display: -webkit-box;
		-webkit-line-clamp: 6;
		line-clamp: 6;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
