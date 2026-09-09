<script lang="ts">
	// Defines the Ochorus wordmark <symbol> ONCE per document; every BrandMark
	// then references it with <use>. Rendered once at the top of the root layout.
	// Hidden but present in the DOM so same-document <use href="#…"> resolves.
	import { LOCKUP_SYMBOL } from '$lib/brand/lockup';
</script>

<svg class="brand-sprite" aria-hidden="true" focusable="false" width="0" height="0">
	<!-- eslint-disable-next-line svelte/no-at-html-tags -- our own build-time asset -->
	{@html LOCKUP_SYMBOL}
</svg>

<style>
	.brand-sprite {
		position: absolute;
		width: 0;
		height: 0;
		overflow: hidden;
	}
</style>
