<script lang="ts">
	import { sermonMonogram } from '$lib/sermonMonogram';
	import Monogram from './Monogram.svelte';

	/**
	 * A passage as a Monogram — "MAT" over 11 — for sermons (rows, tiles, the
	 * plate) and topics (their epigraph). With no parseable passage it wears
	 * the title's first letter, set the same way.
	 */
	let {
		scriptureRef,
		title,
		hue,
		class: klass = ''
	}: {
		scriptureRef: string | null | undefined;
		title: string;
		/** Sets `--chip-hue` here rather than inheriting it. */
		hue?: string;
		class?: string;
	} = $props();

	const mark = $derived(sermonMonogram(scriptureRef, title));
</script>

<Monogram top={mark.book} value={mark.chapter} {hue} class={klass} />
