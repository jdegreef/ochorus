<script lang="ts">
	// Test fixture: a DrawerShell inside a transformed column, fenced by
	// siblings, under an outer {#if} — so DrawerShell.test.ts can open, close
	// and tear down the drawer and see that nothing else moves or goes missing.
	import DrawerShell from '$lib/components/DrawerShell.svelte';

	let open = $state(false);
	let shown = $state(true);

	export function setOpen(v: boolean) {
		open = v;
	}
	export function setShown(v: boolean) {
		shown = v;
	}
	export function isOpen() {
		return open;
	}
</script>

<p id="before">before</p>
{#if shown}
	<div id="col" style="transform: translateX(-50%)">
		<span id="col-first">first</span>
		<DrawerShell bind:open title="Filters" placement="bottom">
			<button id="drawer-body">body</button>
		</DrawerShell>
		<span id="col-last">last</span>
	</div>
{/if}
<p id="after">after</p>
