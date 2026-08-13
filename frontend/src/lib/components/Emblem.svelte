<script lang="ts">
	// A multicolour illustrated emblem (see $lib/emblems.ts) — the richer
	// sibling of Icon.svelte's line glyphs, used on the browse shelves where
	// each topic / plan / sermon wears art of its own. Decorative by default
	// (aria-hidden); pass `label` for an accessible name when the emblem has no
	// adjacent text.
	//
	// Inside an .emblem-chip the chip sizes the art (its `> svg` rule wins over
	// the width/height attributes), so `size` matters only for bare emblems.
	import { EMBLEM_ART, type EmblemName } from '$lib/emblems';

	let {
		name,
		size = 36,
		label,
		class: klass = ''
	}: {
		name: EmblemName;
		size?: number;
		label?: string;
		class?: string;
	} = $props();
</script>

<svg
	class={klass}
	width={size}
	height={size}
	viewBox="0 0 48 48"
	fill="none"
	role={label ? 'img' : undefined}
	aria-label={label}
	aria-hidden={label ? undefined : 'true'}
>
	<!-- eslint-disable-next-line svelte/no-at-html-tags -- static author-controlled
	     artwork strings from $lib/emblems.ts, never user input -->
	{@html EMBLEM_ART[name]}
</svg>
