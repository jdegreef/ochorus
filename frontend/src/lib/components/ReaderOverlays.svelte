<!--
	The four things that float above read prose: the selection bar, the scripture
	and dictionary popovers, the listen bar, and the note editor.

	They are a component of their own — rather than markup inside `Reader` —
	because they must be rendered OUTSIDE the element holding the prose. The
	chapter reader's page-turn mode puts a `translateX` on the container the prose
	sits in, and a `position: fixed` overlay inside a transformed ancestor is laid
	out against that ancestor rather than the viewport: every one of these would
	slide sideways with the page turn. Keeping them separate lets a surface place
	the prose where its layout needs it and these where the viewport is.
-->
<script lang="ts">
	import DefinePopover from '$lib/components/DefinePopover.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import ListenBar from '$lib/components/ListenBar.svelte';
	import NoteDialog from '$lib/components/NoteDialog.svelte';
	import ScripturePopover from '$lib/components/ScripturePopover.svelte';
	import SelectionBar from '$lib/components/SelectionBar.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { listen } from '$lib/listen.svelte';
	import type { ReaderText } from '$lib/readerText.svelte';

	const t = i18n.t;

	let {
		reader,
		container,
		language
	}: {
		/** The shared machinery — see `$lib/readerText.svelte.ts`. */
		reader: ReaderText;
		/** The prose element the selection bar watches for selections. */
		container: HTMLElement | undefined;
		/**
		 * The edition's language. The quote card draws the reader's own sentence
		 * onto a canvas, where a font stack has to be named outright — so it needs
		 * to know the script to pick a face that can actually draw it. Required,
		 * as it is on SelectionBar: a quote card with no language falls back to a
		 * Latin stack, which cannot draw Arabic or Devanagari at all.
		 */
		language: string;
	} = $props();
</script>

<SelectionBar
	{container}
	{language}
	cite={reader.cite}
	onHighlight={reader.onHighlight}
	onNote={reader.openNoteForSelection}
	highlightColor={reader.highlightColor}
	onDefine={reader.onDefine}
	onDefineClose={reader.onDefineClose}
/>

<ScripturePopover />
<DefinePopover />
<ListenBar />

{#if listen.noVoice}
	<!-- The listener tapped Listen but no voice the reader would speak with
	     resolves for this edition, so playback would be silent — say so instead
	     of failing quietly. -->
	<div class="reader-dock listen-notice" role="status">
		<span class="min-w-0 text-small">{t('reader.listenNoVoice')}</span>
		<button
			class="btn btn-icon btn-ghost shrink-0"
			onclick={() => listen.dismissNoVoice()}
			aria-label={t('a11y.close')}
		>
			<Icon name="close" size={16} />
		</button>
	</div>
{/if}

{#if reader.open}
	<NoteDialog
		bind:text={reader.draft}
		bind:color={reader.color}
		canRemove={!!reader.id}
		onSave={reader.saveNote}
		onRemove={reader.removeMark}
		onClose={reader.close}
	/>
{/if}

<style>
	/* Dock chrome (fixed, glass, border) comes from `.reader-dock` in app.css;
	   these are the notice's own inline layout and padding. */
	.listen-notice {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		max-width: 48rem;
		margin-inline: auto;
		padding: 0.625rem 1rem;
		padding-bottom: calc(0.625rem + env(safe-area-inset-bottom));
	}
</style>
