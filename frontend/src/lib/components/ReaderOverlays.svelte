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
	import ListenBar from '$lib/components/ListenBar.svelte';
	import NoteDialog from '$lib/components/NoteDialog.svelte';
	import ScripturePopover from '$lib/components/ScripturePopover.svelte';
	import SelectionBar from '$lib/components/SelectionBar.svelte';
	import type { ReaderText } from '$lib/readerText.svelte';

	let {
		reader,
		container
	}: {
		/** The shared machinery — see `$lib/readerText.svelte.ts`. */
		reader: ReaderText;
		/** The prose element the selection bar watches for selections. */
		container: HTMLElement | undefined;
	} = $props();
</script>

<SelectionBar
	{container}
	cite={reader.cite}
	onHighlight={reader.onHighlight}
	onNote={reader.openNoteForSelection}
	highlightColor={reader.highlightColor}
	onDefine={reader.onDefine}
/>

<ScripturePopover />
<DefinePopover />
<ListenBar />

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
