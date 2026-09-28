<script lang="ts">
	// Test fixture: any one overlay inside a transformed column, fenced by
	// siblings, under an outer {#if} — so overlayPortal.test.ts can mount, close
	// and tear down each portalled overlay and see that nothing else moves or
	// goes missing. The DrawerShellHost shape, with the overlay passed in.
	import type { Component } from 'svelte';

	let {
		overlay: Overlay,
		props = {}
	}: { overlay: Component<Record<string, unknown>>; props?: Record<string, unknown> } = $props();

	let mounted = $state(false);
	let shown = $state(true);

	export function setMounted(v: boolean) {
		mounted = v;
	}
	export function setShown(v: boolean) {
		shown = v;
	}
</script>

<p id="before">before</p>
{#if shown}
	<div id="col" style="transform: translateX(-50%)">
		<span id="col-first">first</span>
		{#if mounted}
			<Overlay {...props} />
		{/if}
		<span id="col-last">last</span>
	</div>
{/if}
<p id="after">after</p>
